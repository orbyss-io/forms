namespace Orbyss.Localization.Web.Management;

/// <summary>Supplies client command identity and concurrency data while server claims supply attribution.</summary>
public sealed record LocalizationWebMutation(
    string IdempotencyKey,
    string? ExpectedVersion,
    DateTimeOffset RequestedAt,
    string? CorrelationId = null);
