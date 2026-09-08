namespace Orbyss.Forms;

/// <summary>Compiles a provider-neutral definition into deterministic target artifacts and manifests.</summary>
public interface IFormCompiler
{
    /// <summary>Compiles a definition at an explicit evidence timestamp.</summary>
    ValueTask<FormCandidate> CompileAsync(
        FormDefinition definition,
        DateTimeOffset compiledAt,
        CancellationToken cancellationToken = default);
}
