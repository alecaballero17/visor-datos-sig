import 'dart:async';
import 'dart:math' show pi;
import '../../../models/secuencia_atencion.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../services/tracking_gps_service.dart';
import '../../../services/rutas_trabajo_service.dart';
import '../../widgets/formulario_cierre_orden_modal.dart';

class NavegacionCampoPantalla extends StatefulWidget {
  final Map<String, dynamic>? rutaInicial;

  const NavegacionCampoPantalla({super.key, this.rutaInicial});

  @override
  State<NavegacionCampoPantalla> createState() => _NavegacionCampoPantallaState();
}

class _NavegacionCampoPantallaState extends State<NavegacionCampoPantalla> {
  final TrackingGpsService _tracking = TrackingGpsService();
  final RutasTrabajoService _rutasService = RutasTrabajoService();
  final MapController _mapController = MapController();

  Map<String, dynamic>? _rutaActiva;
  List<dynamic> _puntos = [];
  Map<String, dynamic>? _objetivoActual;
  int _puntosCompletados = 0;
  bool _cargando = true;
  String? _errorCarga;

  // Estado del GPS en vivo
  double _userLat = -17.78100;
  double _userLng = -63.18120;
  double _userSpeed = 0.0;
  double _userHeading = 0.0;

  // Distancia y tiempo restante al objetivo actual
  double _distanciaMetros = 0.0;
  String _tiempoEstimado = '0 min';

  Timer? _timerSimulacionPaso;
  bool _simulandoAvance = false;

  @override
  void initState() {
    super.initState();
    _userLat = _tracking.latitud;
    _userLng = _tracking.longitud;
    _userSpeed = _tracking.velocidad;
    _userHeading = _tracking.rumbo;

    _tracking.onLocationChanged = (lat, lng, speed, heading) {
      if (!mounted) return;
      setState(() {
        _userLat = lat;
        _userLng = lng;
        _userSpeed = speed;
        _userHeading = heading;
        _recalcularDistancia();
      });
    };

    _tracking.iniciarTransmision();
    _cargarRuta();
  }

  @override
  void dispose() {
    _timerSimulacionPaso?.cancel();
    if (_tracking.isSimulacionActiva) {
      final real = _tracking.ultimaPosicion;
      _tracking.latitud = real?.latitude ?? -16.397;
      _tracking.longitud = real?.longitude ?? -60.960;
      _tracking.velocidad = 0;
    }
    _tracking.isSimulacionActiva = false;
    _tracking.onLocationChanged = null;
    _tracking.detenerTransmision();
    super.dispose();
  }

  Future<void> _cargarRuta() async {
    setState(() { _cargando = true; _errorCarga = null; });
    try {
      final id = widget.rutaInicial?['id'] as int?;
      if (id == null) throw Exception('Seleccione una ruta desde la bandeja.');
      final ruta = await _rutasService.obtenerDetalleRuta(id);
      if (!mounted) return;
      _rutaActiva = ruta;
      _puntos = ordenarPuntos(ruta['puntos'] ?? []);
      _contarCompletados();
      _seleccionarSiguienteObjetivo();
    } catch (e) {
      if (!mounted) return;
      _errorCarga = e.toString().replaceFirst('Exception: ', '');
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  void _contarCompletados() {
    _puntosCompletados = _puntos.where((p) => puntoAtendido(Map<String, dynamic>.from(p))).length;
  }

  void _seleccionarSiguienteObjetivo() {
    _objetivoActual = siguientePunto(_puntos);
    if (_objetivoActual == null) {
      _distanciaMetros = 0;
      _tiempoEstimado = 'Ruta finalizada';
      return;
    }
    _recalcularDistancia();
  }

  void _recalcularDistancia() {
    if (_objetivoActual == null) return;
    if (_tracking.ultimaPosicion == null && !_tracking.isSimulacionActiva) {
      _distanciaMetros = 0;
      _tiempoEstimado = 'Esperando GPS';
      return;
    }
    final tLat = (_objetivoActual!['latitud'] as num).toDouble();
    final tLng = (_objetivoActual!['longitud'] as num).toDouble();
    _distanciaMetros = TrackingGpsService.calcularDistanciaMetros(_userLat, _userLng, tLat, tLng);
    _tiempoEstimado = TrackingGpsService.formatearTiempoEstimado(_distanciaMetros);
  }

  void _toggleSimulacionAvance() {
    if (_simulandoAvance) {
      _timerSimulacionPaso?.cancel();
      setState(() => _simulandoAvance = false);
      return;
    }

    if (_objetivoActual == null) return;
    setState(() => _simulandoAvance = true);

    final tLat = (_objetivoActual!['latitud'] as num).toDouble();
    final tLng = (_objetivoActual!['longitud'] as num).toDouble();

    _timerSimulacionPaso = Timer.periodic(const Duration(milliseconds: 600), (timer) {
      if (!mounted || !_simulandoAvance) {
        timer.cancel();
        return;
      }

      _tracking.avanzarHacia(tLat, tLng, velocidadKmh: 25.0);
      _mapController.move(LatLng(_userLat, _userLng), _mapController.camera.zoom);

      if (_distanciaMetros < 15) {
        timer.cancel();
        setState(() => _simulandoAvance = false);
        _mostrarAlertaLlegada();
      }
    });
  }

  void _mostrarAlertaLlegada() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        backgroundColor: Color(0xFF10B981),
        behavior: SnackBarBehavior.floating,
        content: Text(
          "ENSAYO: destino simulado alcanzado. El registro operativo permanece bloqueado.",
          style: TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  Future<void> _ejecutarAccion() async {
    if (_objetivoActual == null || _rutaActiva == null) return;

    final esCorte = (_rutaActiva!['tipo'] ?? '').toString().toLowerCase().contains('corte');

    await FormularioCierreOrdenModal.mostrar(
      context: context,
      rutaActiva: _rutaActiva!,
      objetivoActual: _objetivoActual!,
      onCompletadoExitoso: (estadoFinal) {
        setState(() {
          _objetivoActual!['estado'] = const ['Observado', 'Omitido'].contains(estadoFinal) ? estadoFinal : 'Completado';
          _contarCompletados();
          _seleccionarSiguienteObjetivo();
        });

        _mostrarNotificacionExito(esCorte, estadoFinal);
      },
    );
  }

  void _mostrarNotificacionExito(bool esCorte, String estadoFinal) {
    final mensaje = estadoFinal == 'Observado'
        ? "Orden registrada como Observada con constancia y evidencia fotográfica transmitida."
        : (esCorte
            ? "Corte registrado satisfactoriamente con lectura y evidencia fotográfica. Sincronizado."
            : "Reconexión registrada satisfactoriamente con lectura y evidencia fotográfica. Servicio restablecido.");

    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: estadoFinal == 'Observado' ? const Color(0xFFF59E0B) : const Color(0xFF10B981),
        behavior: SnackBarBehavior.floating,
        content: Text(
          mensaje,
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final esCorte = (_rutaActiva?['tipo'] ?? '').toString().toLowerCase().contains('corte');

    final tienePosicion = _tracking.ultimaPosicion != null || _tracking.isSimulacionActiva;
    final List<LatLng> linePoints = [
      if (tienePosicion) LatLng(_userLat, _userLng),
      if (_objetivoActual != null)
        LatLng((_objetivoActual!['latitud'] as num).toDouble(), (_objetivoActual!['longitud'] as num).toDouble()),
    ];

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(title: Text(_tracking.isSimulacionActiva ? 'ENSAYO · sin registro operativo' : 'Atención en secuencia'),
        bottom: PreferredSize(preferredSize: const Size.fromHeight(44), child: Padding(
          padding: const EdgeInsets.all(8), child: Text(
            _tracking.ultimoError ?? (_tracking.ultimaPosicion == null ? 'Esperando GPS real…' :
              'GPS ±${_tracking.ultimaPosicion!.accuracy.toStringAsFixed(0)} m · ${_tracking.ultimaPosicion!.timestamp.toLocal()}'),
            maxLines: 2, style: const TextStyle(fontSize: 12)))),
        actions: [IconButton(tooltip: 'Reintentar GPS', icon: const Icon(Icons.gps_fixed), onPressed: () async {
          await _tracking.solicitarPermisosUbicacion();
          if (mounted) setState(() {});
        })]),
      body: _cargando
          ? const Center(child: CircularProgressIndicator(color: Color(0xFF38BDF8)))
          : _errorCarga != null
            ? Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                Text(_errorCarga!, style: const TextStyle(color: Colors.white)),
                TextButton(onPressed: _cargarRuta, child: const Text("Reintentar")),
                TextButton(onPressed: () => Navigator.pop(context), child: const Text("Volver")),
              ]))
            : Stack(
              children: [
                FlutterMap(
                  mapController: _mapController,
                  options: MapOptions(
                    initialCenter: LatLng(_userLat, _userLng),
                    initialZoom: 17.0,
                  ),
                  children: [
                    TileLayer(
                      urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                      userAgentPackageName: 'com.arquis.alfa',
                    ),
                    PolylineLayer(
                      polylines: [
                        Polyline(
                          points: linePoints,
                          strokeWidth: 5,
                          color: const Color(0xFF0284C7),
                          borderStrokeWidth: 2,
                          borderColor: Colors.white,
                        ),
                      ],
                    ),
                    MarkerLayer(
                      markers: [
                        if (tienePosicion) Marker(
                          point: LatLng(_userLat, _userLng),
                          width: 44,
                          height: 44,
                          child: Transform.rotate(
                            angle: _userHeading * pi / 180,
                            child: Container(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: const Color(0xFF0284C7),
                                border: Border.all(color: Colors.white, width: 2),
                                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 6)],
                              ),
                              child: const Icon(Icons.navigation, color: Colors.white, size: 20),
                            ),
                          ),
                        ),
                        ..._puntos.map((p) {
                          final pLat = (p['latitud'] as num).toDouble();
                          final pLng = (p['longitud'] as num).toDouble();
                          final isTarget = _objetivoActual != null && _objetivoActual!['id'] == p['id'];
                          final completado = puntoAtendido(Map<String, dynamic>.from(p));

                          return Marker(
                            point: LatLng(pLat, pLng),
                            width: isTarget ? 44 : 32,
                            height: isTarget ? 44 : 32,
                            child: Container(
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: completado
                                    ? const Color(0xFF10B981)
                                    : (isTarget ? (esCorte ? const Color(0xFFEF4444) : const Color(0xFF2563EB)) : Colors.blueGrey),
                                border: Border.all(color: Colors.white, width: isTarget ? 2.5 : 1.5),
                              ),
                              child: Center(
                                child: completado
                                    ? const Icon(Icons.check, color: Colors.white, size: 16)
                                    : Text(
                                        "${p['orden'] ?? '1'}",
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                          fontSize: isTarget ? 14 : 11,
                                        ),
                                      ),
                              ),
                            ),
                          );
                        }),
                      ],
                    ),
                  ],
                ),

                // Encabezado Superior de Navegación Turn-by-Turn
                SafeArea(
                  child: Align(
                    alignment: Alignment.topCenter,
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(color: Colors.white12),
                        boxShadow: const [BoxShadow(color: Colors.black38, blurRadius: 10, offset: Offset(0, 3))],
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0284C7).withAlpha(40),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: const Icon(Icons.turn_slight_right, color: Color(0xFF38BDF8), size: 26),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      TrackingGpsService.formatearDistancia(_distanciaMetros),
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18),
                                    ),
                                    const SizedBox(width: 8),
                                    Text("· $_tiempoEstimado", style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 13, fontWeight: FontWeight.w500)),
                                  ],
                                ),
                                Text(
                                  _objetivoActual != null
                                      ? "Lote ${_objetivoActual!['lote'] ?? '—'} · ${_objetivoActual!['titular'] ?? 'Pendiente'}"
                                      : "Todos los puntos han sido completados",
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(color: Colors.white70, fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.close, color: Colors.white70, size: 20),
                            onPressed: () => Navigator.pop(context),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),

                // Indicador de Velocidad y Controles
                Positioned(
                  right: 16,
                  top: 100,
                  child: Column(
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1E293B),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.white12),
                        ),
                        child: Column(
                          children: [
                            Text(
                              _userSpeed.toStringAsFixed(0),
                              style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.bold, fontSize: 17),
                            ),
                            const Text("km/h", style: TextStyle(color: Colors.white60, fontSize: 9)),
                          ],
                        ),
                      ),
                      const SizedBox(height: 10),
                      FloatingActionButton.small(
                        heroTag: 'nav_center',
                        backgroundColor: const Color(0xFF1E293B),
                        onPressed: () => _mapController.move(LatLng(_userLat, _userLng), 17.5),
                        child: const Icon(Icons.my_location, color: Color(0xFF38BDF8)),
                      ),
                      const SizedBox(height: 10),
                      FloatingActionButton.small(
                        heroTag: 'nav_nearest',
                        backgroundColor: const Color(0xFF1E293B),
                        onPressed: _seleccionarSiguienteObjetivo,
                        child: const Icon(Icons.near_me, color: Colors.white70),
                      ),
                    ],
                  ),
                ),

                // Panel Inferior de Gestión de Intervención
                Align(
                  alignment: Alignment.bottomCenter,
                  child: Container(
                    margin: const EdgeInsets.all(16),
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: const Color(0xFF1E293B),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: Colors.white12),
                      boxShadow: const [BoxShadow(color: Colors.black45, blurRadius: 14, offset: Offset(0, 4))],
                    ),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              "Hoja de Ruta: ${_rutaActiva?['codigo'] ?? 'Activa'}",
                              style: const TextStyle(color: Color(0xFF38BDF8), fontWeight: FontWeight.w600, fontSize: 12),
                            ),
                            Text(
                              "$_puntosCompletados / ${_puntos.length} Intervenidos",
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 12),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        ClipRRect(
                          borderRadius: BorderRadius.circular(4),
                          child: LinearProgressIndicator(
                            value: _puntos.isNotEmpty ? _puntosCompletados / _puntos.length : 0,
                            backgroundColor: Colors.white12,
                            valueColor: AlwaysStoppedAnimation<Color>(esCorte ? const Color(0xFFEF4444) : const Color(0xFF10B981)),
                            minHeight: 6,
                          ),
                        ),
                        const SizedBox(height: 12),

                        if (_objetivoActual != null) ...[
                          Row(
                            children: [
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      "${_objetivoActual!['titular'] ?? 'Titular no asignado'}",
                                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                                    ),
                                    Text(
                                      "Lote ${_objetivoActual!['lote'] ?? '—'} · Código: ${_objetivoActual!['codigoSuministro'] ?? '—'}",
                                      style: const TextStyle(color: Colors.white60, fontSize: 12),
                                    ),
                                    if (_objetivoActual!['montoDeuda'] != null)
                                      Text(
                                        "Deuda acumulada: Bs. ${_objetivoActual!['montoDeuda']}",
                                        style: const TextStyle(color: Color(0xFFF87171), fontWeight: FontWeight.bold, fontSize: 11),
                                      ),
                                  ],
                                ),
                              ),
                              OutlinedButton.icon(
                                onPressed: _toggleSimulacionAvance,
                                style: OutlinedButton.styleFrom(
                                  foregroundColor: _simulandoAvance ? Colors.amber : const Color(0xFF38BDF8),
                                  side: BorderSide(color: _simulandoAvance ? Colors.amber : const Color(0xFF38BDF8)),
                                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                                ),
                                icon: Icon(_simulandoAvance ? Icons.pause : Icons.fast_forward, size: 14),
                                label: Text(_simulandoAvance ? "Pausar" : "Simular", style: const TextStyle(fontSize: 11)),
                              ),
                            ],
                          ),
                          const SizedBox(height: 12),

                          SizedBox(
                            width: double.infinity,
                            height: 48,
                            child: ElevatedButton.icon(
                              onPressed: _ejecutarAccion,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: esCorte ? const Color(0xFFEF4444) : const Color(0xFF2563EB),
                                foregroundColor: Colors.white,
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                              ),
                              icon: Icon(esCorte ? Icons.content_cut : Icons.water_drop, size: 18),
                              label: Text(
                                esCorte ? "Registrar Corte de Servicio" : "Registrar Reconexión de Agua",
                                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
                              ),
                            ),
                          ),
                        ] else ...[
                          const Padding(
                            padding: EdgeInsets.symmetric(vertical: 6),
                            child: Text(
                              "Todos los puntos de la hoja de ruta han sido ejecutados.",
                              style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.w600, fontSize: 13),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ),
              ],
            ),
    );
  }
}
