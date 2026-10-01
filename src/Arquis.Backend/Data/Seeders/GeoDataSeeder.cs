using System;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Data.Seeders
{
    public static class GeoDataSeeder
    {
        public static async Task SeedAsync(ArquisDbContext context)
        {
            // Walk up from the assembly directory until we find 03_DatosPrueba or hit the drive root
            var dir = new System.IO.DirectoryInfo(AppContext.BaseDirectory);
            string? foundBase = null;
            while (dir != null)
            {
                var candidate = System.IO.Path.Combine(dir.FullName, "03_DatosPrueba", "DatosSIG_Reproj");
                if (System.IO.Directory.Exists(candidate)) { foundBase = candidate; break; }
                dir = dir.Parent;
            }
            var basePath = foundBase ?? System.IO.Path.GetFullPath(System.IO.Path.Combine(AppContext.BaseDirectory, "../../../../03_DatosPrueba/DatosSIG_Reproj"));
            if (!System.IO.Directory.Exists(basePath)) return;

            var factory = NetTopologySuite.NtsGeometryServices.Instance.CreateGeometryFactory(4326);

            int GetIdx(NetTopologySuite.IO.ShapefileDataReader r, string name)
            {
                for (int i = 0; i < r.DbaseHeader.NumFields; i++)
                {
                    if (r.DbaseHeader.Fields[i].Name.Equals(name, StringComparison.OrdinalIgnoreCase)) return i;
                }
                return -1;
            }

            string? GetStr(NetTopologySuite.IO.ShapefileDataReader r, int idx)
            {
                if (idx < 0) return null;
                var val = r.GetValue(idx);
                return val == null || val == DBNull.Value ? null : val.ToString();
            }

            int? GetInt(NetTopologySuite.IO.ShapefileDataReader r, int idx)
            {
                var str = GetStr(r, idx);
                if (int.TryParse(str, out var c)) return c;
                return null;
            }

            // SQL Server geography requires exterior rings to be CCW (left-hand rule).
            // Shapefiles use CW exterior rings (OGC/right-hand rule), so we must reverse.
            NetTopologySuite.Geometries.Geometry? NormalizeCCW(NetTopologySuite.Geometries.Geometry? g)
            {
                if (g == null) return null;
                if (!g.IsValid) g = g.Buffer(0);
                g.SRID = 4326;
                return (NetTopologySuite.Geometries.Geometry)g.Reverse();
            }

            // Manzanas
            var mzaPath = System.IO.Path.Combine(basePath, "Exp_MapaBase_MZA_4326.shp");
            if (System.IO.File.Exists(mzaPath) && !await context.Manzanas.AnyAsync())
            {
                using var reader = new NetTopologySuite.IO.ShapefileDataReader(mzaPath, factory);
                var idIdx = GetIdx(reader, "Id");
                var uvMzaIdx = GetIdx(reader, "UV_MZA");
                var uvIdx = GetIdx(reader, "UV");
                var mzaIdx = GetIdx(reader, "MZA");

                while (reader.Read())
                {
                    var geom = NormalizeCCW(reader.Geometry);
                    
                    context.Manzanas.Add(new Manzana
                    {
                        Geom = geom,
                        IdOrigen = GetInt(reader, idIdx),
                        UV_MZA = GetStr(reader, uvMzaIdx),
                        UV = GetStr(reader, uvIdx),
                        MZA = GetStr(reader, mzaIdx)
                    });
                }
                await context.SaveChangesAsync();
            }

            // Lotes
            var lotesPath = System.IO.Path.Combine(basePath, "Exp_MapaBase_LOTES_4326.shp");
            if (System.IO.File.Exists(lotesPath) && !await context.Lotes.AnyAsync())
            {
                using var reader = new NetTopologySuite.IO.ShapefileDataReader(lotesPath, factory);
                var idIdx = GetIdx(reader, "Id");
                var nroIdx = GetIdx(reader, "NroLote");

                while (reader.Read())
                {
                    var geom = NormalizeCCW(reader.Geometry);
                    
                    context.Lotes.Add(new Lote
                    {
                        Geom = geom,
                        IdOrigen = GetInt(reader, idIdx),
                        NroLote = GetStr(reader, nroIdx)
                    });
                }
                await context.SaveChangesAsync();
            }

            // Codigos Fijos
            var codFijosPath = System.IO.Path.Combine(basePath, "Exp_CodigoFijo_4326.shp");
            if (System.IO.File.Exists(codFijosPath) && !await context.CodigosFijos.AnyAsync())
            {
                using var reader = new NetTopologySuite.IO.ShapefileDataReader(codFijosPath, factory);
                var sqlIdx = GetIdx(reader, "CodF_SQL");
                var sigIdx = GetIdx(reader, "CodF_SIG");
                var fijoIdx = GetIdx(reader, "CodFijo");
                var nomIdx = GetIdx(reader, "Nombre");

                while (reader.Read())
                {
                    var geom = NormalizeCCW(reader.Geometry);

                    context.CodigosFijos.Add(new CodigoFijo
                    {
                        Geom = geom,
                        CodF_SQL = GetInt(reader, sqlIdx),
                        CodF_SIG = GetStr(reader, sigIdx),
                        CodFijo = GetInt(reader, fijoIdx),
                        Nombre = GetStr(reader, nomIdx),
                        Estado = 1,
                        EstadoVerificado = true,
                        FechaCambioEstado = DateTime.UtcNow
                    });
                }
                await context.SaveChangesAsync();
                
                await context.Database.ExecuteSqlRawAsync(@"
                    UPDATE c SET c.IdLote = l.IdLote
                    FROM CodigosFijos c
                    JOIN Lotes l ON c.Geom.STIntersects(l.Geom) = 1
                    WHERE c.IdLote IS NULL
                ");
            }

            // Vias
            var viasPath = System.IO.Path.Combine(basePath, "Exp_MapaBase_VIAS_4326.shp");
            if (System.IO.File.Exists(viasPath) && !await context.Vias.AnyAsync())
            {
                using var reader = new NetTopologySuite.IO.ShapefileDataReader(viasPath, factory);
                var objIdx = GetIdx(reader, "OBJECTID");
                var nomIdx = GetIdx(reader, "Nombre");
                var tipoIdx = GetIdx(reader, "type");
                var osmIdx = GetIdx(reader, "OSMID");

                while (reader.Read())
                {
                    var geom = NormalizeCCW(reader.Geometry);

                    var objStr = GetStr(reader, objIdx);
                    int? objectId = null;
                    if (int.TryParse(objStr, out var o)) objectId = o;

                    context.Vias.Add(new Via
                    {
                        Geom = geom,
                        OBJECTID = objectId,
                        Nombre = GetStr(reader, nomIdx),
                        TipoVia = GetStr(reader, tipoIdx),
                        OSMID = GetStr(reader, osmIdx)
                    });
                }
                await context.SaveChangesAsync();
            }
        }
    }
}
