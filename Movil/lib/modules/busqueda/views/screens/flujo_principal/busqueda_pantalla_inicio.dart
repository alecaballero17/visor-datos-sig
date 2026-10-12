import 'package:flutter/material.dart';
import '../../../../../shared/utils/ui_engine/widget_modifiers.dart';
import '../../../../../shared/utils/ui_engine/string_modifiers.dart';
import '../../../controllers/busqueda_controller.dart';

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
              // Barra de búsqueda integrada estilo Google Maps
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withValues(alpha: 0.06),
                      blurRadius: 4,
                      offset: const Offset(0, 2),
                    )
                  ],
                ),
                child: Row(
                  children: [
                    IconButton(
                      icon: const Icon(Icons.arrow_back, color: Colors.black87),
                      onPressed: () => Navigator.pop(context),
                    ),
                    Expanded(
                      child: TextField(
                        controller: controlador.searchCtrl,
                        autofocus: true,
                        style: const TextStyle(fontSize: 16),
                        decoration: const InputDecoration(
                          hintText: "Buscar por nombre, titular (dueño), código, lote...",
                          hintStyle: TextStyle(color: Colors.black38, fontSize: 14),
                          border: InputBorder.none,
                        ),
                        onChanged: (val) {
                          Future.delayed(const Duration(milliseconds: 350), () {
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

              // Chips de filtro por capa
              Container(
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8F9FA),
                  border: Border(bottom: BorderSide(color: Colors.grey.shade200)),
                ),
                child: ListView(
                  scrollDirection: Axis.horizontal,
                  children: [
                    _buildFilterChip('Todas', '', actualizar),
                    const SizedBox(width: 6),
                    _buildFilterChip('Códigos Fijos', 'codigosfijos', actualizar),
                    const SizedBox(width: 6),
                    _buildFilterChip('Manzanas', 'manzanas', actualizar),
                    const SizedBox(width: 6),
                    _buildFilterChip('Lotes', 'lotes', actualizar),
                    const SizedBox(width: 6),
                    _buildFilterChip('Vías', 'vias', actualizar),
                  ],
                ),
              ),
              
              if (controlador.isCargando)
                const LinearProgressIndicator(color: Color(0xFF1A73E8), minHeight: 2),

              if (controlador.errorMessage != null && !controlador.isCargando)
                Padding(
                  padding: const EdgeInsets.all(20.0),
                  child: Column(
                    children: [
                      Icon(Icons.info_outline, color: Colors.grey.shade400, size: 36),
                      const SizedBox(height: 8),
                      Text(
                        controlador.errorMessage!,
                        textAlign: TextAlign.center,
                        style: TextStyle(color: Colors.grey.shade600, fontSize: 14),
                      ),
                    ],
                  ),
                ),

              // Lista de resultados enriquecida
              Expanded(
                child: ListView.separated(
                  itemCount: controlador.resultados.length,
                  separatorBuilder: (_, _) => Divider(height: 1, color: Colors.grey.shade100),
                  itemBuilder: (context, index) {
                    final item = controlador.resultados[index] as Map<String, dynamic>;
                    final layer = (item['layer'] ?? item['capa'] ?? '').toString().toLowerCase();
                    final label = (item['label'] ?? item['texto'] ?? 'Elemento SIG').toString();
                    final props = item['properties'] as Map<String, dynamic>? ?? {};
                    
                    IconData icon = Icons.location_on;
                    Color iconColor = const Color(0xFF1A73E8);
                    String layerLabel = 'Capa Cartográfica';

                    if (layer == 'manzanas') {
                      icon = Icons.crop_square;
                      iconColor = const Color(0xFFDC2626);
                      layerLabel = 'Manzana Urbana';
                    } else if (layer == 'lotes') {
                      icon = Icons.grid_view;
                      iconColor = const Color(0xFF0284C7);
                      layerLabel = 'Lote / Predio';
                    } else if (layer == 'codigosfijos') {
                      icon = Icons.water_drop;
                      iconColor = const Color(0xFFD97706);
                      layerLabel = 'Cuenta de Agua Potable';
                    } else if (layer == 'vias') {
                      icon = Icons.alt_route;
                      iconColor = const Color(0xFF7C3AED);
                      layerLabel = 'Vía / Calle';
                    }

                    final titular = (props['Titular'] ?? props['Dueno'] ?? props['Nombre'] ?? props['nombreRegistrado'])?.toString();
                    final codFijo = props['CodFijo'] ?? props['codigoFijo'];
                    final nroLote = props['NroLote'] ?? props['numeroLote'];
                    final uv = props['UV'] ?? props['uv'];
                    final mza = props['MZA'] ?? props['manzana'];

                    return InkWell(
                      onTap: () {
                        // Retornar el elemento seleccionado a la pantalla de mapa para centrar y abrir visor
                        Navigator.pop(context, item);
                      },
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.center,
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: iconColor.withValues(alpha: 0.1),
                                shape: BoxShape.circle,
                              ),
                              child: Icon(icon, color: iconColor, size: 20),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    label,
                                    style: const TextStyle(
                                      color: Color(0xFF202124),
                                      fontSize: 15,
                                      fontWeight: FontWeight.w600,
                                    ),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                  ),
                                  const SizedBox(height: 3),
                                  // Titular / Dueño visible claramente en el buscador
                                  if (titular != null && titular.trim().isNotEmpty && titular != 'Sin titular vinculado') ...[
                                    Row(
                                      children: [
                                        const Icon(Icons.person, size: 14, color: Color(0xFF1A73E8)),
                                        const SizedBox(width: 4),
                                        Expanded(
                                          child: RichText(
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            text: TextSpan(
                                              children: [
                                                const TextSpan(
                                                  text: 'Titular: ',
                                                  style: TextStyle(
                                                    fontSize: 13,
                                                    fontWeight: FontWeight.w600,
                                                    color: Color(0xFF3C4043),
                                                  ),
                                                ),
                                                TextSpan(
                                                  text: titular,
                                                  style: const TextStyle(
                                                    fontSize: 13,
                                                    fontWeight: FontWeight.bold,
                                                    color: Color(0xFF1A73E8),
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                  ] else if (layer == 'lotes' || layer == 'codigosfijos') ...[
                                    Row(
                                      children: [
                                        Icon(Icons.person_outline, size: 14, color: Colors.grey.shade500),
                                        const SizedBox(width: 4),
                                        Text(
                                          'Titular: Sin titular registrado',
                                          style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontStyle: FontStyle.italic),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                  ],
                                  // Etiquetas con Capa, Código, Lote, UV, MZA
                                  Wrap(
                                    spacing: 6,
                                    runSpacing: 3,
                                    crossAxisAlignment: WrapCrossAlignment.center,
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                        decoration: BoxDecoration(
                                          color: iconColor.withValues(alpha: 0.1),
                                          borderRadius: BorderRadius.circular(4),
                                        ),
                                        child: Text(
                                          layerLabel,
                                          style: TextStyle(color: iconColor, fontSize: 11, fontWeight: FontWeight.w600),
                                        ),
                                      ),
                                      if (codFijo != null)
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: Colors.amber.shade50,
                                            borderRadius: BorderRadius.circular(4),
                                            border: Border.all(color: Colors.amber.shade200, width: 0.8),
                                          ),
                                          child: Text(
                                            'Cód: $codFijo',
                                            style: TextStyle(fontSize: 11, color: Colors.amber.shade900, fontWeight: FontWeight.w600),
                                          ),
                                        ),
                                      if (nroLote != null)
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: Colors.blue.shade50,
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            'Lote $nroLote',
                                            style: TextStyle(fontSize: 11, color: Colors.blue.shade800, fontWeight: FontWeight.w500),
                                          ),
                                        ),
                                      if (uv != null && uv.toString().isNotEmpty)
                                        Text('UV $uv', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                                      if (mza != null && mza.toString().isNotEmpty)
                                        Text('MZA $mza', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                                    ],
                                  ),
                                ],
                              ),
                            ),
                            const Icon(Icons.north_west, color: Colors.black26, size: 18),
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

  Widget _buildFilterChip(String label, String value, Function(VoidCallback) actualizar) {
    final isSelected = controlador.capaFiltro == value;
    return GestureDetector(
      onTap: () => controlador.cambiarCapaFiltro(value, actualizar),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: isSelected ? const Color(0xFF1A73E8) : Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: isSelected ? const Color(0xFF1A73E8) : Colors.grey.shade300,
          ),
        ),
        child: Center(
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.normal,
              color: isSelected ? Colors.white : Colors.black87,
            ),
          ),
        ),
      ),
    );
  }
}
