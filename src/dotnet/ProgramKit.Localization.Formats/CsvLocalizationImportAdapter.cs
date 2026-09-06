using System.Text;

namespace ProgramKit.Localization.Formats;

/// <summary>Parses RFC 4180-style long or wide localization CSV documents.</summary>
public sealed class CsvLocalizationImportAdapter : ILocalizationImportFormatAdapter
{
    /// <summary>Bounds applied while decoding and expanding CSV input.</summary>
    private readonly LocalizationImportFormatOptions options;

    /// <summary>Initializes the CSV adapter with secure defaults.</summary>
    public CsvLocalizationImportAdapter(LocalizationImportFormatOptions? options = null) =>
        this.options = options ?? new LocalizationImportFormatOptions();

    /// <inheritdoc />
    public LocalizationImportFormat Format => LocalizationImportFormat.Csv;

    /// <inheritdoc />
    public ValueTask<LocalizationImportDocument> ParseAsync(LocalizationImportRequest request, CancellationToken cancellationToken = default)
    {
        FormatGuards.RequireFormatAndBounds(request, Format, options);
        cancellationToken.ThrowIfCancellationRequested();
        string content;
        try
        {
            content = new UTF8Encoding(false, true).GetString(request.Content.Span);
        }
        catch (DecoderFallbackException)
        {
            throw new LocalizationImportFormatException("PKLI101", "CSV content must be valid UTF-8.");
        }
        if (content.Length > 0 && content[0] == '\uFEFF') content = content[1..];

        var rows = ParseRows(content, options, cancellationToken);
        return ValueTask.FromResult(TabularLocalizationImport.Parse(rows, request, options));
    }

    /// <summary>Tokenizes quoted CSV text into a bounded tabular representation.</summary>
    private static IReadOnlyList<IReadOnlyList<string>> ParseRows(string source, LocalizationImportFormatOptions options, CancellationToken cancellationToken)
    {
        var rows = new List<IReadOnlyList<string>>();
        var row = new List<string>();
        var field = new StringBuilder();
        var quoted = false;
        var quoteClosed = false;
        for (var index = 0; index < source.Length; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var character = source[index];
            if (quoted)
            {
                if (character == '"' && index + 1 < source.Length && source[index + 1] == '"')
                {
                    field.Append('"');
                    index++;
                }
                else if (character == '"')
                {
                    quoted = false;
                    quoteClosed = true;
                }
                else
                {
                    field.Append(character);
                }
            }
            else if (quoteClosed && character is not (',' or '\r' or '\n'))
            {
                throw new LocalizationImportFormatException("PKLI106", "CSV contains content after a closing quote.");
            }
            else if (character == '"' && field.Length == 0)
            {
                quoted = true;
            }
            else if (character == ',')
            {
                AddField(row, field, options);
                quoteClosed = false;
            }
            else if (character is '\r' or '\n')
            {
                if (character == '\r' && index + 1 < source.Length && source[index + 1] == '\n') index++;
                AddField(row, field, options);
                AddRow(rows, row, options);
                row = [];
                quoteClosed = false;
            }
            else
            {
                if (character == '"') throw new LocalizationImportFormatException("PKLI106", "CSV contains a quote inside an unquoted field.");
                field.Append(character);
            }
        }

        if (quoted) throw new LocalizationImportFormatException("PKLI102", "CSV contains an unterminated quoted field.");
        if (field.Length > 0 || row.Count > 0)
        {
            AddField(row, field, options);
            AddRow(rows, row, options);
        }
        return rows;
    }

    /// <summary>Commits one bounded cell to the active row.</summary>
    private static void AddField(ICollection<string> row, StringBuilder field, LocalizationImportFormatOptions options)
    {
        if (field.Length > options.MaximumCellCharacters) throw new LocalizationImportFormatException("PKLI103", "CSV cell exceeds the configured character limit.");
        if (row.Count >= options.MaximumColumns) throw new LocalizationImportFormatException("PKLI104", "CSV column limit exceeded.");
        row.Add(field.ToString());
        field.Clear();
    }

    /// <summary>Commits one row while enforcing the configured row ceiling.</summary>
    private static void AddRow(ICollection<IReadOnlyList<string>> rows, IReadOnlyList<string> row, LocalizationImportFormatOptions options)
    {
        if (rows.Count >= options.MaximumRows + 1) throw new LocalizationImportFormatException("PKLI105", "CSV row limit exceeded.");
        rows.Add(row);
    }
}
