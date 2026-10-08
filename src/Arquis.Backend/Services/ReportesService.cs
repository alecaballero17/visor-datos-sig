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
                .Where(c => c.IdLote == idLote || (c.Geom != null && lote.Geom != null && c.Geom.Intersects(lote.Geom)))
                .ToListAsync(ct);

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
                Titular = codigoPrincipal?.Nombre ?? (tieneAgua ? "Titular Registrado" : "Sin titular vinculado"),
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
                var entry = new BitacoraReporte
                {
                    Fecha = DateTime.UtcNow,
                    Usuario = usuario,
                    TipoReporte = tipo,
                    Referencia = referencia,
                    Accion = accion,
                    Detalle = detalle,
                    Ip = ip
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
