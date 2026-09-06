namespace ProgramKit.OpenApiExport;

/// <summary>Defines the platform feature identities supplied by Program Kit runtime packages.</summary>
internal static class BuiltInFeatures
{
    /// <summary>Maps exact feature identities to their package and composition metadata.</summary>
    public static readonly IReadOnlyDictionary<string, BuiltInFeatureDefinition> Definitions =
        new Dictionary<string, BuiltInFeatureDefinition>(StringComparer.Ordinal)
        {
            ["ProgramKit.Authentication"] =
                new("ProgramKit.Authentication", [], [], false),
            ["ProgramKit.Authentication.BffCookie"] =
                new(
                    "ProgramKit.Authentication.BffCookie",
                    ["ProgramKit.Authentication", "ProgramKit.WebDefaults"],
                    ["/bff/login", "/bff/user", "/bff/antiforgery", "/bff/logout", "/bff/signed-out"],
                    false),
            ["ProgramKit.Authentication.SpaPkce"] =
                new(
                    "ProgramKit.Authentication.SpaPkce",
                    ["ProgramKit.Authentication", "ProgramKit.WebDefaults"],
                    [],
                    false),
            ["ProgramKit.DomainEvents"] =
                new("ProgramKit.DomainEvents", [], [], false),
            ["ProgramKit.Localization.Web.Management"] =
                new(
                    "ProgramKit.Localization.Web.Management",
                    [],
                    [
                        "/_program-kit/localization/catalogs",
                        "/_program-kit/localization/catalogs/{catalogId}",
                        "/_program-kit/localization/catalogs/validate",
                        "/_program-kit/localization/catalogs/{catalogId}/imports/preview",
                        "/_program-kit/localization/catalogs/{catalogId}/imports/{previewId}/apply",
                        "/_program-kit/localization/catalogs/{catalogId}/exports",
                        "/_program-kit/localization/releases/{releaseId}",
                        "/_program-kit/localization/releases/{baselineId}/diff/{candidateId}",
                        "/_program-kit/localization/catalogs/{catalogId}/{revision:long}/review",
                        "/_program-kit/localization/catalogs/{catalogId}/{revision:long}/approve",
                        "/_program-kit/localization/catalogs/{catalogId}/{revision:long}/publish",
                        "/_program-kit/localization/releases/{releaseId}/retire",
                    ],
                    false),
            ["ProgramKit.Localization.Web.Runtime"] =
                new(
                    "ProgramKit.Localization.Web.Runtime",
                    [],
                    [
                        "/_program-kit/localization/runtime/bundles/{scopeKind}/{languageTag}",
                        "/_program-kit/localization/runtime/messages/{scopeKind}/{languageTag}/{key}",
                    ],
                    false),
            ["ProgramKitTasks"] =
                new("ProgramKit.Tasks", [], [], false),
            ["ProgramKit.WebDefaults"] =
                new("ProgramKit.WebDefaults", [], [], false),
            ["ProgramKit.Web.OpenApi"] =
                new("ProgramKit.Web.OpenApi", [], ["/_program-kit/openapi/{documentName}.json"], true),
            ["ProgramKit.Web.Discovery"] =
                new("ProgramKit.Web.Discovery", [], ["/robots.txt", "/sitemap.xml"], false),
            ["ProgramKit.Web.ProblemDetails"] =
                new("ProgramKit.Web.ProblemDetails", [], [], false),
        };
}
