import 'api_provider.dart';
import 'base_model.dart';

/// Un repositorio base genérico que implementa las operaciones CRUD estándar.
/// T es el modelo de datos que extiende de BaseModel.
abstract class BaseRepository<T extends BaseModel> {
  /// El endpoint base para este repositorio (ej: '/desarrolladors')
  final String endpoint;

  BaseRepository(this.endpoint);

  /// Método abstracto que cada repositorio específico debe implementar
  /// para convertir un Map a la entidad específica T.
  T fromJson(Map<String, dynamic> json);

  /// Listar todos los registros
  Future<List<T>> getAll() async {
    final response = await api.get(endpoint);
    if (response is List) {
      return response.map((e) => fromJson(e as Map<String, dynamic>)).toList();
    }
    return [];
  }

  /// Obtener por ID (UUID o Integer)
  Future<T> getById(dynamic id) async {
    final response = await api.get('$endpoint/$id');
    return fromJson(response as Map<String, dynamic>);
  }

  /// Crear nuevo registro
  Future<T> create(T item) async {
    final response = await api.post(endpoint, data: item.toJson());
    return fromJson(response as Map<String, dynamic>);
  }

  /// Actualización completa por ID
  Future<T> update(dynamic id, T item) async {
    final response = await api.put('$endpoint/$id', data: item.toJson());
    return fromJson(response as Map<String, dynamic>);
  }

  /// Actualización parcial por ID (solo envía los campos necesarios)
  Future<T> updatePartial(dynamic id, Map<String, dynamic> data) async {
    final response = await api.patch('$endpoint/$id', data: data);
    return fromJson(response as Map<String, dynamic>);
  }

  /// Eliminar registro por ID
  Future<void> delete(dynamic id) async {
    await api.delete('$endpoint/$id');
  }
}
