class TimeUtils {
  static DateTime parseUtc(String timeStr) {
    if (timeStr.isEmpty) return DateTime.now();
    try {
      final dt = DateTime.parse(timeStr);
      if (!timeStr.endsWith('Z') && !timeStr.contains('+')) {
        return DateTime.utc(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second);
      }
      return dt.toUtc();
    } catch (_) {
      return DateTime.now();
    }
  }

  static String toLocalDisplay(String utcTimeStr) {
    if (utcTimeStr.isEmpty) return '';
    final utc = parseUtc(utcTimeStr);
    final local = utc.toLocal();
    return '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }

  static String toLocalFullDisplay(String utcTimeStr) {
    if (utcTimeStr.isEmpty) return '';
    final utc = parseUtc(utcTimeStr);
    final local = utc.toLocal();
    return '${local.year}-${local.month.toString().padLeft(2, '0')}-${local.day.toString().padLeft(2, '0')} '
        '${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
  }
}
