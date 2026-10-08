using System;
using System.Collections.Generic;
using System.Globalization;
using NetTopologySuite.Geometries;
using QuestPDF.Fluent;
using QuestPDF.Infrastructure;

namespace Arquis.Backend.Services.Pdf.Components;

public static class PdfGeometryMetricsComponent
{
    public static void Render(IContainer container, Geometry? geom, bool tieneAgua, Point? waterPoint = null)
    {
        container.Column(col =>
        {
            col.Item().PaddingBottom(4).Text("REPRESENTACIÓN VECTORIAL Y PLANIMETRÍA").FontSize(9.5f).Bold().FontColor("#202124");

            col.Item().Row(r =>
            {
                // Vector visual SVG
                r.RelativeItem(7).Container().Height(135).Svg(SvgVectorHelper.GeneratePolygonSvg(geom, tieneAgua, waterPoint, 420, 200));

                // Resumen Métrico
                r.RelativeItem(5).PaddingLeft(8).Column(c =>
                {
                    c.Item().Border(1).BorderColor("#dadce0").Background("#f8f9fa").Padding(6).Column(box =>
                    {
                        box.Item().Text("MÉTRICAS CARTOGRÁFICAS").FontSize(8).Bold().FontColor("#202124");
                        
                        double areaM2 = 0;
                        double perimM = 0;
                        int verticesCount = 0;
                        Coordinate? centroid = null;

                        if (geom != null && !geom.IsEmpty)
                        {
                            double mX = 106800.0;
                            double mY = 111320.0;
                            areaM2 = Math.Abs(geom.Area) * mX * mY;
                            perimM = geom.Length * ((mX + mY) / 2.0);
                            verticesCount = geom.Coordinates.Length;
                            centroid = geom.Centroid.Coordinate;
                        }

                        box.Item().PaddingTop(2).Text($"Superficie: {areaM2:N1} m²").FontSize(8).SemiBold().FontColor("#1a73e8");
                        box.Item().Text($"Perímetro: {perimM:N1} m").FontSize(7.5f).FontColor("#3c4043");
                        box.Item().Text($"Vértices: {verticesCount} puntos").FontSize(7.5f).FontColor("#3c4043");
                        box.Item().Text($"Sistema: WGS84 (EPSG:4326)").FontSize(7.5f).FontColor("#5f6368");
                        if (centroid != null)
                        {
                            box.Item().Text($"Centroide: {centroid.X:F5}, {centroid.Y:F5}").FontSize(7.5f).FontColor("#5f6368");
                        }
                    });

                    // Tabla condensada de coordenadas de vértices
                    c.Item().PaddingTop(4).Text("VÉRTICES (WGS84)").FontSize(7.5f).Bold().FontColor("#5f6368");
                    c.Item().Border(1).BorderColor("#dadce0").Table(t =>
                    {
                        t.ColumnsDefinition(cols =>
                        {
                            cols.ConstantColumn(20);
                            cols.RelativeColumn();
                            cols.RelativeColumn();
                        });

                        t.Header(h =>
                        {
                            h.Cell().Background("#f8f9fa").BorderBottom(1).BorderColor("#dadce0").Padding(1.5f).Text("V").FontSize(6.5f).Bold().FontColor("#5f6368");
                            h.Cell().Background("#f8f9fa").BorderBottom(1).BorderColor("#dadce0").Padding(1.5f).Text("Longitud (X)").FontSize(6.5f).Bold().FontColor("#5f6368");
                            h.Cell().Background("#f8f9fa").BorderBottom(1).BorderColor("#dadce0").Padding(1.5f).Text("Latitud (Y)").FontSize(6.5f).Bold().FontColor("#5f6368");
                        });

                        var coords = geom?.Coordinates ?? Array.Empty<Coordinate>();
                        int limit = Math.Min(coords.Length, 4);
                        for (int i = 0; i < limit; i++)
                        {
                            var bg = i % 2 == 0 ? "#ffffff" : "#f8fafc";
                            t.Cell().Background(bg).Padding(1.5f).Text($"V{i + 1}").FontSize(6);
                            t.Cell().Background(bg).Padding(1.5f).Text(coords[i].X.ToString("F6", CultureInfo.InvariantCulture)).FontSize(6);
                            t.Cell().Background(bg).Padding(1.5f).Text(coords[i].Y.ToString("F6", CultureInfo.InvariantCulture)).FontSize(6);
                        }
                    });
                });
            });
        });
    }
}
