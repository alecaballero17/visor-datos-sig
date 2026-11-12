import 'package:flutter_test/flutter_test.dart';
import 'package:geolocator/geolocator.dart';
import 'package:movil/modules/mapa/models/ruta_trabajo.dart';
import 'package:movil/modules/mapa/services/navegacion_externa_service.dart';
import 'package:movil/modules/mapa/services/tracking_gps_service.dart';

Map<String, dynamic> parada(int id, int orden, {String estado = 'Pendiente'}) =>
    {
      'id': id,
      'orden': orden,
      'estado': estado,
      'latitud': -16.397,
      'longitud': -60.96,
    };
RutaTrabajo ruta(
  List<Map<String, dynamic>> puntos, {
  String estado = 'Pendiente',
}) => RutaTrabajo.fromJson({
  'id': 1,
  'estado': estado,
  'operarioId': 'ana',
  'puntos': puntos,
});

void main() {
  test(
    'El modelo ordena por servidor, avanza tras observados y conserva el JSON',
    () {
      final actual = ruta([parada(2, 2), parada(1, 1, estado: ' Observado ')]);
      expect(actual.puntos.map((p) => p.id), [1, 2]);
      expect(actual.atendidos, 1);
      expect(actual.siguiente!.id, 2);
      expect(RutaTrabajo.fromJson(actual.toJson()).siguiente!.id, 2);
      expect(actual.perteneceA('ANA'), isTrue);
      expect(actual.perteneceA('otro'), isFalse);
    },
  );

  test('No se atienden rutas vacías, canceladas o completadas', () {
    expect(ruta([]).puedeAtender, isFalse);
    for (final estado in ['Cancelada', 'Completada']) {
      expect(ruta([parada(1, 1)], estado: estado).puedeAtender, isFalse);
    }
    expect(ruta([parada(1, 1, estado: 'Omitido')]).siguiente, isNull);
  });

  test('Una secuencia duplicada o sin orden produce error visible', () {
    expect(() => ruta([parada(1, 1), parada(2, 1)]), throwsFormatException);
    expect(() => ruta([parada(1, 1), parada(1, 2)]), throwsFormatException);
    expect(() => ruta([parada(1, 0)]), throwsFormatException);
  });

  test('Coordenadas ausentes o inválidas nunca se convierten en cero', () {
    for (final valor in [null, double.nan, 91]) {
      final punto = PuntoTrabajo.fromJson({...parada(1, 1), 'latitud': valor});
      expect(punto.tieneCoordenadas, isFalse);
    }
  });

  test(
    'Maps/Waze conservan el destino y usan navegador si falla la app',
    () async {
      final intentos = <Uri>[];
      final servicio = NavegacionExternaService(
        abrir: (uri) async {
          intentos.add(uri);
          if (uri.scheme != 'https') throw Exception('Aplicación ausente');
          return true;
        },
      );
      await servicio.navegar(-16.397, -60.96, app: AplicacionNavegacion.waze);
      expect(intentos.first.scheme, 'waze');
      expect(intentos.last.queryParameters['destination'], '-16.397,-60.96');
      expect(intentos.last.queryParameters.containsKey('origin'), isFalse);
      expect(
        NavegacionExternaService.enlaces(
          -16,
          -60,
          AplicacionNavegacion.googleMaps,
        ).first.scheme,
        'google.navigation',
      );
    },
  );

  test(
    'Fallo total e invalidación del destino se comunican al usuario',
    () async {
      var intentos = 0;
      final servicio = NavegacionExternaService(
        abrir: (_) async {
          intentos++;
          return false;
        },
      );
      await expectLater(servicio.navegar(91, 0), throwsArgumentError);
      expect(intentos, 0);
      await expectLater(servicio.navegar(-16, -60), throwsException);
      expect(intentos, 2);
    },
  );

  test('Una apertura nativa exitosa no abre además el navegador', () async {
    var intentos = 0;
    await NavegacionExternaService(
      abrir: (_) async {
        intentos++;
        return true;
      },
    ).navegar(-16, -60);
    expect(intentos, 1);
  });

  final ahora = DateTime.utc(2026, 10, 29, 12);
  Position posicion(
    Duration edad, {
    double latitud = -16.397,
    double precision = 5,
  }) => Position(
    latitude: latitud,
    longitude: -60.96,
    timestamp: ahora.subtract(edad),
    accuracy: precision,
    altitude: 0,
    altitudeAccuracy: 0,
    heading: 0,
    headingAccuracy: 0,
    speed: 0,
    speedAccuracy: 0,
  );
  test(
    'GPS exige menos de 10 s, hora no futura y coordenadas/precisión válidas',
    () {
      expect(TrackingGpsService.posicionVigente(null, ahora: ahora), isFalse);
      expect(
        TrackingGpsService.posicionVigente(
          posicion(const Duration(seconds: 9)),
          ahora: ahora,
        ),
        isTrue,
      );
      for (final p in [
        posicion(const Duration(seconds: 10)),
        posicion(const Duration(seconds: -1)),
        posicion(Duration.zero, latitud: 91),
        posicion(Duration.zero, precision: -1),
      ]) {
        expect(TrackingGpsService.posicionVigente(p, ahora: ahora), isFalse);
      }
    },
  );

  test('Haversine distingue 29/31 m y funciona con puntos antípodas', () {
    const metrosPorGrado = 111194.9266;
    expect(
      TrackingGpsService.calcularDistanciaMetros(0, 0, 29 / metrosPorGrado, 0),
      lessThan(30),
    );
    expect(
      TrackingGpsService.calcularDistanciaMetros(0, 0, 31 / metrosPorGrado, 0),
      greaterThan(30),
    );
    expect(
      TrackingGpsService.calcularDistanciaMetros(0, 0, 0, 180).isFinite,
      isTrue,
    );
  });

  test('Segundo plano y ausencia de sesión impiden iniciar transmisión', () {
    final tracking = TrackingGpsService();
    tracking.limpiarSesion();
    tracking.actualizarPrimerPlano(false);
    tracking.iniciarTransmision();
    expect(tracking.isTransmitting, isFalse);
    tracking.actualizarPrimerPlano(true);
    expect(tracking.isTransmitting, isFalse);
  });

  test('Cambiar empleado elimina GPS y ensayo de la identidad anterior', () {
    final tracking = TrackingGpsService();
    tracking.configurarOperario(id: 'ana', nombre: 'Ana', cargo: 'Cortador');
    tracking.ultimaPosicion = posicion(Duration.zero);
    tracking.isSimulacionActiva = true;
    tracking.configurarOperario(id: 'luis', nombre: 'Luis', cargo: 'Reconector');
    expect(tracking.operarioId, 'luis');
    expect(tracking.ultimaPosicion, isNull);
    expect(tracking.isSimulacionActiva, isFalse);
    expect(tracking.isTransmitting, isFalse);
    tracking.limpiarSesion();
  });
}
