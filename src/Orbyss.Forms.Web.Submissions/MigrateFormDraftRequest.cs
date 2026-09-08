namespace Orbyss.Forms.Web.Submissions;

/// <summary>Selects a newer release and optional trusted migration for one draft.</summary>
public sealed record MigrateFormDraftRequest(string TargetReleaseId, string? MigrationId, FormWebMutation Mutation);
