import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../services/mapa_service.dart';

class MapaController {
  final MapaService _mapaService = MapaService();
  
  bool isCargando = false;
  String? errorMensaje;
  
  List<Polygon> poligonosManzanas = [];
  bool mostrarManzanas = true;

  List<Polygon> poligonosLotes = [];
  bool mostrarLotes = false;

  Future<void> cargarManzanasEnVista(MapCamera camera, Function(VoidCallback) actualizar) async {
    actualizar(() {
      isCargando = true;
      errorMensaje = null;
    });

    try {
      // Calculamos el bounding box actual basado en la cámara
      final bounds = camera.visibleBounds;
      final bbox = '${bounds.west},${bounds.south},${bounds.east},${bounds.north}';
      
      // Consumimos el API real
      final response = await _mapaService.obtenerGeoJsonCapa('manzanas', bbox);
      
      final features = response['features'] as List;
      final List<Polygon> nuevosPoligonos = [];

      for (var feature in features) {
        if (feature['geometry'] != null && feature['geometry']['type'] == 'Polygon') {
          final coordinates = feature['geometry']['coordinates'][0] as List;
          final points = coordinates.map((coord) => LatLng(coord[1], coord[0])).toList();
          
          nuevosPoligonos.add(Polygon(
            points: points,
            color: Colors.redAccent.withOpacity(0.3),
            borderColor: Colors.redAccent,
            borderStrokeWidth: 2,
          ));
        }
      }

      // Cargar Lotes si están activados
      if (mostrarLotes) {
        final responseLotes = await _mapaService.obtenerGeoJsonCapa('lotes', bbox);
        final featuresLotes = responseLotes['features'] as List;
        final List<Polygon> nuevosLotes = [];
        for (var feature in featuresLotes) {
          if (feature['geometry'] != null && feature['geometry']['type'] == 'Polygon') {
            final coordinates = feature['geometry']['coordinates'][0] as List;
            final points = coordinates.map((coord) => LatLng(coord[1], coord[0])).toList();
            nuevosLotes.add(Polygon(
              points: points,
              color: Colors.blueAccent.withOpacity(0.3),
              borderColor: Colors.blueAccent,
              borderStrokeWidth: 1.5,
            ));
          }
        }
        poligonosLotes = nuevosLotes;
      }

      actualizar(() {
        isCargando = false;
        poligonosManzanas = nuevosPoligonos;
      });
    } catch (e) {
      actualizar(() {
        isCargando = false;
        errorMensaje = 'Error al cargar capas: \${e.toString()}';
      });
    }
  }
}
