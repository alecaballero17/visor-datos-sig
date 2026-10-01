import '../../../../core/network/api_provider.dart';
import 'auth_endpoints.dart';

class AuthService {
  Future<dynamic> login(String usuarioEmail, String password) async {
    final response = await api.post(
      AuthEndpoints.iniciar,
      data: {
        'usuario': usuarioEmail,
        'password': password,
      },
    );
    return response;
  }

  Future<dynamic> register(String nombre, String email, String password) async {
    final response = await api.post(
      AuthEndpoints.registrar,
      data: {
        'nombre': nombre,
        'email': email,
        'password': password,
      },
    );
    return response;
  }

  Future<void> logout() async {
    await api.post(AuthEndpoints.cerrar);
  }

  Future<dynamic> checkSession() async {
    final response = await api.get(AuthEndpoints.sesion);
    return response;
  }
}
