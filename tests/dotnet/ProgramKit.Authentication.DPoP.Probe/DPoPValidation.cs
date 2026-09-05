/// <summary>Captures the proof failure and optional nonce challenge emitted by the pipeline.</summary>
internal readonly record struct DPoPValidation(string? Failure, string? Nonce);
