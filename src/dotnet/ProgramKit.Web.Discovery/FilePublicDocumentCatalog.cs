using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace ProgramKit.Web.Discovery;

/// <summary>Loads a bounded, hash-checked public projection without serving arbitrary files.</summary>
public sealed class FilePublicDocumentCatalog(string contentRoot, string outputDirectory) : IPublicDocumentCatalog
{
    /// <summary>Reads and validates the whole projection before any route is mapped.</summary>
    public IReadOnlyList<PublicDocument> ReadDocuments()
    {
        var root = ResolveInside(contentRoot, outputDirectory);
        var manifestPath = ResolveInside(root, "publication.json");
        if (new FileInfo(manifestPath).Length > 2_000_000)
        {
            throw new InvalidDataException("Public projection manifest is too large.");
        }

        var options = new JsonSerializerOptions(JsonSerializerDefaults.Web)
        {
            UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
            RespectNullableAnnotations = true,
        };
        var manifest = JsonSerializer.Deserialize<PublicationManifest>(System.IO.File.ReadAllBytes(manifestPath), options)
            ?? throw new InvalidDataException("Public projection manifest is empty.");
        if (manifest.Version != "1.0" || manifest.Resources.Count > 4096)
        {
            throw new InvalidDataException("Unsupported public projection version or resource count.");
        }

        var documents = new List<PublicDocument>();
        var routes = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        long total = 0;
        foreach (var resource in manifest.Resources)
        {
            ValidateRoute(resource.Route);
            if (!routes.Add(resource.Route) || resource.Visibility != "public" ||
                !resource.File.StartsWith("public/", StringComparison.Ordinal))
            {
                throw new InvalidDataException("Only unique, explicitly public resources may be exposed.");
            }

            ValidateContentType(resource.ContentType);
            var path = ResolveInside(root, resource.File);
            var length = new FileInfo(path).Length;
            total += length;
            if (length > 1_000_000 || total > 32_000_000)
            {
                throw new InvalidDataException("Public projection exceeds the serving budget.");
            }

            var data = System.IO.File.ReadAllBytes(path);
            if (!StringComparer.OrdinalIgnoreCase.Equals(Convert.ToHexString(SHA256.HashData(data)), resource.Sha256))
            {
                throw new InvalidDataException("Public projection hash mismatch; deploy a coherent build.");
            }

            documents.Add(new PublicDocument(resource.Route, resource.ContentType, data, resource.Index));
        }

        return documents.AsReadOnly();
    }

    /// <summary>Rejects route templates, encodings and ambiguous paths for all catalogue adapters.</summary>
    public static void ValidateRoute(string route)
    {
        if (route is null || route.Length > 1024 || !Regex.IsMatch(route, @"^/(?:[a-zA-Z0-9_-]+(?:\.[a-zA-Z0-9_-]+)?/)*[a-zA-Z0-9_-]*(?:\.[a-zA-Z0-9_-]+)?$", RegexOptions.CultureInvariant))
        {
            throw new InvalidDataException("Discovery routes must be literal root-relative paths.");
        }
    }

    /// <summary>Rejects header injection and unsupported response types for all catalogue adapters.</summary>
    public static void ValidateContentType(string contentType)
    {
        if (contentType is not ("text/html; charset=utf-8" or "text/css; charset=utf-8" or
            "text/javascript; charset=utf-8" or "application/xml; charset=utf-8" or
            "text/markdown; charset=utf-8" or "text/plain; charset=utf-8" or "image/svg+xml"))
        {
            throw new InvalidDataException("Unsupported public document media type.");
        }
    }

    /// <summary>Resolves only literal descendants, refusing linked ancestors and traversal.</summary>
    private static string ResolveInside(string root, string relative)
    {
        if (string.IsNullOrWhiteSpace(relative) || Path.IsPathRooted(relative) || relative.Contains('\\') || relative.Contains(':') ||
            relative.Split('/').Any(part => part is "" or "." or ".."))
        {
            throw new InvalidDataException("Public document paths must stay below their configured root.");
        }

        var current = Path.GetFullPath(root);
        if ((System.IO.File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
        {
            throw new InvalidDataException("Linked public roots are forbidden.");
        }

        foreach (var segment in relative.Split('/'))
        {
            current = Path.Combine(current, segment);
            if ((System.IO.File.GetAttributes(current) & FileAttributes.ReparsePoint) != 0)
            {
                throw new InvalidDataException("Linked public document paths are forbidden.");
            }
        }

        return current;
    }
}
