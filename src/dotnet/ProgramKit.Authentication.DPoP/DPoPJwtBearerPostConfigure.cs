using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.Extensions.Options;
using Microsoft.IdentityModel.JsonWebTokens;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Chains DPoP proof validation after ordinary issuer/signature/audience/lifetime validation.</summary>
internal sealed class DPoPJwtBearerPostConfigure(DPoPProofValidator validator)
    : IPostConfigureOptions<JwtBearerOptions>
{
    /// <inheritdoc />
    public void PostConfigure(string? name, JwtBearerOptions options)
    {
        if (name != JwtBearerDefaults.AuthenticationScheme)
        {
            return;
        }
        var existing = options.Events.OnTokenValidated;
        options.Events.OnTokenValidated = async context =>
        {
            if (existing is not null)
            {
                await existing(context).ConfigureAwait(false);
            }
            if (context.Result?.Failure is not null)
            {
                return;
            }
            var accessToken = context.HttpContext.Items[DPoPRequestState.AccessToken] as string
                ?? (context.SecurityToken as JsonWebToken)?.EncodedToken
                ?? string.Empty;
            var failure = validator.Validate(context.HttpContext, accessToken);
            if (failure is not null)
            {
                context.Fail(failure);
            }
        };
    }
}
