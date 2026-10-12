using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data;
using Arquis.Backend.Hubs;
using Arquis.Backend.Models.Entities;

namespace Arquis.Backend.Controllers
{
    [ApiController]
    [Route("api/rutas-trabajo")]
    public class RutasTrabajoController : ControllerBase
    {
        private readonly ArquisDbContext _context;
        private readonly IHubContext<TrackingHub> _hubContext;

        public RutasTrabajoController(ArquisDbContext context, IHubContext<TrackingHub> hubContext)
        {
            _context = context;
            _hubContext = hubContext;
        }

        [HttpGet]
        public async Task<IActionResult> Listar([FromQuery] string? estado, [FromQuery] string? operario)
        {
            var query = _context.RutasTrabajo.Include(r => r.Puntos).AsQueryable();

            if (!string.IsNullOrWhiteSpace(estado))
                query = query.Where(r => r.Estado == estado);

            if (!string.IsNullOrWhiteSpace(operario))
                query = query.Where(r => r.OperarioAsignado == operario || r.OperarioId == operario);

            var rutas = await query
                .OrderByDescending(r => r.FechaCreacion)
                .Select(r => new
                {
                    r.Id,
                    r.Codigo,
                    r.Titulo,
                    r.Tipo,
                    r.Estado,
                    r.Prioridad,
                    r.OperarioAsignado,
                    r.OperarioId,
                    r.CreadoPor,
                    r.FechaCreacion,
                    r.FechaAsignacion,
                    r.FechaCompletado,
                    r.Observaciones,
                    TotalPuntos = r.Puntos.Count,
                    PuntosCompletados = r.Puntos.Count(p => p.Estado == "Completado" || p.Estado == "Ejecutado"),
                    Puntos = r.Puntos.OrderBy(p => p.Orden).ToList()
                })
                .ToListAsync();

            return Ok(rutas);
        }

        [HttpGet("{id:int}")]
        public async Task<IActionResult> ObtenerPorId(int id)
        {
            var ruta = await _context.RutasTrabajo
                .Include(r => r.Puntos.OrderBy(p => p.Orden))
                .FirstOrDefaultAsync(r => r.Id == id);

            if (ruta == null) return NotFound(new { error = "Ruta de trabajo no encontrada." });

            return Ok(ruta);
        }

        [HttpGet("asignadas")]
        public async Task<IActionResult> ObtenerAsignadas([FromQuery] string? operario)
        {
            var op = !string.IsNullOrWhiteSpace(operario)
                ? operario
                : (User.Identity?.IsAuthenticated == true ? User.Identity.Name : "Pedro");

            var rutas = await _context.RutasTrabajo
                .Include(r => r.Puntos)
                .Where(r => (r.OperarioAsignado == op || r.OperarioId == op) && r.Estado != "Cancelada")
                .OrderByDescending(r => r.FechaCreacion)
                .ToListAsync();

            return Ok(rutas);
        }

        public class AsignacionMasivaDto
        {
            public string TituloGeneral { get; set; } = string.Empty;
            public string Tipo { get; set; } = "Corte"; // "Corte" o "Reconexion"
            public string Prioridad { get; set; } = "Alta";
            public List<string> OperariosAsignados { get; set; } = new();
            public string? Observaciones { get; set; }
            public int? CantidadCuentas { get; set; } // Por ejemplo 100 cortes o 200 reconexiones
            public List<CrearPuntoDto> Puntos { get; set; } = new();
        }

        [HttpPost("asignacion-masiva")]
        public async Task<IActionResult> AsignacionMasiva([FromBody] AsignacionMasivaDto dto)
        {
            if (dto.OperariosAsignados == null || dto.OperariosAsignados.Count == 0)
                return BadRequest(new { error = "Debe seleccionar al menos un operario para la asignación masiva." });

            var puntosAIntervenir = new List<CrearPuntoDto>();
            if (dto.Puntos != null && dto.Puntos.Count > 0)
            {
                puntosAIntervenir.AddRange(dto.Puntos);
            }
            else if (dto.CantidadCuentas.HasValue && dto.CantidadCuentas.Value > 0)
            {
                int cant = Math.Min(dto.CantidadCuentas.Value, 1000);
                // Obtener códigos fijos reales de la base de datos
                var codigosDb = await _context.CodigosFijos
                    .Where(c => c.Latitud != null && c.Longitud != null)
                    .Take(cant)
                    .Select(c => new CrearPuntoDto
                    {
                        IdCodigoFijo = c.IdCodigo,
                        IdLote = c.IdLote,
                        CodigoSuministro = c.CodF_SIG ?? $"CF-{c.CodFijo}",
                        Titular = c.Nombre ?? "Usuario Registrado",
                        Lote = $"Lote {c.IdLote ?? c.IdCodigo}",
                        Direccion = $"Av. Principal / Manzana {c.IdLote ?? 1}",
                        Latitud = c.Latitud!.Value,
                        Longitud = c.Longitud!.Value,
                        MontoDeuda = dto.Tipo == "Corte" ? 350.00m : 0.00m,
                        Observaciones = dto.Tipo == "Corte" ? "Mora mayor a 90 días" : "Pago verificado en caja"
                    })
                    .ToListAsync();

                puntosAIntervenir.AddRange(codigosDb);

                // Si faltan puntos para llegar a la cantidad solicitada (ej. 100 o 200 solicitados),
                // generar puntos distribuidos en la zona urbana de operaciones
                var rnd = new Random();
                int restante = cant - puntosAIntervenir.Count;
                int baseIndice = puntosAIntervenir.Count + 1;
                for (int k = 0; k < restante; k++)
                {
                    var lat = -17.78000 + (rnd.NextDouble() - 0.5) * 0.02;
                    var lng = -63.18000 + (rnd.NextDouble() - 0.5) * 0.02;
                    puntosAIntervenir.Add(new CrearPuntoDto
                    {
                        CodigoSuministro = $"CF-{90000 + baseIndice + k}",
                        Titular = $"Titular Suministro #{baseIndice + k}",
                        Lote = $"Lote {10 + (k % 50)}",
                        Direccion = $"Sector UV {1 + (k % 8)} - MZA {1 + (k % 25)}",
                        Latitud = lat,
                        Longitud = lng,
                        MontoDeuda = dto.Tipo == "Corte" ? (decimal)rnd.Next(180, 890) : 0.00m,
                        Observaciones = dto.Tipo == "Corte" ? "Corte programado por mora" : "Habilitación inmediata solicitada"
                    });
                }
            }

            if (puntosAIntervenir.Count == 0)
                return BadRequest(new { error = "Debe proporcionar los puntos de servicio o una cantidad de cuentas a intervenir." });

            var totalOperarios = dto.OperariosAsignados.Count;
            var rutasCreadas = new List<RutaTrabajo>();
            var baseCount = await _context.RutasTrabajo.CountAsync();
            var prefijo = dto.Tipo.Equals("Reconexion", StringComparison.OrdinalIgnoreCase) ? "RR" : "RC";

            for (int i = 0; i < totalOperarios; i++)
            {
                var operario = dto.OperariosAsignados[i];
                var puntosParaEsteOperario = puntosAIntervenir
                    .Where((p, idx) => idx % totalOperarios == i)
                    .ToList();

                if (puntosParaEsteOperario.Count == 0) continue;

                var codigo = $"{prefijo}-{DateTime.UtcNow.Year}-{(baseCount + i + 1):D3}";
                var nuevaRuta = new RutaTrabajo
                {
                    Codigo = codigo,
                    Titulo = $"{dto.TituloGeneral} ({operario})",
                    Tipo = dto.Tipo,
                    Estado = "Pendiente",
                    Prioridad = dto.Prioridad,
                    OperarioAsignado = operario,
                    OperarioId = operario,
                    CreadoPor = User.Identity?.Name ?? "Gerente de Operaciones",
                    FechaCreacion = DateTime.UtcNow,
                    FechaAsignacion = DateTime.UtcNow,
                    Observaciones = dto.Observaciones
                };

                int orden = 1;
                foreach (var p in puntosParaEsteOperario)
                {
                    nuevaRuta.Puntos.Add(new PuntoRutaTrabajo
                    {
                        Orden = orden++,
                        IdCodigoFijo = p.IdCodigoFijo,
                        IdLote = p.IdLote,
                        CodigoSuministro = p.CodigoSuministro,
                        Lote = p.Lote,
                        Titular = p.Titular,
                        Direccion = p.Direccion,
                        Latitud = p.Latitud,
                        Longitud = p.Longitud,
                        MontoDeuda = p.MontoDeuda,
                        Estado = "Pendiente",
                        Observaciones = p.Observaciones
                    });
                }

                _context.RutasTrabajo.Add(nuevaRuta);
                rutasCreadas.Add(nuevaRuta);
            }

            await _context.SaveChangesAsync();

            foreach (var r in rutasCreadas)
            {
                await _hubContext.Clients.All.SendAsync("ReceiveRutaAsignada", r);
            }

            return Ok(new
            {
                mensaje = $"Se crearon {rutasCreadas.Count} hojas de ruta distribuidas entre {totalOperarios} operarios.",
                totalRutas = rutasCreadas.Count
            });
        }

        public class CrearRutaDto
        {
            public string Titulo { get; set; } = string.Empty;
            public string Tipo { get; set; } = "Corte"; // "Corte" o "Reconexion"
            public string Prioridad { get; set; } = "Normal";
            public string OperarioAsignado { get; set; } = "Pedro";
            public string? Observaciones { get; set; }
            public List<CrearPuntoDto> Puntos { get; set; } = new();
        }

        public class CrearPuntoDto
        {
            public int? IdCodigoFijo { get; set; }
            public int? IdLote { get; set; }
            public string? CodigoSuministro { get; set; }
            public string? Lote { get; set; }
            public string? Titular { get; set; }
            public string? Direccion { get; set; }
            public double Latitud { get; set; }
            public double Longitud { get; set; }
            public decimal? MontoDeuda { get; set; }
            public string? Observaciones { get; set; }
        }

        [HttpPost]
        public async Task<IActionResult> Crear([FromBody] CrearRutaDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto.Titulo) || dto.Puntos.Count == 0)
            {
                return BadRequest(new { error = "La ruta debe tener un título y al menos un punto asignado." });
            }

            var count = await _context.RutasTrabajo.CountAsync() + 1;
            var prefijo = dto.Tipo.Equals("Reconexion", StringComparison.OrdinalIgnoreCase) ? "RR" : "RC";
            var codigo = $"{prefijo}-{DateTime.UtcNow.Year}-{count:D3}";

            var nuevaRuta = new RutaTrabajo
            {
                Codigo = codigo,
                Titulo = dto.Titulo,
                Tipo = dto.Tipo,
                Estado = "Pendiente",
                Prioridad = dto.Prioridad,
                OperarioAsignado = dto.OperarioAsignado,
                OperarioId = dto.OperarioAsignado,
                CreadoPor = "Gerente de Operaciones",
                FechaCreacion = DateTime.UtcNow,
                FechaAsignacion = DateTime.UtcNow,
                Observaciones = dto.Observaciones
            };

            int orden = 1;
            foreach (var p in dto.Puntos)
            {
                nuevaRuta.Puntos.Add(new PuntoRutaTrabajo
                {
                    Orden = orden++,
                    IdCodigoFijo = p.IdCodigoFijo,
                    IdLote = p.IdLote,
                    CodigoSuministro = p.CodigoSuministro,
                    Lote = p.Lote,
                    Titular = p.Titular,
                    Direccion = p.Direccion,
                    Latitud = p.Latitud,
                    Longitud = p.Longitud,
                    MontoDeuda = p.MontoDeuda,
                    Estado = "Pendiente",
                    Observaciones = p.Observaciones
                });
            }

            _context.RutasTrabajo.Add(nuevaRuta);
            await _context.SaveChangesAsync();

            // Notify connected clients (including mobile devices) via SignalR
            await _hubContext.Clients.All.SendAsync("ReceiveRutaAsignada", nuevaRuta);

            return CreatedAtAction(nameof(ObtenerPorId), new { id = nuevaRuta.Id }, nuevaRuta);
        }

        [HttpPut("{id:int}/iniciar")]
        public async Task<IActionResult> IniciarRuta(int id)
        {
            var ruta = await _context.RutasTrabajo.FindAsync(id);
            if (ruta == null) return NotFound(new { error = "Ruta no encontrada." });

            ruta.Estado = "EnProgreso";
            await _context.SaveChangesAsync();

            await _hubContext.Clients.All.SendAsync("ReceiveRutaActualizada", ruta);
            return Ok(new { success = true, estado = ruta.Estado });
        }

        public class EjecutarPuntoDto
        {
            public string? Observaciones { get; set; }
            public string? EvidenciaFotoUrl { get; set; }
        }

        [HttpPut("{rutaId:int}/puntos/{puntoId:int}/ejecutar")]
        public async Task<IActionResult> EjecutarPunto(int rutaId, int puntoId, [FromBody] EjecutarPuntoDto? body)
        {
            var ruta = await _context.RutasTrabajo
                .Include(r => r.Puntos)
                .FirstOrDefaultAsync(r => r.Id == rutaId);

            if (ruta == null) return NotFound(new { error = "Ruta no encontrada." });

            var punto = ruta.Puntos.FirstOrDefault(p => p.Id == puntoId);
            if (punto == null) return NotFound(new { error = "Punto de ruta no encontrado." });

            punto.Estado = "Completado";
            punto.FechaEjecucion = DateTime.UtcNow;
            if (!string.IsNullOrWhiteSpace(body?.Observaciones))
                punto.Observaciones = body.Observaciones;

            // If the route was still "Pendiente", change to "EnProgreso"
            if (ruta.Estado == "Pendiente")
                ruta.Estado = "EnProgreso";

            // If linked to a CodigoFijo, update its Estado in DB
            if (punto.IdCodigoFijo.HasValue)
            {
                var codigoFijo = await _context.CodigosFijos.FindAsync(punto.IdCodigoFijo.Value);
                if (codigoFijo != null)
                {
                    // If route is Corte -> state 0 (cortado). If Reconexion -> state 1 (activo)
                    codigoFijo.Estado = (byte)(ruta.Tipo.Equals("Corte", StringComparison.OrdinalIgnoreCase) ? 0 : 1);
                    codigoFijo.FechaCambioEstado = DateTime.UtcNow;
                }
            }

            // Check if all points are now done
            bool todosCompletados = ruta.Puntos.All(p => p.Estado == "Completado" || p.Estado == "Omitido");
            if (todosCompletados)
            {
                ruta.Estado = "Completada";
                ruta.FechaCompletado = DateTime.UtcNow;
            }

            await _context.SaveChangesAsync();

            // Real-time broadcast
            await _hubContext.Clients.All.SendAsync("ReceivePuntoActualizado", new
            {
                rutaId,
                puntoId,
                estado = punto.Estado,
                rutaEstado = ruta.Estado,
                todosCompletados
            });

            return Ok(new
            {
                success = true,
                puntoEstado = punto.Estado,
                rutaEstado = ruta.Estado,
                todosCompletados
            });
        }

        [HttpGet("zonas")]
        public async Task<IActionResult> ObtenerZonas()
        {
            var manzanas = await _context.Manzanas
                .Where(m => !string.IsNullOrEmpty(m.UV))
                .Select(m => new { m.IdManzana, m.UV, m.MZA, m.UV_MZA })
                .Distinct()
                .OrderBy(m => m.UV)
                .ThenBy(m => m.MZA)
                .Take(200)
                .ToListAsync();

            var uvs = manzanas
                .Where(m => !string.IsNullOrWhiteSpace(m.UV))
                .Select(m => m.UV!)
                .Distinct()
                .OrderBy(x => x)
                .ToList();

            return Ok(new
            {
                uvs,
                manzanas
            });
        }

        [HttpGet("entidades-disponibles")]
        public async Task<IActionResult> ObtenerEntidadesDisponibles(
            [FromQuery] string? tipo,
            [FromQuery] string? uv,
            [FromQuery] string? mza,
            [FromQuery] string? busqueda,
            [FromQuery] int limite = 100)
        {
            var query = _context.CodigosFijos
                .Include(c => c.Lote)
                    .ThenInclude(l => l!.Manzana)
                .Where(c => c.Latitud != null && c.Longitud != null)
                .AsQueryable();

            if (!string.IsNullOrWhiteSpace(uv))
            {
                query = query.Where(c => c.Lote != null && c.Lote.Manzana != null && c.Lote.Manzana.UV == uv);
            }

            if (!string.IsNullOrWhiteSpace(mza))
            {
                query = query.Where(c => c.Lote != null && c.Lote.Manzana != null && c.Lote.Manzana.MZA == mza);
            }

            if (!string.IsNullOrWhiteSpace(busqueda))
            {
                query = query.Where(c =>
                    (c.Nombre != null && c.Nombre.Contains(busqueda)) ||
                    (c.CodF_SIG != null && c.CodF_SIG.Contains(busqueda)) ||
                    (c.CodFijo != null && c.CodFijo.ToString()!.Contains(busqueda)) ||
                    (c.Lote != null && c.Lote.NroLote != null && c.Lote.NroLote.Contains(busqueda)));
            }

            if (string.Equals(tipo, "Reconexion", StringComparison.OrdinalIgnoreCase))
            {
                query = query.Where(c => c.Estado == 0 || !c.EstadoVerificado);
            }

            var items = await query
                .OrderBy(c => c.Lote != null && c.Lote.Manzana != null ? c.Lote.Manzana.UV : "")
                .ThenBy(c => c.Lote != null && c.Lote.Manzana != null ? c.Lote.Manzana.MZA : "")
                .ThenBy(c => c.Lote != null ? c.Lote.NroLote : "")
                .Take(Math.Min(limite, 500))
                .Select(c => new
                {
                    c.IdCodigo,
                    CodigoSuministro = c.CodF_SIG ?? $"CF-{c.CodFijo}",
                    CodFijo = c.CodFijo,
                    Titular = c.Nombre ?? "Usuario Suministro",
                    Estado = (int)c.Estado,
                    IdLote = c.IdLote,
                    NroLote = c.Lote != null ? c.Lote.NroLote : null,
                    UV = c.Lote != null && c.Lote.Manzana != null ? c.Lote.Manzana.UV : null,
                    MZA = c.Lote != null && c.Lote.Manzana != null ? c.Lote.Manzana.MZA : null,
                    Latitud = c.Latitud!.Value,
                    Longitud = c.Longitud!.Value,
                    Direccion = $"UV {c.Lote!.Manzana!.UV ?? "S/N"} - MZA {c.Lote!.Manzana!.MZA ?? "S/N"} - Lote {c.Lote!.NroLote ?? "S/N"}",
                    MontoDeuda = string.Equals(tipo, "Corte", StringComparison.OrdinalIgnoreCase) ? 385.50m : 0.00m
                })
                .ToListAsync();

            return Ok(items);
        }

        public class CrearTicketDto
        {
            public string Titulo { get; set; } = string.Empty;
            public string Tipo { get; set; } = "Corte";
            public string Prioridad { get; set; } = "Normal";
            public string OperarioAsignado { get; set; } = string.Empty;
            public string? Observaciones { get; set; }
            public List<int> IdsCodigosFijos { get; set; } = new();
            public List<CrearPuntoDto> PuntosPersonalizados { get; set; } = new();
        }

        [HttpPost("crear-ticket")]
        public async Task<IActionResult> CrearTicket([FromBody] CrearTicketDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto.OperarioAsignado))
                return BadRequest(new { error = "Debe seleccionar un operario técnico responsable." });

            if (dto.IdsCodigosFijos.Count == 0 && dto.PuntosPersonalizados.Count == 0)
                return BadRequest(new { error = "Debe seleccionar al menos una casa, lote o zona para crear la orden." });

            var puntos = new List<CrearPuntoDto>();

            if (dto.IdsCodigosFijos.Count > 0)
            {
                var codigos = await _context.CodigosFijos
                    .Include(c => c.Lote)
                        .ThenInclude(l => l!.Manzana)
                    .Where(c => dto.IdsCodigosFijos.Contains(c.IdCodigo) && c.Latitud != null && c.Longitud != null)
                    .ToListAsync();

                foreach (var c in codigos)
                {
                    puntos.Add(new CrearPuntoDto
                    {
                        IdCodigoFijo = c.IdCodigo,
                        IdLote = c.IdLote,
                        CodigoSuministro = c.CodF_SIG ?? $"CF-{c.CodFijo}",
                        Titular = c.Nombre ?? "Usuario Suministro",
                        Lote = c.Lote != null ? $"Lote {c.Lote.NroLote}" : "Lote S/N",
                        Direccion = $"UV {c.Lote?.Manzana?.UV ?? "S/N"} - MZA {c.Lote?.Manzana?.MZA ?? "S/N"}",
                        Latitud = c.Latitud!.Value,
                        Longitud = c.Longitud!.Value,
                        MontoDeuda = string.Equals(dto.Tipo, "Corte", StringComparison.OrdinalIgnoreCase) ? 385.50m : 0.00m,
                        Observaciones = dto.Observaciones
                    });
                }
            }

            if (dto.PuntosPersonalizados.Count > 0)
            {
                puntos.AddRange(dto.PuntosPersonalizados);
            }

            var baseCount = await _context.RutasTrabajo.CountAsync() + 1;
            var prefijo = string.Equals(dto.Tipo, "Reconexion", StringComparison.OrdinalIgnoreCase) ? "TK-REC" : "TK-COR";
            var codigo = $"{prefijo}-{DateTime.UtcNow.Year}-{baseCount:D4}";

            var nuevaRuta = new RutaTrabajo
            {
                Codigo = codigo,
                Titulo = string.IsNullOrWhiteSpace(dto.Titulo) ? $"Orden #{codigo} ({dto.Tipo})" : dto.Titulo,
                Tipo = dto.Tipo,
                Estado = "Pendiente",
                Prioridad = dto.Prioridad,
                OperarioAsignado = dto.OperarioAsignado,
                OperarioId = dto.OperarioAsignado,
                CreadoPor = User.Identity?.Name ?? "Administrador SIG",
                FechaCreacion = DateTime.UtcNow,
                FechaAsignacion = DateTime.UtcNow,
                Observaciones = dto.Observaciones
            };

            int orden = 1;
            foreach (var p in puntos)
            {
                nuevaRuta.Puntos.Add(new PuntoRutaTrabajo
                {
                    Orden = orden++,
                    IdCodigoFijo = p.IdCodigoFijo,
                    IdLote = p.IdLote,
                    CodigoSuministro = p.CodigoSuministro,
                    Lote = p.Lote,
                    Titular = p.Titular,
                    Direccion = p.Direccion,
                    Latitud = p.Latitud,
                    Longitud = p.Longitud,
                    MontoDeuda = p.MontoDeuda,
                    Estado = "Pendiente",
                    Observaciones = p.Observaciones
                });
            }

            _context.RutasTrabajo.Add(nuevaRuta);
            await _context.SaveChangesAsync();

            await _hubContext.Clients.All.SendAsync("ReceiveRutaAsignada", nuevaRuta);

            return Ok(new
            {
                mensaje = $"Ticket {nuevaRuta.Codigo} creado exitosamente con {nuevaRuta.Puntos.Count} puntos asignados a {nuevaRuta.OperarioAsignado}.",
                ruta = nuevaRuta
            });
        }
    }
}
