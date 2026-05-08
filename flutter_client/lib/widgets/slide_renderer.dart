import 'package:flutter/material.dart';

class SlideRenderer extends StatelessWidget {
  final Map<String, dynamic> slide;
  final double aspectRatio;
  const SlideRenderer({super.key, required this.slide, this.aspectRatio = 16 / 9});

  @override
  Widget build(BuildContext context) {
    final layout = slide['layout'] ?? 'title';
    final title = slide['title'] ?? '';
    final body = slide['body'] ?? '';
    final bullets = (slide['bullets'] as List<dynamic>?) ?? [];
    final bgColor = _parseColor(slide['bgColor']) ?? Colors.white;

    return AspectRatio(
      aspectRatio: aspectRatio,
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(8),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.1), blurRadius: 4, offset: const Offset(0, 2))],
        ),
        padding: const EdgeInsets.all(24),
        child: _buildLayout(layout, title, body, bullets),
      ),
    );
  }

  Widget _buildLayout(String layout, String title, String body, List<dynamic> bullets) {
    switch (layout) {
      case 'title':
        return Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(title, style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold), textAlign: TextAlign.center),
              if (body.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(body, style: const TextStyle(fontSize: 16, color: Colors.black54), textAlign: TextAlign.center),
              ],
            ],
          ),
        );
      case 'bullets':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            ...bullets.map((b) => Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• ', style: TextStyle(fontSize: 16)),
                  Expanded(child: Text(b.toString(), style: const TextStyle(fontSize: 15, height: 1.4))),
                ],
              ),
            )),
          ],
        );
      case 'two-column':
        final left = body;
        final right = bullets.isNotEmpty ? bullets.join('\n') : '';
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            const SizedBox(height: 16),
            Expanded(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Expanded(child: Text(left, style: const TextStyle(fontSize: 14, height: 1.5))),
                  const SizedBox(width: 16),
                  Expanded(child: Text(right, style: const TextStyle(fontSize: 14, height: 1.5))),
                ],
              ),
            ),
          ],
        );
      default:
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title.isNotEmpty) Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.bold)),
            if (title.isNotEmpty) const SizedBox(height: 12),
            Expanded(child: SingleChildScrollView(child: Text(body, style: const TextStyle(fontSize: 14, height: 1.5)))),
          ],
        );
    }
  }

  Color? _parseColor(dynamic c) {
    if (c == null) return null;
    if (c is String && c.startsWith('#') && c.length == 7) {
      return Color(int.parse('FF${c.substring(1)}', radix: 16));
    }
    return null;
  }
}
