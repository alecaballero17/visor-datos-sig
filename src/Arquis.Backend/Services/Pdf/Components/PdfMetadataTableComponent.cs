using System.Collections.Generic;
using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfMetadataTableComponent
{
    public static void RenderKeyValues(IContainer container, string sectionTitle, List<(string Label, string Value)> items)
    {
        container.Column(col =>
        {
            col.Item().PaddingBottom(6).Text(sectionTitle).FontSize(10.5f).Bold().FontColor("#0f2a50");

            col.Item().Border(1).BorderColor("#e2e8f0").Table(table =>
            {
                table.ColumnsDefinition(columns =>
                {
                    columns.RelativeColumn(1);
                    columns.RelativeColumn(1);
                });

                for (int i = 0; i < items.Count; i += 2)
                {
                    var item1 = items[i];
                    var hasSecond = i + 1 < items.Count;
                    var item2 = hasSecond ? items[i + 1] : default;
                    var bg = (i / 2) % 2 == 0 ? "#f8fafc" : "#ffffff";

                    table.Cell().Background(bg).Padding(6).Row(r =>
                    {
                        r.RelativeItem(4).Text(item1.Label).FontSize(8.5f).FontColor("#64748b").SemiBold();
                        r.RelativeItem(6).Text(item1.Value).FontSize(8.5f).FontColor("#0f172a").Bold();
                    });

                    if (hasSecond)
                    {
                        table.Cell().Background(bg).Padding(6).Row(r =>
                        {
                            r.RelativeItem(4).Text(item2.Label).FontSize(8.5f).FontColor("#64748b").SemiBold();
                            r.RelativeItem(6).Text(item2.Value).FontSize(8.5f).FontColor("#0f172a").Bold();
                        });
                    }
                    else
                    {
                        table.Cell().Background(bg).Padding(6).Text("");
                    }
                }
            });
        });
    }
}
