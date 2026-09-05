using ProgramKit.Authentication.ClientCredentials;

/// <summary>Returns an application-only token while recording its registration.</summary>
internal sealed class DownstreamMachineTokenProvider : IClientCredentialsTokenProvider
{
    /// <summary>Gets the registration requested by the downstream client.</summary>
    internal string? Registration { get; private set; }

    /// <inheritdoc />
    public ValueTask<OAuthAccessToken> GetTokenAsync(
        string registration,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        Registration = registration;
        return ValueTask.FromResult(
            new OAuthAccessToken("machine-access", "Bearer", DateTimeOffset.UtcNow.AddMinutes(1)));
    }
}
