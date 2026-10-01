using Arquis.Backend.Services;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Arquis.Backend.Controllers;

[ApiController]
//[Authorize]
[Route("api/busqueda")]
public sealed class SearchController(GeoDataService geo) : ControllerBase
{
    [HttpGet]
    public async Task<IActionResult> Search([FromQuery] string texto, [FromQuery] string? capa, [FromQuery] int pagina=1, [FromQuery] int tamano=25, CancellationToken ct=default)
    {
        if (string.IsNullOrWhiteSpace(texto)) return Ok(Array.Empty<object>());
        try { return Ok(await geo.SearchAsync(texto,capa,pagina,tamano,ct)); }
        catch (KeyNotFoundException) { return BadRequest(new { mensaje="Capa no válida." }); }
    }
}
