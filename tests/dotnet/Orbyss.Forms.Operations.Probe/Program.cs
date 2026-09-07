using System.Security.Claims;
using System.Text;
using CShells;
using Microsoft.AspNetCore.Authentication;
using ModelContextProtocol.Client;
using ModelContextProtocol.Server;
using Orbyss.Forms;
using Orbyss.Forms.Mcp.AspNetCore;
using Orbyss.Forms.Tool;
using Orbyss.Forms.Web.Submissions;
using Orbyss.Foundation.Mcp.AspNetCore;

var root = Path.Combine(Path.GetTempPath(), "orbyss-forms-form-operations-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
try
{
    var releaseStore = new FileSystemFormReleaseStore(new FileSystemFormReleaseStoreOptions(Path.Combine(root, "releases")));
    var release = FixtureRelease();
    await releaseStore.WriteAsync(release);
    var compatibleRelease = FixtureRelease(2);
    var breakingRelease = FixtureRelease(3, includeCountry: true);
    await releaseStore.WriteAsync(compatibleRelease);
    await releaseStore.WriteAsync(breakingRelease);
    var storageOptions = new FileSystemFormOperationalStoreOptions(Path.Combine(root, "operations"), MaximumDocuments: 100);
    var responseStore = new FileSystemFormSubmissionStore(storageOptions);
    var metadataStore = new FileSystemFormAttachmentStore(storageOptions);
    var contentStore = new FileSystemFormAttachmentContentStore(storageOptions);
    var policy = new DefaultFormAttachmentPolicy(new FormAttachmentPolicyOptions(1024 * 1024, [new AllowedFormAttachmentType("application/pdf", [".pdf"], [Encoding.ASCII.GetBytes("%PDF")])]));
    var validator = new DefaultFormDataValidator();
    var service = new DefaultFormSubmissionService(responseStore, metadataStore, releaseStore, validator, compatibilityAnalyzer: new DefaultFormCompatibilityAnalyzer(), migrations: [new CountryDraftMigration()]);
    var attachmentService = new DefaultFormAttachmentService(metadataStore, contentStore, responseStore, policy, new CleanAttachmentScanner());
    var actor = new FormAuditActor("user-1", "user", "Fixture User");
    var other = new FormAuditActor("user-2", "user");

    var createMutation = Create("draft-create", actor);
    var created = await service.CreateAsync(new FormDraftId("draft-1"), release.Id, "{}", createMutation);
    Require(created.Value.State == FormDraftState.Active && created.Value.Data.Json == "{}", "draft create failed");

    var migrationDraft = await service.CreateAsync(new FormDraftId("draft-migration"), release.Id, "{\"email\":\"migration@example.com\"}", Create("migration-create", actor));
    var compatibleMigration = await service.MigrateAsync(migrationDraft.Value.Id, compatibleRelease.Id, null, Update("migration-compatible", migrationDraft.Version.Value, actor));
    Require(compatibleMigration.Value.ReleaseId == compatibleRelease.Id, "compatible draft migration failed");
    await RequireThrowsAsync<InvalidOperationException>(() => service.MigrateAsync(compatibleMigration.Value.Id, breakingRelease.Id, null, Update("migration-breaking-missing", compatibleMigration.Version.Value, actor)).AsTask(), "breaking migration did not require a trusted handler");
    var breakingMigration = await service.MigrateAsync(compatibleMigration.Value.Id, breakingRelease.Id, "probe.add-country", Update("migration-breaking", compatibleMigration.Version.Value, actor));
    Require(breakingMigration.Value.ReleaseId == breakingRelease.Id && breakingMigration.Value.Data.Json.Contains("\"country\":\"NL\"", StringComparison.Ordinal), "trusted breaking draft migration failed");
    var migrationReplay = await service.MigrateAsync(compatibleMigration.Value.Id, breakingRelease.Id, "probe.add-country", Update("migration-breaking", compatibleMigration.Version.Value, actor));
    Require(migrationReplay.WasReplay && migrationReplay.Version == breakingMigration.Version, "draft migration replay failed");

    var restarted = new DefaultFormSubmissionService(new FileSystemFormSubmissionStore(storageOptions), new FileSystemFormAttachmentStore(storageOptions), releaseStore, validator);
    var createReplay = await restarted.CreateAsync(new FormDraftId("draft-1"), release.Id, "{}", createMutation);
    Require(createReplay.WasReplay && createReplay.Version == created.Version, "durable draft create replay failed");
    await RequireThrowsAsync<UnauthorizedAccessException>(() => restarted.GetAsync(new FormDraftId("draft-1"), new FormRequestContext(other)).AsTask(), "cross-owner draft read was allowed");

    var staleSave = Update("draft-save-stale", "not-the-version", actor);
    await RequireThrowsAsync<InvalidOperationException>(() => restarted.SaveAsync(new FormDraftId("draft-1"), "{\"email\":\"person@example.com\"}", staleSave).AsTask(), "stale draft update was allowed");
    var saved = await restarted.SaveAsync(new FormDraftId("draft-1"), "{ \"email\": \"person@example.com\" }", Update("draft-save", created.Version.Value, actor));
    Require(saved.Value.Data.Json == "{\"email\":\"person@example.com\"}", "canonical form data changed");

    await using var pdf = new MemoryStream(Encoding.ASCII.GetBytes("%PDF-1.7 fixture"));
    var attached = await attachmentService.UploadAsync(new FormAttachmentId("attachment-1"), new FormDraftId("draft-1"), "evidence.pdf", "application/pdf", pdf, Create("attachment-upload", actor));
    Require(attached.Value.State == FormAttachmentState.Available && attached.Value.Length == 16, "clean attachment was not promoted");
    await using (var opened = await attachmentService.OpenReadAsync(attached.Value.Id, new FormRequestContext(actor)))
    using (var reader = new StreamReader(opened, Encoding.ASCII))
    {
        Require(await reader.ReadToEndAsync() == "%PDF-1.7 fixture", "promoted attachment bytes changed");
    }
    await RequireThrowsAsync<UnauthorizedAccessException>(() => attachmentService.OpenReadAsync(attached.Value.Id, new FormRequestContext(other)).AsTask(), "cross-owner attachment read was allowed");

    await using var executable = new MemoryStream(Encoding.ASCII.GetBytes("MZ-not-a-pdf"));
    var rejected = await attachmentService.UploadAsync(new FormAttachmentId("attachment-2"), new FormDraftId("draft-1"), "malware.pdf", "application/pdf", executable, Create("attachment-reject", actor));
    Require(rejected.Value.State == FormAttachmentState.Rejected && rejected.Value.RejectionCode == "content-signature-mismatch", "signature mismatch was not durably rejected");

    var submitted = await restarted.SubmitAsync(new FormDraftId("draft-1"), [attached.Value.Id], Update("draft-submit", saved.Version.Value, actor));
    Require(submitted.Value.State == FormSubmissionState.Submitted && submitted.Value.AttachmentIds.SequenceEqual([attached.Value.Id]), "submission did not snapshot the clean attachment");
    var submittedDraft = await restarted.GetAsync(new FormDraftId("draft-1"), new FormRequestContext(actor));
    Require(submittedDraft?.Draft.State == FormDraftState.Submitted, "submitted draft remained editable");
    await RequireThrowsAsync<InvalidOperationException>(() => restarted.SaveAsync(new FormDraftId("draft-1"), saved.Value.Data.Json, Update("save-after-submit", submittedDraft!.Version.Value, actor)).AsTask(), "submitted draft remained writable");

    var restartAgain = new DefaultFormSubmissionService(new FileSystemFormSubmissionStore(storageOptions), new FileSystemFormAttachmentStore(storageOptions), releaseStore, validator);
    var submitReplay = await restartAgain.SubmitAsync(new FormDraftId("draft-1"), [attached.Value.Id], Update("draft-submit", saved.Version.Value, actor));
    Require(submitReplay.WasReplay && submitReplay.Value.Id == submitted.Value.Id, "durable submit replay failed");
    var withdrawn = await restartAgain.WithdrawAsync(submitted.Value.Id, Update("withdraw", submitted.Version.Value, actor));
    Require(withdrawn.Value.State == FormSubmissionState.Withdrawn, "submission withdrawal failed");

    var empty = await restartAgain.CreateAsync(new FormDraftId("draft-2"), release.Id, "{}", Create("draft-2-create", actor));
    await RequireThrowsAsync<FormDataValidationException>(() => restartAgain.SubmitAsync(new FormDraftId("draft-2"), [], Update("draft-2-submit", empty.Version.Value, actor)).AsTask(), "missing required submission data was accepted");
    var valid = await restartAgain.SaveAsync(new FormDraftId("draft-2"), "{\"email\":\"valid@example.com\"}", Update("draft-2-save", empty.Version.Value, actor));
    var pendingDecision = await restartAgain.SubmitAsync(new FormDraftId("draft-2"), [], Update("draft-2-submit-valid", valid.Version.Value, actor));
    var accepted = await ((IFormSubmissionReview)restartAgain).DecideAsync(pendingDecision.Value.Id, true, "contract accepted", Update("draft-2-accept", pendingDecision.Version.Value, new FormAuditActor("reviewer-1", "service")));
    Require(accepted.Value.State == FormSubmissionState.Accepted && accepted.Value.DecisionReason == "contract accepted", "separate review lifecycle failed");

    var principal = new ClaimsPrincipal(new ClaimsIdentity([new Claim("sub", actor.Id), new Claim("name", actor.DisplayName!)], "probe"));
    var toolDraft = await FormOperationsTools.GetDraftAsync("draft-1", principal, new ClaimsFormToolActorProvider(), restartAgain, CancellationToken.None);
    Require(toolDraft?.Draft.OwnerId == actor.Id, "MCP tool did not derive owner from transport claims");
    var toolAttributes = typeof(FormOperationsTools).GetMethods().Select(method => method.GetCustomAttributes(typeof(McpServerToolAttribute), false).Cast<McpServerToolAttribute>().SingleOrDefault()).Where(attribute => attribute is not null).ToArray();
    Require(toolAttributes.Length == 11 && toolAttributes.Select(attribute => attribute!.Name).Distinct(StringComparer.Ordinal).Count() == toolAttributes.Length, "governed MCP tool catalog changed");
    Require(typeof(FormOperationsTools).GetMethods().SelectMany(method => method.GetParameters()).All(parameter => parameter.ParameterType != typeof(FormAuditActor) && parameter.ParameterType != typeof(FormRequestContext) && parameter.ParameterType != typeof(IFormSubmissionReview)), "MCP schema can receive trusted identity or review authority");

    var builder = WebApplication.CreateBuilder();
    builder.Logging.ClearProviders();
    builder.Services.AddAuthentication("probe").AddScheme<AuthenticationSchemeOptions, TestAuthenticationHandler>("probe", _ => { });
    builder.Services.AddAuthorization();
    builder.Services.AddSingleton<IFormDraftOperations>(restartAgain);
    builder.Services.AddSingleton<IFormDraftMigrationOperations>(restartAgain);
    builder.Services.AddSingleton<IFormSubmissionOperations>(restartAgain);
    builder.Services.AddSingleton<IFormSubmissionReview>(restartAgain);
    builder.Services.AddSingleton<IFormAttachmentOperations>(attachmentService);
    var shellSettings = new ShellSettings(new ShellId("forms-operations"), ["Orbyss.Forms.Web.Submissions", "Orbyss.Foundation.Mcp.AspNetCore", "Orbyss.Forms.Mcp.AspNetCore"]);
    var webFeature = new OrbyssFormSubmissionsFeature(shellSettings);
    var mcpTransport = new FoundationMcpFeature(shellSettings);
    var mcpFeature = new OrbyssFormMcpFeature(shellSettings);
    webFeature.ConfigureServices(builder.Services);
    mcpTransport.ConfigureServices(builder.Services);
    mcpFeature.ConfigureServices(builder.Services);
    await using (var app = builder.Build())
    {
        app.Urls.Add("http://127.0.0.1:0");
        app.UseAuthentication();
        app.UseAuthorization();
        webFeature.MapEndpoints(app, app.Environment);
        mcpTransport.MapEndpoints(app, app.Environment);
        await app.StartAsync();
        try
        {
            using var webClient = new HttpClient { BaseAddress = new Uri(app.Urls.Single()) };
            using var anonymousApi = await webClient.GetAsync("/orbyss-forms/forms/drafts");
            Require(anonymousApi.StatusCode == System.Net.HttpStatusCode.Unauthorized, "form API allowed anonymous access");
            using var anonymousMcp = await webClient.PostAsync("/orbyss-foundation/mcp", new StringContent("{}", Encoding.UTF8, "application/json"));
            Require(anonymousMcp.StatusCode == System.Net.HttpStatusCode.Unauthorized, "form MCP allowed anonymous access");
            webClient.DefaultRequestHeaders.Add("X-Test-Auth", "true");
            using var authenticatedApi = await webClient.GetAsync("/orbyss-forms/forms/drafts");
            Require(authenticatedApi.IsSuccessStatusCode, "form API did not use the selected authentication scheme");

            var transport = new HttpClientTransport(new HttpClientTransportOptions
            {
                Name = "Orbyss Forms operations probe",
                Endpoint = new Uri(new Uri(app.Urls.Single()), "/orbyss-foundation/mcp"),
                TransportMode = HttpTransportMode.StreamableHttp,
                EnableStandaloneGetStream = false,
                AdditionalHeaders = new Dictionary<string, string> { ["X-Test-Auth"] = "true" }
            });
            await using var mcpClient = await McpClient.CreateAsync(transport);
            var listedTools = await mcpClient.ListToolsAsync();
            Require(listedTools.Count == 11 && listedTools.Any(tool => tool.Name == "forms.drafts.get") && listedTools.Any(tool => tool.Name == "forms.drafts.migrate"), "authenticated MCP discovery did not expose the governed tool catalog");
            var call = await mcpClient.CallToolAsync("forms.drafts.get", new Dictionary<string, object?> { ["draftId"] = "draft-1" });
            Require(call.IsError != true, "authenticated MCP tool invocation failed");
        }
        finally
        {
            await app.StopAsync();
        }
    }

    var durableDraft = await new FileSystemFormSubmissionStore(storageOptions).GetByDraftAsync(new FormDraftId("draft-2"));
    Require(durableDraft is { Audit.Count: 4 }, "durable response audit history is incomplete");
    var responseFile = Directory.EnumerateFiles(Path.Combine(storageOptions.DirectoryPath, "responses"), "*.form-response.json").Single(path => File.ReadAllText(path).Contains("draft-2", StringComparison.Ordinal));
    await File.AppendAllTextAsync(responseFile, "tampered");
    await RequireThrowsAsync<System.Text.Json.JsonException>(() => new FileSystemFormSubmissionStore(storageOptions).GetByDraftAsync(new FormDraftId("draft-2")).AsTask(), "tampered response envelope was accepted", allowAnyInvalidData: true);

    Console.WriteLine("Orbyss Forms form operations probe passed.");
}
finally
{
    if (Directory.Exists(root)) Directory.Delete(root, recursive: true);
}

static FormRelease FixtureRelease(int revision = 1, bool includeCountry = false)
{
    var field = new FormFieldDefinition("email", "/email", FormValueKind.String, true, new LocalizedTextReference("fields.email", "Email"), Constraints: new FormConstraints(MinimumLength: 3, MaximumLength: 320));
    FormFieldDefinition[] fields = includeCountry ? [field, new FormFieldDefinition("country", "/country", FormValueKind.String, true, new LocalizedTextReference("fields.country", "Country"))] : [field];
    var candidate = new FormCandidate(new FormId("registration"), new FormRevision(revision), new FormArtifact("application/schema+json", "{}", $"schema-{revision}"), new FormArtifact("application/json", "{}", $"ui-{revision}"), [], [], [], [], DateTimeOffset.Parse("2026-09-06T00:00:00Z"), $"candidate-{revision}", fields);
    return new FormRelease(new FormReleaseId($"registration-r{revision}"), candidate, DateTimeOffset.Parse("2026-09-06T00:00:00Z").AddMinutes(revision), new FormAuditActor("publisher", "service"), ["probe"]);
}

static FormMutationContext Create(string key, FormAuditActor actor) => new(key, null, actor, DateTimeOffset.Parse("2026-09-06T10:00:00Z"), "probe");
static FormMutationContext Update(string key, string version, FormAuditActor actor) => new(key, new FormConcurrencyToken(version), actor, DateTimeOffset.Parse("2026-09-06T10:00:00Z"), "probe");
static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }

static async Task RequireThrowsAsync<T>(Func<Task> action, string message, bool allowAnyInvalidData = false) where T : Exception
{
    try { await action(); }
    catch (T) { return; }
    catch (InvalidDataException) when (allowAnyInvalidData) { return; }
    catch (System.Text.Json.JsonException) when (allowAnyInvalidData) { return; }
    throw new InvalidOperationException(message);
}
