namespace Orbyss.Forms.Web.Management;

/// <summary>Accepts untrusted command metadata while actor identity comes from authentication.</summary>
public sealed record FormWebMutation(string IdempotencyKey, string? ExpectedVersion, DateTimeOffset RequestedAt, string? CorrelationId = null);
