import 'dart:io';
import '../../models/secuencia_atencion.dart';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../../services/rutas_trabajo_service.dart';
import '../../services/tracking_gps_service.dart';

/// Modal completo de Cierre de Orden Operativa (RF-MOB-04 & RF-MOB-05)
/// Integra:
/// 1. Selector Cortado/Reconectado vs Observado (con motivos predefinidos)
/// 2. Campo numérico para Lectura del Medidor
/// 3. Captura de 1–3 fotografías de cámara
/// 4. Validación geográfica y temporal antifraude (RN-01, radio de 30 m)
class FormularioCierreOrdenModal extends StatefulWidget {
  final Map<String, dynamic> rutaActiva;
  final Map<String, dynamic> objetivoActual;
  final Function(String estadoFinal)? onCompletadoExitoso;

  const FormularioCierreOrdenModal({
    super.key,
    required this.rutaActiva,
    required this.objetivoActual,
    this.onCompletadoExitoso,
  });

  static Future<bool?> mostrar({
    required BuildContext context,
    required Map<String, dynamic> rutaActiva,
    required Map<String, dynamic> objetivoActual,
    Function(String estadoFinal)? onCompletadoExitoso,
  }) {
    return showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      isDismissible: false,
      enableDrag: false,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: FormularioCierreOrdenModal(
          rutaActiva: rutaActiva,
          objetivoActual: objetivoActual,
          onCompletadoExitoso: onCompletadoExitoso,
        ),
      ),
    );
  }

  @override
  State<FormularioCierreOrdenModal> createState() => _FormularioCierreOrdenModalState();
}

class _FormularioCierreOrdenModalState extends State<FormularioCierreOrdenModal> {
  final RutasTrabajoService _rutasService = RutasTrabajoService();
  final ImagePicker _picker = ImagePicker();

  final TextEditingController _lecturaCtrl = TextEditingController();
  final TextEditingController _observacionesCtrl = TextEditingController();

  // Estado del formulario
  String _estadoSeleccionado = 'Ejecutado'; // 'Ejecutado' o 'Observado'
  String _motivoObservacion = 'Casa cerrada / Abonado ausente';
  final List<File> _fotos = [];
  bool _isCargando = false;
  bool _resultadoIncierto = false;
  bool _capturandoFoto = false;
  String? _errorMessage;

  final List<String> _motivosPredefinidos = [
    'Casa cerrada / Abonado ausente',
    'Medidor no visible o inaccesible',
    'Medidor enterrado / con escombros',
    'Perro agresivo / Riesgo físico',
    'Abonado presentó comprobante de pago',
    'Oposición violenta / Amenaza verbal',
    'Acometida manipulada / Conexión clandestina',
    'Otro impedimento técnico en terreno'
  ];

  @override
  void dispose() {
    _lecturaCtrl.dispose();
    _observacionesCtrl.dispose();
    super.dispose();
  }

  Future<void> _capturarFoto(ImageSource source, {int? reemplazar}) async {
    if (_isCargando || _capturandoFoto || (reemplazar == null && _fotos.length >= 3)) return;
    setState(() => _capturandoFoto = true);
    try {
      final XFile? image = await _picker.pickImage(
        source: source,
        imageQuality: 80,
        maxWidth: 1280,
      );

      if (image != null && mounted && !_isCargando) {
        setState(() {
          if (reemplazar == null) {
            _fotos.add(File(image.path));
          } else {
            _fotos[reemplazar] = File(image.path);
          }
          _errorMessage = null;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = "No se pudo capturar la fotografía: $e";
      });
    } finally {
      if (mounted) setState(() => _capturandoFoto = false);
    }
  }

  void _mostrarOpcionesFoto() {
    _capturarFoto(ImageSource.camera);
  }

  Future<void> _guardarRegistro() async {
    if (_isCargando || _capturandoFoto) return;
    final esCorte = (widget.rutaActiva['tipo'] ?? '').toString().toLowerCase().contains('corte');
    final lecturaValidada = double.tryParse(_lecturaCtrl.text.trim().replaceAll(',', '.'));
    final estadoFinal = _estadoSeleccionado == 'Observado'
        ? 'Observado'
        : (esCorte ? 'Cortado' : 'Reconectado');

    // 1. Validaciones de formulario
    if (_estadoSeleccionado == 'Ejecutado') {
      if (lecturaValidada == null || !lecturaValidada.isFinite || lecturaValidada < 0) {
        setState(() => _errorMessage = "Ingrese una lectura numérica válida, mayor o igual a cero.");
        return;
      }
    } else {
      if (_motivoObservacion.trim().isEmpty) {
        setState(() => _errorMessage = "Debe seleccionar un motivo estructurado para la observación.");
        return;
      }
    }

    // 2. Evidencia obligatoria para todos los estados.
    if (_fotos.isEmpty) {
      setState(() => _errorMessage = "RF-MOB-04: Es obligatorio adjuntar la fotografía de evidencia antes de enviar.");
      return;
    }

    setState(() { _isCargando = true; _errorMessage = null; });
    try {
      if (_resultadoIncierto) {
        final ruta = await _rutasService.obtenerDetalleRuta(widget.rutaActiva['id'] as int);
        final puntos = ordenarPuntos(ruta['puntos'] ?? []);
        final coincidencias = puntos.where((p) => p['id'] == widget.objetivoActual['id']);
        if (coincidencias.isEmpty) throw Exception('No se pudo verificar el punto. No se reenviará el cierre.');
        final punto = coincidencias.first;
        if (puntoAtendido(punto)) {
          if (!mounted) return;
          widget.onCompletadoExitoso?.call(punto['estadoFinal']?.toString() ?? punto['estado'].toString());
          Navigator.pop(context, true);
          return;
        }
        _resultadoIncierto = false;
      }
      final pos = await TrackingGpsService().capturarPosicionFresca();
      if (!mounted) return;
      final latMovil = pos.latitude;
      final lngMovil = pos.longitude;
      final targetLat = (widget.objetivoActual['latitud'] as num).toDouble();
      final targetLng = (widget.objetivoActual['longitud'] as num).toDouble();
      final distancia = TrackingGpsService.calcularDistanciaMetros(latMovil, lngMovil, targetLat, targetLng);
      if (distancia > 30) {
        throw Exception('Distancia ${distancia.toStringAsFixed(1)} m; máximo 30 m. Precisión GPS ±${pos.accuracy.toStringAsFixed(0)} m.');
      }
      // Conversión de la fotografía a Base64 para adjuntarla al payload
      final fotos = <String>[];
      for (final foto in List<File>.of(_fotos)) {
        final bytes = await foto.readAsBytes();
        fotos.add('data:image/jpeg;base64,${base64Encode(bytes)}');
      }
      if (!mounted) return;

      final double? lectura = _estadoSeleccionado == 'Ejecutado' ? lecturaValidada : null;

      final rutaId = widget.rutaActiva['id'] as int;
      final puntoId = widget.objetivoActual['id'] as int;

      if (DateTime.now().difference(pos.timestamp) >= const Duration(seconds: 10)) {
        throw Exception("La ubicación caducó preparando las fotos. Reintente para capturar GPS nuevo.");
      }
      _resultadoIncierto = true;
      final resultado = await _rutasService.ejecutarAccionPunto(
        rutaId: rutaId,
        puntoId: puntoId,
        observaciones: _observacionesCtrl.text.trim(),
        latitudMovil: latMovil,
        longitudMovil: lngMovil,
        lecturaMedidor: lectura,
        estadoFinal: estadoFinal,
        motivoObservacion: _estadoSeleccionado == 'Observado' ? _motivoObservacion : null,
        fotos: fotos,
      );

      if (!mounted) return;

      if (resultado.exito) {
        widget.onCompletadoExitoso?.call(estadoFinal);
        Navigator.pop(context, true);
      } else {
        setState(() {
          _isCargando = false;
          _errorMessage = resultado.error ?? "No se pudo registrar la orden en el servidor.";
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isCargando = false;
        _errorMessage = "Error inesperado al transmitir registro: $e";
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final esCorte = (widget.rutaActiva['tipo'] ?? '').toString().toLowerCase().contains('corte');
    final tracking = TrackingGpsService();
    final double targetLat = (widget.objetivoActual['latitud'] as num).toDouble();
    final double targetLng = (widget.objetivoActual['longitud'] as num).toDouble();
    final double distCalculada = TrackingGpsService.calcularDistanciaMetros(tracking.latitud, tracking.longitud, targetLat, targetLng);
    final tieneGps = tracking.ultimaPosicion != null && !tracking.isSimulacionActiva;
    final bool dentroDeRadio = tieneGps && distCalculada <= 30.0;

    return PopScope(
      canPop: !_isCargando && !_capturandoFoto,
      child: AbsorbPointer(
      absorbing: _isCargando || _capturandoFoto,
      child: Container(
      constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.90),
      decoration: const BoxDecoration(
        color: Color(0xFF1E293B),
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Tirador superior
          Center(
            child: Container(
              margin: const EdgeInsets.only(top: 10, bottom: 8),
              width: 38,
              height: 4,
              decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(2)),
            ),
          ),

          // Contenido scrollable
          Flexible(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(20, 4, 20, 20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // 1. Cabecera de la Orden
                  Row(
                    children: [
                      CircleAvatar(
                        backgroundColor: esCorte ? const Color(0xFFEF4444) : const Color(0xFF3B82F6),
                        child: Icon(esCorte ? Icons.content_cut : Icons.water_drop, color: Colors.white, size: 20),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              esCorte ? "Acta Digital: Cierre de Corte" : "Acta Digital: Cierre de Reconexión",
                              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16),
                            ),
                            Text(
                              "Hoja de Ruta: ${widget.rutaActiva['codigo'] ?? 'Activa'} · Parada #${widget.objetivoActual['orden'] ?? '1'}",
                              style: const TextStyle(color: Colors.white60, fontSize: 12),
                            ),
                          ],
                        ),
                      ),
                      IconButton(
                        icon: const Icon(Icons.close, color: Colors.white60, size: 20),
                        onPressed: _isCargando ? null : () => Navigator.pop(context, false),
                      ),
                    ],
                  ),

                  const SizedBox(height: 14),

                  // 2. Ficha de Datos del Suministro
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFF0F172A),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white12),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          "${widget.objetivoActual['titular'] ?? 'Usuario no especificado'}",
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Text(
                              "Código: ${widget.objetivoActual['codigoSuministro'] ?? '—'} · Lote: ${widget.objetivoActual['lote'] ?? '—'}",
                              style: const TextStyle(color: Colors.white70, fontSize: 12),
                            ),
                            const Spacer(),
                            if (widget.objetivoActual['montoDeuda'] != null)
                              Text(
                                "Deuda: Bs. ${widget.objetivoActual['montoDeuda']}",
                                style: const TextStyle(color: Color(0xFFF87171), fontWeight: FontWeight.bold, fontSize: 11),
                              ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        // Badge de Validación Antifraude en Tiempo Real (RN-01)
                        Row(
                          children: [
                            Icon(
                              dentroDeRadio ? Icons.verified : Icons.warning_amber,
                              size: 14,
                              color: dentroDeRadio ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                            ),
                            const SizedBox(width: 4),
                            Expanded(child: Text(
                              tieneGps ? 'Última distancia: ${distCalculada.toStringAsFixed(1)} m. Al guardar se solicitará GPS nuevo.' : 'Sin GPS real. Al guardar se solicitará una captura nueva.',
                              style: TextStyle(
                                color: dentroDeRadio ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            )),
                          ],
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 16),

                  // 3. Selector Radial / Segmentado: Ejecutado vs Observado
                  const Text(
                    "Resultado de la Intervención en Terreno:",
                    style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w600, fontSize: 13),
                  ),
                  const SizedBox(height: 8),

                  Row(
                    children: [
                      // Opción Ejecutado (Cortado o Reconectado)
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _estadoSeleccionado = 'Ejecutado'),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                            decoration: BoxDecoration(
                              color: _estadoSeleccionado == 'Ejecutado'
                                  ? (esCorte ? const Color(0xFFEF4444).withAlpha(50) : const Color(0xFF3B82F6).withAlpha(50))
                                  : const Color(0xFF0F172A),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: _estadoSeleccionado == 'Ejecutado'
                                    ? (esCorte ? const Color(0xFFEF4444) : const Color(0xFF3B82F6))
                                    : Colors.white12,
                                width: _estadoSeleccionado == 'Ejecutado' ? 2 : 1,
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  _estadoSeleccionado == 'Ejecutado' ? Icons.radio_button_checked : Icons.radio_button_off,
                                  color: esCorte ? const Color(0xFFEF4444) : const Color(0xFF3B82F6),
                                  size: 18,
                                ),
                                const SizedBox(width: 6),
                                Text(
                                  esCorte ? "Cortado" : "Reconectado",
                                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      // Opción Observado
                      Expanded(
                        child: GestureDetector(
                          onTap: () => setState(() => _estadoSeleccionado = 'Observado'),
                          child: Container(
                            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
                            decoration: BoxDecoration(
                              color: _estadoSeleccionado == 'Observado'
                                  ? const Color(0xFFF59E0B).withAlpha(50)
                                  : const Color(0xFF0F172A),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(
                                color: _estadoSeleccionado == 'Observado' ? const Color(0xFFF59E0B) : Colors.white12,
                                width: _estadoSeleccionado == 'Observado' ? 2 : 1,
                              ),
                            ),
                            child: const Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  Icons.warning_amber,
                                  color: Color(0xFFF59E0B),
                                  size: 18,
                                ),
                                SizedBox(width: 6),
                                Text(
                                  "Observado",
                                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),

                  const SizedBox(height: 14),

                  // 4. Sección Dinámica: Motivo de Observación O Lectura del Medidor
                  if (_estadoSeleccionado == 'Observado') ...[
                    Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: const Color(0xFFF59E0B).withAlpha(20),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFF59E0B).withAlpha(80)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.report_problem_outlined, color: Color(0xFFF59E0B), size: 16),
                              SizedBox(width: 6),
                              Text(
                                "Motivo Estructurado del Impedimento:",
                                style: TextStyle(color: Color(0xFFF59E0B), fontWeight: FontWeight.bold, fontSize: 12),
                              ),
                            ],
                          ),
                          const SizedBox(height: 8),
                          DropdownButtonFormField<String>(
                            value: _motivoObservacion,
                            dropdownColor: const Color(0xFF1E293B),
                            style: const TextStyle(color: Colors.white, fontSize: 13),
                            decoration: InputDecoration(
                              filled: true,
                              fillColor: const Color(0xFF0F172A),
                              contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                              border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide.none),
                            ),
                            items: _motivosPredefinidos.map((m) {
                              return DropdownMenuItem(value: m, child: Text(m, overflow: TextOverflow.ellipsis));
                            }).toList(),
                            onChanged: (val) {
                              if (val != null) setState(() => _motivoObservacion = val);
                            },
                          ),
                        ],
                      ),
                    ),
                  ] else ...[
                    // Campo Numérico: Lectura Actual del Medidor
                    TextField(
                      controller: _lecturaCtrl,
                      keyboardType: const TextInputType.numberWithOptions(decimal: true),
                      style: const TextStyle(color: Colors.white, fontSize: 14, fontWeight: FontWeight.w600),
                      decoration: InputDecoration(
                        labelText: "Lectura / Avance Actual del Medidor (m³)",
                        labelStyle: const TextStyle(color: Colors.white70, fontSize: 13),
                        hintText: "Ej. 00482.50",
                        hintStyle: const TextStyle(color: Colors.white30),
                        prefixIcon: const Icon(Icons.speed, color: Color(0xFF38BDF8), size: 20),
                        filled: true,
                        fillColor: const Color(0xFF0F172A),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                      ),
                    ),
                  ],

                  const SizedBox(height: 14),

                  const Text('Evidencia: 1–3 fotos de cámara', style: TextStyle(color: Colors.white)),
                  for (var i = 0; i < _fotos.length; i++)
                    ListTile(
                      leading: Image.file(_fotos[i], width: 64, height: 64, fit: BoxFit.cover),
                      title: Text('Fotografía ${i + 1}', style: const TextStyle(color: Colors.white)),
                      trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                        IconButton(tooltip: 'Repetir foto', icon: const Icon(Icons.camera_alt),
                          onPressed: _isCargando ? null : () => _capturarFoto(ImageSource.camera, reemplazar: i)),
                        IconButton(tooltip: 'Eliminar foto', icon: const Icon(Icons.delete_outline),
                          onPressed: _isCargando ? null : () => setState(() => _fotos.removeAt(i))),
                      ]),
                    ),
                  if (_fotos.length < 3)
                    TextButton.icon(onPressed: _isCargando ? null : _mostrarOpcionesFoto,
                      icon: const Icon(Icons.add_a_photo), label: const Text('Tomar fotografía')),

                  const SizedBox(height: 14),

                  // 6. Campo de Observaciones / Constancia Técnica
                  TextField(
                    controller: _observacionesCtrl,
                    maxLines: 2,
                    style: const TextStyle(color: Colors.white, fontSize: 13),
                    decoration: InputDecoration(
                      labelText: "Observaciones / Constancia Técnica",
                      labelStyle: const TextStyle(color: Colors.white60, fontSize: 12),
                      filled: true,
                      fillColor: const Color(0xFF0F172A),
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
                    ),
                  ),

                  // 7. Alerta de Error
                  if (_errorMessage != null) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFFEF4444).withAlpha(25),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: const Color(0xFFEF4444)),
                      ),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Icon(Icons.error_outline, color: Color(0xFFEF4444), size: 18),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              _errorMessage!,
                              style: const TextStyle(color: Color(0xFFEF4444), fontSize: 12, fontWeight: FontWeight.w500),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],

                  const SizedBox(height: 18),

                  // 8. Botones de Acción
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton(
                          onPressed: _isCargando ? null : () => Navigator.pop(context, false),
                          style: OutlinedButton.styleFrom(
                            foregroundColor: Colors.white70,
                            side: const BorderSide(color: Colors.white24),
                            padding: const EdgeInsets.symmetric(vertical: 14),
                          ),
                          child: const Text("Cancelar"),
                        ),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        flex: 2,
                        child: ElevatedButton.icon(
                          onPressed: _isCargando ? null : _guardarRegistro,
                          style: ElevatedButton.styleFrom(
                            backgroundColor: _estadoSeleccionado == 'Observado'
                                ? const Color(0xFFF59E0B)
                                : (esCorte ? const Color(0xFFEF4444) : const Color(0xFF2563EB)),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                          ),
                          icon: _isCargando
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                                )
                              : const Icon(Icons.cloud_upload_outlined, size: 18),
                          label: Text(
                            _isCargando
                                ? "Transmitiendo..."
                                : (_estadoSeleccionado == 'Observado'
                                    ? "Registrar Observación"
                                    : (esCorte ? "Confirmar Corte" : "Confirmar Reconexión")),
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                          ),
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    )));
  }
}
