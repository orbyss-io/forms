using Microsoft.AspNetCore.Authorization;

namespace ProgramKit.Authentication.Assurance;

/// <summary>Identifies one named assurance requirement inside ASP.NET authorization.</summary>
internal sealed record AssuranceRequirement(string Policy) : IAuthorizationRequirement;
