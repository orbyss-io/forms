using CShells;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Builder;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Options;
using ProgramKit.Authentication.SpaPkce;

namespace ProgramKit.Authentication.DPoP;

/// <summary>Composes RFC 9449 proof-of-possession enforcement into a bearer API shell.</summary>
[ShellFeature(
    name: "ProgramKit.Authentication.DPoP",
    DisplayName = "Program Kit DPoP",
    Description = "Enforces sender-constrained RFC 9449 access tokens and proof replay defense.",
    DependsOn = [typeof(ProgramKitSpaPkceFeature)])]
public sealed class ProgramKitDPoPFeature(ShellSettings settings) : IMiddlewareShellFeature
{
    /// <inheritdoc />
    public int Order => -900;

    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<DPoPOptions>(
            settings.GetConfigurationRoot().GetSection(DPoPOptions.SectionName));
        services.AddSingleton<IValidateOptions<DPoPOptions>, DPoPOptionsValidator>();
        services.TryAddSingleton(TimeProvider.System);
        services.TryAddSingleton<IDPoPReplayStore, InMemoryDPoPReplayStore>();
        services.TryAddSingleton<IDPoPNonceStore, InMemoryDPoPNonceStore>();
        services.AddSingleton<DPoPProofValidator>();
        services.AddSingleton<IPostConfigureOptions<JwtBearerOptions>, DPoPJwtBearerPostConfigure>();
    }

    /// <inheritdoc />
    public void UseMiddleware(IApplicationBuilder app, IHostEnvironment? environment) =>
        app.UseMiddleware<DPoPAuthorizationHeaderMiddleware>();
}
