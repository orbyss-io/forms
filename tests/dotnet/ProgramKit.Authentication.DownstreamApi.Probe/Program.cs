using System.Net.Http.Headers;
using CShells;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication.ClientCredentials;
using ProgramKit.Authentication.DownstreamApi;
using ProgramKit.Authentication.TokenExchange;

await VerifyDownstreamModesAsync();
VerifyRegistrationValidation();

static async Task VerifyDownstreamModesAsync()
{
    var options = new DownstreamApiOptions();
    options.Registrations.Add("machine-api", new DownstreamApiRegistration
    {
        BaseAddress = "https://api.example/root/",
        AccessMode = "ClientCredentials",
        TokenRegistration = "machine"
    });
    options.Registrations.Add("delegated-api", new DownstreamApiRegistration
    {
        BaseAddress = "https://delegated.example/v1/",
        AccessMode = "TokenExchange",
        TokenRegistration = "delegation",
        Audience = "delegated-api",
        Resource = "https://delegated.example/",
        Scopes = ["records.read"]
    });
    var machine = new DownstreamMachineTokenProvider();
    var exchange = new DownstreamTokenExchangeService();
    var handler = new DownstreamRecordingHandler();
    using var httpClient = new HttpClient(handler);
    using var services = BuildProvider(
        options,
        httpClient,
        Environments.Production,
        machine,
        exchange);
    var client = services.GetRequiredService<IDownstreamApiClient>();

    using (var request = new HttpRequestMessage(HttpMethod.Get, "orders/42"))
    using (var response = await client.SendAsync("machine-api", request))
    {
        Require(response.IsSuccessStatusCode, "machine downstream call failed");
    }
    Require(machine.Registration == "machine", "machine API selected the wrong token registration");
    Require(
        handler.Requests[0] == ("https://api.example/root/orders/42", "Bearer", "machine-access"),
        "machine API routing or authorization changed");

    using (var request = new HttpRequestMessage(HttpMethod.Post, "records/search"))
    using (var response = await client.SendAsync("delegated-api", request))
    {
        Require(response.IsSuccessStatusCode, "delegated downstream call failed");
    }
    Require(exchange.Registration == "delegation", "delegated API selected the wrong exchange policy");
    Require(exchange.Request?.SubjectToken == "validated-user-token", "validated user token was not exchanged");
    Require(exchange.Request?.Audience == "delegated-api", "delegation audience changed");
    Require(exchange.Request?.Resource == "https://delegated.example/", "delegation resource changed");
    Require(exchange.Request?.Scopes.SequenceEqual(["records.read"]) is true, "delegation downscope changed");
    Require(
        handler.Requests[1] == ("https://delegated.example/v1/records/search", "Bearer", "delegated-access"),
        "delegated API routing or authorization changed");

    using var absolute = new HttpRequestMessage(HttpMethod.Get, "https://attacker.example/");
    await RequireThrowsAsync<ArgumentException>(
        () => client.SendAsync("machine-api", absolute).AsTask(),
        "caller-selected absolute downstream destinations must fail");
    using var authorized = new HttpRequestMessage(HttpMethod.Get, "orders");
    authorized.Headers.Authorization = new AuthenticationHeaderValue("Bearer", "caller-token");
    await RequireThrowsAsync<ArgumentException>(
        () => client.SendAsync("machine-api", authorized).AsTask(),
        "caller-owned downstream authorization must fail");
    Require(handler.Requests.Count == 2, "invalid downstream requests unexpectedly reached the network");
}

static void VerifyRegistrationValidation()
{
    var local = OptionsFor("http://localhost:9000/", allowHttp: true);
    RequireOptionsFailure(local, Environments.Production, "production accepted a plaintext downstream API");
    using (var accepted = BuildProvider(
        local,
        new HttpClient(new DownstreamRecordingHandler()),
        Environments.Development))
    {
        _ = accepted.GetRequiredService<IOptions<DownstreamApiOptions>>().Value;
    }

    var broadExchange = OptionsFor("https://api.example/", allowHttp: false);
    broadExchange.Registrations["api"].AccessMode = "TokenExchange";
    RequireOptionsFailure(
        broadExchange,
        Environments.Production,
        "token exchange without audience or resource downscoping was accepted");
}

static ServiceProvider BuildProvider(
    DownstreamApiOptions configured,
    HttpClient client,
    string environmentName,
    IClientCredentialsTokenProvider? machine = null,
    ITokenExchangeService? exchange = null)
{
    var settings = new ShellSettings(new ShellId("probe"), ["ProgramKit.Authentication.DownstreamApi"]);
    foreach (var (name, registration) in configured.Registrations)
    {
        var prefix = $"{DownstreamApiOptions.SectionName}:Registrations:{name}";
        settings.ConfigurationData[$"{prefix}:BaseAddress"] = registration.BaseAddress;
        settings.ConfigurationData[$"{prefix}:AccessMode"] = registration.AccessMode;
        settings.ConfigurationData[$"{prefix}:TokenRegistration"] = registration.TokenRegistration;
        settings.ConfigurationData[$"{prefix}:AllowHttpForLocalDevelopment"] = registration.AllowHttpForLocalDevelopment.ToString();
        if (registration.Audience is not null)
        {
            settings.ConfigurationData[$"{prefix}:Audience"] = registration.Audience;
        }
        if (registration.Resource is not null)
        {
            settings.ConfigurationData[$"{prefix}:Resource"] = registration.Resource;
        }
        for (var index = 0; index < registration.Scopes.Length; index++)
        {
            settings.ConfigurationData[$"{prefix}:Scopes:{index}"] = registration.Scopes[index];
        }
    }

    var services = new ServiceCollection();
    services.AddSingleton<IHostEnvironment>(new DownstreamEnvironment(environmentName));
    services.AddSingleton<ICurrentAccessTokenAccessor>(new DownstreamAccessTokenAccessor("validated-user-token"));
    if (machine is not null)
    {
        services.AddSingleton<IClientCredentialsTokenProvider>(machine);
    }
    if (exchange is not null)
    {
        services.AddSingleton<ITokenExchangeService>(exchange);
    }
    new ProgramKitDownstreamApiFeature(settings).ConfigureServices(services);
    services.RemoveAll<IHttpClientFactory>();
    services.AddSingleton<IHttpClientFactory>(new DownstreamHttpClientFactory(client));
    return services.BuildServiceProvider();
}

static void RequireOptionsFailure(DownstreamApiOptions options, string environment, string message)
{
    using var services = BuildProvider(
        options,
        new HttpClient(new DownstreamRecordingHandler()),
        environment);
    try
    {
        _ = services.GetRequiredService<IOptions<DownstreamApiOptions>>().Value;
    }
    catch (OptionsValidationException)
    {
        return;
    }
    throw new InvalidOperationException(message);
}

static DownstreamApiOptions OptionsFor(string endpoint, bool allowHttp)
{
    var options = new DownstreamApiOptions();
    options.Registrations.Add("api", new DownstreamApiRegistration
    {
        BaseAddress = endpoint,
        TokenRegistration = "machine",
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
