import 'package:flutter/material.dart';
import '../../../../../shared/utils/ui_engine/ui_screen.dart';
import '../../../../../shared/utils/ui_engine/widget_modifiers.dart';
import '../../../../../shared/utils/ui_engine/list_modifiers.dart';
import '../../../../../shared/utils/ui_engine/string_modifiers.dart';
import '../../../../../shared/utils/ui_engine/icon_modifiers.dart';

import '../../../controllers/auth_controller.dart';
import '../../../../mapa/views/screens/flujo_principal/mapa_pantalla_inicio.dart';

class AuthPantallaInicio extends StatefulWidget {
  const AuthPantallaInicio({super.key});

  @override
  State<AuthPantallaInicio> createState() => _AuthPantallaInicioState();
}

class _AuthPantallaInicioState extends State<AuthPantallaInicio> {
  static final AuthController controlador = AuthController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 48.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Logo simple estilo Google
              const SizedBox(height: 40),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icons.map.icono(size: 40, color: const Color(0xFF4285F4)),
                  const SizedBox(width: 12),
                  "Arquis".texto(
                    size: 32, 
                    color: Colors.black87,
                    negrita: true,
                    fontFamily: 'Roboto',
                  ),
                ],
              ),
              const SizedBox(height: 16),
              "Inicia sesión para continuar".texto(
                size: 16, 
                color: Colors.black54, 
                alineacion: TextAlign.center
              ),
              const SizedBox(height: 60),

              CustomRebuilder(
                builder: (actualizar) => Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    if (!controlador.isLogin) ...[
                      _buildMaterialTextField(
                        controller: controlador.nombreCtrl,
                        label: "Nombre completo",
                        isPassword: false,
                      ),
                      const SizedBox(height: 20),
                    ],
                    _buildMaterialTextField(
                      controller: controlador.emailCtrl,
                      label: "Correo electrónico o teléfono",
                      isPassword: false,
                    ),
                    const SizedBox(height: 20),
                    _buildMaterialTextField(
                      controller: controlador.passwordCtrl,
                      label: "Introduce tu contraseña",
                      isPassword: true,
                    ),
                    
                    if (!controlador.isLogin)
                      Padding(
                        padding: const EdgeInsets.only(top: 8.0, left: 4.0),
                        child: "Mínimo 8 caracteres.".texto(color: Colors.black54, size: 12),
                      ),

                    if (controlador.errorMessage != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 16.0),
                        child: Row(
                          children: [
                            const Icon(Icons.error_outline, color: Color(0xFFD93025), size: 16),
                            const SizedBox(width: 8),
                            Expanded(
                              child: controlador.errorMessage!.texto(
                                color: const Color(0xFFD93025), 
                                size: 14
                              ),
                            ),
                          ],
                        ),
                      ),
                      
                    if (controlador.successMessage != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 16.0),
                        child: Row(
                          children: [
                            const Icon(Icons.check_circle_outline, color: Colors.green, size: 16),
                            const SizedBox(width: 8),
                            Expanded(
                              child: controlador.successMessage!.texto(
                                color: Colors.green, 
                                size: 14
                              ),
                            ),
                          ],
                        ),
                      ),

                    const SizedBox(height: 40),
                    
                    // Botón estilo Google Primario
                    ElevatedButton(
                      onPressed: controlador.isCargando ? null : () async {
                        if (controlador.isLogin) {
                          final success = await controlador.login(actualizar);
                          if (success && mounted) {
                            Navigator.pushReplacement(
                              context,
                              MaterialPageRoute(builder: (context) => const MapaPantallaInicio()),
                            );
                          }
                        } else {
                          await controlador.register(actualizar);
                        }
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF1A73E8), // Azul Google
                        foregroundColor: Colors.white,
                        elevation: 0,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(4), 
                        ),
                      ),
                      child: controlador.isCargando 
                        ? const SizedBox(
                            height: 20, width: 20,
                            child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2),
                          )
                        : (controlador.isLogin ? "Ingresar" : "Crear cuenta").texto(color: Colors.white, negrita: true, size: 16),
                    ),
                    
                    const SizedBox(height: 24),
                    
                    // Botón secundario (Toggle)
                    Center(
                      child: TextButton(
                        onPressed: () => controlador.toggleMode(actualizar),
                        child: (controlador.isLogin ? "¿No tienes cuenta? Registrar usuario" : "¿Ya tienes cuenta? Iniciar sesión").texto(
                          color: const Color(0xFF1A73E8),
                          negrita: true,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

Widget _buildMaterialTextField({
  required TextEditingController controller,
  required String label,
  required bool isPassword,
}) {
  return TextField(
    controller: controller,
    obscureText: isPassword,
    style: const TextStyle(color: Colors.black87, fontSize: 16),
    decoration: InputDecoration(
      labelText: label,
      labelStyle: const TextStyle(color: Colors.black54),
      filled: false,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: Colors.black26),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: Colors.black26),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(4),
        borderSide: const BorderSide(color: Color(0xFF1A73E8), width: 2.0),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    ),
  );
}
