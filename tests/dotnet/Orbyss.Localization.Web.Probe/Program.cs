using System.Net;
using System.Net.Http.Json;
using CShells;
using Microsoft.AspNetCore.Authentication;
using Orbyss.Localization;
using Orbyss.Localization.Formats;
using Orbyss.Localization.Web.Management;
using Orbyss.Localization.Web.Runtime;

var actor = new LocalizationAuditActor("publisher", "user");
var scope = new LocalizationScope(LocalizationScopeKind.Application);
var catalog = new LocalizationCatalogDefinition(
    new LocalizationCatalogId("application"),
    new LocalizationRevision(1),
    "Application",
    "en",
    LocalizationLifecycleState.Approved,
    [new LocaleDefinition("en", TextDirection.LeftToRight, RequiredForPublication: true), new LocaleDefinition("nl", TextDirection.LeftToRight, "en")],
    [new LocalizationMessageDefinition("welcome", scope, "Welcome", [], [new LocalizedValue("nl", "Welkom", LocalizationValueState.Approved)])]);
var release = new LocalizationRelease(
    new LocalizationReleaseId("application-v1"),
    catalog.Id,
    catalog.Revision,
    catalog.SourceLocale,
    catalog.Locales,
    [new LocalizationReleaseEntry("welcome", scope, "en", TextDirection.LeftToRight, "Welcome", []), new LocalizationReleaseEntry("welcome", scope, "nl", TextDirection.LeftToRight, "Welkom", [])],
    new string('b', 64),
    DateTimeOffset.UnixEpoch,
    actor);
var services = new FakeLocalizationServices(catalog, release);
var builder = WebApplication.CreateBuilder();
builder.Logging.ClearProviders();
builder.Services.AddAuthentication("probe").AddScheme<AuthenticationSchemeOptions, TestAuthenticationHandler>("probe", _ => { });
builder.Services.AddAuthorization();
builder.Services.AddSingleton<ILocalizationCatalogManagement>(services);
builder.Services.AddSingleton<ILocalizationCatalogQueries>(services);
builder.Services.AddSingleton<ILocalizationReleaseLifecycle>(services);
builder.Services.AddSingleton<ILocalizationReleaseDiffer, DefaultLocalizationReleaseDiffer>();
builder.Services.AddSingleton<ILocalizationExportFormatAdapter, JsonLocalizationExportAdapter>();
builder.Services.AddSingleton<ILocalizationRuntime>(new InMemoryLocalizationRuntime(release));
var settings = new ShellSettings(new ShellId("localization"), ["Orbyss.Localization.Web.Management", "Orbyss.Localization.Web.Runtime"]);
settings.ConfigurationData[$"{LocalizationManagementWebOptions.SectionName}:MaximumImportBytes"] = "1024";
var managementFeature = new OrbyssLocalizationManagementFeature(settings);
var runtimeFeature = new OrbyssLocalizationRuntimeFeature(settings);
managementFeature.ConfigureServices(builder.Services);
runtimeFeature.ConfigureServices(builder.Services);
await using var app = builder.Build();
app.Urls.Add("http://127.0.0.1:0");
app.UseAuthentication();
app.UseAuthorization();
managementFeature.MapEndpoints(app, app.Environment);
runtimeFeature.MapEndpoints(app, app.Environment);
await app.StartAsync();
try
{
    using var client = new HttpClient { BaseAddress = new Uri(app.Urls.Single()) };
    using var unauthorized = await client.GetAsync("/_orbyss-forms/localization/catalogs");
    Require(unauthorized.StatusCode == HttpStatusCode.Unauthorized, "management endpoint allowed an anonymous request");

    client.DefaultRequestHeaders.Add("X-Test-Auth", "true");
    using var catalogs = await client.GetAsync("/_orbyss-forms/localization/catalogs");
    Require(catalogs.StatusCode == HttpStatusCode.OK, "authenticated catalog query failed");
    using var catalogResponse = await client.GetAsync("/_orbyss-forms/localization/catalogs/application");
    var catalogDocument = await catalogResponse.Content.ReadFromJsonAsync<LocalizationCatalogDocument>();
    Require(catalogResponse.StatusCode == HttpStatusCode.OK && catalogDocument?.Version.Value == "v1", "catalog detail did not expose its mutation version");

    var upload = new LocalizationImportUploadModel(LocalizationImportFormat.Csv, Convert.ToBase64String(System.Text.Encoding.UTF8.GetBytes("key,source,nl\nwelcome,Welcome,Welkom")), LocalizationMergePolicy.PreserveExisting, scope);
    using var preview = await client.PostAsJsonAsync("/_orbyss-forms/localization/catalogs/application/imports/preview", upload);
    Require(preview.StatusCode == HttpStatusCode.OK, "bounded import preview endpoint failed");

    var oversizedUpload = upload with { ContentBase64 = Convert.ToBase64String(new byte[1025]) };
    using var oversized = await client.PostAsJsonAsync("/_orbyss-forms/localization/catalogs/application/imports/preview", oversizedUpload);
    Require(oversized.StatusCode == HttpStatusCode.BadRequest, "decoded localization import limit was not enforced");

    var oversizedBody = upload with { ContentBase64 = Convert.ToBase64String(new byte[70_000]) };
    using var rejectedBody = await client.PostAsJsonAsync("/_orbyss-forms/localization/catalogs/application/imports/preview", oversizedBody);
    Require(rejectedBody.StatusCode == HttpStatusCode.RequestEntityTooLarge, "localization import request-body limit was not enforced before binding");

    var mutation = new LocalizationWebMutation("apply-preview", "v1", DateTimeOffset.UnixEpoch);
    using var apply = await client.PostAsJsonAsync("/_orbyss-forms/localization/catalogs/application/imports/preview/apply", new LocalizationImportApplyModel(mutation));
    Require(apply.StatusCode == HttpStatusCode.OK && services.LastMutation?.Actor.Id == "translator-1", "server claim attribution did not reach import application");

    using var exported = await client.PostAsJsonAsync("/_orbyss-forms/localization/catalogs/application/exports", new LocalizationExportWebRequest(LocalizationImportFormat.Json, scope, ["nl"], SuggestedBaseName: "application"));
    Require(exported.StatusCode == HttpStatusCode.OK && exported.Content.Headers.ContentType?.MediaType == "application/json", "authenticated export endpoint failed");

    client.DefaultRequestHeaders.Remove("X-Test-Auth");
    using var bundle = await client.GetAsync("/_orbyss-forms/localization/runtime/bundles/Application/nl");
    Require(bundle.StatusCode == HttpStatusCode.OK && bundle.Headers.ETag?.Tag.Length == 66, "anonymous immutable bundle endpoint or ETag failed");
    var bundleEtag = bundle.Headers.ETag ?? throw new InvalidOperationException("runtime bundle did not include an ETag");
    using var cachedRequest = new HttpRequestMessage(HttpMethod.Get, "/_orbyss-forms/localization/runtime/bundles/Application/nl");
    cachedRequest.Headers.IfNoneMatch.Add(bundleEtag);
    using var cached = await client.SendAsync(cachedRequest);
    Require(cached.StatusCode == HttpStatusCode.NotModified && cached.Headers.ETag?.Tag == bundleEtag.Tag, "runtime bundle conditional request did not return 304 with its validator");

    using var resolved = await client.GetAsync("/_orbyss-forms/localization/runtime/messages/Application/nl/welcome");
    Require(resolved.StatusCode == HttpStatusCode.OK && (await resolved.Content.ReadFromJsonAsync<LocalizationResolution>())?.Pattern == "Welkom", "runtime message resolution endpoint failed");
}
finally
{
    await app.StopAsync();
}

Console.WriteLine("Localization web probe passed: authenticated management, claim-derived audit, bounded import/export, anonymous immutable runtime, ETag, and 304.");

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}
