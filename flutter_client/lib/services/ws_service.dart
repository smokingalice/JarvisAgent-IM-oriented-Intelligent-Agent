import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../config.dart';

class WsService {
  WebSocketChannel? _channel;
  final _controller = StreamController<Map<String, dynamic>>.broadcast();
  String? _token;
  Timer? _reconnectTimer;
  bool _disposed = false;

  Stream<Map<String, dynamic>> get messages => _controller.stream;

  void connect(String? token) {
    _token = token;
    _doConnect();
  }

  void _doConnect() {
    if (_disposed) return;
    final uri = _token != null
        ? '${AppConfig.wsBase}/ws?token=$_token'
        : '${AppConfig.wsBase}/ws';
    try {
      _channel = WebSocketChannel.connect(Uri.parse(uri));
      _channel!.stream.listen(
        (data) {
          try {
            final msg = jsonDecode(data as String) as Map<String, dynamic>;
            _controller.add(msg);
          } catch (_) {}
        },
        onDone: _onDisconnected,
        onError: (_) => _onDisconnected(),
      );
    } catch (_) {
      _scheduleReconnect();
    }
  }

  void _onDisconnected() {
    if (!_disposed) _scheduleReconnect();
  }

  void _scheduleReconnect() {
    _reconnectTimer?.cancel();
    _reconnectTimer = Timer(const Duration(seconds: 3), _doConnect);
  }

  void dispose() {
    _disposed = true;
    _reconnectTimer?.cancel();
    _channel?.sink.close();
    _controller.close();
  }
}
