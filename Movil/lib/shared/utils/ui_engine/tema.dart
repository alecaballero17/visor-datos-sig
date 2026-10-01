import 'package:flutter/material.dart';

// ==========================================
// 1. PALETA DE COLORES
// ==========================================
class AppColores {
  final Color primario;
  final Color secundario;
  final Color fondo;
  final Color fondoSecundario;
  final Color textoPrincipal;
  final Color textoSecundario;
  final Color error;
  final Color exito;
  final Color advertencia;
  final Color borde;

  const AppColores({
    required this.primario,
    required this.secundario,
    required this.fondo,
    required this.fondoSecundario,
    required this.textoPrincipal,
    required this.textoSecundario,
    required this.error,
    required this.exito,
    required this.advertencia,
    required this.borde,
  });

  // Paleta por defecto (Claro)
  static const claro = AppColores(
    primario: Colors.deepPurple,
    secundario: Colors.deepPurpleAccent,
    fondo: Color(0xFFF9FAFB), // Gris muy claro
    fondoSecundario: Colors.white,
    textoPrincipal: Color(0xFF111827), // Casi negro
    textoSecundario: Color(0xFF6B7280), // Gris
    error: Colors.redAccent,
    exito: Colors.green,
    advertencia: Colors.orange,
    borde: Color(0xFFE5E7EB),
  );

  // Paleta por defecto (Oscuro)
  static const oscuro = AppColores(
    primario: Colors.deepPurpleAccent,
    secundario: Colors.deepPurple,
    fondo: Color(0xFF111827),
    fondoSecundario: Color(0xFF1F2937),
    textoPrincipal: Color(0xFFF9FAFB),
    textoSecundario: Color(0xFF9CA3AF),
    error: Colors.redAccent,
    exito: Colors.greenAccent,
    advertencia: Colors.orangeAccent,
    borde: Color(0xFF374151),
  );
}

// ==========================================
// 2. SISTEMA DE TIPOGRAFÍA
// ==========================================
class AppTextos {
  final TextStyle tituloLargo;
  final TextStyle titulo;
  final TextStyle subtitulo;
  final TextStyle cuerpo;
  final TextStyle cuerpoPequeno;
  final TextStyle boton;

  const AppTextos({
    required this.tituloLargo,
    required this.titulo,
    required this.subtitulo,
    required this.cuerpo,
    required this.cuerpoPequeno,
    required this.boton,
  });

  // Generador de estilos basado en los colores actuales
  factory AppTextos.generar(AppColores colores) {
    return AppTextos(
      tituloLargo: TextStyle(fontSize: 32, fontWeight: FontWeight.bold, color: colores.textoPrincipal, letterSpacing: -0.5),
      titulo: TextStyle(fontSize: 24, fontWeight: FontWeight.bold, color: colores.textoPrincipal),
      subtitulo: TextStyle(fontSize: 18, fontWeight: FontWeight.w600, color: colores.textoSecundario),
      cuerpo: TextStyle(fontSize: 16, fontWeight: FontWeight.normal, color: colores.textoPrincipal),
      cuerpoPequeno: TextStyle(fontSize: 14, fontWeight: FontWeight.normal, color: colores.textoSecundario),
      boton: TextStyle(fontSize: 16, fontWeight: FontWeight.w600, color: Colors.white),
    );
  }
}

// ==========================================
// 3. CONTROLADOR GLOBAL DEL TEMA
// ==========================================
class AppTheme {
  // Estado global actual del tema (Modificable en tiempo real si se desea)
  static AppColores colores = AppColores.claro;
  static AppTextos textos = AppTextos.generar(AppColores.claro);

  static void cambiarModo(bool esOscuro) {
    colores = esOscuro ? AppColores.oscuro : AppColores.claro;
    textos = AppTextos.generar(colores);
  }
}

// ==========================================
// 4. EXTENSIONES PARA BUILDCONTEXT
// ==========================================
// Permite usar `context.colores.primario` en cualquier lugar que tenga acceso a un BuildContext.
extension ContextThemeExtension on BuildContext {
  AppColores get colores {
    // Si quisieras conectarlo nativamente a Flutter ThemeMode:
    // final esOscuro = Theme.of(this).brightness == Brightness.dark;
    // return esOscuro ? AppColores.oscuro : AppColores.claro;
    
    // Por ahora, devolvemos el estado global estático
    return AppTheme.colores;
  }
  
  AppTextos get textos => AppTheme.textos;
}
