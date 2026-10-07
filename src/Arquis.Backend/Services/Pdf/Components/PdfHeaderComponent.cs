using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfHeaderComponent
{
    public static void Render(IContainer container, string title, string subtitle, string folio, string fecha)
    {
        container.BorderBottom(2).BorderColor("#0f2a50").PaddingBottom(12).Row(row =>
        {
            row.RelativeItem().Column(col =>
            {
                col.Item().Text("GOBIERNO AUTÓNOMO MUNICIPAL").FontSize(9).FontColor("#64748b").Bold().LetterSpacing(0.05f);
                col.Item().Text("DIRECCIÓN DE CATASTRO Y PLANIFICACIÓN URBANA").FontSize(8).FontColor("#94a3b8").SemiBold();
                col.Item().PaddingTop(4).Text(title).FontSize(18).FontColor("#0f2a50").ExtraBold();
                col.Item().Text(subtitle).FontSize(10).FontColor("#0284c7").Medium();
            });

            row.ConstantItem(150).Column(col =>
            {
                col.Item().AlignRight().Container()
                    .Background("#f1f5f9")
                    .PaddingVertical(4)
                    .PaddingHorizontal(8)
                    .Border(1)
                    .BorderColor("#cbd5e1")
                    .Column(c =>
                    {
                        c.Item().Text($"FOLIO AUDITORÍA: {folio}").FontSize(8).FontColor("#0f2a50").Bold();
                        c.Item().Text($"EMISIÓN: {fecha}").FontSize(7.5f).FontColor("#64748b");
                        c.Item().Text("ESTADO: CERTIFICADO OFICIAL").FontSize(7).FontColor("#16a34a").Bold();
                    });
            });
        });
    }
}
