import '../../../../core/network/api_provider.dart';
import 'mapa_endpoints.dart';

class MapaService {
  Future<dynamic> obtenerCapas() async {
    return await api.get(MapaEndpoints.capas);
  }

  Future<dynamic> obtenerGeoJsonCapa(String capa, String bbox) async {
    return await api.get(MapaEndpoints.geojson(capa, bbox));
  }

  Future<dynamic> obtenerFeature(String capa, String id) async {
    return await api.get(MapaEndpoints.capaId(capa, id));
  }
}
