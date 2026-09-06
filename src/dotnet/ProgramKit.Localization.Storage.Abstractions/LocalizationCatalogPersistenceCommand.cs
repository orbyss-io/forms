namespace ProgramKit.Localization;

/// <summary>Requests one atomic, optimistic, durably idempotent catalog write.</summary>
public sealed record LocalizationCatalogPersistenceCommand(
    string Operation,
    string Fingerprint,
    LocalizationCatalogDefinition Catalog,
    LocalizationMutationContext Mutation,
    bool RequireAbsent = false);
