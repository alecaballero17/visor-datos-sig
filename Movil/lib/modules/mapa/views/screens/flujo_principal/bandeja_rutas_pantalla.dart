import 'package:flutter/material.dart';
import '../../../models/ruta_trabajo.dart';
import '../../../../auth/services/auth_service.dart';
import 'mapa_pantalla_inicio.dart';
import '../../../services/rutas_trabajo_service.dart';
import '../../../services/tracking_gps_service.dart';
import '../../../../auth/models/sesion_usuario.dart';
import 'navegacion_campo_pantalla.dart';

class BandejaRutasPantalla extends StatefulWidget {
  const BandejaRutasPantalla({super.key});

  @override
  State<BandejaRutasPantalla> createState() => _BandejaRutasPantallaState();
}

class _BandejaRutasPantallaState extends State<BandejaRutasPantalla> {
  final _service = RutasTrabajoService();
  bool _cargando = true;
  bool _abriendo = false;
  String? _error;
  List<RutaTrabajo> _rutas = [];
  int _consulta = 0;

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    if (_abriendo) return;
    final consulta = ++_consulta;
    final identidad = SesionUsuario.actual.value?.usuario;
    setState(() {
      _cargando = true;
      _error = null;
      _rutas = [];
    });
    try {
      await TrackingGpsService().cargarSesionUsuario();
      final usuario = SesionUsuario.actual.value?.usuario;
      if (usuario == null || (identidad != null && identidad != usuario)) {
        throw Exception('La sesión cambió. Vuelva a abrir la bandeja.');
      }
      final rutas = await _service.obtenerRutasAsignadas(operario: usuario);
      if (!mounted ||
          consulta != _consulta ||
          SesionUsuario.actual.value?.usuario != usuario) {
        return;
      }
      if (rutas.any((ruta) => !ruta.perteneceA(usuario))) {
        throw Exception(
          'La respuesta contiene rutas de otro empleado. Actualice la sesión.',
        );
      }
      // Mantener el orden cronológico recibido; cada ruta ordena sus paradas por Orden.
      setState(() => _rutas = rutas);
    } catch (e) {
      if (mounted && consulta == _consulta) {
        setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
      }
    } finally {
      if (mounted && consulta == _consulta) setState(() => _cargando = false);
    }
  }

  Future<void> _abrir(RutaTrabajo ruta) async {
    if (_abriendo || _cargando) return;
    setState(() => _abriendo = true);
    final usuario = SesionUsuario.actual.value?.usuario;
    try {
      var actual = await _service.obtenerDetalleRuta(ruta.id);
      if (usuario == null ||
          SesionUsuario.actual.value?.usuario != usuario ||
          !actual.perteneceA(usuario)) {
        throw Exception(
          'La ruta ya no está asignada a esta sesión. Actualice la bandeja.',
        );
      }
      if (!actual.puedeAtender) {
        throw Exception('La ruta está vacía, finalizada o cancelada.');
      }
      if (actual.pendiente) {
        await _service.iniciarRuta(actual.id);
        actual = await _service.obtenerDetalleRuta(actual.id);
      }
      if (!mounted || SesionUsuario.actual.value?.usuario != usuario) return;
      await Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => NavegacionCampoPantalla(rutaInicial: actual),
        ),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) {
        setState(() => _abriendo = false);
        TrackingGpsService().iniciarTransmision();
        await _cargar();
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final sesion = SesionUsuario.actual.value;
    return Scaffold(
      appBar: AppBar(
        title: const Text('Mis rutas'),
        actions: [
          IconButton(
            tooltip: 'Mapa catastral',
            icon: const Icon(Icons.map),
            onPressed: _abriendo
                ? null
                : () async {
                    await Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => const MapaPantallaInicio(),
                      ),
                    );
                    if (mounted) await _cargar();
                  },
          ),
          IconButton(
            tooltip: 'Cerrar sesión',
            icon: const Icon(Icons.logout),
            onPressed: _abriendo
                ? null
                : () async {
                    try {
                      await AuthService().logout();
                    } catch (_) {
                      // AuthService limpia cookie e identidad incluso si el servidor no responde.
                    }
                  },
          ),
          IconButton(
            onPressed: _cargando || _abriendo ? null : _cargar,
            tooltip: 'Actualizar',
            icon: const Icon(Icons.refresh),
          ),
        ],
      ),
      body: _cargando
          ? const Center(child: CircularProgressIndicator())
          : _error != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(_error!),
                    TextButton(
                      onPressed: _cargar,
                      child: const Text('Reintentar'),
                    ),
                  ],
                ),
              ),
            )
          : RefreshIndicator(
              onRefresh: _cargar,
              child: ListView(
                physics: const AlwaysScrollableScrollPhysics(),
                padding: const EdgeInsets.all(16),
                children: [
                  Text(
                    '${sesion?.nombre ?? ""} · ${sesion?.roles.join(", ") ?? ""}',
                  ),
                  if (_abriendo) const LinearProgressIndicator(),
                  if (_rutas.isEmpty)
                    const Padding(
                      padding: EdgeInsets.all(24),
                      child: Text(
                        'No tienes rutas asignadas. Desliza para actualizar.',
                      ),
                    ),
                  for (final item in _rutas) _tarjeta(item),
                ],
              ),
            ),
    );
  }

  Widget _tarjeta(RutaTrabajo ruta) {
    final puntos = ruta.puntos;
    final atendidos = ruta.atendidos;
    return Card(
      child: ExpansionTile(
        title: Text(
          '${ruta.codigo.isEmpty ? ruta.id : ruta.codigo} · ${ruta.tipo}',
        ),
        subtitle: Text(
          '${ruta.estado} · $atendidos/${puntos.length} atendidos',
        ),
        children: [
          if (puntos.isEmpty)
            const ListTile(title: Text('Ruta sin paradas asignadas')),
          for (final punto in puntos)
            ListTile(
              leading: CircleAvatar(child: Text('${punto.orden}')),
              title: Text(
                '${punto.titular ?? "Cliente"} · ${punto.codigoSuministro ?? ""}',
              ),
              subtitle: Text(
                '${punto.direccion ?? "Sin dirección"}\n${punto.estado} · ${punto.tieneCoordenadas ? "${punto.latitud}, ${punto.longitud}" : "Coordenadas no válidas"}',
              ),
              isThreeLine: true,
              trailing: punto.atendido ? const Icon(Icons.check_circle) : null,
            ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: FilledButton(
              onPressed: _abriendo || !ruta.puedeAtender
                  ? null
                  : () => _abrir(ruta),
              child: Text(
                puntos.isEmpty
                    ? 'Sin paradas'
                    : !ruta.puedeAtender
                    ? 'Ruta finalizada o cancelada'
                    : 'Atender en orden',
              ),
            ),
          ),
        ],
      ),
    );
  }
}
