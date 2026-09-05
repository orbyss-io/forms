using CShells;
using CShells.Features;
using Microsoft.AspNetCore.Authorization;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.DependencyInjection.Extensions;
using Microsoft.Extensions.Options;

namespace ProgramKit.Authentication.Assurance;

/// <summary>Composes provider-neutral assurance policies into one shell.</summary>
[ShellFeature(
    name: "ProgramKit.Authentication.Assurance",
    DisplayName = "Program Kit Authentication Assurance",
    Description = "Authorizes named step-up policies using standard acr, amr, and auth_time claims.")]
public sealed class ProgramKitAssuranceFeature(ShellSettings settings) : IShellFeature
{
    /// <inheritdoc />
    public void ConfigureServices(IServiceCollection services)
    {
        services.Configure<AssuranceOptions>(
            settings.GetConfigurationRoot().GetSection(AssuranceOptions.SectionName));
        services.AddSingleton<IValidateOptions<AssuranceOptions>, AssuranceOptionsValidator>();
        services.TryAddSingleton(TimeProvider.System);
        services.AddSingleton<IAssuranceEvaluator, AssuranceEvaluator>();
        services.TryAddEnumerable(
            ServiceDescriptor.Singleton<IAuthorizationHandler, AssuranceAuthorizationHandler>());
        services.AddOptions<AuthorizationOptions>().Configure<IOptions<AssuranceOptions>>((authorization, selected) =>
        {
            foreach (var policy in selected.Value.Policies.Keys)
            {
                authorization.AddPolicy(
                    AssurancePolicyNames.For(policy),
                    builder => builder.RequireAuthenticatedUser().AddRequirements(new AssuranceRequirement(policy)));
            }
        });
    }
}
