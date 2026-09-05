using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.OpenIdConnect;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication;
using ProgramKit.Authentication.BffCookie;

VerifyLocalHttpDevelopmentCookies();
VerifyProductionCookies();

static void VerifyLocalHttpDevelopmentCookies()
{
    using var provider = CreateProvider(Environments.Development, allowHttpForLocalDevelopment: true);
    var oidc = ConfigureOptions<OpenIdConnectOptions>(provider, OpenIdConnectDefaults.AuthenticationScheme);
    Require(
        oidc.CorrelationCookie.SecurePolicy == CookieSecurePolicy.SameAsRequest,
        "local HTTP correlation cookie must follow the request security");
    Require(
        oidc.CorrelationCookie.SameSite == SameSiteMode.Lax,
        "local HTTP correlation cookie must be browser-compatible SameSite=Lax");
    Require(
        oidc.NonceCookie.SecurePolicy == CookieSecurePolicy.SameAsRequest,
        "local HTTP nonce cookie must follow the request security");
    Require(
        oidc.NonceCookie.SameSite == SameSiteMode.Lax,
        "local HTTP nonce cookie must be browser-compatible SameSite=Lax");
    Require(oidc.ResponseMode == "query", "local HTTP OIDC must use the top-level query callback");
}

static void VerifyProductionCookies()
{
    using var provider = CreateProvider(Environments.Production, allowHttpForLocalDevelopment: false);
    var oidc = ConfigureOptions<OpenIdConnectOptions>(provider, OpenIdConnectDefaults.AuthenticationScheme);
    Require(
        oidc.CorrelationCookie.SecurePolicy == CookieSecurePolicy.Always,
        "production correlation cookie must always be Secure");
    Require(
        oidc.CorrelationCookie.SameSite == SameSiteMode.None,
        "production correlation cookie must retain cross-site OIDC SameSite=None");
    Require(
        oidc.NonceCookie.SecurePolicy == CookieSecurePolicy.Always,
        "production nonce cookie must always be Secure");
    Require(
        oidc.NonceCookie.SameSite == SameSiteMode.None,
        "production nonce cookie must retain cross-site OIDC SameSite=None");
    Require(oidc.ResponseMode == "form_post", "production OIDC must retain the form_post callback");

    var session = ConfigureOptions<CookieAuthenticationOptions>(provider, CookieAuthenticationDefaults.AuthenticationScheme);
    Require(session.Cookie.SecurePolicy == CookieSecurePolicy.Always, "production session cookie must be Secure");
    Require(session.Cookie.SameSite == SameSiteMode.Lax, "production session cookie must remain SameSite=Lax");
    Require(session.Cookie.HttpOnly, "production session cookie must remain HttpOnly");
}

static ServiceProvider CreateProvider(string environmentName, bool allowHttpForLocalDevelopment)
{
    var services = new ServiceCollection();
    services.AddLogging();
    services.AddSingleton<IHostEnvironment>(new ProbeEnvironment(environmentName));
    services.AddSingleton<IOptions<ProgramKitWebOptions>>(Options.Create(new ProgramKitWebOptions
    {
        Authority = allowHttpForLocalDevelopment
            ? "http://localhost:8080/realms/program-kit"
            : "https://identity.example/realms/program-kit",
        ClientId = "program-kit-bff",
        ClientSecret = "probe-only-secret",
        Audience = "program-kit-api",
        AllowHttpForLocalDevelopment = allowHttpForLocalDevelopment
    }));
    new ProgramKitBffCookieFeature().ConfigureServices(services);
    return services.BuildServiceProvider(validateScopes: true);
}

static TOptions ConfigureOptions<TOptions>(IServiceProvider provider, string name)
    where TOptions : class, new()
{
    var options = new TOptions();
    foreach (var setup in provider.GetServices<IConfigureOptions<TOptions>>())
    {
        if (setup is IConfigureNamedOptions<TOptions> named)
        {
            named.Configure(name, options);
        }
        else
        {
            setup.Configure(options);
        }
    }
    return options;
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}

sealed class ProbeEnvironment(string environmentName) : IHostEnvironment
{
    public string EnvironmentName { get; set; } = environmentName;

    public string ApplicationName { get; set; } = "ProgramKit.Authentication.BffCookie.Probe";

    public string ContentRootPath { get; set; } = Directory.GetCurrentDirectory();

    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}
