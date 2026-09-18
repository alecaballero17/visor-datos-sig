using Arquis.Backend.Data;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.Data.SqlClient;

namespace Arquis.Backend.Controllers;

[ApiController]
[Authorize(Roles="Administrador")]
[Route("api/migraciones")]
public sealed class MigrationsController(SqlConnectionFactory factory) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> Get(CancellationToken ct)
    {
        const string sql="""
        IF OBJECT_ID('dbo.BitacoraMigracion','U') IS NULL
            SELECT CAST(NULL AS INT) IdMigracion WHERE 1=0;
        ELSE
            SELECT TOP(100) IdMigracion, FechaInicio, FechaFin, Usuario, Capa, Archivo, TablaDestino, Modalidad,
                   Procesados, Exitosos, Omitidos, Fallidos, Estado, Detalle
            FROM dbo.BitacoraMigracion ORDER BY IdMigracion DESC;
        """;
        await using var cn=factory.Create(); await cn.OpenAsync(ct);
        await using var cmd=new SqlCommand(sql,cn); await using var rd=await cmd.ExecuteReaderAsync(ct);
        var rows=new List<Dictionary<string,object?>>();
        while(await rd.ReadAsync(ct))
        {
            var row=new Dictionary<string,object?>(); for(var i=0;i<rd.FieldCount;i++) row[rd.GetName(i)]=rd.IsDBNull(i)?null:rd.GetValue(i); rows.Add(row);
        }
        return Ok(rows);
    }
}
