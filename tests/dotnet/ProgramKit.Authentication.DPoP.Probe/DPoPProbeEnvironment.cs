using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;

/// <summary>Provides the host environment consumed by the public feature composition seam.</summary>
internal sealed class DPoPProbeEnvironment(string environmentName) : IHostEnvironment
{
    /// <inheritdoc />
    public string EnvironmentName { get; set; } = environmentName;

    /// <inheritdoc />
    public string ApplicationName { get; set; } = "ProgramKit.Authentication.DPoP.Probe";

    /// <inheritdoc />
    public string ContentRootPath { get; set; } = Directory.GetCurrentDirectory();

    /// <inheritdoc />
    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}
