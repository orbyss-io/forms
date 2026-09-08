namespace Orbyss.Forms;

/// <summary>Represents an immutable, accepted form release served to runtime consumers.</summary>
public sealed record FormRelease(
    FormReleaseId Id,
    FormCandidate Candidate,
    DateTimeOffset PublishedAt,
    FormAuditActor PublishedBy,
    IReadOnlyList<string> Evidence,
    bool Retired = false);
