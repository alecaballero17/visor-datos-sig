using System.Buffers.Binary;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace Arquis.Migrador.Services;

public sealed class ShapefileValidator
{
    private static readonly LayerDefinition[] Layers =
    [
        new("Manzanas", "Exp_MapaBase_MZA_4326", [5, 15, 25]),
        new("Lotes", "Exp_MapaBase_LOTES_4326", [5, 15, 25]),
        new("Códigos fijos", "Exp_CodigoFijo_4326", [1, 8]),
        new("Vías", "Exp_MapaBase_VIAS_4326", [3, 13, 23])
    ];

    public IReadOnlyList<LayerInspection> InspectFolder(string folder)
        => Layers.Select(layer => InspectLayer(folder, layer)).ToArray();

    private static LayerInspection InspectLayer(string folder, LayerDefinition layer)
    {
        var stem = Path.Combine(folder, layer.Stem);
        var required = new[] { ".shp", ".shx", ".dbf", ".prj" };
        var missing = required.Where(extension => !File.Exists(stem + extension)).ToArray();
        if (missing.Length > 0)
            return new(layer.Name, Path.GetFileName(stem + ".shp"), "-", null, "-", $"Faltan archivos obligatorios: {string.Join(", ", missing)}.");

        try
        {
            var projection = File.ReadAllText(stem + ".prj", Encoding.UTF8);
            if (!IsWgs84(projection))
                return new(layer.Name, Path.GetFileName(stem + ".shp"), "-", null, "-", "La proyección no declara WGS 84 / EPSG:4326; la carga queda bloqueada.");

            var header = ReadShpHeader(stem + ".shp");
            if (!layer.AllowedShapeTypes.Contains(header.ShapeType))
                return new(layer.Name, Path.GetFileName(stem + ".shp"), ShapeName(header.ShapeType), null, FormatExtent(header), "El tipo de geometría no corresponde a la capa esperada.");

            var count = ReadDbfRecordCount(stem + ".dbf");
            return new(layer.Name, Path.GetFileName(stem + ".shp"), ShapeName(header.ShapeType), count, FormatExtent(header), "Validación básica correcta: componentes, WGS 84, tipo y conteo detectados.");
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or InvalidDataException)
        {
            return new(layer.Name, Path.GetFileName(stem + ".shp"), "-", null, "-", $"No se pudo leer la capa: {ex.Message}");
        }
    }

    private static bool IsWgs84(string prj)
        => prj.Contains("WGS_1984", StringComparison.OrdinalIgnoreCase)
           || prj.Contains("WGS 84", StringComparison.OrdinalIgnoreCase)
           || prj.Contains("EPSG", StringComparison.OrdinalIgnoreCase) && prj.Contains("4326", StringComparison.OrdinalIgnoreCase);

    private static ShpHeader ReadShpHeader(string path)
    {
        using var stream = File.OpenRead(path);
        Span<byte> header = stackalloc byte[100];
        if (stream.Read(header) != header.Length) throw new InvalidDataException("El encabezado SHP está incompleto.");
        if (BinaryPrimitives.ReadInt32BigEndian(header) != 9994) throw new InvalidDataException("El archivo no tiene una firma SHP válida.");
        if (BinaryPrimitives.ReadInt32LittleEndian(header[28..]) != 1000) throw new InvalidDataException("La versión SHP no es válida.");
        return new(
            BinaryPrimitives.ReadInt32LittleEndian(header[32..]),
            BitConverter.ToDouble(header[36..44]), BitConverter.ToDouble(header[44..52]),
            BitConverter.ToDouble(header[52..60]), BitConverter.ToDouble(header[60..68]));
    }

    private static int ReadDbfRecordCount(string path)
    {
        using var stream = File.OpenRead(path);
        Span<byte> header = stackalloc byte[32];
        if (stream.Read(header) != header.Length) throw new InvalidDataException("El encabezado DBF está incompleto.");
        return BinaryPrimitives.ReadInt32LittleEndian(header[4..]);
    }

    private static string ShapeName(int type) => type switch { 1 => "Point", 3 => "LineString", 5 => "Polygon", 8 => "MultiPoint", 13 => "PolyLine Z", 15 => "Polygon Z", 23 => "PolyLine M", 25 => "Polygon M", _ => $"Tipo {type}" };
    private static string FormatExtent(ShpHeader header) => $"{header.MinX.ToString("F5", CultureInfo.InvariantCulture)}, {header.MinY.ToString("F5", CultureInfo.InvariantCulture)} a {header.MaxX.ToString("F5", CultureInfo.InvariantCulture)}, {header.MaxY.ToString("F5", CultureInfo.InvariantCulture)}";

    private sealed record LayerDefinition(string Name, string Stem, int[] AllowedShapeTypes);
    private sealed record ShpHeader(int ShapeType, double MinX, double MinY, double MaxX, double MaxY);
}
