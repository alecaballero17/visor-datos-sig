using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Controllers;

[ApiController]
[Route("api/codigos-fijos")]
public class CodigosFijosController(ArquisDbContext context) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetAll()
    {
        var codigos = await context.CodigosFijos
            .Select(c => new
            {
                c.IdCodigo,
                c.CodF_SQL,
                c.CodF_SIG,
                c.CodFijo,
                c.Nombre,
                c.Estado,
                c.EstadoVerificado,
                c.FechaCambioEstado,
                c.IdLote,
                c.Longitud,
                c.Latitud
                // Geom omitido por el momento para no saturar el JSON
            })
            .ToListAsync();
        
        return Ok(codigos);
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> GetById(int id)
    {
        var codigo = await context.CodigosFijos
            .Where(c => c.IdCodigo == id)
            .Select(c => new
            {
                c.IdCodigo,
                c.CodF_SQL,
                c.CodF_SIG,
                c.CodFijo,
                c.Nombre,
                c.Estado,
                c.EstadoVerificado,
                c.FechaCambioEstado,
                c.IdLote,
                c.Longitud,
                c.Latitud
            })
            .FirstOrDefaultAsync();

        if (codigo == null) return NotFound();
        return Ok(codigo);
    }
}
