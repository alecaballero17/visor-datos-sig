/// Contrato JSON de RutasTrabajoController. No se inventan coordenadas faltantes.
class PuntoTrabajo {
  final int id, rutaTrabajoId, orden;
  final int? idCodigoFijo, idLote;
  final String? codigoSuministro, lote, titular, direccion, observaciones;
  final String estado;
  final double? latitud,
      longitud,
      montoDeuda,
      latitudEjecucion,
      longitudEjecucion,
      distanciaAntifraudeMetros,
      lecturaMedidor;
  final DateTime? fechaEjecucion;
  final String? estadoFinal, motivoObservacion, fotosEvidenciasJson;

  PuntoTrabajo.fromJson(Map<String, dynamic> json)
    : id = _id(json['id']),
      rutaTrabajoId = _entero(json['rutaTrabajoId']) ?? 0,
      orden =
          _entero(json['orden']) ??
          (throw const FormatException('Parada sin orden')),
      idCodigoFijo = _entero(json['idCodigoFijo']),
      idLote = _entero(json['idLote']),
      codigoSuministro = json['codigoSuministro'] as String?,
      lote = json['lote'] as String?,
      titular = json['titular'] as String?,
      direccion = json['direccion'] as String?,
      observaciones = json['observaciones'] as String?,
      estado = json['estado'] as String? ?? 'Pendiente',
      latitud = _numero(json['latitud']),
      longitud = _numero(json['longitud']),
      montoDeuda = _numero(json['montoDeuda']),
      latitudEjecucion = _numero(json['latitudEjecucion']),
      longitudEjecucion = _numero(json['longitudEjecucion']),
      distanciaAntifraudeMetros = _numero(json['distanciaAntifraudeMetros']),
      lecturaMedidor = _numero(json['lecturaMedidor']),
      fechaEjecucion = _fecha(json['fechaEjecucion']),
      estadoFinal = json['estadoFinal'] as String?,
      motivoObservacion = json['motivoObservacion'] as String?,
      fotosEvidenciasJson = json['fotosEvidenciasJson'] as String?;

  bool get atendido => const {
    'completado',
    'ejecutado',
    'observado',
    'omitido',
  }.contains(estado.trim().toLowerCase());
  bool get tieneCoordenadas =>
      latitud != null &&
      longitud != null &&
      latitud!.abs() <= 90 &&
      longitud!.abs() <= 180;

  Map<String, dynamic> toJson() => {
    'id': id,
    'rutaTrabajoId': rutaTrabajoId,
    'orden': orden,
    'idCodigoFijo': idCodigoFijo,
    'idLote': idLote,
    'codigoSuministro': codigoSuministro,
    'lote': lote,
    'titular': titular,
    'direccion': direccion,
    'estado': estado,
    'observaciones': observaciones,
    'latitud': latitud,
    'longitud': longitud,
    'montoDeuda': montoDeuda,
    'latitudEjecucion': latitudEjecucion,
    'longitudEjecucion': longitudEjecucion,
    'distanciaAntifraudeMetros': distanciaAntifraudeMetros,
    'lecturaMedidor': lecturaMedidor,
    'fechaEjecucion': fechaEjecucion?.toIso8601String(),
    'estadoFinal': estadoFinal,
    'motivoObservacion': motivoObservacion,
    'fotosEvidenciasJson': fotosEvidenciasJson,
  };
}

class RutaTrabajo {
  final int id;
  final String codigo, titulo, tipo, estado, prioridad, operarioAsignado;
  final String? operarioId,
      creadoPor,
      observaciones,
      partidaNombre,
      geometriaRutaGeoJson;
  final DateTime? fechaCreacion, fechaAsignacion, fechaCompletado;
  final double? partidaLatitud, partidaLongitud, distanciaTotalMetros;
  final int? tiempoEstimadoMinutos;
  final List<PuntoTrabajo> puntos;

  RutaTrabajo.fromJson(Map<String, dynamic> json)
    : id = _id(json['id']),
      codigo = json['codigo'] as String? ?? '',
      titulo = json['titulo'] as String? ?? '',
      tipo = json['tipo'] as String? ?? '',
      estado = json['estado'] as String? ?? 'Pendiente',
      prioridad = json['prioridad'] as String? ?? 'Normal',
      operarioAsignado = json['operarioAsignado'] as String? ?? '',
      operarioId = json['operarioId'] as String?,
      creadoPor = json['creadoPor'] as String?,
      observaciones = json['observaciones'] as String?,
      partidaNombre = json['partidaNombre'] as String?,
      geometriaRutaGeoJson = json['geometriaRutaGeoJson'] as String?,
      fechaCreacion = _fecha(json['fechaCreacion']),
      fechaAsignacion = _fecha(json['fechaAsignacion']),
      fechaCompletado = _fecha(json['fechaCompletado']),
      partidaLatitud = _numero(json['partidaLatitud']),
      partidaLongitud = _numero(json['partidaLongitud']),
      distanciaTotalMetros = _numero(json['distanciaTotalMetros']),
      tiempoEstimadoMinutos = _entero(json['tiempoEstimadoMinutos']),
      puntos = _puntos(json['puntos']);

  int get atendidos => puntos.where((p) => p.atendido).length;
  PuntoTrabajo? get siguiente {
    for (final punto in puntos) {
      if (!punto.atendido) return punto;
    }
    return null;
  }

  bool get pendiente => estado.trim().toLowerCase() == 'pendiente';
  bool get cerrada =>
      const {'completada', 'cancelada'}.contains(estado.trim().toLowerCase());
  bool get puedeAtender =>
      const {'pendiente', 'enprogreso'}.contains(estado.trim().toLowerCase()) &&
      siguiente != null;
  bool perteneceA(String usuario) => [
    operarioId,
    operarioAsignado,
  ].any((op) => op?.trim().toLowerCase() == usuario.trim().toLowerCase());

  Map<String, dynamic> toJson() => {
    'id': id,
    'codigo': codigo,
    'titulo': titulo,
    'tipo': tipo,
    'estado': estado,
    'prioridad': prioridad,
    'operarioAsignado': operarioAsignado,
    'operarioId': operarioId,
    'creadoPor': creadoPor,
    'observaciones': observaciones,
    'partidaNombre': partidaNombre,
    'geometriaRutaGeoJson': geometriaRutaGeoJson,
    'partidaLatitud': partidaLatitud,
    'partidaLongitud': partidaLongitud,
    'distanciaTotalMetros': distanciaTotalMetros,
    'tiempoEstimadoMinutos': tiempoEstimadoMinutos,
    'fechaCreacion': fechaCreacion?.toIso8601String(),
    'fechaAsignacion': fechaAsignacion?.toIso8601String(),
    'fechaCompletado': fechaCompletado?.toIso8601String(),
    'puntos': puntos.map((p) => p.toJson()).toList(),
  };
}

int? _entero(dynamic value) => value is int ? value : int.tryParse('$value');
int _id(dynamic value) {
  final id = _entero(value);
  if (id == null || id <= 0) {
    throw const FormatException('Identificador de ruta/parada inválido');
  }
  return id;
}

double? _numero(dynamic value) {
  final numero = value is num ? value.toDouble() : double.tryParse('$value');
  return numero != null && numero.isFinite ? numero : null;
}

DateTime? _fecha(dynamic value) =>
    value == null ? null : DateTime.parse(value as String);
List<PuntoTrabajo> _puntos(dynamic value) {
  if (value is! List) throw const FormatException('Ruta sin lista de paradas');
  final puntos = value
      .map((p) => PuntoTrabajo.fromJson(Map<String, dynamic>.from(p as Map)))
      .toList();
  if (puntos.any((p) => p.orden <= 0) ||
      puntos.map((p) => p.id).toSet().length != puntos.length ||
      puntos.map((p) => p.orden).toSet().length != puntos.length) {
    throw const FormatException('Secuencia de paradas inválida o duplicada');
  }
  puntos.sort((a, b) => a.orden.compareTo(b.orden));
  return List.unmodifiable(puntos);
}
