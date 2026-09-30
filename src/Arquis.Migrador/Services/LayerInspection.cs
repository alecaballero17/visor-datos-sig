namespace Arquis.Migrador.Services;

public sealed record LayerInspection(
    string DisplayName,
    string FileName,
    string GeometryType,
    int? RecordCount,
    string Extent,
    string Status);
