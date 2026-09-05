namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Configures token acquisition and routing for one downstream API.</summary>
public sealed class DownstreamApiRegistration
{
    /// <summary>Gets or sets the absolute downstream base address.</summary>
    public string BaseAddress { get; set; } = string.Empty;

    /// <summary>Gets or sets `ClientCredentials` or `TokenExchange`.</summary>
    public string AccessMode { get; set; } = "ClientCredentials";

    /// <summary>Gets or sets the named token-source or exchange-policy registration.</summary>
    public string TokenRegistration { get; set; } = string.Empty;

    /// <summary>Gets or sets the exchange target audience.</summary>
    public string? Audience { get; set; }

    /// <summary>Gets or sets the exchange target resource URI.</summary>
    public string? Resource { get; set; }

    /// <summary>Gets or sets exact scopes used to downscope a delegated token.</summary>
    public string[] Scopes { get; set; } = [];

    /// <summary>Gets or sets whether loopback HTTP is accepted during local development.</summary>
    public bool AllowHttpForLocalDevelopment { get; set; }
}
