using System.Reflection;
using System.Security.Cryptography;
using System.Text.Json;
using CShells.AspNetCore.Features;
using CShells.Features;
using Microsoft.AspNetCore.Builder;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.OpenApi;
using Microsoft.AspNetCore.Routing;
using Microsoft.Extensions.DependencyInjection.Extensions;

namespace ProgramKit.OpenApiExport;

/// <summary>Produces OpenAPI from staged feature registration without starting application services.</summary>
internal static class Exporter
{
    /// <summary>Identifies the exact managed exporter contract implemented by this binary.</summary>
    private const string ToolVersion = "0.9.9-preview.1";

    /// <summary>Runs one export and converts deterministic contract failures to PKO200 diagnostics.</summary>
    public static async Task<int> RunAsync(string[] args)
    {
        try
        {
            var options = Arguments.Parse(args);
            await ExportAsync(options).ConfigureAwait(false);
            return 0;
        }
        catch (Exception exception)
        {
            Console.Error.WriteLine($"PKO200 {exception.Message}");
            return 2;
        }
    }

    /// <summary>Composes feature registrations and endpoint descriptions into one raw document.</summary>
    private static async Task ExportAsync(Arguments options)
    {
        var contract = Contract.Load(options.Contract);
        if (!string.Equals(contract.ProducerVersion, ToolVersion, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"contract requires exporter {contract.ProducerVersion}, but this tool is {ToolVersion}.");
        }

        using var shells = JsonDocument.Parse(
            await File.ReadAllTextAsync(options.Shells).ConfigureAwait(false));
        var shell = Shell.Read(shells.RootElement, contract.Shell);
        var packages = PackageSet.Load(options.Packages);
        var descriptors = packages.FeatureDescriptors;
        var missing = shell.Features.Where(feature => !descriptors.ContainsKey(feature)).Order().ToArray();
        if (missing.Length > 0)
        {
            throw new InvalidOperationException(
                "activated features have no unique staged package descriptor: " + string.Join(", ", missing));
        }

        var contractFeatures = contract.Features.ToHashSet(StringComparer.Ordinal);
        var inactive = contractFeatures.Where(feature => !shell.Features.Contains(feature)).Order().ToArray();
        if (inactive.Length > 0)
        {
            throw new InvalidOperationException(
                "contract features are not activated for shell " +
                $"'{contract.Shell}': {string.Join(", ", inactive)}.");
        }
        var undescribed = contractFeatures.Where(feature => !descriptors.ContainsKey(feature)).Order().ToArray();
        if (undescribed.Length > 0)
        {
            throw new InvalidOperationException(
                "contract features have no unique staged package descriptor: " +
                string.Join(", ", undescribed));
        }
        ValidateDependenciesAndRoutes(shell.Features, descriptors);
        var routeContributors = shell.Features.Where(feature =>
                !BuiltInFeatures.Definitions.ContainsKey(feature) &&
                descriptors.TryGetValue(feature, out var descriptor) && descriptor.Routes.Length > 0)
            .ToHashSet(StringComparer.Ordinal);
        var uncovered = routeContributors.Except(contractFeatures).Order().ToArray();
        if (uncovered.Length > 0)
        {
            throw new InvalidOperationException(
                "contract feature coverage omits activated route contributors: " +
                string.Join(", ", uncovered));
        }

        var composed = shell.Features.Where(feature =>
                !BuiltInFeatures.Definitions.TryGetValue(feature, out var definition) ||
                definition.ComposeForOpenApi)
            .ToHashSet(StringComparer.Ordinal);
        var ordered = TopologicalOrder(composed, shell.Features.ToHashSet(StringComparer.Ordinal), descriptors);
        using var resolver = new AssemblyResolver(packages.Assemblies);
        var features = ordered.Select(identity =>
            LoadFeature(identity, descriptors[identity], resolver, shell.Settings)).ToArray();

        var builder = WebApplication.CreateBuilder(new WebApplicationOptions
        {
            ApplicationName = typeof(Exporter).Assembly.FullName,
            ContentRootPath = options.Repository,
            EnvironmentName = Environments.Development,
        });
        builder.Configuration.Sources.Clear();
        builder.Configuration.AddJsonStream(File.OpenRead(options.HostSettings));
        builder.Configuration.AddJsonStream(File.OpenRead(options.Shells));
        foreach (var feature in features)
            feature.ConfigureServices(builder.Services);
        builder.Services.RemoveAll<IHostedService>();
        builder.Services.RemoveAll<IServer>();
        builder.Services.AddSingleton<IServer, NoopServer>();

        await using var application = builder.Build();
        IEndpointRouteBuilder endpoints = application;
        if (!string.IsNullOrEmpty(shell.RoutePrefix))
            endpoints = application.MapGroup(shell.RoutePrefix);
        foreach (var feature in features.OfType<IWebShellFeature>())
            feature.MapEndpoints(endpoints, application.Environment);
        await application.StartAsync().ConfigureAwait(false);
        var composedRoutes = ((IEndpointRouteBuilder)application).DataSources
            .SelectMany(source => source.Endpoints)
            .OfType<RouteEndpoint>().Select(endpoint => endpoint.RoutePattern.RawText).ToArray();
        if (composedRoutes.Length == 0)
            throw new InvalidOperationException("the composed web features registered no route endpoints.");

        var providerType = typeof(OpenApiOptions).Assembly.GetType(
            "Microsoft.Extensions.ApiDescriptions.IDocumentProvider", throwOnError: true)!;
        var provider = application.Services.GetService(providerType)
            ?? throw new InvalidOperationException(
                "the composed features did not register Microsoft.AspNetCore.OpenApi; " +
                "an activated platform web-boundary feature must call AddOpenApi.");
        var documentNames = providerType.GetMethod("GetDocumentNames")?.Invoke(provider, null)
            as IEnumerable<string> ?? [];
        if (!documentNames.Contains(contract.DocumentName, StringComparer.Ordinal))
        {
            throw new InvalidOperationException(
                $"OpenAPI document '{contract.DocumentName}' is not registered by the composed features.");
        }

        var first = await GenerateAsync(provider, contract.DocumentName).ConfigureAwait(false);
        var second = await GenerateAsync(provider, contract.DocumentName).ConfigureAwait(false);
        if (!first.AsSpan().SequenceEqual(second))
            throw new InvalidOperationException("composed OpenAPI generation is not byte-deterministic.");

        Directory.CreateDirectory(Path.GetDirectoryName(options.Output)!);
        await File.WriteAllBytesAsync(options.Output, first).ConfigureAwait(false);
        await WriteEvidenceAsync(
            options,
            contract,
            packages,
            ordered,
            contractFeatures.Order().ToArray(),
            first).ConfigureAwait(false);
        await application.StopAsync().ConfigureAwait(false);
        Console.WriteLine(
            $"exported composed OpenAPI contract '{contract.Identity}' to {options.Output}");
    }

    /// <summary>Serializes one registered document through ASP.NET Core's build-time provider contract.</summary>
    private static async Task<byte[]> GenerateAsync(object provider, string documentName)
    {
        using var writer = new StringWriter(System.Globalization.CultureInfo.InvariantCulture);
        var method = provider.GetType().GetMethod(
            "GenerateAsync", [typeof(string), typeof(TextWriter)])
            ?? throw new InvalidOperationException(
                "the OpenAPI document provider has no supported GenerateAsync method.");
        var task = method.Invoke(provider, [documentName, writer]) as Task
            ?? throw new InvalidOperationException(
                "the OpenAPI document provider returned no generation task.");
        await task.ConfigureAwait(false);
        return System.Text.Encoding.UTF8.GetBytes(writer.ToString());
    }

    /// <summary>Loads the single composition adapter governed by a feature package descriptor.</summary>
    private static IShellFeature LoadFeature(
        string identity,
        FeatureDescriptor descriptor,
        AssemblyResolver resolver,
        CShells.ShellSettings settings)
    {
        var assembly = resolver.Load(descriptor.AssemblyName);
        Type[] types;
        try
        {
            types = assembly.GetTypes();
        }
        catch (ReflectionTypeLoadException exception)
        {
            var details = string.Join(
                "; ",
                exception.LoaderExceptions.Where(item => item is not null).Select(item => item!.Message));
            throw new InvalidOperationException(
                $"cannot inspect feature '{identity}': {details}", exception);
        }
        var candidates = types.Where(type =>
                !type.IsAbstract && !type.IsInterface && typeof(IShellFeature).IsAssignableFrom(type))
            .ToArray();
        if (candidates.Length != 1)
        {
            throw new InvalidOperationException(
                $"feature package '{descriptor.PackageId}' must expose exactly one IShellFeature; " +
                $"found {candidates.Length}.");
        }
        var attribute = candidates[0].GetCustomAttribute<ShellFeatureAttribute>();
        if (!string.Equals(attribute?.Name, identity, StringComparison.Ordinal))
        {
            throw new InvalidOperationException(
                $"feature package '{descriptor.PackageId}' declares descriptor identity '{identity}', but " +
                $"CLR type '{candidates[0].FullName}' does not declare the exact [ShellFeature] identity.");
        }
        var constructors = candidates[0].GetConstructors();
        var settingsConstructor = constructors.SingleOrDefault(constructor =>
            constructor.GetParameters() is [{ ParameterType: var parameterType }] &&
            parameterType == typeof(CShells.ShellSettings));
        var parameterless = constructors.SingleOrDefault(constructor => constructor.GetParameters().Length == 0);
        var instance = settingsConstructor is not null
            ? settingsConstructor.Invoke([settings])
            : parameterless?.Invoke(null);
        return instance as IShellFeature
            ?? throw new InvalidOperationException(
                $"feature '{identity}' must have a public parameterless or ShellSettings constructor.");
    }

    /// <summary>Validates active dependencies and unique route ownership for every staged feature.</summary>
    private static void ValidateDependenciesAndRoutes(
        IReadOnlyCollection<string> active,
        IReadOnlyDictionary<string, FeatureDescriptor> descriptors)
    {
        var activeSet = active.ToHashSet(StringComparer.Ordinal);
        var routes = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
        foreach (var identity in active.Order())
        {
            var descriptor = descriptors[identity];
            foreach (var dependency in descriptor.Dependencies.Order())
            {
                if (!activeSet.Contains(dependency))
                    throw new InvalidOperationException(
                        $"feature '{identity}' requires inactive feature '{dependency}'.");
            }
            foreach (var route in descriptor.Routes.Order())
            {
                if (routes.TryGetValue(route, out var previous) && previous != identity)
                    throw new InvalidOperationException(
                        $"route collision '{route}' between features '{previous}' and '{identity}'.");
                routes[route] = identity;
            }
        }
    }

    /// <summary>Orders activated features by their governed metadata dependencies.</summary>
    private static string[] TopologicalOrder(
        IReadOnlySet<string> active,
        IReadOnlySet<string> shellFeatures,
        IReadOnlyDictionary<string, FeatureDescriptor> descriptors)
    {
        var result = new List<string>();
        var visiting = new HashSet<string>(StringComparer.Ordinal);
        var visited = new HashSet<string>(StringComparer.Ordinal);
        void Visit(string identity)
        {
            if (visited.Contains(identity))
                return;
            if (!visiting.Add(identity))
                throw new InvalidOperationException($"feature dependency cycle includes '{identity}'.");
            foreach (var dependency in descriptors[identity].Dependencies.Order())
            {
                if (!shellFeatures.Contains(dependency))
                {
                    throw new InvalidOperationException(
                        $"feature '{identity}' requires inactive feature '{dependency}'.");
                }
                if (active.Contains(dependency))
                    Visit(dependency);
            }
            visiting.Remove(identity);
            visited.Add(identity);
            result.Add(identity);
        }
        foreach (var identity in active.Order())
            Visit(identity);
        return result.ToArray();
    }

    /// <summary>Writes hash-bound evidence for package, configuration, and output identity.</summary>
    private static async Task WriteEvidenceAsync(
        Arguments options,
        Contract contract,
        PackageSet packages,
        string[] ordered,
        string[] contractFeatures,
        byte[] document)
    {
        var evidence = new
        {
            schemaVersion = 1,
            producer = new { kind = "ProgramKit.OpenApi.Exporter", version = ToolVersion },
            contract = contract.Identity,
            documentName = contract.DocumentName,
            shell = contract.Shell,
            composedFeatures = ordered,
            contractFeatures,
            packages = packages.Hashes.OrderBy(item => item.Key)
                .Select(item => new { file = item.Key, sha256 = item.Value }),
            inputs = new
            {
                shellsSha256 = Hash(options.Shells),
                hostsettingsSha256 = Hash(options.HostSettings),
                contractSha256 = Hash(options.Contract),
            },
            rawDocument = new
            {
                path = options.Output,
                sha256 = Convert.ToHexStringLower(SHA256.HashData(document)),
            },
            sideEffects = new
            {
                listenerStarted = false,
                consumerHostedServicesStarted = false,
                shellInitializersRun = false,
                pipelineMaterialized = true,
            },
        };
        Directory.CreateDirectory(Path.GetDirectoryName(options.Evidence)!);
        await File.WriteAllTextAsync(
            options.Evidence,
            JsonSerializer.Serialize(evidence, new JsonSerializerOptions { WriteIndented = true }) + "\n")
            .ConfigureAwait(false);
    }

    /// <summary>Computes the lowercase SHA-256 identity of one input file.</summary>
    private static string Hash(string path) =>
        Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path)));
}
