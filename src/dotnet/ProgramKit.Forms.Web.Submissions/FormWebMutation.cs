namespace ProgramKit.Forms.Web.Submissions;

/// <summary>Carries client command identity and concurrency but never caller identity.</summary>
public sealed record FormWebMutation(string IdempotencyKey, string? ExpectedVersion, DateTimeOffset RequestedAt, string? CorrelationId = null);
