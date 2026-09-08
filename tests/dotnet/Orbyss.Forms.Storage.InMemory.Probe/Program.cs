using System.Text;
using Orbyss.Forms;

var formActor = new FormAuditActor("author-1", "user");
var metadata = new Dictionary<string, string>(StringComparer.Ordinal) { ["owner"] = "forms" };
var definition = new FormDefinition(new FormId("registration"), new FormRevision(1), "Registration", "en", FormLifecycleState.Draft, [], new FormElementDefinition("root", FormElementKind.VerticalLayout, []), [], metadata);
var definitions = new InMemoryFormDefinitionStore();
var created = await definitions.WriteAsync(new FormDefinitionPersistenceCommand("create", "fp-create", definition, null, [], FormMutation("create", null, formActor, 1), true));
metadata["owner"] = "mutated-after-write";
var stored = await definitions.GetAsync(definition.Id);
Require(stored?.Definition.Metadata?["owner"] == "forms", "form store leaked a caller-owned reference");
var createReplay = await definitions.ReplayAsync(definition.Id, "create", "fp-create");
Require(createReplay?.WasReplay == true && createReplay.Snapshot.Version == created.Snapshot.Version, "form definition exact replay failed");
await RequireThrowsAsync<InvalidOperationException>(() => definitions.ReplayAsync(definition.Id, "create", "different").AsTask(), "form definition accepted conflicting idempotency input");
var replacement = definition with { Revision = new FormRevision(2), Name = "Registration 2" };
var replaced = await definitions.WriteAsync(new FormDefinitionPersistenceCommand("replace", "fp-replace", replacement, null, [], FormMutation("replace", created.Snapshot.Version, formActor, 2)));
await RequireThrowsAsync<InvalidOperationException>(() => definitions.WriteAsync(new FormDefinitionPersistenceCommand("replace", "fp-stale", replacement with { Revision = new FormRevision(3) }, null, [], FormMutation("stale", created.Snapshot.Version, formActor, 3))).AsTask(), "form definition accepted a stale write");
Require((await ReadAllAsync(definitions.FindAsync())).Count == 1 && replaced.Snapshot.AuditTrail.Count == 2, "form definition enumeration or audit failed");
var boundedDefinitions = new InMemoryFormDefinitionStore(new InMemoryFormStorageOptions { MaximumDocumentBytes = 1024 });
var oversizedDefinition = definition with { Metadata = new Dictionary<string, string> { ["oversized"] = new string('x', 2048) } };
await RequireThrowsAsync<InvalidOperationException>(() => boundedDefinitions.WriteAsync(new FormDefinitionPersistenceCommand("create", "fp-oversized", oversizedDefinition, null, [], FormMutation("oversized", null, formActor, 3), true)).AsTask(), "oversized in-memory form definition was accepted");

var candidate = new FormCandidate(definition.Id, new FormRevision(2), new FormArtifact("application/schema+json", "{}", "data-sha"), new FormArtifact("application/json", "{}", "ui-sha"), [], [], [], [], DateTimeOffset.UnixEpoch, "candidate-sha");
var release = new FormRelease(new FormReleaseId("registration-r2"), candidate, DateTimeOffset.UnixEpoch.AddMinutes(4), formActor, ["probe"]);
var releases = new InMemoryFormReleaseStore();
await releases.WriteAsync(release);
await releases.WriteAsync(release);
await RequireThrowsAsync<InvalidOperationException>(() => releases.WriteAsync(release with { Evidence = ["different"] }).AsTask(), "immutable form release overwrite was accepted");
var retired = await releases.RetireAsync(release.Id, "fp-retire", FormMutation("retire", new FormConcurrencyToken(candidate.CandidateSha256), formActor, 5));
var retireReplay = await releases.RetireAsync(release.Id, "fp-retire", FormMutation("retire", new FormConcurrencyToken(candidate.CandidateSha256), formActor, 5));
Require(retired.Value.Retired && retireReplay.WasReplay && (await releases.GetAsync(release.Id))?.Retired == true, "form release retirement failed");

var draft = new FormDraft(new FormDraftId("draft-1"), release.Id, "owner-1", new FormDataDocument("{}", "data"), FormDraftState.Active, DateTimeOffset.UnixEpoch, DateTimeOffset.UnixEpoch, formActor);
var responses = new InMemoryFormSubmissionStore();
var draftCreated = await responses.PersistAsync(new FormSubmissionPersistenceCommand("create", "fp-draft", draft, null, FormMutation("draft-create", null, formActor, 6), true));
var draftReplay = await responses.ReplayAsync(draft.Id, "draft-create", "fp-draft");
Require(draftReplay?.WasReplay == true && (await responses.GetByDraftAsync(draft.Id))?.Audit.Count == 1, "form response replay or audit failed");
await RequireThrowsAsync<InvalidOperationException>(() => responses.PersistAsync(new FormSubmissionPersistenceCommand("save", "fp-stale-draft", draft, null, FormMutation("draft-stale", new FormConcurrencyToken("stale"), formActor, 7))).AsTask(), "form response accepted a stale write");

var attachment = new FormAttachment(new FormAttachmentId("attachment-1"), draft.Id, "owner-1", "proof.txt", "text/plain", 5, "digest", FormAttachmentState.PendingScan, DateTimeOffset.UnixEpoch, DateTimeOffset.UnixEpoch, formActor);
var attachments = new InMemoryFormAttachmentStore();
var attachmentCreated = await attachments.PersistAsync(new FormAttachmentPersistenceCommand("create", "fp-attachment", attachment, "content-key", FormMutation("attachment-create", null, formActor, 8), true));
Require((await ReadAllAsync(attachments.FindByDraftAsync(draft.Id))).Single().Version == attachmentCreated.Snapshot.Version, "attachment metadata query failed");
var content = new InMemoryFormAttachmentContentStore(new InMemoryFormStorageOptions { MaximumAttachmentObjectBytes = 1024, MaximumAttachmentBytes = 1024 });
var written = await content.WriteQuarantinedAsync(attachment.Id, new MemoryStream(Encoding.UTF8.GetBytes("hello")), 16, 4);
Require(Encoding.UTF8.GetString(written.Prefix.Span) == "hell" && written.Length == 5, "attachment quarantine metadata failed");
await content.PromoteAsync(written.ContentKey);
await using (var stream = await content.OpenAvailableAsync(written.ContentKey)) { using var reader = new StreamReader(stream); Require(await reader.ReadToEndAsync() == "hello", "promoted attachment bytes changed"); }
await content.DeleteAsync(written.ContentKey);
await RequireThrowsAsync<KeyNotFoundException>(() => content.OpenAvailableAsync(written.ContentKey).AsTask(), "deleted attachment content remained available");
var boundedContent = new InMemoryFormAttachmentContentStore(new InMemoryFormStorageOptions { MaximumAttachmentObjectBytes = 4, MaximumAttachmentBytes = 8 });
await RequireThrowsAsync<FormAttachmentRejectedException>(() => boundedContent.WriteQuarantinedAsync(attachment.Id, new MemoryStream(Encoding.UTF8.GetBytes("hello")), 4, 4).AsTask(), "oversized in-memory attachment was accepted");


Console.WriteLine("Orbyss Forms in-memory storage probe passed.");

static FormMutationContext FormMutation(string key, FormConcurrencyToken? version, FormAuditActor actor, int minute) => new(key, version, actor, DateTimeOffset.UnixEpoch.AddMinutes(minute), "probe");
static async Task<List<T>> ReadAllAsync<T>(IAsyncEnumerable<T> values) { var result = new List<T>(); await foreach (var value in values) result.Add(value); return result; }
static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
static async Task RequireThrowsAsync<T>(Func<Task> action, string message) where T : Exception { try { await action(); } catch (T) { return; } throw new InvalidOperationException(message); }
