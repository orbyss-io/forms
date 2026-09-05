using Microsoft.Extensions.FileProviders;
using Microsoft.Extensions.Hosting;

/// <summary>Provides the production environment used by the public authentication features.</summary>
internal sealed class RotationProbeEnvironment : IHostEnvironment
{
    /// <inheritdoc />
    public string EnvironmentName { get; set; } = Environments.Production;

    /// <inheritdoc />
    public string ApplicationName { get; set; } = "ProgramKit.Authentication.JwksRotation.Probe";

    /// <inheritdoc />
    public string ContentRootPath { get; set; } = Directory.GetCurrentDirectory();

    /// <inheritdoc />
    public IFileProvider ContentRootFileProvider { get; set; } = new NullFileProvider();
}
