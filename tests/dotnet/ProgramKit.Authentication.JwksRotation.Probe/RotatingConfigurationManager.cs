using Microsoft.IdentityModel.Protocols;
using Microsoft.IdentityModel.Protocols.OpenIdConnect;
using Microsoft.IdentityModel.Tokens;

/// <summary>Models deterministic discovery/JWKS cache generations through the standard metadata contract.</summary>
internal sealed class RotatingConfigurationManager(string issuer, params SecurityKey[] initialKeys)
    : IConfigurationManager<OpenIdConnectConfiguration>
{
    /// <summary>Guards cache generation transitions.</summary>
    private readonly object gate = new();

    /// <summary>Holds the currently cached metadata.</summary>
    private OpenIdConnectConfiguration current = Configuration(issuer, initialKeys);

    /// <summary>Holds metadata published by the issuer but not yet refreshed by the consumer.</summary>
    private OpenIdConnectConfiguration? pending;

    /// <summary>Gets the number of refresh requests issued through the metadata contract.</summary>
    internal int RefreshRequests { get; private set; }

    /// <summary>Publishes the next issuer key set without mutating the consumer's current cache.</summary>
    internal void Publish(params SecurityKey[] keys)
    {
        lock (gate)
        {
            pending = Configuration(issuer, keys);
        }
    }

    /// <inheritdoc />
    public Task<OpenIdConnectConfiguration> GetConfigurationAsync(CancellationToken cancel)
    {
        cancel.ThrowIfCancellationRequested();
        lock (gate)
        {
            return Task.FromResult(current);
        }
    }

    /// <inheritdoc />
    public void RequestRefresh()
    {
        lock (gate)
        {
            RefreshRequests++;
            if (pending is not null)
            {
                current = pending;
                pending = null;
            }
        }
    }

    /// <summary>Creates one discovery generation with the exact active verification keys.</summary>
    private static OpenIdConnectConfiguration Configuration(string issuer, IEnumerable<SecurityKey> keys)
    {
        var configuration = new OpenIdConnectConfiguration { Issuer = issuer };
        foreach (var key in keys)
        {
            configuration.SigningKeys.Add(key);
        }
        return configuration;
    }
}
