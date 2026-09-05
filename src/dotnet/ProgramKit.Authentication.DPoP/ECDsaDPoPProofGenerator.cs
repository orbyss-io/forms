using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Owns a P-256 key and creates ES256 RFC 9449 proofs.</summary>
public sealed class ECDsaDPoPProofGenerator : IDPoPProofGenerator, IDisposable
{
    /// <summary>Serializes access to the owned cryptographic key.</summary>
    private readonly object sync = new();

    /// <summary>Holds the client private key for the generator lifetime.</summary>
    private readonly ECDsa signingKey;

    /// <summary>Supplies deterministic or system issuance times.</summary>
    private readonly TimeProvider timeProvider;

    /// <summary>Holds the public JWK emitted in every proof header.</summary>
    private readonly IReadOnlyDictionary<string, string> publicJwk;

    /// <summary>Initializes an owning proof generator around validated P-256 key material.</summary>
    private ECDsaDPoPProofGenerator(ECDsa signingKey, TimeProvider timeProvider)
    {
        this.signingKey = signingKey;
        this.timeProvider = timeProvider;
        var parameters = signingKey.ExportParameters(false);
        if (parameters.Curve.Oid.Value != ECCurve.NamedCurves.nistP256.Oid.Value
            || parameters.Q.X is null
            || parameters.Q.Y is null)
        {
            signingKey.Dispose();
            throw new CryptographicException("A DPoP proof key must use the P-256 curve.");
        }
        var x = Base64Url(parameters.Q.X);
        var y = Base64Url(parameters.Q.Y);
        publicJwk = new Dictionary<string, string>(StringComparer.Ordinal)
        {
            ["kty"] = "EC",
            ["crv"] = "P-256",
            ["x"] = x,
            ["y"] = y,
        };
        var canonical = Encoding.UTF8.GetBytes(
            $"{{\"crv\":\"P-256\",\"kty\":\"EC\",\"x\":\"{x}\",\"y\":\"{y}\"}}");
        JwkThumbprint = Base64Url(SHA256.HashData(canonical));
    }

    /// <inheritdoc />
    public string JwkThumbprint { get; }

    /// <summary>Creates a new process-local P-256 proof key.</summary>
    public static ECDsaDPoPProofGenerator CreateEphemeral(TimeProvider? timeProvider = null) =>
        new(ECDsa.Create(ECCurve.NamedCurves.nistP256), timeProvider ?? TimeProvider.System);

    /// <summary>Imports a persisted PKCS#8 P-256 private key.</summary>
    public static ECDsaDPoPProofGenerator ImportPkcs8(
        ReadOnlySpan<byte> privateKey,
        TimeProvider? timeProvider = null)
    {
        var key = ECDsa.Create();
        try
        {
            key.ImportPkcs8PrivateKey(privateKey, out var bytesRead);
            if (bytesRead != privateKey.Length)
            {
                throw new CryptographicException("The PKCS#8 DPoP key contains trailing data.");
            }
            return new ECDsaDPoPProofGenerator(key, timeProvider ?? TimeProvider.System);
        }
        catch
        {
            key.Dispose();
            throw;
        }
    }

    /// <summary>Exports the owned private key for consumer-controlled, protected persistence.</summary>
    public byte[] ExportPkcs8PrivateKey()
    {
        lock (sync)
        {
            return signingKey.ExportPkcs8PrivateKey();
        }
    }

    /// <inheritdoc />
    public string CreateProof(DPoPProofRequest request)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (string.IsNullOrWhiteSpace(request.Method))
        {
            throw new ArgumentException("A DPoP proof requires an HTTP method.", nameof(request));
        }
        if (!request.TargetUri.IsAbsoluteUri)
        {
            throw new ArgumentException("A DPoP proof target must be absolute.", nameof(request));
        }
        if (request.ProofIdentifier is not null && string.IsNullOrWhiteSpace(request.ProofIdentifier))
        {
            throw new ArgumentException("An explicit DPoP proof identifier cannot be empty.", nameof(request));
        }
        if (request.Nonce is not null && string.IsNullOrWhiteSpace(request.Nonce))
        {
            throw new ArgumentException("An explicit DPoP nonce cannot be empty.", nameof(request));
        }

        var target = new UriBuilder(request.TargetUri) { Query = string.Empty, Fragment = string.Empty }
            .Uri.AbsoluteUri;
        var header = new Dictionary<string, object>(StringComparer.Ordinal)
        {
            ["typ"] = "dpop+jwt",
            ["alg"] = "ES256",
            ["jwk"] = publicJwk,
        };
        var payload = new Dictionary<string, object>(StringComparer.Ordinal)
        {
            ["jti"] = request.ProofIdentifier ?? Guid.NewGuid().ToString("D"),
            ["htm"] = request.Method.ToUpperInvariant(),
            ["htu"] = target,
            ["iat"] = (request.IssuedAt ?? timeProvider.GetUtcNow()).ToUnixTimeSeconds(),
        };
        if (request.AccessToken is not null)
        {
            payload["ath"] = Base64Url(
                SHA256.HashData(Encoding.ASCII.GetBytes(request.AccessToken)));
        }
        if (request.Nonce is not null)
        {
            payload["nonce"] = request.Nonce;
        }

        var encodedHeader = Base64Url(JsonSerializer.SerializeToUtf8Bytes(header));
        var encodedPayload = Base64Url(JsonSerializer.SerializeToUtf8Bytes(payload));
        var input = Encoding.ASCII.GetBytes($"{encodedHeader}.{encodedPayload}");
        byte[] signature;
        lock (sync)
        {
            signature = signingKey.SignData(
                input,
                HashAlgorithmName.SHA256,
                DSASignatureFormat.IeeeP1363FixedFieldConcatenation);
        }
        return $"{encodedHeader}.{encodedPayload}.{Base64Url(signature)}";
    }

    /// <inheritdoc />
    public void Dispose() => signingKey.Dispose();

    /// <summary>Encodes an unpadded base64url value.</summary>
    private static string Base64Url(ReadOnlySpan<byte> value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
}
