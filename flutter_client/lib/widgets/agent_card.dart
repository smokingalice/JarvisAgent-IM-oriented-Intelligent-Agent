import 'package:flutter/material.dart';

class AgentCardWidget extends StatelessWidget {
  final Map<String, dynamic> cardData;
  const AgentCardWidget({super.key, required this.cardData});

  @override
  Widget build(BuildContext context) {
    final type = cardData['type'] ?? 'delivery';
    final title = cardData['title'] ?? '';
    final content = cardData['content'] ?? '';
    final actions = (cardData['actions'] as List<dynamic>?) ?? [];

    IconData icon;
    Color accentColor;
    switch (type) {
      case 'plan':
        icon = Icons.lightbulb_outline;
        accentColor = const Color(0xFFF59E0B);
        break;
      case 'clarification':
        icon = Icons.help_outline;
        accentColor = const Color(0xFF3B82F6);
        break;
      case 'progress':
        icon = Icons.hourglass_top;
        accentColor = const Color(0xFF8B5CF6);
        break;
      default:
        icon = Icons.check_circle_outline;
        accentColor = const Color(0xFF10B981);
    }

    return Card(
      elevation: 2,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: accentColor.withOpacity(0.3)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, color: accentColor, size: 20),
                const SizedBox(width: 8),
                Text(
                  _typeLabel(type),
                  style: TextStyle(
                    fontSize: 12,
                    color: accentColor,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
            if (title.isNotEmpty) ...[
              const SizedBox(height: 8),
              Text(title, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
            ],
            if (content.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(content, style: const TextStyle(fontSize: 14, height: 1.5, color: Colors.black87)),
            ],
            if (actions.isNotEmpty) ...[
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                children: actions.map<Widget>((a) {
                  return OutlinedButton(
                    onPressed: () {},
                    style: OutlinedButton.styleFrom(
                      foregroundColor: accentColor,
                      side: BorderSide(color: accentColor.withOpacity(0.5)),
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                      minimumSize: Size.zero,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    child: Text(a.toString(), style: const TextStyle(fontSize: 12)),
                  );
                }).toList(),
              ),
            ],
          ],
        ),
      ),
    );
  }

  String _typeLabel(String type) {
    switch (type) {
      case 'plan':
        return 'Agent 计划';
      case 'clarification':
        return 'Agent 确认';
      case 'progress':
        return '执行中...';
      default:
        return 'Agent 交付';
    }
  }
}
