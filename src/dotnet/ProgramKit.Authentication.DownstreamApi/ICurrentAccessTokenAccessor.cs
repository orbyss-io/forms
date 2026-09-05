namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Reads the already-validated current user access token for delegation.</summary>
public interface ICurrentAccessTokenAccessor
{
    /// <summary>Gets the current validated access token or fails when no authenticated session supplies one.</summary>
    ValueTask<string> GetRequiredTokenAsync(CancellationToken cancellationToken);
}
