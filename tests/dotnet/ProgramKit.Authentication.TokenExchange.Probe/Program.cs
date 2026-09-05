using Microsoft.Extensions.Hosting;
using CShells;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication.TokenExchange;

await VerifyExchangeAsync();
VerifyEndpointValidation();

static async Task VerifyExchangeAsync()
{
    var handler = new ExchangeRecordingHandler();
    using var client = new HttpClient(handler);
    var options = new TokenExchangeOptions();
    options.Registrations.Add("downstream", new TokenExchangeRegistration
    {
        TokenEndpoint = "https://identity.example/oauth/token",
        ClientId = "delegating client",
        ClientSecret = "exchange/secret"
    });
    var clock = new DateTimeOffset(2026, 9, 5, 13, 0, 0, TimeSpan.Zero);
    using var services = BuildProvider(options, client, Environments.Production, clock);
    var service = services.GetRequiredService<ITokenExchangeService>();
    var request = new TokenExchangeRequest
    {
        SubjectToken = "subject-token",
        Audience = "orders-api",
        Resource = "https://orders.example/",
        Scopes = ["orders.read"],
        ActorToken = "actor-token",
        ActorTokenType = "urn:ietf:params:oauth:token-type:access_token"
    };
    var result = await service.ExchangeAsync("downstream", request);
    Require(result.AccessToken == "exchanged-access", "the exchanged access token was not projected");
    Require(
        result.IssuedTokenType == "urn:ietf:params:oauth:token-type:access_token",
        "the issued token type changed");
    Require(result.TokenType == "Bearer", "the token authorization scheme changed");
    Require(result.ExpiresAt == clock.AddSeconds(90), "the exchanged token expiry changed");
    Require(result.Scopes.SequenceEqual(["orders.read"]), "the returned downscope changed");

    var invalidActor = new TokenExchangeRequest
    {
        SubjectToken = "subject-token",
        ActorToken = "actor-without-type"
    };
    await RequireThrowsAsync<ArgumentException>(
        () => service.ExchangeAsync("downstream", invalidActor).AsTask(),
        "an untyped actor token must fail before I/O");
    Require(handler.Requests == 1, "invalid actor input unexpectedly reached the token endpoint");

    try
    {
        await service.ExchangeAsync("downstream", new TokenExchangeRequest { SubjectToken = "reject-token" });
        throw new InvalidOperationException("a rejected exchange unexpectedly succeeded");
    }
    catch (HttpRequestException error)
    {
        Require(!error.Message.Contains("provider-secret-body", StringComparison.Ordinal), "provider error body leaked");
    }
}

static void VerifyEndpointValidation()
{
    var local = OptionsFor("http://localhost:8080/token", allowHttp: true);
    RequireOptionsFailure(local, Environments.Production, "production accepted a plaintext exchange endpoint");
    using (var accepted = BuildProvider(
        local,
        new HttpClient(new ExchangeRecordingHandler()),
        Environments.Development,
        DateTimeOffset.UtcNow))
    {
        _ = accepted.GetRequiredService<IOptions<TokenExchangeOptions>>().Value;
    }
    RequireOptionsFailure(
        OptionsFor("http://identity.internal/token", allowHttp: true),
        Environments.Development,
        "development accepted plaintext non-loopback exchange HTTP");
}

static ServiceProvider BuildProvider(
    TokenExchangeOptions configured,
    HttpClient client,
    string environmentName,
    DateTimeOffset now)
{
    var settings = new ShellSettings(new ShellId("probe"), ["ProgramKit.Authentication.TokenExchange"]);
    foreach (var (name, registration) in configured.Registrations)
    {
        var prefix = $"{TokenExchangeOptions.SectionName}:Registrations:{name}";
        settings.ConfigurationData[$"{prefix}:TokenEndpoint"] = registration.TokenEndpoint;
        settings.ConfigurationData[$"{prefix}:ClientId"] = registration.ClientId;
        settings.ConfigurationData[$"{prefix}:ClientSecret"] = registration.ClientSecret;
        settings.ConfigurationData[$"{prefix}:ClientAuthenticationMethod"] = registration.ClientAuthenticationMethod;
        settings.ConfigurationData[$"{prefix}:TimeoutSeconds"] = registration.TimeoutSeconds.ToString();
        settings.ConfigurationData[$"{prefix}:AllowHttpForLocalDevelopment"] = registration.AllowHttpForLocalDevelopment.ToString();
    }

    var services = new ServiceCollection();
    services.AddSingleton<IHostEnvironment>(new ExchangeEnvironment(environmentName));
    services.AddSingleton<TimeProvider>(new ExchangeTimeProvider(now));
    new ProgramKitTokenExchangeFeature(settings).ConfigureServices(services);
    services.RemoveAll<IHttpClientFactory>();
    services.AddSingleton<IHttpClientFactory>(new ExchangeHttpClientFactory(client));
    return services.BuildServiceProvider();
}

static void RequireOptionsFailure(TokenExchangeOptions options, string environment, string message)
{
    using var services = BuildProvider(
        options,
        new HttpClient(new ExchangeRecordingHandler()),
        environment,
        DateTimeOffset.UtcNow);
    try
    {
        _ = services.GetRequiredService<IOptions<TokenExchangeOptions>>().Value;
    }
    catch (OptionsValidationException)
    {
        return;
    }
    throw new InvalidOperationException(message);
}

static TokenExchangeOptions OptionsFor(string endpoint, bool allowHttp)
{
    var options = new TokenExchangeOptions();
    options.Registrations.Add("exchange", new TokenExchangeRegistration
    {
        TokenEndpoint = endpoint,
        ClientId = "exchange-client",
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
