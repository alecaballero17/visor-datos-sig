using System;
using System.Collections.Generic;
using Arquis.Backend.Models.Reports;
using Arquis.Backend.Services.Pdf.Components;
using NetTopologySuite.Geometries;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf;

public class PredialPdfDocument : IDocument
{
    private readonly ReportePredialDto _model;
    private readonly Geometry? _geometry;
    private readonly Point? _waterPoint;

    public PredialPdfDocument(ReportePredialDto model, Geometry? geometry = null, Point? waterPoint = null)
    {
        _model = model;
        _geometry = geometry;
        _waterPoint = waterPoint;
    }

    public DocumentMetadata GetMetadata() => DocumentMetadata.Default;
    public DocumentSettings GetSettings() => DocumentSettings.Default;

    public void Compose(IDocumentContainer container)
    {
        container.Page(page =>
        {
            page.Size(PageSizes.A4);
            page.Margin(20);
            page.PageColor(Colors.White);
            page.DefaultTextStyle(x => x.FontFamily("Lato").FontSize(8.5f).FontColor("#1e293b"));

            page.Header().Element(ComposeHeader);
            page.Content().Element(ComposeContent);
            page.Footer().Element(ComposeFooter);
        });
    }

    private void ComposeHeader(IContainer container)
    {
        var fechaStr = _model.FechaEmision.ToString("dd/MM/yyyy HH:mm");
        var folio = $"PRED-{_model.IdLote:D5}-{_model.FechaEmision:yyyyMMdd}";
        PdfHeaderComponent.Render(container, "DICTAMEN TÉCNICO CATASTRAL", $"INFORME PREDIAL INDIVIDUAL · LOTE N° {_model.NumeroLote}", folio, fechaStr);
    }

    private void ComposeContent(IContainer container)
    {
        container.PaddingVertical(6).Column(col =>
        {
            col.Spacing(6);

            // 1. Diagnóstico de Agua Potable y Habitabilidad
            col.Item().Element(c => PdfDiagnosticCardComponent.RenderWaterDiagnostic(
                c, _model.TieneAgua, _model.CodigoSuministro, _model.CondicionOperativa));

            // 2. Ficha de Identificación del Predio
            var metadata = new List<(string Label, string Value)>
            {
                ("Identificador Catastral:", $"LOTE {_model.NumeroLote}"),
                ("ID Interno SIG:", $"#{_model.IdLote}"),
                ("Unidad Vecinal (UV):", _model.UnidadVecinal ?? "Sin asignar"),
                ("Manzana (MZA):", _model.Manzana ?? "Sin asignar"),
                ("Código de Origen:", _model.ClaveOrigen ?? "N/A"),
                ("Servicio Agua Potable:", _model.TieneAgua ? "Habilitado (Con Conexión)" : "No disponible / Sin Acometida"),
                ("Titular Registrado:", _model.Titular ?? "Sin titular asignado"),
                ("Código Suministro:", _model.CodigoSuministro ?? "Ninguno vinculado")
            };
            col.Item().Element(c => PdfMetadataTableComponent.RenderKeyValues(c, "IDENTIFICACIÓN Y LOCALIZACIÓN CATASTRAL", metadata));

            // 3. Vector y Planimetría Cartográfica
            col.Item().Element(c => PdfGeometryMetricsComponent.Render(c, _geometry, _model.TieneAgua, _waterPoint));

            // 4. Dictamen Técnico y Recomendaciones Urbanísticas
            col.Item().Border(1).BorderColor("#dadce0").Background("#ffffff").Padding(8).Column(d =>
            {
                d.Item().Text("DICTAMEN TÉCNICO Y RECOMENDACIÓN").FontSize(9).Bold().FontColor("#202124");
                d.Item().PaddingTop(3).Text(
                    _model.TieneAgua
                        ? "1. Predio verificado con infraestructura activa de agua potable en el sistema municipal.\n2. Linderos y vértices debidamente georreferenciados en el plano base catastral.\n3. Apto para trámites administrativos de derecho propietario y licencias urbanísticas."
                        : "1. No se registra conexión de agua potable en el padrón catastral.\n2. Se sugiere gestionar la solicitud de acometida formal ante la administración de servicios básicos.\n3. Geometría perimétrica reconocida en la base cartográfica municipal."
                ).FontSize(8).FontColor("#3c4043").LineHeight(1.25f);
            });

            // 5. Trazabilidad de Bitácora
            var hash = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.Text.Encoding.UTF8.GetBytes($"{_model.IdLote}-{_model.FechaEmision:O}-{_model.UsuarioEmisor}")))[..16];
            col.Item().Element(c => PdfAuditTraceabilityComponent.Render(c, _model.UsuarioEmisor, _model.FechaEmision.ToString("dd/MM/yyyy HH:mm:ss"), "127.0.0.1 (Local)", hash));
        });
    }

    private void ComposeFooter(IContainer container)
    {
        PdfFooterComponent.Render(container);
    }
}
