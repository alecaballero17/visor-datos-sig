import 'dart:typed_data';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:movil/core/network/interceptors/auth_interceptor.dart';
import 'package:movil/modules/auth/models/sesion_usuario.dart';
import 'package:movil/modules/mapa/services/tracking_gps_service.dart';

class _Adapter implements HttpClientAdapter {
  int status = 200;
  Map<String, List<String>> headers = {};
  RequestOptions? request;

  @override
  Future<ResponseBody> fetch(RequestOptions options,
      Stream<Uint8List>? requestStream, Future<void>? cancelFuture) async {
    request = options;
    return ResponseBody.fromString('{}', status, headers: headers);
  }

  @override
  void close({bool force = false}) {}
}

void main() {
  late Dio dio;
  late _Adapter adapter;

  setUp(() {
    AuthInterceptor.sessionCookie = null;
    SesionUsuario.actual.value = null;
    adapter = _Adapter();
    dio = Dio(BaseOptions(baseUrl: 'http://localhost/api'))
      ..httpClientAdapter = adapter
      ..interceptors.add(AuthInterceptor());
  });

  tearDown(() {
    dio.close();
    SesionUsuario.actual.value = null;
    TrackingGpsService().limpiarSesion();
    AuthInterceptor.sessionCookie = null;
  });

  test('Cookie de login se conserva y se envía sin atributos HTTP', () async {
    adapter.headers = {'set-cookie': ['Arquis.Auth=prueba; Path=/; HttpOnly']};
    await dio.post('/autenticacion/iniciar');
    adapter.headers = {};
    await dio.get('/rutas-trabajo/asignadas');
    expect(adapter.request!.headers['Cookie'], 'Arquis.Auth=prueba');
  });

  test('401 elimina identidad, cookie y datos del tracking', () async {
    final tracking = TrackingGpsService();
    SesionUsuario.actual.value = SesionUsuario(
      usuario: 'empleado', nombre: 'Empleado', roles: ['Cortador']);
    AuthInterceptor.sessionCookie = 'Arquis.Auth=prueba';
    tracking.isSimulacionActiva = true;
    adapter.status = 401;
    await expectLater(dio.get('/autenticacion/sesion'), throwsA(isA<DioException>()));
    expect(SesionUsuario.actual.value, isNull);
    expect(AuthInterceptor.sessionCookie, isNull);
    expect(tracking.operarioId, isEmpty);
    expect(tracking.isTransmitting, isFalse);
    expect(tracking.isSimulacionActiva, isFalse);
  });

  test('El modo de ensayo bloquea la captura operativa antes de usar GPS', () async {
    final tracking = TrackingGpsService()..isSimulacionActiva = true;
    await expectLater(tracking.capturarPosicionFresca(), throwsA(isA<Exception>()));
  });
}
