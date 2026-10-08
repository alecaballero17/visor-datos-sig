using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfDiagnosticCardComponent
{
    public static void RenderWaterDiagnostic(IContainer container, bool tieneAgua, string? codFijo, string? estadoServicio)
    {
        container.Border(1).BorderColor("#dadce0").Background("#f8f9fa").Padding(8).Column(col =>
        {
            col.Item().Row(r =>
            {
                r.RelativeItem().Text(tieneAgua ? "SERVICIO DE AGUA POTABLE: CONEXIÓN REGISTRADA" : "SERVICIO DE AGUA POTABLE: SIN CONEXIÓN FORMAL")
                    .FontSize(9.5f).Bold().FontColor("#202124");

                r.ConstantItem(85).AlignRight().Container()
                    .Background(tieneAgua ? "#e6f4ea" : "#f1f3f4")
                    .PaddingVertical(2).PaddingHorizontal(6)
                    .Text(tieneAgua ? "HABILITADO" : "PENDIENTE")
                    .FontSize(7.5f).Bold().FontColor(tieneAgua ? "#137333" : "#5f6368");
            });

            col.Item().PaddingTop(3).Text(tieneAgua
                ? $"El predio dispone de acometida formal vinculada al código de suministro #{codFijo ?? "Registrado"} con condición operativa '{estadoServicio ?? "Normal"}'. Cuenta con viabilidad técnica para trámites catastrales."
                : "No se registra código fijo ni medidor formal en la base catastral para este lote. Se sugiere tramitar acometida ante la administración de servicios de agua potable.")
                .FontSize(8).FontColor("#3c4043").LineHeight(1.25f);
        });
    }
}
