/// <summary>Returns the downstream probe's recording HTTP client.</summary>
internal sealed class DownstreamHttpClientFactory(HttpClient client) : IHttpClientFactory
{
    /// <inheritdoc />
    public HttpClient CreateClient(string name) => client;
}
