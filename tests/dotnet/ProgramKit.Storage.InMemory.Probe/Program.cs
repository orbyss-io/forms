using System.Text;
using ProgramKit.Forms;
using ProgramKit.Localization;

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

var localizationActor = new LocalizationAuditActor("translator-1", "user");
var catalog = new LocalizationCatalogDefinition(new LocalizationCatalogId("application"), new LocalizationRevision(1), "Application", "en", LocalizationLifecycleState.Draft, [new LocaleDefinition("en", TextDirection.LeftToRight, RequiredForPublication: true)], [], new Dictionary<string, string> { ["team"] = "core" });
var catalogs = new InMemoryLocalizationCatalogStore();
var catalogCreated = await catalogs.WriteAsync(new LocalizationCatalogPersistenceCommand("create", "fp-catalog", catalog, LocalizationMutation("catalog-create", null, localizationActor, 9), true));
var catalogReplay = await catalogs.ReplayAsync(catalog.Id, "catalog-create", "fp-catalog");
Require(catalogReplay?.WasReplay == true && catalogReplay.Snapshot.Version == catalogCreated.Snapshot.Version, "localization catalog replay failed");
await RequireThrowsAsync<InvalidOperationException>(() => catalogs.WriteAsync(new LocalizationCatalogPersistenceCommand("replace", "fp-catalog-stale", catalog with { Revision = new LocalizationRevision(2) }, LocalizationMutation("catalog-stale", new LocalizationConcurrencyToken("stale"), localizationActor, 10))).AsTask(), "localization catalog accepted a stale write");
var boundedCatalogs = new InMemoryLocalizationCatalogStore(new InMemoryLocalizationStorageOptions { MaximumDocumentBytes = 1024 });
var oversizedCatalog = catalog with { Metadata = new Dictionary<string, string> { ["oversized"] = new string('x', 2048) } };
await RequireThrowsAsync<InvalidOperationException>(() => boundedCatalogs.WriteAsync(new LocalizationCatalogPersistenceCommand("create", "fp-catalog-oversized", oversizedCatalog, LocalizationMutation("catalog-oversized", null, localizationActor, 10), true)).AsTask(), "oversized in-memory localization catalog was accepted");

var localizationRelease = new LocalizationRelease(new LocalizationReleaseId("application-r1"), catalog.Id, catalog.Revision, "en", catalog.Locales, [], "localization-sha", DateTimeOffset.UnixEpoch.AddMinutes(11), localizationActor);
var localizationReleases = new InMemoryLocalizationReleaseStore();
await localizationReleases.WriteAsync(localizationRelease);
var localizationRetired = await localizationReleases.RetireAsync(localizationRelease.Id, "fp-localization-retire", LocalizationMutation("localization-retire", new LocalizationConcurrencyToken(localizationRelease.Sha256), localizationActor, 12));
var localizationRetireReplay = await localizationReleases.RetireAsync(localizationRelease.Id, "fp-localization-retire", LocalizationMutation("localization-retire", new LocalizationConcurrencyToken(localizationRelease.Sha256), localizationActor, 12));
Require(localizationRetired.Value.Retired && localizationRetireReplay.WasReplay && (await ReadAllAsync(localizationReleases.FindByCatalogAsync(catalog.Id))).Single().Retired, "localization release retirement failed");

Console.WriteLine("Program Kit in-memory Forms and Localization storage probe passed.");

static FormMutationContext FormMutation(string key, FormConcurrencyToken? version, FormAuditActor actor, int minute) => new(key, version, actor, DateTimeOffset.UnixEpoch.AddMinutes(minute), "probe");
static LocalizationMutationContext LocalizationMutation(string key, LocalizationConcurrencyToken? version, LocalizationAuditActor actor, int minute) => new(key, version, actor, DateTimeOffset.UnixEpoch.AddMinutes(minute), "probe");
static async Task<List<T>> ReadAllAsync<T>(IAsyncEnumerable<T> values) { var result = new List<T>(); await foreach (var value in values) result.Add(value); return result; }
static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
static async Task RequireThrowsAsync<T>(Func<Task> action, string message) where T : Exception { try { await action(); } catch (T) { return; } throw new InvalidOperationException(message); }
