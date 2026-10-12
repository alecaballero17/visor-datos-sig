using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.SignalR;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data;
using Arquis.Backend.Hubs;
using Arquis.Backend.Models.Entities;
using Arquis.Backend.Services;

namespace Arquis.Backend.Controllers
{
    [ApiController]
    [Route("api/tracking")]
    public class TrackingController : ControllerBase
    {
        private readonly ArquisDbContext _context;
        private readonly TrackingCacheService _cache;
        private readonly IHubContext<TrackingHub> _hubContext;

        public TrackingController(
            ArquisDbContext context,
            TrackingCacheService cache,
            IHubContext<TrackingHub> hubContext)
        {
            _context = context;
            _cache = cache;
            _hubContext = hubContext;
        }

        [HttpPost("posicion")]
        public async Task<IActionResult> RegistrarPosicion([FromBody] TrackingPosicion dto)
        {
            if (dto == null || string.IsNullOrWhiteSpace(dto.OperarioId))
            {
                return BadRequest(new { error = "Datos de ubicación u operario inválidos." });
            }

            dto.Timestamp = DateTime.UtcNow;
            dto.EnLinea = true;

            // Update in-memory cache for ultra-fast active lists
            _cache.ActualizarPosicion(dto);

            // Persist breadcrumb in database
            _context.TrackingPosiciones.Add(dto);
            await _context.SaveChangesAsync();

            // Broadcast via SignalR to web clients in real time
            await _hubContext.Clients.All.SendAsync("ReceivePosicion", dto);

            return Ok(new { success = true, timestamp = dto.Timestamp });
        }

        [HttpGet("activos")]
        public async Task<IActionResult> ObtenerActivos()
        {
            var activos = _cache.ObtenerActivos().ToList();

            // If in-memory is empty (e.g. freshly restarted server), load latest position per operario from DB
            if (activos.Count == 0)
            {
                var operarios = await _context.TrackingPosiciones
                    .Select(p => p.OperarioId)
                    .Distinct()
                    .ToListAsync();

                foreach (var opId in operarios)
                {
                    var last = await _context.TrackingPosiciones
                        .Where(p => p.OperarioId == opId)
                        .OrderByDescending(p => p.Timestamp)
                        .FirstOrDefaultAsync();

                    if (last != null)
                    {
                        _cache.ActualizarPosicion(last);
                        activos.Add(last);
                    }
                }
            }

            return Ok(activos);
        }

        [HttpGet("historial/{operarioId}")]
        public async Task<IActionResult> ObtenerHistorial(string operarioId, [FromQuery] DateTime? fecha)
        {
            var queryDate = fecha ?? DateTime.UtcNow.Date;
            var start = queryDate.Date;
            var end = start.AddDays(1);

            var puntos = await _context.TrackingPosiciones
                .Where(p => p.OperarioId == operarioId && p.Timestamp >= start && p.Timestamp < end)
                .OrderBy(p => p.Timestamp)
                .Select(p => new
                {
                    p.Id,
                    p.OperarioId,
                    p.NombreOperario,
                    p.Rol,
                    p.Latitud,
                    p.Longitud,
                    p.Velocidad,
                    p.Rumbo,
                    p.Bateria,
                    p.Timestamp
                })
                .ToListAsync();

            return Ok(puntos);
        }

        [HttpGet("operarios")]
        public async Task<IActionResult> ObtenerOperarios()
        {
            var operarioRoles = new[] { "Operador", "Cortador", "Lecturador", "Reconexion" };

            // 1. Usuarios con rol de operador o creados desde el móvil
            var usuarios = await _context.Usuarios
                .Where(u => u.Activo)
                .Select(u => new
                {
                    OperarioId = u.Login,
                    NombreOperario = u.Nombre,
                    Email = u.Email,
                    Rol = _context.UsuariosRoles
                        .Where(ur => ur.IdUsuario == u.IdUsuario)
                        .Select(ur => ur.Rol.NombreRol)
                        .FirstOrDefault() ?? "Operador"
                })
                .ToListAsync();

            // Filtrar usuarios operadores o que hayan reportado ubicacion
            var operariosDict = new Dictionary<string, (string Nombre, string Rol)>(StringComparer.OrdinalIgnoreCase);
            foreach (var u in usuarios)
            {
                if (operarioRoles.Contains(u.Rol, StringComparer.OrdinalIgnoreCase) || 
                    (!string.IsNullOrEmpty(u.OperarioId) && u.OperarioId.StartsWith("oper", StringComparison.OrdinalIgnoreCase)) ||
                    (!string.IsNullOrEmpty(u.Email) && u.Email.Contains("operador", StringComparison.OrdinalIgnoreCase)))
                {
                    operariosDict[u.OperarioId] = (u.NombreOperario, u.Rol);
                }
            }

            // 2. Estadísticas y últimas posiciones desde la base de datos
            var trackingStats = await _context.TrackingPosiciones
                .GroupBy(p => p.OperarioId)
                .Select(g => new
                {
                    OperarioId = g.Key,
                    Nombre = g.OrderByDescending(x => x.Timestamp).Select(x => x.NombreOperario).FirstOrDefault() ?? g.Key,
                    Rol = g.OrderByDescending(x => x.Timestamp).Select(x => x.Rol).FirstOrDefault() ?? "Operador",
                    TotalPuntos = g.Count(),
                    UltimaActividad = g.Max(x => x.Timestamp),
                    UltimaPosicion = g.OrderByDescending(x => x.Timestamp).FirstOrDefault()
                })
                .ToListAsync();

            // Asegurar que cualquier operario que haya emitido GPS aparezca
            foreach (var t in trackingStats)
            {
                if (!operariosDict.ContainsKey(t.OperarioId))
                {
                    var nombreUsuario = usuarios.FirstOrDefault(u => string.Equals(u.OperarioId, t.OperarioId, StringComparison.OrdinalIgnoreCase))?.NombreOperario;
                    operariosDict[t.OperarioId] = (nombreUsuario ?? t.Nombre, t.Rol);
                }
            }

            var activosMemoria = _cache.ObtenerActivos().ToDictionary(a => a.OperarioId, StringComparer.OrdinalIgnoreCase);
            var statsDict = trackingStats.ToDictionary(x => x.OperarioId, StringComparer.OrdinalIgnoreCase);

            var resultado = operariosDict.Select(kv =>
            {
                var opId = kv.Key;
                var (nombre, rol) = kv.Value;
                var hasStats = statsDict.TryGetValue(opId, out var stats);
                var isLive = activosMemoria.TryGetValue(opId, out var live);

                var ultimaPos = live ?? stats?.UltimaPosicion;

                return new
                {
                    OperarioId = opId,
                    NombreOperario = string.IsNullOrWhiteSpace(nombre) ? opId : nombre,
                    Rol = rol,
                    TotalPuntos = stats?.TotalPuntos ?? (live != null ? 1 : 0),
                    UltimaActividad = live?.Timestamp ?? stats?.UltimaActividad,
                    EnLinea = isLive || (stats != null && stats.UltimaActividad > DateTime.UtcNow.AddMinutes(-10)),
                    Latitud = ultimaPos?.Latitud,
                    Longitud = ultimaPos?.Longitud,
                    Velocidad = ultimaPos?.Velocidad ?? 0.0,
                    Rumbo = ultimaPos?.Rumbo ?? 0.0,
                    Bateria = ultimaPos?.Bateria ?? 100
                };
            })
            .OrderByDescending(x => x.EnLinea)
            .ThenByDescending(x => x.UltimaActividad.HasValue)
            .ThenByDescending(x => x.UltimaActividad)
            .ThenBy(x => x.NombreOperario)
            .ToList();

            return Ok(resultado);
        }
    }
}
