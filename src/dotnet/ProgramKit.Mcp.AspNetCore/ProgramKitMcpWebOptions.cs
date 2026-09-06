namespace ProgramKit.Mcp.AspNetCore;

/// <summary>Configures the shared authenticated stateless MCP transport endpoint.</summary>
public sealed class ProgramKitMcpWebOptions
{
    /// <summary>Names the shell configuration section.</summary>
    public const string SectionName = "ProgramKit:Mcp";
    /// <summary>Gets or sets the fixed Streamable HTTP route.</summary>
    public string Route { get; set; } = "/program-kit/mcp";
    /// <summary>Gets or sets the policy; null or whitespace uses the host default policy.</summary>
    public string? Policy { get; set; }
}
