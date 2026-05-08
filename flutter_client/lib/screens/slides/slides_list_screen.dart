import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/document_provider.dart';
import '../../models/presentation.dart';
import 'slides_view_screen.dart';

class SlidesListScreen extends ConsumerWidget {
  const SlidesListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final presentations = ref.watch(presentationListProvider);

    if (presentations.isEmpty) {
      return const Center(child: Text('暂无演示稿', style: TextStyle(color: Colors.grey)));
    }

    return RefreshIndicator(
      onRefresh: () => ref.read(presentationListProvider.notifier).load(),
      child: ListView.builder(
        itemCount: presentations.length,
        itemBuilder: (ctx, i) => _SlideTile(pres: presentations[i]),
      ),
    );
  }
}

class _SlideTile extends StatelessWidget {
  final Presentation pres;
  const _SlideTile({required this.pres});

  @override
  Widget build(BuildContext context) {
    final time = pres.updatedAt.length >= 16 ? pres.updatedAt.substring(0, 16) : pres.updatedAt;
    final slideCount = pres.slides.length;

    return ListTile(
      leading: const CircleAvatar(
        backgroundColor: Color(0xFFFEF3C7),
        child: Icon(Icons.slideshow, color: Color(0xFFF59E0B)),
      ),
      title: Text(pres.title, style: const TextStyle(fontWeight: FontWeight.w500)),
      subtitle: Text('$slideCount 页幻灯片', style: const TextStyle(fontSize: 13, color: Colors.grey)),
      trailing: Text(time, style: const TextStyle(fontSize: 11, color: Colors.grey)),
      onTap: () {
        Navigator.of(context).push(
          MaterialPageRoute(builder: (_) => SlidesViewScreen(presentation: pres)),
        );
      },
    );
  }
}
