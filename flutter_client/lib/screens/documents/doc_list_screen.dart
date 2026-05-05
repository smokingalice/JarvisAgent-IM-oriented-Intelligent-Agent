import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/document_provider.dart';
import '../../models/document.dart';
import 'doc_view_screen.dart';

class DocListScreen extends ConsumerWidget {
  const DocListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final docs = ref.watch(documentListProvider);

    if (docs.isEmpty) {
      return const Center(child: Text('暂无文档', style: TextStyle(color: Colors.grey)));
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(documentListProvider.notifier).load(),
      child: ListView.builder(
        itemCount: docs.length,
        itemBuilder: (ctx, i) => _DocTile(doc: docs[i]),
      ),
    );
  }
}

class _DocTile extends StatelessWidget {
  final Document doc;
  const _DocTile({required this.doc});

  @override
  Widget build(BuildContext context) {
    final time = doc.updatedAt.length >= 16 ? doc.updatedAt.substring(0, 16) : doc.updatedAt;
    final preview = doc.content.length > 60 ? '${doc.content.substring(0, 60)}...' : doc.content;

    return ListTile(
      leading: const CircleAvatar(
        backgroundColor: Color(0xFFEDE9FE),
        child: Icon(Icons.description, color: Color(0xFF7C3AED)),
      ),
      title: Text(doc.title, style: const TextStyle(fontWeight: FontWeight.w500)),
      subtitle: Text(preview, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, color: Colors.grey)),
      trailing: Text(time, style: const TextStyle(fontSize: 11, color: Colors.grey)),
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => DocViewScreen(doc: doc)),
        );
      },
    );
  }
}
