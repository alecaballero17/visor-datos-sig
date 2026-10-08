using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfHeaderComponent
{
    public static void Render(IContainer container, string title, string subtitle, string folio, string fecha)
    {
        container.BorderBottom(1).BorderColor("#dadce0").PaddingBottom(8).Row(row =>
        {
            row.RelativeItem().Column(col =>
            {
                col.Item().Text("DIRECCIÓN DE CATASTRO Y ORDENAMIENTO TERRITORIAL").FontSize(8).FontColor("#5f6368").SemiBold();
                col.Item().PaddingTop(2).Text(title).FontSize(14).FontColor("#202124").Bold();
                col.Item().Text(subtitle).FontSize(9).FontColor("#1a73e8");
            });

            row.ConstantItem(140).Column(col =>
            {
                col.Item().AlignRight().Column(c =>
                {
                    c.Item().Text($"FOLIO: {folio}").FontSize(8).FontColor("#202124").Bold();
                    c.Item().Text($"FECHA: {fecha}").FontSize(7.5f).FontColor("#5f6368");
                    c.Item().Text("SISTEMA SIG MUNICIPAL").FontSize(7).FontColor("#137333").SemiBold();
                });
            });
        });
    }
}
