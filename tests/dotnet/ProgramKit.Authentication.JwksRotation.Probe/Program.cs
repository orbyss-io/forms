using System.Security.Claims;
using System.Security.Cryptography;
using CShells;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using Microsoft.IdentityModel.Tokens;
using ProgramKit.Authentication;
using ProgramKit.Authentication.SpaPkce;

const string issuer = "https://identity.example";
const string audience = "program-kit-api";
using var oldPrivateKey = RSA.Create(2048);
using var newPrivateKey = RSA.Create(2048);
var oldKey = PublicKey(oldPrivateKey, "old-signing-key");
var newKey = PublicKey(newPrivateKey, "new-signing-key");
var metadata = new RotatingConfigurationManager(issuer, oldKey);
using var services = BuildProvider(metadata, issuer, audience);

var oldToken = Token(oldPrivateKey, oldKey.KeyId!, issuer, audience);
var newToken = Token(newPrivateKey, newKey.KeyId!, issuer, audience);
Require((await AuthenticateAsync(services, oldToken)).Succeeded, "the initial issuer key was rejected");
Require(!(await AuthenticateAsync(services, newToken)).Succeeded,
    "a token signed by an unpublished key was accepted");

metadata.Publish(oldKey, newKey);
var firstNewAttempt = await AuthenticateAsync(services, newToken);
var secondNewAttempt = firstNewAttempt.Succeeded
    ? firstNewAttempt
    : await AuthenticateAsync(services, newToken);
Require(secondNewAttempt.Succeeded, "the bearer handler did not recover after an unfamiliar signing key");
Require(metadata.RefreshRequests > 0, "an unfamiliar kid did not request discovery/JWKS refresh");
Require((await AuthenticateAsync(services, oldToken)).Succeeded,
    "the previous signing key was rejected during the overlap window");

metadata.Publish(newKey);
metadata.RequestRefresh();
Require(!(await AuthenticateAsync(services, oldToken)).Succeeded,
    "a retired signing key remained accepted after refreshed metadata removed it");
Require((await AuthenticateAsync(services, newToken)).Succeeded,
    "the active signing key was rejected after retirement of its predecessor");

static ServiceProvider BuildProvider(
    RotatingConfigurationManager metadata,
    string issuer,
    string audience)
{
    var settings = new ShellSettings(
        new ShellId("probe"),
        ["ProgramKit.Authentication", "ProgramKit.Authentication.SpaPkce"]);
    settings.ConfigurationData[$"{ProgramKitWebOptions.SectionName}:Authority"] = issuer;
    settings.ConfigurationData[$"{ProgramKitWebOptions.SectionName}:ClientId"] = "program-kit-spa";
    settings.ConfigurationData[$"{ProgramKitWebOptions.SectionName}:Audience"] = audience;
    settings.ConfigurationData[$"{ProgramKitWebOptions.SectionName}:Scopes:0"] = "openid";
    settings.ConfigurationData[$"{ProgramKitWebOptions.SectionName}:AllowedOrigins:0"] = "https://app.example";

    var services = new ServiceCollection();
    services.AddLogging();
    services.AddSingleton<IHostEnvironment, RotationProbeEnvironment>();
    new ProgramKitAuthenticationFeature(settings).ConfigureServices(services);
    new ProgramKitSpaPkceFeature().ConfigureServices(services);
    services.PostConfigure<JwtBearerOptions>(JwtBearerDefaults.AuthenticationScheme, options =>
    {
        options.ConfigurationManager = metadata;
        options.RefreshOnIssuerKeyNotFound = true;
    });
    return services.BuildServiceProvider();
}

static async Task<AuthenticateResult> AuthenticateAsync(IServiceProvider services, string token)
{
    using var scope = services.CreateScope();
    var context = new DefaultHttpContext { RequestServices = scope.ServiceProvider };
    context.Request.Headers.Authorization = $"Bearer {token}";
    return await context.AuthenticateAsync(JwtBearerDefaults.AuthenticationScheme);
}

static RsaSecurityKey PublicKey(RSA source, string identifier)
{
    var key = new RsaSecurityKey(source.ExportParameters(false)) { KeyId = identifier };
    return key;
}

static string Token(RSA privateKey, string identifier, string issuer, string audience)
{
    var signingKey = new RsaSecurityKey(privateKey) { KeyId = identifier };
    var descriptor = new SecurityTokenDescriptor
    {
        Issuer = issuer,
        Audience = audience,
        Subject = new ClaimsIdentity([new Claim("sub", "rotation-subject")]),
        IssuedAt = DateTime.UtcNow.AddSeconds(-5),
        NotBefore = DateTime.UtcNow.AddSeconds(-5),
        Expires = DateTime.UtcNow.AddMinutes(5),
        SigningCredentials = new SigningCredentials(signingKey, SecurityAlgorithms.RsaSha256)
    };
    return new JsonWebTokenHandler().CreateToken(descriptor);
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
