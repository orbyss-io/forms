namespace ProgramKit.Forms;

/// <summary>Persists and retrieves immutable published form releases.</summary>
public interface IFormReleaseStore
{
    /// <summary>Writes a release once, accepting only byte-equivalent idempotent replays.</summary>
    ValueTask WriteAsync(FormRelease release, CancellationToken cancellationToken = default);

    /// <summary>Gets an immutable release, or returns null when it is absent.</summary>
    ValueTask<FormRelease?> GetAsync(FormReleaseId releaseId, CancellationToken cancellationToken = default);

    /// <summary>Lists immutable releases for one logical form in publication order.</summary>
    IAsyncEnumerable<FormRelease> FindByFormAsync(FormId formId, CancellationToken cancellationToken = default);
}
