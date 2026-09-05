using System.Globalization;
using System.Security.Claims;
using CShells;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication.Assurance;

var now = new DateTimeOffset(2026, 9, 5, 18, 0, 0, TimeSpan.Zero);
using var services = BuildProvider(now, valid: true);
var evaluator = services.GetRequiredService<IAssuranceEvaluator>();
var authorization = services.GetRequiredService<IAuthorizationService>();
var strong = Principal("urn:example:assurance:high", ["pwd", "otp"], now.AddMinutes(-2));
var evaluation = evaluator.Evaluate(strong, "high-value");
Require(evaluation.Satisfied, "valid high assurance evidence was rejected");
Require(evaluation.AcceptedAcrValues.SequenceEqual(["urn:example:assurance:high"]),
    "step-up ACR request values changed");
Require((await authorization.AuthorizeAsync(strong, null, AssurancePolicyNames.For("high-value"))).Succeeded,
    "the assurance authorization policy rejected valid evidence");

var wrongAcr = Principal("urn:example:assurance:low", ["pwd", "otp"], now.AddMinutes(-2));
Require(evaluator.Evaluate(wrongAcr, "high-value").FailureCode == "assurance_acr_insufficient",
    "an unaccepted ACR value did not fail closed");
var missingMethod = Principal("urn:example:assurance:high", ["pwd"], now.AddMinutes(-2));
Require(evaluator.Evaluate(missingMethod, "high-value").FailureCode == "assurance_amr_insufficient",
    "a missing authentication method did not fail closed");
var stale = Principal("urn:example:assurance:high", ["pwd", "otp"], now.AddMinutes(-11));
Require(evaluator.Evaluate(stale, "high-value").FailureCode == "assurance_authentication_stale",
    "stale authentication evidence was accepted");
var arrayAmr = new ClaimsPrincipal(new ClaimsIdentity(
    [
        new Claim("acr", "urn:example:assurance:high"),
        new Claim("amr", "[\"pwd\",\"otp\"]"),
        new Claim("auth_time", now.AddMinutes(-1).ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture))
    ],
    "probe"));
Require(evaluator.Evaluate(arrayAmr, "high-value").Satisfied,
    "the interoperable JSON-array AMR representation was rejected");

using var invalid = BuildProvider(now, valid: false);
try
{
    _ = invalid.GetRequiredService<IOptions<AssuranceOptions>>().Value;
    throw new InvalidOperationException("an ineffective assurance policy passed validation");
}
catch (OptionsValidationException)
{
}

static ServiceProvider BuildProvider(DateTimeOffset now, bool valid)
{
    var settings = new ShellSettings(new ShellId("probe"), ["ProgramKit.Authentication.Assurance"]);
    var prefix = $"{AssuranceOptions.SectionName}:Policies:high-value";
    if (valid)
    {
        settings.ConfigurationData[$"{prefix}:AcceptedAcrValues:0"] = "urn:example:assurance:high";
        settings.ConfigurationData[$"{prefix}:RequiredAmrValues:0"] = "pwd";
        settings.ConfigurationData[$"{prefix}:RequiredAmrValues:1"] = "otp";
        settings.ConfigurationData[$"{prefix}:MaximumAuthenticationAgeSeconds"] = "600";
    }
    else
    {
        settings.ConfigurationData[$"{prefix}:AcceptedAcrValues"] = "";
    }
    var services = new ServiceCollection();
    services.AddLogging();
    services.AddAuthorization();
    services.AddSingleton<TimeProvider>(new AssuranceProbeTimeProvider(now));
    new ProgramKitAssuranceFeature(settings).ConfigureServices(services);
    return services.BuildServiceProvider();
}

static ClaimsPrincipal Principal(string acr, string[] methods, DateTimeOffset authenticatedAt)
{
    var claims = new List<Claim>
    {
        new("acr", acr),
        new("auth_time", authenticatedAt.ToUnixTimeSeconds().ToString(CultureInfo.InvariantCulture))
    };
    claims.AddRange(methods.Select(method => new Claim("amr", method)));
    return new ClaimsPrincipal(new ClaimsIdentity(claims, "probe"));
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}
