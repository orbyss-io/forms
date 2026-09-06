using System.Net;
using System.Text.Json.Nodes;
using CShells;
using ProgramKit.Web.Discovery;

if (args.Length != 1)
{
    throw new ArgumentException("Supply the generated disposable fixture root.");
}

var fixtureRoot = Path.GetFullPath(args[0]);
var output = "web/generated/program-kit";
var catalog = new FilePublicDocumentCatalog(fixtureRoot, output);
var documents = catalog.ReadDocuments();
Require(documents.Any(d => d.Route == "/sitemap.xml"), "missing sitemap");
Require(documents.All(d => d.Route != "/account"), "private route was published");
var manifestPath = Path.Combine(fixtureRoot, output, "publication.json");
var original = File.ReadAllText(manifestPath);
foreach (var mutation in new Action<JsonObject>[]
{
    resource => resource["file"] = "public/../../../secret.txt",
    resource => resource["file"] = "integration/tokens.json",
    resource => resource["visibility"] = "private",
    resource => resource["sha256"] = new string('0', 64),
    resource => resource["route"] = "/{**all}",
    resource => resource["contentType"] = "text/html\r\nX-Evil: injected",
})
{
    try
    {
        var document = JsonNode.Parse(original)!.AsObject();
        mutation(document["resources"]![0]!.AsObject());
        File.WriteAllText(manifestPath, document.ToJsonString());
        try
        {
            catalog.ReadDocuments();
            throw new InvalidOperationException("malicious manifest accepted");
        }
        catch (InvalidDataException)
        {
        }
    }
    finally
    {
        File.WriteAllText(manifestPath, original);
    }
}

var builder = WebApplication.CreateBuilder(new WebApplicationOptions { ContentRootPath = fixtureRoot });
var settings = new ShellSettings(new ShellId("public"), ["ProgramKit.Web.Discovery"]);
var feature = new ProgramKitDiscoveryFeature(settings);
feature.ConfigureServices(builder.Services);
await using var app = builder.Build();
app.Urls.Add("http://127.0.0.1:0");
feature.MapEndpoints(app, app.Environment);
await app.StartAsync();
try
{
    using var client = new HttpClient { BaseAddress = new Uri(app.Urls.Single()) };
    foreach (var document in documents)
    {
        using var response = await client.GetAsync(document.Route);
        Require(response.StatusCode == HttpStatusCode.OK, "public GET failed");
        Require((await response.Content.ReadAsByteArrayAsync()).SequenceEqual(document.Content.ToArray()), "body changed");
        Require(response.Content.Headers.ContentType!.ToString() == document.ContentType, "content type changed");
        Require(response.Headers.GetValues("X-Content-Type-Options").Single() == "nosniff", "missing nosniff");
        Require(response.Headers.Contains("X-Robots-Tag") == !document.Index, "indexing policy changed");
        using var request = new HttpRequestMessage(HttpMethod.Head, document.Route);
        using var head = await client.SendAsync(request);
        Require(head.StatusCode == HttpStatusCode.OK && (await head.Content.ReadAsByteArrayAsync()).Length == 0, "HEAD failed");
    }

    foreach (var path in new[] { "/account", "/publication.json", "/integration/tokens.json", "/acceptance/gallery.html", "/.program-kit/ui/content.json" })
    {
        using var response = await client.GetAsync(path);
        Require(response.StatusCode == HttpStatusCode.NotFound, "nonpublic artifact exposed");
    }

    using var post = await client.PostAsync("/", new StringContent(""));
    Require(post.StatusCode == HttpStatusCode.MethodNotAllowed, "unexpected write endpoint");
}
finally
{
    await app.StopAsync();
}

// An existing provider-neutral adapter remains authoritative when the feature configures defaults.
var customBuilder = WebApplication.CreateBuilder();
customBuilder.Services.AddSingleton<IPublicDocumentCatalog, CustomDocumentCatalog>();
feature.ConfigureServices(customBuilder.Services);
await using var customApp = customBuilder.Build();
Require(customApp.Services.GetRequiredService<IPublicDocumentCatalog>() is CustomDocumentCatalog, "consumer adapter was replaced");
Console.WriteLine($"Discovery public-contract probe passed: {documents.Count} GET/HEAD routes, manifest attacks, private 404s, and adapter override.");

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
