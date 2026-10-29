import 'package:flutter/material.dart';
import '../../../models/secuencia_atencion.dart';
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
  List<dynamic> _rutas = [];

  @override
  void initState() {
    super.initState();
    _cargar();
  }

  Future<void> _cargar() async {
    setState(() { _cargando = true; _error = null; });
    try {
      await TrackingGpsService().cargarSesionUsuario();
      final usuario = SesionUsuario.actual.value!.usuario;
      final rutas = await _service.obtenerRutasAsignadas(operario: usuario);
      if (mounted) setState(() => _rutas = rutas);
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _cargando = false);
    }
  }

  Future<void> _abrir(Map<String, dynamic> ruta) async {
    if (_abriendo) return;
    setState(() => _abriendo = true);
    try {
      if (ruta['estado'] == 'Pendiente' && !await _service.iniciarRuta(ruta['id'] as int)) {
        throw Exception('No se pudo iniciar la ruta. Reintente.');
      }
      if (!mounted) return;
      await Navigator.push(context, MaterialPageRoute(
        builder: (_) => NavegacionCampoPantalla(rutaInicial: ruta)));
      TrackingGpsService().iniciarTransmision();
      if (mounted) await _cargar();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
    } finally {
      if (mounted) setState(() => _abriendo = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final sesion = SesionUsuario.actual.value;
    return Scaffold(
      appBar: AppBar(title: const Text('Mis rutas'), actions: [
        IconButton(onPressed: _cargando || _abriendo ? null : _cargar,
          tooltip: 'Actualizar', icon: const Icon(Icons.refresh)),
      ]),
      body: _cargando ? const Center(child: CircularProgressIndicator())
        : _error != null ? Center(child: Padding(padding: const EdgeInsets.all(24),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(_error!), TextButton(onPressed: _cargar, child: const Text('Reintentar')),
          ])))
        : RefreshIndicator(onRefresh: _cargar, child: ListView(
          physics: const AlwaysScrollableScrollPhysics(), padding: const EdgeInsets.all(16),
          children: [
            Text('${sesion?.nombre ?? ""} · ${sesion?.roles.join(", ") ?? ""}'),
            if (_abriendo) const LinearProgressIndicator(),
            if (_rutas.isEmpty) const Padding(padding: EdgeInsets.all(24),
              child: Text('No tienes rutas asignadas. Desliza para actualizar.')),
            for (final item in _rutas) _tarjeta(Map<String, dynamic>.from(item as Map)),
          ],
        )),
    );
  }

  Widget _tarjeta(Map<String, dynamic> ruta) {
    final puntos = ordenarPuntos(ruta['puntos'] ?? []);
    final atendidos = puntos.where(puntoAtendido).length;
    return Card(child: ExpansionTile(
      title: Text('${ruta["codigo"] ?? ruta["id"]} · ${ruta["tipo"] ?? "Ruta"}'),
      subtitle: Text('${ruta["estado"]} · $atendidos/${puntos.length} atendidos'),
      children: [
        for (final punto in puntos) ListTile(
          leading: CircleAvatar(child: Text('${punto["orden"]}')),
          title: Text('${punto["titular"] ?? punto["nombre"] ?? "Cliente"} · ${punto["codigoSuministro"] ?? ""}'),
          subtitle: Text('${punto["direccion"] ?? "Sin dirección"}\n${punto["estado"]} · ${punto["latitud"]}, ${punto["longitud"]}'),
          isThreeLine: true,
          trailing: puntoAtendido(punto) ? const Icon(Icons.check_circle) : null,
        ),
        Padding(padding: const EdgeInsets.all(12), child: FilledButton(
          onPressed: _abriendo || puntos.isEmpty || atendidos == puntos.length ? null : () => _abrir(ruta),
          child: Text(atendidos == puntos.length ? 'Ruta finalizada' : 'Atender en orden'),
        )),
      ],
    ));
  }
}
