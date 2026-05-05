class Message {
  final String id;
  final String chatId;
  final String senderId;
  final String content;
  final String msgType;
  final String? replyToId;
  final Map<String, dynamic>? cardData;
  final String createdAt;
  final String? recalledAt;

  Message({
    required this.id,
    required this.chatId,
    required this.senderId,
    required this.content,
    this.msgType = 'text',
    this.replyToId,
    this.cardData,
    required this.createdAt,
    this.recalledAt,
  });

  factory Message.fromJson(Map<String, dynamic> json) {
    return Message(
      id: json['id'] ?? '',
      chatId: json['chat_id'] ?? '',
      senderId: json['sender_id'] ?? '',
      content: json['content'] ?? '',
      msgType: json['msg_type'] ?? 'text',
      replyToId: json['reply_to_id'],
      cardData: json['card_data'] is Map ? json['card_data'] : null,
      createdAt: json['created_at'] ?? '',
      recalledAt: json['recalled_at'],
    );
  }

  bool get isAgent => senderId == 'agent';
  bool get isAgentCard => msgType == 'agent_card' && cardData != null;
}
