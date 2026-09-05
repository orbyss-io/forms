/// <summary>Returns the probe's recording HTTP client.</summary>
internal sealed class ProbeHttpClientFactory(HttpClient client) : IHttpClientFactory
{
    /// <inheritdoc />
    public HttpClient CreateClient(string name) => client;
}
