import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import '../../models/document.dart';
import '../../services/api_service.dart';

class DocViewScreen extends StatelessWidget {
  final Document doc;
  const DocViewScreen({super.key, required this.doc});

  Future<void> _export(BuildContext context, String format) async {
    try {
      final api = ApiService();
      await api.get('/documents/${doc.id}/export?format=$format');
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('导出成功（$format）'), backgroundColor: Colors.green),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('导出失败: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(doc.title),
        actions: [
          PopupMenuButton<String>(
            icon: const Icon(Icons.download),
            onSelected: (format) => _export(context, format),
            itemBuilder: (_) => const [
              PopupMenuItem(value: 'md', child: Text('导出 Markdown')),
              PopupMenuItem(value: 'html', child: Text('导出 HTML')),
            ],
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: Markdown(
          data: doc.content,
          selectable: true,
          styleSheet: MarkdownStyleSheet(
            h1: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
            h2: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
            p: const TextStyle(fontSize: 15, height: 1.6),
          ),
        ),
      ),
    );
  }
}
