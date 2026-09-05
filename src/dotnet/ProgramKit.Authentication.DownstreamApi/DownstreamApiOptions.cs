namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Defines named provider-neutral authenticated downstream APIs.</summary>
public sealed class DownstreamApiOptions
{
    /// <summary>Gets the configuration section containing downstream API registrations.</summary>
    public const string SectionName = "ProgramKit:Authentication:DownstreamApis";

    /// <summary>Gets downstream APIs keyed by an application-owned name.</summary>
    public Dictionary<string, DownstreamApiRegistration> Registrations { get; } =
        new(StringComparer.Ordinal);
}
