import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../models/chat.dart';
import '../../models/message.dart';
import '../../providers/auth_provider.dart';
import '../../providers/chat_provider.dart';
import '../../services/speech_service.dart';
import '../../widgets/agent_card.dart';
import '../../widgets/voice_button.dart';

class ChatScreen extends ConsumerStatefulWidget {
  final Chat chat;
  const ChatScreen({super.key, required this.chat});

  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _inputCtrl = TextEditingController();
  final _scrollCtrl = ScrollController();
  final _speechService = SpeechService();
  bool _speechReady = false;
  String? _agentHint;

  @override
  void initState() {
    super.initState();
    final userId = ref.read(authProvider).user?.id ?? '';
    final notifier = ref.read(messagesProvider.notifier);
    notifier.setCurrentUser(userId);
    notifier.setAgentHintCallback((hint) {
      if (mounted) setState(() => _agentHint = hint);
      Future.delayed(const Duration(seconds: 8), () {
        if (mounted) setState(() => _agentHint = null);
      });
    });
    notifier.loadMessages(widget.chat.id);
    _initSpeech();
  }

  Future<void> _initSpeech() async {
    _speechReady = await _speechService.initialize();
    if (mounted) setState(() {});
  }

  void _scrollToBottom() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollCtrl.hasClients && mounted) {
        _scrollCtrl.jumpTo(_scrollCtrl.position.maxScrollExtent);
      }
    });
  }

  Future<void> _send() async {
    final text = _inputCtrl.text.trim();
    if (text.isEmpty) return;
    _inputCtrl.clear();

    final notifier = ref.read(messagesProvider.notifier);
    await notifier.sendMessage(widget.chat.id, text);

    _scrollToBottom();
  }

  @override
  Widget build(BuildContext context) {
    final messages = ref.watch(messagesProvider);
    final userId = ref.watch(authProvider).user?.id ?? '';

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.chat.displayName),
        centerTitle: true,
      ),
      body: Column(
        children: [
          Expanded(
            child: ListView.builder(
              controller: _scrollCtrl,
              padding: const EdgeInsets.all(12),
              itemCount: messages.length,
              itemBuilder: (ctx, i) => _MessageBubble(
                message: messages[i],
                isSelf: messages[i].senderId == userId,
              ),
            ),
          ),
          if (_agentHint != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              color: const Color(0xFFF5F3FF),
              child: Text(
                '✨ $_agentHint',
                style: const TextStyle(fontSize: 11, color: Color(0xFF6B7280), fontStyle: FontStyle.italic),
              ),
            ),
          _buildComposer(),
        ],
      ),
    );
  }

  Widget _buildComposer() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(top: BorderSide(color: Colors.grey.shade200)),
      ),
      child: Row(
        children: [
          if (_speechReady)
            VoiceButton(
              speechService: _speechService,
              onResult: (text) {
                _inputCtrl.text = text;
                _send();
              },
            ),
          const SizedBox(width: 8),
          Expanded(
            child: TextField(
              controller: _inputCtrl,
              decoration: const InputDecoration(
                hintText: '输入消息或语音指令...',
                border: OutlineInputBorder(),
                contentPadding: EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                isDense: true,
              ),
              maxLines: 3,
              minLines: 1,
              onSubmitted: (_) => _send(),
            ),
          ),
          const SizedBox(width: 8),
          IconButton.filled(
            onPressed: _send,
            icon: const Icon(Icons.send, size: 20),
          ),
        ],
      ),
    );
  }
}

class _MessageBubble extends StatelessWidget {
  final Message message;
  final bool isSelf;
  const _MessageBubble({required this.message, required this.isSelf});

  @override
  Widget build(BuildContext context) {
    if (message.isAgentCard) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: AgentCardWidget(cardData: message.cardData!),
      );
    }

    final isAgent = message.isAgent;
    final alignment = isSelf ? CrossAxisAlignment.end : CrossAxisAlignment.start;
    final bgColor = isSelf
        ? const Color(0xFF4F46E5)
        : isAgent
            ? const Color(0xFFEDE9FE)
            : Colors.white;
    final textColor = isSelf ? Colors.white : Colors.black87;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: alignment,
        children: [
          if (!isSelf)
            Padding(
              padding: const EdgeInsets.only(bottom: 2, left: 4),
              child: Text(
                isAgent ? 'JarvisAgent' : message.senderId,
                style: const TextStyle(fontSize: 11, color: Colors.grey),
              ),
            ),
          Container(
            constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.75),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: bgColor,
              borderRadius: BorderRadius.circular(12),
              border: isAgent ? Border.all(color: const Color(0xFFC4B5FD)) : null,
              boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.05), blurRadius: 2, offset: const Offset(0, 1))],
            ),
            child: Text(message.content, style: TextStyle(color: textColor, fontSize: 14, height: 1.5)),
          ),
        ],
      ),
    );
  }
}
