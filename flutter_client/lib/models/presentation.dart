class Presentation {
  final String id;
  final String title;
  final List<Map<String, dynamic>> slides;
  final String createdAt;
  final String updatedAt;

  Presentation({
    required this.id,
    required this.title,
    this.slides = const [],
    this.createdAt = '',
    this.updatedAt = '',
  });

  factory Presentation.fromJson(Map<String, dynamic> json) {
    List<Map<String, dynamic>> slidesList = [];
    if (json['slides'] is List) {
      slidesList = (json['slides'] as List).map((s) => Map<String, dynamic>.from(s)).toList();
    }
    return Presentation(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      slides: slidesList,
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? json['created_at'] ?? '',
    );
  }
}
