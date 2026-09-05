namespace ProgramKit.Authentication.DownstreamApi;

/// <summary>Sends bounded authenticated requests to configured downstream APIs.</summary>
public interface IDownstreamApiClient
{
    /// <summary>Sends one relative request using the named API's governed token mode.</summary>
    /// <param name="registration">The exact configured downstream API name.</param>
    /// <param name="request">A request with a relative URI and no caller-owned authorization header.</param>
    /// <param name="cancellationToken">Cancels token and downstream I/O.</param>
    /// <returns>The downstream response, owned by the caller.</returns>
    ValueTask<HttpResponseMessage> SendAsync(
        string registration,
        HttpRequestMessage request,
        CancellationToken cancellationToken = default);
}
