import 'package:flutter/material.dart';
import '../../../../../shared/utils/ui_engine/ui_screen.dart';
import '../../../../../shared/utils/ui_engine/widget_modifiers.dart';
import '../../../../../shared/utils/ui_engine/string_modifiers.dart';
import '../../../../../shared/utils/ui_engine/icon_modifiers.dart';
import '../../controllers/busqueda_controller.dart';
import '../../../../agua_potable/views/screens/flujo_principal/agua_potable_pantalla_inicio.dart';

class BusquedaPantallaInicio extends StatefulWidget {
  const BusquedaPantallaInicio({super.key});

  @override
  State<BusquedaPantallaInicio> createState() => _BusquedaPantallaInicioState();
}

class _BusquedaPantallaInicioState extends State<BusquedaPantallaInicio> {
  final BusquedaController controlador = BusquedaController();

  @override
  void dispose() {
    controlador.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: CustomRebuilder(
          builder: (actualizar) => Column(
            children: [
              // AppBar integrado tipo Google Maps
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.05),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    )
                  ],
                ),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back, color: Colors.black54),
                      onPressed: () => Navigator.pop(context),
                    ),
                    Expanded(
                      child: TextField(
                        controller: controlador.searchCtrl,
                        autofocus: true,
                        style: const TextStyle(fontSize: 16),
                        decoration: const InputDecoration(
                          hintText: "Buscar código, manzana, lote o vía",
                          hintStyle: TextStyle(color: Colors.black38),
                          border: InputBorder.none,
                        ),
                        onChanged: (val) {
                          // Simple debounce manual
                          Future.delayed(const Duration(milliseconds: 500), () {
                            if (controlador.searchCtrl.text == val) {
                              controlador.buscar(val, actualizar);
                            }
                          });
                        },
                      ),
                    ),
                    if (controlador.searchCtrl.text.isNotEmpty)
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.black54),
                        onPressed: () {
                          controlador.searchCtrl.clear();
                          controlador.buscar('', actualizar);
                        },
                      ),
                  ],
                ),
              ),
              
              if (controlador.isCargando)
                const LinearProgressIndicator(color: Color(0xFF1A73E8)),

              if (controlador.errorMessage != null)
                Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: controlador.errorMessage!.texto(color: Colors.red),
                ),

              // Resultados
              Expanded(
                child: ListView.builder(
                  itemCount: controlador.resultados.length,
                  itemBuilder: (context, index) {
                    final item = controlador.resultados[index];
                    final layer = item['layer'];
                    final label = item['label'];
                    
                    IconData icon = Icons.location_on;
                    if (layer == 'manzanas') icon = Icons.crop_square;
                    if (layer == 'lotes') icon = Icons.grid_view;
                    if (layer == 'codigosfijos') icon = Icons.water_drop;

                    return InkWell(
                      onTap: () {
                        // Si es lote o codigos fijos, podríamos abrir la pantalla de Agua
                        if (layer == 'lotes' || layer == 'codigosfijos') {
                           Navigator.push(
                            context,
                            MaterialPageRoute(builder: (context) => const AguaPotablePantallaInicio()),
                          );
                        } else {
                           Navigator.pop(context); // Solo vuelve al mapa por ahora
                        }
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.grey.shade100,
                                shape: BoxShape.circle,
                              ),
                              child: Icon(icon, color: Colors.black54, size: 20),
                            ),
                            const SizedBox(width: 16),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  label.toString().texto(color: Colors.black87, size: 16),
                                  const SizedBox(height: 2),
                                  "Capa: $layer".texto(color: Colors.black54, size: 13),
                                ],
                              ),
                            ),
                            const Icon(Icons.north_west, color: Colors.black26, size: 20),
                          ],
                        ),
                      ),
                    );
                  },
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
