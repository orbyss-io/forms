using System.Net;

/// <summary>Records final downstream destinations and authorization values.</summary>
internal sealed class DownstreamRecordingHandler : HttpMessageHandler
{
    /// <summary>Gets the ordered requests observed by the governed HTTP client.</summary>
    internal List<(string Uri, string Scheme, string Token)> Requests { get; } = [];

    /// <inheritdoc />
    protected override Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var authorization = request.Headers.Authorization
            ?? throw new InvalidOperationException("downstream request omitted authorization");
        Requests.Add((request.RequestUri!.AbsoluteUri, authorization.Scheme, authorization.Parameter!));
        return Task.FromResult(new HttpResponseMessage(HttpStatusCode.NoContent));
    }
}
