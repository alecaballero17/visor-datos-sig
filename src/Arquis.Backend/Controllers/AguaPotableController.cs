using Arquis.Backend.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;

namespace Arquis.Backend.Controllers;

[ApiController]
[Authorize]
[Route("api/agua-potable")]
public sealed class AguaPotableController(SqlConnectionFactory connections) : ControllerBase
{
    [HttpGet("codigos/{id:int:min(1)}")]
    public Task<IActionResult> Codigo(int id, CancellationToken ct) => Ficha(id, false, ct);

    [HttpGet("lotes/{id:int:min(1)}")]
    public Task<IActionResult> Lote(int id, CancellationToken ct) => Ficha(id, true, ct);

    private async Task<IActionResult> Ficha(int id, bool porLote, CancellationToken ct)
    {
        await using var cn = connections.Create();
        await cn.OpenAsync(ct);
        if (porLote)
        {
            await using var exists = new SqlCommand("SELECT COUNT(*) FROM dbo.Lotes WHERE IdLote=@Id", cn);
            exists.Parameters.AddWithValue("@Id", id);
            if (Convert.ToInt32(await exists.ExecuteScalarAsync(ct)) == 0) return NotFound();
        }
        var sql = """
            SELECT c.IdCodigo,c.CodFijo,c.CodF_SIG,c.Nombre,c.Estado,c.EstadoVerificado,
                   CASE WHEN @PorLote=1 THEN @Id ELSE c.IdLote END AS IdLote,l.NroLote,m.UV,m.MZA,
                   CASE WHEN c.Geom.STGeometryType()='Point' THEN c.Geom.STX END AS Longitud,
                   CASE WHEN c.Geom.STGeometryType()='Point' THEN c.Geom.STY END AS Latitud
            FROM dbo.CodigosFijos c
            LEFT JOIN dbo.Lotes l ON l.IdLote=CASE WHEN @PorLote=1 THEN @Id ELSE c.IdLote END
            LEFT JOIN dbo.Manzanas m ON m.IdManzana=l.IdManzana
            WHERE
            """ + (porLote ? " (c.IdLote=@Id OR c.Geom.STIntersects(@LoteGeom)=1)" : " c.IdCodigo=@Id") + " ORDER BY c.IdCodigo";
        if (porLote) sql = "DECLARE @LoteGeom geometry; SELECT @LoteGeom=Geom FROM dbo.Lotes WHERE IdLote=@Id; " + sql;
        await using var cmd = new SqlCommand(sql, cn);
        cmd.Parameters.AddWithValue("@Id", id);
        cmd.Parameters.AddWithValue("@PorLote", porLote);
        await using var rd = await cmd.ExecuteReaderAsync(ct);
        var registros = new List<object>();
        while (await rd.ReadAsync(ct))
        {
            object? Value(string column) => rd[column] is DBNull ? null : rd[column];
            var verificado = (bool)rd["EstadoVerificado"];
            registros.Add(new {
                idCodigo = (int)rd["IdCodigo"], codigoFijo = Value("CodFijo"), codigoSig = Value("CodF_SIG"),
                nombreRegistrado = Value("Nombre"), idLote = Value("IdLote"), numeroLote = Value("NroLote"),
                uv = Value("UV"), manzana = Value("MZA"), longitud = Value("Longitud"), latitud = Value("Latitud"),
                estadoVerificado = verificado,
                estadoServicio = verificado ? (int?)Convert.ToInt32(rd["Estado"]) : null
            });
        }
        if (!porLote && registros.Count == 0) return NotFound();
        return Ok(new {
            tieneAgua = !porLote || registros.Count > 0,
            criterioDisponibilidad = "Con código fijo: agua potable. Lote sin código fijo asociado: sin agua.",
            fuente = "Exp_CodigoFijo_4326.shp", registros,
            datosNoDisponibles = new[] { "Número de medidor", "Detalles de la conexión", "Lecturas", "Consumo", "Historial del servicio" }
        });
    }
}
