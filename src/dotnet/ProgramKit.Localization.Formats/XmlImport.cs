using System.Xml;
using System.Xml.Linq;

namespace ProgramKit.Localization.Formats;

/// <summary>Reads XML with DTDs, resolvers, and excessive document expansion disabled.</summary>
internal static class XmlImport
{
    /// <summary>Parses bounded XML bytes without DTD or external resource resolution.</summary>
    public static XDocument Read(ReadOnlyMemory<byte> content, LocalizationImportFormatOptions options)
    {
        using var stream = new MemoryStream(content.ToArray(), writable: false);
        using var reader = XmlReader.Create(stream, new XmlReaderSettings { DtdProcessing = DtdProcessing.Prohibit, XmlResolver = null, MaxCharactersInDocument = options.MaximumExpandedBytes, MaxCharactersFromEntities = 0 });
        try { return XDocument.Load(reader, LoadOptions.None); }
        catch (XmlException) { throw new LocalizationImportFormatException("PKLI408", "XML localization content is malformed or violates secure parser limits."); }
    }
}
