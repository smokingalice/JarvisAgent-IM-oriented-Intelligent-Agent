import 'package:flutter/material.dart';
import '../../models/presentation.dart';
import '../../widgets/slide_renderer.dart';

class SlidesViewScreen extends StatefulWidget {
  final Presentation presentation;
  const SlidesViewScreen({super.key, required this.presentation});

  @override
  State<SlidesViewScreen> createState() => _SlidesViewScreenState();
}

class _SlidesViewScreenState extends State<SlidesViewScreen> {
  int _currentIndex = 0;
  late final PageController _pageCtrl;

  @override
  void initState() {
    super.initState();
    _pageCtrl = PageController();
  }

  @override
  void dispose() {
    _pageCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final slides = widget.presentation.slides;

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.presentation.title),
        actions: [
          Center(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text(
                '${_currentIndex + 1} / ${slides.length}',
                style: const TextStyle(fontSize: 14),
              ),
            ),
          ),
        ],
      ),
      body: Column(
        children: [
          Expanded(
            child: PageView.builder(
              controller: _pageCtrl,
              itemCount: slides.length,
              onPageChanged: (i) => setState(() => _currentIndex = i),
              itemBuilder: (ctx, i) => Padding(
                padding: const EdgeInsets.all(16),
                child: SlideRenderer(slide: slides[i]),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  onPressed: _currentIndex > 0
                      ? () => _pageCtrl.previousPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut)
                      : null,
                  icon: const Icon(Icons.arrow_back_ios),
                ),
                Row(
                  children: List.generate(slides.length, (i) => Container(
                    width: 8,
                    height: 8,
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: i == _currentIndex ? const Color(0xFF4F46E5) : Colors.grey.shade300,
                    ),
                  )),
                ),
                IconButton(
                  onPressed: _currentIndex < slides.length - 1
                      ? () => _pageCtrl.nextPage(duration: const Duration(milliseconds: 300), curve: Curves.easeInOut)
                      : null,
                  icon: const Icon(Icons.arrow_forward_ios),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
