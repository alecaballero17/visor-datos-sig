import 'dart:math';
import 'package:flutter/material.dart';

/// Pinta las olas animadas estilo Gemini con múltiples capas de color.
class WavePainter extends CustomPainter {
  final double animationValue;   // 0.0 → 1.0, progresa continuamente
  final double amplitude;        // Intensidad de la ola (sube si el usuario habla)
  final LiderEstado estado;

  WavePainter({
    required this.animationValue,
    required this.amplitude,
    required this.estado,
  });

  // Colores de las olas según el estado del asistente
  List<Color> get _colores {
    switch (estado) {
      case LiderEstado.escuchando:
        return [
          const Color(0xFF4285F4), // Azul Google
          const Color(0xFF9C27B0), // Morado
          const Color(0xFF00BCD4), // Cyan
          const Color(0xFF4CAF50), // Verde
        ];
      case LiderEstado.pensando:
        return [
          const Color(0xFFFF9800), // Naranja
          const Color(0xFFF44336), // Rojo
          const Color(0xFFFFEB3B), // Amarillo
          const Color(0xFFFF5722), // Deep Orange
        ];
      case LiderEstado.resultado:
        return [
          const Color(0xFF4CAF50), // Verde éxito
          const Color(0xFF66BB6A),
          const Color(0xFF81C784),
          const Color(0xFFA5D6A7),
        ];
      default:
        return [
          const Color(0xFF4285F4),
          const Color(0xFF9C27B0),
          const Color(0xFF00BCD4),
          const Color(0xFF4CAF50),
        ];
    }
  }

  @override
  void paint(Canvas canvas, Size size) {
    final colores = _colores;

    for (int i = 0; i < colores.length; i++) {
      // La velocidad de la ola sube con la amplitud (reacciona a la voz)
      final speedMult = 1.0 + amplitude * 2.0;
      final fase = animationValue * 2 * pi * speedMult + (i * pi / 2);
      final velocidad = 1.0 + (i * 0.4);
      // Amplitud mínima visible + reacción directa a la voz
      final alturaOla = (amplitude * (55 + i * 20)).clamp(5.0, 120.0);
      final opacidad = (0.85 - (i * 0.15)).clamp(0.2, 0.9);
      final offsetY = size.height * 0.5 + (i - 1.5) * 15 * amplitude;

      final paint = Paint()
        ..color = colores[i].withValues(alpha: opacidad)
        ..style = PaintingStyle.stroke
        ..strokeWidth = (3.5 - (i * 0.5)).clamp(1.0, 4.0)
        ..strokeCap = StrokeCap.round;

      final path = Path();

      for (double x = 0; x <= size.width; x += 1) {
        final y = offsetY +
            sin((x / size.width * 2 * pi * velocidad) + fase) * alturaOla +
            sin((x / size.width * pi * velocidad * 0.5) + fase * 0.7) * (alturaOla * 0.35);
        if (x == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
      }

      canvas.drawPath(path, paint);
    }
  }

  @override
  bool shouldRepaint(WavePainter oldDelegate) =>
      oldDelegate.animationValue != animationValue ||
      oldDelegate.amplitude != amplitude ||
      oldDelegate.estado != estado;
}

enum LiderEstado { inactivo, escuchando, pensando, resultado, error }
