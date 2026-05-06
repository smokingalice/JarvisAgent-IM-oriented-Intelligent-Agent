import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/chat.dart';
import '../models/message.dart';
import '../services/api_service.dart';
import '../services/ws_service.dart';
import 'auth_provider.dart';

final chatListProvider = StateNotifierProvider<ChatListNotifier, List<Chat>>((ref) {
  return ChatListNotifier(ref.read(apiServiceProvider), ref.read(wsServiceProvider));
});

final activeChatProvider = StateProvider<String?>((ref) => null);

final messagesProvider = StateNotifierProvider<MessagesNotifier, List<Message>>((ref) {
  return MessagesNotifier(ref.read(apiServiceProvider), ref.read(wsServiceProvider));
});

final agentHintProvider = StateProvider<String?>((ref) => null);

class ChatListNotifier extends StateNotifier<List<Chat>> {
  final ApiService _api;
  final WsService _ws;
  StreamSubscription? _sub;

  ChatListNotifier(this._api, this._ws) : super([]);

  Future<void> load() async {
    try {
      final data = await _api.get('/chats') as List;
      state = data.map((j) => Chat.fromJson(j)).toList();
    } catch (_) {}
  }

  void listenWs() {
    _sub?.cancel();
    _sub = _ws.messages.listen((msg) {
      if (msg['type'] == 'new_message' || msg['type'] == 'friend_accepted') {
        load();
      }
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

class MessagesNotifier extends StateNotifier<List<Message>> {
  final ApiService _api;
  final WsService _ws;
  StreamSubscription? _sub;
  String? _chatId;
  String? _currentUserId;
  void Function(String)? _onAgentHint;

  MessagesNotifier(this._api, this._ws) : super([]);

  void setCurrentUser(String userId) {
    _currentUserId = userId;
  }

  void setAgentHintCallback(void Function(String) callback) {
    _onAgentHint = callback;
  }

  Future<void> loadMessages(String chatId) async {
    _chatId = chatId;
    try {
      final data = await _api.get('/chats/$chatId/messages') as List;
      state = data.map((j) => Message.fromJson(j)).toList();
    } catch (_) {}
    _listenWs();
  }

  void _listenWs() {
    _sub?.cancel();
    _sub = _ws.messages.listen((msg) {
      if (msg['type'] == 'new_message') {
        final data = msg['data'] as Map<String, dynamic>;
        if (data['chat_id'] == _chatId) {
          final newMsg = Message.fromJson(data);
          if (!state.any((m) => m.id == newMsg.id)) {
            state = [...state, newMsg];
          }
          // Trigger agent summary only for messages from others
          final senderId = data['sender_id'] as String?;
          if (senderId != null && senderId != _currentUserId && senderId != 'agent') {
            _triggerAgentSummary(data['chat_id'], data['content'] ?? '');
          }
        }
      } else if (msg['type'] == 'message_recalled') {
        final msgId = msg['data']?['message_id'];
        state = state.where((m) => m.id != msgId).toList();
      }
    });
  }

  Future<void> _triggerAgentSummary(String chatId, String content) async {
    try {
      final res = await _api.post('/agent/chat', {
        'chat_id': chatId,
        'message': content,
        'user_id': _currentUserId ?? '',
        'mode': 'summary',
      });
      if (res is Map && res['summary'] != null) {
        _onAgentHint?.call(res['summary'] as String);
      }
    } catch (_) {}
  }

  Future<void> sendMessage(String chatId, String content) async {
    await _api.post('/chats/$chatId/messages', {'content': content, 'msg_type': 'text'});
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
