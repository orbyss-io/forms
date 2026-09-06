namespace ProgramKit.Localization.Web.Management;

/// <summary>Configures shell-owned localization management routes, claims, authorization, and upload bounds.</summary>
public sealed class LocalizationManagementWebOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Localization:Management";

    /// <summary>Gets or sets the route prefix mapped by the selected feature.</summary>
    public string RoutePrefix { get; set; } = "/_program-kit/localization";

    /// <summary>Gets or sets an optional named policy for management reads; the default policy is used when absent.</summary>
    public string? ReadPolicy { get; set; }

    /// <summary>Gets or sets an optional named policy for catalog mutations and lifecycle actions.</summary>
    public string? WritePolicy { get; set; }

    /// <summary>Gets or sets an optional named policy for import preview and application.</summary>
    public string? ImportPolicy { get; set; }

    /// <summary>Gets or sets an optional named policy for exports.</summary>
    public string? ExportPolicy { get; set; }

    /// <summary>Gets or sets the claim that supplies the immutable audit actor identifier.</summary>
    public string SubjectClaimType { get; set; } = "sub";

    /// <summary>Gets or sets the optional claim that supplies the audit actor kind.</summary>
    public string ActorKindClaimType { get; set; } = "actor_kind";

    /// <summary>Gets or sets the optional claim that supplies the audit display name.</summary>
    public string DisplayNameClaimType { get; set; } = "name";

    /// <summary>Gets or sets the maximum decoded import payload accepted by the endpoint.</summary>
    public int MaximumImportBytes { get; set; } = 8 * 1024 * 1024;
}
