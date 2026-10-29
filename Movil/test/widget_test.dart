import 'package:flutter_test/flutter_test.dart';
import 'package:movil/modules/mapa/models/secuencia_atencion.dart';
import 'package:movil/modules/auth/models/sesion_usuario.dart';

void main() {
  test('Respeta orden asignado aunque la lista llegue desordenada', () {
    final puntos = [
      {'id': 3, 'orden': 3, 'estado': 'Pendiente'},
      {'id': 1, 'orden': 1, 'estado': 'Observado'},
      {'id': 2, 'orden': 2, 'estado': 'Pendiente'},
    ];
    expect(siguientePunto(puntos)?['id'], 2);
    expect(puntos.first['id'], 3); // No altera la respuesta original.
  });

  test('Al observar el objetivo se avanza sin volver a seleccionarlo', () {
    final puntos = <Map<String, dynamic>>[
      {'id': 1, 'orden': 1, 'estado': 'Pendiente'},
      {'id': 2, 'orden': 2, 'estado': 'Pendiente'},
    ];
    siguientePunto(puntos)!['estado'] = 'Observado';
    expect(siguientePunto(puntos)?['id'], 2);
  });

  test('Todos los estados terminales permiten avanzar', () {
    final puntos = [
      for (final estado in ['Completado', 'Ejecutado', 'Observado', 'Omitido'])
        {'orden': 1, 'estado': estado},
    ];
    expect(puntos.every(puntoAtendido), isTrue);
    expect(siguientePunto(puntos), isNull);
    expect(siguientePunto([]), isNull);
  });

  test('Identidad exige usuario real y conserva roles', () {
    expect(() => SesionUsuario.fromJson({'nombre': 'Sin login'}), throwsFormatException);
    final sesion = SesionUsuario.fromJson({
      'usuario': 'empleado', 'nombre': 'Empleado de prueba', 'roles': ['Cortador'],
    });
    expect(sesion.usuario, 'empleado');
    expect(sesion.roles, ['Cortador']);
  });
}
