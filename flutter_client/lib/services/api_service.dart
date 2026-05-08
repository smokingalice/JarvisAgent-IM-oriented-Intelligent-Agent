import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config.dart';

class ApiService {
  String? _token;

  void setToken(String? token) => _token = token;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Future<dynamic> get(String path) async {
    final resp = await http.get(Uri.parse('${AppConfig.apiBase}$path'), headers: _headers);
    if (resp.statusCode == 200) return jsonDecode(resp.body);
    throw ApiException(resp.statusCode, resp.body);
  }

  Future<dynamic> post(String path, Map<String, dynamic> body) async {
    final resp = await http.post(
      Uri.parse('${AppConfig.apiBase}$path'),
      headers: _headers,
      body: jsonEncode(body),
    );
    if (resp.statusCode == 200) return jsonDecode(resp.body);
    throw ApiException(resp.statusCode, resp.body);
  }

  Future<dynamic> delete(String path) async {
    final resp = await http.delete(Uri.parse('${AppConfig.apiBase}$path'), headers: _headers);
    if (resp.statusCode == 200) return jsonDecode(resp.body);
    throw ApiException(resp.statusCode, resp.body);
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String body;
  ApiException(this.statusCode, this.body);

  String get message {
    try {
      final json = jsonDecode(body);
      return json['detail'] ?? 'Error $statusCode';
    } catch (_) {
      return 'Error $statusCode';
    }
  }

  @override
  String toString() => message;
}
