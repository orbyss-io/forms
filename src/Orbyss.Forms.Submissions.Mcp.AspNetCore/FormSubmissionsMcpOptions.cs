namespace Orbyss.Forms.Submissions.Mcp.AspNetCore;

/// <summary>Configures claims used by the form-operations MCP contributor.</summary>
public sealed class FormSubmissionsMcpOptions
{
    /// <summary>Gets the configuration section name.</summary>
    public const string SectionName = "Orbyss:Forms:Submissions:Mcp";
    /// <summary>Gets or sets the principal subject claim.</summary>
    public string SubjectClaimType { get; set; } = "sub";
    /// <summary>Gets or sets the optional actor-kind claim.</summary>
    public string ActorKindClaimType { get; set; } = "actor_kind";
    /// <summary>Gets or sets the optional display-name claim.</summary>
    public string DisplayNameClaimType { get; set; } = "name";
}
