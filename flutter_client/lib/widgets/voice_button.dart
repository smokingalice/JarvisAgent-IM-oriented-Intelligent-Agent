import 'package:flutter/material.dart';
import '../services/speech_service.dart';

class VoiceButton extends StatefulWidget {
  final SpeechService speechService;
  final void Function(String text) onResult;
  const VoiceButton({super.key, required this.speechService, required this.onResult});

  @override
  State<VoiceButton> createState() => _VoiceButtonState();
}

class _VoiceButtonState extends State<VoiceButton> {
  bool _isListening = false;

  void _toggle() async {
    if (_isListening) {
      await widget.speechService.stopListening();
      setState(() => _isListening = false);
    } else {
      setState(() => _isListening = true);
      await widget.speechService.startListening(
        onResult: (text) {
          setState(() => _isListening = false);
          if (text.isNotEmpty) {
            widget.onResult(text);
          }
        },
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: _toggle,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _isListening ? Colors.red.shade50 : Colors.grey.shade100,
          border: Border.all(
            color: _isListening ? Colors.red : Colors.grey.shade300,
            width: _isListening ? 2 : 1,
          ),
        ),
        child: Icon(
          _isListening ? Icons.mic : Icons.mic_none,
          color: _isListening ? Colors.red : Colors.grey.shade600,
          size: 20,
        ),
      ),
    );
  }
}
