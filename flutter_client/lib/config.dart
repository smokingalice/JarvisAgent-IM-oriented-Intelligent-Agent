class AppConfig {
  static const String serverHost = 'localhost';
  static const String apiBase = 'http://$serverHost:8000/api';
  static const String wsBase = 'ws://$serverHost:8000';
  static const Duration httpTimeout = Duration(seconds: 10);
}
