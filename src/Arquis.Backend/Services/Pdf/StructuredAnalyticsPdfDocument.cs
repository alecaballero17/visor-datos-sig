using System;
using System.Collections.Generic;
using System.Linq;
using Arquis.Backend.Models.Reports;
using Arquis.Backend.Services.Pdf.Components;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf;

public sealed class StructuredAnalyticsPdfDocument : IDocument
{
    private readonly string _docTitle;
    private readonly string _docSubtitle;
    private readonly string _folio;
    private readonly DateTime _fechaEmision;
    private readonly string _usuario;
    private readonly string _ip;
    private readonly Action<ColumnDescriptor> _bodyComposer;

    public StructuredAnalyticsPdfDocument(
        string docTitle,
        string docSubtitle,
        string folio,
        DateTime fechaEmision,
        string usuario,
        string ip,
        Action<ColumnDescriptor> bodyComposer)
    {
        _docTitle = docTitle;
        _docSubtitle = docSubtitle;
        _folio = folio;
        _fechaEmision = fechaEmision;
        _usuario = usuario;
        _ip = ip;
        _bodyComposer = bodyComposer;
    }

    public DocumentMetadata GetMetadata() => DocumentMetadata.Default;
    public DocumentSettings GetSettings() => DocumentSettings.Default;

    public void Compose(IDocumentContainer container)
    {
        container.Page(page =>
        {
            page.Size(PageSizes.A4);
            page.Margin(22);
            page.PageColor(Colors.White);
            page.DefaultTextStyle(x => x.FontFamily("Lato").FontSize(8.5f).FontColor("#1e293b"));

            page.Header().Element(c => PdfHeaderComponent.Render(
                c, _docTitle, _docSubtitle, _folio, _fechaEmision.ToString("dd/MM/yyyy HH:mm")));

            page.Content().PaddingVertical(8).Column(col =>
            {
                col.Spacing(8);
                _bodyComposer(col);

                var hash = PdfReportSharedComponents.ComputeAuditHash($"{_folio}-{_fechaEmision:O}-{_usuario}");
                col.Item().Element(c => PdfAuditTraceabilityComponent.Render(
                    c, _usuario, _fechaEmision.ToString("dd/MM/yyyy HH:mm:ss"), _ip, hash));
            });

            page.Footer().Element(PdfFooterComponent.Render);
        });
    }

    public static IDocument ForOperacionesRutas(ReporteOperacionesRutasDto model, string ip) =>
        new StructuredAnalyticsPdfDocument(
            model.Titulo,
            $"{model.Subtitulo} · {model.FiltroAplicado}",
            model.CodigoReporte,
            model.FechaEmision,
            model.UsuarioEmisor,
            ip,
            col =>
            {
                col.Item().Element(c => PdfReportSharedComponents.RenderKpiGrid(c, new()
                {
                    ("ÓRDENES / RUTAS", $"{model.TotalRutas}", "#1a73e8"),
                    ("PARADAS TOTALES", $"{model.TotalParadas}", "#0f2a50"),
                    ("EJECUTADAS", $"{model.ParadasCompletadas} ({model.PorcentajeAvance}%)", "#137333"),
                    ("OBSERVADAS", $"{model.ParadasObservadas}", "#d97706"),
                    ("DISTANCIA DIJKSTRA", $"{model.DistanciaTotalKm:F2} km", "#0284c7")
                }));

                col.Item().Element(c => PdfMetadataTableComponent.RenderKeyValues(c, "PARÁMETROS Y CONSOLIDADO OPERATIVO", new()
                {
                    ("Filtros Aplicados:", model.FiltroAplicado),
                    ("Monto Total en Mora:", $"Bs. {model.MontoTotalDeudaBs:N2}"),
                    ("Rutas Completadas:", $"{model.RutasCompletadas} de {model.TotalRutas}"),
                    ("Validación Antifraude (<=30m):", $"{model.ValidacionesAntifraudeOk} / {model.ValidacionesGpsTotales}"),
                    ("En Progreso / Pendientes:", $"{model.RutasEnProgreso} en curso · {model.RutasPendientes} pendientes"),
                    ("Paradas Pendientes:", $"{model.ParadasPendientes} predios")
                }));

                col.Item().Element(c => PdfReportSharedComponents.RenderNarrativeSection(
                    c, "SÍNTESIS EJECUTIVA Y RECOMENDACIONES", model.ResumenEjecutivo, model.Recomendaciones));

                var rutaCols = new List<(string, float)>
                {
                    ("Código", 1.8f),
                    ("Tipo", 1.3f),
                    ("Operario", 1.8f),
                    ("Estado", 1.4f),
                    ("Dist. (km)", 1.1f),
                    ("Avance", 1.2f),
                    ("Mora (Bs.)", 1.4f)
                };
                var rutaRows = model.Rutas.Take(40).Select(r => new List<(string, string?, bool)>
                {
                    (r.Codigo, "#1a73e8", true),
                    (r.Tipo, r.Tipo == "Corte" ? "#c5221f" : "#1a73e8", true),
                    (r.OperarioAsignado, null, false),
                    (r.Estado, r.Estado == "Completada" ? "#137333" : "#5f6368", false),
                    ($"{r.DistanciaKm:F2}", null, false),
                    ($"{r.PuntosCompletados}/{r.TotalPuntos}", null, true),
                    ($"{r.MontoDeudaTotalBs:N2}", null, false)
                }).ToList();

                col.Item().Element(c => PdfReportSharedComponents.RenderStyledTable(
                    c, $"DETALLE DE ÓRDENES DE TRABAJO (Mostrando {rutaRows.Count} de {model.Rutas.Count})", rutaCols, rutaRows));
            });

    public static IDocument ForCuadrillas(ReporteDesempenoCuadrillasDto model, string ip) =>
        new StructuredAnalyticsPdfDocument(
            model.Titulo,
            $"{model.Subtitulo} · {model.FiltroAplicado}",
            model.CodigoReporte,
            model.FechaEmision,
            model.UsuarioEmisor,
            ip,
            col =>
            {
                col.Item().Element(c => PdfReportSharedComponents.RenderKpiGrid(c, new()
                {
                    ("OPERARIOS", $"{model.TotalOperarios}", "#1a73e8"),
                    ("CORTADORES", $"{model.TotalCortadores}", "#dc2626"),
                    ("REPONEDORES", $"{model.TotalReconectores}", "#0284c7"),
                    ("EJECUTADAS", $"{model.TotalEjecutadas}/{model.TotalParadasAsignadas}", "#137333"),
                    ("CUMPLIMIENTO", $"{model.CumplimientoPromedioPct}%", "#0f2a50")
                }));

                col.Item().Element(c => PdfReportSharedComponents.RenderNarrativeSection(
                    c, "ANÁLISIS DE PRODUCTIVIDAD EN CAMPO", model.ResumenEjecutivo, model.Recomendaciones));

                var cols = new List<(string, float)>
                {
                    ("Operario", 2.2f),
                    ("Rol", 1.8f),
                    ("Rutas", 0.9f),
                    ("Asignadas", 1.0f),
                    ("Ejecut.", 0.9f),
                    ("Obs.", 0.8f),
                    ("Cumpl.", 1.1f),
                    ("Dist. km", 1.1f),
                    ("GPS Prom.", 1.2f)
                };
                var rows = model.Cuadrillas.Select(q => new List<(string, string?, bool)>
                {
                    ($"{q.NombreOperario} ({q.OperarioId})", "#202124", true),
                    (q.Rol, q.Rol.Contains("Cortador") ? "#c5221f" : "#1a73e8", true),
                    ($"{q.RutasAsignadas}", null, false),
                    ($"{q.ParadasTotales}", null, false),
                    ($"{q.Ejecutadas}", "#137333", true),
                    ($"{q.Observadas}", q.Observadas > 0 ? "#d97706" : "#5f6368", false),
                    ($"{q.PorcentajeCumplimiento}%", q.PorcentajeCumplimiento >= 80 ? "#137333" : "#1a73e8", true),
                    ($"{q.DistanciaTotalKm:F2}", null, false),
                    (q.PrecisionGpsPromedioMetros.HasValue ? $"{q.PrecisionGpsPromedioMetros:F1} m" : "—", null, false)
                }).ToList();

                col.Item().Element(c => PdfReportSharedComponents.RenderStyledTable(
                    c, "RANKING Y PRODUCTIVIDAD POR TÉCNICO DE CAMPO", cols, rows));
            });

    public static IDocument ForSuministros(ReporteEstadoSuministrosDto model, string ip) =>
        new StructuredAnalyticsPdfDocument(
            model.Titulo,
            $"{model.Subtitulo} · {model.FiltroAplicado}",
            model.CodigoReporte,
            model.FechaEmision,
            model.UsuarioEmisor,
            ip,
            col =>
            {
                col.Item().Element(c => PdfReportSharedComponents.RenderKpiGrid(c, new()
                {
                    ("TOTAL CUENTAS", $"{model.TotalSuministros}", "#0f2a50"),
                    ("NORMAL", $"{model.Normal}", "#137333"),
                    ("PARA CORTE", $"{model.ParaCorte}", "#d97706"),
                    ("CORTADOS", $"{model.Cortado}", "#dc2626"),
                    ("PARA RECONEXIÓN", $"{model.ParaReconexion}", "#0284c7")
                }));

                col.Item().Element(c => PdfMetadataTableComponent.RenderKeyValues(c, "DISTRIBUCIÓN DE ESTADOS Y VERIFICACIÓN", new()
                {
                    ("Filtro Aplicado:", model.FiltroAplicado),
                    ("Baja Parcial / Total:", $"{model.BajaParcial} parcial · {model.BajaTotal} total"),
                    ("Verificados en Campo:", $"{model.Verificados} conexiones"),
                    ("Pendientes de Verificar:", $"{model.SinVerificar} conexiones")
                }));

                col.Item().Element(c => PdfReportSharedComponents.RenderNarrativeSection(
                    c, "DIAGNÓSTICO DE CARTERA COMERCIAL", model.ResumenEjecutivo, model.Recomendaciones));

                var cols = new List<(string, float)>
                {
                    ("Cód. Fijo", 1.3f),
                    ("Clave SIG", 1.4f),
                    ("Titular / Abonado", 2.5f),
                    ("Ubicación", 1.7f),
                    ("Estado Actual", 2.0f),
                    ("Verif.", 1.1f)
                };
                var rows = model.Suministros.Take(60).Select(s => new List<(string, string?, bool)>
                {
                    (s.CodigoFijo, "#202124", true),
                    (s.CodigoSig, "#5f6368", false),
                    (s.Titular, null, false),
                    ($"UV {s.UnidadVecinal} · MZA {s.Manzana} · L{s.NumeroLote}", null, false),
                    (s.EstadoTexto, s.EstadoCodigo == 1 ? "#137333" : (s.EstadoCodigo is 2 or 3 ? "#c5221f" : "#1a73e8"), true),
                    (s.EstadoVerificado ? "Sí" : "No", s.EstadoVerificado ? "#137333" : "#5f6368", false)
                }).ToList();

                col.Item().Element(c => PdfReportSharedComponents.RenderStyledTable(
                    c, $"PADRÓN DE SUMINISTROS AUDITADOS (Muestra {rows.Count} de {model.Suministros.Count})", cols, rows));
            });

    public static IDocument ForEjecutivoGlobal(ReporteEjecutivoGlobalDto model, string ip) =>
        new StructuredAnalyticsPdfDocument(
            model.Titulo,
            model.Subtitulo,
            model.CodigoReporte,
            model.FechaEmision,
            model.UsuarioEmisor,
            ip,
            col =>
            {
                col.Item().Element(c => PdfReportSharedComponents.RenderKpiGrid(c, new()
                {
                    ("PREDIOS CATASTRO", $"{model.TotalLotes:N0}", "#0f2a50"),
                    ("COBERTURA HÍDRICA", $"{model.CoberturaGlobalPct}%", "#1a73e8"),
                    ("ACOMETIDAS", $"{model.TotalCodigosFijos:N0}", "#137333"),
                    ("RED VIAL (KM)", $"{model.LongitudRedVialKm:N1} km", "#0284c7"),
                    ("EFECTIVIDAD CAMPO", $"{model.TasaEfectividadCampoPct}%", "#d97706")
                }));

                col.Item().Element(c => PdfMetadataTableComponent.RenderKeyValues(c, "BALANCE TERRITORIAL Y OPERATIVO", new()
                {
                    ("Manzanas / Ejes Viales:", $"{model.TotalManzanas:N0} manzanas · {model.TotalVias:N0} vías"),
                    ("Lotes Con / Sin Agua:", $"{model.LotesConServicio:N0} con agua · {model.LotesSinServicio:N0} sin servicio"),
                    ("Normal / Para Corte:", $"{model.Normal:N0} normal · {model.ParaCorte:N0} para corte"),
                    ("Cortado / Reconexión:", $"{model.Cortado:N0} cortado · {model.ParaReconexion:N0} para reconexión"),
                    ("Baja Parcial / Total:", $"{model.BajaParcial:N0} parcial · {model.BajaTotal:N0} total"),
                    ("Órdenes Históricas:", $"{model.TotalRutasHistoricas:N0} rutas ({model.IntervencionesCompletadas}/{model.TotalIntervencionesCampo} paradas)")
                }));

                col.Item().Element(c => PdfReportSharedComponents.RenderNarrativeSection(
                    c, "DICTAMEN EJECUTIVO MUNICIPAL", model.ResumenEjecutivo, model.Recomendaciones));

                var cols = new List<(string, float)>
                {
                    ("Unidad Vecinal", 1.6f),
                    ("Manzanas", 1.2f),
                    ("Total Lotes", 1.3f),
                    ("Con Agua", 1.3f),
                    ("Cobertura %", 1.3f),
                    ("Para Corte", 1.1f),
                    ("Cortadas", 1.1f),
                    ("Para Rec.", 1.1f)
                };
                var rows = model.ResumenPorUv.Select(u => new List<(string, string?, bool)>
                {
                    ($"UV {u.UnidadVecinal}", "#202124", true),
                    ($"{u.TotalManzanas}", null, false),
                    ($"{u.TotalLotes:N0}", null, false),
                    ($"{u.LotesConAgua:N0}", "#137333", true),
                    ($"{u.CoberturaPct}%", "#1a73e8", true),
                    ($"{u.CuentasParaCorte}", u.CuentasParaCorte > 0 ? "#d97706" : "#5f6368", false),
                    ($"{u.CuentasCortadas}", u.CuentasCortadas > 0 ? "#c5221f" : "#5f6368", false),
                    ($"{u.CuentasParaReconexion}", "#0284c7", false)
                }).ToList();

                col.Item().Element(c => PdfReportSharedComponents.RenderStyledTable(
                    c, "DESGLOSE TERRITORIAL POR UNIDAD VECINAL (TOP 25)", cols, rows));
            });
}
