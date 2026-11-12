import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../../../shared/utils/ui_engine/widget_modifiers.dart';

import '../../../controllers/mapa_controller.dart';
import '../../../services/tracking_gps_service.dart';
import '../../widgets/visor_datos_bottom_sheet.dart';
import 'bandeja_rutas_pantalla.dart';
import '../../../../auth/models/sesion_usuario.dart';
import '../../../../busqueda/views/screens/flujo_principal/busqueda_pantalla_inicio.dart';
import '../../../../auth/services/auth_service.dart';

class MapaPantallaInicio extends StatefulWidget {
  const MapaPantallaInicio({super.key});

  @override
  State<MapaPantallaInicio> createState() => _MapaPantallaInicioState();
}

class _MapaPantallaInicioState extends State<MapaPantallaInicio> {
  final MapaController controlador = MapaController();
  final MapController mapController = MapController();

  @override
  void initState() {
    super.initState();
    // 1. Iniciar transmisión telemática y solicitar permisos de GPS
    TrackingGpsService().iniciarTransmision();

    // 2. Cargar capas iniciales de San Ignacio de Velasco
    WidgetsBinding.instance.addPostFrameCallback((_) {
      controlador.cargarCapasEnVista(null, (fn) {
        if (mounted) setState(fn);
      }, onFeatureTap: (feature) {
        if (mounted) {
          VisorDatosBottomSheet.mostrar(context, feature);
        }
      });
    });
  }

  Future<void> centrarEnMiUbicacion() async {
    final tracking = TrackingGpsService();
    final exito = await tracking.solicitarPermisosUbicacion();
    if (!mounted) return;
    if (exito) {
      mapController.move(LatLng(tracking.latitud, tracking.longitud), 17);
    } else {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tracking.ultimoError ?? 'No se pudo obtener la ubicación. Reintente.'),
      ));
    }
  }

  void centrarEnCentroCatastral() {
    mapController.move(MapaController.centroSigSanIgnacio, 15.5);
    controlador.cargarCapasEnVista(mapController.camera, (fn) {
      if (mounted) setState(fn);
    });
  }

  void _enfocarElementoSeleccionado(Map<String, dynamic> item) {
    double? lat, lng;
    final bbox = item['bbox'] as List?;
    if (bbox != null && bbox.length == 4) {
      lng = ((bbox[0] as num) + (bbox[2] as num)) / 2;
      lat = ((bbox[1] as num) + (bbox[3] as num)) / 2;
    }
    final props = item['properties'] as Map<String, dynamic>? ?? {};
    lat ??= (props['Latitud'] ?? props['AguaLatitud'] as num?)?.toDouble();
    lng ??= (props['Longitud'] ?? props['AguaLongitud'] as num?)?.toDouble();

    if (lat != null && lng != null) {
      mapController.move(LatLng(lat, lng), 17.5);
    }

    // Abrir el Visor de Datos Catastrales de inmediato con toda la información
    VisorDatosBottomSheet.mostrar(context, item, onCentrar: () {
      if (lat != null && lng != null) {
        mapController.move(LatLng(lat, lng), 18.0);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F3F4),
      body: CustomRebuilder(
        builder: (actualizar) => Stack(
          children: [
            // 1. Mapa Real Leaflet / OSM consumiendo datos SIG
            FlutterMap(
              mapController: mapController,
              options: MapOptions(
                initialCenter: MapaController.centroSigSanIgnacio,
                initialZoom: 15.5,
                onPositionChanged: (camera, hasGesture) {
                  // Cargar si el usuario dejó de mover el mapa
                },
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.arquis.alfa',
                ),
                if (controlador.mostrarManzanas)
                  PolygonLayer(
                    polygons: controlador.poligonosManzanas,
                  ),
                if (controlador.mostrarLotes)
                  PolygonLayer(
                    polygons: controlador.poligonosLotes,
                  ),
                if (controlador.mostrarAgua)
                  MarkerLayer(
                    markers: controlador.marcadoresAgua,
                  ),
              ],
            ),

            // 2. Buscador Flotante Superior (Estilo Google Maps)
            SafeArea(
              child: Align(
                alignment: Alignment.topCenter,
                child: GestureDetector(
                  onTap: () async {
                    final resultado = await Navigator.push(
                      context, 
                      MaterialPageRoute(builder: (context) => const BusquedaPantallaInicio()),
                    );
                    if (resultado is Map<String, dynamic> && mounted) {
                      _enfocarElementoSeleccionado(resultado);
                    }
                  },
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(30),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.15),
                          blurRadius: 10,
                          offset: const Offset(0, 3),
                        )
                      ],
                    ),
                    child: Row(
                      children: [
                        const Icon(Icons.search, color: Color(0xFF1A73E8), size: 24),
                        const SizedBox(width: 12),
                        const Expanded(
                          child: Text(
                            "Buscar por nombre, titular (dueño), código...",
                            style: TextStyle(color: Colors.black54, fontSize: 15),
                          ),
                        ),
                        // Menú de perfil rápido / Cerrar sesión
                        PopupMenuButton<String>(
                          icon: Container(
                            width: 32,
                            height: 32,
                            decoration: const BoxDecoration(
                              color: Color(0xFF1A73E8),
                              shape: BoxShape.circle,
                            ),
                            child: Center(
                              child: Text(
                                (SesionUsuario.actual.value?.nombre ?? "U").substring(0, 1),
                                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                              ),
                            ),
                          ),
                          onSelected: (val) async {
                            if (val == 'logout') {
                              TrackingGpsService().limpiarSesion();
                              try { await AuthService().logout(); } catch (_) {}
                            } else if (val == 'catastro') {
                              centrarEnCentroCatastral();
                            }
                          },
                          itemBuilder: (context) => [
                            const PopupMenuItem(
                              value: 'catastro',
                              child: Row(
                                children: [
                                  Icon(Icons.map, size: 20, color: Color(0xFF1A73E8)),
                                  SizedBox(width: 10),
                                  Text("Centro Catastral"),
                                ],
                              ),
                            ),
                            const PopupMenuItem(
                              value: 'logout',
                              child: Row(
                                children: [
                                  Icon(Icons.logout, size: 20, color: Colors.red),
                                  SizedBox(width: 10),
                                  Text("Cerrar Sesión"),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),

            // 3. Botones Flotantes Laterales (Acciones y Capas)
            Positioned(
              right: 16,
              top: 100,
              child: Column(
                children: [
                  _GoogleMapFab(
                    icon: Icons.layers,
                    tooltip: 'Recargar sector',
                    onTap: () {
                      controlador.cargarCapasEnVista(mapController.camera, actualizar, onFeatureTap: (feature) {
                        VisorDatosBottomSheet.mostrar(context, feature);
                      });
                    },
                  ),
                  const SizedBox(height: 12),
                  _GoogleMapFab(
                    icon: Icons.location_city,
                    tooltip: 'Centrar en San Ignacio (SIG)',
                    onTap: centrarEnCentroCatastral,
                  ),
                  const SizedBox(height: 12),
                  _GoogleMapFab(
                    icon: Icons.my_location,
                    tooltip: 'Mi ubicación GPS',
                    onTap: centrarEnMiUbicacion,
                  ),
                ],
              ),
            ),

            // 4. Panel Inferior de Capas Interactivas
            Align(
              alignment: Alignment.bottomCenter,
              child: Container(
                margin: const EdgeInsets.all(16),
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.15),
                      blurRadius: 15,
                      offset: const Offset(0, 5),
                    )
                  ],
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Row(
                      children: [
                        const Text(
                          "Capas Territoriales SIG",
                          style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16, color: Color(0xFF202124)),
                        ),
                        const Spacer(),
                        if (controlador.isCargando)
                          const SizedBox(
                            height: 18,
                            width: 18,
                            child: CircularProgressIndicator(color: Color(0xFF1A73E8), strokeWidth: 2),
                          ),
                      ],
                    ),
                    const SizedBox(height: 12),
                    if (controlador.errorMensaje != null)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 8.0),
                        child: Text(
                          controlador.errorMensaje!,
                          style: const TextStyle(color: Colors.red, fontSize: 12),
                        ),
                      ),

                    // Fila de Capas
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _LayerOption(
                          title: "Manzanas",
                          icon: Icons.crop_square,
                          isActive: controlador.mostrarManzanas,
                          activeColor: const Color(0xFFDC2626),
                          onTap: () {
                            actualizar(() {
                              controlador.mostrarManzanas = !controlador.mostrarManzanas;
                            });
                            controlador.cargarCapasEnVista(mapController.camera, actualizar);
                          },
                        ),
                        _LayerOption(
                          title: "Lotes",
                          icon: Icons.grid_view,
                          isActive: controlador.mostrarLotes,
                          activeColor: const Color(0xFF0284C7),
                          onTap: () {
                            actualizar(() {
                              controlador.mostrarLotes = !controlador.mostrarLotes;
                            });
                            controlador.cargarCapasEnVista(mapController.camera, actualizar);
                          },
                        ),
                        _LayerOption(
                          title: "Agua",
                          icon: Icons.water_drop,
                          isActive: controlador.mostrarAgua,
                          activeColor: const Color(0xFF1A73E8),
                          onTap: () {
                            actualizar(() {
                              controlador.mostrarAgua = !controlador.mostrarAgua;
                            });
                            controlador.cargarCapasEnVista(mapController.camera, actualizar);
                          },
                        ),
                        _LayerOption(
                          title: "Rutas",
                          icon: Icons.alt_route,
                          isActive: true,
                          activeColor: const Color(0xFF1A73E8),
                          onTap: () {
                            Navigator.push(
                              context, 
                              MaterialPageRoute(builder: (context) => const BandejaRutasPantalla()),
                            );
                          },
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GoogleMapFab extends StatelessWidget {
  final IconData icon;
  final VoidCallback onTap;
  final String? tooltip;

  const _GoogleMapFab({required this.icon, required this.onTap, this.tooltip});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Tooltip(
        message: tooltip ?? '',
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.white,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.18),
                blurRadius: 6,
                offset: const Offset(0, 3),
              )
            ],
          ),
          child: Icon(icon, color: const Color(0xFF3C4043), size: 24),
        ),
      ),
    );
  }
}

class _LayerOption extends StatelessWidget {
  final String title;
  final IconData icon;
  final bool isActive;
  final Color activeColor;
  final VoidCallback onTap;

  const _LayerOption({
    required this.title,
    required this.icon,
    required this.isActive,
    this.activeColor = const Color(0xFF1A73E8),
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: isActive ? activeColor.withValues(alpha: 0.12) : Colors.grey.withValues(alpha: 0.08),
              shape: BoxShape.circle,
              border: Border.all(
                color: isActive ? activeColor : Colors.transparent,
                width: 2,
              ),
            ),
            child: Icon(
              icon, 
              color: isActive ? activeColor : Colors.black54,
              size: 26,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            title,
            style: TextStyle(
              fontSize: 12, 
              fontWeight: isActive ? FontWeight.w600 : FontWeight.normal,
              color: isActive ? activeColor : const Color(0xFF3C4043),
            ),
          ),
        ],
      ),
    );
  }
}
