import 'dart:async';
import 'dart:math';
import 'package:geolocator/geolocator.dart';
import '../../../core/network/api_provider.dart';
import '../../auth/models/sesion_usuario.dart';

class TrackingGpsService {
  static final TrackingGpsService _instance = TrackingGpsService._internal();
  factory TrackingGpsService() => _instance;
  TrackingGpsService._internal() {
    SesionUsuario.actual.addListener(() {
      final sesion = SesionUsuario.actual.value;
      if (sesion == null) {
        limpiarSesion();
      } else {
        configurarOperario(id: sesion.usuario, nombre: sesion.nombre, cargo: sesion.roles.join(', '));
      }
    });
  }

  Timer? _timerTransmision;
  bool _capturando = false;
  int _generacion = 0;
  bool isTransmitting = false;
  bool isSimulacionActiva = false;
  String operarioId = '';
  String nombreOperario = '';
  String rol = '';
  // Centro del mapa, nunca se transmite como una lectura GPS.
  double latitud = -16.397;
  double longitud = -60.960;
  double velocidad = 0;
  double rumbo = 0;
  Position? ultimaPosicion;
  String? ultimoError;
  Function(double lat, double lng, double speed, double heading)? onLocationChanged;

  Future<void> cargarSesionUsuario() async {
    final generacion = _generacion;
    final res = await ApiProvider().get('/autenticacion/sesion');
    if (generacion != _generacion) throw Exception('La sesión cambió durante la consulta.');
    final sesion = SesionUsuario.fromJson(Map<String, dynamic>.from(res));
    SesionUsuario.actual.value = sesion;
    configurarOperario(id: sesion.usuario, nombre: sesion.nombre,
      cargo: sesion.roles.join(', '));
  }

  void configurarOperario({required String id, required String nombre, required String cargo}) {
    operarioId = id;
    nombreOperario = nombre;
    rol = cargo;
  }

  void limpiarSesion() {
    detenerTransmision();
    operarioId = '';
    nombreOperario = '';
    rol = '';
    ultimaPosicion = null;
    ultimoError = null;
    isSimulacionActiva = false;
    latitud = -16.397;
    longitud = -60.960;
    velocidad = 0;
    rumbo = 0;
    onLocationChanged = null;
  }

  Future<Position> capturarPosicionFresca() async {
    if (isSimulacionActiva) {
      throw Exception('Modo de ensayo: no permite registrar atención ni transmitir GPS. Salga y vuelva a abrir la ruta para usar GPS real.');
    }
    final generacion = _generacion;
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw Exception('GPS apagado. Active la ubicación y reintente.');
    }
    var permiso = await Geolocator.checkPermission();
    if (permiso == LocationPermission.denied) permiso = await Geolocator.requestPermission();
    if (permiso == LocationPermission.deniedForever) {
      throw Exception('Permiso de ubicación bloqueado. Habilítelo en Ajustes de la aplicación.');
    }
    if (permiso != LocationPermission.always && permiso != LocationPermission.whileInUse) {
      throw Exception('Permiso de ubicación denegado. Habilítelo y reintente.');
    }
    final pos = await Geolocator.getCurrentPosition(locationSettings: const LocationSettings(
      accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 15)));
    if (generacion != _generacion || isSimulacionActiva) {
      throw Exception('La sesión o el modo de ubicación cambió. Reintente.');
    }
    final edad = DateTime.now().difference(pos.timestamp);
    if (edad.isNegative || edad >= const Duration(seconds: 10) ||
        !pos.latitude.isFinite || !pos.longitude.isFinite ||
        pos.latitude.abs() > 90 || pos.longitude.abs() > 180 ||
        !pos.accuracy.isFinite || pos.accuracy < 0) {
      throw Exception('No se obtuvo una ubicación GPS válida y reciente. Reintente.');
    }
    ultimaPosicion = pos;
    ultimoError = null;
    latitud = pos.latitude;
    longitud = pos.longitude;
    velocidad = max(0, pos.speed * 3.6);
    rumbo = pos.heading;
    onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
    return pos;
  }

  Future<bool> solicitarPermisosUbicacion() async {
    try {
      await capturarPosicionFresca();
      return true;
    } catch (e) {
      ultimoError = e.toString().replaceFirst('Exception: ', '');
      return false;
    }
  }

  void iniciarTransmision({Duration intervalo = const Duration(seconds: 4)}) {
    if (isTransmitting) return;
    isTransmitting = true;
    _timerTransmision = Timer.periodic(intervalo, (_) => _capturarYEnviarPosicion());
    _capturarYEnviarPosicion();
  }

  void detenerTransmision() {
    _generacion++;
    _timerTransmision?.cancel();
    _timerTransmision = null;
    isTransmitting = false;
  }

  Future<void> _capturarYEnviarPosicion() async {
    if (_capturando || !isTransmitting || isSimulacionActiva) return;
    _capturando = true;
    final generacion = _generacion;
    try {
      if (operarioId.isEmpty) await cargarSesionUsuario();
      final pos = await capturarPosicionFresca();
      if (!isTransmitting || generacion != _generacion || isSimulacionActiva) return;
      await ApiProvider().post('/tracking/posicion', data: {
        'operarioId': operarioId, 'nombreOperario': nombreOperario, 'rol': rol,
        'latitud': pos.latitude, 'longitud': pos.longitude,
        'velocidad': velocidad, 'rumbo': rumbo,
        'timestamp': pos.timestamp.toUtc().toIso8601String(), 'enLinea': true,
      });
    } catch (e) {
      ultimoError = e.toString().replaceFirst('Exception: ', '');
      onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
    } finally {
      _capturando = false;
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
