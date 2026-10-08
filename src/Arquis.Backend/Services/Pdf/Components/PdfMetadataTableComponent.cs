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
            col.Item().PaddingBottom(4).Text(sectionTitle).FontSize(9.5f).Bold().FontColor("#202124");

            col.Item().Border(1).BorderColor("#dadce0").Table(table =>
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
                    var bg = (i / 2) % 2 == 0 ? "#f8f9fa" : "#ffffff";

                    table.Cell().Background(bg).PaddingVertical(3.5f).PaddingHorizontal(6).Row(r =>
                    {
                        r.RelativeItem(4).Text(item1.Label).FontSize(8).FontColor("#5f6368");
                        r.RelativeItem(6).Text(item1.Value).FontSize(8).FontColor("#202124").SemiBold();
                    });

                    if (hasSecond)
                    {
                        table.Cell().Background(bg).PaddingVertical(3.5f).PaddingHorizontal(6).Row(r =>
                        {
                            r.RelativeItem(4).Text(item2.Label).FontSize(8).FontColor("#5f6368");
                            r.RelativeItem(6).Text(item2.Value).FontSize(8).FontColor("#202124").SemiBold();
                        });
                    }
                    else
                    {
                        table.Cell().Background(bg).Padding(3.5f).Text("");
                    }
                }
            });
        });
    }
}
