/// <summary>Captures one immutable outbound adapter request.</summary>
internal sealed record RecordedRequest(string Method, string PathAndQuery, string? Body, string? Authorization);
