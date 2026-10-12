import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/mapa_service.dart';

class MapaController {
  final MapaService _mapaService = MapaService();
  
  bool isCargando = false;
  String? errorMensaje;
  
  // Capas disponibles
  List<Polygon> poligonosManzanas = [];
  bool mostrarManzanas = true;

  List<Polygon> poligonosLotes = [];
  bool mostrarLotes = true;

  List<Marker> marcadoresAgua = [];
  bool mostrarAgua = true;

  List<Polyline> lineasVias = [];
  bool mostrarVias = false;

  // Centro de datos SIG urbano de San Ignacio de Velasco
  static const LatLng centroSigSanIgnacio = LatLng(-16.400, -60.960);
  static const String bboxSanIgnacioUrbano = '-60.985,-16.425,-60.935,-16.365';

  Function(Map<String, dynamic>)? onFeatureSelected;

  Future<void> cargarCapasEnVista(
    MapCamera? camera, 
    Function(VoidCallback) actualizar,
    {Function(Map<String, dynamic>)? onFeatureTap}
  ) async {
    if (onFeatureTap != null) onFeatureSelected = onFeatureTap;

    actualizar(() {
      isCargando = true;
      errorMensaje = null;
    });

    try {
      String bbox = bboxSanIgnacioUrbano;
      if (camera != null) {
        final b = camera.visibleBounds;
        // Si la cámara está en el sector de San Ignacio (-61 a -60, -17 a -16), usar su bbox visible
        if (b.west >= -61.5 && b.east <= -60.0 && b.south >= -17.0 && b.north <= -15.8) {
          bbox = '${b.west},${b.south},${b.east},${b.north}';
        }
      }

      final List<Polygon> nuevosPoligonosMza = [];
      final List<Polygon> nuevosPoligonosLotes = [];
      final List<Marker> nuevosMarcadoresAgua = [];

      // 1. Cargar Manzanas si están activas
      if (mostrarManzanas) {
        final responseMza = await _mapaService.obtenerGeoJsonCapa('manzanas', bbox);
        if (responseMza is Map<String, dynamic> && responseMza['features'] is List) {
          final features = responseMza['features'] as List;
          nuevosPoligonosMza.addAll(_parsearPoligonos(
            features, 
            fillColor: const Color(0xFFDC2626).withValues(alpha: 0.08),
            borderColor: const Color(0xFFDC2626).withValues(alpha: 0.7),
            borderWidth: 2.0,
          ));
        }
      }

      // 2. Cargar Lotes si están activos
      if (mostrarLotes) {
        final responseLotes = await _mapaService.obtenerGeoJsonCapa('lotes', bbox);
        if (responseLotes is Map<String, dynamic> && responseLotes['features'] is List) {
          final features = responseLotes['features'] as List;
          nuevosPoligonosLotes.addAll(_parsearPoligonos(
            features, 
            fillColor: const Color(0xFF0284C7).withValues(alpha: 0.08),
            borderColor: const Color(0xFF0284C7).withValues(alpha: 0.6),
            borderWidth: 1.2,
          ));
        }
      }

      // 3. Cargar Códigos Fijos / Agua Potable si están activos
      if (mostrarAgua) {
        final responseAgua = await _mapaService.obtenerGeoJsonCapa('codigosfijos', bbox);
        if (responseAgua is Map<String, dynamic> && responseAgua['features'] is List) {
          final features = responseAgua['features'] as List;
          nuevosMarcadoresAgua.addAll(_parsearMarcadoresAgua(features));
        }
      }

      actualizar(() {
        isCargando = false;
        poligonosManzanas = nuevosPoligonosMza;
        poligonosLotes = nuevosPoligonosLotes;
        marcadoresAgua = nuevosMarcadoresAgua;
      });
    } catch (e) {
      actualizar(() {
        isCargando = false;
        errorMensaje = 'Error al conectar con la cartografía: ${e.toString().replaceAll("Exception: ", "")}';
      });
    }
  }

  List<Polygon> _parsearPoligonos(
    List features, {
    required Color fillColor,
    required Color borderColor,
    required double borderWidth,
  }) {
    final List<Polygon> lista = [];

    for (var f in features) {
      if (f == null || f['geometry'] == null) continue;
      final geom = f['geometry'];
      final type = geom['type']?.toString();
      final coords = geom['coordinates'];

      if (type == 'Polygon' && coords is List && coords.isNotEmpty) {
        final ring = coords[0] as List;
        final points = ring.map((pt) => LatLng((pt[1] as num).toDouble(), (pt[0] as num).toDouble())).toList();
        if (points.isNotEmpty) {
          lista.add(Polygon(
            points: points,
            color: fillColor,
            borderColor: borderColor,
            borderStrokeWidth: borderWidth,
          ));
        }
      } else if (type == 'MultiPolygon' && coords is List) {
        for (var poly in coords) {
          if (poly is List && poly.isNotEmpty) {
            final ring = poly[0] as List;
            final points = ring.map((pt) => LatLng((pt[1] as num).toDouble(), (pt[0] as num).toDouble())).toList();
            if (points.isNotEmpty) {
              lista.add(Polygon(
                points: points,
                color: fillColor,
                borderColor: borderColor,
                borderStrokeWidth: borderWidth,
              ));
            }
          }
        }
      }
    }

    return lista;
  }

  List<Marker> _parsearMarcadoresAgua(List features) {
    final List<Marker> markers = [];

    for (var f in features) {
      if (f == null) continue;
      final geom = f['geometry'];
      final props = f['properties'] as Map<String, dynamic>? ?? {};

      double? lat, lng;
      if (geom != null && geom['type'] == 'Point' && geom['coordinates'] is List) {
        final c = geom['coordinates'] as List;
        lng = (c[0] as num).toDouble();
        lat = (c[1] as num).toDouble();
      } else if (props['Latitud'] != null && props['Longitud'] != null) {
        lat = (props['Latitud'] as num).toDouble();
        lng = (props['Longitud'] as num).toDouble();
      }

      if (lat != null && lng != null) {
        final tieneAgua = props['TieneAgua'] == true || props['Estado'] == 1;

        markers.add(Marker(
          point: LatLng(lat, lng),
          width: 30,
          height: 30,
          child: GestureDetector(
            onTap: () {
              // Notificar al visor de datos
              onFeatureSelected?.call(f as Map<String, dynamic>);
            },
            child: Container(
              decoration: BoxDecoration(
                color: tieneAgua ? const Color(0xFF1A73E8) : const Color(0xFFD93025),
                shape: BoxShape.circle,
                border: Border.all(color: Colors.white, width: 2),
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.3),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  )
                ],
              ),
              child: Icon(
                tieneAgua ? Icons.water_drop : Icons.water_drop_outlined,
                color: Colors.white,
                size: 15,
              ),
            ),
          ),
        ));
      }
    }

    return markers;
  }
}
