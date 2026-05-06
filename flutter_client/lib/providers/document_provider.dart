import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/document.dart';
import '../models/presentation.dart';
import '../services/api_service.dart';
import '../services/ws_service.dart';
import 'auth_provider.dart';

final documentListProvider = StateNotifierProvider<DocumentListNotifier, List<Document>>((ref) {
  return DocumentListNotifier(ref.read(apiServiceProvider), ref.read(wsServiceProvider));
});

final presentationListProvider = StateNotifierProvider<PresentationListNotifier, List<Presentation>>((ref) {
  return PresentationListNotifier(ref.read(apiServiceProvider), ref.read(wsServiceProvider));
});

class DocumentListNotifier extends StateNotifier<List<Document>> {
  final ApiService _api;
  final WsService _ws;
  StreamSubscription? _sub;

  DocumentListNotifier(this._api, this._ws) : super([]);

  Future<void> load() async {
    try {
      final data = await _api.get('/documents') as List;
      state = data.map((j) => Document.fromJson(j)).toList();
    } catch (_) {}
  }

  void listenWs() {
    _sub?.cancel();
    _sub = _ws.messages.listen((msg) {
      if (msg['type'] == 'document_updated') {
        load();
      }
    });
  }

  Future<Document?> getDocument(String id) async {
    try {
      final data = await _api.get('/documents/$id');
      return Document.fromJson(data);
    } catch (_) {
      return null;
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}

class PresentationListNotifier extends StateNotifier<List<Presentation>> {
  final ApiService _api;
  final WsService _ws;
  StreamSubscription? _sub;

  PresentationListNotifier(this._api, this._ws) : super([]);

  Future<void> load() async {
    try {
      final data = await _api.get('/presentations') as List;
      state = data.map((j) => Presentation.fromJson(j)).toList();
    } catch (_) {}
  }

  void listenWs() {
    _sub?.cancel();
    _sub = _ws.messages.listen((msg) {
      if (msg['type'] == 'presentation_updated') {
        load();
      }
    });
  }

  Future<Presentation?> getPresentation(String id) async {
    try {
      final data = await _api.get('/presentations/$id');
      return Presentation.fromJson(data);
    } catch (_) {
      return null;
    }
  }

  @override
  void dispose() {
    _sub?.cancel();
    super.dispose();
  }
}
