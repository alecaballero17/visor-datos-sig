/// Contrato de la ficha de agua potable (AguaPotableController del backend):
///
///   GET /api/agua-potable/codigos/{idCodigo}   → un medidor (404 si no existe)
///   GET /api/agua-potable/lotes/{idLote}       → los medidores de un lote (registros vacio = sin agua)
///
/// Respuesta:
/// ```json
/// {
///   "tieneAgua": true,
///   "criterioDisponibilidad": "...",
///   "fuente": "Exp_CodigoFijo_4326.shp",
///   "registros": [
///     { "idCodigo": 12, "codigoFijo": 3456, "codigoSig": "A-12", "nombreRegistrado": "Juan Perez",
///       "idLote": 8, "numeroLote": "5", "uv": "12", "manzana": "34",
///       "longitud": -60.96, "latitud": -16.40,
///       "estadoVerificado": true, "estadoServicio": 1 }
///   ],
///   "datosNoDisponibles": ["Numero de medidor", "..."]
/// }
/// ```
/// Los datos del titular y del medidor estan DENTRO de `registros`, no en el primer nivel.
class FichaAgua {
  final bool tieneAgua;
  final String? criterioDisponibilidad;
  final String? fuente;
  final List<RegistroAgua> registros;
  final List<String> datosNoDisponibles;

  const FichaAgua({
    required this.tieneAgua,
    this.criterioDisponibilidad,
    this.fuente,
    this.registros = const [],
    this.datosNoDisponibles = const [],
  });

  factory FichaAgua.fromJson(Map<String, dynamic> json) {
    final lista = json['registros'];
    return FichaAgua(
      tieneAgua: json['tieneAgua'] == true,
      criterioDisponibilidad: _texto(json['criterioDisponibilidad']),
      fuente: _texto(json['fuente']),
      registros: lista is List
          ? lista.whereType<Map>().map((r) => RegistroAgua.fromJson(Map<String, dynamic>.from(r))).toList()
          : const [],
      datosNoDisponibles: (json['datosNoDisponibles'] is List)
          ? (json['datosNoDisponibles'] as List).map((e) => e.toString()).toList()
          : const [],
    );
  }

  /// Primer medidor (el unico cuando se consulta por codigo).
  RegistroAgua? get principal => registros.isEmpty ? null : registros.first;

  /// Titulares distintos registrados (un lote puede tener varios medidores).
  List<String> get titulares {
    final vistos = <String>{};
    for (final r in registros) {
      final n = r.nombreRegistrado;
      if (n != null) vistos.add(n);
    }
    return vistos.toList();
  }

  /// Texto para mostrar: "Juan Perez", "Juan Perez y 2 mas" o null si no hay titular.
  String? get titularResumen {
    final t = titulares;
    if (t.isEmpty) return null;
    return t.length == 1 ? t.first : '${t.first} y ${t.length - 1} más';
  }
}

class RegistroAgua {
  final int idCodigo;
  final String? codigoFijo;
  final String? codigoSig;
  final String? nombreRegistrado;
  final int? idLote;
  final String? numeroLote;
  final String? uv;
  final String? manzana;
  final double? longitud;
  final double? latitud;
  final bool estadoVerificado;

  /// Solo viene si el estado esta verificado.
  /// 0=Para reconexion, 1=Normal, 2=Para corte, 3=Cortado, 4=Baja parcial, 5=Baja total.
  final int? estadoServicio;

  const RegistroAgua({
    required this.idCodigo,
    this.codigoFijo,
    this.codigoSig,
    this.nombreRegistrado,
    this.idLote,
    this.numeroLote,
    this.uv,
    this.manzana,
    this.longitud,
    this.latitud,
    this.estadoVerificado = false,
    this.estadoServicio,
  });

  factory RegistroAgua.fromJson(Map<String, dynamic> json) => RegistroAgua(
        idCodigo: _entero(json['idCodigo']) ?? 0,
        codigoFijo: _texto(json['codigoFijo']),
        codigoSig: _texto(json['codigoSig']),
        nombreRegistrado: _texto(json['nombreRegistrado']),
        idLote: _entero(json['idLote']),
        numeroLote: _texto(json['numeroLote']),
        uv: _texto(json['uv']),
        manzana: _texto(json['manzana']),
        longitud: _numero(json['longitud']),
        latitud: _numero(json['latitud']),
        estadoVerificado: json['estadoVerificado'] == true,
        estadoServicio: _entero(json['estadoServicio']),
      );

  static const Map<int, String> nombresEstado = {
    0: 'Para reconexión',
    1: 'Normal',
    2: 'Para corte',
    3: 'Cortado',
    4: 'Baja parcial',
    5: 'Baja total',
  };

  String get estadoTexto {
    if (!estadoVerificado || estadoServicio == null) return 'Estado sin verificar';
    return nombresEstado[estadoServicio] ?? 'Estado desconocido ($estadoServicio)';
  }

  /// Con suministro activo (normal o pendiente de corte).
  bool get conServicio => estadoServicio == 1 || estadoServicio == 2;
}

String? _texto(Object? v) {
  if (v == null) return null;
  final s = v.toString().trim();
  return s.isEmpty ? null : s;
}

int? _entero(Object? v) => v is num ? v.toInt() : int.tryParse(v?.toString() ?? '');

double? _numero(Object? v) => v is num ? v.toDouble() : double.tryParse(v?.toString() ?? '');
