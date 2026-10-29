import 'package:flutter/foundation.dart';

class SesionUsuario {
  static final actual = ValueNotifier<SesionUsuario?>(null);
  final String usuario;
  final String nombre;
  final List<String> roles;

  SesionUsuario({required this.usuario, required this.nombre, required this.roles});

  factory SesionUsuario.fromJson(Map<String, dynamic> json) {
    final usuario = json['usuario']?.toString().trim() ?? '';
    if (usuario.isEmpty) throw const FormatException('La sesión no contiene un usuario.');
    return SesionUsuario(
      usuario: usuario,
      nombre: (json['nombre']?.toString().trim().isNotEmpty ?? false) ? json['nombre'].toString() : usuario,
      roles: List<String>.from(json['roles'] ?? const []),
    );
  }
}
