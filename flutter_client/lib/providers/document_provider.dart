import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../models/document.dart';
import '../models/presentation.dart';
import '../services/api_service.dart';
import 'auth_provider.dart';

final documentListProvider = StateNotifierProvider<DocumentListNotifier, List<Document>>((ref) {
  return DocumentListNotifier(ref.read(apiServiceProvider));
});

final presentationListProvider = StateNotifierProvider<PresentationListNotifier, List<Presentation>>((ref) {
  return PresentationListNotifier(ref.read(apiServiceProvider));
});

class DocumentListNotifier extends StateNotifier<List<Document>> {
  final ApiService _api;

  DocumentListNotifier(this._api) : super([]);

  Future<void> load() async {
    try {
      final data = await _api.get('/documents') as List;
      state = data.map((j) => Document.fromJson(j)).toList();
    } catch (_) {}
  }

  Future<Document?> getDocument(String id) async {
    try {
      final data = await _api.get('/documents/$id');
      return Document.fromJson(data);
    } catch (_) {
      return null;
    }
  }
}

class PresentationListNotifier extends StateNotifier<List<Presentation>> {
  final ApiService _api;

  PresentationListNotifier(this._api) : super([]);

  Future<void> load() async {
    try {
      final data = await _api.get('/presentations') as List;
      state = data.map((j) => Presentation.fromJson(j)).toList();
    } catch (_) {}
  }

  Future<Presentation?> getPresentation(String id) async {
    try {
      final data = await _api.get('/presentations/$id');
      return Presentation.fromJson(data);
    } catch (_) {
      return null;
    }
  }
}
