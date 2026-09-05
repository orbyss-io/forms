using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;

/// <summary>Provides the environment used by transport-policy validation.</summary>
internal sealed class ProbeEnvironment(string environmentName) : IHostEnvironment
{
    /// <inheritdoc />
    public string EnvironmentName { get; set; } = environmentName;

    /// <inheritdoc />
    public string ApplicationName { get; set; } = "ProgramKit.Authentication.ClientCredentials.Probe";

    /// <inheritdoc />
    public string ContentRootPath { get; set; } = Directory.GetCurrentDirectory();

    /// <inheritdoc />
    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}
