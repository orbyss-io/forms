using CShells;
using CShells.Features;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.ClientCredentials;

/// <summary>Composes provider-neutral machine-token acquisition into one shell.</summary>
[ShellFeature(
    name: "ProgramKit.Authentication.ClientCredentials",
    DisplayName = "Program Kit OAuth Client Credentials",
    Description = "Acquires and safely caches named OAuth client-credentials tokens.")]
public sealed class ProgramKitClientCredentialsFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<ClientCredentialsOptions>(
            settings.GetConfigurationRoot().GetSection(ClientCredentialsOptions.SectionName));
        services.AddSingleton<IValidateOptions<ClientCredentialsOptions>, ClientCredentialsOptionsValidator>();
        services.AddHttpClient(ClientCredentialsTokenProvider.HttpClientName);
        services.TryAddSingleton(TimeProvider.System);
        services.AddSingleton<IClientCredentialsTokenProvider, ClientCredentialsTokenProvider>();
    }
}
