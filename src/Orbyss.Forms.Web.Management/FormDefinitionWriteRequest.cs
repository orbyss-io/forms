namespace Orbyss.Forms.Web.Management;

/// <summary>Combines a provider-neutral definition with one mutation command.</summary>
public sealed record FormDefinitionWriteRequest(FormDefinition Definition, FormWebMutation Mutation);
