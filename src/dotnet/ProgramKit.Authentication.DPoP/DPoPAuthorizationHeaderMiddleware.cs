using Microsoft.AspNetCore.Http;
using Microsoft.Extensions.Primitives;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Normalizes the RFC 9449 authorization scheme for standard JWT signature validation.</summary>
internal sealed class DPoPAuthorizationHeaderMiddleware(RequestDelegate next)
{
    /// <summary>Captures the proof and lets the existing bearer handler validate the access token first.</summary>
    public async Task InvokeAsync(HttpContext context)
    {
        var original = context.Request.Headers.Authorization;
        var value = original.ToString();
        if (!value.StartsWith("DPoP ", StringComparison.OrdinalIgnoreCase))
        {
            await next(context).ConfigureAwait(false);
            return;
        }

        var token = value[5..].Trim();
        var proofs = context.Request.Headers["DPoP"];
        if (string.IsNullOrWhiteSpace(token) || proofs.Count != 1 || StringValues.IsNullOrEmpty(proofs))
        {
            await next(context).ConfigureAwait(false);
            return;
        }

        context.Items[DPoPRequestState.AccessToken] = token;
        context.Items[DPoPRequestState.Proof] = proofs[0]!;
        context.Request.Headers.Authorization = $"Bearer {token}";
        try
        {
            await next(context).ConfigureAwait(false);
        }
        finally
        {
            context.Request.Headers.Authorization = original;
        }
    }
}
