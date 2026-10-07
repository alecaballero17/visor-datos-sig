using System;
using Arquis.Backend.Models.Reports;
using NetTopologySuite.Geometries;
using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf;

public sealed class PdfReportGeneratorService
{
    static PdfReportGeneratorService()
    {
        // Licencia comunitaria gratuita de QuestPDF para proyectos educativos y FOSS
        QuestPDF.Settings.License = LicenseType.Community;
        QuestPDF.Settings.UseSystemFonts = true;
        QuestPDF.Settings.ThrowOnMissingFontFamilies = false;
    }

    public byte[] GeneratePredialPdf(ReportePredialDto model, Geometry? geom = null, Point? waterPoint = null)
    {
        var doc = new PredialPdfDocument(model, geom, waterPoint);
        return doc.GeneratePdf();
    }

    public byte[] GenerateSectorPdf(ReporteSectorDto model, Geometry? geom = null)
    {
        var doc = new SectorPdfDocument(model, geom);
        return doc.GeneratePdf();
    }
}
