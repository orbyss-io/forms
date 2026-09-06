namespace ProgramKit.Forms.Web.Management;

/// <summary>Configures form-management routes, claims, and authorization policies.</summary>
public sealed class FormManagementWebOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Forms:Management";
    /// <summary>Gets or sets the fixed management route prefix.</summary>
    public string RoutePrefix { get; set; } = "/_program-kit/forms";
    /// <summary>Gets or sets the optional management-read policy.</summary>
    public string? ReadPolicy { get; set; }
    /// <summary>Gets or sets the optional authoring and compilation policy.</summary>
    public string? WritePolicy { get; set; }
    /// <summary>Gets or sets the optional review and approval policy.</summary>
    public string? ReviewPolicy { get; set; }
    /// <summary>Gets or sets the optional publication policy.</summary>
    public string? PublishPolicy { get; set; }
    /// <summary>Gets or sets the optional retirement policy.</summary>
    public string? RetirePolicy { get; set; }
    /// <summary>Gets or sets the immutable principal subject claim.</summary>
    public string SubjectClaimType { get; set; } = "sub";
    /// <summary>Gets or sets the optional audit actor-kind claim.</summary>
    public string ActorKindClaimType { get; set; } = "actor_kind";
    /// <summary>Gets or sets the optional audit display-name claim.</summary>
    public string DisplayNameClaimType { get; set; } = "name";
}
