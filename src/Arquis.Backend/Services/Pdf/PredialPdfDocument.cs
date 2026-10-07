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
            col.Item().Border(1).BorderColor("#e2e8f0").Background("#ffffff").Padding(10).Column(d =>
            {
                d.Item().Text("DICTAMEN Y RECOMENDACIÓN TÉCNICA").FontSize(9.5f).Bold().FontColor("#0f2a50");
                d.Item().PaddingTop(4).Text(
                    _model.TieneAgua
                        ? "1. Predio apto para trámites de derecho propietario, regularización de plano de lote o permiso de edificación.\n2. Se certifica que la infraestructura de agua potable se encuentra en operación normal.\n3. Los linderos y vértices se encuentran debidamente georreferenciados en el sistema catastral municipal."
                        : "1. Se recomienda a la parte interesada coordinar con la entidad prestadora de servicios de agua potable para la instalación de acometida formal.\n2. Los límites perimétricos y la geometría cartográfica están registrados y reconocidos en el plano base municipal."
                ).FontSize(8.5f).FontColor("#334155").LineHeight(1.3f);
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
