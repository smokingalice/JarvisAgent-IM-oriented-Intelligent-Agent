class AppConfig {
  static const String serverHost = String.fromEnvironment('SERVER_HOST', defaultValue: 'localhost');
  static const String serverPort = String.fromEnvironment('SERVER_PORT', defaultValue: '8000');
  static const String apiBase = 'http://$serverHost:$serverPort/api';
  static const String wsBase = 'ws://$serverHost:$serverPort';
  static const Duration httpTimeout = Duration(seconds: 10);
}
