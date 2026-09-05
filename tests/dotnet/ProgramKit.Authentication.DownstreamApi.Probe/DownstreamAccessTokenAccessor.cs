using ProgramKit.Authentication.DownstreamApi;

/// <summary>Returns one already-validated user token for delegation.</summary>
internal sealed class DownstreamAccessTokenAccessor(string token) : ICurrentAccessTokenAccessor
{
    /// <inheritdoc />
    public ValueTask<string> GetRequiredTokenAsync(CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        return ValueTask.FromResult(token);
    }
}
