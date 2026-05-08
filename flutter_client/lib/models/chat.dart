import 'message.dart';

class Chat {
  final String id;
  final String type;
  final String name;
  final String displayName;
  final Message? lastMessage;
  final int unreadCount;

  Chat({
    required this.id,
    required this.type,
    required this.name,
    required this.displayName,
    this.lastMessage,
    this.unreadCount = 0,
  });

  factory Chat.fromJson(Map<String, dynamic> json) {
    return Chat(
      id: json['id'] ?? '',
      type: json['type'] ?? 'private',
      name: json['name'] ?? '',
      displayName: json['display_name'] ?? json['name'] ?? '',
      lastMessage: json['last_message'] != null ? Message.fromJson(json['last_message']) : null,
      unreadCount: json['unread_count'] ?? 0,
    );
  }
}
