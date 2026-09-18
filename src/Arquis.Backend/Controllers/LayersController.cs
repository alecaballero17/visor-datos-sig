using Arquis.Backend.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Arquis.Backend.Controllers;

[ApiController]
[Authorize]
[Route("api/capas")]
public sealed class LayersController(GeoDataService geo) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> GetLayers(CancellationToken ct) => Ok(await geo.GetLayersAsync(ct));

    [HttpGet("{capa}/geojson")]
    public async Task<IActionResult> GetGeoJson(string capa, [FromQuery] string? bbox, [FromQuery] string? q, [FromQuery] int? limit, CancellationToken ct)
    {
        try { return Ok(await geo.GetGeoJsonAsync(capa, bbox, q, limit, ct)); }
        catch (KeyNotFoundException) { return NotFound(new { mensaje="Capa no válida." }); }
    }

    [HttpGet("{capa}/{id:int}")]
    public async Task<IActionResult> GetById(string capa, int id, CancellationToken ct)
    {
        try
        {
            var feature=await geo.GetByIdAsync(capa,id,ct);
            return feature is null ? NotFound() : Ok(feature);
        }
        catch (KeyNotFoundException) { return NotFound(new { mensaje="Capa no válida." }); }
    }
}
