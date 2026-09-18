namespace Arquis.Backend.Models;

public sealed record LayerInfo(
    string Key,
    string Title,
    string GeometryType,
    string IdField,
    IReadOnlyList<string> SearchableFields,
    object Style,
    double[]? Extent);

public sealed record SearchResult(
    string Layer,
    int Id,
    string Label,
    IReadOnlyDictionary<string, object?> Properties,
    double[]? Bbox);
