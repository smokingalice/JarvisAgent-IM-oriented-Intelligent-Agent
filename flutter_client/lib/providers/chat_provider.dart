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

  MessagesNotifier(this._api, this._ws) : super([]);

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
        }
      } else if (msg['type'] == 'message_recalled') {
        final msgId = msg['data']?['message_id'];
        state = state.where((m) => m.id != msgId).toList();
      }
    });
  }

  Future<void> sendMessage(String chatId, String content) async {
    await _api.post('/chats/$chatId/messages', {'content': content, 'msg_type': 'text'});
  }

  Future<void> triggerAgent(String chatId, String message, String userId) async {
    await _api.post('/agent/chat', {'chat_id': chatId, 'message': message, 'user_id': userId});
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
