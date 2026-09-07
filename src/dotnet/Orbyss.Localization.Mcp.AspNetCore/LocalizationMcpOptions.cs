namespace Orbyss.Localization.Mcp.AspNetCore;

/// <summary>Configures localization MCP identity claims and transfer bounds.</summary>
public sealed class LocalizationMcpOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "Orbyss:Localization:Mcp";
    /// <summary>Gets or sets the principal subject claim.</summary>
    public string SubjectClaimType { get; set; } = "sub";
    /// <summary>Gets or sets the optional actor-kind claim.</summary>
    public string ActorKindClaimType { get; set; } = "actor_kind";
    /// <summary>Gets or sets the optional display-name claim.</summary>
    public string DisplayNameClaimType { get; set; } = "name";
    /// <summary>Gets or sets the maximum decoded import size.</summary>
    public int MaximumImportBytes { get; set; } = 8 * 1024 * 1024;
    /// <summary>Gets or sets the maximum decoded export size.</summary>
    public int MaximumExportBytes { get; set; } = 8 * 1024 * 1024;
}
