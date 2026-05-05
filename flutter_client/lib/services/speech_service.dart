import 'package:speech_to_text/speech_to_text.dart' as stt;

class SpeechService {
  final stt.SpeechToText _speech = stt.SpeechToText();
  bool _initialized = false;
  bool _isListening = false;

  bool get isListening => _isListening;
  bool get isAvailable => _initialized;

  Future<bool> initialize() async {
    _initialized = await _speech.initialize();
    return _initialized;
  }

  Future<void> startListening({required Function(String) onResult}) async {
    if (!_initialized) return;
    _isListening = true;
    await _speech.listen(
      onResult: (result) {
        if (result.finalResult) {
          onResult(result.recognizedWords);
          _isListening = false;
        }
      },
      localeId: 'zh_CN',
      listenMode: stt.ListenMode.confirmation,
    );
  }

  Future<void> stopListening() async {
    _isListening = false;
    await _speech.stop();
  }
}
