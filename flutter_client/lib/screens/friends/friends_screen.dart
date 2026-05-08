import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/api_service.dart';

final _friendsProvider = StateNotifierProvider<_FriendsNotifier, _FriendsState>((ref) => _FriendsNotifier());

class _FriendsState {
  final List<Map<String, dynamic>> friends;
  final List<Map<String, dynamic>> requests;
  final bool isLoading;
  _FriendsState({this.friends = const [], this.requests = const [], this.isLoading = false});
  _FriendsState copyWith({List<Map<String, dynamic>>? friends, List<Map<String, dynamic>>? requests, bool? isLoading}) {
    return _FriendsState(friends: friends ?? this.friends, requests: requests ?? this.requests, isLoading: isLoading ?? this.isLoading);
  }
}

class _FriendsNotifier extends StateNotifier<_FriendsState> {
  _FriendsNotifier() : super(_FriendsState());
  final _api = ApiService();

  Future<void> load() async {
    state = state.copyWith(isLoading: true);
    try {
      final friends = await _api.get('/friends') as List;
      final requests = await _api.get('/friends/requests') as List;
      state = state.copyWith(
        friends: friends.cast<Map<String, dynamic>>(),
        requests: requests.cast<Map<String, dynamic>>(),
        isLoading: false,
      );
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> search(String query) async {
    if (query.isEmpty) return;
    try {
      final results = await _api.get('/friends/search?q=$query') as List;
      state = state.copyWith(friends: results.cast<Map<String, dynamic>>());
    } catch (_) {}
  }

  Future<void> sendRequest(String userId) async {
    await _api.post('/friends/request', {'to_user_id': userId});
    await load();
  }

  Future<void> acceptRequest(String requestId) async {
    await _api.post('/friends/accept', {'request_id': requestId});
    await load();
  }
}

class FriendsScreen extends ConsumerStatefulWidget {
  const FriendsScreen({super.key});

  @override
  ConsumerState<FriendsScreen> createState() => _FriendsScreenState();
}

class _FriendsScreenState extends ConsumerState<FriendsScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabCtrl;
  final _searchCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
    ref.read(_friendsProvider.notifier).load();
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    _searchCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(_friendsProvider);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            controller: _searchCtrl,
            decoration: InputDecoration(
              hintText: '搜索用户...',
              prefixIcon: const Icon(Icons.search),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16),
              isDense: true,
            ),
            onSubmitted: (q) => ref.read(_friendsProvider.notifier).search(q),
          ),
        ),
        TabBar(
          controller: _tabCtrl,
          tabs: [
            Tab(text: '好友 (${state.friends.length})'),
            Tab(text: '请求 (${state.requests.length})'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabCtrl,
            children: [
              _buildFriendsList(state),
              _buildRequestsList(state),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildFriendsList(_FriendsState state) {
    if (state.friends.isEmpty) {
      return const Center(child: Text('暂无好友', style: TextStyle(color: Colors.grey)));
    }
    return RefreshIndicator(
      onRefresh: () => ref.read(_friendsProvider.notifier).load(),
      child: ListView.builder(
        itemCount: state.friends.length,
        itemBuilder: (ctx, i) {
          final f = state.friends[i];
          final name = f['name'] ?? f['username'] ?? '';
          final id = f['id'] ?? f['user_id'] ?? '';
          return ListTile(
            leading: CircleAvatar(
              backgroundColor: const Color(0xFF818CF8),
              child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Colors.white)),
            ),
            title: Text(name),
            subtitle: Text(id, style: const TextStyle(fontSize: 12, color: Colors.grey)),
            trailing: IconButton(
              icon: const Icon(Icons.person_add, size: 20),
              onPressed: () => ref.read(_friendsProvider.notifier).sendRequest(id),
            ),
          );
        },
      ),
    );
  }

  Widget _buildRequestsList(_FriendsState state) {
    if (state.requests.isEmpty) {
      return const Center(child: Text('暂无待处理请求', style: TextStyle(color: Colors.grey)));
    }
    return ListView.builder(
      itemCount: state.requests.length,
      itemBuilder: (ctx, i) {
        final r = state.requests[i];
        final from = r['from_user_id'] ?? '';
        final reqId = r['id'] ?? '';
        return ListTile(
          leading: const CircleAvatar(
            backgroundColor: Color(0xFFFECACA),
            child: Icon(Icons.person, color: Color(0xFFEF4444)),
          ),
          title: Text('来自: $from'),
          trailing: FilledButton(
            onPressed: () => ref.read(_friendsProvider.notifier).acceptRequest(reqId),
            child: const Text('接受'),
          ),
        );
      },
    );
  }
}
