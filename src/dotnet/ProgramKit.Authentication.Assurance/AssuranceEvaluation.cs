namespace ProgramKit.Authentication.Assurance;

/// <summary>Reports whether a principal satisfies one named assurance policy.</summary>
/// <param name="Satisfied">Whether all configured evidence requirements passed.</param>
/// <param name="FailureCode">Stable failure code, or null when satisfied.</param>
/// <param name="AcceptedAcrValues">Exact ACR values an interactive client may request for step-up.</param>
/// <param name="MaximumAuthenticationAgeSeconds">Maximum authentication age requested by the policy.</param>
public sealed record AssuranceEvaluation(
    bool Satisfied,
    string? FailureCode,
    IReadOnlyList<string> AcceptedAcrValues,
    int? MaximumAuthenticationAgeSeconds);
