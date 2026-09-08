namespace Orbyss.Forms;

/// <summary>Bounds canonical form data and operational queries.</summary>
public sealed record FormSubmissionOptions(
    int MaximumDataBytes = 1_048_576,
    int MaximumQuerySize = 1000);
