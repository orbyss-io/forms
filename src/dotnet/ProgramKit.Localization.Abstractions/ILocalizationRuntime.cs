namespace ProgramKit.Localization;

/// <summary>Resolves immutable localized messages and bundles for application runtimes.</summary>
public interface ILocalizationRuntime
{
    /// <summary>Resolves one message through the catalog's explicit fallback chain.</summary>
    ValueTask<LocalizationResolution?> ResolveAsync(
        LocalizationScope scope,
        string key,
        string languageTag,
        CancellationToken cancellationToken = default);

    /// <summary>Gets the current immutable message bundle for a scope and locale.</summary>
    ValueTask<LocalizationBundle?> GetBundleAsync(
        LocalizationScope scope,
        string languageTag,
        CancellationToken cancellationToken = default);
}
