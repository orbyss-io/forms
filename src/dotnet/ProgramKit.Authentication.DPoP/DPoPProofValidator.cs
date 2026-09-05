using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Validates ES256 RFC 9449 proofs and their access-token confirmation binding.</summary>
internal sealed class DPoPProofValidator(
    IOptions<DPoPOptions> options,
    TimeProvider timeProvider,
    IDPoPReplayStore replayStore,
    IDPoPNonceStore nonceStore)
{
    /// <summary>Returns a stable failure code or null when the request satisfies the DPoP contract.</summary>
    internal string? Validate(HttpContext context, string accessToken)
    {
        var settings = options.Value;
        var boundThumbprint = ReadBoundThumbprint(accessToken);
        var proof = context.Items[DPoPRequestState.Proof] as string;
        if (proof is null)
        {
            return settings.Required || boundThumbprint is not null ? "dpop_proof_required" : null;
        }
        if (boundThumbprint is null)
        {
            return "dpop_token_not_bound";
        }

        var parts = proof.Split('.');
        if (parts.Length != 3)
        {
            return "dpop_proof_malformed";
        }
        try
        {
            using var header = JsonDocument.Parse(Base64UrlDecode(parts[0]));
            using var payload = JsonDocument.Parse(Base64UrlDecode(parts[1]));
            if (!TryReadPublicKey(header.RootElement, out var key, out var thumbprint))
            {
                return "dpop_proof_key_invalid";
            }
            using (key)
            {
                var input = Encoding.ASCII.GetBytes($"{parts[0]}.{parts[1]}");
                var signature = Base64UrlDecode(parts[2]);
                if (!key.VerifyData(
                    input,
                    signature,
                    HashAlgorithmName.SHA256,
                    DSASignatureFormat.IeeeP1363FixedFieldConcatenation))
                {
                    return "dpop_proof_signature_invalid";
                }
            }
            if (!CryptographicOperations.FixedTimeEquals(
                Encoding.ASCII.GetBytes(boundThumbprint),
                Encoding.ASCII.GetBytes(thumbprint)))
            {
                return "dpop_key_binding_invalid";
            }
            return ValidateClaims(context, accessToken, payload.RootElement, thumbprint, settings);
        }
        catch (JsonException)
        {
            return "dpop_proof_malformed";
        }
        catch (FormatException)
        {
            return "dpop_proof_malformed";
        }
        catch (CryptographicException)
        {
            return "dpop_proof_key_invalid";
        }
    }

    /// <summary>Validates request binding, freshness, access-token hash, and replay uniqueness.</summary>
    private string? ValidateClaims(
        HttpContext context,
        string accessToken,
        JsonElement payload,
        string thumbprint,
        DPoPOptions settings)
    {
        if (!TryString(payload, "jti", out var jti)
            || !TryString(payload, "htm", out var method)
            || !TryString(payload, "htu", out var target)
            || !TryString(payload, "ath", out var accessTokenHash)
            || !payload.TryGetProperty("iat", out var issuedAt)
            || !issuedAt.TryGetInt64(out var issuedAtSeconds))
        {
            return "dpop_proof_claims_missing";
        }
        if (!string.Equals(method, context.Request.Method, StringComparison.OrdinalIgnoreCase))
        {
            return "dpop_http_method_invalid";
        }
        var expectedTarget = new Uri(
            new Uri(settings.PublicOrigin, UriKind.Absolute),
            $"{context.Request.PathBase}{context.Request.Path}");
        if (!Uri.TryCreate(target, UriKind.Absolute, out var targetUri)
            || !string.IsNullOrEmpty(targetUri.Query)
            || !string.IsNullOrEmpty(targetUri.Fragment)
            || targetUri != expectedTarget)
        {
            return "dpop_http_target_invalid";
        }
        var expectedHash = Base64UrlEncode(SHA256.HashData(Encoding.ASCII.GetBytes(accessToken)));
        if (!CryptographicOperations.FixedTimeEquals(
            Encoding.ASCII.GetBytes(expectedHash),
            Encoding.ASCII.GetBytes(accessTokenHash)))
        {
            return "dpop_access_token_hash_invalid";
        }

        var now = timeProvider.GetUtcNow().ToUnixTimeSeconds();
        if (issuedAtSeconds > now + settings.ClockSkewSeconds
            || issuedAtSeconds < now - settings.ProofMaxAgeSeconds - settings.ClockSkewSeconds)
        {
            return "dpop_proof_expired";
        }
        if (settings.RequireNonce
            && (!TryString(payload, "nonce", out var nonce) || !nonceStore.TryConsume(nonce)))
        {
            var expiresAt = timeProvider.GetUtcNow().AddSeconds(settings.NonceLifetimeSeconds);
            context.Response.Headers["DPoP-Nonce"] = nonceStore.Issue(expiresAt);
            return "use_dpop_nonce";
        }
        var expires = issuedAtSeconds + settings.ProofMaxAgeSeconds + settings.ClockSkewSeconds;
        return replayStore.TryUse(
            thumbprint,
            jti,
            DateTimeOffset.FromUnixTimeSeconds(expires))
            ? null
            : "dpop_proof_replayed";
    }

    /// <summary>Reads the verified access token's RFC 7800 JWK thumbprint binding.</summary>
    private static string? ReadBoundThumbprint(string accessToken)
    {
        var parts = accessToken.Split('.');
        if (parts.Length != 3)
        {
            return null;
        }
        try
        {
            using var payload = JsonDocument.Parse(Base64UrlDecode(parts[1]));
            return payload.RootElement.TryGetProperty("cnf", out var confirmation)
                && confirmation.ValueKind == JsonValueKind.Object
                && TryString(confirmation, "jkt", out var thumbprint)
                    ? thumbprint
                    : null;
        }
        catch (JsonException)
        {
            return null;
        }
        catch (FormatException)
        {
            return null;
        }
    }

    /// <summary>Imports the proof's public ES256 key and computes its RFC 7638 thumbprint.</summary>
    private static bool TryReadPublicKey(JsonElement header, out ECDsa key, out string thumbprint)
    {
        key = ECDsa.Create();
        thumbprint = string.Empty;
        if (!TryString(header, "typ", out var type)
            || type != "dpop+jwt"
            || !TryString(header, "alg", out var algorithm)
            || algorithm != "ES256"
            || !header.TryGetProperty("jwk", out var jwk)
            || jwk.ValueKind != JsonValueKind.Object
            || jwk.TryGetProperty("d", out _)
            || !TryString(jwk, "kty", out var keyType)
            || keyType != "EC"
            || !TryString(jwk, "crv", out var curve)
            || curve != "P-256"
            || !TryString(jwk, "x", out var x)
            || !TryString(jwk, "y", out var y))
        {
            key.Dispose();
            return false;
        }
        var xBytes = Base64UrlDecode(x);
        var yBytes = Base64UrlDecode(y);
        if (xBytes.Length != 32 || yBytes.Length != 32)
        {
            key.Dispose();
            return false;
        }
        key.ImportParameters(new ECParameters
        {
            Curve = ECCurve.NamedCurves.nistP256,
            Q = new ECPoint { X = xBytes, Y = yBytes }
        });
        var canonical = Encoding.UTF8.GetBytes($"{{\"crv\":\"P-256\",\"kty\":\"EC\",\"x\":\"{x}\",\"y\":\"{y}\"}}");
        thumbprint = Base64UrlEncode(SHA256.HashData(canonical));
        return true;
    }

    /// <summary>Reads one required non-empty JSON string.</summary>
    private static bool TryString(JsonElement value, string property, out string result)
    {
        result = string.Empty;
        if (!value.TryGetProperty(property, out var candidate) || candidate.ValueKind != JsonValueKind.String)
        {
            return false;
        }
        result = candidate.GetString() ?? string.Empty;
        return result.Length > 0;
    }

    /// <summary>Decodes an unpadded base64url value.</summary>
    private static byte[] Base64UrlDecode(string value)
    {
        var padded = value.Replace('-', '+').Replace('_', '/');
        padded += new string('=', (4 - padded.Length % 4) % 4);
        return Convert.FromBase64String(padded);
    }

    /// <summary>Encodes an unpadded base64url value.</summary>
    private static string Base64UrlEncode(ReadOnlySpan<byte> value) =>
        Convert.ToBase64String(value).TrimEnd('=').Replace('+', '-').Replace('/', '_');
}
