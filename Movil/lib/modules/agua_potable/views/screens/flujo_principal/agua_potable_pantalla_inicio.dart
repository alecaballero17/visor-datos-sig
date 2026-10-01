import 'package:flutter/material.dart';
import '../../../../../shared/utils/ui_engine/ui_screen.dart';
import '../../../../../shared/utils/ui_engine/widget_modifiers.dart';
import '../../../../../shared/utils/ui_engine/list_modifiers.dart';
import '../../../../../shared/utils/ui_engine/string_modifiers.dart';
import '../../../../../shared/utils/ui_engine/icon_modifiers.dart';

class AguaPotablePantallaInicio extends StatelessWidget {
  const AguaPotablePantallaInicio({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      // AppBar limpia y blanca, típica de detalles de Google Maps
      appBar: AppBar(
        backgroundColor: Colors.white,
        foregroundColor: Colors.black87,
        elevation: 0,
        actions: [
          IconButton(icon: const Icon(Icons.share, color: Colors.black87), onPressed: () {}),
          IconButton(icon: const Icon(Icons.star_border, color: Colors.black87), onPressed: () {}),
        ],
      ),
      body: SingleChildScrollView(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Cabecera de la ficha (Foto o mapa genérico)
            Container(
              height: 200,
              width: double.infinity,
              color: Colors.grey.shade200,
              child: Stack(
                alignment: Alignment.center,
                children: [
                  const Icon(Icons.map, size: 80, color: Colors.black12),
                  Positioned(
                    bottom: 10,
                    right: 10,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black54,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: "Street View".texto(color: Colors.white, size: 12),
                    ),
                  ),
                ],
              ),
            ),
            
            Padding(
              padding: const EdgeInsets.all(20.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Título grande
                  "Lote #84920 - Agua Potable".texto(
                    size: 24, 
                    color: Colors.black87,
                    negrita: true,
                  ),
                  const SizedBox(height: 8),
                  
                  // Resumen
                  Row(
                    children: [
                      "4.8".texto(color: Colors.black54),
                      const SizedBox(width: 4),
                      Row(
                        children: List.generate(5, (index) => 
                          Icon(Icons.star, size: 16, color: index < 4 ? Colors.amber : Colors.grey.shade300)
                        ),
                      ),
                      const SizedBox(width: 8),
                      "(12 inspecciones)".texto(color: Colors.blue),
                    ],
                  ),
                  const SizedBox(height: 8),
                  "Servicio Activo · Infraestructura urbana".texto(color: Colors.black54),
                  
                  const SizedBox(height: 20),
                  
                  // Botones de acción rápida estilo Google Maps
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                    children: [
                      _buildQuickAction(Icons.directions, "Cómo llegar", const Color(0xFF1A73E8)),
                      _buildQuickAction(Icons.bookmark_border, "Guardar", const Color(0xFF1A73E8)),
                      _buildQuickAction(Icons.build, "Inspeccionar", const Color(0xFF1A73E8)),
                      _buildQuickAction(Icons.download, "Descargar", const Color(0xFF1A73E8)),
                    ],
                  ),
                  
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 20.0),
                    child: Divider(),
                  ),
                  
                  // Filas de información con iconos
                  _buildInfoRow(Icons.location_on, "Sector Norte, Manzana 14"),
                  _buildInfoRow(Icons.water_drop, "Toma de 1/2 Pulgada - Presión 45 PSI"),
                  _buildInfoRow(Icons.access_time, "Última inspección: Hace 2 meses"),
                  _buildInfoRow(Icons.check_circle, "Estado del medidor operativo"),
                  _buildInfoRow(Icons.edit, "Sugerir una modificación", isLink: true),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildQuickAction(IconData icon, String label, Color color) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: Colors.blue.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: color),
        ),
        const SizedBox(height: 8),
        label.texto(color: color, size: 12),
      ],
    );
  }

  Widget _buildInfoRow(IconData icon, String text, {bool isLink = false}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 24.0),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: const Color(0xFF1A73E8), size: 24),
          const SizedBox(width: 20),
          Expanded(
            child: text.texto(
              color: isLink ? const Color(0xFF1A73E8) : Colors.black87, 
              size: 15,
              negrita: isLink
            ),
          ),
        ],
      ),
    );
  }
}
