# JarvisAgent_3.1

基于 IM 的 AI 协同办公助手。在聊天中通过自然语言指令驱动 Agent 完成文档生成、PPT 制作、聊天总结等任务。支持 Web 前端和 Flutter 多端客户端。

---

## 快速开始

### 1. 启动后端服务

```bash
cd server
pip install -r requirements.txt
python main.py
```

服务默认运行在 `http://localhost:8000`

> **可选**：复制 `.env.example` 为 `.env` 并填入 Anthropic API Key。不填也能运行（自动降级为模板模式）。

```bash
cp .env.example .env
# 编辑 .env，设置:
# ANTHROPIC_API_KEY=your-key-here
# ANTHROPIC_BASE_URL=（自定义代理地址，可选）
# ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

### 2. 使用 Web 前端

后端启动后直接打开浏览器访问：

```
http://localhost:8000
```

Web 前端是 PWA 应用，支持离线缓存和桌面安装。

### 3. 使用 Flutter 客户端（多端）

```bash
cd flutter_client
flutter pub get
```

**运行 Windows 桌面版**：
```bash
flutter run -d windows
```

**运行 Android 版**：
```bash
flutter run -d android
```

**运行 Web 版**：
```bash
flutter run -d chrome
```

**运行 iOS 版**（需 macOS）：
```bash
flutter run -d ios
```

> Flutter 客户端默认连接 `http://localhost:8000`，如需修改服务器地址，编辑 `flutter_client/lib/config.dart`。

---

## 功能特性

### 核心功能
- **IM 即时通讯**：多用户会话、消息收发、消息撤回、WebSocket 实时同步
- **Agent 引擎**：意图解析 → 任务规划 → 工具执行，支持 Claude API 和 fallback 模板模式
- **文档生成**：通过 IM 指令自动生成 Markdown 文档，支持导出 MD/HTML
- **演示稿生成**：自动生成多布局幻灯片，支持导出 JSON/HTML
- **富媒体内容**：表格、图表、布局调整等富文本插入

### v3.1 新增
- **用户认证系统**：注册/登录/登出，JWT Token 认证
- **好友系统**：好友搜索、发送/接受/拒绝好友请求
- **多设备同步**：同一用户多端登录，消息实时同步到所有设备
- **Token 注销**：登出后 Token 立即失效
- **PWA 支持**：Web 端支持离线缓存、桌面安装
- **Flutter 多端客户端**：Windows/Android/iOS/Web，支持语音输入
- **Agent 主动能力**：长对话自动建议总结、上下文推荐下一步操作
- **文档/演示稿导出**：支持 Markdown、HTML、JSON 格式导出

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11+ / FastAPI / WebSocket / SQLite (aiosqlite) |
| Web 前端 | Vanilla JS + CSS（无框架依赖）/ PWA / Service Worker |
| 多端客户端 | Flutter 3.x / Riverpod 状态管理 / Material Design 3 |
| AI | Anthropic Claude API（可选，无 Key 时自动降级为模板模式） |
| 认证 | JWT (python-jose) + bcrypt 密码哈希 |

---

## 项目结构

```
JarvisAgent/
├── server/                         # Python 后端
│   ├── main.py                     # FastAPI 服务入口
│   ├── config.py                   # 环境变量配置
│   ├── database.py                 # SQLite schema 和初始化
│   ├── models.py                   # Pydantic 模型
│   ├── ws_manager.py               # WebSocket 多设备连接管理
│   ├── routes_auth.py              # 认证 API（注册/登录/登出/会话）
│   ├── routes_im.py                # IM 消息 API
│   ├── routes_friends.py           # 好友系统 API
│   ├── routes_agent.py             # Agent 任务 API
│   ├── routes_documents.py         # 文档 CRUD + 导出 API
│   ├── routes_presentations.py     # 演示稿 CRUD + 导出 API
│   ├── requirements.txt            # Python 依赖
│   ├── .env.example                # 环境变量模板
│   └── agent/                      # Agent 引擎
│       ├── orchestrator.py         # 编排器（主动能力、上下文分析）
│       ├── planner.py              # 意图解析与任务规划
│       ├── executor.py             # 工具执行器
│       └── tools/
│           ├── create_document.py  # 文档生成工具
│           ├── create_slides.py    # 演示稿生成工具
│           ├── summarize_chat.py   # 聊天总结工具
│           ├── insert_rich_content.py # 富媒体内容工具
│           └── general_reply.py    # 通用回复工具
│
├── public/                         # Web 前端（PWA）
│   ├── index.html                  # 主页面
│   ├── app.js                      # 前端逻辑
│   ├── styles.css                  # 样式
│   ├── manifest.json               # PWA manifest
│   ├── sw.js                       # Service Worker
│   └── icon-192.svg                # 应用图标
│
├── flutter_client/                 # Flutter 多端客户端
│   ├── lib/
│   │   ├── main.dart               # 应用入口
│   │   ├── config.dart             # 服务器地址配置
│   │   ├── models/                 # 数据模型
│   │   ├── providers/              # Riverpod 状态管理
│   │   ├── screens/                # 页面
│   │   │   ├── auth/               # 登录/注册
│   │   │   ├── im/                 # IM 聊天
│   │   │   ├── friends/            # 好友管理
│   │   │   ├── documents/          # 文档查看
│   │   │   └── slides/             # 演示稿查看
│   │   ├── services/               # API/WS/语音/存储服务
│   │   └── widgets/                # 公共组件
│   └── pubspec.yaml                # Flutter 依赖
│
└── .gitignore
```

---

## API 接口

### 认证
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 注册新用户 |
| `/api/auth/login` | POST | 用户登录，返回 JWT Token |
| `/api/auth/logout` | POST | 登出，注销 Token |
| `/api/auth/me` | GET | 获取当前用户信息 |
| `/api/sessions` | GET | 查询多设备在线状态 |

### IM 消息
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/users` | GET | 用户列表 |
| `/api/chats` | GET | 当前用户会话列表 |
| `/api/chats/{id}/messages` | GET | 获取聊天消息 |
| `/api/chats/{id}/messages` | POST | 发送消息 |
| `/api/messages/{id}` | DELETE | 撤回消息 |

### 好友
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/friends` | GET | 好友列表 |
| `/api/friends/requests` | GET | 待处理好友请求 |
| `/api/friends/request` | POST | 发送好友请求 |
| `/api/friends/accept/{id}` | POST | 接受好友请求 |
| `/api/friends/reject/{id}` | POST | 拒绝好友请求 |
| `/api/users/search?q=` | GET | 搜索用户 |

### Agent
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/agent/chat` | POST | 触发 Agent 任务 |
| `/api/agent/tasks/{id}` | GET | 查询任务状态 |
| `/api/agent/tasks/{id}/cancel` | POST | 取消任务 |

### 文档
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/documents` | GET | 文档列表 |
| `/api/documents/{id}` | GET | 文档详情 |
| `/api/documents/{id}` | PATCH | 更新文档 |
| `/api/documents/{id}/export?format=md\|html` | GET | 导出文档 |

### 演示稿
| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/presentations` | GET | 演示稿列表 |
| `/api/presentations/{id}` | GET | 演示稿详情 |
| `/api/presentations/{id}` | PATCH | 更新演示稿 |
| `/api/presentations/{id}/export?format=json\|html` | GET | 导出演示稿 |

### WebSocket
| 端点 | 说明 |
|------|------|
| `/ws?token=xxx` | 全局实时通信（多设备同步） |
| `/ws/chat/{chat_id}?token=xxx` | 聊天室级别通信 |

---

## 环境要求

### 后端
- Python 3.11+
- pip

### Flutter 客户端（可选）
- Flutter SDK 3.x（`>=3.11.3`）
- Dart SDK `>=3.11.3`
- 对应平台编译工具链：
  - Windows: Visual Studio 2022 + C++ 桌面开发工作负载
  - Android: Android Studio + Android SDK
  - iOS: Xcode 15+（仅 macOS）

---

## 预设用户

系统启动时自动创建以下用户（首次登录时可设置任意密码）：

| 用户名 | 昵称 | 说明 |
|--------|------|------|
| alice | Alice | 默认用户 |
| bob | Bob | 测试用户 |
| charlie | Charlie | 测试用户 |
| diana | Diana | 测试用户 |
| agent | JarvisAgent | AI 助手（系统角色） |

---

## 使用方式

1. 启动后端服务
2. 打开 Web 前端 或 Flutter 客户端
3. 登录（首次使用预设用户可输入任意密码）
4. 打开 JarvisAgent 会话
5. 输入自然语言指令，例如：
   - 「帮我写一份产品方案」
   - 「做一个10页的项目汇报PPT」
   - 「总结一下我们的聊天」
   - 「帮我插入一个对比表格」
6. Agent 解析意图 → 生成执行计划 → 执行并推送结果
7. 在「文档」或「演示稿」页面查看和导出生成结果

