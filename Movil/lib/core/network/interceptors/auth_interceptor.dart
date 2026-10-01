import 'package:dio/dio.dart';

class AuthInterceptor extends Interceptor {
  // Almacenamiento en memoria del cookie de sesión (para pruebas simples)
  static String? sessionCookie;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    // Si tenemos una cookie guardada, la inyectamos en la petición
    if (sessionCookie != null && sessionCookie!.isNotEmpty) {
      options.headers['Cookie'] = sessionCookie;
    }
    
    // Continuar con la petición
    super.onRequest(options, handler);
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    final cookies = response.headers['set-cookie'];
    if (cookies != null && cookies.isNotEmpty) {
      // Extraemos la cookie que necesitamos (Arquis.Auth o .AspNetCore.Cookies)
      for (var cookie in cookies) {
        if (cookie.startsWith('Arquis.Auth=') || cookie.startsWith('.AspNetCore.')) {
          sessionCookie = cookie.split(';').first; // Guardar solo la clave=valor
          break;
        }
      }
    }
    
    super.onResponse(response, handler);
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    // Manejo global de errores a nivel de interceptor
    if (err.response?.statusCode == 401) {
      // Usuario no autorizado, borrar cookie
      sessionCookie = null;
    }
    super.onError(err, handler);
  }
}
