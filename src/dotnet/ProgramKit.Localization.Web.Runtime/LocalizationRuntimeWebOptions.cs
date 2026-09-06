namespace ProgramKit.Localization.Web.Runtime;

/// <summary>Configures immutable localization runtime routes, authorization, and client caching.</summary>
public sealed class LocalizationRuntimeWebOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Localization:Runtime";

    /// <summary>Gets or sets the fixed route prefix mapped by the selected feature.</summary>
    public string RoutePrefix { get; set; } = "/_program-kit/localization/runtime";

    /// <summary>Gets or sets whether immutable translation reads are public.</summary>
    public bool AllowAnonymous { get; set; } = true;

    /// <summary>Gets or sets an optional named authorization policy when anonymous access is disabled.</summary>
    public string? AuthorizationPolicy { get; set; }

    /// <summary>Gets or sets the client cache duration for ETag-protected runtime responses.</summary>
    public int CacheSeconds { get; set; } = 300;
}
