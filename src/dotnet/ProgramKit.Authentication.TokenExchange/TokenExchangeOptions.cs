namespace ProgramKit.Authentication.TokenExchange;

/// <summary>Defines named provider-neutral RFC 8693 token-exchange registrations.</summary>
public sealed class TokenExchangeOptions
{
    /// <summary>Gets the configuration section containing token-exchange registrations.</summary>
    public const string SectionName = "ProgramKit:Authentication:TokenExchange";

    /// <summary>Gets registrations keyed by an application-owned exchange-policy name.</summary>
    public Dictionary<string, TokenExchangeRegistration> Registrations { get; } =
        new(StringComparer.Ordinal);
}
