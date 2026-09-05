using Microsoft.AspNetCore.Authorization;

namespace ProgramKit.Authentication.Assurance;

/// <summary>Applies assurance evaluation to ASP.NET authorization.</summary>
internal sealed class AssuranceAuthorizationHandler(IAssuranceEvaluator evaluator)
    : AuthorizationHandler<AssuranceRequirement>
{
    /// <inheritdoc />
    protected override Task HandleRequirementAsync(
        AuthorizationHandlerContext context,
        AssuranceRequirement requirement)
    {
        if (evaluator.Evaluate(context.User, requirement.Policy).Satisfied)
        {
            context.Succeed(requirement);
        }
        return Task.CompletedTask;
    }
}
