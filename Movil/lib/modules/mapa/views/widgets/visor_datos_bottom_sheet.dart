import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../../../../core/network/api_provider.dart';
import '../screens/flujo_principal/navegacion_campo_pantalla.dart';

class VisorDatosBottomSheet extends StatefulWidget {
  final Map<String, dynamic> feature;
  final VoidCallback? onCentrar;

  const VisorDatosBottomSheet({
    super.key,
    required this.feature,
    this.onCentrar,
  });

  static void mostrar(BuildContext context, Map<String, dynamic> feature, {VoidCallback? onCentrar}) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => VisorDatosBottomSheet(
        feature: feature,
        onCentrar: onCentrar,
      ),
    );
  }

  @override
  State<VisorDatosBottomSheet> createState() => _VisorDatosBottomSheetState();
}

class _VisorDatosBottomSheetState extends State<VisorDatosBottomSheet> {
  final ApiProvider _api = ApiProvider();
  bool _cargandoFicha = false;
  Map<String, dynamic>? _fichaAgua;

  @override
  void initState() {
    super.initState();
    _cargarFichaCompleta();
  }

  Future<void> _cargarFichaCompleta() async {
    final layer = (widget.feature['layer'] ?? widget.feature['capa'] ?? '').toString().toLowerCase();
    final id = widget.feature['id'] ?? widget.feature['properties']?['IdCodigo'] ?? widget.feature['properties']?['IdLote'];

    if (id == null) return;

    setState(() => _cargandoFicha = true);
    try {
      if (layer == 'codigosfijos' || widget.feature['properties']?['IdCodigo'] != null) {
        final res = await _api.get('/agua-potable/codigos/$id');
        if (res is Map<String, dynamic> && mounted) {
          setState(() => _fichaAgua = res);
        }
      } else if (layer == 'lotes' || widget.feature['properties']?['IdLote'] != null) {
        final res = await _api.get('/agua-potable/lotes/$id');
        if (res is Map<String, dynamic> && mounted) {
          setState(() => _fichaAgua = res);
        }
      }
    } catch (_) {
      // Usar datos locales de la feature si falla
    } finally {
      if (mounted) setState(() => _cargandoFicha = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final props = widget.feature['properties'] as Map<String, dynamic>? ?? {};
    final layer = (widget.feature['layer'] ?? widget.feature['capa'] ?? 'Predio').toString().toLowerCase();
    
    // Extracción de datos normalizada
    final rawTitular = _fichaAgua?['nombreRegistrado'] ?? props['Titular'] ?? props['Dueno'] ?? props['Nombre'];
    final titular = (rawTitular != null && rawTitular.toString().trim().isNotEmpty && rawTitular != 'Sin titular vinculado')
        ? rawTitular.toString()
        : 'Sin titular registrado';
    final codigoFijo = _fichaAgua?['codigoFijo'] ?? props['CodFijo'] ?? props['CodF_SIG'] ?? props['CodigoSuministro'] ?? 'S/N';
    final codigoSig = _fichaAgua?['codigoSig'] ?? props['CodF_SIG'] ?? '';
    final uv = _fichaAgua?['uv'] ?? props['UV'] ?? props['uv'] ?? 'S/N';
    final mza = _fichaAgua?['manzana'] ?? props['MZA'] ?? props['mza'] ?? 'S/N';
    final nroLote = _fichaAgua?['numeroLote'] ?? props['NroLote'] ?? props['nroLote'] ?? props['Lote'] ?? 'S/N';
    
    final tieneAgua = _fichaAgua?['tieneAgua'] ?? props['TieneAgua'] == true || props['Estado'] == 1;
    final estadoTexto = tieneAgua ? 'Servicio Activo' : 'Corte / Suspendido';

    double? lat, lng;
    final geom = widget.feature['geometry'] as Map<String, dynamic>?;
    if (geom != null && geom['coordinates'] is List) {
      final c = geom['coordinates'] as List;
      if (geom['type'] == 'Point' && c.length >= 2) {
        lng = (c[0] as num).toDouble();
        lat = (c[1] as num).toDouble();
      }
    }
    lat ??= (_fichaAgua?['latitud'] ?? props['Latitud'] ?? props['AguaLatitud'] as num?)?.toDouble();
    lng ??= (_fichaAgua?['longitud'] ?? props['Longitud'] ?? props['AguaLongitud'] as num?)?.toDouble();

    return Container(
      constraints: BoxConstraints(
        maxHeight: MediaQuery.of(context).size.height * 0.82,
      ),
      decoration: const BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: SafeArea(
        top: false,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Tirador superior del Bottom Sheet
            Center(
              child: Container(
                margin: const EdgeInsets.only(top: 10, bottom: 8),
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey.shade300,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),

            // Encabezado del visor de datos
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: tieneAgua ? const Color(0xFFE8F0FE) : const Color(0xFFFCE8E6),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      tieneAgua ? Icons.water_drop : Icons.water_drop_outlined,
                      color: tieneAgua ? const Color(0xFF1A73E8) : const Color(0xFFD93025),
                      size: 26,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: tieneAgua ? const Color(0xFFE6F4EA) : const Color(0xFFFCE8E6),
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                estadoTexto,
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: tieneAgua ? const Color(0xFF137333) : const Color(0xFFC5221F),
                                ),
                              ),
                            ),
                            const Spacer(),
                            if (_cargandoFicha)
                              const SizedBox(
                                width: 14,
                                height: 14,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF1A73E8)),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          codigoFijo != 'S/N' ? 'Código: $codigoFijo' : 'Predio Lote $nroLote',
                          style: const TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: Color(0xFF202124),
                          ),
                        ),
                        const SizedBox(height: 2),
                        Row(
                          children: [
                            const Icon(Icons.person, size: 15, color: Color(0xFF1A73E8)),
                            const SizedBox(width: 4),
                            Expanded(
                              child: Text(
                                'Titular: $titular',
                                style: const TextStyle(fontSize: 14, color: Color(0xFF3C4043), fontWeight: FontWeight.w600),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                  IconButton(
                    icon: const Icon(Icons.close, color: Color(0xFF5F6368)),
                    onPressed: () => Navigator.pop(context),
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Acciones rápidas (Estilo Google Maps)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  _buildActionButton(
                    icon: Icons.directions,
                    label: 'Cómo llegar',
                    color: const Color(0xFF1A73E8),
                    onTap: () {
                      if (lat != null && lng != null) {
                        Navigator.pop(context);
                        Navigator.push(
                          context,
                          MaterialPageRoute(
                            builder: (context) => NavegacionCampoPantalla(
                              rutaInicial: {
                                'latitud': lat,
                                'longitud': lng,
                                'titulo': '$codigoFijo · $titular',
                                'direccion': 'UV $uv - MZA $mza - Lote $nroLote',
                              },
                            ),
                          ),
                        );
                      }
                    },
                  ),
                  _buildActionButton(
                    icon: Icons.center_focus_strong,
                    label: 'Centrar Mapa',
                    color: const Color(0xFF1A73E8),
                    onTap: () {
                      Navigator.pop(context);
                      widget.onCentrar?.call();
                    },
                  ),
                  _buildActionButton(
                    icon: Icons.content_copy,
                    label: 'Copiar GPS',
                    color: const Color(0xFF5F6368),
                    onTap: () {
                      if (lat != null && lng != null) {
                        Clipboard.setData(ClipboardData(text: '$lat, $lng'));
                        ScaffoldMessenger.of(context).showSnackBar(
                          const SnackBar(content: Text('Coordenadas copiadas al portapapeles.')),
                        );
                      }
                    },
                  ),
                ],
              ),
            ),

            const Divider(height: 1),

            // Contenido con ficha técnica y atributos catastrales
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'DATOS CATASTRALES Y TERRITORIALES',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                        color: Color(0xFF5F6368),
                      ),
                    ),
                    const SizedBox(height: 12),

                    _buildInfoRow('Titular (Dueño)', titular.toString(), isHighlighted: true),
                    _buildInfoRow('Capa', layer.toUpperCase()),
                    _buildInfoRow('Unidad Vecinal (UV)', 'UV $uv'),
                    _buildInfoRow('Manzana (MZA)', 'MZA $mza'),
                    _buildInfoRow('Lote / Terreno', 'Lote $nroLote'),
                    if (codigoSig.toString().isNotEmpty)
                      _buildInfoRow('Código SIG', codigoSig.toString()),
                    if (lat != null && lng != null)
                      _buildInfoRow('Coordenadas GPS', '${lat.toStringAsFixed(6)}, ${lng.toStringAsFixed(6)}'),

                    const SizedBox(height: 16),
                    const Text(
                      'INFORMACIÓN DE SUMINISTRO Y RED',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 0.8,
                        color: Color(0xFF5F6368),
                      ),
                    ),
                    const SizedBox(height: 12),

                    _buildInfoRow('Estado del Agua', estadoTexto, isHighlighted: true, highlightColor: tieneAgua ? const Color(0xFF137333) : const Color(0xFFC5221F)),
                    _buildInfoRow('Criterio Técnico', tieneAgua ? 'Conexión activa a la red' : 'Sin servicio registrado'),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionButton({
    required IconData icon,
    required String label,
    required Color color,
    required VoidCallback onTap,
  }) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 22),
            ),
            const SizedBox(height: 6),
            Text(
              label,
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500, color: color),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildInfoRow(String label, String value, {bool isHighlighted = false, Color? highlightColor}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 150,
            child: Text(
              label,
              style: const TextStyle(fontSize: 13, color: Color(0xFF5F6368)),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: TextStyle(
                fontSize: 13,
                fontWeight: isHighlighted ? FontWeight.bold : FontWeight.w500,
                color: isHighlighted ? highlightColor : const Color(0xFF202124),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
