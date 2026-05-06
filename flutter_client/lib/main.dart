import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'providers/auth_provider.dart';
import 'screens/auth/login_screen.dart';
import 'screens/im/chat_list_screen.dart';
import 'screens/documents/doc_list_screen.dart';
import 'screens/slides/slides_list_screen.dart';
import 'screens/friends/friends_screen.dart';
import 'providers/chat_provider.dart';
import 'providers/document_provider.dart';

void main() {
  runApp(const ProviderScope(child: JarvisApp()));
}

class JarvisApp extends StatelessWidget {
  const JarvisApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'JarvisAgent',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF4F46E5)),
        useMaterial3: true,
      ),
      home: const AppShell(),
    );
  }
}

class AppShell extends ConsumerStatefulWidget {
  const AppShell({super.key});

  @override
  ConsumerState<AppShell> createState() => _AppShellState();
}

class _AppShellState extends ConsumerState<AppShell> {
  @override
  void initState() {
    super.initState();
    ref.read(authProvider.notifier).tryAutoLogin();
  }

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authProvider);

    if (auth.isLoading) {
      return const Scaffold(body: Center(child: CircularProgressIndicator()));
    }

    if (!auth.isLoggedIn) {
      return const LoginScreen();
    }

    return const MainNavigation();
  }
}

class MainNavigation extends ConsumerStatefulWidget {
  const MainNavigation({super.key});

  @override
  ConsumerState<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends ConsumerState<MainNavigation> {
  int _currentIndex = 0;

  final _screens = const [
    ChatListScreen(),
    DocListScreen(),
    SlidesListScreen(),
    FriendsScreen(),
  ];

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  void _loadData() {
    ref.read(chatListProvider.notifier).load();
    ref.read(chatListProvider.notifier).listenWs();
    ref.read(documentListProvider.notifier).load();
    ref.read(documentListProvider.notifier).listenWs();
    ref.read(presentationListProvider.notifier).load();
    ref.read(presentationListProvider.notifier).listenWs();
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;

    return Scaffold(
      appBar: AppBar(
        title: const Text('JarvisAgent'),
        actions: [
          if (user != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Center(child: Text(user.name, style: const TextStyle(fontSize: 14))),
            ),
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => ref.read(authProvider.notifier).logout(),
          ),
        ],
      ),
      body: _screens[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (i) => setState(() => _currentIndex = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.chat), label: 'IM'),
          NavigationDestination(icon: Icon(Icons.description), label: '文档'),
          NavigationDestination(icon: Icon(Icons.slideshow), label: '演示稿'),
          NavigationDestination(icon: Icon(Icons.people), label: '好友'),
        ],
      ),
    );
  }
}
