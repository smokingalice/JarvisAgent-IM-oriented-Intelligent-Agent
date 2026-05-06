class AppConfig {
  // ============================================================
  // 切换服务器：修改下方 defaultValue 为新服务器的局域网 IP
  // 或在构建时通过 --dart-define 覆盖:
  //   flutter run --dart-define=SERVER_HOST=192.168.1.100
  // Android 模拟器请改为: '10.0.2.2'
  // ============================================================
  static const String serverHost = String.fromEnvironment('SERVER_HOST', defaultValue: '10.163.245.214');
  static const String serverPort = String.fromEnvironment('SERVER_PORT', defaultValue: '8000');
  static const String apiBase = 'http://$serverHost:$serverPort/api';
  static const String wsBase = 'ws://$serverHost:$serverPort';
  static const Duration httpTimeout = Duration(seconds: 10);
}
