class Document {
  final String id;
  final String title;
  final String content;
  final String status;
  final String createdAt;
  final String updatedAt;

  Document({
    required this.id,
    required this.title,
    this.content = '',
    this.status = 'draft',
    this.createdAt = '',
    this.updatedAt = '',
  });

  factory Document.fromJson(Map<String, dynamic> json) {
    return Document(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      content: json['content'] ?? '',
      status: json['status'] ?? 'draft',
      createdAt: json['created_at'] ?? '',
      updatedAt: json['updated_at'] ?? '',
    );
  }
}
