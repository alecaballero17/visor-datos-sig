using Arquis.Backend.Data;
using Arquis.Backend.Models;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;

namespace Arquis.Backend.Services;

public sealed class GeoDataService(ArquisDbContext context, IConfiguration configuration)
{
    private int DefaultLimit => configuration.GetValue("Viewer:DefaultFeatureLimit", 1500);
    private int MaxLimit => configuration.GetValue("Viewer:MaxFeatureLimit", 5000);

    private static readonly IReadOnlyDictionary<string, (string Title, string Type, object Style)> LayerMetadata = new Dictionary<string, (string, string, object)>(StringComparer.OrdinalIgnoreCase)
    {
        ["manzanas"] = ("Manzanas", "Polygon", new { color="#dc2626", weight=2, fillOpacity=0.08 }),
        ["lotes"] = ("Lotes", "Polygon", new { color="#38bdf8", weight=1, fillOpacity=0.06 }),
        ["codigosfijos"] = ("Códigos fijos", "Point", new { color="#f59e0b", radius=3 }),
        ["vias"] = ("Vías", "LineString", new { color="#a855f7", weight=3 })
    };

    public async Task<IReadOnlyList<LayerInfo>> GetLayersAsync(CancellationToken ct)
    {
        var result = new List<LayerInfo>();
        foreach (var (key, meta) in LayerMetadata)
        {
            var extent = await GetExtentAsync(key, ct);
            result.Add(new LayerInfo(key, meta.Title, meta.Type, $"Id{meta.Title.Split(' ')[0]}", [], meta.Style, extent));
        }
        return result;
    }

    public async Task<object> GetGeoJsonAsync(string layer, string? bbox, string? query, int? limit, CancellationToken ct)
    {
        var take = Math.Clamp(limit ?? DefaultLimit, 1, MaxLimit);
        Geometry? bboxGeom = null;
        if (TryParseBbox(bbox, out var wkt))
        {
            bboxGeom = new NetTopologySuite.IO.WKTReader().Read(wkt);
            bboxGeom.SRID = 4326;
        }

        var qStr = query?.Trim();
        var features = new List<object>();
        var isTruncated = false;

        switch (layer.ToLowerInvariant())
        {
            case "manzanas":
                var qM = context.Manzanas.Where(m => m.Geom != null).AsQueryable();
                if (bboxGeom != null) qM = qM.Where(m => m.Geom!.Intersects(bboxGeom));
                if (!string.IsNullOrWhiteSpace(qStr)) qM = qM.Where(m => m.UV_MZA!.Contains(qStr) || m.UV!.Contains(qStr) || m.MZA!.Contains(qStr));
                
                var manzanas = await qM.OrderBy(m => m.IdManzana).Take(take).ToListAsync(ct);
                isTruncated = manzanas.Count >= take;
                features.AddRange(manzanas.Select(m => new {
                    type = "Feature", id = m.IdManzana, geometry = ToGeoJsonGeometry(m.Geom!),
                    properties = new { m.IdManzana, m.IdOrigen, m.UV_MZA, m.UV, m.MZA }
                }));
                break;

            case "lotes":
                var qL = context.Lotes.Where(l => l.Geom != null).AsQueryable();
                if (bboxGeom != null) qL = qL.Where(l => l.Geom!.Intersects(bboxGeom));
                if (!string.IsNullOrWhiteSpace(qStr)) qL = qL.Where(l => l.NroLote!.Contains(qStr));
                
                var lotesData = await qL.OrderBy(l => l.IdLote).Take(take)
                    .Select(l => new {
                        l,
                        TieneAgua = context.CodigosFijos.Any(c => c.IdLote == l.IdLote)
                    }).ToListAsync(ct);
                
                isTruncated = lotesData.Count >= take;
                features.AddRange(lotesData.Select(x => {
                    var point = x.l.Geom!.InteriorPoint;
                    return new {
                        type = "Feature", id = x.l.IdLote, geometry = ToGeoJsonGeometry(x.l.Geom!),
                        properties = new { x.l.IdLote, x.l.IdOrigen, x.l.NroLote, x.l.IdManzana, TieneAgua = x.TieneAgua, AguaLongitud = point.X, AguaLatitud = point.Y }
                    };
                }));
                break;

            case "codigosfijos":
                var qC = context.CodigosFijos.Where(c => c.Geom != null).AsQueryable();
                if (bboxGeom != null) qC = qC.Where(c => c.Geom!.Intersects(bboxGeom));
                if (!string.IsNullOrWhiteSpace(qStr)) qC = qC.Where(c => c.CodF_SIG!.Contains(qStr) || c.CodFijo.ToString()!.Contains(qStr) || c.Nombre!.Contains(qStr));
                
                var codigos = await qC.OrderBy(c => c.IdCodigo).Take(take).ToListAsync(ct);
                isTruncated = codigos.Count >= take;
                features.AddRange(codigos.Select(c => new {
                    type = "Feature", id = c.IdCodigo, geometry = ToGeoJsonGeometry(c.Geom!),
                    properties = new { c.IdCodigo, c.CodF_SQL, c.CodF_SIG, c.CodFijo, c.Nombre, c.Estado, c.EstadoVerificado, c.FechaCambioEstado, c.IdLote, c.Longitud, c.Latitud, TieneAgua = true }
                }));
                break;

            case "vias":
                var qV = context.Vias.Where(v => v.Geom != null).AsQueryable();
                if (bboxGeom != null) qV = qV.Where(v => v.Geom!.Intersects(bboxGeom));
                if (!string.IsNullOrWhiteSpace(qStr)) qV = qV.Where(v => v.Nombre!.Contains(qStr) || v.TipoVia!.Contains(qStr) || v.OSMID!.Contains(qStr));
                
                var vias = await qV.OrderBy(v => v.IdVia).Take(take).ToListAsync(ct);
                isTruncated = vias.Count >= take;
                features.AddRange(vias.Select(v => new {
                    type = "Feature", id = v.IdVia, geometry = ToGeoJsonGeometry(v.Geom!),
                    properties = new { v.IdVia, v.OBJECTID, v.Nombre, v.TipoVia, v.OSMID }
                }));
                break;

            default:
                throw new KeyNotFoundException("Capa no válida.");
        }

        return new { type = "FeatureCollection", name = layer, features, count = features.Count, truncated = isTruncated };
    }

    public async Task<object?> GetByIdAsync(string layer, int id, CancellationToken ct)
    {
        return layer.ToLowerInvariant() switch
        {
            "manzanas" => await context.Manzanas.Where(m => m.IdManzana == id && m.Geom != null)
                .Select(m => new { type = "Feature", id, geometry = ToGeoJsonGeometry(m.Geom!), properties = new { m.IdManzana, m.IdOrigen, m.UV_MZA, m.UV, m.MZA }, bbox = GetBbox(m.Geom!) }).FirstOrDefaultAsync(ct),
            
            "lotes" => await context.Lotes.Where(l => l.IdLote == id && l.Geom != null)
                .Select(l => new {
                    l, TieneAgua = context.CodigosFijos.Any(c => c.IdLote == l.IdLote)
                })
                .Select(x => new {
                    type = "Feature", id, geometry = ToGeoJsonGeometry(x.l.Geom!), 
                    properties = new { x.l.IdLote, x.l.IdOrigen, x.l.NroLote, x.l.IdManzana, TieneAgua = x.TieneAgua, AguaLongitud = x.l.Geom!.InteriorPoint.X, AguaLatitud = x.l.Geom!.InteriorPoint.Y }, bbox = GetBbox(x.l.Geom!)
                }).FirstOrDefaultAsync(ct),
            
            "codigosfijos" => await context.CodigosFijos.Where(c => c.IdCodigo == id && c.Geom != null)
                .Select(c => new { type = "Feature", id, geometry = ToGeoJsonGeometry(c.Geom!), properties = new { c.IdCodigo, c.CodF_SQL, c.CodF_SIG, c.CodFijo, c.Nombre, c.Estado, c.EstadoVerificado, c.FechaCambioEstado, c.IdLote, c.Longitud, c.Latitud, TieneAgua = true }, bbox = GetBbox(c.Geom!) }).FirstOrDefaultAsync(ct),
            
            "vias" => await context.Vias.Where(v => v.IdVia == id && v.Geom != null)
                .Select(v => new { type = "Feature", id, geometry = ToGeoJsonGeometry(v.Geom!), properties = new { v.IdVia, v.OBJECTID, v.Nombre, v.TipoVia, v.OSMID }, bbox = GetBbox(v.Geom!) }).FirstOrDefaultAsync(ct),
            
            _ => null
        };
    }

    public async Task<IReadOnlyList<SearchResult>> SearchAsync(string text, string? layer, int page, int pageSize, CancellationToken ct)
    {
        var qStr = (text ?? "").Trim();
        if (qStr.Length == 0) return [];
        page = Math.Max(1, page); pageSize = Math.Clamp(pageSize, 1, 100);

        var all = new List<SearchResult>();
        var checkLayer = string.IsNullOrWhiteSpace(layer) ? null : layer.ToLowerInvariant();

        if (checkLayer == null || checkLayer == "codigosfijos")
        {
            var dataC = await context.CodigosFijos.Where(c => c.Geom != null && (c.CodF_SIG!.Contains(qStr) || c.CodFijo.ToString()!.Contains(qStr) || c.Nombre!.Contains(qStr)))
                .Take(100).Select(c => new { c.IdCodigo, c.CodFijo, c.Nombre, c.Geom }).ToListAsync(ct);
            all.AddRange(dataC.Select(c => new SearchResult("codigosfijos", c.IdCodigo, $"{c.CodFijo} - {c.Nombre}", new Dictionary<string, object?> { ["IdCodigo"] = c.IdCodigo, ["CodFijo"] = c.CodFijo, ["Nombre"] = c.Nombre }, GetBbox(c.Geom!))));
        }
        if (checkLayer == null || checkLayer == "manzanas")
        {
            var dataM = await context.Manzanas.Where(m => m.Geom != null && (m.UV_MZA!.Contains(qStr) || m.UV!.Contains(qStr) || m.MZA!.Contains(qStr)))
                .Take(100).Select(m => new { m.IdManzana, m.UV, m.MZA, m.Geom }).ToListAsync(ct);
            all.AddRange(dataM.Select(m => new SearchResult("manzanas", m.IdManzana, $"UV {m.UV} / MZA {m.MZA}", new Dictionary<string, object?> { ["IdManzana"] = m.IdManzana, ["UV"] = m.UV, ["MZA"] = m.MZA }, GetBbox(m.Geom!))));
        }
        if (checkLayer == null || checkLayer == "lotes")
        {
            var dataL = await context.Lotes.Where(l => l.Geom != null && l.NroLote!.Contains(qStr))
                .Take(100).Select(l => new { l.IdLote, l.NroLote, l.Geom }).ToListAsync(ct);
            all.AddRange(dataL.Select(l => new SearchResult("lotes", l.IdLote, $"Lote {l.NroLote}", new Dictionary<string, object?> { ["IdLote"] = l.IdLote, ["NroLote"] = l.NroLote }, GetBbox(l.Geom!))));
        }
        if (checkLayer == null || checkLayer == "vias")
        {
            var dataV = await context.Vias.Where(v => v.Geom != null && (v.Nombre!.Contains(qStr) || v.TipoVia!.Contains(qStr) || v.OSMID!.Contains(qStr)))
                .Take(100).Select(v => new { v.IdVia, v.Nombre, v.Geom, v.TipoVia }).ToListAsync(ct);
            all.AddRange(dataV.Select(v => new SearchResult("vias", v.IdVia, $"{v.Nombre} {v.TipoVia}", new Dictionary<string, object?> { ["IdVia"] = v.IdVia, ["Nombre"] = v.Nombre }, GetBbox(v.Geom!))));
        }

        return all.Skip((page - 1) * pageSize).Take(pageSize).ToList();
    }

    private async Task<double[]?> GetExtentAsync(string layer, CancellationToken ct)
    {
        // Coordenadas del casco urbano de San Ignacio de Velasco [MinLon, MinLat, MaxLon, MaxLat]
        await Task.CompletedTask;
        return [-60.985, -16.425, -60.935, -16.365];
    }

    private static bool TryParseBbox(string? bbox, out string wkt)
    {
        wkt = "";
        if (string.IsNullOrWhiteSpace(bbox)) return false;
        var p = bbox.Split(',', StringSplitOptions.TrimEntries);
        if (p.Length != 4 || !p.Select(x => double.TryParse(x, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out _)).All(x => x)) return false;
        var nums = p.Select(x => double.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
        var minX = nums[0]; var minY = nums[1]; var maxX = nums[2]; var maxY = nums[3];
        if (minX >= maxX || minY >= maxY) return false;
        wkt = FormattableString.Invariant($"POLYGON(({minX} {minY},{maxX} {minY},{maxX} {maxY},{minX} {maxY},{minX} {minY}))");
        return true;
    }

    private static object ToGeoJsonGeometry(Geometry g) => g switch
    {
        Point p => new { type = "Point", coordinates = new[] { p.X, p.Y } },
        LineString l => new { type = "LineString", coordinates = l.Coordinates.Select(c => new[] { c.X, c.Y }).ToArray() },
        Polygon p => new { type = "Polygon", coordinates = PolygonCoords(p) },
        MultiPoint mp => new { type = "MultiPoint", coordinates = mp.Geometries.Cast<Point>().Select(p => new[] { p.X, p.Y }).ToArray() },
        MultiLineString ml => new { type = "MultiLineString", coordinates = ml.Geometries.Cast<LineString>().Select(l => l.Coordinates.Select(c => new[] { c.X, c.Y }).ToArray()).ToArray() },
        MultiPolygon mp => new { type = "MultiPolygon", coordinates = mp.Geometries.Cast<Polygon>().Select(PolygonCoords).ToArray() },
        GeometryCollection gc => new { type = "GeometryCollection", geometries = gc.Geometries.Select(ToGeoJsonGeometry).ToArray() },
        _ => throw new NotSupportedException($"Geometría {g.GeometryType} no soportada.")
    };

    private static double[][][] PolygonCoords(Polygon p)
    {
        var rings = new List<double[][]> { p.ExteriorRing.Coordinates.Select(c => new[] { c.X, c.Y }).ToArray() };
        for (var i = 0; i < p.NumInteriorRings; i++) rings.Add(p.GetInteriorRingN(i).Coordinates.Select(c => new[] { c.X, c.Y }).ToArray());
        return rings.ToArray();
    }

    private static double[] GetBbox(Geometry g)
    {
        var e = g.EnvelopeInternal; return [e.MinX, e.MinY, e.MaxX, e.MaxY];
    }
}
