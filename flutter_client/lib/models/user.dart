class User {
  final String id;
  final String name;
  final String avatar;
  final String status;

  User({required this.id, required this.name, this.avatar = '', this.status = 'online'});

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      avatar: json['avatar'] ?? '',
      status: json['status'] ?? 'online',
    );
  }
}
