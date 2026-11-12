import 'package:flutter_test/flutter_test.dart';
import 'package:movil/modules/agua_potable/models/agua_potable_model.dart';

/// Respuestas con la forma exacta de AguaPotableController (backend):
/// el titular y los datos del medidor vienen dentro de `registros`.
void main() {
  group('FichaAgua: GET /agua-potable/codigos/{id}', () {
    final json = {
      'tieneAgua': true,
      'criterioDisponibilidad': 'Con código fijo: agua potable.',
      'fuente': 'Exp_CodigoFijo_4326.shp',
      'registros': [
        {
          'idCodigo': 12,
          'codigoFijo': 3456,
          'codigoSig': 'A-12',
          'nombreRegistrado': '  Juan Perez  ',
          'idLote': 8,
          'numeroLote': '5',
          'uv': '12',
          'manzana': '34',
          'longitud': -60.96,
          'latitud': -16.40,
          'estadoVerificado': true,
          'estadoServicio': 3,
        }
      ],
      'datosNoDisponibles': ['Número de medidor', 'Lecturas'],
    };

    test('el titular se lee de registros[].nombreRegistrado', () {
      final f = FichaAgua.fromJson(json);
      expect(f.titularResumen, 'Juan Perez');
      expect(f.principal!.nombreRegistrado, 'Juan Perez');
    });

    test('codigos numericos y datos del lote', () {
      final r = FichaAgua.fromJson(json).principal!;
      expect(r.idCodigo, 12);
      expect(r.codigoFijo, '3456');
      expect(r.numeroLote, '5');
      expect(r.uv, '12');
      expect(r.manzana, '34');
      expect(r.latitud, -16.40);
      expect(r.longitud, -60.96);
    });

    test('estado verificado se traduce con el catalogo del backend', () {
      final r = FichaAgua.fromJson(json).principal!;
      expect(r.estadoTexto, 'Cortado');
      expect(r.conServicio, isFalse);
    });

    test('datos no disponibles se exponen tal cual', () {
      expect(FichaAgua.fromJson(json).datosNoDisponibles, contains('Lecturas'));
    });
  });

  group('FichaAgua: GET /agua-potable/lotes/{id}', () {
    test('lote con varios medidores resume los titulares', () {
      final f = FichaAgua.fromJson({
        'tieneAgua': true,
        'registros': [
          {'idCodigo': 1, 'nombreRegistrado': 'Ana', 'estadoVerificado': false, 'estadoServicio': null},
          {'idCodigo': 2, 'nombreRegistrado': 'Luis', 'estadoVerificado': true, 'estadoServicio': 1},
          {'idCodigo': 3, 'nombreRegistrado': 'Ana', 'estadoVerificado': true, 'estadoServicio': 1},
        ],
      });
      expect(f.titulares, ['Ana', 'Luis']);
      expect(f.titularResumen, 'Ana y 1 más');
      expect(f.principal!.estadoTexto, 'Estado sin verificar');
    });

    test('lote sin codigo fijo: sin agua y sin titular', () {
      final f = FichaAgua.fromJson({'tieneAgua': false, 'registros': []});
      expect(f.tieneAgua, isFalse);
      expect(f.principal, isNull);
      expect(f.titularResumen, isNull);
    });

    test('titular vacio o ausente no se muestra como nombre', () {
      final f = FichaAgua.fromJson({
        'tieneAgua': true,
        'registros': [
          {'idCodigo': 1, 'nombreRegistrado': '   '},
          {'idCodigo': 2},
        ],
      });
      expect(f.titularResumen, isNull);
    });
  });
}
