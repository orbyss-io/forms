namespace ProgramKit.Forms;

/// <summary>Controls element visibility through a bounded declarative field comparison.</summary>
public sealed record FormVisibilityCondition(string FieldId, FormConditionOperator Operator, string? Value = null);
