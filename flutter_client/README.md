# JarvisAgent Flutter 客户端

JarvisAgent 的多端原生客户端，支持 Windows、Android、iOS 和 Web。

## 环境要求

- Flutter SDK >= 3.11.3
- Dart SDK >= 3.11.3

### 各平台额外要求

| 平台 | 工具 |
|------|------|
| Windows | Visual Studio 2022 + C++ 桌面开发工作负载 |
| Android | Android Studio + Android SDK 34+ |
| iOS | macOS + Xcode 15+ |
| Web | Chrome 浏览器 |

## 快速启动

```bash
# 安装依赖
flutter pub get

# 运行（选择你的目标平台）
flutter run -d windows     # Windows 桌面
flutter run -d android     # Android 设备/模拟器
flutter run -d ios          # iOS 设备/模拟器（仅 macOS）
flutter run -d chrome       # Web 浏览器
```

## 配置服务器地址

编辑 `lib/config.dart`：

```dart
class AppConfig {
  static const String apiBase = 'http://localhost:8000/api';  // 改为你的服务器地址
  static const String wsBase = 'ws://localhost:8000';
}
```

如果在真机调试，需要将 `localhost` 改为你电脑的局域网 IP（如 `192.168.1.x`）。

## 功能

- 用户认证（登录/注册）
- IM 聊天（实时 WebSocket 消息）
- Agent 交互（发送指令、查看任务卡片）
- 好友管理（搜索、添加、接受/拒绝）
- 文档查看（Markdown 渲染）
- 演示稿查看（幻灯片轮播）
- 语音输入（Speech-to-Text）
- 离线缓存（SharedPreferences）

## 项目结构

```
lib/
├── main.dart               # 应用入口
├── config.dart             # 服务器地址配置
├── models/                 # 数据模型（User, Chat, Message, Document, Presentation）
├── providers/              # Riverpod 状态管理
├── screens/                # 页面
│   ├── auth/               # 登录/注册页
│   ├── im/                 # IM 聊天页
│   ├── friends/            # 好友管理页
│   ├── documents/          # 文档列表/详情页
│   └── slides/             # 演示稿列表/详情页
├── services/               # 服务层
│   ├── api_service.dart    # HTTP 请求
│   ├── auth_service.dart   # 认证逻辑
│   ├── ws_service.dart     # WebSocket 连接
│   ├── speech_service.dart # 语音输入
│   └── storage_service.dart# 本地存储
└── widgets/                # 公共组件
    ├── agent_card.dart     # Agent 卡片消息
    ├── slide_renderer.dart # 幻灯片渲染器
    └── voice_button.dart   # 语音按钮
```

## 构建发布版本

```bash
# Windows
flutter build windows --release

# Android APK
flutter build apk --release

# Android App Bundle
flutter build appbundle --release

# iOS
flutter build ios --release

# Web
flutter build web --release
```
