using System.Net;
using System.Net.Http.Headers;
using System.Text;

/// <summary>Records and validates provider-neutral OAuth token requests.</summary>
internal sealed class RecordingHandler : HttpMessageHandler
{
    /// <summary>Gets the number of client-secret Basic requests.</summary>
    internal int BasicRequests { get; private set; }

    /// <summary>Gets the number of client-secret POST requests.</summary>
    internal int PostRequests { get; private set; }

    /// <inheritdoc />
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        ProbeAssertions.Require(request.Method == HttpMethod.Post, "token acquisition must use POST");
        ProbeAssertions.Require(
            request.RequestUri == new Uri("https://identity.example/oauth/token"),
            "token endpoint changed");
        var body = await request.Content!.ReadAsStringAsync(cancellationToken);
        ProbeAssertions.Require(
            body.Contains("grant_type=client_credentials", StringComparison.Ordinal),
            "grant type was omitted");
        if (request.Headers.Authorization is AuthenticationHeaderValue { Scheme: "Basic" } authorization)
        {
            BasicRequests++;
            var credentials = Encoding.UTF8.GetString(Convert.FromBase64String(authorization.Parameter!));
            ProbeAssertions.Require(
                credentials == "machine+id:s%2Fecret%3Avalue",
                $"HTTP Basic credentials were not form encoded: {credentials}");
            ProbeAssertions.Require(
                body.Contains("scope=orders.read+orders.write", StringComparison.Ordinal),
                "machine scopes changed");
            return Json("{\"access_token\":\"basic-access\",\"token_type\":\"Bearer\",\"expires_in\":120}");
        }

        PostRequests++;
        ProbeAssertions.Require(
            body.Contains("client_id=post-client", StringComparison.Ordinal),
            "POST client identifier was omitted");
        ProbeAssertions.Require(
            body.Contains("client_secret=post-secret", StringComparison.Ordinal),
            "POST client secret was omitted");
        return Json("{\"access_token\":\"post-access\",\"token_type\":\"Bearer\",\"expires_in\":\"60\"}");
    }

    /// <summary>Creates a successful JSON token response.</summary>
    private static HttpResponseMessage Json(string value) => new(HttpStatusCode.OK)
    {
        Content = new StringContent(value, Encoding.UTF8, "application/json")
    };
}
