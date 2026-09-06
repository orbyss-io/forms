using System.Net;
using System.Net.Http.Json;
using System.Security.Claims;
using CShells;
using Microsoft.AspNetCore.Authentication;
using ModelContextProtocol.Client;
using ProgramKit.Forms;
using ProgramKit.Forms.Management.Mcp.AspNetCore;
using ProgramKit.Forms.Web.Management;
using ProgramKit.Forms.Web.Runtime;
using ProgramKit.Localization;
using ProgramKit.Localization.Formats;
using ProgramKit.Localization.Mcp.AspNetCore;
using ProgramKit.Mcp.AspNetCore;

var root = Path.Combine(Path.GetTempPath(), "program-kit-form-management-" + Guid.NewGuid().ToString("N"));
Directory.CreateDirectory(root);
try
{
    var definitionStore = new FileSystemFormDefinitionStore(new FileSystemFormDefinitionStoreOptions(Path.Combine(root, "definitions"), MaximumForms: 100));
    var releaseStore = new FileSystemFormReleaseStore(new FileSystemFormReleaseStoreOptions(Path.Combine(root, "releases")));
    var validator = new FormDefinitionValidator();
    var compiler = new JsonFormsCompiler(validator);
    var forms = new DefaultFormCatalogService(definitionStore, releaseStore, releaseStore, validator, compiler);
    var actor = new FormAuditActor("author-1", "user", "Form Author");
    var definition = FixtureDefinition();
    var created = await forms.CreateAsync(definition, Mutation("create", null, actor, 1));
    Require(created.Value.State == FormLifecycleState.Draft, "form create failed");
    var replayService = new DefaultFormCatalogService(new FileSystemFormDefinitionStore(new FileSystemFormDefinitionStoreOptions(Path.Combine(root, "definitions"), MaximumForms: 100)), releaseStore, releaseStore, validator, compiler);
    var createReplay = await replayService.CreateAsync(definition, Mutation("create", null, actor, 1));
    Require(createReplay.WasReplay && createReplay.Version == created.Version, "durable form create replay failed");
    var compiled = await replayService.CompileAsync(definition.Id, definition.Revision);
    var compiledAgain = await replayService.CompileAsync(definition.Id, definition.Revision);
    Require(compiled.CandidateSha256 == compiledAgain.CandidateSha256, "stored-revision compilation was not deterministic");
    var review = await replayService.SubmitForReviewAsync(definition.Id, definition.Revision, ["browser:chromium", "contract:ajv"], Mutation("review", created.Version.Value, actor, 2));
    Require(review.Value == FormLifecycleState.InReview, "form review transition failed");
    var reviewReplay = await replayService.SubmitForReviewAsync(definition.Id, definition.Revision, ["browser:chromium", "contract:ajv"], Mutation("review", created.Version.Value, actor, 2));
    Require(reviewReplay.WasReplay && reviewReplay.Version == review.Version, "durable review replay failed");
    var approval = await replayService.ApproveAsync(definition.Id, definition.Revision, Mutation("approve", review.Version.Value, new FormAuditActor("reviewer-1", "user"), 3));
    var published = await replayService.PublishAsync(definition.Id, definition.Revision, Mutation("publish", approval.Version.Value, new FormAuditActor("publisher-1", "user"), 4));
    Require(published.Value.Evidence.Count == 2 && !published.Value.Retired, "immutable publication lost evidence");
    var publishReplayService = new DefaultFormCatalogService(new FileSystemFormDefinitionStore(new FileSystemFormDefinitionStoreOptions(Path.Combine(root, "definitions"), MaximumForms: 100)), new FileSystemFormReleaseStore(new FileSystemFormReleaseStoreOptions(Path.Combine(root, "releases"))), new FileSystemFormReleaseStore(new FileSystemFormReleaseStoreOptions(Path.Combine(root, "releases"))), validator, compiler);
    var publishReplay = await publishReplayService.PublishAsync(definition.Id, definition.Revision, Mutation("publish", approval.Version.Value, new FormAuditActor("publisher-1", "user"), 4));
    Require(publishReplay.WasReplay && publishReplay.Value.Candidate.CandidateSha256 == published.Value.Candidate.CandidateSha256, "durable publish replay failed");

    await RequireThrowsAsync<InvalidOperationException>(() => replayService.ReplaceAsync(definition with { Revision = new FormRevision(2) }, Mutation("stale", created.Version.Value, actor, 5)).AsTask(), "stale form replacement was accepted");

    var localizationValidator = new LocalizationCatalogValidator();
    var importAdapter = new JsonLocalizationImportAdapter();
    var localizationReleaseStore = new FileSystemLocalizationReleaseStore(new FileSystemLocalizationReleaseStoreOptions(Path.Combine(root, "localization-releases")));
    var localization = new DefaultLocalizationCatalogService(
        new FileSystemLocalizationCatalogStore(new FileSystemLocalizationCatalogStoreOptions(Path.Combine(root, "localization-catalogs"))),
        localizationReleaseStore,
        localizationReleaseStore,
        localizationValidator,
        new LocalizationImportCoordinator([importAdapter], localizationValidator));
    var localizationRelease = FixtureLocalizationRelease();

    var builder = WebApplication.CreateBuilder();
    builder.Logging.ClearProviders();
    builder.Services.AddAuthentication("probe").AddScheme<AuthenticationSchemeOptions, TestAuthenticationHandler>("probe", _ => { });
    builder.Services.AddAuthorization();
    builder.Services.AddSingleton<IFormAuthoring>(replayService);
    builder.Services.AddSingleton<IFormCatalogQueries>(replayService);
    builder.Services.AddSingleton<IFormReleaseLifecycle>(replayService);
    builder.Services.AddSingleton<IFormCompatibilityAnalyzer, DefaultFormCompatibilityAnalyzer>();
    builder.Services.AddSingleton<ILocalizationCatalogManagement>(localization);
    builder.Services.AddSingleton<ILocalizationCatalogQueries>(localization);
    builder.Services.AddSingleton<ILocalizationReleaseLifecycle>(localization);
    builder.Services.AddSingleton<ILocalizationReleaseDiffer, DefaultLocalizationReleaseDiffer>();
    builder.Services.AddSingleton<ILocalizationImportFormatAdapter>(importAdapter);
    builder.Services.AddSingleton<ILocalizationExportFormatAdapter, JsonLocalizationExportAdapter>();
    builder.Services.AddSingleton<ILocalizationRuntime>(new InMemoryLocalizationRuntime(localizationRelease));
    var settings = new ShellSettings(new ShellId("management"), ["ProgramKit.Forms.Web.Management", "ProgramKit.Forms.Web.Runtime", "ProgramKit.Mcp.AspNetCore", "ProgramKit.Forms.Management.Mcp.AspNetCore", "ProgramKit.Localization.Mcp.AspNetCore"]);
    var formWeb = new ProgramKitFormManagementFeature(settings);
    var formRuntime = new ProgramKitFormRuntimeFeature(settings);
    var mcp = new ProgramKitMcpFeature(settings);
    var formTools = new ProgramKitFormManagementMcpFeature(settings);
    var localizationTools = new ProgramKitLocalizationMcpFeature(settings);
    formWeb.ConfigureServices(builder.Services);
    formRuntime.ConfigureServices(builder.Services);
    mcp.ConfigureServices(builder.Services);
    formTools.ConfigureServices(builder.Services);
    localizationTools.ConfigureServices(builder.Services);

    await using var app = builder.Build();
    app.Urls.Add("http://127.0.0.1:0");
    app.UseAuthentication();
    app.UseAuthorization();
    formWeb.MapEndpoints(app, app.Environment);
    formRuntime.MapEndpoints(app, app.Environment);
    mcp.MapEndpoints(app, app.Environment);
    await app.StartAsync();
    try
    {
        using var client = new HttpClient { BaseAddress = new Uri(app.Urls.Single()) };
        using var anonymousManagement = await client.GetAsync("/_program-kit/forms/forms");
        Require(anonymousManagement.StatusCode == HttpStatusCode.Unauthorized, "form management allowed anonymous access");
        using var anonymousMcp = await client.PostAsync("/program-kit/mcp", new StringContent("{}", System.Text.Encoding.UTF8, "application/json"));
        Require(anonymousMcp.StatusCode == HttpStatusCode.Unauthorized, "shared MCP allowed anonymous access");
        using var runtime = await client.GetAsync("/_program-kit/forms/runtime/forms/registration/current");
        Require(runtime.StatusCode == HttpStatusCode.OK && runtime.Headers.ETag?.Tag.Length == 66, "anonymous immutable form runtime failed");
        var etag = runtime.Headers.ETag ?? throw new InvalidOperationException("form runtime omitted ETag");
        using var conditional = new HttpRequestMessage(HttpMethod.Get, "/_program-kit/forms/runtime/forms/registration/current");
        conditional.Headers.IfNoneMatch.Add(etag);
        using var cached = await client.SendAsync(conditional);
        Require(cached.StatusCode == HttpStatusCode.NotModified, "form runtime conditional request did not return 304");

        client.DefaultRequestHeaders.Add("X-Test-Auth", "true");
        using var managed = await client.GetAsync("/_program-kit/forms/forms/registration");
        Require(managed.StatusCode == HttpStatusCode.OK && (await managed.Content.ReadFromJsonAsync<FormDefinitionDocument>())?.Version == published.Version, "authenticated form management query failed");

        var transport = new HttpClientTransport(new HttpClientTransportOptions
        {
            Name = "Program Kit management probe",
            Endpoint = new Uri(new Uri(app.Urls.Single()), "/program-kit/mcp"),
            TransportMode = HttpTransportMode.StreamableHttp,
            EnableStandaloneGetStream = false,
            AdditionalHeaders = new Dictionary<string, string> { ["X-Test-Auth"] = "true" }
        });
        await using var mcpClient = await McpClient.CreateAsync(transport);
        var tools = await mcpClient.ListToolsAsync();
        Require(tools.Count == 28 && tools.Any(tool => tool.Name == "forms.management.get") && tools.Any(tool => tool.Name == "localization.catalogs.get"), "shared MCP did not compose both bounded-context tool catalogs");
        var formCall = await mcpClient.CallToolAsync("forms.management.get", new Dictionary<string, object?> { ["formId"] = "registration" });
        Require(formCall.IsError != true, "authenticated Forms management MCP call failed");
        var localizationCall = await mcpClient.CallToolAsync("localization.catalogs.list", new Dictionary<string, object?> { ["search"] = null, ["first"] = 0, ["maximum"] = 10 });
        Require(localizationCall.IsError != true, "authenticated Localization MCP call failed");
    }
    finally { await app.StopAsync(); }

    var retired = await replayService.RetireAsync(published.Value.Id, Mutation("retire", published.Value.Candidate.CandidateSha256, new FormAuditActor("publisher-1", "user"), 6));
    Require(retired.Value.Retired, "form retirement failed");
    var retiredReplay = await replayService.RetireAsync(published.Value.Id, Mutation("retire", published.Value.Candidate.CandidateSha256, new FormAuditActor("publisher-1", "user"), 6));
    Require(retiredReplay.WasReplay, "form retirement replay failed");
    Require(await replayService.GetCurrentReleaseAsync(definition.Id) is null, "retired form remained current");

    var definitionFile = Directory.EnumerateFiles(Path.Combine(root, "definitions"), "*.form-definition.json").Single();
    await File.AppendAllTextAsync(definitionFile, "tampered");
    await RequireThrowsAsync<System.Text.Json.JsonException>(() => new FileSystemFormDefinitionStore(new FileSystemFormDefinitionStoreOptions(Path.Combine(root, "definitions"))).GetAsync(definition.Id).AsTask(), "tampered form aggregate was accepted", allowInvalidData: true);
}
finally
{
    if (Directory.Exists(root)) Directory.Delete(root, recursive: true);
}

Console.WriteLine("Program Kit form management and shared MCP probe passed.");

static FormDefinition FixtureDefinition()
{
    var field = new FormFieldDefinition("email", "/email", FormValueKind.String, true, new LocalizedTextReference("fields.email", "Email"), Constraints: new FormConstraints(MinimumLength: 3, MaximumLength: 320));
    var layout = new FormElementDefinition("root", FormElementKind.VerticalLayout, [new FormElementDefinition("email-control", FormElementKind.Control, [], FieldId: "email")]);
    return new FormDefinition(new FormId("registration"), new FormRevision(1), "Registration", "en", FormLifecycleState.Draft, [field], layout, []);
}

static LocalizationRelease FixtureLocalizationRelease()
{
    var scope = new LocalizationScope(LocalizationScopeKind.Application);
    var actor = new LocalizationAuditActor("publisher", "service");
    return new LocalizationRelease(new LocalizationReleaseId("fixture-v1"), new LocalizationCatalogId("fixture"), new LocalizationRevision(1), "en", [new LocaleDefinition("en", TextDirection.LeftToRight, RequiredForPublication: true)], [new LocalizationReleaseEntry("hello", scope, "en", TextDirection.LeftToRight, "Hello", [])], new string('a', 64), DateTimeOffset.UnixEpoch, actor);
}

static FormMutationContext Mutation(string key, string? version, FormAuditActor actor, int minute) => new(key, version is null ? null : new FormConcurrencyToken(version), actor, DateTimeOffset.UnixEpoch.AddMinutes(minute));
static void Require(bool condition, string message) { if (!condition) throw new InvalidOperationException(message); }
static async Task RequireThrowsAsync<T>(Func<Task> action, string message, bool allowInvalidData = false) where T : Exception
{
    try { await action(); }
    catch (T) { return; }
    catch (InvalidDataException) when (allowInvalidData) { return; }
    throw new InvalidOperationException(message);
}
