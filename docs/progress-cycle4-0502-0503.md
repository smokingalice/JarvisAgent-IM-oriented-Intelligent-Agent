# JarvisAgent 第四周期进度记录（5.2 - 5.3）

## 一、核心产出

本周期完成了项目从 Node.js 原型到 Python 全栈架构的重大升级，交付了完整的 Agent 智能体引擎和协同办公后端。

### 1. Python 后端架构重建

- 放弃 Node.js 原生 HTTP 方案，迁移至 **FastAPI + WebSocket + SQLite** 技术栈
- 完成 18 个 Python 模块的开发，包含完整的 REST API 和实时通信层
- 数据库 schema 设计：users、chats、chat_members、messages、documents、presentations、tasks 7 张核心表
- WebSocket 连接管理器：支持频道订阅、全局广播、个人推送

### 2. Agent 智能体引擎（核心模块）

实现了完整的 Agent Orchestrator 工作流：

```
用户消息 → 意图解析(Planner) → 任务规划 → 工具执行(Executor) → 结果交付
```

- **意图解析器 (Planner)**：调用 Claude API 进行意图识别，支持 fallback 关键词匹配
- **任务执行器 (Executor)**：工具注册表机制，支持依赖链执行和进度回调
- **工具集**：
  - `create_document` — LLM 驱动的文档生成（方案、报告、文章等）
  - `create_slides` — 多布局 PPT 生成（title/content/two_column/summary/image_text）
  - `summarize_chat` — 聊天记录自动总结
  - `general_reply` — 通用对话回复

### 3. 前端全面重写

- 三视图架构：IM 聊天 / 文档 / 演示稿，Tab 切换
- Agent Card 消息卡片：支持 plan（执行计划）、delivery（任务完成）、clarification（需要确认）三种类型
- 实时进度条：WebSocket 驱动的任务进度可视化
- 文档渲染：Markdown → HTML 转换与排版
- 幻灯片渲染：5 种布局模板的完整渲染

### 4. 全链路可用性

- 服务端通过测试：所有 API 端点正常响应
- 前端静态资源正确挂载
- WebSocket 实时通信就绪
- 无 API Key 时所有 LLM 工具具有 fallback 降级能力

## 二、量化指标

| 指标 | 数据 |
|------|------|
| 新增 Python 后端代码 | 1430 行（18 个模块） |
| 前端重写代码 | 773 行（app.js 479 + CSS 208 + HTML 86） |
| 总新增代码 | 2200+ 行 |
| REST API 端点 | 10 个（IM 5 + Agent 3 + Doc 2 + Pres 2） |
| WebSocket 端点 | 2 个（全局 + 聊天频道） |
| Agent 工具 | 4 个（文档生成、PPT 生成、聊天总结、通用回复） |
| 数据库表 | 7 张 |
| AI 使用场景 | 架构迁移决策、Agent 工作流设计、工具链实现、前端组件生成 |
| 技术栈变更 | Node.js → Python FastAPI（重大架构升级） |

## 三、过程复盘与沉淀

### 1. 本周期主要搞定了哪些环节？用了什么方法？

- **架构决策**：评估了 C++ IM + Python Agent 的分体方案，最终选择 Python 统一技术栈（FastAPI）。原因：5.7 截止日期紧迫，Agent 能力是核心差异化价值，IM 性能不是瓶颈
- **Agent 引擎设计**：参考 ReAct 范式设计了 Planner → Executor → Tool 三层架构，使用 Claude Code 辅助生成了 Orchestrator 的状态机逻辑
- **LLM 工具链**：每个工具都实现了"有 API Key 用 LLM + 无 Key 用模板"的双模式，确保 Demo 在任何环境下都可用
- **前端重构**：从 SSE 单向推送升级为 WebSocket 双向通信，新增 Agent Card 组件和多视图切换

### 2. 遇到的困难和解决方式

- **依赖安装问题**：pydantic-core 在 Python 3.14 上构建失败，通过放宽版本约束（`>=` 替代 `==`）解决
- **SSE → WebSocket 迁移**：之前的前端基于 SSE，需要重写为 WebSocket。新方案更简洁，支持双向通信
- **Agent 异步执行**：Agent 任务可能耗时较长，通过 FastAPI BackgroundTasks 实现异步执行，API 立即返回 task_id

### 3. 可复用的经验

- **FastAPI + WebSocket + SQLite** 技术组合：轻量、无需额外服务依赖，适合快速原型和演示
- **Agent Orchestrator 模式**：意图解析 → 计划生成 → 工具执行的三阶段流水线，可复用到任何 Agent 应用
- **Fallback 降级策略**：每个 LLM 依赖点都有关键词匹配或模板降级，确保无 API Key 时系统仍可运行

## 四、随手记

- Python FastAPI 的开发效率比 Node.js 原生 HTTP 高很多，类型提示 + 自动文档 + 依赖注入三件套非常顺手
- WebSocket 比 SSE 更适合 IM 场景：支持双向通信，连接管理也更标准化
- Agent 的 fallback 关键词匹配意外地好用，在没有 API Key 的演示场景下体验也不差
- 下一步关键：接入真实 Claude API 进行端到端测试，优化 Agent 的意图解析准确度

## 五、文件结构

```
server/
├── main.py              # FastAPI 入口，路由注册，WebSocket 端点
├── config.py            # 环境变量配置
├── database.py          # SQLite 初始化、Schema、种子数据
├── models.py            # Pydantic 数据模型
├── ws_manager.py        # WebSocket 连接管理器
├── routes_im.py         # IM 消息 REST API
├── routes_agent.py      # Agent 任务 REST API
├── routes_documents.py  # 文档 REST API
├── routes_presentations.py  # 演示稿 REST API
├── requirements.txt     # Python 依赖
└── agent/
    ├── orchestrator.py  # Agent 编排器（核心工作流）
    ├── planner.py       # 意图解析与任务规划
    ├── executor.py      # 工具执行器
    └── tools/
        ├── create_document.py   # 文档生成工具
        ├── create_slides.py     # PPT 生成工具
        ├── summarize_chat.py    # 聊天总结工具
        └── general_reply.py     # 通用回复工具

public/
├── index.html           # 三视图前端页面
├── app.js               # 前端交互逻辑（WebSocket、渲染、Agent Card）
└── styles.css           # 完整 UI 样式系统
```
