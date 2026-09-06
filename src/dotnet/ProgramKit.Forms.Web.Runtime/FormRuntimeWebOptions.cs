namespace ProgramKit.Forms.Web.Runtime;

/// <summary>Configures immutable form runtime routes, authorization, and client caching.</summary>
public sealed class FormRuntimeWebOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Forms:Runtime";
    /// <summary>Gets or sets the fixed runtime route prefix.</summary>
    public string RoutePrefix { get; set; } = "/_program-kit/forms/runtime";
    /// <summary>Gets or sets whether immutable releases may be read anonymously.</summary>
    public bool AllowAnonymous { get; set; } = true;
    /// <summary>Gets or sets the optional named policy when anonymous access is disabled.</summary>
    public string? AuthorizationPolicy { get; set; }
    /// <summary>Gets or sets the client cache duration in seconds.</summary>
    public int CacheSeconds { get; set; } = 300;
}
