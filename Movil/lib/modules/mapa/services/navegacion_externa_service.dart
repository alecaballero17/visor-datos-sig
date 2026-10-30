import 'package:url_launcher/url_launcher.dart';

enum AplicacionNavegacion { googleMaps, waze }

typedef AbrirEnlace = Future<bool> Function(Uri uri);

class NavegacionExternaService {
  final AbrirEnlace _abrir;
  NavegacionExternaService({AbrirEnlace? abrir})
    : _abrir =
          abrir ??
          ((uri) => launchUrl(uri, mode: LaunchMode.externalApplication));

  static List<Uri> enlaces(
    double latitud,
    double longitud,
    AplicacionNavegacion app,
  ) {
    if (!latitud.isFinite ||
        !longitud.isFinite ||
        latitud.abs() > 90 ||
        longitud.abs() > 180) {
      throw ArgumentError('El destino no tiene coordenadas válidas.');
    }
    final destino = '$latitud,$longitud';
    final web = Uri.https('www.google.com', '/maps/dir/', {
      'api': '1',
      'destination': destino,
      'travelmode': 'driving',
      'dir_action': 'navigate',
    });
    return app == AplicacionNavegacion.waze
        ? [Uri.parse('waze://?ll=$destino&navigate=yes'), web]
        : [Uri.parse('google.navigation:q=$destino&mode=d'), web];
  }

  Future<void> navegar(
    double latitud,
    double longitud, {
    AplicacionNavegacion app = AplicacionNavegacion.googleMaps,
  }) async {
    for (final uri in enlaces(latitud, longitud, app)) {
      try {
        if (await _abrir(uri)) return;
      } catch (_) {
        // El esquema nativo puede no estar registrado; se intenta el enlace web.
      }
    }
    throw Exception(
      'No se pudo abrir la navegación. Instale Maps/Waze o habilite un navegador.',
    );
  }
}
