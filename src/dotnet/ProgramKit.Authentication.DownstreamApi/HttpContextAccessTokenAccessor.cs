using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Http;

namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Reads the current access token from ASP.NET Core's authenticated session.</summary>
internal sealed class HttpContextAccessTokenAccessor(IHttpContextAccessor contextAccessor)
    : ICurrentAccessTokenAccessor
{
    /// <inheritdoc />
    public async ValueTask<string> GetRequiredTokenAsync(CancellationToken cancellationToken)
    {
        var context = contextAccessor.HttpContext
            ?? throw new InvalidOperationException("A delegated downstream call requires an active HTTP request.");
        cancellationToken.ThrowIfCancellationRequested();
        var token = await context.GetTokenAsync("access_token").ConfigureAwait(false);
        if (string.IsNullOrWhiteSpace(token))
        {
            throw new InvalidOperationException(
                "A delegated downstream call requires an authenticated session containing an access token.");
        }
        return token;
    }
}
