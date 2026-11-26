using System.Threading;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Arquis.Backend.Services;

namespace Arquis.Backend.Controllers
{
    [ApiController]
    [Route("api/reportes")]
    public class ReportesController(
        ReportesService reportesService,
        Arquis.Backend.Services.Pdf.PdfReportGeneratorService pdfGenerator,
        Arquis.Backend.Data.ArquisDbContext context) : ControllerBase
    {
        [HttpGet("predio/{id:int}")]
        public async Task<IActionResult> GetReportePredio(int id, [FromQuery] string? usuario, CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();

            var reporte = await reportesService.GenerarReportePredioAsync(id, user, ip, ct);
            if (reporte == null)
            {
                return NotFound(new { mensaje = "No se encontró el predio para generar el informe técnico." });
            }

            return Ok(reporte);
        }

        [HttpGet("predio/{id:int}/pdf")]
        public async Task<IActionResult> GetReportePredioPdf(int id, [FromQuery] string? usuario, CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();

            var reporte = await reportesService.GenerarReportePredioAsync(id, user, ip, ct);
            if (reporte == null)
            {
                return NotFound(new { mensaje = "No se encontró el predio para generar el PDF oficial." });
            }

            // Geometría del lote para el croquis vectorial SVG
            var lote = await Microsoft.EntityFrameworkCore.EntityFrameworkQueryableExtensions.FirstOrDefaultAsync(
                context.Lotes, l => l.IdLote == id, ct);

            NetTopologySuite.Geometries.Point? waterPoint = null;
            if (reporte.Latitud.HasValue && reporte.Longitud.HasValue)
            {
                waterPoint = new NetTopologySuite.Geometries.Point(reporte.Longitud.Value, reporte.Latitud.Value) { SRID = 4326 };
            }

            var pdfBytes = pdfGenerator.GeneratePredialPdf(reporte, lote?.Geom, waterPoint);
            var filename = $"Informe_Predial_Lote_{reporte.NumeroLote}_{DateTime.UtcNow:yyyyMMdd}.pdf";
            return File(pdfBytes, "application/pdf", filename);
        }

        [HttpGet("sector")]
        public async Task<IActionResult> GetReporteSector([FromQuery] string? uv, [FromQuery] string? mza, [FromQuery] string? usuario, CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();

            var reporte = await reportesService.GenerarReporteSectorAsync(uv ?? "", mza ?? "", user, ip, ct);
            if (reporte == null)
            {
                return NotFound(new { mensaje = "No se encontraron predios para el sector o manzana especificada." });
            }

            return Ok(reporte);
        }

        [HttpGet("sector/pdf")]
        public async Task<IActionResult> GetReporteSectorPdf([FromQuery] string? uv, [FromQuery] string? mza, [FromQuery] string? usuario, CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();

            var reporte = await reportesService.GenerarReporteSectorAsync(uv ?? "", mza ?? "", user, ip, ct);
            if (reporte == null)
            {
                return NotFound(new { mensaje = "No se encontraron datos para generar el PDF del sector." });
            }

            // Geometría de la manzana para el croquis vectorial SVG
            var manzana = await Microsoft.EntityFrameworkCore.EntityFrameworkQueryableExtensions.FirstOrDefaultAsync(
                context.Manzanas, m => (string.IsNullOrWhiteSpace(uv) || m.UV == uv) && (string.IsNullOrWhiteSpace(mza) || m.MZA == mza), ct);

            var pdfBytes = pdfGenerator.GenerateSectorPdf(reporte, manzana?.Geom);
            var filename = $"Diagnostico_Sector_UV{uv}_MZA{mza}_{DateTime.UtcNow:yyyyMMdd}.pdf";
            return File(pdfBytes, "application/pdf", filename);
        }

        [HttpGet("operaciones")]
        public async Task<IActionResult> GetReporteOperaciones(
            [FromQuery] string? tipo,
            [FromQuery] string? estado,
            [FromQuery] string? operario,
            [FromQuery] DateTime? desde,
            [FromQuery] DateTime? hasta,
            [FromQuery] string? usuario,
            CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();
            var reporte = await reportesService.GenerarReporteOperacionesRutasAsync(tipo, estado, operario, desde, hasta, user, ip, ct);
            return Ok(reporte);
        }

        [HttpGet("operaciones/pdf")]
        public async Task<IActionResult> GetReporteOperacionesPdf(
            [FromQuery] string? tipo,
            [FromQuery] string? estado,
            [FromQuery] string? operario,
            [FromQuery] DateTime? desde,
            [FromQuery] DateTime? hasta,
            [FromQuery] string? usuario,
            CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "127.0.0.1";
            var reporte = await reportesService.GenerarReporteOperacionesRutasAsync(tipo, estado, operario, desde, hasta, user, ip, ct);
            var pdfBytes = pdfGenerator.GenerateOperacionesRutasPdf(reporte, ip);
            var filename = $"Informe_Operaciones_Rutas_{DateTime.UtcNow:yyyyMMdd_HHmm}.pdf";
            return File(pdfBytes, "application/pdf", filename);
        }

        [HttpGet("cuadrillas")]
        public async Task<IActionResult> GetReporteCuadrillas(
            [FromQuery] string? rol,
            [FromQuery] DateTime? desde,
            [FromQuery] DateTime? hasta,
            [FromQuery] string? usuario,
            CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();
            var reporte = await reportesService.GenerarReporteDesempenoCuadrillasAsync(rol, desde, hasta, user, ip, ct);
            return Ok(reporte);
        }

        [HttpGet("cuadrillas/pdf")]
        public async Task<IActionResult> GetReporteCuadrillasPdf(
            [FromQuery] string? rol,
            [FromQuery] DateTime? desde,
            [FromQuery] DateTime? hasta,
            [FromQuery] string? usuario,
            CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "127.0.0.1";
            var reporte = await reportesService.GenerarReporteDesempenoCuadrillasAsync(rol, desde, hasta, user, ip, ct);
            var pdfBytes = pdfGenerator.GenerateCuadrillasPdf(reporte, ip);
            var filename = $"Desempeno_Cuadrillas_{DateTime.UtcNow:yyyyMMdd_HHmm}.pdf";
            return File(pdfBytes, "application/pdf", filename);
        }

        [HttpGet("suministros")]
        public async Task<IActionResult> GetReporteSuministros(
            [FromQuery] int? estado,
            [FromQuery] string? uv,
            [FromQuery] bool? soloVerificados,
            [FromQuery] int limite = 120,
            [FromQuery] string? usuario = null,
            CancellationToken ct = default)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();
            var reporte = await reportesService.GenerarReporteEstadoSuministrosAsync(estado, uv, soloVerificados, limite, user, ip, ct);
            return Ok(reporte);
        }

        [HttpGet("suministros/pdf")]
        public async Task<IActionResult> GetReporteSuministrosPdf(
            [FromQuery] int? estado,
            [FromQuery] string? uv,
            [FromQuery] bool? soloVerificados,
            [FromQuery] int limite = 120,
            [FromQuery] string? usuario = null,
            CancellationToken ct = default)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "127.0.0.1";
            var reporte = await reportesService.GenerarReporteEstadoSuministrosAsync(estado, uv, soloVerificados, limite, user, ip, ct);
            var pdfBytes = pdfGenerator.GenerateSuministrosPdf(reporte, ip);
            var filename = $"Cartera_Suministros_{DateTime.UtcNow:yyyyMMdd_HHmm}.pdf";
            return File(pdfBytes, "application/pdf", filename);
        }

        [HttpGet("ejecutivo-global")]
        public async Task<IActionResult> GetReporteEjecutivoGlobal([FromQuery] string? usuario, CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString();
            var reporte = await reportesService.GenerarReporteEjecutivoGlobalAsync(user, ip, ct);
            return Ok(reporte);
        }

        [HttpGet("ejecutivo-global/pdf")]
        public async Task<IActionResult> GetReporteEjecutivoGlobalPdf([FromQuery] string? usuario, CancellationToken ct)
        {
            var user = !string.IsNullOrWhiteSpace(usuario) ? usuario : (User.Identity?.Name ?? "Usuario SIG");
            var ip = HttpContext.Connection.RemoteIpAddress?.ToString() ?? "127.0.0.1";
            var reporte = await reportesService.GenerarReporteEjecutivoGlobalAsync(user, ip, ct);
            var pdfBytes = pdfGenerator.GenerateEjecutivoGlobalPdf(reporte, ip);
            var filename = $"Informe_Ejecutivo_SIG_{DateTime.UtcNow:yyyyMMdd_HHmm}.pdf";
            return File(pdfBytes, "application/pdf", filename);
        }

        [HttpGet("bitacora")]
        public async Task<IActionResult> GetBitacora([FromQuery] int limite = 50, CancellationToken ct = default)
        {
            var registros = await reportesService.ObtenerBitacoraAsync(limite, ct);
            return Ok(registros);
        }
    }
}
