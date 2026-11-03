import 'dart:convert';
import 'package:latlong2/latlong.dart';

/// Conserva los vértices y su orden del GeoJSON calculado por el servidor.
/// Una geometría inválida se descarta entera para no unir tramos ficticios.
List<LatLng> leerRecorridoAsignado(String? geoJson) {
  if (geoJson == null || geoJson.trim().isEmpty) return const [];
  try {
    final contenido = jsonDecode(geoJson);
    if (contenido is! Map) return const [];
    final geometria = contenido['type'] == 'Feature'
        ? contenido['geometry']
        : contenido;
    if (geometria is! Map || geometria['type'] != 'LineString') {
      return const [];
    }
    final coordenadas = geometria['coordinates'];
    if (coordenadas is! List || coordenadas.length < 2) return const [];
    final puntos = <LatLng>[];
    for (final coordenada in coordenadas) {
      if (coordenada is! List || coordenada.length < 2) return const [];
      final longitud = coordenada[0];
      final latitud = coordenada[1];
      if (longitud is! num ||
          latitud is! num ||
          !longitud.isFinite ||
          !latitud.isFinite ||
          longitud.abs() > 180 ||
          latitud.abs() > 90) {
        return const [];
      }
      puntos.add(LatLng(latitud.toDouble(), longitud.toDouble()));
    }
    return List.unmodifiable(puntos);
  } on FormatException {
    return const [];
  }
}
