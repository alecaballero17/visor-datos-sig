import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:movil/modules/mapa/models/recorrido_asignado.dart';

void main() {
  test(
    'Respeta los vértices de calle y convierte longitud/latitud a LatLng',
    () {
      final geometria = {
        'type': 'LineString',
        'coordinates': [
          [-60.96, -16.397],
          [-60.959, -16.397],
          [-60.959, -16.396],
          [-60.96, -16.397],
        ],
      };
      for (final geoJson in [
        geometria,
        {'type': 'Feature', 'geometry': geometria},
      ]) {
        final puntos = leerRecorridoAsignado(jsonEncode(geoJson));
        expect(
          puntos.map((p) => [p.longitude, p.latitude]).toList(),
          geometria['coordinates'],
        );
        expect(puntos.length, 4); // Conserva esquina y retorno, sin atajos.
      }
    },
  );

  test('Geometría ausente o incompatible no inventa un recorrido', () {
    for (final valor in [
      null,
      '',
      '{',
      'null',
      '[]',
      '{}',
      '{"type":"Feature","geometry":null}',
      '{"type":"Point","coordinates":[-60.96,-16.397]}',
      '{"type":"LineString","coordinates":[]}',
      '{"type":"LineString","coordinates":[[-60.96,-16.397]]}',
    ]) {
      expect(leerRecorridoAsignado(valor), isEmpty, reason: '$valor');
    }
  });

  test(
    'Un vértice inválido descarta todo el trazado, sin unir sus extremos',
    () {
      for (final invalido in [
        [181, -16],
        [-60, 91],
        ['-60', -16],
        [null, -16],
        [-60],
        null,
      ]) {
        final geoJson = jsonEncode({
          'type': 'LineString',
          'coordinates': [
            [-60.96, -16.397],
            invalido,
            [-60.95, -16.39],
          ],
        });
        expect(leerRecorridoAsignado(geoJson), isEmpty);
      }
      expect(
        leerRecorridoAsignado(
          '{"type":"LineString","coordinates":[[1e999,0],[0,0]]}',
        ),
        isEmpty,
      );
    },
  );
}
