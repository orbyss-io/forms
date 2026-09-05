/// <summary>Returns the token-exchange probe's recording client.</summary>
internal sealed class ExchangeHttpClientFactory(HttpClient client) : IHttpClientFactory
{
    /// <inheritdoc />
    public HttpClient CreateClient(string name) => client;
}
