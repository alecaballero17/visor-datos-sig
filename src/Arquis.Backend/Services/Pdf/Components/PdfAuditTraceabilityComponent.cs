using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfAuditTraceabilityComponent
{
    public static void Render(IContainer container, string usuario, string fechaEmision, string ip, string hashAuditoria)
    {
        container.Border(1).BorderColor("#cbd5e1").Background("#f8fafc").Padding(10).Column(col =>
        {
            col.Item().Text("TRAZABILIDAD Y REGISTRO EN BITÁCORA DE AUDITORÍA").FontSize(9).Bold().FontColor("#0f2a50");
            col.Item().PaddingTop(4).Row(r =>
            {
                r.RelativeItem().Column(c =>
                {
                    c.Item().Text($"Operador Emisor: {usuario}").FontSize(8).SemiBold().FontColor("#334155");
                    c.Item().Text($"Terminal / IP Origen: {ip}").FontSize(8).FontColor("#64748b");
                    c.Item().Text($"Fecha/Hora Registro: {fechaEmision} UTC").FontSize(8).FontColor("#64748b");
                });

                r.RelativeItem().Column(c =>
                {
                    c.Item().Text($"Hash de Seguridad: {hashAuditoria}").FontSize(8).FontColor("#0284c7").Bold();
                    c.Item().Text("La emisión de este informe ha quedado registrada de forma inalterable en la bitácora municipal (dbo.BitacoraReportes).").FontSize(7.5f).FontColor("#475569");
                });
            });
        });
    }
}
