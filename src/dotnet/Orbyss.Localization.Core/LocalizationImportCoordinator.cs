using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Orbyss.Localization;

/// <summary>Creates hash-bound import previews and applies only the exact validated proposal.</summary>
public sealed class LocalizationImportCoordinator
{
    /// <summary>Adapters selected explicitly by supported interchange format.</summary>
    private readonly IReadOnlyDictionary<LocalizationImportFormat, ILocalizationImportFormatAdapter> adapters;
    /// <summary>Semantic catalog validator applied after an import is materialized.</summary>
    private readonly ILocalizationCatalogValidator validator;
    /// <summary>Coordinator retention and resource settings.</summary>
    private readonly LocalizationImportCoordinatorOptions options;
    /// <summary>Hash-bound import proposals awaiting an apply command.</summary>
    private readonly ConcurrentDictionary<string, StoredPreview> previews = new(StringComparer.Ordinal);
    /// <summary>Insertion order used to evict bounded preview state.</summary>
    private readonly ConcurrentQueue<string> previewOrder = new();
    /// <summary>Completed applications retained for command idempotency.</summary>
    private readonly ConcurrentDictionary<string, StoredApplication> applications = new(StringComparer.Ordinal);
    /// <summary>Stable serializer settings used to derive catalog concurrency tokens.</summary>
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web);

    /// <summary>Initializes the coordinator from explicitly registered format adapters.</summary>
    public LocalizationImportCoordinator(
        IEnumerable<ILocalizationImportFormatAdapter> adapters,
        ILocalizationCatalogValidator validator,
        LocalizationImportCoordinatorOptions? options = null)
    {
        ArgumentNullException.ThrowIfNull(adapters);
        ArgumentNullException.ThrowIfNull(validator);
        this.adapters = adapters.ToDictionary(adapter => adapter.Format);
        this.validator = validator;
        this.options = options ?? new LocalizationImportCoordinatorOptions();
        if (this.options.MaximumStoredPreviews < 1) throw new ArgumentOutOfRangeException(nameof(options));
    }

    /// <summary>Parses and compares untrusted content without changing the supplied catalog.</summary>
    public async ValueTask<LocalizationImportPreview> PreviewAsync(
        LocalizationCatalogDefinition catalog,
        LocalizationImportRequest request,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalog);
        ArgumentNullException.ThrowIfNull(request);
        if (!adapters.TryGetValue(request.Format, out var adapter)) throw new InvalidOperationException($"No localization adapter is registered for '{request.Format}'.");
        var parsed = await adapter.ParseAsync(request, cancellationToken).ConfigureAwait(false);
        var diagnostics = parsed.Diagnostics.ToList();
        var entries = NormalizeEntries(parsed.Entries, catalog, diagnostics);
        var changes = Compare(catalog, entries, request.MergePolicy);
        var contentHash = Convert.ToHexStringLower(SHA256.HashData(request.Content.Span));
        var previewId = Hash($"{catalog.Id.Value}\n{catalog.Revision.Value}\n{contentHash}\n{request.MergePolicy}\n{ScopeIdentity(request.Scope)}\n{CanonicalMapping(request.Mapping)}");
        var preview = new LocalizationImportPreview(previewId, contentHash, catalog.Revision, request.MergePolicy, changes, diagnostics);
        previews[previewId] = new StoredPreview(preview, entries);
        previewOrder.Enqueue(previewId);
        while (previews.Count > options.MaximumStoredPreviews && previewOrder.TryDequeue(out var expired)) previews.TryRemove(expired, out _);
        return preview;
    }

    /// <summary>Applies a stored non-conflicting preview with optimistic concurrency and idempotent replay.</summary>
    public async ValueTask<LocalizationMutationResult<LocalizationImportApplicationResult>> ApplyAsync(
        LocalizationCatalogDefinition catalog,
        string previewId,
        LocalizationMutationContext mutation,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalog);
        ArgumentNullException.ThrowIfNull(mutation);
        if (!previews.TryGetValue(previewId, out var stored)) throw new InvalidOperationException("The localization import preview is missing or expired.");
        var fingerprint = Hash($"{previewId}\n{catalog.Id.Value}\n{catalog.Revision.Value}\n{mutation.Actor.Id}\n{mutation.RequestedAt:O}");
        if (applications.TryGetValue(mutation.IdempotencyKey, out var replay))
        {
            if (!string.Equals(replay.Fingerprint, fingerprint, StringComparison.Ordinal)) throw new InvalidOperationException("The localization idempotency key was reused for a different import application.");
            return replay.Result with { WasReplay = true };
        }
        if (stored.Preview.BasedOnRevision != catalog.Revision) throw new InvalidOperationException("The localization catalog changed after the import preview was created.");
        var currentVersion = CreateConcurrencyToken(catalog);
        if (mutation.ExpectedVersion is not null && !string.Equals(mutation.ExpectedVersion.Value, currentVersion.Value, StringComparison.Ordinal)) throw new InvalidOperationException("The localization catalog concurrency token does not match.");
        if (stored.Preview.Diagnostics.Any(item => item.Severity == LocalizationDiagnosticSeverity.Error) || stored.Preview.Changes.Any(change => change.Kind == LocalizationImportChangeKind.Conflict)) throw new InvalidOperationException("The localization import preview contains blocking diagnostics or conflicts.");
        var updated = ApplyEntries(catalog, stored);
        var validation = await validator.ValidateAsync(updated, cancellationToken).ConfigureAwait(false);
        if (validation.Any(item => item.Severity == LocalizationDiagnosticSeverity.Error)) throw new InvalidOperationException("The imported localization catalog failed semantic validation.");
        var result = new LocalizationMutationResult<LocalizationImportApplicationResult>(
            new LocalizationImportApplicationResult(updated, stored.Preview),
            CreateConcurrencyToken(updated),
            false);
        if (!applications.TryAdd(mutation.IdempotencyKey, new StoredApplication(fingerprint, result))) return await ApplyAsync(catalog, previewId, mutation, cancellationToken).ConfigureAwait(false);
        return result;
    }

    /// <summary>Creates the deterministic opaque token used by the in-process import coordinator.</summary>
    public static LocalizationConcurrencyToken CreateConcurrencyToken(LocalizationCatalogDefinition catalog)
    {
        ArgumentNullException.ThrowIfNull(catalog);
        return new LocalizationConcurrencyToken(Hash(JsonSerializer.Serialize(catalog, JsonOptions)));
    }

    /// <summary>Normalizes parsed entries and emits catalog-aware identity and locale diagnostics.</summary>
    private static IReadOnlyList<LocalizationImportEntry> NormalizeEntries(
        IReadOnlyList<LocalizationImportEntry> entries,
        LocalizationCatalogDefinition catalog,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        var locales = catalog.Locales.Select(locale => locale.LanguageTag).ToHashSet(StringComparer.OrdinalIgnoreCase);
        var identities = new HashSet<string>(StringComparer.Ordinal);
        var result = new List<LocalizationImportEntry>();
        foreach (var entry in entries)
        {
            var identity = $"{ScopeIdentity(entry.Scope)}:{entry.Key}:{entry.LanguageTag.ToUpperInvariant()}";
            if (!identities.Add(identity)) { diagnostics.Add(Error("PKLI601", "The import repeats a key, scope, and locale identity.", entry)); continue; }
            if (!locales.Contains(entry.LanguageTag)) { diagnostics.Add(Error("PKLI602", "The import locale is not declared by the catalog.", entry)); continue; }
            if (string.IsNullOrWhiteSpace(entry.Key) || string.IsNullOrWhiteSpace(entry.Pattern)) { diagnostics.Add(Error("PKLI603", "Imported keys and patterns are required.", entry)); continue; }
            var message = FindMessage(catalog.Messages, entry.Scope, entry.Key);
            if (message is null && string.IsNullOrWhiteSpace(entry.SourcePattern)) { diagnostics.Add(Error("PKLI604", "A new imported message requires its source pattern.", entry)); continue; }
            if (message is not null && entry.SourcePattern is not null && !string.Equals(entry.SourcePattern, message.SourcePattern, StringComparison.Ordinal)) { diagnostics.Add(Error("PKLI605", "The imported source pattern conflicts with the existing message contract.", entry)); continue; }
            if (message is not null && entry.Arguments is not null && !entry.Arguments.SequenceEqual(message.Arguments)) { diagnostics.Add(Error("PKLI606", "The imported argument definitions conflict with the existing message contract.", entry)); continue; }
            result.Add(entry);
        }
        return result;
    }

    /// <summary>Produces the deterministic add, replace, preserve, remove, and conflict proposal.</summary>
    private static IReadOnlyList<LocalizationImportChange> Compare(LocalizationCatalogDefinition catalog, IReadOnlyList<LocalizationImportEntry> entries, LocalizationMergePolicy policy)
    {
        var changes = new List<LocalizationImportChange>();
        foreach (var entry in entries)
        {
            var message = FindMessage(catalog.Messages, entry.Scope, entry.Key);
            var existing = message?.Values.FirstOrDefault(value => string.Equals(value.LanguageTag, entry.LanguageTag, StringComparison.OrdinalIgnoreCase));
            var kind = existing is null ? LocalizationImportChangeKind.Add
                : string.Equals(existing.Pattern, entry.Pattern, StringComparison.Ordinal) ? LocalizationImportChangeKind.Preserve
                : policy == LocalizationMergePolicy.AddOnly ? LocalizationImportChangeKind.Conflict
                : policy == LocalizationMergePolicy.PreserveExisting ? LocalizationImportChangeKind.Preserve
                : LocalizationImportChangeKind.Replace;
            changes.Add(new LocalizationImportChange(entry.Key, entry.LanguageTag, entry.Scope, kind, existing?.Pattern, entry.Pattern));
        }
        if (policy == LocalizationMergePolicy.ReplaceScope)
        {
            var imported = entries.Select(entry => $"{ScopeIdentity(entry.Scope)}:{entry.Key}:{entry.LanguageTag.ToUpperInvariant()}").ToHashSet(StringComparer.Ordinal);
            var scopes = entries.Select(entry => ScopeIdentity(entry.Scope)).ToHashSet(StringComparer.Ordinal);
            foreach (var message in catalog.Messages.Where(message => scopes.Contains(ScopeIdentity(message.Scope))))
            foreach (var value in message.Values)
            if (!imported.Contains($"{ScopeIdentity(message.Scope)}:{message.Key}:{value.LanguageTag.ToUpperInvariant()}")) changes.Add(new LocalizationImportChange(message.Key, value.LanguageTag, message.Scope, LocalizationImportChangeKind.Remove, value.Pattern, null));
        }
        return changes.OrderBy(change => ScopeIdentity(change.Scope), StringComparer.Ordinal).ThenBy(change => change.Key, StringComparer.Ordinal).ThenBy(change => change.LanguageTag, StringComparer.OrdinalIgnoreCase).ToArray();
    }

    /// <summary>Materializes the exact stored proposal as the next draft catalog revision.</summary>
    private static LocalizationCatalogDefinition ApplyEntries(LocalizationCatalogDefinition catalog, StoredPreview stored)
    {
        var messages = catalog.Messages.ToList();
        if (stored.Preview.MergePolicy == LocalizationMergePolicy.ReplaceScope)
        {
            foreach (var removal in stored.Preview.Changes.Where(change => change.Kind == LocalizationImportChangeKind.Remove))
            {
                var index = messages.FindIndex(message => message.Scope == removal.Scope && string.Equals(message.Key, removal.Key, StringComparison.Ordinal));
                if (index >= 0) messages[index] = messages[index] with { Values = messages[index].Values.Where(value => !string.Equals(value.LanguageTag, removal.LanguageTag, StringComparison.OrdinalIgnoreCase)).ToArray() };
            }
        }
        foreach (var entry in stored.Entries)
        {
            var change = stored.Preview.Changes.Single(item => item.Scope == entry.Scope && item.Key == entry.Key && string.Equals(item.LanguageTag, entry.LanguageTag, StringComparison.OrdinalIgnoreCase));
            if (change.Kind is LocalizationImportChangeKind.Preserve) continue;
            var index = messages.FindIndex(message => message.Scope == entry.Scope && string.Equals(message.Key, entry.Key, StringComparison.Ordinal));
            if (index < 0)
            {
                if (string.IsNullOrWhiteSpace(entry.SourcePattern)) throw new InvalidOperationException($"New message '{entry.Key}' requires a source pattern.");
                messages.Add(new LocalizationMessageDefinition(entry.Key, entry.Scope, entry.SourcePattern, entry.Arguments ?? [], [Value(entry)], entry.Description, entry.Context));
            }
            else
            {
                var message = messages[index];
                var values = message.Values.Where(value => !string.Equals(value.LanguageTag, entry.LanguageTag, StringComparison.OrdinalIgnoreCase)).Append(Value(entry)).ToArray();
                messages[index] = message with { Values = values };
            }
        }
        return catalog with { Revision = new LocalizationRevision(catalog.Revision.Value + 1), State = LocalizationLifecycleState.Draft, Messages = messages.OrderBy(message => ScopeIdentity(message.Scope), StringComparer.Ordinal).ThenBy(message => message.Key, StringComparer.Ordinal).ToArray() };
    }

    /// <summary>Projects an imported value into draft workflow state.</summary>
    private static LocalizedValue Value(LocalizationImportEntry entry) => new(entry.LanguageTag, entry.Pattern, LocalizationValueState.Draft, entry.Provenance);

    /// <summary>Finds one provider-neutral message by structured scope and ordinal key.</summary>
    private static LocalizationMessageDefinition? FindMessage(IEnumerable<LocalizationMessageDefinition> messages, LocalizationScope scope, string key) => messages.FirstOrDefault(message => message.Scope == scope && string.Equals(message.Key, key, StringComparison.Ordinal));

    /// <summary>Creates an entry-scoped blocking import diagnostic.</summary>
    private static LocalizationDiagnostic Error(string code, string message, LocalizationImportEntry entry) => new(code, LocalizationDiagnosticSeverity.Error, message, entry.Key, entry.LanguageTag);

    /// <summary>Creates a stable structured-scope identity for ordering and comparison.</summary>
    private static string ScopeIdentity(LocalizationScope? scope) => scope is null ? string.Empty : $"{scope.Kind}:{scope.ParentResourceId}:{scope.ResourceId}";

    /// <summary>Canonicalizes column and format mappings independently of dictionary order.</summary>
    private static string CanonicalMapping(IReadOnlyDictionary<string, string>? mapping) => mapping is null ? string.Empty : string.Join("\n", mapping.OrderBy(item => item.Key, StringComparer.Ordinal).Select(item => $"{item.Key}={item.Value}"));

    /// <summary>Creates a lowercase SHA-256 identity from UTF-8 text.</summary>
    private static string Hash(string value) => Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(value)));
}
