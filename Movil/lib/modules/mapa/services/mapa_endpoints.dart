class MapaEndpoints {
  static const String capas = '/capas';
  static String geojson(String capa, String bbox) => '/capas/$capa/geojson?bbox=$bbox';
  static String capaId(String capa, String id) => '/capas/$capa/$id';
}
