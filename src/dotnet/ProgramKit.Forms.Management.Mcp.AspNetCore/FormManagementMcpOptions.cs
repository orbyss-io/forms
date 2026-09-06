namespace ProgramKit.Forms.Management.Mcp.AspNetCore;

/// <summary>Configures identity claims for form-management tool calls.</summary>
public sealed class FormManagementMcpOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Forms:Management:Mcp";
    /// <summary>Gets or sets the principal subject claim.</summary>
    public string SubjectClaimType { get; set; } = "sub";
    /// <summary>Gets or sets the optional actor-kind claim.</summary>
    public string ActorKindClaimType { get; set; } = "actor_kind";
    /// <summary>Gets or sets the optional display-name claim.</summary>
    public string DisplayNameClaimType { get; set; } = "name";
}
