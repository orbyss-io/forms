using FormsModel = ProgramKit.Forms;
using LocalizationModel = ProgramKit.Localization;

namespace ProgramKit.Forms.Localization;

/// <summary>Merges form requirements into structured form-scoped localization messages.</summary>
public sealed class DefaultFormLocalizationBridge : IFormLocalizationBridge
{
    /// <inheritdoc />
    public FormLocalizationMergeResult Merge(
        FormsModel.FormCandidate candidate,
        LocalizationModel.LocalizationCatalogDefinition catalog)
    {
        ArgumentNullException.ThrowIfNull(candidate);
        ArgumentNullException.ThrowIfNull(catalog);
        var diagnostics = new List<LocalizationModel.LocalizationDiagnostic>();
        var messages = catalog.Messages.ToList();
        var scope = new LocalizationModel.LocalizationScope(LocalizationModel.LocalizationScopeKind.Form, candidate.FormId.Value);
        var existing = messages
            .Where(message => message.Scope == scope)
            .ToDictionary(message => message.Key, StringComparer.Ordinal);
        var added = 0;
        var retained = 0;
        foreach (var requirement in candidate.Translations.OrderBy(item => item.Key, StringComparer.Ordinal))
        {
            var path = requirement.Key;
            if (!string.Equals(requirement.SourceLocale, catalog.SourceLocale, StringComparison.OrdinalIgnoreCase))
            {
                diagnostics.Add(Error(
                    "PKFL001",
                    $"Form source locale '{requirement.SourceLocale}' does not match catalog source locale '{catalog.SourceLocale}'.",
                    path));
                continue;
            }

            var expectedScope = $"forms:{candidate.FormId.Value}";
            if (!string.Equals(requirement.Scope, expectedScope, StringComparison.Ordinal))
            {
                diagnostics.Add(Error("PKFL002", $"Translation requirement scope must be '{expectedScope}'.", path));
                continue;
            }

            if (existing.TryGetValue(requirement.Key, out var current))
            {
                if (!string.Equals(current.SourcePattern, requirement.DefaultText, StringComparison.Ordinal)
                    || !string.Equals(current.Context, requirement.Context, StringComparison.Ordinal))
                {
                    diagnostics.Add(Error("PKFL003", "The existing localization message conflicts with the form source contract.", path));
                }
                else
                {
                    retained++;
                }

                continue;
            }

            var arguments = requirement.Arguments?
                .Distinct(StringComparer.Ordinal)
                .OrderBy(argument => argument, StringComparer.Ordinal)
                .Select(argument => new LocalizationModel.LocalizationArgumentDefinition(argument, LocalizationModel.LocalizationArgumentType.String))
                .ToArray()
                ?? [];
            var message = new LocalizationModel.LocalizationMessageDefinition(
                requirement.Key,
                scope,
                requirement.DefaultText,
                arguments,
                [],
                Context: requirement.Context);
            messages.Add(message);
            existing.Add(message.Key, message);
            added++;
        }

        var merged = catalog with
        {
            Revision = diagnostics.Any(item => item.Severity == LocalizationModel.LocalizationDiagnosticSeverity.Error)
                ? catalog.Revision
                : new LocalizationModel.LocalizationRevision(catalog.Revision.Value + 1),
            Messages = messages
                .OrderBy(message => message.Scope.Kind)
                .ThenBy(message => message.Scope.ParentResourceId, StringComparer.Ordinal)
                .ThenBy(message => message.Scope.ResourceId, StringComparer.Ordinal)
                .ThenBy(message => message.Key, StringComparer.Ordinal)
                .ToArray()
        };
        return new FormLocalizationMergeResult(merged, added, retained, diagnostics);
    }

    /// <summary>Creates a stable cross-context integration diagnostic.</summary>
    private static LocalizationModel.LocalizationDiagnostic Error(string code, string message, string key) =>
        new(code, LocalizationModel.LocalizationDiagnosticSeverity.Error, message, key);
}
