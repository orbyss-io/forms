using System.Text.Json.Nodes;
using ProgramKit.Forms;

/// <summary>Adds the required country value for the probe's breaking target release.</summary>
internal sealed class CountryDraftMigration : IFormDraftDataMigration
{
    /// <inheritdoc />
    public string Id => "probe.add-country";

    /// <inheritdoc />
    public ValueTask<string> MigrateAsync(FormRelease source, FormRelease target, FormDataDocument data, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var document = JsonNode.Parse(data.Json)?.AsObject() ?? throw new InvalidOperationException("Probe draft data must be an object.");
        document["country"] = "NL";
        return ValueTask.FromResult(document.ToJsonString());
    }
}
