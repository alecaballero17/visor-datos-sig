import 'package:flutter/material.dart';
import 'wave_painter.dart';
import 'lider_controller.dart';
import 'lider_overlay.dart';

/// Maneja la inserción y eliminación del overlay en el árbol de widgets.
class LiderOverlayManager {
  static OverlayEntry? _entry;

  /// Abre el overlay del asistente.
  static void abrir(BuildContext context) {
    if (_entry != null) return; // Ya está abierto
    
    _entry = OverlayEntry(builder: (_) => const LiderOverlay());
    Overlay.of(context).insert(_entry!);

    // Escuchar cuando el controlador vuelve a inactivo para cerrar el overlay
    final ctrl = LiderController();
    void listener() {
      if (ctrl.estado == LiderEstado.inactivo) {
        cerrar();
        ctrl.removeListener(listener);
      }
    }
    ctrl.addListener(listener);
  }

  /// Elimina el overlay de la pantalla.
  static void cerrar() {
    _entry?.remove();
    _entry = null;
  }
}

/// Botón flotante del micrófono que activa "Oye Líder".
/// Se agrega automáticamente a todas las pantallas desde UIScreen.
class LiderButton extends StatefulWidget {
  const LiderButton({super.key});

  @override
  State<LiderButton> createState() => _LiderButtonState();
}

class _LiderButtonState extends State<LiderButton>
    with SingleTickerProviderStateMixin {
  final LiderController _ctrl = LiderController();
  late AnimationController _pulseCtrl;
  late Animation<double> _pulseAnim;



  @override
  void initState() {
    super.initState();
    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    )..repeat(reverse: true);

    _pulseAnim = Tween<double>(begin: 1.0, end: 1.12).animate(
      CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut),
    );

    // Inicializar el STT y empezar a escuchar el wake word
    _ctrl.inicializar();

    _ctrl.addListener(() {
      // Cuando el controlador se activa (por wake word), abrir el overlay
      if (_ctrl.estado == LiderEstado.escuchando && mounted) {
        LiderOverlayManager.abrir(context);
      }
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  void _onPresionar() {
    if (_ctrl.estado != LiderEstado.inactivo) return;
    LiderOverlayManager.abrir(context);
    _ctrl.activar();
  }

  @override
  Widget build(BuildContext context) {
    final activo = _ctrl.estado != LiderEstado.inactivo;
    final color = activo 
        ? const Color(0xFF4285F4)
        : const Color(0xFF7C3AED);

    return AnimatedBuilder(
      animation: _pulseAnim,
      builder: (_, child) {
        return Transform.scale(
          scale: activo ? _pulseAnim.value : 1.0,
          child: child,
        );
      },
      child: FloatingActionButton(
        onPressed: _onPresionar,
        backgroundColor: color,
        elevation: 8,
        tooltip: 'Oye Líder',
        child: AnimatedSwitcher(
          duration: const Duration(milliseconds: 300),
          child: Icon(
            activo ? Icons.mic : Icons.mic_none,
            key: ValueKey(activo),
            color: Colors.white,
            size: 28,
          ),
        ),
      ),
    );
  }
}
