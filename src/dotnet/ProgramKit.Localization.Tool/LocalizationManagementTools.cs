using System.ComponentModel;
using System.Security.Claims;
using ModelContextProtocol.Server;

namespace ProgramKit.Localization.Tool;

/// <summary>Exposes governed localization workflows without duplicating application rules.</summary>
[McpServerToolType]
public sealed class LocalizationManagementTools
{
    /// <summary>Prevents direct construction; the SDK binds static tool methods.</summary>
    private LocalizationManagementTools() { }

    /// <summary>Lists bounded catalog projections.</summary>
    [McpServerTool(Name = "localization.catalogs.list", Title = "List localization catalogs", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("List a bounded page of localization catalogs by identifier or name.")]
    public static ValueTask<LocalizationPage<LocalizationCatalogItem>> ListAsync(string? search, int first, int maximum, ILocalizationCatalogQueries queries, CancellationToken cancellationToken) => queries.FindAsync(search, first, maximum, cancellationToken);

    /// <summary>Gets one editable catalog and version.</summary>
    [McpServerTool(Name = "localization.catalogs.get", Title = "Get localization catalog", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one editable localization catalog and its current opaque version.")]
    public static ValueTask<LocalizationCatalogDocument?> GetAsync(string catalogId, ILocalizationCatalogQueries queries, CancellationToken cancellationToken) => queries.GetCatalogAsync(new LocalizationCatalogId(catalogId), cancellationToken);

    /// <summary>Validates a complete catalog without mutation.</summary>
    [McpServerTool(Name = "localization.catalogs.validate", Title = "Validate localization catalog", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Validate a provider-neutral localization catalog and return stable ICU, locale, scope, and fallback diagnostics.")]
    public static ValueTask<IReadOnlyList<LocalizationDiagnostic>> ValidateAsync(LocalizationCatalogDefinition catalog, ILocalizationCatalogManagement management, CancellationToken cancellationToken) => management.ValidateAsync(catalog, cancellationToken);

    /// <summary>Creates a catalog draft.</summary>
    [McpServerTool(Name = "localization.catalogs.create", Title = "Create localization catalog", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Create revision 1 of a localization catalog with exact idempotency and principal-derived audit identity.")]
    public static async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> CreateAsync(LocalizationCatalogDefinition catalog, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationCatalogManagement management, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await management.CreateAsync(catalog, new LocalizationMutationContext(idempotencyKey, null, actor, requestedAt), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Replaces an editable catalog.</summary>
    [McpServerTool(Name = "localization.catalogs.replace", Title = "Replace localization catalog", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Replace an editable catalog with its next draft revision using the exact opaque version.")]
    public static async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ReplaceAsync(LocalizationCatalogDefinition catalog, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationCatalogManagement management, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await management.ReplaceAsync(catalog, Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Previews one bounded import without mutation.</summary>
    [McpServerTool(Name = "localization.imports.preview", Title = "Preview localization import", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Decode, parse, validate, and preview one bounded hash-aware localization import without applying it.")]
    public static ValueTask<LocalizationImportPreview> PreviewImportAsync(string catalogId, LocalizationImportFormat format, string contentBase64, LocalizationMergePolicy mergePolicy, LocalizationScope? scope, IReadOnlyDictionary<string, string>? mapping, string? sourceName, string? contentSha256, LocalizationToolTransferOptions limits, ILocalizationCatalogManagement management, CancellationToken cancellationToken)
    {
        var content = Decode(contentBase64, limits.MaximumImportBytes);
        return management.PreviewImportAsync(new LocalizationCatalogId(catalogId), new LocalizationImportRequest(format, content, mergePolicy, scope, mapping, sourceName, contentSha256), cancellationToken);
    }

    /// <summary>Applies the exact stored import preview.</summary>
    [McpServerTool(Name = "localization.imports.apply", Title = "Apply localization import", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Apply an exact stored localization import preview using its preview ID and current catalog version.")]
    public static async ValueTask<LocalizationMutationResult<LocalizationCatalogDefinition>> ApplyImportAsync(string catalogId, string previewId, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationCatalogManagement management, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await management.ApplyImportAsync(new LocalizationCatalogId(catalogId), previewId, Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Exports selected localization content through bounded base64.</summary>
    [McpServerTool(Name = "localization.exports.create", Title = "Export localization catalog", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Export selected catalog scopes and locales through a registered deterministic format adapter.")]
    public static async ValueTask<LocalizationToolExport?> ExportAsync(string catalogId, LocalizationImportFormat format, LocalizationScope? scope, string[]? languageTags, IReadOnlyDictionary<string, string>? mapping, string? suggestedBaseName, LocalizationToolTransferOptions limits, ILocalizationCatalogQueries queries, IEnumerable<ILocalizationExportFormatAdapter> adapters, CancellationToken cancellationToken)
    {
        var document = await queries.GetCatalogAsync(new LocalizationCatalogId(catalogId), cancellationToken).ConfigureAwait(false);
        if (document is null) return null;
        var adapter = adapters.SingleOrDefault(item => item.Format == format) ?? throw new InvalidOperationException($"No localization export adapter is registered for '{format}'.");
        var exported = await adapter.ExportAsync(new LocalizationExportRequest(format, document.Catalog, scope, languageTags, mapping, suggestedBaseName), cancellationToken).ConfigureAwait(false);
        if (exported.Content.Length > limits.MaximumExportBytes) throw new InvalidOperationException("The localization export exceeds the configured MCP transfer limit.");
        return new LocalizationToolExport(exported.Format, Convert.ToBase64String(exported.Content.Span), exported.MediaType, exported.SuggestedFileName, exported.ContentSha256);
    }

    /// <summary>Submits one exact catalog revision for review.</summary>
    [McpServerTool(Name = "localization.lifecycle.review", Title = "Submit localization for review", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Submit an exact validated localization catalog revision for authorized review.")]
    public static ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> ReviewAsync(string catalogId, long revision, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken) => StateMutationAsync(false, catalogId, revision, expectedVersion, idempotencyKey, requestedAt, principal, actors, lifecycle, cancellationToken);

    /// <summary>Approves one reviewed catalog revision.</summary>
    [McpServerTool(Name = "localization.lifecycle.approve", Title = "Approve localization", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Approve an exact reviewed localization catalog revision without publishing it.")]
    public static ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> ApproveAsync(string catalogId, long revision, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken) => StateMutationAsync(true, catalogId, revision, expectedVersion, idempotencyKey, requestedAt, principal, actors, lifecycle, cancellationToken);

    /// <summary>Publishes one approved catalog revision.</summary>
    [McpServerTool(Name = "localization.lifecycle.publish", Title = "Publish localization", ReadOnly = false, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Publish an exact approved localization catalog revision as an immutable release.")]
    public static async ValueTask<LocalizationMutationResult<LocalizationRelease>> PublishAsync(string catalogId, long revision, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await lifecycle.PublishAsync(new LocalizationCatalogId(catalogId), new LocalizationRevision(revision), Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Gets one immutable localization release.</summary>
    [McpServerTool(Name = "localization.releases.get", Title = "Get localization release", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one immutable localization release by stable identifier.")]
    public static ValueTask<LocalizationRelease?> GetReleaseAsync(string releaseId, ILocalizationCatalogQueries queries, CancellationToken cancellationToken) => queries.GetReleaseAsync(new LocalizationReleaseId(releaseId), cancellationToken);

    /// <summary>Compares two immutable localization releases.</summary>
    [McpServerTool(Name = "localization.releases.compare", Title = "Compare localization releases", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Compare two immutable localization releases and return deterministic locale and message differences.")]
    public static async ValueTask<LocalizationReleaseDifference?> CompareReleasesAsync(string baselineReleaseId, string candidateReleaseId, ILocalizationCatalogQueries queries, ILocalizationReleaseDiffer differ, CancellationToken cancellationToken)
    {
        var baseline = await queries.GetReleaseAsync(new LocalizationReleaseId(baselineReleaseId), cancellationToken).ConfigureAwait(false);
        var candidate = await queries.GetReleaseAsync(new LocalizationReleaseId(candidateReleaseId), cancellationToken).ConfigureAwait(false);
        return baseline is null || candidate is null ? null : await differ.CompareAsync(baseline, candidate, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Retires a localization release without deleting it.</summary>
    [McpServerTool(Name = "localization.releases.retire", Title = "Retire localization release", ReadOnly = false, Destructive = true, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Retire an immutable localization release while preserving messages and audit evidence.")]
    public static async ValueTask<LocalizationMutationResult<LocalizationRelease>> RetireAsync(string releaseId, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        return await lifecycle.RetireAsync(new LocalizationReleaseId(releaseId), Mutation(idempotencyKey, expectedVersion, requestedAt, actor), cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Resolves one runtime message through immutable fallback policy.</summary>
    [McpServerTool(Name = "localization.runtime.resolve", Title = "Resolve localized message", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Resolve one immutable localized message through the catalog fallback chain.")]
    public static ValueTask<LocalizationResolution?> ResolveAsync(LocalizationScope scope, string key, string languageTag, ILocalizationRuntime runtime, CancellationToken cancellationToken) => runtime.ResolveAsync(scope, key, languageTag, cancellationToken);

    /// <summary>Gets one runtime bundle for a scope and language.</summary>
    [McpServerTool(Name = "localization.runtime.bundle", Title = "Get localization bundle", ReadOnly = true, Destructive = false, Idempotent = true, OpenWorld = false, UseStructuredContent = true)]
    [Description("Get one immutable localized message bundle for a structured scope and language.")]
    public static ValueTask<LocalizationBundle?> BundleAsync(LocalizationScope scope, string languageTag, ILocalizationRuntime runtime, CancellationToken cancellationToken) => runtime.GetBundleAsync(scope, languageTag, cancellationToken);

    /// <summary>Runs review or approval with a principal-derived actor.</summary>
    private static async ValueTask<LocalizationMutationResult<LocalizationLifecycleState>> StateMutationAsync(bool approve, string catalogId, long revision, string expectedVersion, string idempotencyKey, DateTimeOffset requestedAt, ClaimsPrincipal principal, ILocalizationToolActorProvider actors, ILocalizationReleaseLifecycle lifecycle, CancellationToken cancellationToken)
    {
        var actor = await actors.GetActorAsync(principal, cancellationToken).ConfigureAwait(false);
        var mutation = Mutation(idempotencyKey, expectedVersion, requestedAt, actor);
        return approve ? await lifecycle.ApproveAsync(new LocalizationCatalogId(catalogId), new LocalizationRevision(revision), mutation, cancellationToken).ConfigureAwait(false) : await lifecycle.SubmitForReviewAsync(new LocalizationCatalogId(catalogId), new LocalizationRevision(revision), mutation, cancellationToken).ConfigureAwait(false);
    }

    /// <summary>Creates an optimistic mutation with trusted identity.</summary>
    private static LocalizationMutationContext Mutation(string key, string version, DateTimeOffset requestedAt, LocalizationAuditActor actor) => new(key, new LocalizationConcurrencyToken(version), actor, requestedAt);

    /// <summary>Decodes one bounded base64 input without allowing oversized allocation.</summary>
    private static byte[] Decode(string content, int maximumBytes)
    {
        if (maximumBytes is < 1 or > 67_108_864) throw new InvalidOperationException("The localization MCP import limit is invalid.");
        var maximumEncodedLength = (((long)maximumBytes + 2L) / 3L) * 4L;
        if (string.IsNullOrWhiteSpace(content) || content.Length > maximumEncodedLength) throw new InvalidOperationException("Localization import content is empty or exceeds the configured limit.");
        try
        {
            var bytes = Convert.FromBase64String(content);
            if (bytes.Length > maximumBytes) throw new InvalidOperationException("Localization import content exceeds the configured limit.");
            return bytes;
        }
        catch (FormatException) { throw new InvalidOperationException("Localization import content is not valid base64."); }
    }
}
