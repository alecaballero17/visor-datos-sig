import 'api_provider.dart';

/// Este es el repositorio universal que maneja automáticamente las peticiones CRUD.
/// No necesitas escribir clases individuales como 'JuegoRepository'.
class MagicRepository {
  final String endpoint;

  MagicRepository(this.endpoint);

  Future<dynamic> obtener([dynamic id]) async {
    final ruta = id != null ? '/$endpoint/$id' : '/$endpoint';
    return await api.get(ruta);
  }

  Future<dynamic> crear(Map<String, dynamic> datos) async {
    return await api.post('/$endpoint', data: datos);
  }

  Future<dynamic> actualizar(dynamic id, Map<String, dynamic> datos) async {
    return await api.put('/$endpoint/$id', data: datos);
  }

  Future<dynamic> borrar(dynamic id) async {
    return await api.delete('/$endpoint/$id');
  }
}

/// El ApiManager usa `noSuchMethod` para interceptar CUALQUIER llamada
/// a una propiedad que no existe, y la convierte en una ruta de API.
class ApiManager {
  /// Helper explícito para cuando el nombre del endpoint viene como String en runtime.
  MagicRepository noSuchMethodHelper(String endpoint) {
    return MagicRepository(endpoint);
  }

  @override
  dynamic noSuchMethod(Invocation invocation) {
    // Si llamas a api.juegos, interceptamos "juegos"
    if (invocation.isGetter) {
      // Limpiamos el nombre interceptado (ej: Symbol("juegos") -> "juegos")
      final nombre = invocation.memberName.toString().replaceAll('Symbol("', '').replaceAll('")', '');
      
      // Devolvemos un repositorio mágico con esa ruta lista para usarse
      return MagicRepository(nombre);
    }
    return super.noSuchMethod(invocation);
  }
}

/// Instancia global, tipada como dynamic para que Dart nos deje llamar 
/// a cualquier propiedad (ej: UI.api.juegos, UI.api.plataformas) sin chistar.
final dynamic magiaApi = ApiManager();

/// Una clase falsa para simular la sintaxis UI.api (o lo integras en tu UI Engine)
class UI {
  static dynamic get api => magiaApi;
}
