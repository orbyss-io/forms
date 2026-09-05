using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using CShells;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;
using ProgramKit.Authentication.DPoP;

var now = new DateTimeOffset(2026, 9, 5, 14, 0, 0, TimeSpan.Zero);
using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
var publicKey = key.ExportParameters(false);
var x = Base64Url(publicKey.Q.X!);
var y = Base64Url(publicKey.Q.Y!);
var canonicalJwk = Encoding.UTF8.GetBytes(
    $"{{\"crv\":\"P-256\",\"kty\":\"EC\",\"x\":\"{x}\",\"y\":\"{y}\"}}");
var thumbprint = Base64Url(SHA256.HashData(canonicalJwk));
var accessToken = Jwt(
    new { alg = "RS256" },
    new { sub = "subject", cnf = new { jkt = thumbprint } },
    [1]);

using var services = BuildProvider(now);
var replayStore = services.GetRequiredService<IDPoPReplayStore>();
Require(replayStore is RecordingReplayStore, "a consumer-provided replay store was replaced");
var feature = services.GetRequiredService<ProgramKitDPoPFeature>();
var pipeline = BuildPipeline(services, feature);
var proof = Proof(key, x, y, "proof-1", "GET", "https://api.example/protected", accessToken, now);
Require(await ValidateAsync(pipeline, services, "GET", "/protected", accessToken, proof) is null,
    "a valid bound DPoP proof was rejected");
Require(await ValidateAsync(pipeline, services, "GET", "/protected", accessToken, proof) == "dpop_proof_replayed",
    "proof replay was not rejected");
Require(((RecordingReplayStore)replayStore).Reservations == 2,
    "the replaceable replay-store contract did not observe both atomic reservations");
Require(
    await ValidateAsync(
        pipeline,
        services,
        "POST",
        "/protected",
        accessToken,
        Proof(key, x, y, "proof-2", "GET", "https://api.example/protected", accessToken, now))
        == "dpop_http_method_invalid",
    "HTTP method binding was not enforced");
Require(
    await ValidateAsync(
        pipeline,
        services,
        "GET",
        "/different",
        accessToken,
        Proof(key, x, y, "proof-3", "GET", "https://api.example/protected", accessToken, now))
        == "dpop_http_target_invalid",
    "public target binding was not enforced");
Require(await ValidateAsync(pipeline, services, "GET", "/protected", accessToken, null) == "dpop_proof_required",
    "bound token fell back to bearer use");

var unbound = Jwt(new { alg = "RS256" }, new { sub = "subject" }, [1]);
Require(
    await ValidateAsync(
        pipeline,
        services,
        "GET",
        "/protected",
        unbound,
        Proof(key, x, y, "proof-4", "GET", "https://api.example/protected", unbound, now))
        == "dpop_token_not_bound",
    "an unbound token was accepted as proof-of-possession");

using var nonceServices = BuildProvider(now, requireNonce: true);
var nonceFeature = nonceServices.GetRequiredService<ProgramKitDPoPFeature>();
var noncePipeline = BuildPipeline(nonceServices, nonceFeature);
var challenged = await ValidateDetailedAsync(
    noncePipeline,
    nonceServices,
    "GET",
    "/protected",
    accessToken,
    Proof(key, x, y, "nonce-proof-1", "GET", "https://api.example/protected", accessToken, now));
Require(challenged.Failure == "use_dpop_nonce" && !string.IsNullOrWhiteSpace(challenged.Nonce),
    "a missing nonce did not produce a fresh DPoP-Nonce challenge");
var nonceProof = Proof(
    key,
    x,
    y,
    "nonce-proof-2",
    "GET",
    "https://api.example/protected",
    accessToken,
    now,
    challenged.Nonce);
Require((await ValidateDetailedAsync(
    noncePipeline, nonceServices, "GET", "/protected", accessToken, nonceProof)).Failure is null,
    "a proof carrying the server-issued nonce was rejected");
var consumed = await ValidateDetailedAsync(
    noncePipeline,
    nonceServices,
    "GET",
    "/protected",
    accessToken,
    Proof(
        key,
        x,
        y,
        "nonce-proof-3",
        "GET",
        "https://api.example/protected",
        accessToken,
        now,
        challenged.Nonce));
Require(consumed.Failure == "use_dpop_nonce" && consumed.Nonce != challenged.Nonce,
    "a consumed nonce was not rejected with a fresh challenge");

using var outbound = ECDsaDPoPProofGenerator.CreateEphemeral(
    new DPoPProbeTimeProvider(now));
var exportedKey = outbound.ExportPkcs8PrivateKey();
using var restored = ECDsaDPoPProofGenerator.ImportPkcs8(
    exportedKey,
    new DPoPProbeTimeProvider(now));
Require(restored.JwkThumbprint == outbound.JwkThumbprint,
    "persisted DPoP key material changed its binding thumbprint");
var outboundToken = Jwt(
    new { alg = "RS256" },
    new { sub = "outbound", cnf = new { jkt = restored.JwkThumbprint } },
    [1]);
var outboundProof = restored.CreateProof(new DPoPProofRequest
{
    Method = "get",
    TargetUri = new Uri("https://api.example/protected?sensitive=query#fragment"),
    AccessToken = outboundToken,
    Nonce = "provider-supplied-nonce",
    ProofIdentifier = "outbound-proof-1",
});
Require(await ValidateAsync(
    pipeline, services, "GET", "/protected", outboundToken, outboundProof) is null,
    "the public outbound proof generator did not interoperate with resource validation");
using (var generatedPayload = JsonDocument.Parse(Base64UrlDecode(outboundProof.Split('.')[1])))
{
    Require(generatedPayload.RootElement.GetProperty("htu").GetString()
        == "https://api.example/protected",
        "the outbound proof leaked a target query or fragment into htu");
    Require(generatedPayload.RootElement.GetProperty("nonce").GetString()
        == "provider-supplied-nonce",
        "the outbound proof omitted the supplied server nonce");
}

static ServiceProvider BuildProvider(DateTimeOffset now, bool requireNonce = false)
{
    var settings = new ShellSettings(new ShellId("probe"), ["ProgramKit.Authentication.DPoP"]);
    settings.ConfigurationData[$"{DPoPOptions.SectionName}:PublicOrigin"] = "https://api.example";
    settings.ConfigurationData[$"{DPoPOptions.SectionName}:ProofMaxAgeSeconds"] = "60";
    settings.ConfigurationData[$"{DPoPOptions.SectionName}:ClockSkewSeconds"] = "5";
    settings.ConfigurationData[$"{DPoPOptions.SectionName}:RequireNonce"] = requireNonce.ToString();
    var feature = new ProgramKitDPoPFeature(settings);
    var services = new ServiceCollection();
    services.AddLogging();
    services.AddSingleton<IHostEnvironment>(new DPoPProbeEnvironment(Environments.Production));
    services.AddSingleton<TimeProvider>(new DPoPProbeTimeProvider(now));
    services.AddSingleton<IDPoPReplayStore, RecordingReplayStore>();
    services.AddSingleton(feature);
    services.AddAuthentication().AddJwtBearer();
    feature.ConfigureServices(services);
    return services.BuildServiceProvider();
}

static RequestDelegate BuildPipeline(IServiceProvider services, ProgramKitDPoPFeature feature)
{
    var app = new ApplicationBuilder(services);
    feature.UseMiddleware(app, services.GetRequiredService<IHostEnvironment>());
    app.Run(async context =>
    {
        var authorization = context.Request.Headers.Authorization.ToString();
        if (!authorization.StartsWith("Bearer ", StringComparison.Ordinal))
        {
            context.Items["probe-failure"] = "authorization_not_normalized";
            return;
        }

        var token = authorization[7..];
        var monitor = services.GetRequiredService<IOptionsMonitor<JwtBearerOptions>>();
        var options = monitor.Get(JwtBearerDefaults.AuthenticationScheme);
        var scheme = new AuthenticationScheme(
            JwtBearerDefaults.AuthenticationScheme,
            JwtBearerDefaults.AuthenticationScheme,
            typeof(JwtBearerHandler));
        var validated = new TokenValidatedContext(context, scheme, options)
        {
            Principal = new ClaimsPrincipal(new ClaimsIdentity("probe")),
            SecurityToken = new JsonWebToken(token)
        };
        await options.Events.TokenValidated(validated);
        context.Items["probe-failure"] = validated.Result?.Failure?.Message;
    });
    return app.Build();
}

static async Task<string?> ValidateAsync(
    RequestDelegate pipeline,
    IServiceProvider services,
    string method,
    string path,
    string accessToken,
    string? proof)
    => (await ValidateDetailedAsync(pipeline, services, method, path, accessToken, proof)).Failure;

static async Task<DPoPValidation> ValidateDetailedAsync(
    RequestDelegate pipeline,
    IServiceProvider services,
    string method,
    string path,
    string accessToken,
    string? proof)
{
    var context = new DefaultHttpContext { RequestServices = services };
    context.Request.Method = method;
    context.Request.Path = path;
    context.Request.Headers.Authorization = proof is null ? $"Bearer {accessToken}" : $"DPoP {accessToken}";
    if (proof is not null)
    {
        context.Request.Headers["DPoP"] = proof;
    }
    await pipeline(context);
    return new DPoPValidation(
        context.Items["probe-failure"] as string,
        context.Response.Headers["DPoP-Nonce"].FirstOrDefault());
}

static string Proof(
    ECDsa key,
    string x,
    string y,
    string identifier,
    string method,
    string target,
    string accessToken,
    DateTimeOffset issuedAt,
    string? nonce = null)
{
    var header = new { typ = "dpop+jwt", alg = "ES256", jwk = new { kty = "EC", crv = "P-256", x, y } };
    var payload = new
    {
        jti = identifier,
        htm = method,
        htu = target,
        iat = issuedAt.ToUnixTimeSeconds(),
        ath = Base64Url(SHA256.HashData(Encoding.ASCII.GetBytes(accessToken))),
        nonce
    };
    var encodedHeader = Base64Url(JsonSerializer.SerializeToUtf8Bytes(header));
    var encodedPayload = Base64Url(JsonSerializer.SerializeToUtf8Bytes(payload));
    var input = Encoding.ASCII.GetBytes($"{encodedHeader}.{encodedPayload}");
    var signature = key.SignData(
        input,
        HashAlgorithmName.SHA256,
        DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
    return $"{encodedHeader}.{encodedPayload}.{Base64Url(signature)}";
}

static string Jwt(object header, object payload, byte[] signature) =>
    $"{Base64Url(JsonSerializer.SerializeToUtf8Bytes(header))}."
    + $"{Base64Url(JsonSerializer.SerializeToUtf8Bytes(payload))}.{Base64Url(signature)}";

static string Base64Url(ReadOnlySpan<byte> value) =>
    Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');

static byte[] Base64UrlDecode(string value)
{
    var padded = value.Replace('-', '+').Replace('_', '/');
    padded += new string('=', (4 - padded.Length % 4) % 4);
    return Convert.FromBase64String(padded);
}

static void Require(bool condition, string message)
{
    if (!condition)
    {
        throw new InvalidOperationException(message);
    }
}

/// <summary>Records use of the public replay-store replacement seam.</summary>
sealed class RecordingReplayStore(TimeProvider timeProvider) : IDPoPReplayStore
{
    /// <summary>Provides the actual atomic in-process reservation behavior.</summary>
    private readonly InMemoryDPoPReplayStore inner = new(timeProvider);

    /// <summary>Gets the number of attempted proof reservations.</summary>
    public int Reservations { get; private set; }

    /// <inheritdoc />
    public bool TryUse(string proofThumbprint, string proofIdentifier, DateTimeOffset expiresAt)
    {
        Reservations++;
        return inner.TryUse(proofThumbprint, proofIdentifier, expiresAt);
    }
}
