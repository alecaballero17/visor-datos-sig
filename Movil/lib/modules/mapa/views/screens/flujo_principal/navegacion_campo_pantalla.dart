import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';
import '../../../models/ruta_trabajo.dart';
import '../../../services/tracking_gps_service.dart';
import '../../../services/rutas_trabajo_service.dart';
import '../../../services/navegacion_externa_service.dart';
import '../../../../auth/models/sesion_usuario.dart';
import '../../widgets/formulario_cierre_orden_modal.dart';

class NavegacionCampoPantalla extends StatefulWidget {
  final RutaTrabajo rutaInicial;
  const NavegacionCampoPantalla({super.key, required this.rutaInicial});
  @override
  State<NavegacionCampoPantalla> createState() =>
      _NavegacionCampoPantallaState();
}

class _NavegacionCampoPantallaState extends State<NavegacionCampoPantalla>
    with WidgetsBindingObserver {
  final _tracking = TrackingGpsService();
  final _service = RutasTrabajoService();
  final _map = MapController();
  RutaTrabajo? _ruta;
  String? _error;
  bool _cargando = true,
      _formulario = false,
      _abriendoMapa = false,
      _gpsOcupado = false;
  Timer? _reloj, _simulacion;
  String? _usuario;
  int _consulta = 0;

  PuntoTrabajo? get _objetivo => _ruta?.siguiente;
  bool get _gpsVigente =>
      TrackingGpsService.posicionVigente(_tracking.ultimaPosicion);
  bool get _ensayo => _tracking.isSimulacionActiva;
  bool get _tienePosicion => _ensayo || _gpsVigente;
  double? get _distancia {
    final punto = _objetivo;
    if (!_tienePosicion || punto == null || !punto.tieneCoordenadas) {
      return null;
    }
    return TrackingGpsService.calcularDistanciaMetros(
      _tracking.latitud,
      _tracking.longitud,
      punto.latitud!,
      punto.longitud!,
    );
  }

  @override
  void initState() {
    super.initState();
    _usuario = SesionUsuario.actual.value?.usuario;
    WidgetsBinding.instance.addObserver(this);
    _tracking.onLocationChanged = (_, _, _, _) {
      if (mounted) setState(() {});
    };
    // Caducar también la distancia visible aunque el receptor deje de entregar lecturas.
    _reloj = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() {});
    });
    _cargar();
    _reintentarGps();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed) {
      _simulacion?.cancel();
      _simulacion = null;
      _tracking.detenerTransmision();
    } else {
      if (!_ensayo) _tracking.iniciarTransmision();
      if (!_formulario) _cargar();
      if (mounted) setState(() {});
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _reloj?.cancel();
    _simulacion?.cancel();
    _tracking.onLocationChanged = null;
    _tracking.detenerTransmision();
    _tracking.isSimulacionActiva = false;
    final real = _tracking.ultimaPosicion;
    _tracking.latitud = real?.latitude ?? -16.397;
    _tracking.longitud = real?.longitude ?? -60.960;
    _tracking.velocidad = 0;
    _map.dispose();
    super.dispose();
  }

  Future<void> _cargar() async {
    if (_formulario) return;
    final consulta = ++_consulta;
    setState(() {
      _cargando = true;
      _error = null;
    });
    try {
      final ruta = await _service.obtenerDetalleRuta(widget.rutaInicial.id);
      if (_usuario == null ||
          SesionUsuario.actual.value?.usuario != _usuario ||
          !ruta.perteneceA(_usuario!)) {
        throw Exception(
          'La ruta no pertenece a la sesión actual. Regrese a la bandeja.',
        );
      }
      if (!mounted || consulta != _consulta) return;
      setState(() => _ruta = ruta);
    } catch (e) {
      if (mounted && consulta == _consulta) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted && consulta == _consulta) setState(() => _cargando = false);
    }
  }

  Future<void> _reintentarGps() async {
    if (_gpsOcupado) return;
    setState(() => _gpsOcupado = true);
    _simulacion?.cancel();
    _simulacion = null;
    await _tracking.volverAGpsReal();
    if (mounted) setState(() => _gpsOcupado = false);
  }

  Future<void> _navegar(AplicacionNavegacion app) async {
    final punto = _objetivo;
    if (_abriendoMapa || punto == null || !punto.tieneCoordenadas || _ensayo) {
      return;
    }
    setState(() => _abriendoMapa = true);
    try {
      await NavegacionExternaService().navegar(
        punto.latitud!,
        punto.longitud!,
        app: app,
      );
    } catch (e) {
      if (mounted) _mensaje(e.toString());
    } finally {
      if (mounted) setState(() => _abriendoMapa = false);
    }
  }

  void _simular() {
    if (_simulacion != null) {
      _simulacion!.cancel();
      setState(() => _simulacion = null);
      return;
    }
    final punto = _objetivo;
    if (punto == null || !punto.tieneCoordenadas) return;
    _tracking.avanzarHacia(punto.latitud!, punto.longitud!);
    _simulacion = Timer.periodic(const Duration(milliseconds: 600), (timer) {
      _tracking.avanzarHacia(punto.latitud!, punto.longitud!);
      if ((_distancia ?? double.infinity) < 10) {
        timer.cancel();
        if (mounted) setState(() => _simulacion = null);
      }
    });
    setState(() {});
  }

  Future<void> _atender() async {
    final punto = _objetivo;
    if (_formulario ||
        _cargando ||
        _error != null ||
        _ensayo ||
        !_gpsVigente ||
        punto == null ||
        !punto.tieneCoordenadas ||
        !(_ruta?.puedeAtender ?? false)) {
      return;
    }
    setState(() => _formulario = true);
    try {
      // Releer antes de abrir: otra pantalla/sesión pudo cambiar el estado o la asignación.
      final actual = await _service.obtenerDetalleRuta(_ruta!.id);
      if (SesionUsuario.actual.value?.usuario != _usuario ||
          !actual.perteneceA(_usuario!)) {
        throw Exception(
          'La asignación o la sesión cambió. Regrese a la bandeja.',
        );
      }
      if (!mounted) return;
      setState(() => _ruta = actual);
      final siguiente = actual.siguiente;
      if (!actual.puedeAtender || siguiente?.id != punto.id) {
        _mensaje(
          'La ruta cambió. Revise el siguiente punto antes de continuar.',
        );
        return;
      }
      await FormularioCierreOrdenModal.mostrar(
        context: context,
        rutaActiva: actual.toJson(),
        objetivoActual: siguiente!.toJson(),
        onCompletadoExitoso: (_) =>
            _mensaje('Atención registrada. Actualizando la ruta…'),
      );
    } catch (e) {
      if (mounted) _mensaje(e.toString());
    } finally {
      if (mounted) {
        setState(() => _formulario = false);
        await _cargar();
      }
    }
  }

  void _mensaje(String mensaje) => ScaffoldMessenger.of(
    context,
  ).showSnackBar(SnackBar(content: Text(mensaje)));

  @override
  Widget build(BuildContext context) {
    final punto = _objetivo;
    final distancia = _distancia;
    final posicion = _tracking.ultimaPosicion;
    final destinoValido = punto?.tieneCoordenadas ?? false;
    final centro = _tienePosicion
        ? LatLng(_tracking.latitud, _tracking.longitud)
        : destinoValido
        ? LatLng(punto!.latitud!, punto.longitud!)
        : const LatLng(-16.397, -60.960);
    return Scaffold(
      appBar: AppBar(
        title: Text(
          _ensayo ? 'ENSAYO · sin registro operativo' : 'Atención en secuencia',
        ),
        actions: [
          IconButton(
            tooltip: 'Actualizar ruta',
            onPressed: _cargando || _formulario ? null : _cargar,
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _cargando
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_error!),
                  TextButton(
                    onPressed: _cargar,
                    child: const Text('Reintentar'),
                  ),
                  TextButton(
                    onPressed: () => Navigator.pop(context),
                    child: const Text('Volver a la bandeja'),
                  ),
                ],
              ),
            )
          : Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(8),
                  child: Column(
                    children: [
                      Text(
                        _ensayo
                            ? 'Posición simulada. No se transmite ni permite cierres.'
                            : _tracking.ultimoError ??
                                  (!_gpsVigente
                                      ? 'GPS ausente o caducado. Reintente.'
                                      : 'GPS ±${posicion!.accuracy.toStringAsFixed(0)} m · ${posicion.timestamp.toLocal()}'),
                      ),
                      Wrap(
                        alignment: WrapAlignment.center,
                        children: [
                          TextButton(
                            onPressed: _gpsOcupado ? null : _reintentarGps,
                            child: Text(
                              _gpsOcupado
                                  ? 'Obteniendo GPS…'
                                  : _ensayo
                                  ? 'Volver a GPS real'
                                  : 'Reintentar GPS',
                            ),
                          ),
                          TextButton(
                            onPressed: () => Geolocator.openAppSettings(),
                            child: const Text('Permisos'),
                          ),
                          TextButton(
                            onPressed: () => Geolocator.openLocationSettings(),
                            child: const Text('Ajustes GPS'),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: FlutterMap(
                    mapController: _map,
                    options: MapOptions(initialCenter: centro, initialZoom: 16),
                    children: [
                      TileLayer(
                        urlTemplate:
                            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                        userAgentPackageName: 'com.arquis.alfa',
                      ),
                      MarkerLayer(
                        markers: [
                          if (_tienePosicion)
                            Marker(
                              point: centro,
                              width: 40,
                              height: 40,
                              child: Icon(
                                Icons.my_location,
                                color: _ensayo ? Colors.amber : Colors.blue,
                              ),
                            ),
                          for (final parada
                              in _ruta?.puntos ?? <PuntoTrabajo>[])
                            if (parada.tieneCoordenadas)
                              Marker(
                                point: LatLng(
                                  parada.latitud!,
                                  parada.longitud!,
                                ),
                                width: 36,
                                height: 36,
                                child: CircleAvatar(
                                  backgroundColor: parada.atendido
                                      ? Colors.green
                                      : parada.id == punto?.id
                                      ? Colors.red
                                      : Colors.blueGrey,
                                  child: Text('${parada.orden}'),
                                ),
                              ),
                        ],
                      ),
                    ],
                  ),
                ),
                SafeArea(
                  top: false,
                  child: Padding(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Text(
                          '${_ruta?.codigo} · ${_ruta?.atendidos ?? 0}/${_ruta?.puntos.length ?? 0} atendidos',
                        ),
                        if (_ruta != null)
                          LinearProgressIndicator(
                            value: _ruta!.puntos.isEmpty
                                ? 0
                                : _ruta!.atendidos / _ruta!.puntos.length,
                          ),
                        if (punto != null &&
                            (_ruta?.puedeAtender ?? false)) ...[
                          Text(
                            '${punto.orden}. ${punto.titular ?? "Cliente"} · ${punto.codigoSuministro ?? ""}',
                          ),
                          Text(punto.direccion ?? 'Sin dirección'),
                          Text(
                            !destinoValido
                                ? 'Destino sin coordenadas válidas. Solicite corregir la asignación.'
                                : distancia == null
                                ? 'Distancia no disponible: esperando GPS reciente'
                                : '${TrackingGpsService.formatearDistancia(distancia)} en línea recta · proximidad de registro: 30 m',
                          ),
                          Row(
                            children: [
                              Expanded(
                                child: FilledButton.icon(
                                  onPressed:
                                      !destinoValido || _ensayo || _abriendoMapa
                                      ? null
                                      : () => _navegar(
                                          AplicacionNavegacion.googleMaps,
                                        ),
                                  icon: const Icon(Icons.directions),
                                  label: const Text('Navegar'),
                                ),
                              ),
                              TextButton(
                                onPressed:
                                    !destinoValido || _ensayo || _abriendoMapa
                                    ? null
                                    : () => _navegar(AplicacionNavegacion.waze),
                                child: const Text('Waze'),
                              ),
                              TextButton(
                                onPressed: !destinoValido || _gpsOcupado
                                    ? null
                                    : _simular,
                                child: Text(
                                  _simulacion == null ? 'Simular' : 'Pausar',
                                ),
                              ),
                            ],
                          ),
                          FilledButton(
                            onPressed:
                                _formulario ||
                                    _ensayo ||
                                    !_gpsVigente ||
                                    !destinoValido ||
                                    (distancia ?? double.infinity) > 30
                                ? null
                                : _atender,
                            child: const Text('Registrar atención'),
                          ),
                        ] else
                          Text(
                            _ruta?.puntos.isEmpty ?? true
                                ? 'Ruta sin paradas'
                                : 'Ruta finalizada o cancelada',
                          ),
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
