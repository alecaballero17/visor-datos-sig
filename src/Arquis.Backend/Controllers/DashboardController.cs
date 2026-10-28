using System;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Arquis.Backend.Data;

namespace Arquis.Backend.Controllers
{
    [ApiController]
    [Route("api/dashboard")]
    public class DashboardController : ControllerBase
    {
        private readonly ArquisDbContext _context;

        public DashboardController(ArquisDbContext context)
        {
            _context = context;
        }

        /// <summary>
        /// RF-WEB-02: Dashboard General y Métricas Operativas.
        /// Indicadores clave de rendimiento (KPIs), comparativas por cuadrilla y distribución porcentual.
        /// </summary>
        [HttpGet("kpis")]
        public async Task<IActionResult> ObtenerKpis()
        {
            // 1. Tarjetas de Resumen: Estados de Conexiones Catastradas
            // Catálogo estándar: 1=Normal, 2=Para Corte, 3=Cortado, 4=Baja Parcial, 5=Baja Total
            var totalConexiones = await _context.CodigosFijos.CountAsync();
            var countNormal = await _context.CodigosFijos.CountAsync(c => c.Estado == 1);
            var countParaCorte = await _context.CodigosFijos.CountAsync(c => c.Estado == 2);
            var countCortado = await _context.CodigosFijos.CountAsync(c => c.Estado == 3);
            var countBajaParcial = await _context.CodigosFijos.CountAsync(c => c.Estado == 4);
            var countBajaTotal = await _context.CodigosFijos.CountAsync(c => c.Estado == 5);

            var countSinVerificar = await _context.CodigosFijos.CountAsync(c => c.Estado < 1 || c.Estado > 5);
            var estadosNoVerificados = await _context.CodigosFijos.CountAsync(c => !c.EstadoVerificado);

            // 2. Gráfico de Dona: Distribución porcentual del estado de las conexiones del municipio
            double sumTotal = totalConexiones > 0 ? totalConexiones : 1;
            double pctNormal = Math.Round((double)countNormal / sumTotal * 100.0, 1);
            double pctParaCorte = Math.Round((double)countParaCorte / sumTotal * 100.0, 1);
            double pctCortado = Math.Round((double)countCortado / sumTotal * 100.0, 1);
            double pctBajaParcial = Math.Round((double)countBajaParcial / sumTotal * 100.0, 1);
            double pctBajaTotal = Math.Round((double)countBajaTotal / sumTotal * 100.0, 1);

            // 3. Gráfico de Barras: Comparativa de intervenciones ejecutadas vs. pendientes por cuadrilla
            var rutasConPuntos = await _context.RutasTrabajo
                .Include(r => r.Puntos)
                .ToListAsync();

            var cuadrillasStats = rutasConPuntos
                .GroupBy(r => string.IsNullOrWhiteSpace(r.OperarioAsignado) ? "Cuadrilla General" : r.OperarioAsignado)
                .Select(g =>
                {
                    int total = g.SelectMany(r => r.Puntos).Count();
                    int ejecutadas = g.SelectMany(r => r.Puntos).Count(p => p.Estado == "Completado" || p.Estado == "Ejecutado");
                    int pendientes = g.SelectMany(r => r.Puntos).Count(p => p.Estado == "Pendiente");
                    int observadas = g.SelectMany(r => r.Puntos).Count(p => p.Estado == "Observado");
                    double avance = total > 0 ? Math.Round((double)ejecutadas / total * 100.0, 1) : 0;

                    return new
                    {
                        Operario = g.Key,
                        Rol = g.Any(r => r.Tipo == "Corte") ? "Cortador" : "Reconector",
                        TotalAsignadas = total,
                        Ejecutadas = ejecutadas,
                        Pendientes = pendientes,
                        Observadas = observadas,
                        PorcentajeCumplimiento = avance
                    };
                })
                .OrderByDescending(c => c.TotalAsignadas)
                .ToList();

            var totalLotes = await _context.Lotes.CountAsync();
            var totalVias = await _context.Vias.CountAsync();
            var totalManzanas = await _context.Manzanas.CountAsync();

            return Ok(new
            {
                // Tarjetas de Resumen RF-WEB-02
                tarjetasResumen = new
                {
                    totalConexionesCatastradas = totalConexiones,
                    conexionesNormal = countNormal,
                    conexionesParaCorte = countParaCorte,
                    conexionesCortado = countCortado,
                    conexionesBajaParcial = countBajaParcial,
                    conexionesBajaTotal = countBajaTotal,
                    conexionesSinClasificar = countSinVerificar,
                    estadosNoVerificados
                },
                // Gráfico de Dona RF-WEB-02
                graficoDona = new
                {
                    total = totalConexiones,
                    porcentajes = new
                    {
                        normal = pctNormal,
                        paraCorte = pctParaCorte,
                        cortado = pctCortado,
                        bajaParcial = pctBajaParcial,
                        bajaTotal = pctBajaTotal,
                        sinClasificar = Math.Round(countSinVerificar / sumTotal * 100.0, 1)
                    },
                    cantidades = new
                    {
                        normal = countNormal,
                        paraCorte = countParaCorte,
                        cortado = countCortado,
                        bajaParcial = countBajaParcial,
                        bajaTotal = countBajaTotal
                    }
                },
                // Gráfico de Barras RF-WEB-02
                graficoBarrasCuadrillas = cuadrillasStats,
                // Resumen territorial general
                infraestructuraTerritorial = new
                {
                    lotes = totalLotes,
                    vias = totalVias,
                    manzanas = totalManzanas
                }
            });
        }
    }
}
