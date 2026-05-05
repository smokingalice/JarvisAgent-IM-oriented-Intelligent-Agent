import 'package:shared_preferences/shared_preferences.dart';
import '../models/user.dart';
import 'api_service.dart';

class AuthService {
  final ApiService _api;
  static const _tokenKey = 'jarvis_token';
  static const _userKey = 'jarvis_user_id';
  static const _nameKey = 'jarvis_user_name';

  AuthService(this._api);

  Future<({String token, User user})?> loadSavedSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    final userId = prefs.getString(_userKey);
    final userName = prefs.getString(_nameKey);
    if (token != null && userId != null) {
      _api.setToken(token);
      return (token: token, user: User(id: userId, name: userName ?? userId));
    }
    return null;
  }

  Future<({String token, User user})> login(String username, String password) async {
    final resp = await _api.post('/auth/login', {'username': username, 'password': password});
    final token = resp['token'] as String;
    final user = User.fromJson(resp['user']);
    _api.setToken(token);
    await _saveSession(token, user);
    return (token: token, user: user);
  }

  Future<({String token, User user})> register(String username, String password, String name) async {
    final resp = await _api.post('/auth/register', {
      'username': username,
      'password': password,
      'name': name,
    });
    final token = resp['token'] as String;
    final user = User.fromJson(resp['user']);
    _api.setToken(token);
    await _saveSession(token, user);
    return (token: token, user: user);
  }

  Future<void> logout() async {
    _api.setToken(null);
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_tokenKey);
    await prefs.remove(_userKey);
    await prefs.remove(_nameKey);
  }

  Future<void> _saveSession(String token, User user) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, token);
    await prefs.setString(_userKey, user.id);
    await prefs.setString(_nameKey, user.name);
  }
}
