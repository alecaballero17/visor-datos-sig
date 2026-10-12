import 'dart:async';
import 'dart:math';
import 'package:geolocator/geolocator.dart';
import '../../../../core/network/api_provider.dart';

class TrackingGpsService {
  static final TrackingGpsService _instance = TrackingGpsService._internal();
  factory TrackingGpsService() => _instance;
  TrackingGpsService._internal();

  Timer? _timerTransmision;
  bool isTransmitting = false;
  bool isSimulacionActiva = false;

  // Estado dinámico del operario autenticado
  String operarioId = '';
  String nombreOperario = '';
  String rol = 'Operario';
  double latitud = -17.78100;
  double longitud = -63.18120;
  double velocidad = 0.0;
  double rumbo = 0.0;
  int bateria = 100;

  // Callbacks para UI
  Function(double lat, double lng, double speed, double heading)? onLocationChanged;

  Future<void> cargarSesionUsuario() async {
    try {
      final res = await ApiProvider().get('/autenticacion/sesion');
      if (res is Map<String, dynamic>) {
        operarioId = res['usuario']?.toString() ?? '';
        nombreOperario = res['nombre']?.toString() ?? operarioId;
        final roles = res['roles'] as List?;
        if (roles != null && roles.isNotEmpty) {
          rol = roles.first.toString();
        }
      }
    } catch (_) {
      if (operarioId.isEmpty) {
        operarioId = 'Operario';
        nombreOperario = 'Operario de Campo';
      }
    }
  }

  void configurarOperario({required String id, required String nombre, required String cargo}) {
    operarioId = id;
    nombreOperario = nombre;
    rol = cargo;
  }

  /// Solicita los permisos de ubicación al usuario para que salte el diálogo nativo
  Future<bool> solicitarPermisosUbicacion() async {
    try {
      // 1. Comprobar si los servicios de GPS están activados en el teléfono
      bool servicioHabilitado = await Geolocator.isLocationServiceEnabled();
      if (!servicioHabilitado) {
        // Solicitar abrir la pantalla de activación de GPS
        await Geolocator.openLocationSettings();
      }

      // 2. Comprobar permisos actuales
      LocationPermission permiso = await Geolocator.checkPermission();
      if (permiso == LocationPermission.denied) {
        // Disparar diálogo nativo de permisos de Android / iOS
        permiso = await Geolocator.requestPermission();
        if (permiso == LocationPermission.denied) {
          return false;
        }
      }

      if (permiso == LocationPermission.deniedForever) {
        // Permiso denegado permanentemente, abrir configuración de la app
        await Geolocator.openAppSettings();
        return false;
      }

      final concedido = permiso == LocationPermission.always || permiso == LocationPermission.whileInUse;
      if (concedido) {
        try {
          final pos = await Geolocator.getCurrentPosition(
            locationSettings: const LocationSettings(
              accuracy: LocationAccuracy.high,
              timeLimit: Duration(seconds: 5),
            ),
          );
          latitud = pos.latitude;
          longitud = pos.longitude;
          velocidad = max(0, pos.speed * 3.6);
          rumbo = pos.heading;
          onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
        } catch (_) {}
      }

      return concedido;
    } catch (_) {
      return false;
    }
  }

  void iniciarTransmision({Duration intervalo = const Duration(seconds: 4)}) {
    if (operarioId.isEmpty) {
      cargarSesionUsuario();
    }

    // Solicitar permisos de inmediato para activar el hardware GPS
    solicitarPermisosUbicacion();

    if (isTransmitting) return;
    isTransmitting = true;

    _timerTransmision = Timer.periodic(intervalo, (_) async {
      await _capturarYEnviarPosicion();
    });

    _capturarYEnviarPosicion();
  }

  void detenerTransmision() {
    _timerTransmision?.cancel();
    _timerTransmision = null;
    isTransmitting = false;
  }

  Future<void> _capturarYEnviarPosicion() async {
    try {
      if (!isSimulacionActiva) {
        // Comprobar o solicitar permiso si aún no se tiene
        var permiso = await Geolocator.checkPermission();
        if (permiso == LocationPermission.denied) {
          permiso = await Geolocator.requestPermission();
        }

        if (permiso == LocationPermission.always || permiso == LocationPermission.whileInUse) {
          final pos = await Geolocator.getCurrentPosition(
            locationSettings: const LocationSettings(
              accuracy: LocationAccuracy.high,
              timeLimit: Duration(seconds: 4),
            ),
          ).catchError((_) => Position(
            latitude: latitud,
            longitude: longitud,
            timestamp: DateTime.now(),
            accuracy: 10,
            altitude: 400,
            altitudeAccuracy: 1,
            heading: rumbo,
            headingAccuracy: 1,
            speed: velocidad / 3.6,
            speedAccuracy: 1,
          ));

          latitud = pos.latitude;
          longitud = pos.longitude;
          velocidad = max(0, pos.speed * 3.6);
          rumbo = pos.heading;
        }
      }

      onLocationChanged?.call(latitud, longitud, velocidad, rumbo);

      // Enviar a la plataforma web vía API
      await ApiProvider().post(
        '/tracking/posicion',
        data: {
          'operarioId': operarioId,
          'nombreOperario': nombreOperario,
          'rol': rol,
          'latitud': latitud,
          'longitud': longitud,
          'velocidad': velocidad,
          'rumbo': rumbo,
          'bateria': bateria,
          'timestamp': DateTime.now().toUtc().toIso8601String(),
          'enLinea': true,
        },
      );
    } catch (e) {
      // Ignorar errores de red transitorios
    }
  }

  /// Simula el avance continuo hacia un punto de destino para pruebas de campo
  void avanzarHacia(double targetLat, double targetLng, {double velocidadKmh = 22.0}) {
    isSimulacionActiva = true;
    velocidad = velocidadKmh;

    // Calcular vector y rumbo
    final dLat = targetLat - latitud;
    final dLng = targetLng - longitud;
    final dist = calcularDistanciaMetros(latitud, longitud, targetLat, targetLng);

    if (dist < 10) {
      latitud = targetLat;
      longitud = targetLng;
      velocidad = 0;
      onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
      _capturarYEnviarPosicion();
      return;
    }

    // Calcular ángulo de rumbo en grados
    rumbo = (atan2(dLng, dLat) * 180 / pi) % 360;
    if (rumbo < 0) rumbo += 360;

    // Paso de avance proporcional a velocidad (~6 metros por paso)
    final step = min(0.00008, dist * 0.000001 + 0.00004);
    latitud += (dLat / (dist + 0.0001)) * step * 100;
    longitud += (dLng / (dist + 0.0001)) * step * 100;

    onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
    _capturarYEnviarPosicion();
  }

  /// Calcula distancia en metros usando la fórmula de Haversine
  static double calcularDistanciaMetros(double lat1, double lon1, double lat2, double lon2) {
    const r = 6371000.0; // Radio de la Tierra en metros
    final dLat = (lat2 - lat1) * pi / 180.0;
    final dLon = (lon2 - lon1) * pi / 180.0;
    final a = sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1 * pi / 180.0) * cos(lat2 * pi / 180.0) *
        sin(dLon / 2) * sin(dLon / 2);
    final c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return r * c;
  }

  /// Formatea la distancia a texto legible: "150 m" o "1.4 km"
  static String formatearDistancia(double metros) {
    if (metros < 1000) {
      return '${metros.round()} m';
    } else {
      return '${(metros / 1000).toStringAsFixed(1)} km';
    }
  }

  /// Calcula tiempo estimado de llegada a pie o en moto
  static String formatearTiempoEstimado(double metros, {double velocidadPromedioKmh = 20.0}) {
    if (metros <= 0) return 'Llegada';
    final horas = (metros / 1000.0) / velocidadPromedioKmh;
    final minutos = (horas * 60).round();
    if (minutos <= 1) return '< 1 min';
    return '$minutos min';
  }
}
