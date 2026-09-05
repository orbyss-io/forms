using System.Security.Claims;

namespace ProgramKit.Authentication.Assurance;

/// <summary>Evaluates standard assurance claims without depending on an identity-provider product.</summary>
public interface IAssuranceEvaluator
{
    /// <summary>Evaluates one named policy against an already validated principal.</summary>
    AssuranceEvaluation Evaluate(ClaimsPrincipal principal, string policy);
}
