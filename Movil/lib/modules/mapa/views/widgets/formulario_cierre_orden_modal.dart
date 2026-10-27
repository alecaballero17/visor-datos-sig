import 'dart:io';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import '../../services/rutas_trabajo_service.dart';
import '../../services/tracking_gps_service.dart';

/// Modal completo de Cierre de Orden Operativa (RF-MOB-04 & RF-MOB-05)
/// Integra:
/// 1. Selector Cortado/Reconectado vs Observado (con motivos predefinidos)
/// 2. Campo numérico para Lectura del Medidor
/// 3. Captura obligatoria de 1 Fotografía de evidencia
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
  File? _fotoEvidencia; // Exactamente 1 fotografía según requerimiento
  bool _isCargando = false;
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
  void initState() {
    super.initState();
    final esCorte = (widget.rutaActiva['tipo'] ?? '').toString().toLowerCase().contains('corte');
    _observacionesCtrl.text = esCorte
        ? 'Válvula precintada. Corte ejecutado conforme al protocolo.'
        : 'Servicio restablecido y verificado correctamente.';
  }

  @override
  void dispose() {
    _lecturaCtrl.dispose();
    _observacionesCtrl.dispose();
    super.dispose();
  }

  Future<void> _capturarFoto(ImageSource source) async {
    try {
      final XFile? image = await _picker.pickImage(
        source: source,
        imageQuality: 80,
        maxWidth: 1280,
      );

      if (image != null) {
        setState(() {
          _fotoEvidencia = File(image.path);
          _errorMessage = null;
        });
      }
    } catch (e) {
      setState(() {
        _errorMessage = "No se pudo capturar la fotografía: $e";
      });
    }
  }

  void _mostrarOpcionesFoto() {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(16))),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 16.0),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text(
                "Capturar Fotografía de Evidencia (1 foto)",
                style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 15),
              ),
              const SizedBox(height: 12),
              ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Color(0xFF0284C7),
                  child: Icon(Icons.camera_alt, color: Colors.white, size: 20),
                ),
                title: const Text("Tomar con la Cámara", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                subtitle: const Text("Recomendado para evidenciar medidor en campo", style: TextStyle(color: Colors.white60, fontSize: 12)),
                onTap: () {
                  Navigator.pop(ctx);
                  _capturarFoto(ImageSource.camera);
                },
              ),
              ListTile(
                leading: const CircleAvatar(
                  backgroundColor: Color(0xFF334155),
                  child: Icon(Icons.photo_library, color: Colors.white, size: 20),
                ),
                title: const Text("Seleccionar de la Galería", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w600)),
                subtitle: const Text("Para pruebas o fotografías tomadas previamente", style: TextStyle(color: Colors.white60, fontSize: 12)),
                onTap: () {
                  Navigator.pop(ctx);
                  _capturarFoto(ImageSource.gallery);
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _eliminarFoto() {
    setState(() {
      _fotoEvidencia = null;
    });
  }

  Future<void> _guardarRegistro() async {
    final esCorte = (widget.rutaActiva['tipo'] ?? '').toString().toLowerCase().contains('corte');
    final estadoFinal = _estadoSeleccionado == 'Observado'
        ? 'Observado'
        : (esCorte ? 'Cortado' : 'Reconectado');

    // 1. Validaciones de formulario
    if (_estadoSeleccionado == 'Ejecutado') {
      if (_lecturaCtrl.text.trim().isEmpty) {
        setState(() => _errorMessage = "Por favor ingrese la lectura o avance actual del medidor.");
        return;
      }
    } else {
      if (_motivoObservacion.trim().isEmpty) {
        setState(() => _errorMessage = "Debe seleccionar un motivo estructurado para la observación.");
        return;
      }
    }

    // 2. Validación de Evidencia Fotográfica (Exactamente 1 foto)
    if (_fotoEvidencia == null) {
      setState(() => _errorMessage = "RF-MOB-04: Es obligatorio adjuntar la fotografía de evidencia antes de enviar.");
      return;
    }

    // 3. Captura y Validación Geográfica Antifraude (RF-MOB-05 / RN-01)
    final tracking = TrackingGpsService();
    final double latMovil = tracking.latitud;
    final double lngMovil = tracking.longitud;

    final double targetLat = (widget.objetivoActual['latitud'] as num).toDouble();
    final double targetLng = (widget.objetivoActual['longitud'] as num).toDouble();
    final double distCalculada = TrackingGpsService.calcularDistanciaMetros(latMovil, lngMovil, targetLat, targetLng);

    // Validación preventiva en el cliente (Regla de 30 metros)
    if (distCalculada > 30.0) {
      setState(() {
        _errorMessage = "RN-01 Antifraude: Su distancia actual (${distCalculada.toStringAsFixed(1)} m) excede el radio de tolerancia de 30 m respecto al predio (${widget.objetivoActual['codigoSuministro']}). Debe encontrarse físicamente en el lugar.";
      });
      return;
    }

    setState(() {
      _isCargando = true;
      _errorMessage = null;
    });

    try {
      // Conversión de la fotografía a Base64 para adjuntarla al payload
      final bytes = await _fotoEvidencia!.readAsBytes();
      final base64String = "data:image/jpeg;base64,${base64Encode(bytes)}";

      final double? lectura = double.tryParse(_lecturaCtrl.text.trim().replaceAll(',', '.'));

      final rutaId = widget.rutaActiva['id'] as int;
      final puntoId = widget.objetivoActual['id'] as int;

      final resultado = await _rutasService.ejecutarAccionPunto(
        rutaId: rutaId,
        puntoId: puntoId,
        observaciones: _observacionesCtrl.text.trim(),
        latitudMovil: latMovil,
        longitudMovil: lngMovil,
        lecturaMedidor: lectura,
        estadoFinal: estadoFinal,
        motivoObservacion: _estadoSeleccionado == 'Observado' ? _motivoObservacion : null,
        fotos: [base64String],
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
    final bool dentroDeRadio = distCalculada <= 30.0;

    return Container(
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
                        onPressed: () => Navigator.pop(context, false),
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
                            Text(
                              "Distancia al medidor: ${distCalculada.toStringAsFixed(1)} m ${dentroDeRadio ? '(Dentro del radio de 30 m)' : '(¡Fuera del radio permitido!)'}",
                              style: TextStyle(
                                color: dentroDeRadio ? const Color(0xFF10B981) : const Color(0xFFF59E0B),
                                fontSize: 11,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
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

                  // 5. Módulo de Fotografía de Evidencia (1 Sola Foto)
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        "Evidencia Fotográfica (1 Foto):",
                        style: TextStyle(color: Colors.white70, fontWeight: FontWeight.w600, fontSize: 13),
                      ),
                      if (_fotoEvidencia != null)
                        const Text(
                          "✓ 1 Foto capturada",
                          style: TextStyle(color: Color(0xFF10B981), fontWeight: FontWeight.bold, fontSize: 11),
                        ),
                    ],
                  ),
                  const SizedBox(height: 8),

                  if (_fotoEvidencia == null)
                    InkWell(
                      onTap: _mostrarOpcionesFoto,
                      borderRadius: BorderRadius.circular(10),
                      child: Container(
                        padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFF38BDF8).withAlpha(100), style: BorderStyle.solid),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(Icons.add_a_photo, color: Color(0xFF38BDF8), size: 24),
                            SizedBox(width: 10),
                            Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  "Tomar Fotografía de Evidencia",
                                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                                Text(
                                  "1 imagen nítida del medidor o fachada del predio",
                                  style: TextStyle(color: Colors.white60, fontSize: 11),
                                ),
                              ],
                            ),
                          ],
                        ),
                      ),
                    )
                  else
                    // Previsualización de la Única Fotografía Adjunta
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: const Color(0xFF0F172A),
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: const Color(0xFF10B981).withAlpha(120)),
                      ),
                      child: Row(
                        children: [
                          ClipRRect(
                            borderRadius: BorderRadius.circular(8),
                            child: Image.file(
                              _fotoEvidencia!,
                              width: 64,
                              height: 64,
                              fit: BoxFit.cover,
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  "Fotografía de Evidencia Adjunta",
                                  style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 13),
                                ),
                                Text(
                                  "1 archivo listo para transmitir al backend",
                                  style: TextStyle(color: Colors.white60, fontSize: 11),
                                ),
                              ],
                            ),
                          ),
                          IconButton(
                            icon: const Icon(Icons.refresh, color: Color(0xFF38BDF8), size: 22),
                            onPressed: _mostrarOpcionesFoto,
                            tooltip: "Cambiar / Repetir foto",
                          ),
                          IconButton(
                            icon: const Icon(Icons.delete_outline, color: Color(0xFFEF4444), size: 22),
                            onPressed: _eliminarFoto,
                            tooltip: "Eliminar foto",
                          ),
                        ],
                      ),
                    ),

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
    );
  }
}
