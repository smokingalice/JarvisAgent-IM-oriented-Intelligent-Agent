# Agent-Pilot

基于 IM 的 AI 协同办公助手。在聊天中通过自然语言指令驱动 Agent 完成文档生成、PPT 制作、聊天总结等任务。

## 功能

- **IM 即时通讯**：多用户会话、消息收发、WebSocket 实时同步
- **Agent 引擎**：意图解析 → 任务规划 → 工具执行，支持 Claude API 和 fallback 关键词匹配
- **文档生成**：通过 IM 指令（如「帮我写一份产品方案」）自动生成 Markdown 文档
- **演示稿生成**：自动生成多布局幻灯片（标题页、内容页、双栏对比、总结页等）
- **聊天总结**：自动提取聊天记录生成结构化总结文档

## 技术栈

- **后端**：Python / FastAPI / WebSocket / SQLite
- **前端**：Vanilla JS + CSS（无框架依赖）
- **AI**：Anthropic Claude API（可选，无 Key 时自动降级为模板模式）

## 项目结构

```
server/
├── main.py                  # FastAPI 服务入口
├── config.py                # 配置
├── database.py              # SQLite schema 和初始化
├── models.py                # Pydantic 模型
├── ws_manager.py            # WebSocket 连接管理
├── routes_im.py             # IM 消息 API
├── routes_agent.py          # Agent 任务 API
├── routes_documents.py      # 文档 API
├── routes_presentations.py  # 演示稿 API
├── requirements.txt
└── agent/
    ├── orchestrator.py      # Agent 编排器
    ├── planner.py           # 意图解析与任务规划
    ├── executor.py          # 工具执行器
    └── tools/
        ├── create_document.py
        ├── create_slides.py
        ├── summarize_chat.py
        └── general_reply.py

public/
├── index.html               # 前端页面
├── app.js                   # 前端逻辑
└── styles.css               # 样式
```

## 运行

```bash
cd server
pip install -r requirements.txt
```

可选：复制 `.env.example` 为 `.env` 并填入 API Key：

```bash
cp .env.example .env
# 编辑 .env，设置 ANTHROPIC_API_KEY（不设也能跑，会使用模板降级模式）
```

启动服务：

```bash
python main.py
```

打开 [http://localhost:8000](http://localhost:8000)

## API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/users` | GET | 用户列表 |
| `/api/chats` | GET | 会话列表 |
| `/api/chats/{id}/messages` | GET | 获取消息 |
| `/api/chats/{id}/messages` | POST | 发送消息 |
| `/api/agent/chat` | POST | 触发 Agent 任务 |
| `/api/documents` | GET | 文档列表 |
| `/api/documents/{id}` | GET | 文档详情 |
| `/api/presentations` | GET | 演示稿列表 |
| `/api/presentations/{id}` | GET | 演示稿详情 |
| `/ws` | WebSocket | 全局实时通信 |

## 预设用户

Alice、Bob、Charlie、Diana 四个用户 + Agent-Pilot 助手，启动时自动创建。

## 使用方式

1. 选择一个用户（默认 Alice）
2. 打开 Agent-Pilot 会话
3. 输入指令，例如：
   - 「帮我写一份产品方案」
   - 「做一个项目汇报PPT」
   - 「总结一下我们的聊天」
4. Agent 会解析意图、生成执行计划并执行
5. 在「文档」或「演示稿」Tab 查看生成结果
