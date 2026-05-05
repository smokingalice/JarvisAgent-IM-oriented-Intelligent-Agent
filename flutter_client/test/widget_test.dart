import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:jarvis_client/main.dart';

void main() {
  testWidgets('App launches with login screen', (WidgetTester tester) async {
    await tester.pumpWidget(const ProviderScope(child: JarvisApp()));
    await tester.pump();
    expect(find.text('JarvisAgent'), findsAny);
  });
}
