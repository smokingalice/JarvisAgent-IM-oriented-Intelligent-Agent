import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/api_service.dart';

final _friendsProvider = StateNotifierProvider<_FriendsNotifier, _FriendsState>((ref) => _FriendsNotifier());

class _FriendsState {
  final List<Map<String, dynamic>> friends;
  final List<Map<String, dynamic>> requests;
  final List<Map<String, dynamic>> searchResults;
  final bool isLoading;
  final bool isSearching;
  _FriendsState({
    this.friends = const [],
    this.requests = const [],
    this.searchResults = const [],
    this.isLoading = false,
    this.isSearching = false,
  });
  _FriendsState copyWith({
    List<Map<String, dynamic>>? friends,
    List<Map<String, dynamic>>? requests,
    List<Map<String, dynamic>>? searchResults,
    bool? isLoading,
    bool? isSearching,
  }) {
    return _FriendsState(
      friends: friends ?? this.friends,
      requests: requests ?? this.requests,
      searchResults: searchResults ?? this.searchResults,
      isLoading: isLoading ?? this.isLoading,
      isSearching: isSearching ?? this.isSearching,
    );
  }
}

class _FriendsNotifier extends StateNotifier<_FriendsState> {
  _FriendsNotifier() : super(_FriendsState());
  final _api = ApiService();

  Future<void> load() async {
    state = state.copyWith(isLoading: true);
    try {
      final friends = await _api.get('/friends') as List;
      final requestsData = await _api.get('/friends/requests');
      final List<Map<String, dynamic>> incoming;
      if (requestsData is Map) {
        incoming = ((requestsData['incoming'] ?? []) as List).cast<Map<String, dynamic>>();
      } else {
        incoming = (requestsData as List).cast<Map<String, dynamic>>();
      }
      state = state.copyWith(
        friends: friends.cast<Map<String, dynamic>>(),
        requests: incoming,
        isLoading: false,
        isSearching: false,
        searchResults: [],
      );
    } catch (_) {
      state = state.copyWith(isLoading: false);
    }
  }

  Future<void> search(String query) async {
    if (query.isEmpty) {
      state = state.copyWith(isSearching: false, searchResults: []);
      return;
    }
    try {
      final results = await _api.get('/users/search?q=$query') as List;
      state = state.copyWith(
        searchResults: results.cast<Map<String, dynamic>>(),
        isSearching: true,
      );
    } catch (_) {}
  }

  void clearSearch() {
    state = state.copyWith(isSearching: false, searchResults: []);
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
              suffixIcon: state.isSearching
                  ? IconButton(
                      icon: const Icon(Icons.close, size: 18),
                      onPressed: () {
                        _searchCtrl.clear();
                        ref.read(_friendsProvider.notifier).clearSearch();
                      },
                    )
                  : null,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(24)),
              contentPadding: const EdgeInsets.symmetric(horizontal: 16),
              isDense: true,
            ),
            onSubmitted: (q) => ref.read(_friendsProvider.notifier).search(q),
          ),
        ),
        if (state.isSearching)
          Expanded(child: _buildSearchResults(state))
        else ...[
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
      ],
    );
  }

  Widget _buildSearchResults(_FriendsState state) {
    if (state.searchResults.isEmpty) {
      return const Center(child: Text('未找到用户', style: TextStyle(color: Colors.grey)));
    }
    final friendIds = state.friends.map((f) => f['id'] ?? f['user_id']).toSet();
    return ListView.builder(
      itemCount: state.searchResults.length,
      itemBuilder: (ctx, i) {
        final user = state.searchResults[i];
        final name = user['name'] ?? user['username'] ?? '';
        final id = user['id'] ?? '';
        final isAlreadyFriend = friendIds.contains(id);
        return ListTile(
          leading: CircleAvatar(
            backgroundColor: const Color(0xFF818CF8),
            child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Colors.white)),
          ),
          title: Text(name),
          subtitle: Text(id, style: const TextStyle(fontSize: 12, color: Colors.grey)),
          trailing: isAlreadyFriend
              ? const Text('已是好友', style: TextStyle(fontSize: 12, color: Colors.grey))
              : IconButton(
                  icon: const Icon(Icons.person_add, size: 20, color: Color(0xFF4F46E5)),
                  onPressed: () => ref.read(_friendsProvider.notifier).sendRequest(id),
                ),
        );
      },
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
            trailing: const Icon(Icons.chat_bubble_outline, size: 20, color: Colors.grey),
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
        final fromName = r['from_name'] ?? r['from_user_id'] ?? '';
        final reqId = r['id'] ?? '';
        return ListTile(
          leading: const CircleAvatar(
            backgroundColor: Color(0xFFFECACA),
            child: Icon(Icons.person, color: Color(0xFFEF4444)),
          ),
          title: Text('来自: $fromName'),
          trailing: FilledButton(
            onPressed: () => ref.read(_friendsProvider.notifier).acceptRequest(reqId),
            child: const Text('接受'),
          ),
        );
      },
    );
  }
}
