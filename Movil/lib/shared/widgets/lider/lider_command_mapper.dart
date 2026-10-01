import 'dart:convert';
import '../../../core/network/api_magic.dart';
import '../../../core/ai/local_llm_manager.dart';

class ComandoResultado {
  final bool exito;
  final String mensaje;
  final dynamic datos;
  ComandoResultado({required this.exito, required this.mensaje, this.datos});
}

/// Analiza comandos de voz usando Gemini para entender la intención del usuario
/// y ejecutar la llamada correcta a la API mágica.
class LiderCommandMapper {

  // El System Prompt le dice a Gemini/LLM exactamente qué debe hacer:
  // Analizar el texto y devolver SIEMPRE un JSON estructurado.
  static const _systemPrompt = '''
Eres el asistente de comandos de una app móvil. Tu única función es analizar texto de voz y responder ÚNICAMENTE con un JSON válido. Sin texto adicional. Sin markdown. Solo el JSON puro.

El JSON debe tener este formato exacto:
{
  "accion": "listar" | "crear" | "borrar" | "actualizar" | "desconocido",
  "endpoint": "nombre_del_recurso_en_plural_snake_case",
  "nombre": "nombre del elemento si se menciona, o null",
  "anio": número_entero_o_null,
  "explicacion": "frase corta describiendo qué hiciste"
}

Reglas:
- "endpoint" siempre debe ser el recurso en plural (juegos, desarrolladors, plataformas, etc.)
- Si el usuario dice "juego" → "juegos". "desarrollador" → "desarrolladors"
- "nombre" es el nombre específico del elemento que mencionan
- Si el comando no tiene sentido o no hay recurso claro → accion="desconocido"
- Hablen como hablen (coloquial, formal, con errores) → siempre detecta la intención

Ejemplos:
"lista los juegos" → {"accion":"listar","endpoint":"juegos","nombre":null,"anio":null,"explicacion":"Listando todos los juegos"}
"crea un juego llamado God of War del año 2026" → {"accion":"crear","endpoint":"juegos","nombre":"God of War","anio":2026,"explicacion":"Creando juego God of War (2026)"}
"muéstrame los desarrolladores" → {"accion":"listar","endpoint":"desarrolladors","nombre":null,"anio":null,"explicacion":"Listando desarrolladores"}
"quiero ver qué juegos hay" → {"accion":"listar","endpoint":"juegos","nombre":null,"anio":null,"explicacion":"Mostrando lista de juegos"}
"agrega a Nintendo como desarrollador" → {"accion":"crear","endpoint":"desarrolladors","nombre":"Nintendo","anio":null,"explicacion":"Creando desarrollador Nintendo"}
"metele un juego que se llama zelda del 1987" → {"accion":"crear","endpoint":"juegos","nombre":"Zelda","anio":1987,"explicacion":"Creando juego Zelda (1987)"}
''';

  /// Recibe texto de voz libre → IA Local analiza → ejecuta la API correspondiente
  Future<ComandoResultado> procesar(String textoVoz) async {
    final llm = LocalLlmManager();
    
    if (!llm.isReady) {
      if (llm.isDownloading) {
        return ComandoResultado(
          exito: false, 
          mensaje: '⏳ Descargando modelo de IA Local (${(llm.downloadProgress * 100).toStringAsFixed(1)}%). Intenta en un momento.',
        );
      }
      return ComandoResultado(exito: false, mensaje: '⚠️ La IA Local no está lista.');
    }

    try {
      final textoRespuesta = await llm.generateContent(_systemPrompt, textoVoz);

      if (textoRespuesta.isEmpty) {
        return ComandoResultado(exito: false, mensaje: '⚠️ La IA local no respondió. Intenta de nuevo.');
      }

      // Limpiar la respuesta por si viene con bloques de markdown
      final jsonLimpio = textoRespuesta
          .replaceAll('```json', '')
          .replaceAll('```', '')
          .trim();

      final Map<String, dynamic> cmd = jsonDecode(jsonLimpio);
      final accion    = cmd['accion'] as String? ?? 'desconocido';
      final endpoint  = cmd['endpoint'] as String? ?? '';
      final nombre    = cmd['nombre'] as String?;
      final anio      = cmd['anio'] as int?;
      final explicacion = cmd['explicacion'] as String? ?? '';

      if (accion == 'desconocido' || endpoint.isEmpty) {
        return ComandoResultado(exito: false, mensaje: '🤔 No entendí el comando. Prueba ser más específico.');
      }

      // Ejecutar la acción en la API mágica
      return await _ejecutar(accion, endpoint, nombre, anio, explicacion);

    } on FormatException catch (e) {
      return ComandoResultado(exito: false, mensaje: '⚠️ Error parseando respuesta: $e');
    } catch (e) {
      return ComandoResultado(exito: false, mensaje: '❌ Error con Gemini: ${e.toString().replaceAll('Exception: ', '')}');
    }
  }

  Future<ComandoResultado> _ejecutar(
    String accion,
    String endpoint,
    String? nombre,
    int? anio,
    String explicacion,
  ) async {
    switch (accion) {
      case 'listar':
        final datos = await UI.api.noSuchMethodHelper(endpoint).obtener();
        final cantidad = datos is List ? datos.length : '?';
        return ComandoResultado(
          exito: true,
          mensaje: '✅ $explicacion — $cantidad registros encontrados.',
          datos: datos,
        );

      case 'crear':
        if (nombre == null || nombre.isEmpty) {
          return ComandoResultado(
            exito: false,
            mensaje: '⚠️ ¿Cómo se llama? Di: "crea un [recurso] llamado [nombre]".',
          );
        }
        final payload = <String, dynamic>{'nombre': nombre};
        if (anio != null) payload['aolanzamiento'] = anio;
        // idjuego aleatorio para endpoints de juegos
        if (endpoint == 'juegos') payload['idjuego'] = DateTime.now().millisecondsSinceEpoch % 10000;

        final datos = await UI.api.noSuchMethodHelper(endpoint).crear(payload);
        return ComandoResultado(
          exito: true,
          mensaje: '✅ $explicacion.',
          datos: datos,
        );

      case 'borrar':
        return ComandoResultado(
          exito: false,
          mensaje: '⚠️ Para borrar usa el botón 🗑 en la lista. Necesito el ID exacto del registro.',
        );

      case 'actualizar':
        return ComandoResultado(
          exito: false,
          mensaje: '⚠️ Para editar usa el botón ✏️ en la lista.',
        );

      default:
        return ComandoResultado(exito: false, mensaje: '🤔 No reconocí la acción "$accion".');
    }
  }
}
