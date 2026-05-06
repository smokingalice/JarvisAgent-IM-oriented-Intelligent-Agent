import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../providers/auth_provider.dart';
import '../../services/api_service.dart';

final _friendsProvider = StateNotifierProvider<_FriendsNotifier, _FriendsState>((ref) {
  return _FriendsNotifier(ref.read(apiServiceProvider));
});

class _FriendsState {
  final List<Map<String, dynamic>> friends;
  final List<Map<String, dynamic>> incomingRequests;
  final List<Map<String, dynamic>> searchResults;
  final bool isLoading;
  _FriendsState({this.friends = const [], this.incomingRequests = const [], this.searchResults = const [], this.isLoading = false});
  _FriendsState copyWith({List<Map<String, dynamic>>? friends, List<Map<String, dynamic>>? incomingRequests, List<Map<String, dynamic>>? searchResults, bool? isLoading}) {
    return _FriendsState(
      friends: friends ?? this.friends,
      incomingRequests: incomingRequests ?? this.incomingRequests,
      searchResults: searchResults ?? this.searchResults,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

class _FriendsNotifier extends StateNotifier<_FriendsState> {
  final ApiService _api;
  _FriendsNotifier(this._api) : super(_FriendsState());

  Future<void> load() async {
    state = state.copyWith(isLoading: true);
    try {
      final friends = await _api.get('/friends') as List;
      final requestsResp = await _api.get('/friends/requests');
      final incoming = (requestsResp['incoming'] as List?) ?? [];
      state = state.copyWith(
        friends: friends.cast<Map<String, dynamic>>(),
        incomingRequests: incoming.cast<Map<String, dynamic>>(),
        isLoading: false,
      );
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> search(String query) async {
    if (query.isEmpty) return;
    try {
      final results = await _api.get('/users/search?q=$query') as List;
      state = state.copyWith(searchResults: results.cast<Map<String, dynamic>>());
    } catch (_) {}
  }

  void clearSearch() {
    state = state.copyWith(searchResults: []);
  }

  Future<void> sendRequest(String userId) async {
    await _api.post('/friends/request?target_user_id=$userId', {});
    await load();
  }

  Future<void> acceptRequest(String friendshipId) async {
    await _api.post('/friends/accept/$friendshipId', {});
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
    _tabCtrl = TabController(length: 3, vsync: this);
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
              suffixIcon: _searchCtrl.text.isNotEmpty
                  ? IconButton(
                      icon: const Icon(Icons.clear, size: 18),
                      onPressed: () {
                        _searchCtrl.clear();
                        ref.read(_friendsProvider.notifier).clearSearch();
                        setState(() {});
                      },
                    )
                  : null,
            ),
            onChanged: (_) => setState(() {}),
            onSubmitted: (q) => ref.read(_friendsProvider.notifier).search(q),
          ),
        ),
        TabBar(
          controller: _tabCtrl,
          tabs: [
            Tab(text: '好友 (${state.friends.length})'),
            Tab(text: '请求 (${state.incomingRequests.length})'),
            const Tab(text: '搜索'),
          ],
        ),
        Expanded(
          child: TabBarView(
            controller: _tabCtrl,
            children: [
              _buildFriendsList(state),
              _buildRequestsList(state),
              _buildSearchResults(state),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildFriendsList(_FriendsState state) {
    if (state.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }
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
          return ListTile(
            leading: CircleAvatar(
              backgroundColor: const Color(0xFF818CF8),
              child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Colors.white)),
            ),
            title: Text(name),
            subtitle: Text(f['id'] ?? '', style: const TextStyle(fontSize: 12, color: Colors.grey)),
          );
        },
      ),
    );
  }

  Widget _buildRequestsList(_FriendsState state) {
    if (state.incomingRequests.isEmpty) {
      return const Center(child: Text('暂无待处理请求', style: TextStyle(color: Colors.grey)));
    }
    return ListView.builder(
      itemCount: state.incomingRequests.length,
      itemBuilder: (ctx, i) {
        final r = state.incomingRequests[i];
        final fromName = r['from_name'] ?? r['from_user_id'] ?? '';
        final friendshipId = r['id'] ?? '';
        return ListTile(
          leading: const CircleAvatar(
            backgroundColor: Color(0xFFFECACA),
            child: Icon(Icons.person, color: Color(0xFFEF4444)),
          ),
          title: Text('来自: $fromName'),
          trailing: FilledButton(
            onPressed: () => ref.read(_friendsProvider.notifier).acceptRequest(friendshipId),
            child: const Text('接受'),
          ),
        );
      },
    );
  }

  Widget _buildSearchResults(_FriendsState state) {
    if (state.searchResults.isEmpty) {
      return const Center(child: Text('输入用户名或ID进行搜索', style: TextStyle(color: Colors.grey)));
    }
    return ListView.builder(
      itemCount: state.searchResults.length,
      itemBuilder: (ctx, i) {
        final u = state.searchResults[i];
        final name = u['name'] ?? '';
        final id = u['id'] ?? '';
        return ListTile(
          leading: CircleAvatar(
            backgroundColor: const Color(0xFFBFDBFE),
            child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Color(0xFF1D4ED8))),
          ),
          title: Text(name),
          subtitle: Text(id, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          trailing: IconButton(
            icon: const Icon(Icons.person_add, size: 20),
            onPressed: () => ref.read(_friendsProvider.notifier).sendRequest(id),
          ),
        );
      },
    );
  }
}
