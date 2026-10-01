import 'package:flutter/material.dart';
import '../services/auth_service.dart';

class AuthController {
  final AuthService _authService = AuthService();

  final TextEditingController emailCtrl = TextEditingController();
  final TextEditingController passwordCtrl = TextEditingController();
  final TextEditingController nombreCtrl = TextEditingController();

  bool isLogin = true;
  bool isCargando = false;
  String? errorMessage;
  String? successMessage;

  Future<bool> login(Function(VoidCallback) actualizar) async {
    final email = emailCtrl.text.trim();
    final password = passwordCtrl.text;

    if (email.isEmpty || password.isEmpty) {
      actualizar(() {
        errorMessage = 'Ingresa todos los campos requeridos';
      });
      return false;
    }

    actualizar(() {
      isCargando = true;
      errorMessage = null;
    });

    try {
      final respuesta = await _authService.login(email, password);
      // Aquí normalmente guardarías el token o redirigirías
      actualizar(() {
        isCargando = false;
        errorMessage = null;
      });
      return true;
    } catch (e) {
      actualizar(() {
        isCargando = false;
        errorMessage = e.toString().replaceAll('Exception: ', '');
      });
      return false;
    }
  }

  Future<bool> register(Function(VoidCallback) actualizar) async {
    final email = emailCtrl.text.trim();
    final password = passwordCtrl.text;
    final nombre = nombreCtrl.text.trim();

    if (email.isEmpty || password.isEmpty || nombre.isEmpty) {
      actualizar(() => errorMessage = 'Ingresa todos los campos requeridos');
      return false;
    }

    if (nombre.length < 2) {
      actualizar(() => errorMessage = 'El nombre es muy corto');
      return false;
    }

    if (password.length < 8) {
      actualizar(() => errorMessage = 'La contraseña debe tener mínimo 8 caracteres');
      return false;
    }

    actualizar(() {
      isCargando = true;
      errorMessage = null;
      successMessage = null;
    });

    try {
      final respuesta = await _authService.register(nombre, email, password);
      actualizar(() {
        isCargando = false;
        errorMessage = null;
        successMessage = respuesta['mensaje'] ?? 'Cuenta creada. Inicia sesión.';
        isLogin = true; // Volver al login para que ingrese
      });
      return true;
    } catch (e) {
      actualizar(() {
        isCargando = false;
        errorMessage = e.toString().replaceAll('Exception: ', '');
      });
      return false;
    }
  }

  void toggleMode(Function(VoidCallback) actualizar) {
    actualizar(() {
      isLogin = !isLogin;
      errorMessage = null;
      successMessage = null;
    });
  }

  void dispose() {
    emailCtrl.dispose();
    passwordCtrl.dispose();
    nombreCtrl.dispose();
  }
}
