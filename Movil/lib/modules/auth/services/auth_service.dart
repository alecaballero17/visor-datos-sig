import '../../../core/network/api_provider.dart';
import 'auth_endpoints.dart';
import '../models/sesion_usuario.dart';
import '../../../core/network/interceptors/auth_interceptor.dart';

class AuthService {
  Future<dynamic> login(String usuarioEmail, String password) async {
    final response = await api.post(
      AuthEndpoints.iniciar,
      data: {
        'usuario': usuarioEmail,
        'password': password,
        'origen': 'movil',
      },
    );
    SesionUsuario.actual.value = SesionUsuario.fromJson(Map<String, dynamic>.from(response));
    return response;
  }

  Future<dynamic> register(String nombre, String email, String password) async {
    final response = await api.post(
      AuthEndpoints.registrar,
      data: {
        'nombre': nombre,
        'email': email,
        'password': password,
        'origen': 'movil',
      },
    );
    return response;
  }

  Future<void> logout() async {
    try {
      await api.post(AuthEndpoints.cerrar);
    } finally {
      AuthInterceptor.sessionCookie = null;
      SesionUsuario.actual.value = null;
    }
  }

  Future<dynamic> checkSession() async {
    final response = await api.get(AuthEndpoints.sesion);
    return response;
  }
}
