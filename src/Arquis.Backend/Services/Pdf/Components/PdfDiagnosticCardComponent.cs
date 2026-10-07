using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfDiagnosticCardComponent
{
    public static void RenderWaterDiagnostic(IContainer container, bool tieneAgua, string? codFijo, string? estadoServicio)
    {
        var bgColor = tieneAgua ? "#f0fdf4" : "#fef2f2";
        var borderColor = tieneAgua ? "#86efac" : "#fca5a5";
        var titleColor = tieneAgua ? "#166534" : "#991b1b";
        var statusBadgeBg = tieneAgua ? "#22c55e" : "#ef4444";

        container.Border(1.2f).BorderColor(borderColor).Background(bgColor).Padding(12).Column(col =>
        {
            col.Item().Row(r =>
            {
                r.RelativeItem().Text(tieneAgua ? "SERVICIO DE AGUA POTABLE: OPERATIVO Y DISPONIBLE" : "SERVICIO DE AGUA POTABLE: SIN CONEXIÓN FORMAL")
                    .FontSize(11).Bold().FontColor(titleColor);

                r.ConstantItem(90).AlignRight().Container()
                    .Background(statusBadgeBg)
                    .PaddingVertical(2).PaddingHorizontal(6)
                    .Text(tieneAgua ? "HABILITADO" : "PENDIENTE")
                    .FontSize(8).Bold().FontColor("#ffffff");
            });

            col.Item().PaddingTop(6).Text(tieneAgua
                ? $"El predio cuenta con acometida y suministro de agua potable regularizado bajo el código de usuario {codFijo ?? "Registrado"} con estado técnico {estadoServicio ?? "Normal"}. Cuenta con viabilidad técnica para habitabilidad o edificación."
                : "No se identificó medidor ni conexión domiciliaria de agua potable activa en el registro catastral para este lote. Se sugiere al propietario tramitar la solicitud de acometida ante la cooperativa correspondiente.")
                .FontSize(9).FontColor("#334155").LineHeight(1.25f);
        });
    }
}
