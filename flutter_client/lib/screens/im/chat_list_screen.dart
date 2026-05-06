import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/chat_provider.dart';
import '../../models/chat.dart';
import '../../utils/time_utils.dart';
import 'chat_screen.dart';

class ChatListScreen extends ConsumerWidget {
  const ChatListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final chats = ref.watch(chatListProvider);

    if (chats.isEmpty) {
      return const Center(child: Text('暂无会话', style: TextStyle(color: Colors.grey)));
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(chatListProvider.notifier).load(),
      child: ListView.builder(
        itemCount: chats.length,
        itemBuilder: (ctx, i) => _ChatTile(chat: chats[i]),
      ),
    );
  }
}

class _ChatTile extends StatelessWidget {
  final Chat chat;
  const _ChatTile({required this.chat});

  @override
  Widget build(BuildContext context) {
    final isAgent = chat.id.contains('agent');
    final preview = chat.lastMessage?.content ?? '';
    final time = chat.lastMessage?.createdAt ?? '';
    final timeStr = TimeUtils.toLocalDisplay(time);

    return ListTile(
      leading: CircleAvatar(
        backgroundColor: isAgent ? const Color(0xFF4F46E5) : const Color(0xFF818CF8),
        child: Text(
          isAgent ? '🤖' : (chat.displayName.isNotEmpty ? chat.displayName[0].toUpperCase() : '?'),
          style: const TextStyle(fontSize: 18),
        ),
      ),
      title: Text(chat.displayName, style: const TextStyle(fontWeight: FontWeight.w500)),
      subtitle: Text(
        preview.length > 30 ? '${preview.substring(0, 30)}...' : preview,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 13, color: Colors.grey),
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(timeStr, style: const TextStyle(fontSize: 11, color: Colors.grey)),
          if (chat.unreadCount > 0)
            Container(
              margin: const EdgeInsets.only(top: 4),
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF4F46E5),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text('${chat.unreadCount}', style: const TextStyle(fontSize: 11, color: Colors.white)),
            ),
        ],
      ),
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => ChatScreen(chat: chat)),
        );
      },
    );
  }
}
