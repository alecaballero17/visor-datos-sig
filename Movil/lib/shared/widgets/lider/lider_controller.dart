import 'package:flutter/material.dart';
import 'package:speech_to_text/speech_to_text.dart';
import 'package:permission_handler/permission_handler.dart';
import 'wave_painter.dart';
import 'lider_command_mapper.dart';
import '../../../core/ai/local_llm_manager.dart';

/// Controlador del asistente Líder.
/// Maneja el STT, el estado de la ola, y el wake word "oye líder".
class LiderController extends ChangeNotifier {
  static final LiderController _instance = LiderController._internal();
  factory LiderController() => _instance;
  LiderController._internal();

  final SpeechToText _stt = SpeechToText();
  final LiderCommandMapper _mapper = LiderCommandMapper();

  LiderEstado estado = LiderEstado.inactivo;
  String textoEscuchado = '';
  String mensajeResultado = '';
  dynamic datosResultado;
  double amplitudOnda = 0.3;

  bool _sttListo = false;
  bool _wakeWordActivo = false;
  bool _inicializando = false;

  // ─────────────────────────────────────────────
  // INICIALIZACIÓN (idempotente y segura)
  // ─────────────────────────────────────────────
  Future<void> inicializar() async {
    if (_sttListo || _inicializando) return;
    _inicializando = true;

    // Pedir permiso de micrófono explícitamente en Android
    final status = await Permission.microphone.request();
    if (status.isDenied || status.isPermanentlyDenied) {
      _inicializando = false;
      return;
    }

    _sttListo = await _stt.initialize(
      onError: (e) => _manejarError('Error de voz: ${e.errorMsg}'),
      onStatus: (s) => _manejarStatus(s),
    );
    
    // Iniciar la descarga/carga del modelo LLM local en background
    LocalLlmManager().initModel(
      onProgress: (progreso) {
        if (estado != LiderEstado.escuchando && estado != LiderEstado.pensando) {
          if (progreso < 1.0) {
            mensajeResultado = 'Descargando IA... ${(progreso * 100).toStringAsFixed(0)}%';
            if (estado != LiderEstado.error) estado = LiderEstado.resultado;
            notifyListeners();
          } else {
            mensajeResultado = 'IA Lista';
            Future.delayed(const Duration(seconds: 2), cerrar);
          }
        }
      }
    );

    _inicializando = false;

    if (_sttListo) iniciarEscuchaWakeWord();
  }

  // ─────────────────────────────────────────────
  // WAKE WORD — Escucha silenciosa en segundo plano
  // ─────────────────────────────────────────────
  Future<void> iniciarEscuchaWakeWord() async {
    if (!_sttListo || _wakeWordActivo || estado != LiderEstado.inactivo) return;
    _wakeWordActivo = true;

    _stt.listen(
      onResult: (resultado) {
        final texto = resultado.recognizedWords.toLowerCase();
        if (texto.contains('líder') || texto.contains('lider')) {
          _wakeWordActivo = false;
          activar();
        }
      },
      listenOptions: SpeechListenOptions(
        listenFor: const Duration(seconds: 60),
        pauseFor: const Duration(seconds: 8),
        localeId: 'es_MX',
        partialResults: true,
        listenMode: ListenMode.dictation,
        cancelOnError: false,
      ),
    );
  }

  // ─────────────────────────────────────────────
  // ACTIVACIÓN MANUAL O POR WAKE WORD
  // ─────────────────────────────────────────────
  Future<void> activar() async {
    // Asegurarse de que el STT esté listo antes de hacer cualquier cosa
    if (!_sttListo) {
      await inicializar();
      if (!_sttListo) {
        estado = LiderEstado.error;
        mensajeResultado = '⚠️ El micrófono no está disponible. Verifica los permisos.';
        notifyListeners();
        Future.delayed(const Duration(seconds: 3), cerrar);
        return;
      }
    }

    estado = LiderEstado.escuchando;
    textoEscuchado = '';
    mensajeResultado = '';
    datosResultado = null;
    amplitudOnda = 0.4;
    notifyListeners();

    // Detener cualquier escucha previa antes de iniciar una nueva
    await _stt.stop();
    await Future.delayed(const Duration(milliseconds: 200));

    _stt.listen(
      onResult: (resultado) {
        textoEscuchado = resultado.recognizedWords;
        notifyListeners();

        if (resultado.finalResult) {
          _procesarComando(textoEscuchado);
        }
      },
      // ← LAS OLAS REACCIONAN A TU VOZ EN TIEMPO REAL
      onSoundLevelChange: (nivel) {
        // nivel va de -2.0 (silencio) a 10.0 (grito) aproximadamente
        // Lo normalizamos a un rango 0.2 - 1.0 para la amplitud
        amplitudOnda = 0.2 + ((nivel + 2.0) / 12.0).clamp(0.0, 0.8);
        notifyListeners();
      },
      listenOptions: SpeechListenOptions(
        listenFor: const Duration(seconds: 15),
        pauseFor: const Duration(seconds: 3),
        localeId: 'es_MX',
        partialResults: true,
        listenMode: ListenMode.dictation,
        cancelOnError: false,
      ),
    );
  }

  // ─────────────────────────────────────────────
  // PROCESAMIENTO DEL COMANDO
  // ─────────────────────────────────────────────
  Future<void> _procesarComando(String texto) async {
    if (texto.trim().isEmpty) {
      cerrar();
      return;
    }

    estado = LiderEstado.pensando;
    amplitudOnda = 0.9; // Olas bien activas mientras "piensa"
    notifyListeners();

    final resultado = await _mapper.procesar(texto);

    estado = resultado.exito ? LiderEstado.resultado : LiderEstado.error;
    mensajeResultado = resultado.mensaje;
    datosResultado = resultado.datos;
    amplitudOnda = 0.4;
    notifyListeners();

    // Cierra automáticamente después de 4 segundos
    await Future.delayed(const Duration(seconds: 4));
    cerrar();
  }

  void _manejarStatus(String status) {
    // Cuando el STT termina mientras estamos inactivos → reiniciar wake word
    if ((status == 'done' || status == 'notListening') && estado == LiderEstado.inactivo) {
      _wakeWordActivo = false;
      Future.delayed(const Duration(milliseconds: 800), iniciarEscuchaWakeWord);
    }
    // Si terminó mientras escuchaba un comando sin resultado → cerrar limpio
    if (status == 'done' && estado == LiderEstado.escuchando) {
      if (textoEscuchado.trim().isEmpty) cerrar();
    }
  }

  void _manejarError(String msg) {
    // Ignorar errores menores del wake word listener
    if (estado == LiderEstado.inactivo) {
      _wakeWordActivo = false;
      Future.delayed(const Duration(seconds: 2), iniciarEscuchaWakeWord);
      return;
    }
    estado = LiderEstado.error;
    mensajeResultado = msg;
    notifyListeners();
    Future.delayed(const Duration(seconds: 3), cerrar);
  }

  // ─────────────────────────────────────────────
  // CERRAR
  // ─────────────────────────────────────────────
  void cerrar() {
    _stt.stop();
    estado = LiderEstado.inactivo;
    amplitudOnda = 0.3;
    textoEscuchado = '';
    notifyListeners();
    // Reactivar wake word
    _wakeWordActivo = false;
    Future.delayed(const Duration(milliseconds: 500), iniciarEscuchaWakeWord);
  }
}
