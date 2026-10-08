using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfFooterComponent
{
    public static void Render(IContainer container)
    {
        container.BorderTop(1).BorderColor("#e2e8f0").PaddingTop(8).Row(r =>
        {
            r.RelativeItem().Column(c =>
            {
                c.Item().Text("Sistema de Información Geográfica Catastral · Arquis SIG").FontSize(7.5f).FontColor("#64748b");
                c.Item().Text("Documento emitido conforme a las bases de datos cartográficas oficiales vigentes.").FontSize(7).FontColor("#94a3b8");
            });

            r.ConstantItem(120).AlignRight().Text(text =>
            {
                text.Span("Página ").FontSize(8).FontColor("#64748b");
                text.CurrentPageNumber().FontSize(8).FontColor("#0f2a50").Bold();
                text.Span(" de ").FontSize(8).FontColor("#64748b");
                text.TotalPages().FontSize(8).FontColor("#0f2a50").Bold();
            });
        });
    }
}
