import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import '../../../../../shared/utils/ui_engine/ui_screen.dart';
import '../../../../../shared/utils/ui_engine/widget_modifiers.dart';
import '../../../../../shared/utils/ui_engine/list_modifiers.dart';
import '../../../../../shared/utils/ui_engine/string_modifiers.dart';
import '../../../../../shared/utils/ui_engine/icon_modifiers.dart';

import '../../../controllers/mapa_controller.dart';
import '../../../../busqueda/views/screens/flujo_principal/busqueda_pantalla_inicio.dart';
import '../../../../agua_potable/views/screens/flujo_principal/agua_potable_pantalla_inicio.dart';
import '../../../../auth/services/auth_service.dart';
import '../../../../auth/views/screens/flujo_principal/auth_pantalla_inicio.dart';

class MapaPantallaInicio extends StatefulWidget {
  const MapaPantallaInicio({super.key});

  @override
  State<MapaPantallaInicio> createState() => _MapaPantallaInicioState();
}

class _MapaPantallaInicioState extends State<MapaPantallaInicio> {
  static final MapaController controlador = MapaController();
  final MapController mapController = MapController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F3F4), // Gris muy claro típico de fondo
      body: CustomRebuilder(
        builder: (actualizar) => Stack(
          children: [
            // 1. Mapa Real consumiendo datos (Ocupa todo el fondo)
            FlutterMap(
              mapController: mapController,
              options: MapOptions(
                initialCenter: const LatLng(-17.78, -63.18),
                initialZoom: 16.0,
                onPositionChanged: (camera, hasGesture) {},
              ),
              children: [
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'com.arquis.alfa',
                ),
                if (controlador.mostrarLotes)
                  PolygonLayer(
                    polygons: controlador.poligonosLotes,
                  ),
                if (controlador.mostrarManzanas)
                  PolygonLayer(
                    polygons: controlador.poligonosManzanas,
                  ),
              ],
            ),

            // 2. Panel Flotante Superior (Búsqueda Estilo Google Maps)
            SafeArea(
              child: Align(
                alignment: Alignment.topCenter,
                child: GestureDetector(
                  onTap: () {
                    Navigator.push(
                      context, 
                      MaterialPageRoute(builder: (context) => const BusquedaPantallaInicio())
                    );
                  },
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(30),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.15),
                        blurRadius: 10,
                        offset: const Offset(0, 3),
                      )
                    ],
                  ),
                  child: Row(
                    children: [
                      Icons.menu.icono(color: Colors.black54, size: 28),
                      const SizedBox(width: 15),
                      Expanded(
                        child: "Buscar en Arquis".texto(
                          color: Colors.black54, 
                          size: 16,
                        ),
                      ),
                      Icons.mic.icono(color: Colors.black54, size: 24),
                      const SizedBox(width: 15),
                      GestureDetector(
                        onTap: () async {
                          await AuthService().logout();
                          if (context.mounted) {
                            Navigator.pushReplacement(
                              context, 
                              MaterialPageRoute(builder: (context) => const AuthPantallaInicio())
                            );
                          }
                        },
                        child: const CircleAvatar(
                          radius: 16,
                          backgroundColor: Colors.blue,
                          child: Icon(Icons.logout, color: Colors.white, size: 16),
                        ),
                      ),
                    ],
                  ),
                ),
                ),
              ),
            ),

            // 3. Botones Flotantes Laterales (Material Design)
            Positioned(
              right: 16,
              top: 100,
              child: Column(
                children: [
                  _GoogleMapFab(
                    icon: Icons.layers,
                    onTap: () {},
                  ),
                  const SizedBox(height: 16),
                  _GoogleMapFab(
                    icon: Icons.my_location,
                    onTap: () {},
                  ),
                  const SizedBox(height: 16),
                  _GoogleMapFab(
                    icon: Icons.sync,
                    onTap: () {
                      controlador.cargarManzanasEnVista(mapController.camera, actualizar);
                    },
                  ),
                ],
              ),
            ),

            // 4. Panel Inferior (Estilo Bottom Sheet)
            Align(
              alignment: Alignment.bottomCenter,
              child: Container(
                margin: const EdgeInsets.all(16),
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.15),
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
                        "Explorar Capas".texto(negrita: true, size: 20, color: Colors.black87),
                        const Spacer(),
                        if (controlador.isCargando)
                          const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(color: Colors.blue, strokeWidth: 2),
                          ),
                      ],
                    ),
                    const SizedBox(height: 15),
                    if (controlador.errorMensaje != null)
                      controlador.errorMensaje!.texto(color: Colors.red, size: 14).padSolo(b: 10),

                    // Fila de Capas
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _LayerOption(
                          title: "Manzanas",
                          icon: Icons.business,
                          isActive: controlador.mostrarManzanas,
                          onTap: () {
                            actualizar(() {
                              controlador.mostrarManzanas = !controlador.mostrarManzanas;
                            });
                          },
                        ),
                        _LayerOption(
                          title: "Lotes",
                          icon: Icons.grid_view,
                          isActive: controlador.mostrarLotes,
                          onTap: () {
                            actualizar(() {
                              controlador.mostrarLotes = !controlador.mostrarLotes;
                            });
                            controlador.cargarManzanasEnVista(mapController.camera, actualizar);
                          },
                        ),
                        _LayerOption(
                          title: "Agua",
                          icon: Icons.water_drop,
                          isActive: false,
                          onTap: () {
                            Navigator.push(
                              context, 
                              MaterialPageRoute(builder: (context) => const AguaPotablePantallaInicio())
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

  const _GoogleMapFab({required this.icon, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white,
          shape: BoxShape.circle,
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.2),
              blurRadius: 6,
              offset: const Offset(0, 3),
            )
          ],
        ),
        child: Icon(icon, color: Colors.black87, size: 26),
      ),
    );
  }
}

class _LayerOption extends StatelessWidget {
  final String title;
  final IconData icon;
  final bool isActive;
  final VoidCallback onTap;

  const _LayerOption({
    required this.title,
    required this.icon,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: isActive ? Colors.blue.withOpacity(0.1) : Colors.grey.withOpacity(0.1),
              shape: BoxShape.circle,
              border: Border.all(
                color: isActive ? Colors.blue : Colors.transparent,
                width: 2,
              ),
            ),
            child: Icon(
              icon, 
              color: isActive ? Colors.blue : Colors.black54,
              size: 28,
            ),
          ),
          const SizedBox(height: 8),
          title.texto(
            size: 13, 
            color: isActive ? Colors.blue : Colors.black87,
            negrita: isActive,
          ),
        ],
      ),
    );
  }
}
