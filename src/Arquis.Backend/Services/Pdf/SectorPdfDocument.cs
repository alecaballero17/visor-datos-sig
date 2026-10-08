using System;
using System.Collections.Generic;
using System.Linq;
using Arquis.Backend.Models.Reports;
using Arquis.Backend.Services.Pdf.Components;
using NetTopologySuite.Geometries;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf;

public class SectorPdfDocument : IDocument
{
    private readonly ReporteSectorDto _model;
    private readonly Geometry? _geometry;

    public SectorPdfDocument(ReporteSectorDto model, Geometry? geometry = null)
    {
        _model = model;
        _geometry = geometry;
    }

    public DocumentMetadata GetMetadata() => DocumentMetadata.Default;
    public DocumentSettings GetSettings() => DocumentSettings.Default;

    public void Compose(IDocumentContainer container)
    {
        container.Page(page =>
        {
            page.Size(PageSizes.A4);
            page.Margin(28);
            page.PageColor(Colors.White);
            page.DefaultTextStyle(x => x.FontFamily("Lato").FontSize(9).FontColor("#1e293b"));

            page.Header().Element(ComposeHeader);
            page.Content().Element(ComposeContent);
            page.Footer().Element(ComposeFooter);
        });
    }

    private void ComposeHeader(IContainer container)
    {
        var fechaStr = _model.FechaEmision.ToString("dd/MM/yyyy HH:mm");
        var folio = $"SEC-{_model.UnidadVecinal}-{_model.Manzana}-{_model.FechaEmision:yyyyMMdd}";
        PdfHeaderComponent.Render(container, "INFORME DE DIAGNÓSTICO URBANO", $"SECTOR TERRITORIAL · UV {_model.UnidadVecinal} / MZA {_model.Manzana}", folio, fechaStr);
    }

    private void ComposeContent(IContainer container)
    {
        container.PaddingVertical(6).Column(col =>
        {
            col.Spacing(6);

            // 1. Resumen Ejecutivo de Cobertura
            var pct = _model.TotalPredios > 0 ? (_model.PrediosConServicio * 100.0 / _model.TotalPredios) : 0;
            col.Item().Border(1).BorderColor("#dadce0").Background("#f8f9fa").Padding(8).Column(c =>
            {
                c.Item().Row(r =>
                {
                    r.RelativeItem().Text($"COBERTURA DE AGUA POTABLE: {pct:F1}%").FontSize(10).Bold().FontColor("#202124");
                    r.ConstantItem(120).AlignRight().Text($"{_model.PrediosConServicio} de {_model.TotalPredios} Predios").FontSize(8.5f).Bold().FontColor("#1a73e8");
                });

                c.Item().PaddingTop(3).Text(
                    $"Sector UV {_model.UnidadVecinal}, MZA {_model.Manzana} cuenta con {_model.TotalPredios} lotes catastrados ({_model.PrediosConServicio} con suministro verificado y {_model.PrediosSinServicio} sin conexión formal)."
                ).FontSize(8).FontColor("#3c4043");
            });

            // 2. Ficha de Datos del Sector
            var metadata = new List<(string Label, string Value)>
            {
                ("Unidad Vecinal (UV):", _model.UnidadVecinal),
                ("Manzana (MZA):", _model.Manzana),
                ("Total de Predios:", $"{_model.TotalPredios} lotes"),
                ("Lotes con Agua Potable:", $"{_model.PrediosConServicio} predios"),
                ("Lotes sin Servicio:", $"{_model.PrediosSinServicio} predios"),
                ("Índice de Cobertura:", $"{pct:F1}%"),
                ("Estado de Consolidación:", _model.IndiceConsolidacion),
                ("Fecha de Relevamiento:", _model.FechaEmision.ToString("dd/MM/yyyy"))
            };
            col.Item().Element(c => PdfMetadataTableComponent.RenderKeyValues(c, "MÉTRICAS TERRITORIALES AGREGADAS", metadata));

            // 3. Vector y Planimetría Cartográfica de la Manzana
            col.Item().Element(c => PdfGeometryMetricsComponent.Render(c, _geometry, pct >= 50));

            // 4. Detalle y Listado Parcial de Lotes en el Sector
            if (_model.Predios != null && _model.Predios.Count > 0)
            {
                col.Item().Column(sec =>
                {
                    sec.Item().PaddingBottom(4).Text("INVENTARIO PREDIAL DEL SECTOR").FontSize(9.5f).Bold().FontColor("#202124");
                    sec.Item().Border(1).BorderColor("#dadce0").Table(t =>
                    {
                        t.ColumnsDefinition(cols =>
                        {
                            cols.RelativeColumn(3);
                            cols.RelativeColumn(3);
                            cols.RelativeColumn(4);
                        });

                        t.Header(h =>
                        {
                            h.Cell().Background("#f8f9fa").BorderBottom(1).BorderColor("#dadce0").Padding(3).Text("N° Lote").FontSize(7.5f).Bold().FontColor("#5f6368");
                            h.Cell().Background("#f8f9fa").BorderBottom(1).BorderColor("#dadce0").Padding(3).Text("Agua Potable").FontSize(7.5f).Bold().FontColor("#5f6368");
                            h.Cell().Background("#f8f9fa").BorderBottom(1).BorderColor("#dadce0").Padding(3).Text("Código Suministro").FontSize(7.5f).Bold().FontColor("#5f6368");
                        });

                        var sampleLotes = _model.Predios.Take(8).ToList();
                        for (int i = 0; i < sampleLotes.Count; i++)
                        {
                            var item = sampleLotes[i];
                            var bg = i % 2 == 0 ? "#ffffff" : "#f8f9fa";
                            t.Cell().Background(bg).Padding(2.5f).Text($"Lote {item.NumeroLote}").FontSize(7).FontColor("#202124");
                            t.Cell().Background(bg).Padding(2.5f).Text(item.TieneAgua ? "Con Suministro" : "Sin Suministro").FontSize(7)
                                .FontColor(item.TieneAgua ? "#137333" : "#5f6368").SemiBold();
                            t.Cell().Background(bg).Padding(2.5f).Text(item.CodigoSuministro ?? (item.TieneAgua ? "Activo" : "No asignado")).FontSize(7).FontColor("#5f6368");
                        }
                    });
                });
            }

            // 5. Trazabilidad de Bitácora
            var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes($"{_model.UnidadVecinal}-{_model.Manzana}-{_model.FechaEmision:O}-{_model.UsuarioEmisor}")))[..16];
            col.Item().Element(c => PdfAuditTraceabilityComponent.Render(c, _model.UsuarioEmisor, _model.FechaEmision.ToString("dd/MM/yyyy HH:mm:ss"), "127.0.0.1 (Local)", hash));
        });
    }

    private void ComposeFooter(IContainer container)
    {
        PdfFooterComponent.Render(container);
    }
}
