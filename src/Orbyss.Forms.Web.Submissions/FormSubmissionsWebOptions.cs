namespace Orbyss.Forms.Web.Submissions;

/// <summary>Configures endpoint routes, policies, and principal claim mappings.</summary>
public sealed class FormSubmissionsWebOptions
{
    /// <summary>Gets the configuration section name.</summary>
    public const string SectionName = "Orbyss:Forms:SubmissionsWeb";
    /// <summary>Gets or sets the fixed endpoint prefix.</summary>
    public string RoutePrefix { get; set; } = "/orbyss-forms/forms";
    /// <summary>Gets or sets the optional owner-read policy.</summary>
    public string? ReadPolicy { get; set; }
    /// <summary>Gets or sets the optional owner-write policy.</summary>
    public string? WritePolicy { get; set; }
    /// <summary>Gets or sets the policy for scanner retries.</summary>
    public string? ScanPolicy { get; set; }
    /// <summary>Gets or sets the required administrative review policy.</summary>
    public string ReviewPolicy { get; set; } = "Orbyss.Forms.Submissions.Review";
    /// <summary>Gets or sets the principal subject claim.</summary>
    public string SubjectClaimType { get; set; } = "sub";
    /// <summary>Gets or sets the optional actor-kind claim.</summary>
    public string ActorKindClaimType { get; set; } = "actor_kind";
    /// <summary>Gets or sets the optional display-name claim.</summary>
    public string DisplayNameClaimType { get; set; } = "name";
}
