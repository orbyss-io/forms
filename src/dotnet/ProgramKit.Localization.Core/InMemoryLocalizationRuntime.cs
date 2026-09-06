using System.Security.Cryptography;
using System.Text;

namespace ProgramKit.Localization;

/// <summary>Resolves immutable localization releases without persistence or framework dependencies.</summary>
public sealed class InMemoryLocalizationRuntime : ILocalizationRuntime
{
    /// <summary>Holds the immutable release exposed by this runtime instance.</summary>
    private readonly LocalizationRelease release;

    /// <summary>Indexes locale declarations case-insensitively for bounded fallback traversal.</summary>
    private readonly IReadOnlyDictionary<string, LocaleDefinition> locales;

    /// <summary>Indexes immutable message entries by structured scope, key, and locale.</summary>
    private readonly IReadOnlyDictionary<(LocalizationScope Scope, string Key, string Locale), LocalizationReleaseEntry> entries;

    /// <summary>Initializes a runtime over one immutable localization release.</summary>
    public InMemoryLocalizationRuntime(LocalizationRelease release)
    {
        ArgumentNullException.ThrowIfNull(release);
        this.release = release;
        locales = release.Locales.ToDictionary(locale => locale.LanguageTag, StringComparer.OrdinalIgnoreCase);
        entries = release.Entries.ToDictionary(
            entry => (entry.Scope, entry.Key, entry.LanguageTag.ToUpperInvariant()),
            entry => entry);
    }

    /// <inheritdoc />
    public ValueTask<LocalizationResolution?> ResolveAsync(
        LocalizationScope scope,
        string key,
        string languageTag,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(scope);
        ArgumentException.ThrowIfNullOrWhiteSpace(key);
        ArgumentException.ThrowIfNullOrWhiteSpace(languageTag);
        cancellationToken.ThrowIfCancellationRequested();
        return ValueTask.FromResult(Resolve(scope, key, languageTag));
    }

    /// <inheritdoc />
    public ValueTask<LocalizationBundle?> GetBundleAsync(
        LocalizationScope scope,
        string languageTag,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(scope);
        ArgumentException.ThrowIfNullOrWhiteSpace(languageTag);
        cancellationToken.ThrowIfCancellationRequested();
        var keys = release.Entries
            .Where(entry => entry.Scope == scope)
            .Select(entry => entry.Key)
            .Distinct(StringComparer.Ordinal)
            .OrderBy(key => key, StringComparer.Ordinal)
            .ToArray();
        if (keys.Length == 0)
        {
            return ValueTask.FromResult<LocalizationBundle?>(null);
        }

        var messages = new SortedDictionary<string, string>(StringComparer.Ordinal);
        var resolvedLocales = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach (var key in keys)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var resolution = Resolve(scope, key, languageTag);
            if (resolution is not null)
            {
                messages[key] = resolution.Pattern;
                resolvedLocales.Add(resolution.ResolvedLanguageTag);
            }
        }

        if (messages.Count == 0)
        {
            return ValueTask.FromResult<LocalizationBundle?>(null);
        }

        var representativeLocale = resolvedLocales.Count == 1 ? resolvedLocales.Single() : languageTag;
        var direction = locales.TryGetValue(representativeLocale, out var locale)
            ? locale.Direction
            : TextDirection.LeftToRight;
        var hashInput = string.Join("\n", messages.Select(item => item.Key + "=" + item.Value));
        var bundle = new LocalizationBundle(
            release.Id,
            scope,
            languageTag,
            representativeLocale,
            direction,
            messages,
            Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(hashInput))));
        return ValueTask.FromResult<LocalizationBundle?>(bundle);
    }

    /// <summary>Resolves one entry through the requested locale, explicit fallbacks, and source locale.</summary>
    private LocalizationResolution? Resolve(LocalizationScope scope, string key, string languageTag)
    {
        foreach (var locale in FallbackChain(languageTag))
        {
            if (entries.TryGetValue((scope, key, locale.ToUpperInvariant()), out var entry))
            {
                return new LocalizationResolution(
                    key,
                    scope,
                    languageTag,
                    entry.LanguageTag,
                    entry.Direction,
                    entry.Pattern,
                    !string.Equals(languageTag, entry.LanguageTag, StringComparison.OrdinalIgnoreCase));
            }
        }

        return null;
    }

    /// <summary>Enumerates each locale at most once to remain safe even for externally built releases.</summary>
    private IEnumerable<string> FallbackChain(string requested)
    {
        var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var current = requested;
        while (visited.Add(current))
        {
            yield return current;
            if (!locales.TryGetValue(current, out var locale) || locale.FallbackLanguageTag is not { } fallback)
            {
                break;
            }

            current = fallback;
        }

        if (visited.Add(release.SourceLocale))
        {
            yield return release.SourceLocale;
        }
    }
}
