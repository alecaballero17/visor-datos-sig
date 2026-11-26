using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data;
using Arquis.Backend.Models.Entities;
using Arquis.Backend.Models.Reports;

namespace Arquis.Backend.Services
{
    public class ReportesService(ArquisDbContext context)
    {
        private static readonly Dictionary<int, string> EstadosServicio = new()
        {
            [0] = "Para Reconexión (Candidato)",
            [1] = "Normal / Suministro Activo",
            [2] = "Notificado para Corte",
            [3] = "Servicio Cortado / Suspendido",
            [4] = "Baja Parcial de Conexión",
            [5] = "Baja Total"
        };

        public async Task<ReportePredialDto?> GenerarReportePredioAsync(int idLote, string usuario, string? ip, CancellationToken ct = default)
        {
            var lote = await context.Lotes.FirstOrDefaultAsync(l => l.IdLote == idLote, ct);
            if (lote == null) return null;

            var manzana = await context.Manzanas.FirstOrDefaultAsync(m => m.IdManzana == lote.IdManzana, ct);
            var uv = manzana?.UV ?? "-";
            var mza = manzana?.MZA ?? "-";
            var sector = manzana?.UV_MZA ?? $"UV {uv} · MZA {mza}";

            // Conexión asociada de agua potable
            var codigos = await context.CodigosFijos
                .Where(c => c.IdLote == idLote)
                .ToListAsync(ct);

            if (codigos.Count == 0 && lote.Geom != null)
            {
                try
                {
                    codigos = await context.CodigosFijos
                        .FromSqlRaw(@"
                            SELECT TOP 3 c.*
                            FROM dbo.CodigosFijos c
                            WHERE c.Geom IS NOT NULL AND (
                                c.Geom.STIntersects((SELECT Geom FROM dbo.Lotes WHERE IdLote = {0})) = 1 OR
                                c.Geom.STDistance((SELECT Geom FROM dbo.Lotes WHERE IdLote = {0})) <= 25
                            )
                            ORDER BY c.Geom.STDistance((SELECT Geom FROM dbo.Lotes WHERE IdLote = {0})) ASC", idLote)
                        .ToListAsync(ct);
                }
                catch { }
            }

            var codigoPrincipal = codigos.FirstOrDefault();
            var tieneAgua = codigos.Count > 0;

            // Contexto de la manzana
            var lotesManzana = await context.Lotes
                .Where(l => l.IdManzana == lote.IdManzana)
                .Select(l => new { l.IdLote, l.Geom })
                .ToListAsync(ct);

            int totalManzana = lotesManzana.Count;
            int conAguaManzana = 0;

            if (totalManzana > 0)
            {
                var idsManzana = lotesManzana.Select(x => x.IdLote).ToList();
                conAguaManzana = await context.CodigosFijos
                    .Where(c => c.IdLote.HasValue && idsManzana.Contains(c.IdLote.Value))
                    .Select(c => c.IdLote!.Value)
                    .Distinct()
                    .CountAsync(ct);

                if (tieneAgua && conAguaManzana == 0) conAguaManzana = 1;
            }

            double tasaManzana = totalManzana > 0 ? Math.Round((double)conAguaManzana / totalManzana * 100, 1) : 0;

            var condOperativa = "Sin conexión asignada";
            if (tieneAgua && codigoPrincipal != null)
            {
                condOperativa = EstadosServicio.TryGetValue(codigoPrincipal.Estado, out var desc)
                    ? desc
                    : (codigoPrincipal.EstadoVerificado ? "Verificado en Campo" : "Activo Regular");
            }

            var lat = codigoPrincipal?.Latitud ?? lote.Geom?.InteriorPoint.Y;
            var lon = codigoPrincipal?.Longitud ?? lote.Geom?.InteriorPoint.X;

            var dto = new ReportePredialDto
            {
                CodigoReporte = $"RPT-PRED-{lote.IdLote:D5}-{DateTime.UtcNow:yyyyMM}",
                FechaEmision = DateTime.UtcNow,
                UsuarioEmisor = string.IsNullOrWhiteSpace(usuario) ? "Usuario SIG" : usuario,
                IdLote = lote.IdLote,
                NumeroLote = lote.NroLote ?? lote.IdLote.ToString(),
                UnidadVecinal = uv,
                Manzana = mza,
                Sector = sector,
                ClaveOrigen = lote.IdOrigen?.ToString() ?? "Catastro Municipal",
                Latitud = lat,
                Longitud = lon,
                TieneAgua = tieneAgua,
                Titular = !string.IsNullOrWhiteSpace(codigoPrincipal?.Nombre) 
                    ? codigoPrincipal.Nombre 
                    : (codigoPrincipal != null ? $"Titular Cód. #{codigoPrincipal.CodFijo}" : "Sin titular vinculado"),
                CodigoSuministro = codigoPrincipal?.CodFijo.ToString() ?? (tieneAgua ? "Asignado" : "Pendiente"),
                CodigoSig = codigoPrincipal?.CodF_SIG ?? "—",
                CondicionOperativa = condOperativa,
                TotalLotesManzana = totalManzana,
                LotesConAguaManzana = conAguaManzana,
                PorcentajeCoberturaManzana = tasaManzana,
                ClasificacionUrbana = "Lote Residencial Consolidado",
                FactibilidadHidraulica = tieneAgua
                    ? "Conexión activa a la red matriz pública."
                    : "Factible de incorporación a la red secundaria (manzana con cobertura)."
            };

            // Redacción ejecutiva comprensible
            if (tieneAgua)
            {
                dto.ResumenEjecutivo = $"El predio Lote N° {dto.NumeroLote} ubicado en Manzana {mza} (UV {uv}) cuenta con conexión formalizada de agua potable bajo el código #{dto.CodigoSuministro}, a nombre de {dto.Titular}. El entorno inmediato presenta un {tasaManzana}% de cobertura en la manzana. Su condición operativa se encuentra clasificada como '{condOperativa}'.";
                dto.Recomendaciones.Add("Verificar periódicamente el estado físico de la acometida y la válvula de paso.");
                dto.Recomendaciones.Add("Mantener actualizada la titularidad del contrato en caso de transferencia del predio.");
            }
            else
            {
                dto.ResumenEjecutivo = $"El predio Lote N° {dto.NumeroLote} ubicado en Manzana {mza} (UV {uv}) actualmente NO cuenta con conexión de agua potable registrada en la base catastral. Dado que la manzana circundante presenta un índice de cobertura del {tasaManzana}%, existe factibilidad técnica para solicitar la instalación de una acometida domiciliaria conectada a la red matriz.";
                dto.Recomendaciones.Add("Iniciar trámite de solicitud de nueva acometida con la documentación de propiedad del lote.");
                dto.Recomendaciones.Add("Inspeccionar la proximidad de la red matriz sobre la calzada para determinar la distancia de empalme.");
            }

            // Registrar en la Bitácora
            await RegistrarEnBitacoraAsync(
                usuario: dto.UsuarioEmisor,
                tipo: "Predial",
                referencia: $"Lote {dto.NumeroLote} · MZA {mza} · UV {uv}",
                accion: "Generación de Informe Técnico Predial",
                detalle: $"Estado de agua: {(tieneAgua ? "Activo" : "Sin conexión")}, Titular: {dto.Titular}",
                ip: ip,
                ct: ct
            );

            return dto;
        }

        public async Task<ReporteSectorDto?> GenerarReporteSectorAsync(string uv, string mza, string usuario, string? ip, CancellationToken ct = default)
        {
            var manzanas = await context.Manzanas
                .Where(m => (string.IsNullOrWhiteSpace(uv) || m.UV == uv) &&
                            (string.IsNullOrWhiteSpace(mza) || m.MZA == mza))
                .ToListAsync(ct);

            if (manzanas.Count == 0) return null;

            var idManzanas = manzanas.Select(m => m.IdManzana).ToList();
            var lotes = await context.Lotes
                .Where(l => l.IdManzana.HasValue && idManzanas.Contains(l.IdManzana.Value))
                .OrderBy(l => l.NroLote)
                .ToListAsync(ct);

            var idLotes = lotes.Select(l => l.IdLote).ToList();
            var codigos = await context.CodigosFijos
                .Where(c => c.IdLote.HasValue && idLotes.Contains(c.IdLote.Value))
                .ToListAsync(ct);

            var codigosDict = codigos.GroupBy(c => c.IdLote!.Value)
                                     .ToDictionary(g => g.Key, g => g.First());

            int total = lotes.Count;
            int conAgua = 0;
            int enMora = 0;
            var prediosList = new List<PredioItemDto>();

            foreach (var lote in lotes)
            {
                bool tiene = codigosDict.TryGetValue(lote.IdLote, out var cod);
                if (tiene) conAgua++;
                if (cod != null && cod.Estado == 2) enMora++;

                prediosList.Add(new PredioItemDto
                {
                    IdLote = lote.IdLote,
                    NumeroLote = lote.NroLote ?? lote.IdLote.ToString(),
                    TieneAgua = tiene,
                    Titular = cod?.Nombre,
                    CodigoSuministro = cod?.CodFijo.ToString(),
                    Condicion = cod != null && EstadosServicio.TryGetValue(cod.Estado, out var cond) ? cond : (tiene ? "Normal" : "Sin Servicio")
                });
            }

            int sinAgua = total - conAgua;
            double tasa = total > 0 ? Math.Round((double)conAgua / total * 100, 1) : 0;

            var dto = new ReporteSectorDto
            {
                CodigoReporte = $"RPT-SEC-{uv}-{mza}-{DateTime.UtcNow:yyyyMMdd}",
                FechaEmision = DateTime.UtcNow,
                UsuarioEmisor = string.IsNullOrWhiteSpace(usuario) ? "Usuario SIG" : usuario,
                Titulo = $"DIAGNÓSTICO TERRITORIAL Y COBERTURA DEL SECTOR (UV {uv} / MZA {mza})",
                UnidadVecinal = uv,
                Manzana = mza,
                TotalPredios = total,
                PrediosConServicio = conAgua,
                PrediosSinServicio = sinAgua,
                PorcentajeCobertura = tasa,
                PrediosEnMoraOCorte = enMora,
                IndiceConsolidacion = tasa >= 70 ? "Alta Consolidación" : (tasa >= 40 ? "Consolidación Media" : "Sector en Crecimiento"),
                Predios = prediosList,
                DiagnosticoSituacional = $"La Manzana {mza} de la Unidad Vecinal {uv} integra un universo de {total} predios catastrados. El servicio de agua potable alcanza un nivel de cobertura del {tasa}%, con {conAgua} conexiones regulares activas y {sinAgua} lotes pendientes de empalme a la red. El sector presenta condiciones aptas para proyectos de extensión y regularización.",
                RecomendacionesTecnicas = new List<string>
                {
                    $"Priorizar campañas de información y regularización para los {sinAgua} predios sin acometida registrada.",
                    "Monitorear la capacidad hidráulica de la red de distribución ante nuevas incorporaciones.",
                    "Verificar el estado técnico de los medidores en campo."
                }
            };

            await RegistrarEnBitacoraAsync(
                usuario: dto.UsuarioEmisor,
                tipo: "Sector/Barrio",
                referencia: $"UV {uv} · Manzana {mza}",
                accion: "Diagnóstico de Cobertura Territorial",
                detalle: $"Total predios: {total}, Cobertura: {tasa}%, Sin agua: {sinAgua}",
                ip: ip,
                ct: ct
            );

            return dto;
        }

        public async Task<ReporteOperacionesRutasDto> GenerarReporteOperacionesRutasAsync(
            string? tipo,
            string? estado,
            string? operario,
            DateTime? desde,
            DateTime? hasta,
            string usuario,
            string? ip,
            CancellationToken ct = default)
        {
            var query = context.RutasTrabajo
                .Include(r => r.Puntos.OrderBy(p => p.Orden))
                .AsQueryable();

            var partesFiltro = new List<string>();

            if (!string.IsNullOrWhiteSpace(tipo) && !tipo.Equals("Todos", StringComparison.OrdinalIgnoreCase))
            {
                if (EsTipoReconexion(tipo))
                {
                    query = query.Where(r => r.Tipo == "Reconexion" || r.Tipo == "Reconector" || r.Tipo == "Reponedor" || r.Tipo == "Reposicion");
                    partesFiltro.Add("Tipo: Reconexión / Reposición");
                }
                else
                {
                    query = query.Where(r => r.Tipo == "Corte" || r.Tipo == "Cortador");
                    partesFiltro.Add("Tipo: Corte");
                }
            }

            if (!string.IsNullOrWhiteSpace(estado) && !estado.Equals("Todos", StringComparison.OrdinalIgnoreCase))
            {
                var est = estado.Trim();
                query = query.Where(r => r.Estado == est);
                partesFiltro.Add($"Estado: {est}");
            }
            else
            {
                query = query.Where(r => r.Estado != "Cancelada");
            }

            if (!string.IsNullOrWhiteSpace(operario) && !operario.Equals("Todos", StringComparison.OrdinalIgnoreCase))
            {
                var op = operario.Trim();
                query = query.Where(r => r.OperarioAsignado == op || r.OperarioId == op);
                partesFiltro.Add($"Operario: {op}");
            }

            if (desde.HasValue)
            {
                var d = desde.Value.Date;
                query = query.Where(r => r.FechaCreacion >= d);
                partesFiltro.Add($"Desde: {d:dd/MM/yyyy}");
            }

            if (hasta.HasValue)
            {
                var h = hasta.Value.Date.AddDays(1);
                query = query.Where(r => r.FechaCreacion < h);
                partesFiltro.Add($"Hasta: {hasta.Value:dd/MM/yyyy}");
            }

            var rutasDb = await query
                .OrderByDescending(r => r.FechaCreacion)
                .ToListAsync(ct);

            var todasParadas = rutasDb.SelectMany(r => r.Puntos).ToList();
            int completadas = todasParadas.Count(p => p.Estado == "Completado" || p.Estado == "Ejecutado");
            int observadas = todasParadas.Count(p => p.Estado == "Observado");
            int pendientes = todasParadas.Count(p => p.Estado == "Pendiente");
            double avance = todasParadas.Count > 0 ? Math.Round(completadas * 100.0 / todasParadas.Count, 1) : 0;
            double distKm = Math.Round(rutasDb.Sum(r => r.DistanciaTotalMetros ?? 0) / 1000.0, 2);
            decimal deudaTotal = todasParadas.Sum(p => p.MontoDeuda ?? 0m);
            var gpsValidaciones = todasParadas.Where(p => p.DistanciaAntifraudeMetros.HasValue).ToList();
            int antifraudeOk = gpsValidaciones.Count(p => p.DistanciaAntifraudeMetros!.Value <= 30.0);

            var filtroTexto = partesFiltro.Count > 0 ? string.Join(" · ", partesFiltro) : "Todas las órdenes activas";
            var emisor = string.IsNullOrWhiteSpace(usuario) ? "Usuario SIG" : usuario;

            var dto = new ReporteOperacionesRutasDto
            {
                CodigoReporte = $"RPT-OPE-{DateTime.UtcNow:yyyyMMdd-HHmm}",
                FechaEmision = DateTime.UtcNow,
                UsuarioEmisor = emisor,
                FiltroAplicado = filtroTexto,
                TotalRutas = rutasDb.Count,
                RutasCompletadas = rutasDb.Count(r => r.Estado == "Completada"),
                RutasEnProgreso = rutasDb.Count(r => r.Estado == "EnProgreso"),
                RutasPendientes = rutasDb.Count(r => r.Estado == "Pendiente"),
                TotalParadas = todasParadas.Count,
                ParadasCompletadas = completadas,
                ParadasObservadas = observadas,
                ParadasPendientes = pendientes,
                PorcentajeAvance = avance,
                DistanciaTotalKm = distKm,
                MontoTotalDeudaBs = deudaTotal,
                ValidacionesGpsTotales = gpsValidaciones.Count,
                ValidacionesAntifraudeOk = antifraudeOk,
                ResumenEjecutivo = $"Se consolidaron {rutasDb.Count} hojas de ruta optimizadas con Dijkstra que abarcan {todasParadas.Count} predios ({distKm:F2} km planificados). Se registra un avance efectivo del {avance}% ({completadas} ejecutadas, {observadas} observadas y {pendientes} pendientes), con {antifraudeOk}/{gpsValidaciones.Count} cierres validados dentro de los 30 m antifraude.",
                Recomendaciones = new List<string>
                {
                    pendientes > 0 ? $"Dar seguimiento en campo a las {pendientes} paradas pendientes de ejecución." : "Todas las paradas filtradas fueron atendidas en campo.",
                    observadas > 0 ? $"Revisar los {observadas} predios observados para reprogramación o verificación administrativa." : "Sin novedades de predios observados en el periodo.",
                    "Validar el cumplimiento secuencial de rutas asignadas mediante monitoreo GPS en tiempo real."
                },
                Rutas = rutasDb.Select(r => new RutaReporteItemDto
                {
                    Id = r.Id,
                    Codigo = r.Codigo,
                    Titulo = r.Titulo,
                    Tipo = EsTipoReconexion(r.Tipo) ? "Reconexión" : "Corte",
                    Estado = r.Estado,
                    Prioridad = r.Prioridad,
                    OperarioAsignado = r.OperarioAsignado,
                    FechaCreacion = r.FechaCreacion,
                    DistanciaKm = Math.Round((r.DistanciaTotalMetros ?? 0) / 1000.0, 2),
                    TiempoEstimadoMinutos = r.TiempoEstimadoMinutos ?? 0,
                    TotalPuntos = r.Puntos.Count,
                    PuntosCompletados = r.Puntos.Count(p => p.Estado == "Completado" || p.Estado == "Ejecutado"),
                    PuntosObservados = r.Puntos.Count(p => p.Estado == "Observado"),
                    MontoDeudaTotalBs = r.Puntos.Sum(p => p.MontoDeuda ?? 0m)
                }).ToList(),
                DetalleParadas = rutasDb.SelectMany(r => r.Puntos.Select(p => new ParadaAuditoriaItemDto
                {
                    CodigoRuta = r.Codigo,
                    Operario = r.OperarioAsignado,
                    TipoRuta = EsTipoReconexion(r.Tipo) ? "Reconexión" : "Corte",
                    Orden = p.Orden,
                    CodigoSuministro = p.CodigoSuministro ?? "—",
                    Titular = p.Titular ?? "Sin titular",
                    Direccion = p.Direccion ?? "—",
                    Estado = p.Estado,
                    EstadoFinal = p.EstadoFinal,
                    DistanciaAntifraudeMetros = p.DistanciaAntifraudeMetros,
                    MontoDeuda = p.MontoDeuda,
                    FechaEjecucion = p.FechaEjecucion
                })).Take(120).ToList()
            };

            await RegistrarEnBitacoraAsync(
                usuario: emisor,
                tipo: "Operaciones/Rutas",
                referencia: filtroTexto,
                accion: "Generación de Informe Operativo de Rutas",
                detalle: $"Rutas: {dto.TotalRutas}, Paradas: {dto.TotalParadas}, Avance: {dto.PorcentajeAvance}%",
                ip: ip,
                ct: ct);

            return dto;
        }

        public async Task<ReporteDesempenoCuadrillasDto> GenerarReporteDesempenoCuadrillasAsync(
            string? rol,
            DateTime? desde,
            DateTime? hasta,
            string usuario,
            string? ip,
            CancellationToken ct = default)
        {
            var rutasQuery = context.RutasTrabajo
                .Include(r => r.Puntos)
                .Where(r => r.Estado != "Cancelada")
                .AsQueryable();

            var partes = new List<string>();
            if (!string.IsNullOrWhiteSpace(rol) && !rol.Equals("Todos", StringComparison.OrdinalIgnoreCase))
            {
                partes.Add($"Rol: {rol}");
            }
            if (desde.HasValue)
            {
                var d = desde.Value.Date;
                rutasQuery = rutasQuery.Where(r => r.FechaCreacion >= d);
                partes.Add($"Desde: {d:dd/MM/yyyy}");
            }
            if (hasta.HasValue)
            {
                var h = hasta.Value.Date.AddDays(1);
                rutasQuery = rutasQuery.Where(r => r.FechaCreacion < h);
                partes.Add($"Hasta: {hasta.Value:dd/MM/yyyy}");
            }

            var rutas = await rutasQuery.ToListAsync(ct);

            var usuariosDb = await context.Usuarios
                .Include(u => u.UsuariosRoles)
                    .ThenInclude(ur => ur.Rol)
                .ToListAsync(ct);

            var ultimasPosiciones = await context.TrackingPosiciones
                .GroupBy(t => t.OperarioId)
                .Select(g => new { OperarioId = g.Key, Ultima = g.Max(x => x.Timestamp) })
                .ToListAsync(ct);

            var ultPosDict = ultimasPosiciones.ToDictionary(x => x.OperarioId, x => (DateTime?)x.Ultima, StringComparer.OrdinalIgnoreCase);

            var rolesPermitidos = new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "Cortador", "Reconector", "Reponedor", "Reconexion", "Reposicion", "Operador", "Lecturador"
            };

            var operariosMap = new Dictionary<string, (string Nombre, string Rol)>(StringComparer.OrdinalIgnoreCase);

            foreach (var u in usuariosDb)
            {
                var rolesUsuario = u.UsuariosRoles.Select(ur => ur.Rol.NombreRol).ToList();
                if (!rolesUsuario.Any(r => rolesPermitidos.Contains(r)) &&
                    !u.Login.StartsWith("oper", StringComparison.OrdinalIgnoreCase))
                {
                    continue;
                }

                string rolNorm = rolesUsuario.Any(EsTipoReconexion) ? "Reconector" : "Cortador";
                operariosMap[u.Login] = (u.Nombre, rolNorm);
            }

            foreach (var r in rutas)
            {
                var key = string.IsNullOrWhiteSpace(r.OperarioAsignado) ? (r.OperarioId ?? "Sin asignar") : r.OperarioAsignado;
                if (!operariosMap.ContainsKey(key))
                {
                    operariosMap[key] = (key, EsTipoReconexion(r.Tipo) ? "Reconector" : "Cortador");
                }
            }

            var rutasPorOperario = rutas
                .GroupBy(r => string.IsNullOrWhiteSpace(r.OperarioAsignado) ? (r.OperarioId ?? "Sin asignar") : r.OperarioAsignado, StringComparer.OrdinalIgnoreCase)
                .ToDictionary(g => g.Key, g => g.ToList(), StringComparer.OrdinalIgnoreCase);

            var items = new List<CuadrillaDesempenoItemDto>();
            foreach (var (opId, info) in operariosMap)
            {
                if (!string.IsNullOrWhiteSpace(rol) && !rol.Equals("Todos", StringComparison.OrdinalIgnoreCase))
                {
                    var filtroEsReconexion = EsTipoReconexion(rol);
                    var opEsReconexion = EsTipoReconexion(info.Rol);
                    if (filtroEsReconexion != opEsReconexion) continue;
                }

                rutasPorOperario.TryGetValue(opId, out var opRutas);
                opRutas ??= new List<RutaTrabajo>();
                var puntos = opRutas.SelectMany(r => r.Puntos).ToList();
                int ejecutadas = puntos.Count(p => p.Estado == "Completado" || p.Estado == "Ejecutado");
                int observadas = puntos.Count(p => p.Estado == "Observado");
                int pendientes = puntos.Count(p => p.Estado == "Pendiente");
                double cumpl = puntos.Count > 0 ? Math.Round(ejecutadas * 100.0 / puntos.Count, 1) : 0;
                var distGps = puntos.Where(p => p.DistanciaAntifraudeMetros.HasValue).Select(p => p.DistanciaAntifraudeMetros!.Value).ToList();
                double? avgGps = distGps.Count > 0 ? Math.Round(distGps.Average(), 1) : null;
                ultPosDict.TryGetValue(opId, out var ultAct);

                items.Add(new CuadrillaDesempenoItemDto
                {
                    OperarioId = opId,
                    NombreOperario = info.Nombre,
                    Rol = info.Rol == "Reconector" ? "Reponedor / Reconector" : "Cortador",
                    RutasAsignadas = opRutas.Count,
                    RutasCompletadas = opRutas.Count(r => r.Estado == "Completada"),
                    ParadasTotales = puntos.Count,
                    Ejecutadas = ejecutadas,
                    Observadas = observadas,
                    Pendientes = pendientes,
                    PorcentajeCumplimiento = cumpl,
                    DistanciaTotalKm = Math.Round(opRutas.Sum(r => r.DistanciaTotalMetros ?? 0) / 1000.0, 2),
                    PrecisionGpsPromedioMetros = avgGps,
                    MontoGestionadoBs = puntos.Sum(p => p.MontoDeuda ?? 0m),
                    UltimaActividad = ultAct
                });
            }

            items = items
                .OrderByDescending(i => i.Ejecutadas)
                .ThenByDescending(i => i.ParadasTotales)
                .ThenBy(i => i.NombreOperario)
                .ToList();

            int sumParadas = items.Sum(i => i.ParadasTotales);
            int sumEjec = items.Sum(i => i.Ejecutadas);
            double promCumpl = sumParadas > 0 ? Math.Round(sumEjec * 100.0 / sumParadas, 1) : 0;
            var emisor = string.IsNullOrWhiteSpace(usuario) ? "Usuario SIG" : usuario;
            var filtroTexto = partes.Count > 0 ? string.Join(" · ", partes) : "Todas las cuadrillas";

            var dto = new ReporteDesempenoCuadrillasDto
            {
                CodigoReporte = $"RPT-CUA-{DateTime.UtcNow:yyyyMMdd-HHmm}",
                FechaEmision = DateTime.UtcNow,
                UsuarioEmisor = emisor,
                FiltroAplicado = filtroTexto,
                TotalOperarios = items.Count,
                TotalCortadores = items.Count(i => i.Rol.Contains("Cortador")),
                TotalReconectores = items.Count(i => i.Rol.Contains("Reponedor")),
                TotalRutasAsignadas = items.Sum(i => i.RutasAsignadas),
                TotalParadasAsignadas = sumParadas,
                TotalEjecutadas = sumEjec,
                TotalObservadas = items.Sum(i => i.Observadas),
                TotalPendientes = items.Sum(i => i.Pendientes),
                CumplimientoPromedioPct = promCumpl,
                DistanciaTotalKm = Math.Round(items.Sum(i => i.DistanciaTotalKm), 2),
                Cuadrillas = items,
                ResumenEjecutivo = $"La fuerza operativa evaluada comprende {items.Count} técnicos ({items.Count(i => i.Rol.Contains("Cortador"))} cortadores y {items.Count(i => i.Rol.Contains("Reponedor"))} reponedores/reconectores) con {items.Sum(i => i.RutasAsignadas)} hojas de ruta y {sumParadas} intervenciones programadas. El cumplimiento global alcanza el {promCumpl}%.",
                Recomendaciones = new List<string>
                {
                    "Equilibrar la carga de asignaciones masivas considerando el porcentaje de cumplimiento y zona de trabajo.",
                    "Auditar operarios con alta tasa de observaciones para validar causales en campo.",
                    "Verificar la calibración GPS de dispositivos cuya distancia promedio antifraude se acerque al límite de 30 m."
                }
            };

            await RegistrarEnBitacoraAsync(
                usuario: emisor,
                tipo: "Cuadrillas",
                referencia: filtroTexto,
                accion: "Generación de Informe de Desempeño de Cuadrillas",
                detalle: $"Operarios: {dto.TotalOperarios}, Ejecutadas: {dto.TotalEjecutadas}/{dto.TotalParadasAsignadas} ({dto.CumplimientoPromedioPct}%)",
                ip: ip,
                ct: ct);

            return dto;
        }

        public async Task<ReporteEstadoSuministrosDto> GenerarReporteEstadoSuministrosAsync(
            int? estado,
            string? uv,
            bool? soloVerificados,
            int limite,
            string usuario,
            string? ip,
            CancellationToken ct = default)
        {
            var baseQuery = context.CodigosFijos
                .Include(c => c.Lote)
                    .ThenInclude(l => l!.Manzana)
                .AsQueryable();

            var partes = new List<string>();
            if (!string.IsNullOrWhiteSpace(uv))
            {
                var uvTrim = uv.Trim();
                baseQuery = baseQuery.Where(c => c.Lote != null && c.Lote.Manzana != null && c.Lote.Manzana.UV == uvTrim);
                partes.Add($"UV: {uvTrim}");
            }

            var resumenCounts = await baseQuery
                .GroupBy(c => new { c.Estado, c.EstadoVerificado })
                .Select(g => new { g.Key.Estado, g.Key.EstadoVerificado, Count = g.Count() })
                .ToListAsync(ct);

            int total = resumenCounts.Sum(x => x.Count);
            int cParaRec = resumenCounts.Where(x => x.Estado == 0).Sum(x => x.Count);
            int cNormal = resumenCounts.Where(x => x.Estado == 1).Sum(x => x.Count);
            int cParaCorte = resumenCounts.Where(x => x.Estado == 2).Sum(x => x.Count);
            int cCortado = resumenCounts.Where(x => x.Estado == 3).Sum(x => x.Count);
            int cBajaP = resumenCounts.Where(x => x.Estado == 4).Sum(x => x.Count);
            int cBajaT = resumenCounts.Where(x => x.Estado == 5).Sum(x => x.Count);
            int verif = resumenCounts.Where(x => x.EstadoVerificado).Sum(x => x.Count);

            var filteredQuery = baseQuery;
            if (estado.HasValue)
            {
                filteredQuery = filteredQuery.Where(c => c.Estado == (byte)estado.Value);
                var labelEst = EstadosServicio.TryGetValue(estado.Value, out var desc) ? desc : $"Estado {estado.Value}";
                partes.Add($"Estado: {labelEst}");
            }
            if (soloVerificados == true)
            {
                filteredQuery = filteredQuery.Where(c => c.EstadoVerificado);
                partes.Add("Solo verificados en campo");
            }

            int maxRows = Math.Clamp(limite <= 0 ? 120 : limite, 10, 500);
            var rawRows = await filteredQuery
                .OrderByDescending(c => c.FechaCambioEstado)
                .ThenBy(c => c.IdCodigo)
                .Take(maxRows)
                .Select(c => new
                {
                    c.IdCodigo,
                    CodFijo = c.CodFijo,
                    CodFSig = c.CodF_SIG,
                    Nombre = c.Nombre,
                    Estado = (int)c.Estado,
                    c.EstadoVerificado,
                    UV = c.Lote != null && c.Lote.Manzana != null ? c.Lote.Manzana.UV : null,
                    MZA = c.Lote != null && c.Lote.Manzana != null ? c.Lote.Manzana.MZA : null,
                    NroLote = c.Lote != null ? c.Lote.NroLote : null,
                    IdLote = c.IdLote,
                    c.FechaCambioEstado
                })
                .ToListAsync(ct);

            var rows = rawRows.Select(c => new SuministroEstadoItemDto
            {
                IdCodigo = c.IdCodigo,
                CodigoFijo = c.CodFijo.HasValue ? c.CodFijo.Value.ToString() : c.IdCodigo.ToString(),
                CodigoSig = c.CodFSig ?? "—",
                Titular = !string.IsNullOrWhiteSpace(c.Nombre) ? c.Nombre : $"Titular #{c.CodFijo ?? c.IdCodigo}",
                EstadoCodigo = c.Estado,
                EstadoTexto = EstadosServicio.TryGetValue(c.Estado, out var txt) ? txt : $"Estado {c.Estado}",
                EstadoVerificado = c.EstadoVerificado,
                UnidadVecinal = c.UV ?? "—",
                Manzana = c.MZA ?? "—",
                NumeroLote = c.NroLote ?? c.IdLote?.ToString() ?? "—",
                FechaCambioEstado = c.FechaCambioEstado
            }).ToList();

            var emisor = string.IsNullOrWhiteSpace(usuario) ? "Usuario SIG" : usuario;
            var filtroTexto = partes.Count > 0 ? string.Join(" · ", partes) : "Todo el municipio";

            var dto = new ReporteEstadoSuministrosDto
            {
                CodigoReporte = $"RPT-SUM-{DateTime.UtcNow:yyyyMMdd-HHmm}",
                FechaEmision = DateTime.UtcNow,
                UsuarioEmisor = emisor,
                FiltroAplicado = filtroTexto,
                TotalSuministros = total,
                Normal = cNormal,
                ParaCorte = cParaCorte,
                ParaReconexion = cParaRec,
                Cortado = cCortado,
                BajaParcial = cBajaP,
                BajaTotal = cBajaT,
                Verificados = verif,
                SinVerificar = total - verif,
                Suministros = rows,
                ResumenEjecutivo = $"La cartera auditada ({filtroTexto}) registra {total} conexiones fijas: {cNormal} en estado Normal, {cParaCorte} notificadas para Corte por mora, {cCortado} Cortadas, {cParaRec} habilitadas para Reconexión y {cBajaP + cBajaT} en baja. Un total de {verif} registros cuentan con verificación operativa en campo.",
                Recomendaciones = new List<string>
                {
                    cParaCorte > 0 ? $"Despachar cuadrillas de cortadores hacia las {cParaCorte} cuentas en mora." : "No existen cuentas pendientes en mora para corte.",
                    cParaRec > 0 ? $"Priorizar las {cParaRec} órdenes pendientes para cuadrillas de reponedores/reconectores." : "Sin cuentas pendientes de reconexión inmediata.",
                    "Mantener la actualización de verificación física conforme las cuadrillas cierran tickets en campo."
                }
            };

            await RegistrarEnBitacoraAsync(
                usuario: emisor,
                tipo: "Suministros",
                referencia: filtroTexto,
                accion: "Auditoría de Cartera de Suministros",
                detalle: $"Total: {total}, ParaCorte: {cParaCorte}, Cortados: {cCortado}, ParaRec: {cParaRec}",
                ip: ip,
                ct: ct);

            return dto;
        }

        public async Task<ReporteEjecutivoGlobalDto> GenerarReporteEjecutivoGlobalAsync(
            string usuario,
            string? ip,
            CancellationToken ct = default)
        {
            var totalManzanas = await context.Manzanas.CountAsync(ct);
            var totalLotes = await context.Lotes.CountAsync(ct);
            var totalVias = await context.Vias.CountAsync(ct);
            var totalCodigos = await context.CodigosFijos.CountAsync(ct);

            double longitudKm = 0;
            try
            {
                var lengthDeg = await context.Vias
                    .Where(v => v.Geom != null)
                    .SumAsync(v => v.Geom!.Length, ct);
                longitudKm = Math.Round(lengthDeg * 109.06, 2);
            }
            catch { }

            var estados = await context.CodigosFijos
                .GroupBy(c => c.Estado)
                .Select(g => new { Estado = g.Key, Count = g.Count() })
                .ToListAsync(ct);

            int cRec = estados.Where(x => x.Estado == 0).Sum(x => x.Count);
            int cNorm = estados.Where(x => x.Estado == 1).Sum(x => x.Count);
            int cCorte = estados.Where(x => x.Estado == 2).Sum(x => x.Count);
            int cCortado = estados.Where(x => x.Estado == 3).Sum(x => x.Count);
            int cBajaP = estados.Where(x => x.Estado == 4).Sum(x => x.Count);
            int cBajaT = estados.Where(x => x.Estado == 5).Sum(x => x.Count);

            var lotesConAguaCount = await context.CodigosFijos
                .Where(c => c.IdLote.HasValue)
                .Select(c => c.IdLote!.Value)
                .Distinct()
                .CountAsync(ct);

            int lotesSinAgua = Math.Max(0, totalLotes - lotesConAguaCount);
            double cobPct = totalLotes > 0 ? Math.Round(lotesConAguaCount * 100.0 / totalLotes, 1) : 0;

            var totalRutas = await context.RutasTrabajo.CountAsync(r => r.Estado != "Cancelada", ct);
            var totalParadas = await context.PuntosRutaTrabajo.CountAsync(ct);
            var paradasComp = await context.PuntosRutaTrabajo.CountAsync(p => p.Estado == "Completado" || p.Estado == "Ejecutado", ct);
            double efPct = totalParadas > 0 ? Math.Round(paradasComp * 100.0 / totalParadas, 1) : 0;

            var uvsData = await context.Manzanas
                .Where(m => m.UV != null && m.UV != "")
                .Select(m => new
                {
                    UV = m.UV!,
                    TotalLotes = m.Lotes.Count,
                    LotesConAgua = m.Lotes.Count(l => l.CodigosFijos.Any()),
                    ParaCorte = m.Lotes.SelectMany(l => l.CodigosFijos).Count(c => c.Estado == 2),
                    Cortados = m.Lotes.SelectMany(l => l.CodigosFijos).Count(c => c.Estado == 3),
                    ParaRec = m.Lotes.SelectMany(l => l.CodigosFijos).Count(c => c.Estado == 0)
                })
                .ToListAsync(ct);

            var resumenPorUv = uvsData
                .GroupBy(x => x.UV)
                .Select(g =>
                {
                    int tLotes = g.Sum(x => x.TotalLotes);
                    int cAgua = g.Sum(x => x.LotesConAgua);
                    return new ResumenUvItemDto
                    {
                        UnidadVecinal = g.Key,
                        TotalManzanas = g.Count(),
                        TotalLotes = tLotes,
                        LotesConAgua = cAgua,
                        CoberturaPct = tLotes > 0 ? Math.Round(cAgua * 100.0 / tLotes, 1) : 0,
                        CuentasParaCorte = g.Sum(x => x.ParaCorte),
                        CuentasCortadas = g.Sum(x => x.Cortados),
                        CuentasParaReconexion = g.Sum(x => x.ParaRec)
                    };
                })
                .OrderByDescending(u => u.TotalLotes)
                .Take(25)
                .ToList();

            var emisor = string.IsNullOrWhiteSpace(usuario) ? "Usuario SIG" : usuario;

            var dto = new ReporteEjecutivoGlobalDto
            {
                CodigoReporte = $"RPT-GSL-{DateTime.UtcNow:yyyyMMdd-HHmm}",
                FechaEmision = DateTime.UtcNow,
                UsuarioEmisor = emisor,
                TotalManzanas = totalManzanas,
                TotalLotes = totalLotes,
                TotalVias = totalVias,
                LongitudRedVialKm = longitudKm,
                TotalCodigosFijos = totalCodigos,
                LotesConServicio = lotesConAguaCount,
                LotesSinServicio = lotesSinAgua,
                CoberturaGlobalPct = cobPct,
                Normal = cNorm,
                ParaCorte = cCorte,
                ParaReconexion = cRec,
                Cortado = cCortado,
                BajaParcial = cBajaP,
                BajaTotal = cBajaT,
                TotalRutasHistoricas = totalRutas,
                TotalIntervencionesCampo = totalParadas,
                IntervencionesCompletadas = paradasComp,
                TasaEfectividadCampoPct = efPct,
                ResumenPorUv = resumenPorUv,
                ResumenEjecutivo = $"El catastro municipal SIG administra {totalLotes:N0} predios distribuidos en {totalManzanas:N0} manzanas y {longitudKm:N1} km de ejes viales ({totalVias:N0} tramos). Se registran {totalCodigos:N0} acometidas de agua potable con una cobertura predial del {cobPct}% y una efectividad operativa de cuadrillas del {efPct}%.",
                Recomendaciones = new List<string>
                {
                    $"Focalizar la expansión de acometidas en las Unidades Vecinales con menor porcentaje de cobertura ({lotesSinAgua:N0} lotes sin servicio).",
                    $"Gestionar la cartera crítica de {cCorte:N0} cuentas para corte y {cRec:N0} listas para reconexión mediante rutas óptimas Dijkstra.",
                    "Ejecutar auditorías periódicas en la Bitácora SIG para asegurar la integridad catastral y trazabilidad operativa."
                }
            };

            await RegistrarEnBitacoraAsync(
                usuario: emisor,
                tipo: "Ejecutivo Global",
                referencia: "Consolidado Municipal SIG",
                accion: "Generación de Informe Ejecutivo Consolidado",
                detalle: $"Lotes: {totalLotes}, Cobertura: {cobPct}%, Suministros: {totalCodigos}, Efectividad campo: {efPct}%",
                ip: ip,
                ct: ct);

            return dto;
        }

        private static bool EsTipoReconexion(string? tipo) =>
            !string.IsNullOrWhiteSpace(tipo) && (
                tipo.Contains("recon", StringComparison.OrdinalIgnoreCase) ||
                tipo.Contains("repon", StringComparison.OrdinalIgnoreCase) ||
                tipo.Contains("repos", StringComparison.OrdinalIgnoreCase));

        public async Task<List<BitacoraReporteDto>> ObtenerBitacoraAsync(int limite = 50, CancellationToken ct = default)
        {
            return await context.BitacoraReportes
                .OrderByDescending(b => b.Fecha)
                .Take(limite)
                .Select(b => new BitacoraReporteDto
                {
                    IdBitacora = b.IdBitacora,
                    Fecha = b.Fecha,
                    Usuario = b.Usuario,
                    TipoReporte = b.TipoReporte,
                    Referencia = b.Referencia,
                    Accion = b.Accion,
                    Detalle = b.Detalle
                })
                .ToListAsync(ct);
        }

        private async Task RegistrarEnBitacoraAsync(string usuario, string tipo, string referencia, string accion, string? detalle, string? ip, CancellationToken ct)
        {
            try
            {
                static string Trunc(string? s, int max) => string.IsNullOrEmpty(s) ? string.Empty : (s.Length <= max ? s : s[..max]);
                var entry = new BitacoraReporte
                {
                    Fecha = DateTime.UtcNow,
                    Usuario = Trunc(usuario, 254),
                    TipoReporte = Trunc(tipo, 64),
                    Referencia = Trunc(referencia, 254),
                    Accion = Trunc(accion, 128),
                    Detalle = detalle == null ? null : Trunc(detalle, 1000),
                    Ip = ip == null ? null : Trunc(ip, 64)
                };
                context.BitacoraReportes.Add(entry);
                await context.SaveChangesAsync(ct);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error registrando en bitácora: {ex.Message}");
            }
        }
    }
}
