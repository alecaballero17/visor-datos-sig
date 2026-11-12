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
        configurarOperario(
          id: sesion.usuario,
          nombre: sesion.nombre,
          cargo: sesion.roles.join(', '),
        );
      }
    });
  }

  Timer? _timerTransmision;
  bool _capturando = false;
  int _generacion = 0;
  bool _enPrimerPlano = true;
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
  Function(double lat, double lng, double speed, double heading)?
  onLocationChanged;

  Future<void> cargarSesionUsuario() async {
    final generacion = _generacion;
    final res = await ApiProvider().get('/autenticacion/sesion');
    if (generacion != _generacion) {
      throw Exception('La sesión cambió durante la consulta.');
    }
    final sesion = SesionUsuario.fromJson(Map<String, dynamic>.from(res));
    SesionUsuario.actual.value = sesion;
    configurarOperario(
      id: sesion.usuario,
      nombre: sesion.nombre,
      cargo: sesion.roles.join(', '),
    );
  }

  void configurarOperario({
    required String id,
    required String nombre,
    required String cargo,
  }) {
    if (operarioId.isNotEmpty && operarioId != id) limpiarSesion();
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

  Future<Position> capturarPosicionFresca({
    bool solicitarPermiso = true,
  }) async {
    if (!_enPrimerPlano) {
      throw Exception('Regrese a la aplicación para capturar GPS.');
    }
    if (isSimulacionActiva) {
      throw Exception(
        'Modo de ensayo: no permite registrar atención ni transmitir GPS. Salga y vuelva a abrir la ruta para usar GPS real.',
      );
    }
    final generacion = _generacion;
    if (!await Geolocator.isLocationServiceEnabled()) {
      throw Exception('GPS apagado. Active la ubicación y reintente.');
    }
    var permiso = await Geolocator.checkPermission();
    if (permiso == LocationPermission.denied && solicitarPermiso) {
      permiso = await Geolocator.requestPermission();
    }
    if (permiso == LocationPermission.deniedForever) {
      throw Exception(
        'Permiso de ubicación bloqueado. Habilítelo en Ajustes de la aplicación.',
      );
    }
    if (permiso != LocationPermission.always &&
        permiso != LocationPermission.whileInUse) {
      throw Exception('Permiso de ubicación denegado. Habilítelo y reintente.');
    }
    final pos = await Geolocator.getCurrentPosition(
      locationSettings: const LocationSettings(
        accuracy: LocationAccuracy.high,
        timeLimit: Duration(seconds: 15),
      ),
    );
    if (generacion != _generacion || isSimulacionActiva || !_enPrimerPlano) {
      throw Exception('La sesión o el modo de ubicación cambió. Reintente.');
    }
    if (!posicionVigente(pos)) {
      throw Exception(
        'No se obtuvo una ubicación GPS válida y reciente. Reintente.',
      );
    }
    ultimaPosicion = pos;
    ultimoError = null;
    latitud = pos.latitude;
    longitud = pos.longitude;
    velocidad = pos.speed.isFinite ? max(0, pos.speed * 3.6) : 0;
    rumbo = pos.heading.isFinite && pos.heading >= 0 ? pos.heading % 360 : 0;
    onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
    return pos;
  }

  Future<bool> solicitarPermisosUbicacion() async {
    final generacion = _generacion;
    try {
      await capturarPosicionFresca();
      return true;
    } catch (e) {
      if (generacion != _generacion) return false;
      ultimoError = e.toString().replaceFirst('Exception: ', '');
      return false;
    }
  }

  void iniciarTransmision({Duration intervalo = const Duration(seconds: 4)}) {
    if (isTransmitting ||
        !_enPrimerPlano ||
        SesionUsuario.actual.value == null ||
        isSimulacionActiva) {
      return;
    }
    isTransmitting = true;
    _timerTransmision = Timer.periodic(
      intervalo,
      (_) => _capturarYEnviarPosicion(),
    );
    _capturarYEnviarPosicion();
  }

  void detenerTransmision() {
    _generacion++;
    _timerTransmision?.cancel();
    _timerTransmision = null;
    isTransmitting = false;
  }

  void actualizarPrimerPlano(bool activo) {
    _enPrimerPlano = activo;
    if (activo) {
      iniciarTransmision();
    } else {
      detenerTransmision();
    }
  }

  Future<void> _capturarYEnviarPosicion() async {
    if (_capturando || !isTransmitting || isSimulacionActiva) return;
    _capturando = true;
    final generacion = _generacion;
    try {
      if (operarioId.isEmpty) await cargarSesionUsuario();
      final pos = await capturarPosicionFresca(solicitarPermiso: false);
      if (!isTransmitting || generacion != _generacion || isSimulacionActiva) {
        return;
      }
      await ApiProvider().post(
        '/tracking/posicion',
        data: {
          'operarioId': operarioId,
          'nombreOperario': nombreOperario,
          'rol': rol,
          'latitud': pos.latitude,
          'longitud': pos.longitude,
          'velocidad': velocidad,
          'rumbo': rumbo,
          'timestamp': pos.timestamp.toUtc().toIso8601String(),
          'enLinea': true,
        },
      );
    } catch (e) {
      if (generacion != _generacion) return;
      ultimoError = e.toString().replaceFirst('Exception: ', '');
      onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
    } finally {
      _capturando = false;
    }
  }

  /// Simula el avance continuo hacia un punto de destino para pruebas de campo
  void avanzarHacia(
    double targetLat,
    double targetLng, {
    double velocidadKmh = 22.0,
  }) {
    if (!isSimulacionActiva) detenerTransmision();
    isSimulacionActiva = true;
    velocidad = velocidadKmh;

    // Calcular vector y rumbo
    final dLat = targetLat - latitud;
    final dLng = targetLng - longitud;
    final dist = calcularDistanciaMetros(
      latitud,
      longitud,
      targetLat,
      targetLng,
    );

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

    // Un paso representa 600 ms; no sobrepasar el destino.
    final fraccion = min(1.0, max(0, velocidadKmh) / 3.6 * 0.6 / dist);
    latitud += dLat * fraccion;
    longitud += dLng * fraccion;

    onLocationChanged?.call(latitud, longitud, velocidad, rumbo);
  }

  static bool posicionVigente(Position? posicion, {DateTime? ahora}) {
    if (posicion == null) return false;
    final edad = (ahora ?? DateTime.now()).difference(posicion.timestamp);
    return !edad.isNegative &&
        edad < const Duration(seconds: 10) &&
        posicion.latitude.isFinite &&
        posicion.longitude.isFinite &&
        posicion.latitude.abs() <= 90 &&
        posicion.longitude.abs() <= 180 &&
        posicion.accuracy.isFinite &&
        posicion.accuracy >= 0;
  }

  Future<bool> volverAGpsReal() async {
    detenerTransmision();
    isSimulacionActiva = false;
    ultimaPosicion = null;
    velocidad = 0;
    final exito = await solicitarPermisosUbicacion();
    iniciarTransmision();
    return exito;
  }

  /// Calcula distancia en metros usando la fórmula de Haversine
  static double calcularDistanciaMetros(
    double lat1,
    double lon1,
    double lat2,
    double lon2,
  ) {
    const r = 6371000.0; // Radio de la Tierra en metros
    final dLat = (lat2 - lat1) * pi / 180.0;
    final dLon = (lon2 - lon1) * pi / 180.0;
    final a =
        sin(dLat / 2) * sin(dLat / 2) +
        cos(lat1 * pi / 180.0) *
            cos(lat2 * pi / 180.0) *
            sin(dLon / 2) *
            sin(dLon / 2);
    final c = 2 * atan2(sqrt(a.clamp(0.0, 1.0)), sqrt(1 - a.clamp(0.0, 1.0)));
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
  static String formatearTiempoEstimado(
    double metros, {
    double velocidadPromedioKmh = 20.0,
  }) {
    if (metros <= 0) return 'Llegada';
    final horas = (metros / 1000.0) / velocidadPromedioKmh;
    final minutos = (horas * 60).round();
    if (minutos <= 1) return '< 1 min';
    return '$minutos min';
  }
}
