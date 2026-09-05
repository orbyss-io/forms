namespace ProgramKit.Identity.Keycloak.Admin;

/// <summary>Configures service-account access to one Keycloak realm's Admin REST API.</summary>
public sealed class KeycloakAdminOptions
{
    /// <summary>Gets the configuration section containing Keycloak Admin REST settings.</summary>
    public const string SectionName = "ProgramKit:Identity:Keycloak:Admin";
    /// <summary>Gets or sets the externally reachable Keycloak server base URL.</summary>
    public string ServerUrl { get; set; } = string.Empty;
    /// <summary>Gets or sets the target realm whose resources are administered.</summary>
    public string Realm { get; set; } = string.Empty;
    /// <summary>Gets or sets the realm that authenticates the service-account client.</summary>
    public string AdminRealm { get; set; } = "master";
    /// <summary>Gets or sets the confidential service-account client identifier.</summary>
    public string ClientId { get; set; } = string.Empty;
    /// <summary>Gets or sets the confidential service-account client secret.</summary>
    public string ClientSecret { get; set; } = string.Empty;
    /// <summary>Gets or sets whether loopback HTTP is allowed in the Development environment.</summary>
    public bool AllowHttpForLocalDevelopment { get; set; }
    /// <summary>Gets or sets the bounded HTTP operation timeout in seconds.</summary>
    public int TimeoutSeconds { get; set; } = 30;
    /// <summary>Gets or sets how early a cached service-account token is refreshed.</summary>
    public int RefreshBeforeExpirySeconds { get; set; } = 30;
}
