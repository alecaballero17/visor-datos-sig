using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using QuestPDF.Fluent;
using QuestPDF.Helpers;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfReportSharedComponents
{
    public static void RenderKpiGrid(IContainer container, List<(string Label, string Value, string AccentHex)> kpis)
    {
        if (kpis.Count == 0) return;

        container.Row(row =>
        {
            row.Spacing(6);
            foreach (var kpi in kpis)
            {
                row.RelativeItem().Border(1).BorderColor("#dadce0").Background("#f8f9fa")
                    .BorderLeft(3).BorderColor(kpi.AccentHex)
                    .PaddingVertical(5).PaddingHorizontal(7)
                    .Column(col =>
                    {
                        col.Item().Text(kpi.Label).FontSize(6.8f).FontColor("#5f6368").SemiBold();
                        col.Item().PaddingTop(1).Text(kpi.Value).FontSize(11).Bold().FontColor("#202124");
                    });
            }
        });
    }

    public static void RenderNarrativeSection(IContainer container, string title, string summary, List<string>? bullets = null)
    {
        container.Border(1).BorderColor("#dadce0").Background("#ffffff").Padding(8).Column(col =>
        {
            col.Item().Text(title).FontSize(8.5f).Bold().FontColor("#202124");
            col.Item().PaddingTop(3).Text(summary).FontSize(8).FontColor("#3c4043").LineHeight(1.25f);

            if (bullets != null && bullets.Count > 0)
            {
                col.Item().PaddingTop(4).Column(b =>
                {
                    foreach (var item in bullets)
                    {
                        b.Item().Text($"• {item}").FontSize(7.5f).FontColor("#5f6368").LineHeight(1.2f);
                    }
                });
            }
        });
    }

    public static void RenderStyledTable(
        IContainer container,
        string sectionTitle,
        List<(string Title, float Weight)> columns,
        List<List<(string Text, string? ColorHex, bool Bold)>> rows,
        string emptyMessage = "No hay registros disponibles para los filtros aplicados.")
    {
        container.Column(col =>
        {
            col.Item().PaddingBottom(4).Text(sectionTitle).FontSize(9).Bold().FontColor("#202124");

            if (rows.Count == 0)
            {
                col.Item().Border(1).BorderColor("#dadce0").Background("#f8f9fa").Padding(10)
                    .Text(emptyMessage).FontSize(8).FontColor("#5f6368");
                return;
            }

            col.Item().Border(1).BorderColor("#dadce0").Table(table =>
            {
                table.ColumnsDefinition(defs =>
                {
                    foreach (var c in columns)
                    {
                        defs.RelativeColumn(c.Weight);
                    }
                });

                table.Header(h =>
                {
                    foreach (var c in columns)
                    {
                        h.Cell().Background("#f1f3f4").BorderBottom(1).BorderColor("#dadce0")
                            .PaddingVertical(4).PaddingHorizontal(5)
                            .Text(c.Title).FontSize(7).Bold().FontColor("#3c4043");
                    }
                });

                for (int rIdx = 0; rIdx < rows.Count; rIdx++)
                {
                    var row = rows[rIdx];
                    var bg = rIdx % 2 == 0 ? "#ffffff" : "#f8f9fa";
                    for (int cIdx = 0; cIdx < columns.Count; cIdx++)
                    {
                        var cell = cIdx < row.Count ? row[cIdx] : (Text: "—", ColorHex: (string?)null, Bold: false);
                        var txt = table.Cell().Background(bg).BorderBottom(0.5f).BorderColor("#e2e8f0")
                            .PaddingVertical(3).PaddingHorizontal(5)
                            .Text(cell.Text ?? "—").FontSize(7).FontColor(cell.ColorHex ?? "#202124");
                        if (cell.Bold) txt.SemiBold();
                    }
                }
            });
        });
    }

    public static string ComputeAuditHash(string seed)
    {
        var bytes = SHA256.HashData(Encoding.UTF8.GetBytes(seed));
        return Convert.ToHexString(bytes)[..16];
    }
}
