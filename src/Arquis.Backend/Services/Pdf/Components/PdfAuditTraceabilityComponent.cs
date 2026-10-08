using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfAuditTraceabilityComponent
{
    public static void Render(IContainer container, string usuario, string fechaEmision, string ip, string hashAuditoria)
    {
        container.Border(1).BorderColor("#dadce0").Background("#f8f9fa").Padding(6).Column(col =>
        {
            col.Item().Text("TRAZABILIDAD Y REGISTRO EN BITÁCORA").FontSize(8).Bold().FontColor("#202124");
            col.Item().PaddingTop(2).Row(r =>
            {
                r.RelativeItem().Column(c =>
                {
                    c.Item().Text($"Operador: {usuario}").FontSize(7.5f).FontColor("#202124").SemiBold();
                    c.Item().Text($"Terminal: {ip} · Emisión: {fechaEmision}").FontSize(7.5f).FontColor("#5f6368");
                });

                r.RelativeItem().Column(c =>
                {
                    c.Item().Text($"Firma Hash: {hashAuditoria}").FontSize(7.5f).FontColor("#1a73e8").Bold();
                    c.Item().Text("Registro inalterable en base catastral municipal.").FontSize(7).FontColor("#5f6368");
                });
            });
        });
    }
}
