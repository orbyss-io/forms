namespace Orbyss.Localization;

/// <summary>Compares locale policies and scoped message entries by stable provider-neutral identity.</summary>
public sealed class DefaultLocalizationReleaseDiffer : ILocalizationReleaseDiffer
{
    /// <inheritdoc />
    public ValueTask<LocalizationReleaseDifference> CompareAsync(
        LocalizationRelease baseline,
        LocalizationRelease candidate,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(baseline);
        ArgumentNullException.ThrowIfNull(candidate);
        cancellationToken.ThrowIfCancellationRequested();
        if (baseline.CatalogId != candidate.CatalogId) throw new ArgumentException("Localization release diff requires releases from the same catalog.", nameof(candidate));

        var localeDifferences = CompareLocales(baseline.Locales, candidate.Locales);
        var entryDifferences = CompareEntries(baseline.Entries, candidate.Entries);
        return ValueTask.FromResult(new LocalizationReleaseDifference(
            baseline.Id,
            candidate.Id,
            !string.Equals(baseline.SourceLocale, candidate.SourceLocale, StringComparison.OrdinalIgnoreCase),
            localeDifferences,
            entryDifferences));
    }

    /// <summary>Compares locale direction, fallback, and publication policy by language tag.</summary>
    private static IReadOnlyList<LocalizationLocaleDifference> CompareLocales(
        IReadOnlyList<LocaleDefinition> baseline,
        IReadOnlyList<LocaleDefinition> candidate)
    {
        var before = baseline.ToDictionary(locale => locale.LanguageTag, StringComparer.OrdinalIgnoreCase);
        var after = candidate.ToDictionary(locale => locale.LanguageTag, StringComparer.OrdinalIgnoreCase);
        return before.Keys.Concat(after.Keys).Distinct(StringComparer.OrdinalIgnoreCase)
            .OrderBy(languageTag => languageTag, StringComparer.OrdinalIgnoreCase)
            .Select(languageTag => (LanguageTag: languageTag, Before: before.GetValueOrDefault(languageTag), After: after.GetValueOrDefault(languageTag)))
            .Where(item => !LocaleEquals(item.Before, item.After))
            .Select(item => new LocalizationLocaleDifference(
                item.Before is null ? LocalizationDifferenceKind.Added : item.After is null ? LocalizationDifferenceKind.Removed : LocalizationDifferenceKind.Changed,
                item.LanguageTag,
                item.Before,
                item.After))
            .ToArray();
    }

    /// <summary>Compares patterns, direction, and typed arguments by scope, key, and language tag.</summary>
    private static IReadOnlyList<LocalizationEntryDifference> CompareEntries(
        IReadOnlyList<LocalizationReleaseEntry> baseline,
        IReadOnlyList<LocalizationReleaseEntry> candidate)
    {
        var before = baseline.ToDictionary(EntryIdentity, StringComparer.Ordinal);
        var after = candidate.ToDictionary(EntryIdentity, StringComparer.Ordinal);
        return before.Keys.Concat(after.Keys).Distinct(StringComparer.Ordinal)
            .OrderBy(identity => identity, StringComparer.Ordinal)
            .Select(identity => (Before: before.GetValueOrDefault(identity), After: after.GetValueOrDefault(identity)))
            .Where(item => !EntryEquals(item.Before, item.After))
            .Select(item =>
            {
                var value = item.After ?? item.Before!;
                return new LocalizationEntryDifference(
                    item.Before is null ? LocalizationDifferenceKind.Added : item.After is null ? LocalizationDifferenceKind.Removed : LocalizationDifferenceKind.Changed,
                    value.Key,
                    value.Scope,
                    value.LanguageTag,
                    item.Before,
                    item.After);
            })
            .ToArray();
    }

    /// <summary>Creates the stable scoped identity of one localized release entry.</summary>
    private static string EntryIdentity(LocalizationReleaseEntry entry) =>
        $"{entry.Scope.Kind}:{entry.Scope.ParentResourceId}:{entry.Scope.ResourceId}:{entry.Key}:{entry.LanguageTag.ToUpperInvariant()}";

    /// <summary>Compares locale policy using case-insensitive BCP 47 identities.</summary>
    private static bool LocaleEquals(LocaleDefinition? before, LocaleDefinition? after) =>
        before is not null && after is not null
        && string.Equals(before.LanguageTag, after.LanguageTag, StringComparison.OrdinalIgnoreCase)
        && before.Direction == after.Direction
        && string.Equals(before.FallbackLanguageTag, after.FallbackLanguageTag, StringComparison.OrdinalIgnoreCase)
        && before.RequiredForPublication == after.RequiredForPublication;

    /// <summary>Compares all entry content while treating argument lists as semantic sequences.</summary>
    private static bool EntryEquals(LocalizationReleaseEntry? before, LocalizationReleaseEntry? after) =>
        before is not null && after is not null
        && string.Equals(before.Key, after.Key, StringComparison.Ordinal)
        && before.Scope == after.Scope
        && string.Equals(before.LanguageTag, after.LanguageTag, StringComparison.OrdinalIgnoreCase)
        && before.Direction == after.Direction
        && string.Equals(before.Pattern, after.Pattern, StringComparison.Ordinal)
        && before.Arguments.SequenceEqual(after.Arguments);
}
