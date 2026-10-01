import 'dart:ui';
import 'package:flutter/material.dart';
import 'wave_painter.dart';
import 'lider_controller.dart';

/// El overlay visual completo del asistente "Oye Líder".
/// Se superpone sobre toda la pantalla con glassmorphism + olas animadas.
class LiderOverlay extends StatefulWidget {
  const LiderOverlay({super.key});

  @override
  State<LiderOverlay> createState() => _LiderOverlayState();
}

class _LiderOverlayState extends State<LiderOverlay>
    with TickerProviderStateMixin {
  final LiderController _ctrl = LiderController();

  late AnimationController _waveController;   // Animación continua de las olas
  late AnimationController _entradaController; // Animación de entrada del overlay
  late Animation<double> _entradaAnim;

  @override
  void initState() {
    super.initState();

    _waveController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 3),
    )..repeat();

    _entradaController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 400),
    );
    _entradaAnim = CurvedAnimation(parent: _entradaController, curve: Curves.easeOutCubic);
    _entradaController.forward();

    _ctrl.addListener(() {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _waveController.dispose();
    _entradaController.dispose();
    super.dispose();
  }

  String get _textoEstado {
    switch (_ctrl.estado) {
      case LiderEstado.escuchando: return _ctrl.textoEscuchado.isNotEmpty ? _ctrl.textoEscuchado : 'Escuchando...';
      case LiderEstado.pensando:   return 'Procesando...';
      case LiderEstado.resultado:  return _ctrl.mensajeResultado;
      case LiderEstado.error:      return _ctrl.mensajeResultado;
      default:                     return '';
    }
  }

  Color get _colorTexto {
    switch (_ctrl.estado) {
      case LiderEstado.resultado:  return const Color(0xFF4CAF50);
      case LiderEstado.error:      return const Color(0xFFF44336);
      default:                     return Colors.white;
    }
  }

  IconData get _icono {
    switch (_ctrl.estado) {
      case LiderEstado.escuchando: return Icons.mic;
      case LiderEstado.pensando:   return Icons.psychology;
      case LiderEstado.resultado:  return Icons.check_circle_outline;
      case LiderEstado.error:      return Icons.error_outline;
      default:                     return Icons.mic_none;
    }
  }

  @override
  Widget build(BuildContext context) {
    final screenH = MediaQuery.of(context).size.height;

    return FadeTransition(
      opacity: _entradaAnim,
      child: SlideTransition(
        position: Tween<Offset>(
          begin: const Offset(0, 0.1),
          end: Offset.zero,
        ).animate(_entradaAnim),
        child: Material(
          color: Colors.transparent,
          child: Stack(
            children: [
              // ── FONDO: Glassmorphism oscuro ──────────────────
              GestureDetector(
                onTap: _ctrl.cerrar,
                child: BackdropFilter(
                  filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
                  child: Container(
                    color: Colors.black.withValues(alpha: 0.65),
                    width: double.infinity,
                    height: double.infinity,
                  ),
                ),
              ),

              // ── OLAS ANIMADAS ────────────────────────────────
              Positioned(
                bottom: screenH * 0.15,
                left: 0,
                right: 0,
                child: SizedBox(
                  height: 200,
                  child: AnimatedBuilder(
                    animation: _waveController,
                    builder: (_, __) {
                      return CustomPaint(
                        painter: WavePainter(
                          animationValue: _waveController.value,
                          amplitude: _ctrl.amplitudOnda,
                          estado: _ctrl.estado,
                        ),
                      );
                    },
                  ),
                ),
              ),

              // ── PANEL CENTRAL ────────────────────────────────
              Align(
                alignment: Alignment.center,
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 30),
                  padding: const EdgeInsets.all(28),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.15),
                      width: 1,
                    ),
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Título fijo
                      const Text(
                        'Líder',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 13,
                          letterSpacing: 4,
                          fontWeight: FontWeight.w300,
                        ),
                      ),
                      const SizedBox(height: 20),

                      // Ícono del estado con animación de pulso
                      TweenAnimationBuilder<double>(
                        tween: Tween(begin: 0.9, end: 1.1),
                        duration: const Duration(milliseconds: 800),
                        curve: Curves.easeInOut,
                        builder: (_, val, child) => Transform.scale(scale: val, child: child),
                        child: Icon(_icono, color: Colors.white, size: 52),
                      ),
                      const SizedBox(height: 20),

                      // Texto del estado
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 300),
                        child: Text(
                          _textoEstado,
                          key: ValueKey(_textoEstado),
                          style: TextStyle(
                            color: _colorTexto,
                            fontSize: 18,
                            fontWeight: FontWeight.w400,
                            height: 1.4,
                          ),
                          textAlign: TextAlign.center,
                          maxLines: 4,
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),

                      // Datos de respuesta si hay lista
                      if (_ctrl.datosResultado is List && (_ctrl.datosResultado as List).isNotEmpty)
                        ...[
                          const SizedBox(height: 16),
                          Container(
                            constraints: const BoxConstraints(maxHeight: 150),
                            child: SingleChildScrollView(
                              child: Column(
                                children: (_ctrl.datosResultado as List).take(5).map((item) {
                                  final nombre = item['nombre'] ?? item.toString();
                                  return Padding(
                                    padding: const EdgeInsets.symmetric(vertical: 3),
                                    child: Text(
                                      '• $nombre',
                                      style: const TextStyle(color: Colors.white60, fontSize: 14),
                                    ),
                                  );
                                }).toList(),
                              ),
                            ),
                          ),
                        ],
                    ],
                  ),
                ),
              ),

              // ── BOTÓN DE CIERRE ──────────────────────────────
              Positioned(
                top: 50,
                right: 20,
                child: GestureDetector(
                  onTap: _ctrl.cerrar,
                  child: Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.1),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(Icons.close, color: Colors.white70, size: 22),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
