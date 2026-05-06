class AppConfig {
  // ============================================================
  // 切换服务器：修改 serverHost 为新服务器的局域网 IP 地址
  // 例如: '192.168.1.100', '10.163.245.214'
  // Android 模拟器请改为: '10.0.2.2'
  // ============================================================
  static const String serverHost = '10.163.245.214';
  static const String apiBase = 'http://$serverHost:8000/api';
  static const String wsBase = 'ws://$serverHost:8000';
}
