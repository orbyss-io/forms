namespace Orbyss.Forms;

/// <summary>Returns a bounded page of form catalog results and an optional total.</summary>
/// <typeparam name="T">The catalog projection type.</typeparam>
public sealed record FormPage<T>(IReadOnlyList<T> Items, int? Total = null);
