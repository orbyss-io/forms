using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;
/// <summary>Provides the development environment used by endpoint-policy validation.</summary>
internal sealed class ProbeEnvironment : IHostEnvironment
{
    /// <inheritdoc />
    public string EnvironmentName { get; set; } = Environments.Development;
    /// <inheritdoc />
    public string ApplicationName { get; set; } = "ProgramKit.Identity.Keycloak.Admin.Probe";
    /// <inheritdoc />
    public string ContentRootPath { get; set; } = Directory.GetCurrentDirectory();
    /// <inheritdoc />
    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}
