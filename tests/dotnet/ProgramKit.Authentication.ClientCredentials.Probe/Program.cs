using System.Net;
using System.Net.Http.Headers;
using System.Text;
using CShells;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication.ClientCredentials;

await VerifyTokenRequestsAsync();
VerifyEndpointValidation();

static async Task VerifyTokenRequestsAsync()
{
    var handler = new RecordingHandler();
    using var client = new HttpClient(handler);
    var registrations = new ClientCredentialsOptions();
    registrations.Registrations.Add("machine", new ClientCredentialsRegistration
    {
        TokenEndpoint = "https://identity.example/oauth/token",
        ClientId = "machine id",
        ClientSecret = "s/ecret:value",
        Scopes = ["orders.read", "orders.write"]
    });
    registrations.Registrations.Add("post", new ClientCredentialsRegistration
    {
        TokenEndpoint = "https://identity.example/oauth/token",
        ClientId = "post-client",
        ClientSecret = "post-secret",
        ClientAuthenticationMethod = "client_secret_post"
    });
    using var services = BuildProvider(registrations, client, Environments.Production);
    var provider = services.GetRequiredService<IClientCredentialsTokenProvider>();

    var first = await provider.GetTokenAsync("machine");
    var cached = await provider.GetTokenAsync("machine");
    Require(first == cached, "client-credentials tokens must be cached within the safe lifetime");
    Require(handler.BasicRequests == 1, "a cached machine token must not repeat the token request");
    Require(first.Value == "basic-access" && first.TokenType == "Bearer", "the successful token response was not projected");
    Require(
        first.ExpiresAt == new DateTimeOffset(2026, 9, 5, 12, 2, 0, TimeSpan.Zero),
        "expires_in did not produce the expected absolute expiry");

    var post = await provider.GetTokenAsync("post");
    Require(post.Value == "post-access", "client_secret_post did not acquire its token");
    Require(handler.PostRequests == 1, "client_secret_post issued an unexpected number of requests");

    await RequireThrowsAsync<InvalidOperationException>(
        () => provider.GetTokenAsync("missing").AsTask(),
        "an unknown machine registration must fail closed");
}

static void VerifyEndpointValidation()
{
    var local = OptionsFor("http://localhost:8080/token", allowHttp: true);
    RequireOptionsFailure(local, Environments.Production, "production accepted a plaintext token endpoint");
    using (var accepted = BuildProvider(local, new HttpClient(new RecordingHandler()), Environments.Development))
    {
        _ = accepted.GetRequiredService<IClientCredentialsTokenProvider>();
        _ = accepted.GetRequiredService<IOptions<ClientCredentialsOptions>>().Value;
    }
    var remote = OptionsFor("http://identity.internal/token", allowHttp: true);
    RequireOptionsFailure(remote, Environments.Development, "development accepted plaintext non-loopback HTTP");
}

static ServiceProvider BuildProvider(
    ClientCredentialsOptions configured,
    HttpClient client,
    string environmentName)
{
    var settings = new ShellSettings(new ShellId("probe"), ["ProgramKit.Authentication.ClientCredentials"]);
    foreach (var (name, registration) in configured.Registrations)
    {
        var prefix = $"{ClientCredentialsOptions.SectionName}:Registrations:{name}";
        settings.ConfigurationData[$"{prefix}:TokenEndpoint"] = registration.TokenEndpoint;
        settings.ConfigurationData[$"{prefix}:ClientId"] = registration.ClientId;
        settings.ConfigurationData[$"{prefix}:ClientSecret"] = registration.ClientSecret;
        settings.ConfigurationData[$"{prefix}:ClientAuthenticationMethod"] = registration.ClientAuthenticationMethod;
        settings.ConfigurationData[$"{prefix}:RefreshBeforeExpirySeconds"] = registration.RefreshBeforeExpirySeconds.ToString();
        settings.ConfigurationData[$"{prefix}:TimeoutSeconds"] = registration.TimeoutSeconds.ToString();
        settings.ConfigurationData[$"{prefix}:AllowHttpForLocalDevelopment"] = registration.AllowHttpForLocalDevelopment.ToString();
        for (var index = 0; index < registration.Scopes.Length; index++)
        {
            settings.ConfigurationData[$"{prefix}:Scopes:{index}"] = registration.Scopes[index];
        }
    }

    var services = new ServiceCollection();
    services.AddSingleton<IHostEnvironment>(new ProbeEnvironment(environmentName));
    services.AddSingleton<TimeProvider>(
        new ProbeTimeProvider(new DateTimeOffset(2026, 9, 5, 12, 0, 0, TimeSpan.Zero)));
    new ProgramKitClientCredentialsFeature(settings).ConfigureServices(services);
    services.RemoveAll<IHttpClientFactory>();
    services.AddSingleton<IHttpClientFactory>(new ProbeHttpClientFactory(client));
    return services.BuildServiceProvider();
}

static void RequireOptionsFailure(ClientCredentialsOptions options, string environment, string message)
{
    using var services = BuildProvider(options, new HttpClient(new RecordingHandler()), environment);
    try
    {
        _ = services.GetRequiredService<IOptions<ClientCredentialsOptions>>().Value;
    }
    catch (OptionsValidationException)
    {
        return;
    }
    throw new InvalidOperationException(message);
}

static ClientCredentialsOptions OptionsFor(string endpoint, bool allowHttp)
{
    var options = new ClientCredentialsOptions();
    options.Registrations.Add("machine", new ClientCredentialsRegistration
    {
        TokenEndpoint = endpoint,
        ClientId = "machine",
        ClientSecret = "probe-secret",
        AllowHttpForLocalDevelopment = allowHttp
    });
    return options;
}

static async Task RequireThrowsAsync<TException>(Func<Task> operation, string message)
    where TException : Exception
{
    try
    {
        await operation();
    }
    catch (TException)
    {
        return;
    }

    throw new InvalidOperationException(message);
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
