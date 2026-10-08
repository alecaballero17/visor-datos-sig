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
                <rect width=""{width}"" height=""{height}"" fill=""#f8f9fa"" rx=""6"" stroke=""#dadce0"" stroke-width=""1""/>
                <text x=""{width/2}"" y=""{height/2}"" font-family=""sans-serif"" font-size=""12"" fill=""#5f6368"" text-anchor=""middle"">
                    Geometría vectorial no disponible
                </text>
            </svg>";
        }

        var env = geom.EnvelopeInternal;
        var padX = env.Width * 0.18;
        var padY = env.Height * 0.18;
        if (padX < 0.00001) padX = 0.0005;
        if (padY < 0.00001) padY = 0.0005;

        var minX = env.MinX - padX;
        var maxX = env.MaxX + padX;
        var minY = env.MinY - padY;
        var maxY = env.MaxY + padY;

        var rangeX = maxX - minX;
        var rangeY = maxY - minY;

        double ToSvgX(double x) => ((x - minX) / rangeX) * (width - 40) + 20;
        double ToSvgY(double y) => height - (((y - minY) / rangeY) * (height - 40) + 20);

        var sb = new StringBuilder();
        sb.AppendLine($@"<svg xmlns=""http://www.w3.org/2000/svg"" viewBox=""0 0 {width} {height}"" width=""100%"" height=""100%"">");
        
        // Marco de mapa estilo Google
        sb.AppendLine($@"  <rect width=""{width}"" height=""{height}"" fill=""#ffffff"" rx=""6"" stroke=""#dadce0"" stroke-width=""1""/>");
        sb.AppendLine(@"  <defs>
            <pattern id=""ggrid"" width=""20"" height=""20"" patternUnits=""userSpaceOnUse"">
                <path d=""M 20 0 L 0 0 0 20"" fill=""none"" stroke=""#f1f3f4"" stroke-width=""0.8""/>
            </pattern>
        </defs>");
        sb.AppendLine($@"  <rect width=""{width}"" height=""{height}"" fill=""url(#ggrid)"" rx=""6""/>");

        // Polígonos
        var polygons = new List<Polygon>();
        if (geom is Polygon p) polygons.Add(p);
        else if (geom is MultiPolygon mp)
        {
            for (int i = 0; i < mp.NumGeometries; i++)
                if (mp.GetGeometryN(i) is Polygon subP) polygons.Add(subP);
        }

        // Colores estilo Google Maps (azul Google #1a73e8)
        var strokeColor = "#1a73e8";
        var fillColor = "rgba(26, 115, 232, 0.14)";

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

                // Vértices discretos
                if (i < coords.Length - 1 && verticeNum <= 8)
                {
                    verticeMarkers.AppendLine($@"  <circle cx=""{sx}"" cy=""{sy}"" r=""3"" fill=""#ffffff"" stroke=""#1a73e8"" stroke-width=""1.5""/>");
                    verticeMarkers.AppendLine($@"  <text x=""{sx}"" y=""{ToSvgY(coords[i].Y) - 5:F1}"" font-family=""sans-serif"" font-size=""7.5"" font-weight=""600"" fill=""#5f6368"" text-anchor=""middle"">V{verticeNum}</text>");
                    verticeNum++;
                }
            }

            sb.AppendLine($@"  <polygon points=""{pointsStr.ToString().Trim()}"" fill=""{fillColor}"" stroke=""{strokeColor}"" stroke-width=""2"" stroke-linejoin=""round""/>");
        }

        sb.Append(verticeMarkers.ToString());

        // Punto de acometida / conexión (Google Red Pin)
        if (waterPoint != null && !waterPoint.IsEmpty)
        {
            var wx = ToSvgX(waterPoint.X).ToString("F1", CultureInfo.InvariantCulture);
            var wy = ToSvgY(waterPoint.Y).ToString("F1", CultureInfo.InvariantCulture);
            sb.AppendLine($@"  <circle cx=""{wx}"" cy=""{wy}"" r=""5"" fill=""#ea4335"" stroke=""#ffffff"" stroke-width=""1.5""/>");
            sb.AppendLine($@"  <text x=""{wx}"" y=""{double.Parse(wy, CultureInfo.InvariantCulture) + 12:F1}"" font-family=""sans-serif"" font-size=""7"" font-weight=""600"" fill=""#202124"" text-anchor=""middle"">Acometida</text>");
        }

        // Flecha Norte sobria
        sb.AppendLine($@"  <g transform=""translate({width - 34}, 14)"">
            <circle cx=""10"" cy=""10"" r=""9"" fill=""#ffffff"" stroke=""#dadce0"" stroke-width=""1""/>
            <polygon points=""10,3 12.5,12 10,10.5 7.5,12"" fill=""#1a73e8""/>
            <polygon points=""10,17 12.5,12 10,10.5 7.5,12"" fill=""#9aa0a6""/>
            <text x=""10"" y=""2"" font-family=""sans-serif"" font-size=""6.5"" font-weight=""bold"" fill=""#5f6368"" text-anchor=""middle"">N</text>
        </g>");

        // Barra de escala sobria estilo Google Maps
        sb.AppendLine($@"  <g transform=""translate(14, {height - 18})"">
            <line x1=""0"" y1=""0"" x2=""50"" y2=""0"" stroke=""#5f6368"" stroke-width=""1.5""/>
            <line x1=""0"" y1=""-3"" x2=""0"" y2=""3"" stroke=""#5f6368"" stroke-width=""1.5""/>
            <line x1=""50"" y1=""-3"" x2=""50"" y2=""3"" stroke=""#5f6368"" stroke-width=""1.5""/>
            <text x=""0"" y=""9"" font-family=""sans-serif"" font-size=""6.5"" fill=""#5f6368"">Croquis de ubicación</text>
        </g>");

        sb.AppendLine("</svg>");
        return sb.ToString();
    }
}
