using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text;
using NetTopologySuite.Geometries;

namespace Arquis.Backend.Services.Pdf;

public static class SvgVectorHelper
{
    public static string GeneratePolygonSvg(Geometry? geom, bool hasWater, Point? waterPoint = null, int width = 500, int height = 320)
    {
        if (geom == null || geom.IsEmpty)
        {
            return $@"<svg xmlns=""http://www.w3.org/2000/svg"" viewBox=""0 0 {width} {height}"" width=""100%"" height=""100%"">
                <rect width=""{width}"" height=""{height}"" fill=""#f8fafc"" rx=""8"" stroke=""#e2e8f0""/>
                <text x=""{width/2}"" y=""{height/2}"" font-family=""sans-serif"" font-size=""14"" fill=""#94a3b8"" text-anchor=""middle"">
                    Geometría vectorial no disponible
                </text>
            </svg>";
        }

        var env = geom.EnvelopeInternal;
        var padX = env.Width * 0.15;
        var padY = env.Height * 0.15;
        if (padX < 0.00001) padX = 0.0005;
        if (padY < 0.00001) padY = 0.0005;

        var minX = env.MinX - padX;
        var maxX = env.MaxX + padX;
        var minY = env.MinY - padY;
        var maxY = env.MaxY + padY;

        var rangeX = maxX - minX;
        var rangeY = maxY - minY;

        // Proyección a coordenadas SVG (eje Y invertido)
        double ToSvgX(double x) => ((x - minX) / rangeX) * (width - 40) + 20;
        double ToSvgY(double y) => height - (((y - minY) / rangeY) * (height - 40) + 20);

        var sb = new StringBuilder();
        sb.AppendLine($@"<svg xmlns=""http://www.w3.org/2000/svg"" viewBox=""0 0 {width} {height}"" width=""100%"" height=""100%"">");
        
        // Fondo y grilla
        sb.AppendLine($@"  <rect width=""{width}"" height=""{height}"" fill=""#f8fafc"" rx=""10"" stroke=""#cbd5e1"" stroke-width=""1.5""/>");
        sb.AppendLine(@"  <defs>
            <pattern id=""grid"" width=""25"" height=""25"" patternUnits=""userSpaceOnUse"">
                <path d=""M 25 0 L 0 0 0 25"" fill=""none"" stroke=""#f1f5f9"" stroke-width=""1""/>
            </pattern>
            <filter id=""shadow"" x=""-10%"" y=""-10%"" width=""130%"" height=""130%"">
                <feDropShadow dx=""0"" dy=""3"" stdDeviation=""4"" flood-color=""#0f172a"" flood-opacity=""0.15""/>
            </filter>
        </defs>");
        sb.AppendLine($@"  <rect width=""{width}"" height=""{height}"" fill=""url(#grid)"" rx=""10""/>");

        // Polígonos
        var polygons = new List<Polygon>();
        if (geom is Polygon p) polygons.Add(p);
        else if (geom is MultiPolygon mp)
        {
            for (int i = 0; i < mp.NumGeometries; i++)
                if (mp.GetGeometryN(i) is Polygon subP) polygons.Add(subP);
        }

        var strokeColor = hasWater ? "#0284c7" : "#0f766e";
        var fillColor = hasWater ? "rgba(2, 132, 199, 0.20)" : "rgba(15, 118, 110, 0.18)";

        int verticeNum = 1;
        var verticeMarkers = new StringBuilder();

        foreach (var poly in polygons)
        {
            var coords = poly.ExteriorRing.Coordinates;
            if (coords.Length == 0) continue;

            var pointsStr = new StringBuilder();
            for (int i = 0; i < coords.Length; i++)
            {
                var sx = ToSvgX(coords[i].X).ToString("F1", CultureInfo.InvariantCulture);
                var sy = ToSvgY(coords[i].Y).ToString("F1", CultureInfo.InvariantCulture);
                pointsStr.Append($"{sx},{sy} ");

                // Marcadores de vértice (solo primeros 12 vértices para no saturar)
                if (i < coords.Length - 1 && verticeNum <= 12)
                {
                    verticeMarkers.AppendLine($@"  <circle cx=""{sx}"" cy=""{sy}"" r=""4.5"" fill=""#ffffff"" stroke=""{strokeColor}"" stroke-width=""2""/>");
                    verticeMarkers.AppendLine($@"  <text x=""{sx}"" y=""{ToSvgY(coords[i].Y) - 7:F1}"" font-family=""sans-serif"" font-size=""9"" font-weight=""bold"" fill=""#334155"" text-anchor=""middle"">V{verticeNum}</text>");
                    verticeNum++;
                }
            }

            sb.AppendLine($@"  <polygon points=""{pointsStr.ToString().Trim()}"" fill=""{fillColor}"" stroke=""{strokeColor}"" stroke-width=""2.5"" filter=""url(#shadow)"" stroke-linejoin=""round""/>");
        }

        // Vértices encima del polígono
        sb.Append(verticeMarkers.ToString());

        // Conexión de agua (si tiene coordenada de agua)
        if (waterPoint != null && !waterPoint.IsEmpty)
        {
            var wx = ToSvgX(waterPoint.X).ToString("F1", CultureInfo.InvariantCulture);
            var wy = ToSvgY(waterPoint.Y).ToString("F1", CultureInfo.InvariantCulture);
            sb.AppendLine($@"  <circle cx=""{wx}"" cy=""{wy}"" r=""7"" fill=""#f59e0b"" stroke=""#ffffff"" stroke-width=""2"" filter=""url(#shadow)""/>");
            sb.AppendLine($@"  <text x=""{wx}"" y=""{double.Parse(wy, CultureInfo.InvariantCulture) + 16:F1}"" font-family=""sans-serif"" font-size=""8.5"" font-weight=""bold"" fill=""#b45309"" text-anchor=""middle"">Punto Conexión</text>");
        }

        // Rosa de los vientos / Flecha Norte
        sb.AppendLine($@"  <g transform=""translate({width - 45}, 20)"">
            <circle cx=""16"" cy=""16"" r=""14"" fill=""#ffffff"" stroke=""#cbd5e1"" stroke-width=""1.2""/>
            <polygon points=""16,6 20,20 16,17 12,20"" fill=""#0284c7""/>
            <polygon points=""16,26 20,20 16,17 12,20"" fill=""#94a3b8""/>
            <text x=""16"" y=""4"" font-family=""sans-serif"" font-size=""9"" font-weight=""bold"" fill=""#0f172a"" text-anchor=""middle"">N</text>
        </g>");

        // Barra de escala de referencia
        sb.AppendLine($@"  <g transform=""translate(20, {height - 24})"">
            <rect x=""0"" y=""0"" width=""80"" height=""4"" fill=""#0f172a"" rx=""1""/>
            <text x=""0"" y=""14"" font-family=""sans-serif"" font-size=""8.5"" fill=""#64748b"">Croquis Territorial Catastral</text>
        </g>");

        sb.AppendLine("</svg>");
        return sb.ToString();
    }
}
