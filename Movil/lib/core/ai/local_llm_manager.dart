import 'dart:io';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:llama_cpp_dart/llama_cpp_dart.dart';

class LocalLlmManager {
  static final LocalLlmManager _instance = LocalLlmManager._internal();
  factory LocalLlmManager() => _instance;
  LocalLlmManager._internal();

  Llama? _llama;
  bool _isDownloading = false;
  bool _isModelLoaded = false;
  double _downloadProgress = 0.0;

  // Usaremos un modelo ultraligero (Qwen2.5-0.5B-Instruct-Q4_K_M.gguf ~350MB)
  // ideal para tareas básicas de JSON sin reventar la memoria.
  static const String modelUrl = 'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true';
  static const String modelFileName = 'qwen_0.5b_q4.gguf';

  bool get isReady => _isModelLoaded;
  bool get isDownloading => _isDownloading;
  double get downloadProgress => _downloadProgress;

  Future<void> initModel({Function(double)? onProgress}) async {
    if (_isModelLoaded) return;
    if (_isDownloading) return;

    try {
      _isDownloading = true;
      final dir = await getApplicationDocumentsDirectory();
      final modelFile = File('${dir.path}/$modelFileName');

      if (!await modelFile.exists()) {
        final dio = Dio();
        await dio.download(
          modelUrl,
          modelFile.path,
          onReceiveProgress: (rec, total) {
            if (total != -1) {
              _downloadProgress = rec / total;
              if (onProgress != null) onProgress(_downloadProgress);
            }
          },
        );
      }

      _downloadProgress = 1.0;
      if (onProgress != null) onProgress(1.0);

      _llama = Llama(
        modelFile.path,
        ModelParams(),
        ContextParams(),
      );

      _isModelLoaded = true;
    } catch (e) {
      debugPrint("Error inicializando modelo local: $e");
      rethrow;
    } finally {
      _isDownloading = false;
    }
  }

  Future<String> generateContent(String systemPrompt, String userPrompt) async {
    if (!_isModelLoaded || _llama == null) {
      throw Exception('El modelo no está cargado. Llama a initModel() primero.');
    }

    final prompt = "<|im_start|>system\n$systemPrompt<|im_end|>\n<|im_start|>user\n$userPrompt<|im_end|>\n<|im_start|>assistant\n";

    String result = '';
    
    // Llama_cpp_dart requiere setear el prompt
    _llama!.setPrompt(prompt);
    
    // Y luego generar
    await for (final text in _llama!.generateText()) {
      result += text;
    }
    
    return result;
  }
}
