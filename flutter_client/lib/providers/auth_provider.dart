import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/user.dart';
import '../services/api_service.dart';
import '../services/auth_service.dart';
import '../services/ws_service.dart';

final apiServiceProvider = Provider<ApiService>((ref) => ApiService());
final wsServiceProvider = Provider<WsService>((ref) => WsService());
final authServiceProvider = Provider<AuthService>((ref) => AuthService(ref.read(apiServiceProvider)));

class AuthState {
  final User? user;
  final String? token;
  final bool isLoading;
  final String? error;

  AuthState({this.user, this.token, this.isLoading = false, this.error});

  bool get isLoggedIn => user != null && token != null;
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthService _authService;
  final WsService _wsService;

  AuthNotifier(this._authService, this._wsService) : super(AuthState());

  Future<void> tryAutoLogin() async {
    state = AuthState(isLoading: true);
    final session = await _authService.loadSavedSession();
    if (session != null) {
      _wsService.connect(session.token);
      state = AuthState(user: session.user, token: session.token);
    } else {
      state = AuthState();
    }
  }

  Future<void> login(String username, String password) async {
    state = AuthState(isLoading: true);
    try {
      final session = await _authService.login(username, password);
      _wsService.connect(session.token);
      state = AuthState(user: session.user, token: session.token);
    } catch (e) {
      state = AuthState(error: e.toString());
    }
  }

  Future<void> register(String username, String password, String name) async {
    state = AuthState(isLoading: true);
    try {
      final session = await _authService.register(username, password, name);
      _wsService.connect(session.token);
      state = AuthState(user: session.user, token: session.token);
    } catch (e) {
      state = AuthState(error: e.toString());
    }
  }

  Future<void> logout() async {
    await _authService.logout();
    _wsService.dispose();
    state = AuthState();
  }
}

final authProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.read(authServiceProvider), ref.read(wsServiceProvider));
});
