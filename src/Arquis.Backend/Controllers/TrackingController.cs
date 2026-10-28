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

                    if (last != null && last.EnLinea && last.Timestamp >= DateTime.UtcNow.AddMinutes(-30))
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

            string NormalizarRol(string r, string opId)
            {
                if (string.Equals(r, "Reconector", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(r, "Reconexion", StringComparison.OrdinalIgnoreCase) ||
                    opId.Contains("recon", StringComparison.OrdinalIgnoreCase) ||
                    opId.Equals("Juan", StringComparison.OrdinalIgnoreCase) ||
                    opId.Equals("Carlos", StringComparison.OrdinalIgnoreCase))
                {
                    return "Reconector";
                }
                return "Cortador";
            }

            var resultado = operariosDict.Select(kv =>
            {
                var opId = kv.Key;
                var (nombre, rolRaw) = kv.Value;
                var rol = NormalizarRol(rolRaw, opId);
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

        public class ActualizarRolDto
        {
            public string Rol { get; set; } = string.Empty; // "Cortador" o "Reconector"
        }

        [HttpPut("operarios/{operarioId}/rol")]
        public async Task<IActionResult> ActualizarRolOperario(string operarioId, [FromBody] ActualizarRolDto dto)
        {
            if (string.IsNullOrWhiteSpace(dto?.Rol))
            {
                return BadRequest(new { error = "Debe especificar el nuevo rol del trabajador ('Cortador' o 'Reconector')." });
            }

            var rolNormalizado = dto.Rol.Trim().Equals("Reconector", StringComparison.OrdinalIgnoreCase) ||
                                 dto.Rol.Trim().Equals("Reconexion", StringComparison.OrdinalIgnoreCase)
                                 ? "Reconector" : "Cortador";

            // 1. Asegurar que el rol existe en la BD
            var rolEntity = await _context.Roles.FirstOrDefaultAsync(r => r.NombreRol == rolNormalizado);
            if (rolEntity == null)
            {
                rolEntity = new Rol 
                { 
                    NombreRol = rolNormalizado, 
                    Descripcion = rolNormalizado == "Cortador" ? "Rol para corte de servicios de agua" : "Rol para reconexión de servicios de agua", 
                    Estado = true 
                };
                _context.Roles.Add(rolEntity);
                await _context.SaveChangesAsync();
            }

            // 2. Actualizar la asignación en UsuariosRoles si el usuario existe
            var usuario = await _context.Usuarios.FirstOrDefaultAsync(u => u.Login == operarioId);
            if (usuario != null)
            {
                var rolesPrevios = await _context.UsuariosRoles
                    .Include(ur => ur.Rol)
                    .Where(ur => ur.IdUsuario == usuario.IdUsuario)
                    .ToListAsync();

                // Quitar roles operacionales anteriores
                var rolesOperacionales = rolesPrevios.Where(ur => 
                    ur.Rol.NombreRol == "Cortador" || 
                    ur.Rol.NombreRol == "Reconector" || 
                    ur.Rol.NombreRol == "Reconexion" || 
                    ur.Rol.NombreRol == "Operador" || 
                    ur.Rol.NombreRol == "Lecturador").ToList();

                _context.UsuariosRoles.RemoveRange(rolesOperacionales);
                _context.UsuariosRoles.Add(new UsuarioRol { IdUsuario = usuario.IdUsuario, IdRol = rolEntity.IdRol });
                await _context.SaveChangesAsync();
            }

            // 3. Actualizar en el servicio en memoria de tracking
            _cache.ActualizarRol(operarioId, rolNormalizado);

            // 4. Actualizar las últimas posiciones en base de datos para consistencia
            var ultimasPosiciones = await _context.TrackingPosiciones
                .Where(p => p.OperarioId == operarioId)
                .OrderByDescending(p => p.Timestamp)
                .Take(20)
                .ToListAsync();

            foreach (var pos in ultimasPosiciones)
            {
                pos.Rol = rolNormalizado;
            }
            await _context.SaveChangesAsync();

            // 5. Emitir evento SignalR para sincronización reactiva en tiempo real en los clientes web
            await _hubContext.Clients.All.SendAsync("ReceiveOperarioRolActualizado", new
            {
                operarioId,
                nuevoRol = rolNormalizado
            });

            return Ok(new
            {
                success = true,
                mensaje = $"El trabajador {operarioId} ahora tiene el rol asignado de {rolNormalizado}.",
                operarioId,
                nuevoRol = rolNormalizado
            });
        }
    }
}
