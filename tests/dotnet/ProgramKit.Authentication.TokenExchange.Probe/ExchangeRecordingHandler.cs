using System.Net;
using System.Net.Http.Headers;
using System.Text;

/// <summary>Records and validates one provider-neutral RFC 8693 exchange.</summary>
internal sealed class ExchangeRecordingHandler : HttpMessageHandler
{
    /// <summary>Gets the number of token-endpoint requests.</summary>
    internal int Requests { get; private set; }

    /// <inheritdoc />
    protected override async Task<HttpResponseMessage> SendAsync(
        HttpRequestMessage request,
        CancellationToken cancellationToken)
    {
        Requests++;
        ExchangeProbeAssertions.Require(request.Method == HttpMethod.Post, "token exchange must use POST");
        var authorization = request.Headers.Authorization;
        ExchangeProbeAssertions.Require(
            authorization is AuthenticationHeaderValue { Scheme: "Basic" },
            "token exchange omitted client_secret_basic authentication");
        var credentials = Encoding.UTF8.GetString(Convert.FromBase64String(authorization!.Parameter!));
        ExchangeProbeAssertions.Require(
            credentials == "delegating+client:exchange%2Fsecret",
            "exchange-client credentials were not form encoded");
        var body = await request.Content!.ReadAsStringAsync(cancellationToken);
        if (body.Contains("subject_token=reject-token", StringComparison.Ordinal))
        {
            return new HttpResponseMessage(HttpStatusCode.BadRequest)
            {
                Content = new StringContent("provider-secret-body", Encoding.UTF8, "text/plain")
            };
        }

        foreach (var required in new[]
        {
            "grant_type=urn%3Aietf%3Aparams%3Aoauth%3Agrant-type%3Atoken-exchange",
            "subject_token=subject-token",
            "subject_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Aaccess_token",
            "requested_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Aaccess_token",
            "audience=orders-api",
            "resource=https%3A%2F%2Forders.example%2F",
            "scope=orders.read",
            "actor_token=actor-token",
            "actor_token_type=urn%3Aietf%3Aparams%3Aoauth%3Atoken-type%3Aaccess_token"
        })
        {
            ExchangeProbeAssertions.Require(body.Contains(required, StringComparison.Ordinal), $"exchange omitted {required}");
        }

        return new HttpResponseMessage(HttpStatusCode.OK)
        {
            Content = new StringContent(
                "{\"access_token\":\"exchanged-access\","
                + "\"issued_token_type\":\"urn:ietf:params:oauth:token-type:access_token\","
                + "\"token_type\":\"Bearer\",\"expires_in\":90,\"scope\":\"orders.read\"}",
                Encoding.UTF8,
                "application/json")
        };
    }
}
