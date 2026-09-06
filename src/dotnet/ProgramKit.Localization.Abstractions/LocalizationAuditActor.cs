namespace ProgramKit.Localization;

/// <summary>Identifies the human, service, or governed tool requesting a localization mutation.</summary>
public sealed record LocalizationAuditActor(string Id, string Kind, string? DisplayName = null);
