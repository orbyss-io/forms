namespace Orbyss.Localization;

/// <summary>Validates localization identity, fallback graphs, scopes, arguments, and message patterns.</summary>
public sealed class LocalizationCatalogValidator : ILocalizationCatalogValidator
{
    /// <summary>Holds limits applied to potentially untrusted catalog content.</summary>
    private readonly LocalizationValidationOptions options;

    /// <summary>Initializes a validator with secure default catalog limits.</summary>
    public LocalizationCatalogValidator()
        : this(new LocalizationValidationOptions())
    {
    }

    /// <summary>Initializes a validator with explicit catalog limits.</summary>
    public LocalizationCatalogValidator(LocalizationValidationOptions options)
    {
        ArgumentNullException.ThrowIfNull(options);
        if (options.MaximumLocales <= 0
            || options.MaximumMessages <= 0
            || options.MaximumArgumentsPerMessage <= 0
            || options.MaximumPatternLength <= 0
            || options.MaximumFallbackDepth <= 0)
        {
            throw new ArgumentOutOfRangeException(nameof(options), "All localization validation limits must be positive.");
        }

        this.options = options;
    }

    /// <inheritdoc />
    public ValueTask<IReadOnlyList<LocalizationDiagnostic>> ValidateAsync(
        LocalizationCatalogDefinition catalog,
        CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(catalog);
        cancellationToken.ThrowIfCancellationRequested();
        var diagnostics = new List<LocalizationDiagnostic>();
        ValidateIdentity(catalog, diagnostics);
        var locales = ValidateLocales(catalog, diagnostics);
        ValidateFallbacks(catalog.Locales, locales, diagnostics);
        ValidateMessages(catalog.Messages, locales, diagnostics, cancellationToken);
        return ValueTask.FromResult<IReadOnlyList<LocalizationDiagnostic>>(diagnostics);
    }

    /// <summary>Validates the stable catalog identity and source locale.</summary>
    private static void ValidateIdentity(
        LocalizationCatalogDefinition catalog,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        Required(catalog.Id.Value, "PKL001", "A catalog identifier is required.", "/id", diagnostics);
        Required(catalog.Name, "PKL002", "A catalog name is required.", "/name", diagnostics);
        Required(catalog.SourceLocale, "PKL003", "A source locale is required.", "/sourceLocale", diagnostics);
        if (catalog.Revision.Value <= 0)
        {
            diagnostics.Add(Error("PKL004", "The catalog revision must be positive.", "/revision"));
        }

        if (!string.IsNullOrWhiteSpace(catalog.SourceLocale) && !IsLocaleTag(catalog.SourceLocale))
        {
            diagnostics.Add(Error("PKL005", "The source locale must be a bounded BCP 47 language tag.", "/sourceLocale"));
        }
    }

    /// <summary>Validates locale tags and creates the lookup used by fallback and message checks.</summary>
    private IReadOnlyDictionary<string, LocaleDefinition> ValidateLocales(
        LocalizationCatalogDefinition catalog,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        if (catalog.Locales.Count > options.MaximumLocales)
        {
            diagnostics.Add(Error("PKL010", $"A catalog cannot contain more than {options.MaximumLocales} locales.", "/locales"));
        }

        var locales = new Dictionary<string, LocaleDefinition>(StringComparer.OrdinalIgnoreCase);
        for (var index = 0; index < catalog.Locales.Count; index++)
        {
            var locale = catalog.Locales[index];
            var path = $"/locales/{index}/languageTag";
            if (!IsLocaleTag(locale.LanguageTag))
            {
                diagnostics.Add(Error("PKL011", $"Locale '{locale.LanguageTag}' is not a bounded BCP 47 language tag.", path));
            }
            else if (!locales.TryAdd(locale.LanguageTag, locale))
            {
                diagnostics.Add(Error("PKL012", $"Locale '{locale.LanguageTag}' is duplicated.", path));
            }
        }

        if (!locales.ContainsKey(catalog.SourceLocale))
        {
            diagnostics.Add(Error("PKL013", "The source locale must be declared in the locale collection.", "/sourceLocale"));
        }

        return locales;
    }

    /// <summary>Requires fallback targets to exist and rejects bounded-depth cycles.</summary>
    private void ValidateFallbacks(
        IReadOnlyList<LocaleDefinition> definitions,
        IReadOnlyDictionary<string, LocaleDefinition> locales,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        foreach (var locale in definitions)
        {
            if (locale.FallbackLanguageTag is { } fallback && !locales.ContainsKey(fallback))
            {
                diagnostics.Add(Error("PKL020", $"Fallback locale '{fallback}' is not declared.", $"/locales/{locale.LanguageTag}/fallbackLanguageTag"));
                continue;
            }

            var visited = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var current = locale;
            for (var depth = 0; current.FallbackLanguageTag is { } next; depth++)
            {
                if (!visited.Add(current.LanguageTag) || string.Equals(next, locale.LanguageTag, StringComparison.OrdinalIgnoreCase))
                {
                    diagnostics.Add(Error("PKL021", $"Locale '{locale.LanguageTag}' participates in a fallback cycle.", $"/locales/{locale.LanguageTag}/fallbackLanguageTag"));
                    break;
                }

                if (depth >= options.MaximumFallbackDepth)
                {
                    diagnostics.Add(Error("PKL022", $"Locale '{locale.LanguageTag}' exceeds the maximum fallback depth.", $"/locales/{locale.LanguageTag}/fallbackLanguageTag"));
                    break;
                }

                if (!locales.TryGetValue(next, out current!))
                {
                    break;
                }
            }
        }
    }

    /// <summary>Validates message identity, scope, arguments, translations, and placeholder signatures.</summary>
    private void ValidateMessages(
        IReadOnlyList<LocalizationMessageDefinition> messages,
        IReadOnlyDictionary<string, LocaleDefinition> locales,
        ICollection<LocalizationDiagnostic> diagnostics,
        CancellationToken cancellationToken)
    {
        if (messages.Count > options.MaximumMessages)
        {
            diagnostics.Add(Error("PKL030", $"A catalog cannot contain more than {options.MaximumMessages} messages.", "/messages"));
        }

        var identities = new HashSet<string>(StringComparer.Ordinal);
        for (var index = 0; index < messages.Count; index++)
        {
            cancellationToken.ThrowIfCancellationRequested();
            var message = messages[index];
            var path = $"/messages/{index}";
            Required(message.Key, "PKL031", "A message key is required.", $"{path}/key", diagnostics);
            var identity = ScopeIdentity(message.Scope) + ":" + message.Key;
            if (!string.IsNullOrWhiteSpace(message.Key) && !identities.Add(identity))
            {
                diagnostics.Add(Error("PKL032", $"Message '{message.Key}' is duplicated in its scope.", $"{path}/key"));
            }

            ValidateScope(message.Scope, path, diagnostics);
            var arguments = ValidateArguments(message, path, diagnostics);
            ValidatePattern(message.SourcePattern, arguments, $"{path}/sourcePattern", diagnostics);
            var translatedLocales = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            for (var valueIndex = 0; valueIndex < message.Values.Count; valueIndex++)
            {
                var value = message.Values[valueIndex];
                var valuePath = $"{path}/values/{valueIndex}";
                if (!locales.ContainsKey(value.LanguageTag))
                {
                    diagnostics.Add(Error("PKL033", $"Translation locale '{value.LanguageTag}' is not declared.", $"{valuePath}/languageTag"));
                }
                else if (!translatedLocales.Add(value.LanguageTag))
                {
                    diagnostics.Add(Error("PKL034", $"Translation locale '{value.LanguageTag}' is duplicated for this message.", $"{valuePath}/languageTag"));
                }

                ValidatePattern(value.Pattern, arguments, $"{valuePath}/pattern", diagnostics);
            }
        }
    }

    /// <summary>Requires structured scope ownership for every non-application message.</summary>
    private static void ValidateScope(
        LocalizationScope scope,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        if (scope.Kind == LocalizationScopeKind.Application && scope.ResourceId is not null)
        {
            diagnostics.Add(Error("PKL040", "Application scope cannot carry a resource identifier.", $"{path}/scope/resourceId"));
        }
        else if (scope.Kind != LocalizationScopeKind.Application && string.IsNullOrWhiteSpace(scope.ResourceId))
        {
            diagnostics.Add(Error("PKL041", "A non-application scope requires a resource identifier.", $"{path}/scope/resourceId"));
        }
    }

    /// <summary>Validates unique bounded argument declarations and returns their name lookup.</summary>
    private IReadOnlyDictionary<string, LocalizationArgumentDefinition> ValidateArguments(
        LocalizationMessageDefinition message,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        if (message.Arguments.Count > options.MaximumArgumentsPerMessage)
        {
            diagnostics.Add(Error("PKL050", $"A message cannot declare more than {options.MaximumArgumentsPerMessage} arguments.", $"{path}/arguments"));
        }

        var arguments = new Dictionary<string, LocalizationArgumentDefinition>(StringComparer.Ordinal);
        for (var index = 0; index < message.Arguments.Count; index++)
        {
            var argument = message.Arguments[index];
            if (!IsIdentifier(argument.Name))
            {
                diagnostics.Add(Error("PKL051", $"Argument '{argument.Name}' is not a portable identifier.", $"{path}/arguments/{index}/name"));
            }
            else if (!arguments.TryAdd(argument.Name, argument))
            {
                diagnostics.Add(Error("PKL052", $"Argument '{argument.Name}' is duplicated.", $"{path}/arguments/{index}/name"));
            }
        }

        return arguments;
    }

    /// <summary>Validates a bounded ICU-style pattern and its declared argument/type signature.</summary>
    private void ValidatePattern(
        string pattern,
        IReadOnlyDictionary<string, LocalizationArgumentDefinition> arguments,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        if (string.IsNullOrWhiteSpace(pattern))
        {
            diagnostics.Add(Error("PKL060", "A message pattern is required.", path));
            return;
        }

        if (pattern.Length > options.MaximumPatternLength)
        {
            diagnostics.Add(Error("PKL061", $"A message pattern cannot exceed {options.MaximumPatternLength} characters.", path));
            return;
        }

        var used = new HashSet<string>(StringComparer.Ordinal);
        AnalyzePattern(pattern, arguments, used, path, diagnostics);
        foreach (var argument in arguments.Values.Where(argument => argument.Required && !used.Contains(argument.Name)))
        {
            diagnostics.Add(new LocalizationDiagnostic("PKL062", LocalizationDiagnosticSeverity.Warning, $"Required argument '{argument.Name}' is not used by the pattern.", path));
        }
    }

    /// <summary>Walks nested ICU arguments while respecting apostrophe-quoted literal braces.</summary>
    private static void AnalyzePattern(
        string pattern,
        IReadOnlyDictionary<string, LocalizationArgumentDefinition> arguments,
        ISet<string> used,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        var quoted = false;
        for (var index = 0; index < pattern.Length; index++)
        {
            if (pattern[index] == '\'' && (index + 1 >= pattern.Length || pattern[index + 1] != '\''))
            {
                quoted = !quoted;
                continue;
            }

            if (pattern[index] != '{' || quoted)
            {
                if (pattern[index] == '}' && !quoted)
                {
                    diagnostics.Add(Error("PKL063", "The message pattern contains an unmatched closing brace.", path));
                    return;
                }

                continue;
            }

            var close = FindClosingBrace(pattern, index);
            if (close < 0)
            {
                diagnostics.Add(Error("PKL064", "The message pattern contains an unmatched opening brace.", path));
                return;
            }

            var content = pattern[(index + 1)..close];
            var commas = TopLevelCommas(content);
            var name = (commas.Count == 0 ? content : content[..commas[0]]).Trim();
            if (!arguments.TryGetValue(name, out var argument))
            {
                diagnostics.Add(Error("PKL065", $"Pattern argument '{name}' is not declared.", path));
            }
            else
            {
                used.Add(name);
            }

            if (commas.Count >= 2)
            {
                var format = content[(commas[0] + 1)..commas[1]].Trim();
                var optionsText = content[(commas[1] + 1)..];
                ValidateFormat(format, argument, optionsText, path, diagnostics);
                if (string.Equals(format, "plural", StringComparison.Ordinal)
                    || string.Equals(format, "selectordinal", StringComparison.Ordinal)
                    || string.Equals(format, "select", StringComparison.Ordinal))
                {
                    AnalyzeOptionBodies(optionsText, arguments, used, path, diagnostics);
                }
            }

            index = close;
        }
    }

    /// <summary>Validates plural/select argument types and mandatory ICU fallback branches.</summary>
    private static void ValidateFormat(
        string format,
        LocalizationArgumentDefinition? argument,
        string optionsText,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        var plural = string.Equals(format, "plural", StringComparison.Ordinal)
            || string.Equals(format, "selectordinal", StringComparison.Ordinal);
        var select = string.Equals(format, "select", StringComparison.Ordinal);
        if (!plural && !select)
        {
            return;
        }

        if (!HasOtherBranch(optionsText))
        {
            diagnostics.Add(Error("PKL066", $"The '{format}' argument must define an 'other' branch.", path));
        }

        if (argument is not null
            && plural
            && argument.Type is not LocalizationArgumentType.Integer and not LocalizationArgumentType.Number)
        {
            diagnostics.Add(Error("PKL067", $"Plural argument '{argument.Name}' must be numeric.", path));
        }

        if (argument is not null
            && select
            && argument.Type is not LocalizationArgumentType.Select and not LocalizationArgumentType.String)
        {
            diagnostics.Add(Error("PKL068", $"Select argument '{argument.Name}' must be a selector or string.", path));
        }
    }

    /// <summary>Finds a matching ICU brace while ignoring apostrophe-quoted literals.</summary>
    private static int FindClosingBrace(string value, int openingIndex)
    {
        var depth = 0;
        var quoted = false;
        for (var index = openingIndex; index < value.Length; index++)
        {
            if (value[index] == '\'' && (index + 1 >= value.Length || value[index + 1] != '\''))
            {
                quoted = !quoted;
            }
            else if (!quoted && value[index] == '{')
            {
                depth++;
            }
            else if (!quoted && value[index] == '}' && --depth == 0)
            {
                return index;
            }
        }

        return -1;
    }

    /// <summary>Returns comma positions outside nested ICU option branches.</summary>
    private static IReadOnlyList<int> TopLevelCommas(string value)
    {
        var result = new List<int>();
        var depth = 0;
        var quoted = false;
        for (var index = 0; index < value.Length; index++)
        {
            if (value[index] == '\'' && (index + 1 >= value.Length || value[index + 1] != '\''))
            {
                quoted = !quoted;
            }
            else if (!quoted && value[index] == '{')
            {
                depth++;
            }
            else if (!quoted && value[index] == '}')
            {
                depth--;
            }
            else if (!quoted && depth == 0 && value[index] == ',')
            {
                result.Add(index);
            }
        }

        return result;
    }

    /// <summary>Recognizes an explicit top-level ICU `other` option.</summary>
    private static bool HasOtherBranch(string value)
    {
        var index = 0;
        while (index < value.Length)
        {
            while (index < value.Length && char.IsWhiteSpace(value[index]))
            {
                index++;
            }

            var start = index;
            while (index < value.Length && !char.IsWhiteSpace(value[index]) && value[index] != '{')
            {
                index++;
            }

            var selector = value[start..index];
            while (index < value.Length && char.IsWhiteSpace(value[index]))
            {
                index++;
            }

            if (index >= value.Length || value[index] != '{')
            {
                return false;
            }

            if (string.Equals(selector, "other", StringComparison.Ordinal))
            {
                return true;
            }

            var close = FindClosingBrace(value, index);
            if (close < 0)
            {
                return false;
            }

            index = close + 1;
        }

        return false;
    }

    /// <summary>Validates nested arguments inside ICU plural and select option bodies.</summary>
    private static void AnalyzeOptionBodies(
        string value,
        IReadOnlyDictionary<string, LocalizationArgumentDefinition> arguments,
        ISet<string> used,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        var index = 0;
        while (index < value.Length)
        {
            while (index < value.Length && char.IsWhiteSpace(value[index]))
            {
                index++;
            }

            while (index < value.Length && !char.IsWhiteSpace(value[index]) && value[index] != '{')
            {
                index++;
            }

            while (index < value.Length && char.IsWhiteSpace(value[index]))
            {
                index++;
            }

            if (index >= value.Length || value[index] != '{')
            {
                return;
            }

            var close = FindClosingBrace(value, index);
            if (close < 0)
            {
                return;
            }

            AnalyzePattern(value[(index + 1)..close], arguments, used, path, diagnostics);
            index = close + 1;
        }
    }

    /// <summary>Creates a stable structured scope identity for duplicate detection.</summary>
    private static string ScopeIdentity(LocalizationScope scope) =>
        $"{scope.Kind}:{scope.ParentResourceId}:{scope.ResourceId}";

    /// <summary>Recognizes portable argument identifiers shared by server and browser formatters.</summary>
    private static bool IsIdentifier(string value) =>
        !string.IsNullOrWhiteSpace(value)
        && (char.IsAsciiLetter(value[0]) || value[0] == '_')
        && value.Skip(1).All(character => char.IsAsciiLetterOrDigit(character) || character == '_');

    /// <summary>Recognizes a bounded interoperable subset of BCP 47 language tags.</summary>
    private static bool IsLocaleTag(string value)
    {
        if (string.IsNullOrWhiteSpace(value)
            || value.Length > 64
            || value.StartsWith("-", StringComparison.Ordinal)
            || value.EndsWith("-", StringComparison.Ordinal))
        {
            return false;
        }

        var segments = value.Split('-');
        return segments[0].Length is >= 2 and <= 8
            && segments[0].All(char.IsAsciiLetter)
            && segments.Skip(1).All(segment => segment.Length is >= 1 and <= 8 && segment.All(char.IsAsciiLetterOrDigit));
    }

    /// <summary>Adds a stable missing-value diagnostic when a catalog string is blank.</summary>
    private static void Required(
        string value,
        string code,
        string message,
        string path,
        ICollection<LocalizationDiagnostic> diagnostics)
    {
        if (string.IsNullOrWhiteSpace(value))
        {
            diagnostics.Add(Error(code, message, path));
        }
    }

    /// <summary>Creates a blocking localization diagnostic with a stable semantic path.</summary>
    private static LocalizationDiagnostic Error(string code, string message, string path) =>
        new(code, LocalizationDiagnosticSeverity.Error, message, path);
}
