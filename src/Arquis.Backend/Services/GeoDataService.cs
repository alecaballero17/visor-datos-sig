using System.Data;
using Arquis.Backend.Data;
using Arquis.Backend.Models;
using Microsoft.Data.SqlClient;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO;

namespace Arquis.Backend.Services;

public sealed class GeoDataService(SqlConnectionFactory connectionFactory, IConfiguration configuration)
{
    private sealed record LayerDef(string Key, string Table, string Id, string[] Columns, string[] Search, string GeometryType, object Style);

    private static readonly IReadOnlyDictionary<string, LayerDef> Layers = new Dictionary<string, LayerDef>(StringComparer.OrdinalIgnoreCase)
    {
        ["manzanas"] = new("manzanas", "dbo.Manzanas", "IdManzana", ["IdOrigen","UV_MZA","UV","MZA"], ["UV_MZA","UV","MZA"], "Polygon", new { color="#dc2626", weight=2, fillOpacity=0.08 }),
        ["lotes"] = new("lotes", "dbo.Lotes", "IdLote", ["IdOrigen","NroLote","IdManzana"], ["NroLote"], "Polygon", new { color="#38bdf8", weight=1, fillOpacity=0.06 }),
        ["codigosfijos"] = new("codigosfijos", "dbo.CodigosFijos", "IdCodigo", ["CodF_SQL","CodF_SIG","CodFijo","Nombre","Estado","EstadoVerificado","FechaCambioEstado","IdLote","Longitud","Latitud"], ["CodF_SIG","CodFijo","Nombre"], "Point", new { color="#f59e0b", radius=3 }),
        ["vias"] = new("vias", "dbo.Vias", "IdVia", ["OBJECTID","Nombre","TipoVia","OSMID"], ["Nombre","TipoVia","OSMID"], "LineString", new { color="#a855f7", weight=3 })
    };

    private int DefaultLimit => configuration.GetValue("Viewer:DefaultFeatureLimit", 1500);
    private int MaxLimit => configuration.GetValue("Viewer:MaxFeatureLimit", 5000);

    public async Task<IReadOnlyList<LayerInfo>> GetLayersAsync(CancellationToken ct)
    {
        var result = new List<LayerInfo>();
        foreach (var def in Layers.Values)
            result.Add(new LayerInfo(def.Key, Title(def.Key), def.GeometryType, def.Id, def.Search, def.Style, await GetExtentAsync(def, ct)));
        return result;
    }

    public async Task<object> GetGeoJsonAsync(string layer, string? bbox, string? query, int? limit, CancellationToken ct)
    {
        var def = GetLayer(layer);
        var take = Math.Clamp(limit ?? DefaultLimit, 1, MaxLimit);
        var sql = $"SELECT TOP (@Take) {Escape(def.Id)} AS FeatureId, {string.Join(",", def.Columns.Select(Escape))}, {WaterColumns(def)}Geom.STAsText() AS Wkt FROM {def.Table} AS entidad WHERE Geom IS NOT NULL";
        var parameters = new List<SqlParameter> { new("@Take", SqlDbType.Int) { Value = take } };

        if (TryParseBbox(bbox, out var bboxWkt))
        {
            sql += " AND Geom.STIntersects(geometry::STGeomFromText(@BboxWkt,4326)) = 1";
            parameters.Add(new SqlParameter("@BboxWkt", SqlDbType.NVarChar, -1) { Value = bboxWkt });
        }
        if (!string.IsNullOrWhiteSpace(query) && def.Search.Length > 0)
        {
            var clauses = def.Search.Select(c => $"CONVERT(NVARCHAR(200),{Escape(c)}) LIKE @Q");
            sql += " AND (" + string.Join(" OR ", clauses) + ")";
            parameters.Add(new SqlParameter("@Q", SqlDbType.NVarChar, 220) { Value = $"%{query.Trim()}%" });
        }
        sql += $" ORDER BY {Escape(def.Id)}";

        await using var cn = connectionFactory.Create();
        await cn.OpenAsync(ct);
        await using var cmd = new SqlCommand(sql, cn);
        cmd.Parameters.AddRange(parameters.ToArray());
        await using var rd = await cmd.ExecuteReaderAsync(ct);
        var features = new List<object>();
        var wktReader = new WKTReader();
        while (await rd.ReadAsync(ct))
        {
            var props = new Dictionary<string, object?> { [def.Id] = rd["FeatureId"] };
            foreach (var col in def.Columns) props[col] = rd[col] is DBNull ? null : rd[col];
            var geom = wktReader.Read(Convert.ToString(rd["Wkt"])!);
            AddWaterProperties(def, props, rd, geom);
            features.Add(new { type="Feature", id=rd["FeatureId"], geometry=ToGeoJsonGeometry(geom), properties=props });
        }
        return new { type="FeatureCollection", name=def.Key, features, count=features.Count, truncated=features.Count >= take };
    }

    public async Task<object?> GetByIdAsync(string layer, int id, CancellationToken ct)
    {
        var def = GetLayer(layer);
        var sql = $"SELECT {Escape(def.Id)} AS FeatureId, {string.Join(",", def.Columns.Select(Escape))}, {WaterColumns(def)}Geom.STAsText() AS Wkt FROM {def.Table} AS entidad WHERE {Escape(def.Id)}=@Id AND Geom IS NOT NULL";
        await using var cn = connectionFactory.Create();
        await cn.OpenAsync(ct);
        await using var cmd = new SqlCommand(sql, cn);
        cmd.Parameters.Add(new SqlParameter("@Id", SqlDbType.Int){Value=id});
        await using var rd = await cmd.ExecuteReaderAsync(ct);
        if (!await rd.ReadAsync(ct)) return null;
        var props = new Dictionary<string, object?> { [def.Id] = rd["FeatureId"] };
        foreach (var col in def.Columns) props[col] = rd[col] is DBNull ? null : rd[col];
        var geom = new WKTReader().Read(Convert.ToString(rd["Wkt"])!);
        AddWaterProperties(def, props, rd, geom);
        return new { type="Feature", id, geometry=ToGeoJsonGeometry(geom), properties=props, bbox=GetBbox(geom) };
    }

    public async Task<IReadOnlyList<SearchResult>> SearchAsync(string text, string? layer, int page, int pageSize, CancellationToken ct)
    {
        text = (text ?? "").Trim();
        if (text.Length == 0) return [];
        page = Math.Max(1, page); pageSize = Math.Clamp(pageSize, 1, 100);
        var targets = string.IsNullOrWhiteSpace(layer) ? Layers.Values : [GetLayer(layer)];
        var all = new List<SearchResult>();
        foreach (var def in targets)
        {
            var labelExpr = def.Key switch
            {
                "codigosfijos" => "CONCAT(CodFijo, ' - ', ISNULL(Nombre,''))",
                "manzanas" => "CONCAT('UV ',ISNULL(UV,''),' / MZA ',ISNULL(MZA,''))",
                "lotes" => "CONCAT('Lote ',ISNULL(NroLote,''))",
                "vias" => "CONCAT(ISNULL(Nombre,''),' ',ISNULL(TipoVia,''))",
                _ => $"CONVERT(NVARCHAR(50),{Escape(def.Id)})"
            };
            var searchClauses = string.Join(" OR ", def.Search.Select(c => $"CONVERT(NVARCHAR(200),{Escape(c)}) LIKE @Q"));
            var sql = $"SELECT TOP (100) {Escape(def.Id)} AS FeatureId, {labelExpr} AS Label, {string.Join(",", def.Columns.Select(Escape))}, Geom.STAsText() AS Wkt FROM {def.Table} WHERE Geom IS NOT NULL AND ({searchClauses}) ORDER BY {Escape(def.Id)}";
            await using var cn = connectionFactory.Create();
            await cn.OpenAsync(ct);
            await using var cmd = new SqlCommand(sql, cn);
            cmd.Parameters.Add(new SqlParameter("@Q", SqlDbType.NVarChar, 220){Value=$"%{text}%"});
            await using var rd = await cmd.ExecuteReaderAsync(ct);
            var wkt = new WKTReader();
            while (await rd.ReadAsync(ct))
            {
                var props = new Dictionary<string, object?>();
                foreach (var col in def.Columns) props[col] = rd[col] is DBNull ? null : rd[col];
                var g = wkt.Read(Convert.ToString(rd["Wkt"])!);
                all.Add(new SearchResult(def.Key, Convert.ToInt32(rd["FeatureId"]), Convert.ToString(rd["Label"]) ?? def.Key, props, GetBbox(g)));
            }
        }
        return all.Skip((page-1)*pageSize).Take(pageSize).ToList();
    }

    private async Task<double[]?> GetExtentAsync(LayerDef def, CancellationToken ct)
    {
        var sql = $"SELECT geometry::EnvelopeAggregate(Geom).STEnvelope().STAsText() FROM {def.Table} WHERE Geom IS NOT NULL";
        try
        {
            await using var cn = connectionFactory.Create();
            await cn.OpenAsync(ct);
            await using var cmd = new SqlCommand(sql, cn);
            var raw = await cmd.ExecuteScalarAsync(ct);
            if (raw is null or DBNull) return null;
            var g = new WKTReader().Read(Convert.ToString(raw)!);
            return GetBbox(g);
        }
        catch { return null; }
    }

    private static string WaterColumns(LayerDef def) => def.Key == "lotes"
        ? "CAST(CASE WHEN EXISTS (SELECT 1 FROM dbo.CodigosFijos c WHERE c.IdLote=entidad.IdLote) OR EXISTS (SELECT 1 FROM dbo.CodigosFijos c WITH (INDEX(SIX_CodigosFijos_Geom)) WHERE c.Geom.STIntersects(entidad.Geom)=1) THEN 1 ELSE 0 END AS bit) AS TieneAgua, "
        : "";

    private static void AddWaterProperties(LayerDef def, Dictionary<string, object?> props, System.Data.Common.DbDataReader rd, Geometry geom)
    {
        if (def.Key == "codigosfijos") props["TieneAgua"] = true;
        if (def.Key != "lotes") return;
        props["TieneAgua"] = (bool)rd["TieneAgua"];
        var point = geom.InteriorPoint;
        props["AguaLongitud"] = point.X;
        props["AguaLatitud"] = point.Y;
    }

    private static LayerDef GetLayer(string key) => Layers.TryGetValue(key, out var d) ? d : throw new KeyNotFoundException("Capa no válida.");
    private static string Escape(string identifier) => $"[{identifier.Replace("]", "]]", StringComparison.Ordinal)}]";
    private static string Title(string key) => key switch { "manzanas"=>"Manzanas", "lotes"=>"Lotes", "codigosfijos"=>"Códigos fijos", "vias"=>"Vías", _=>key };

    private static bool TryParseBbox(string? bbox, out string wkt)
    {
        wkt = "";
        if (string.IsNullOrWhiteSpace(bbox)) return false;
        var p = bbox.Split(',', StringSplitOptions.TrimEntries);
        if (p.Length != 4 || !p.Select(x => double.TryParse(x, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out _)).All(x => x)) return false;
        var nums = p.Select(x => double.Parse(x, System.Globalization.CultureInfo.InvariantCulture)).ToArray();
        var minX=nums[0]; var minY=nums[1]; var maxX=nums[2]; var maxY=nums[3];
        if (minX>=maxX || minY>=maxY) return false;
        wkt = FormattableString.Invariant($"POLYGON(({minX} {minY},{maxX} {minY},{maxX} {maxY},{minX} {maxY},{minX} {minY}))");
        return true;
    }

    private static object ToGeoJsonGeometry(Geometry g) => g switch
    {
        Point p => new { type="Point", coordinates=new[]{p.X,p.Y} },
        LineString l => new { type="LineString", coordinates=l.Coordinates.Select(c => new[]{c.X,c.Y}).ToArray() },
        Polygon p => new { type="Polygon", coordinates=PolygonCoords(p) },
        MultiPoint mp => new { type="MultiPoint", coordinates=mp.Geometries.Cast<Point>().Select(p=>new[]{p.X,p.Y}).ToArray() },
        MultiLineString ml => new { type="MultiLineString", coordinates=ml.Geometries.Cast<LineString>().Select(l=>l.Coordinates.Select(c=>new[]{c.X,c.Y}).ToArray()).ToArray() },
        MultiPolygon mp => new { type="MultiPolygon", coordinates=mp.Geometries.Cast<Polygon>().Select(PolygonCoords).ToArray() },
        GeometryCollection gc => new { type="GeometryCollection", geometries=gc.Geometries.Select(ToGeoJsonGeometry).ToArray() },
        _ => throw new NotSupportedException($"Geometría {g.GeometryType} no soportada.")
    };

    private static double[][][] PolygonCoords(Polygon p)
    {
        var rings = new List<double[][]> { p.ExteriorRing.Coordinates.Select(c=>new[]{c.X,c.Y}).ToArray() };
        for (var i=0;i<p.NumInteriorRings;i++) rings.Add(p.GetInteriorRingN(i).Coordinates.Select(c=>new[]{c.X,c.Y}).ToArray());
        return rings.ToArray();
    }

    private static double[] GetBbox(Geometry g)
    {
        var e=g.EnvelopeInternal; return [e.MinX,e.MinY,e.MaxX,e.MaxY];
    }
}
