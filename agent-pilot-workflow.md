# Agent-Pilot 工作流程文档

> 基于 IM 的办公协同智能助手 -- 从 IM 对话到演示稿的一键智能闭环
> 创建日期：2026-04-24

---

## 目录

1. [项目全景](#一项目全景)
2. [系统架构总览](#二系统架构总览)
3. [技术选型](#三技术选型)
4. [六大场景模块详细设计](#四六大场景模块详细设计)
5. [Agent 核心引擎设计](#五agent-核心引擎设计)
6. [多端协同框架](#六多端协同框架)
7. [数据模型与协议](#七数据模型与协议)
8. [端到端工作流编排](#八端到端工作流编排)
9. [演示场景脚本](#九演示场景脚本)
10. [开发阶段规划](#十开发阶段规划)
11. [项目目录结构](#十一项目目录结构)
12. [质量保障与验收标准](#十二质量保障与验收标准)

---

## 一、项目全景

### 1.1 核心理念

```
AI Agent 是主驾驶（Pilot），GUI 界面是仪表盘与辅助操作台（Co-pilot）。
用户通过自然语言下达指令，Agent 负责理解、拆解、驱动；GUI 负责展示、确认、微调。
```

### 1.2 产品定位

```
IM 对话 → Agent 理解意图 → 自动拆解任务 → 生成文档 → 生成演示稿 → 多端同步 → 交付归档
```

### 1.3 必须覆盖的三大办公套件

| 套件 | 定位 | 核心能力 |
|------|------|---------|
| IM（即时通讯） | 意图入口 + 协作通道 | 群聊/单聊、文本/语音指令、任务状态推送 |
| Doc（文档） | 内容沉淀 + 协作编辑 | 自动生成、实时协同编辑、版本管理 |
| Slides/Canvas（演示稿/画布） | 成果输出 + 汇报展示 | 结构化生成、布局排版、演练支持 |

### 1.4 六大场景模块

```
场景 A：意图/指令入口（IM）
场景 B：任务理解与规划（Planner）
场景 C：文档/白板生成与编辑（Doc Engine）
场景 D：演示稿/画布生成与排练（Slides Engine）
场景 E：多端协作与一致性（Sync Framework）
场景 F：总结与交付（Delivery）
```

---

## 二、系统架构总览

### 2.1 分层架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端表现层                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  移动端 App   │  │  桌面端 App   │  │  (可选) Web 端       │  │
│  │  iOS/Android  │  │  macOS/Win   │  │                      │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│  ┌──────┴─────────────────┴──────────────────────┴───────────┐  │
│  │              Flutter 跨端 UI 层（统一代码库）                │  │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────┐  ┌──────────┐  │  │
│  │  │ IM 模块  │  │ Doc 模块  │  │ Slides 模块│  │ Agent UI │  │  │
│  │  └─────────┘  └──────────┘  └───────────┘  └──────────┘  │  │
│  └───────────────────────┬───────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                     业务逻辑层                                   │
│  ┌───────────────────────┴───────────────────────────────────┐  │
│  │                  Agent 编排引擎（Orchestrator）              │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Intent   │  │ Planner  │  │ Executor │  │ Monitor  │  │  │
│  │  │ Parser   │  │          │  │          │  │          │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              实时同步引擎（Sync Engine）                      ││
│  │  WebSocket + CRDT + Conflict Resolution                     ││
│  └─────────────────────────────────────────────────────────────┘│
└──────────────────────────┼──────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────┐
│                     基础设施层                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐ │
│  │ LLM API  │  │ 对象存储  │  │ 数据库   │  │ 消息队列/推送   │ │
│  │(Claude等)│  │ (OSS/S3) │  │(Postgres)│  │ (WS/FCM/APNs) │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 核心数据流

```
用户语音/文本 ──→ IM 入口 ──→ Intent Parser ──→ Planner
                                                   │
                              ┌─────────────────────┤
                              ▼                     ▼
                         Doc Engine           Slides Engine
                              │                     │
                              ▼                     ▼
                         Sync Engine ◄──────► Sync Engine
                              │                     │
                              ▼                     ▼
                     多端实时同步更新          多端实时同步更新
                              │                     │
                              └──────────┬──────────┘
                                         ▼
                                   Delivery Engine
                                   (总结/归档/分享)
```

---

## 三、技术选型

### 3.1 客户端

| 层面 | 技术 | 理由 |
|------|------|------|
| 跨端 UI 框架 | **Flutter 3.x** | 一套代码覆盖 iOS + Android + macOS + Windows，保证多端一致性 |
| 状态管理 | **Riverpod 2.x** | 编译安全、可测试、支持异步状态 |
| 路由 | **go_router** | 声明式路由，支持深度链接 |
| 本地存储 | **Hive / Isar** | 支持离线缓存和离线编辑 |
| 网络层 | **dio + WebSocket** | HTTP 请求 + 实时双向通信 |
| 语音识别 | **speech_to_text** (本地) + 云端 ASR 备选 | 语音指令入口 |
| 富文本编辑 | **flutter_quill** 或 **super_editor** | 文档编辑器核心 |
| 画布/演示稿 | **CustomPainter + 自定义 Widget** | 自由画布 + 幻灯片渲染 |

### 3.2 后端

| 层面 | 技术 | 理由 |
|------|------|------|
| 服务框架 | **Dart Shelf** 或 **Node.js (Fastify)** 或 **Python (FastAPI)** | 根据团队能力选择 |
| LLM 接入 | **Claude API (Anthropic)** | 强推理、长上下文、Tool Use 支持 |
| 实时通信 | **WebSocket (Socket.IO / 原生)** | 多端实时同步 |
| 协同编辑 | **CRDT (Yjs / Automerge)** | 无冲突分布式数据结构 |
| 数据库 | **PostgreSQL + Redis** | 持久化 + 缓存 + 消息队列 |
| 文件存储 | **MinIO / S3** | 文档、图片、演示稿资源 |
| 消息推送 | **FCM (Android) + APNs (iOS)** | 任务状态推送 |

### 3.3 AI/Agent

| 层面 | 技术 | 理由 |
|------|------|------|
| LLM | **Claude Sonnet 4.6 / Opus 4.6** | 意图理解 + 内容生成 |
| Agent 框架 | **自建 Orchestrator** | 灵活控制任务编排、状态机、重试 |
| Tool Use | **Claude Tool Use (Function Calling)** | Agent 调用文档/幻灯片/搜索等工具 |
| 语音 | **Whisper API / 讯飞 ASR** | 语音转文本 |
| 向量检索 | **Embedding + 向量数据库（可选）** | 上下文记忆与检索 |

---

## 四、六大场景模块详细设计

### 场景 A：意图/指令入口（IM）

#### 功能描述

IM 是整个系统的入口和协作通道。用户在群聊或单聊中通过自然语言（文本/语音）发出指令，Agent 捕捉意图并启动任务。

#### 详细流程

```
用户在 IM 中输入/说出指令
    │
    ▼
┌─────────────────────────┐
│  输入预处理              │
│  - 文本：直接提取        │
│  - 语音：ASR 转文本      │
│  - @Agent 触发 / 关键词  │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  意图识别               │
│  - 是否为任务指令？      │
│  - 是否为追问/修改？     │
│  - 是否为进度查询？      │
│  - 是否为闲聊（忽略）？  │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│  上下文组装             │
│  - 当前对话上下文        │
│  - 历史任务上下文        │
│  - @提及的人员信息       │
│  - 引用的消息内容        │
└────────────┬────────────┘
             ▼
      传递给场景 B（Planner）
```

#### 核心交互设计

```
┌──────────────────────────────────────────┐
│  IM 对话界面                              │
│                                          │
│  张三: 我们下周要给客户做个产品介绍，      │
│       需要一份方案文档和 PPT               │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │ 🤖 Agent-Pilot                      │ │
│  │                                     │ │
│  │ 收到！我来帮你完成这个任务。          │ │
│  │ 我将为你：                           │ │
│  │                                     │ │
│  │ 1. 📄 生成产品介绍方案文档            │ │
│  │ 2. 📊 基于文档生成演示 PPT            │ │
│  │ 3. 📤 完成后发送分享链接              │ │
│  │                                     │ │
│  │ 请问产品的核心卖点和目标客户是？      │ │
│  │                                     │ │
│  │ [确认开始] [修改计划] [取消]          │ │
│  └─────────────────────────────────────┘ │
│                                          │
│  张三: 核心卖点是 AI 协同办公，           │
│       目标客户是中大型企业                 │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │ 🤖 Agent-Pilot                      │ │
│  │                                     │ │
│  │ 明白，开始执行 ━━━━━━━━━━░░ 20%     │ │
│  │ 当前：正在生成方案文档大纲...         │ │
│  │                                     │ │
│  │ [查看进度] [暂停]                    │ │
│  └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
```

#### 支持的指令类型

| 指令类型 | 示例 | Agent 行为 |
|---------|------|-----------|
| 创建任务 | "帮我写一份产品方案" | 启动 Planner → Doc 生成 |
| 组合任务 | "写个方案然后做成 PPT" | 启动 Planner → Doc → Slides 串联 |
| 查询进度 | "文档写到哪了？" | 返回当前任务状态 |
| 修改内容 | "第二章加上竞品分析" | 定位文档 → 插入/修改 |
| 语音指令 | [语音] "总结一下今天的讨论" | ASR → 意图识别 → 执行 |
| 分享交付 | "把 PPT 发给李四" | 生成分享链接 → 推送 |

#### 数据模型

```json
{
  "IMMessage": {
    "id": "msg_001",
    "chatId": "chat_group_001",
    "chatType": "group | private",
    "senderId": "user_001",
    "content": {
      "type": "text | voice | image | file",
      "text": "帮我写一份产品方案和PPT",
      "voiceUrl": null,
      "duration": null
    },
    "mentions": ["agent_pilot"],
    "replyTo": null,
    "timestamp": "2026-04-24T10:30:00Z"
  }
}
```

---

### 场景 B：任务理解与规划（Planner）

#### 功能描述

Planner 是 Agent 的大脑。接收来自 IM 的意图，将其拆解为可执行的子任务序列，并决定调用哪些场景模块、以什么顺序执行。

#### 详细流程

```
意图输入（来自场景 A）
    │
    ▼
┌──────────────────────────────┐
│  1. 意图分类与确认            │
│  - 任务类型识别               │
│  - 必要信息是否充足？          │
│  - 需要向用户澄清什么？       │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  2. 任务拆解（Task Decompose）│
│  - 拆分为原子子任务            │
│  - 确定子任务依赖关系          │
│  - 估算每步耗时               │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  3. 执行计划生成               │
│  - 编排场景模块调用顺序        │
│  - 分配每步所需的 Tool         │
│  - 生成 DAG（有向无环图）      │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  4. 计划确认                  │
│  - 向用户展示计划摘要          │
│  - 等待确认/修改              │
│  - 确认后开始执行              │
└──────────────┬───────────────┘
               ▼
       传递给 Orchestrator 执行
```

#### Planner 的 LLM Prompt 设计

```
你是 Agent-Pilot 的任务规划器。

用户在 IM 中的消息：{user_message}
对话上下文：{chat_context}

你的职责：
1. 理解用户真正想要完成什么
2. 将任务拆解为子任务，每个子任务对应以下工具之一：
   - create_document: 创建/编辑文档
   - create_slides: 创建/编辑演示稿
   - create_canvas: 创建自由画布
   - search_context: 搜索相关上下文
   - summarize_chat: 总结聊天内容
   - share_deliverable: 分享交付物
   - notify_user: 通知用户

3. 输出 JSON 格式的执行计划：
{
  "intent": "用户意图的一句话描述",
  "clarifications_needed": ["需要向用户确认的问题"],
  "tasks": [
    {
      "id": "task_1",
      "name": "任务名称",
      "tool": "工具名",
      "params": {},
      "depends_on": [],
      "estimated_seconds": 30
    }
  ]
}
```

#### 执行计划示例

```json
{
  "intent": "为客户创建产品介绍方案文档和演示PPT",
  "clarifications_needed": [],
  "tasks": [
    {
      "id": "task_1",
      "name": "收集产品信息",
      "tool": "search_context",
      "params": {
        "query": "产品核心功能、卖点、目标客户",
        "sources": ["chat_history", "existing_docs"]
      },
      "depends_on": [],
      "estimated_seconds": 10
    },
    {
      "id": "task_2",
      "name": "生成方案文档",
      "tool": "create_document",
      "params": {
        "title": "XX产品介绍方案",
        "outline": ["产品概述", "核心功能", "竞争优势", "目标客户", "实施方案"],
        "style": "formal",
        "context_from": "task_1"
      },
      "depends_on": ["task_1"],
      "estimated_seconds": 45
    },
    {
      "id": "task_3",
      "name": "生成演示PPT",
      "tool": "create_slides",
      "params": {
        "source_doc": "task_2",
        "slide_count": 12,
        "style": "professional",
        "include_charts": true
      },
      "depends_on": ["task_2"],
      "estimated_seconds": 60
    },
    {
      "id": "task_4",
      "name": "交付与通知",
      "tool": "share_deliverable",
      "params": {
        "targets": ["task_2", "task_3"],
        "share_to": "current_chat",
        "message": "方案文档和PPT已生成完毕"
      },
      "depends_on": ["task_3"],
      "estimated_seconds": 5
    }
  ]
}
```

---

### 场景 C：文档/白板生成与编辑（Doc Engine）

#### 功能描述

接受 Planner 的指令，自动生成并迭代文档或白板内容。支持实时协同编辑，Agent 和用户可同时操作文档。

#### 详细流程

```
接收生成指令（来自 Planner）
    │
    ▼
┌──────────────────────────────┐
│  1. 大纲生成                  │
│  - 根据上下文生成文档大纲      │
│  - 推送大纲到 IM 供用户确认    │
│  - 用户可通过 IM 修改大纲      │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  2. 内容填充                  │
│  - 逐章节生成内容             │
│  - 支持流式输出（边生成边展示）│
│  - 实时推送进度到 IM          │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  3. 格式优化                  │
│  - 标题层级规范化             │
│  - 列表、表格、代码块格式化   │
│  - 插入图表占位符              │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  4. 交互式修改                │
│  - 用户在文档中直接编辑       │
│  - 用户在 IM 中语音/文本修改  │
│  - Agent 实时响应修改指令      │
│  - 通过 CRDT 保证多端一致     │
└──────────────┬───────────────┘
               ▼
       文档就绪，通知 Planner
```

#### 文档数据模型

```json
{
  "Document": {
    "id": "doc_001",
    "title": "XX产品介绍方案",
    "taskId": "task_002",
    "createdBy": "agent_pilot",
    "collaborators": ["user_001", "agent_pilot"],
    "status": "draft | reviewing | finalized",
    "content": {
      "format": "delta",
      "ops": [
        {"insert": "产品概述\n", "attributes": {"header": 1}},
        {"insert": "我们的产品致力于..."},
        {"insert": "\n核心功能\n", "attributes": {"header": 2}}
      ]
    },
    "outline": [
      {"level": 1, "title": "产品概述", "status": "completed"},
      {"level": 1, "title": "核心功能", "status": "in_progress"},
      {"level": 1, "title": "竞争优势", "status": "pending"}
    ],
    "version": 12,
    "lastModified": "2026-04-24T10:45:00Z"
  }
}
```

#### 文档编辑器 UI 设计

```
┌──────────────────────────────────────────────────────────────┐
│  📄 XX产品介绍方案                    [分享] [导出] [历史]    │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  # 产品概述                                                  │
│                                                              │
│  我们的产品 AgentPilot 是一款面向中大型企业的                 │
│  AI 协同办公解决方案...                                      │
│                                                              │
│  ## 核心功能                                                 │
│                                                              │
│  | 功能     | 描述           | 优势         |                │
│  |---------|---------------|-------------|                  │
│  | IM 协同  | 自然语言驱动    | 零学习成本   |                │
│  | 文档生成  | AI 自动撰写    | 效率提升10x  |                │
│  | PPT 生成 | 一键成稿       | 专业排版     |                │
│  │                                                          │
│  ░░░░ Agent 正在生成 "竞争优势" 章节...                      │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  🤖 对 Agent 说: [在第二章补充一个架构图___________] [发送]   │
└──────────────────────────────────────────────────────────────┘
```

---

### 场景 D：演示稿/画布生成与排练（Slides Engine）

#### 功能描述

将文档内容或用户指令结构化为演示材料（PPT 或自由画布），支持模板选择、布局排版、动画预览和演练。

#### 详细流程

```
接收生成指令（来自 Planner 或 Doc Engine 产出）
    │
    ▼
┌──────────────────────────────┐
│  1. 结构规划                  │
│  - 分析源文档结构             │
│  - 确定幻灯片数量与章节分布   │
│  - 生成 Slide Outline        │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  2. 模板匹配与布局            │
│  - 选择/推荐演示模板          │
│  - 为每页选择合适的布局        │
│  - 分配内容到布局 slot        │
│  Layout 类型：                │
│  - 标题页 (title_slide)       │
│  - 标题+正文 (title_body)     │
│  - 两栏对比 (two_column)      │
│  - 图表页 (chart_slide)       │
│  - 图片+文字 (image_text)     │
│  - 纯图片 (full_image)       │
│  - 总结页 (summary_slide)     │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  3. 内容生成                  │
│  - 提炼关键信息为要点         │
│  - 生成 Speaker Notes        │
│  - 生成图表数据               │
│  - AI 配图建议                │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  4. 渲染与预览               │
│  - 渲染为可交互的幻灯片       │
│  - 支持拖拽调整               │
│  - 演练模式（全屏+计时）      │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  5. 迭代修改                  │
│  - IM 指令修改 ("第3页换个图") │
│  - 直接在画布上编辑           │
│  - Agent 智能调整排版         │
└──────────────┘
```

#### 幻灯片数据模型

```json
{
  "Presentation": {
    "id": "ppt_001",
    "title": "XX产品介绍",
    "taskId": "task_003",
    "template": "professional_blue",
    "slides": [
      {
        "id": "slide_1",
        "order": 1,
        "layout": "title_slide",
        "elements": [
          {
            "type": "text",
            "role": "title",
            "content": "XX 产品介绍",
            "style": {"fontSize": 36, "fontWeight": "bold", "color": "#1a1a2e"}
          },
          {
            "type": "text",
            "role": "subtitle",
            "content": "AI 驱动的下一代协同办公",
            "style": {"fontSize": 18, "color": "#666"}
          }
        ],
        "speakerNotes": "欢迎各位，今天为大家介绍...",
        "transition": "fade"
      },
      {
        "id": "slide_2",
        "order": 2,
        "layout": "two_column",
        "elements": [
          {
            "type": "text",
            "role": "title",
            "content": "核心功能"
          },
          {
            "type": "list",
            "role": "left_column",
            "items": ["IM 自然语言交互", "智能文档生成", "一键 PPT"]
          },
          {
            "type": "chart",
            "role": "right_column",
            "chartType": "bar",
            "data": {"labels": ["传统方式", "Agent-Pilot"], "values": [100, 15]}
          }
        ],
        "speakerNotes": "我们的三大核心功能..."
      }
    ],
    "globalStyle": {
      "primaryColor": "#1a1a2e",
      "accentColor": "#e94560",
      "fontFamily": "Noto Sans SC",
      "backgroundColor": "#ffffff"
    }
  }
}
```

#### Slides 编辑器 UI 设计

```
┌──────────────────────────────────────────────────────────────────┐
│  📊 XX产品介绍              [演练] [导出PDF] [分享] [AI助手]     │
├──────┬───────────────────────────────────────────────────────────┤
│      │                                                           │
│ [1]  │   ┌───────────────────────────────────────────┐          │
│ ██   │   │                                           │          │
│      │   │           XX 产品介绍                      │          │
│ [2]  │   │    AI 驱动的下一代协同办公                  │          │
│ ██   │   │                                           │          │
│      │   │                                           │          │
│ [3]  │   └───────────────────────────────────────────┘          │
│ ██   │                                                           │
│      │   Speaker Notes:                                          │
│ [4]  │   欢迎各位，今天为大家介绍我们的新产品...                  │
│ ██   │                                                           │
│      ├───────────────────────────────────────────────────────────┤
│ [+]  │  🤖 [把第2页的柱状图换成饼图_______________] [发送]        │
└──────┴───────────────────────────────────────────────────────────┘
```

---

### 场景 E：多端协作与一致性（Sync Framework）

#### 功能描述

构建一套跨移动端与桌面端的实时同步框架，保证任何一端的操作能无缝体现在另一端。

#### 同步架构

```
┌──────────────┐          ┌──────────────┐
│   移动端      │          │   桌面端      │
│  (Flutter)   │          │  (Flutter)   │
│              │          │              │
│ ┌──────────┐ │          │ ┌──────────┐ │
│ │ Local    │ │          │ │ Local    │ │
│ │ CRDT     │ │          │ │ CRDT     │ │
│ │ Store    │ │          │ │ Store    │ │
│ └────┬─────┘ │          │ └────┬─────┘ │
│      │       │          │      │       │
│ ┌────┴─────┐ │          │ ┌────┴─────┐ │
│ │ Sync     │ │          │ │ Sync     │ │
│ │ Client   │ │          │ │ Client   │ │
│ └────┬─────┘ │          │ └────┬─────┘ │
└──────┼───────┘          └──────┼───────┘
       │                         │
       │    ┌──────────────┐     │
       └───►│  Sync Server │◄────┘
            │              │
            │  - WebSocket │
            │  - CRDT Merge│
            │  - Conflict  │
            │    Resolver  │
            │  - Event     │
            │    Broadcast │
            └──────────────┘
```

#### 同步的数据类型

| 数据类型 | 同步策略 | 冲突解决 |
|---------|---------|---------|
| IM 消息 | 服务端权威 + 本地乐观更新 | 服务端时间戳排序 |
| 文档内容 | CRDT (Yjs Delta) | 自动合并，无冲突 |
| 幻灯片结构 | 操作变换 (OT) | Last-Writer-Wins per element |
| 任务状态 | 服务端权威 | 服务端单点决策 |
| 用户状态（在线/离线） | 心跳 + 服务端推送 | 服务端权威 |

#### 离线支持流程（加分项）

```
正常在线工作
    │
    ▼ (网络断开)
┌──────────────────────────────┐
│  离线模式激活                 │
│  - 本地 CRDT 存储继续工作     │
│  - 操作记录到 Operation Log   │
│  - UI 显示离线标识            │
│  - 部分 AI 功能降级           │
└──────────────┬───────────────┘
               ▼ (网络恢复)
┌──────────────────────────────┐
│  同步恢复                     │
│  - 上传本地 Operation Log     │
│  - 服务端 CRDT 合并           │
│  - 拉取远端变更               │
│  - 冲突提示（如有）           │
│  - UI 恢复在线标识            │
└──────────────────────────────┘
```

#### 同步消息协议

```json
{
  "SyncMessage": {
    "type": "delta | state | presence | ack",
    "source": {
      "deviceId": "device_001",
      "platform": "mobile | desktop",
      "userId": "user_001"
    },
    "target": {
      "resourceType": "document | presentation | task",
      "resourceId": "doc_001"
    },
    "payload": {
      "version": 12,
      "operations": [
        {
          "type": "insert | delete | retain | update",
          "position": 42,
          "content": "新增内容",
          "timestamp": "2026-04-24T10:45:00.123Z"
        }
      ]
    },
    "timestamp": "2026-04-24T10:45:00.123Z"
  }
}
```

---

### 场景 F：总结与交付（Delivery）

#### 功能描述

任务完成后，输出面向汇报/归档的成果，包括分享链接、导出文件、工作总结等。

#### 详细流程

```
所有子任务完成
    │
    ▼
┌──────────────────────────────┐
│  1. 成果汇总                  │
│  - 列出本次任务所有产出物      │
│  - 统计用时与修改次数          │
│  - 生成任务执行摘要            │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  2. 导出与格式化              │
│  - 文档：导出为 PDF/DOCX/MD  │
│  - PPT：导出为 PDF/PPTX      │
│  - 画布：导出为 PNG/SVG/PDF  │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  3. 分享                      │
│  - 生成在线浏览链接           │
│  - 设置访问权限               │
│  - 推送到 IM 聊天             │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│  4. 归档                      │
│  - 保存到项目知识库            │
│  - 打标签分类                  │
│  - 关联到 IM 对话记录          │
└──────────────────────────────┘
```

#### 交付消息模板

```
┌─────────────────────────────────────────┐
│ 🤖 Agent-Pilot                          │
│                                         │
│ ✅ 任务完成！以下是本次工作成果：         │
│                                         │
│ 📄 产品介绍方案                          │
│    ├ 在线查看: https://xxx/doc/001       │
│    └ 下载 PDF: [点击下载]                │
│                                         │
│ 📊 产品介绍PPT（12页）                   │
│    ├ 在线查看: https://xxx/ppt/001       │
│    ├ 下载 PPTX: [点击下载]               │
│    └ 演练模式: [开始演练]                │
│                                         │
│ ⏱ 总用时：3分12秒                       │
│ 📝 迭代次数：2次                         │
│                                         │
│ 需要修改或有其他需求吗？                  │
└─────────────────────────────────────────┘
```

---

## 五、Agent 核心引擎设计

### 5.1 Agent Orchestrator 架构

```
┌─────────────────────────────────────────────────────┐
│                 Agent Orchestrator                    │
│                                                     │
│  ┌─────────────┐    ┌──────────────────────────┐    │
│  │ Intent      │    │ Task State Machine        │    │
│  │ Classifier  │    │                          │    │
│  │             │    │  pending ──→ planning     │    │
│  │ 文本/语音 → │    │     │         │          │    │
│  │ 意图类型    │    │     │    ┌────┘          │    │
│  └──────┬──────┘    │     ▼    ▼              │    │
│         │           │  executing ──→ reviewing │    │
│         │           │     │           │        │    │
│         ▼           │     │    ┌──────┘        │    │
│  ┌─────────────┐    │     ▼    ▼              │    │
│  │ Planner     │    │  completed / failed      │    │
│  │ (LLM)       │    └──────────────────────────┘    │
│  │             │                                     │
│  │ 意图 →      │    ┌──────────────────────────┐    │
│  │ 执行计划    │    │ Tool Registry             │    │
│  └──────┬──────┘    │                          │    │
│         │           │  create_document          │    │
│         ▼           │  edit_document            │    │
│  ┌─────────────┐    │  create_slides            │    │
│  │ Executor    │───►│  edit_slides              │    │
│  │             │    │  search_context           │    │
│  │ 按 DAG 顺序│    │  summarize_chat           │    │
│  │ 调用 Tool   │    │  share_deliverable        │    │
│  └──────┬──────┘    │  export_file              │    │
│         │           │  notify_user              │    │
│         ▼           └──────────────────────────┘    │
│  ┌─────────────┐                                     │
│  │ Monitor     │    ┌──────────────────────────┐    │
│  │             │    │ Context Memory            │    │
│  │ 进度追踪    │    │                          │    │
│  │ 错误恢复    │    │  - 当前任务上下文          │    │
│  │ 用户通知    │    │  - 历史对话摘要            │    │
│  └─────────────┘    │  - 用户偏好               │    │
│                     │  - 已生成产出物            │    │
│                     └──────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

### 5.2 LLM 调用策略

```
┌─────────────────────────────────────────────┐
│            LLM 调用层级                      │
│                                             │
│  Level 1 - 快速响应（Haiku/小模型）          │
│  ├ 意图分类                                  │
│  ├ 关键词提取                                │
│  └ 简单问答                                  │
│                                             │
│  Level 2 - 标准推理（Sonnet 4.6）            │
│  ├ 任务规划与拆解                            │
│  ├ 文档内容生成                              │
│  ├ 幻灯片内容提炼                            │
│  └ 对话总结                                  │
│                                             │
│  Level 3 - 复杂推理（Opus 4.6，按需）        │
│  ├ 复杂多步骤规划                            │
│  ├ 长文档理解与重构                          │
│  └ 跨文档关联分析                            │
└─────────────────────────────────────────────┘
```

### 5.3 Tool Use 定义

```json
{
  "tools": [
    {
      "name": "create_document",
      "description": "创建新文档，支持指定标题、大纲和内容风格",
      "input_schema": {
        "type": "object",
        "properties": {
          "title": {"type": "string"},
          "outline": {"type": "array", "items": {"type": "string"}},
          "style": {"type": "string", "enum": ["formal", "casual", "technical"]},
          "context": {"type": "string"},
          "language": {"type": "string", "default": "zh-CN"}
        },
        "required": ["title"]
      }
    },
    {
      "name": "edit_document",
      "description": "编辑已有文档的指定部分",
      "input_schema": {
        "type": "object",
        "properties": {
          "documentId": {"type": "string"},
          "action": {"type": "string", "enum": ["insert", "replace", "delete", "append"]},
          "section": {"type": "string"},
          "content": {"type": "string"},
          "instruction": {"type": "string"}
        },
        "required": ["documentId", "action"]
      }
    },
    {
      "name": "create_slides",
      "description": "从文档或描述创建演示稿",
      "input_schema": {
        "type": "object",
        "properties": {
          "sourceDocId": {"type": "string"},
          "title": {"type": "string"},
          "slideCount": {"type": "integer"},
          "template": {"type": "string"},
          "includeCharts": {"type": "boolean"},
          "audienceType": {"type": "string"}
        },
        "required": ["title"]
      }
    },
    {
      "name": "edit_slides",
      "description": "编辑演示稿中的指定页面或元素",
      "input_schema": {
        "type": "object",
        "properties": {
          "presentationId": {"type": "string"},
          "slideId": {"type": "string"},
          "action": {"type": "string", "enum": ["update_text", "change_layout", "add_element", "remove_element", "reorder"]},
          "instruction": {"type": "string"}
        },
        "required": ["presentationId", "action"]
      }
    },
    {
      "name": "summarize_chat",
      "description": "总结 IM 对话内容",
      "input_schema": {
        "type": "object",
        "properties": {
          "chatId": {"type": "string"},
          "messageRange": {"type": "object"},
          "focusTopics": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["chatId"]
      }
    },
    {
      "name": "share_deliverable",
      "description": "分享交付物到指定目标",
      "input_schema": {
        "type": "object",
        "properties": {
          "resourceId": {"type": "string"},
          "resourceType": {"type": "string", "enum": ["document", "presentation"]},
          "shareTo": {"type": "string", "enum": ["current_chat", "specific_user", "link"]},
          "targetId": {"type": "string"},
          "exportFormat": {"type": "string", "enum": ["pdf", "docx", "pptx", "png"]}
        },
        "required": ["resourceId", "resourceType", "shareTo"]
      }
    }
  ]
}
```

### 5.4 Agent 主动能力（加分项）

```
Agent 不只是被动执行，还能主动：

1. 任务澄清
   - 信息不足时主动追问
   - "你希望 PPT 面向技术团队还是管理层？"

2. 讨论总结
   - 群聊中检测到讨论告一段落时主动总结
   - "刚才的讨论涉及3个要点，需要我整理成文档吗？"

3. 上下文推荐
   - 根据当前任务推荐下一步
   - "文档已完成，建议接下来生成 PPT。要开始吗？"

4. 异常恢复
   - 生成失败时自动重试或降级
   - "PPT 生成遇到问题，已自动切换到简化模板重新生成"
```

---

## 六、多端协同框架

### 6.1 Flutter 跨端统一策略

```dart
// 平台自适应布局框架
class AdaptiveScaffold extends StatelessWidget {
  // 根据平台自动选择布局
  // 移动端：底部导航 + 全屏页面
  // 桌面端：侧边栏 + 多面板

  Widget build(BuildContext context) {
    if (isDesktop) {
      return DesktopLayout(
        sidebar: NavigationRail(...),
        mainPanel: ...,
        detailPanel: ...,  // 桌面端可以同时显示列表+详情
      );
    } else {
      return MobileLayout(
        bottomNav: BottomNavigationBar(...),
        body: ...,  // 移动端单页面导航
      );
    }
  }
}
```

### 6.2 移动端 vs 桌面端差异处理

| 功能 | 移动端 | 桌面端 |
|------|--------|--------|
| 导航 | 底部 Tab + 页面跳转 | 侧边栏 + 多面板 |
| IM 聊天 | 全屏对话 | 左侧列表 + 右侧对话 |
| 文档编辑 | 全屏编辑器 | 分屏（文档+AI助手面板） |
| PPT 编辑 | 纵向滑动浏览，单页编辑 | 左侧缩略图 + 中央画布 + 右侧属性 |
| 语音输入 | 长按录音按钮 | 快捷键触发 |
| 拖拽操作 | 长按拖拽 | 鼠标拖拽 |
| 键盘快捷键 | 不适用 | Ctrl+S 保存, Ctrl+Enter 发送 |

### 6.3 状态同步层

```dart
// 同步状态管理
class SyncProvider {
  final WebSocketChannel _channel;
  final CRDTDocument _localDoc;

  // 本地操作 → 发送到服务端 → 广播到其他端
  void applyLocalChange(Operation op) {
    _localDoc.apply(op);           // 1. 本地立即生效
    _channel.sink.add(op.toJson()); // 2. 发送到服务端
  }

  // 接收远端变更 → 合并到本地
  void onRemoteChange(Operation op) {
    _localDoc.merge(op);           // CRDT 自动合并，无冲突
    notifyListeners();             // 更新 UI
  }
}
```

---

## 七、数据模型与协议

### 7.1 核心实体关系

```
User ──┬── Chat (1:N)
       │     │
       │     ├── Message (1:N)
       │     │
       │     └── Task (1:N)
       │           │
       │           ├── SubTask (1:N)
       │           │
       │           ├── Document (0:N)
       │           │
       │           └── Presentation (0:N)
       │
       └── Device (1:N) ── SyncSession (1:1)
```

### 7.2 API 接口设计

#### 认证

```
POST   /api/auth/login              # 登录
POST   /api/auth/refresh            # 刷新 Token
```

#### IM

```
GET    /api/chats                   # 获取聊天列表
GET    /api/chats/:id/messages      # 获取消息历史
POST   /api/chats/:id/messages      # 发送消息
WS     /ws/chat/:id                 # 实时消息 WebSocket
```

#### Agent

```
POST   /api/agent/intent            # 提交意图（触发 Agent）
GET    /api/agent/tasks/:id         # 获取任务状态
POST   /api/agent/tasks/:id/cancel  # 取消任务
POST   /api/agent/tasks/:id/modify  # 修改任务计划
WS     /ws/agent/tasks/:id          # 任务进度实时推送
```

#### 文档

```
POST   /api/documents               # 创建文档
GET    /api/documents/:id           # 获取文档
PATCH  /api/documents/:id           # 更新文档元数据
WS     /ws/documents/:id            # 文档协同编辑 WebSocket
POST   /api/documents/:id/export    # 导出文档
```

#### 演示稿

```
POST   /api/presentations           # 创建演示稿
GET    /api/presentations/:id       # 获取演示稿
PATCH  /api/presentations/:id       # 更新演示稿
WS     /ws/presentations/:id        # 演示稿协同编辑 WebSocket
POST   /api/presentations/:id/export # 导出演示稿
```

#### 同步

```
WS     /ws/sync                     # 全局同步 WebSocket
POST   /api/sync/resolve            # 手动解决冲突
GET    /api/sync/status             # 同步状态查询
```

### 7.3 WebSocket 消息协议

```json
{
  "protocol_version": "1.0",
  "message_types": {
    "agent_progress": {
      "taskId": "string",
      "step": "string",
      "progress": "number (0-100)",
      "message": "string",
      "artifacts": ["resourceId"]
    },
    "doc_delta": {
      "documentId": "string",
      "version": "number",
      "delta": "QuillDelta",
      "author": "string"
    },
    "slides_update": {
      "presentationId": "string",
      "version": "number",
      "slideId": "string",
      "operation": "object",
      "author": "string"
    },
    "presence": {
      "userId": "string",
      "deviceId": "string",
      "status": "online | idle | offline",
      "activeResource": "string",
      "cursor": "object"
    },
    "im_message": {
      "chatId": "string",
      "message": "IMMessage"
    }
  }
}
```

---

## 八、端到端工作流编排

### 8.1 典型工作流：从 IM 对话到 PPT

这是演示中最核心的端到端工作流，完整串联所有六个场景模块。

```
时间线    场景     动作                              数据流向
─────────────────────────────────────────────────────────────
T+0s      A      用户在IM中: "@Agent 帮我基于        IM → Intent Parser
                  今天的讨论写个方案和PPT"

T+2s      B      Agent 分析意图，生成执行计划          Intent → Planner
                  Agent 回复: "好的，我将：              Planner → IM (确认)
                  1.总结讨论 2.生成文档 3.生成PPT"
                  用户确认: "开始吧"

T+5s      B→C    Planner 启动子任务1:                  Chat History → LLM
                  总结IM讨论内容

T+15s     C      子任务2: 基于总结生成文档大纲          Summary → Doc Engine
                  Agent 在IM推送大纲预览
                  用户: "大纲OK，开始写"

T+20s     C      子任务3: 逐章节生成文档内容            Outline → LLM → Doc
                  (流式输出，实时可见)
                  进度推送到IM: "文档生成中 60%..."

T+60s     C→E    文档生成完毕，多端同步                 Doc → Sync Engine
                  移动端和桌面端同时可见                  Sync → All Devices

T+62s     C      用户在桌面端打开文档微调               User Edit → CRDT
                  移动端实时看到修改                     CRDT → Mobile Sync

T+70s     D      子任务4: 基于文档生成PPT              Doc → Slides Engine
                  Agent: "正在生成PPT..."
                  12页幻灯片逐页生成

T+120s    D→E    PPT生成完毕，多端同步                  Slides → Sync Engine
                  用户在移动端浏览PPT缩略图              Sync → All Devices
                  用户在桌面端编辑PPT详情

T+130s    D      用户在IM: "第3页换个配色"              IM → Agent → Slides
                  Agent 修改并同步

T+140s    F      所有内容就绪                          All Artifacts → Delivery
                  Agent: "✅ 全部完成！                  Delivery → IM
                  📄 方案文档: [查看] [下载PDF]
                  📊 演示PPT: [查看] [下载] [演练]"

T+145s    F      用户: "发给李四"                       Share → Target User
                  Agent 生成分享链接推送
```

### 8.2 其他典型工作流

#### 工作流 B：讨论总结 → 文档归档

```
场景 A → 场景 B → 场景 C → 场景 F

IM 讨论 → Agent 识别总结意图 → 自动总结 → 生成文档 → 归档分享
```

#### 工作流 C：语音指令 → 快速 PPT

```
场景 A → 场景 B → 场景 D → 场景 F

语音 "帮我做个5页的项目汇报PPT" → 规划 → 直接生成PPT → 交付
```

#### 工作流 D：多人协作 → 文档+画布

```
场景 A → 场景 B → 场景 C + 场景 E → 场景 F

多人在IM讨论 → Agent 收集需求 → 生成文档 → 多端实时协同编辑 → 交付
```

### 8.3 工作流编排引擎

```dart
class WorkflowOrchestrator {
  final PlannedWorkflow workflow;
  final Map<String, ToolExecutor> tools;

  Future<void> execute() async {
    for (final step in workflow.topologicalSort()) {
      // 检查前置依赖是否完成
      await _waitForDependencies(step.dependsOn);

      // 通知用户当前进度
      _notifyProgress(step);

      // 执行当前步骤
      final result = await tools[step.tool]!.execute(step.params);

      // 更新任务状态
      _updateTaskState(step.id, result);

      // 检查是否需要用户确认
      if (step.requiresConfirmation) {
        await _waitForUserConfirmation(step);
      }
    }

    // 所有步骤完成，触发交付
    await _triggerDelivery();
  }
}
```

---

## 九、演示场景脚本

### 9.1 演示一：端到端全链路（约 5 分钟）

**目标：展示从 IM 对话到 PPT 交付的完整闭环**

```
Step 1 [桌面端] - IM 入口
- 打开 Agent-Pilot 桌面端
- 进入 "产品团队" 群聊
- 输入: "@Agent-Pilot 帮我基于我们上周的讨论，
         写一份新产品的介绍方案，然后做成PPT"
- 展示：Agent 回复执行计划，用户确认

Step 2 [桌面端] - 文档生成
- Agent 开始生成文档，进度条在 IM 中实时更新
- 切换到文档模块，看到文档正在实时填充内容
- 展示：流式生成效果

Step 3 [移动端] - 多端同步
- 拿起手机，打开移动端 App
- 展示：IM 中可以看到相同的任务进度
- 打开文档：内容与桌面端完全一致
- 在移动端修改文档标题

Step 4 [桌面端] - 实时同步
- 回到桌面端，展示标题已经同步更新
- 在 IM 中输入: "在文档里加一个竞品对比表格"
- 展示：Agent 自动在文档中插入表格

Step 5 [桌面端] - PPT 生成
- Agent 自动开始基于文档生成 PPT
- 切换到 PPT 模块，展示幻灯片逐页生成
- 在 IM 中输入: "第3页的配色改成蓝色系"
- 展示：PPT 实时更新

Step 6 [移动端+桌面端] - 交付
- Agent 在 IM 中发送完成消息，附带分享链接
- 移动端点击链接可以浏览 PPT
- 桌面端可以导出 PDF
```

### 9.2 演示二：语音驱动（约 2 分钟）

```
Step 1 [移动端] - 语音入口
- 长按语音按钮
- 说: "帮我把今天群里关于新功能的讨论总结一下，做成一份简短的汇报文档"
- 展示：语音转文本 → Agent 理解 → 开始执行

Step 2 [移动端] - 结果查看
- Agent 自动总结群聊讨论
- 生成汇报文档
- 在 IM 中返回文档链接
- 点击直接在移动端预览
```

### 9.3 演示三：多场景独立演示（各约 1 分钟）

```
A. 单独演示意图理解
- 输入模糊指令: "整理一下最近的东西"
- Agent 主动追问: "你是想整理最近的聊天记录、文档还是任务？"
- 体现 Agent 的澄清能力

B. 单独演示文档协同编辑
- 在桌面端和移动端同时打开一份文档
- 双端同时编辑不同段落
- 展示 CRDT 无冲突合并效果

C. 单独演示 PPT 画布操作
- 通过自然语言指令操控 PPT
- "添加一页图表对比" → Agent 自动添加
- "把标题字号放大" → Agent 自动调整
```

---

## 十、开发阶段规划

### Phase 1：基础框架搭建（Week 1-2）

```
目标：跑通多端基础架构 + Agent 最小闭环

┌─────────────────────────────────────────────┐
│  Day 1-3: 项目初始化                         │
│  ├ Flutter 项目搭建（移动端 + 桌面端）        │
│  ├ 项目结构、路由、状态管理基础               │
│  ├ 后端服务初始化（API + WebSocket）          │
│  └ 数据库设计与初始化                        │
│                                             │
│  Day 4-7: 核心模块骨架                       │
│  ├ IM 模块：聊天列表、消息收发、@Agent 触发   │
│  ├ Agent 引擎：Intent Parser + 简易 Planner  │
│  ├ LLM 集成：Claude API Tool Use 接入        │
│  └ WebSocket 实时通信基础                    │
│                                             │
│  Day 8-10: 最小闭环验证                      │
│  ├ IM 输入 → Agent 理解 → 回复确认           │
│  ├ 简单任务执行（如文本回复）                 │
│  └ 移动端 + 桌面端基础 UI 联调               │
│                                             │
│  Day 11-14: 同步框架                         │
│  ├ WebSocket 长连接管理                      │
│  ├ 基础状态同步（任务状态、消息）             │
│  └ 多端登录与设备管理                        │
└─────────────────────────────────────────────┘

交付物：
✅ 可运行的移动端 + 桌面端 App（骨架）
✅ IM 基础聊天功能
✅ Agent 基础意图识别
✅ 多端同步基础框架
```

### Phase 2：文档引擎（Week 3-4）

```
目标：Agent 驱动的文档生成与协同编辑

┌─────────────────────────────────────────────┐
│  Day 15-18: 文档编辑器                       │
│  ├ 集成 flutter_quill / super_editor        │
│  ├ 富文本编辑基础功能                        │
│  ├ 桌面端：分屏编辑器布局                    │
│  └ 移动端：全屏编辑器适配                    │
│                                             │
│  Day 19-22: Agent 文档生成                   │
│  ├ create_document Tool 实现                 │
│  ├ 大纲生成 → 用户确认 → 内容填充流程        │
│  ├ 流式输出（打字机效果）                    │
│  └ edit_document Tool（修改/插入/删除）      │
│                                             │
│  Day 23-26: 文档协同                         │
│  ├ CRDT 集成（Yjs 或自实现简化版）            │
│  ├ 文档实时同步                              │
│  ├ 光标位置同步                              │
│  └ 冲突自动合并测试                          │
│                                             │
│  Day 27-28: 集成测试                         │
│  ├ IM → Agent → 文档生成 全链路测试          │
│  ├ 多端同步文档编辑测试                      │
│  └ Bug 修复与优化                            │
└─────────────────────────────────────────────┘

交付物：
✅ 完整的文档编辑器（多端适配）
✅ Agent 驱动的文档自动生成
✅ 文档实时协同编辑
✅ IM → 文档 全链路打通
```

### Phase 3：演示稿/画布引擎（Week 5-6）

```
目标：Agent 驱动的 PPT/画布 生成

┌─────────────────────────────────────────────┐
│  Day 29-33: Slides 渲染引擎                  │
│  ├ 幻灯片数据模型实现                        │
│  ├ 基础布局模板（标题页、正文页、图表页等）   │
│  ├ 幻灯片渲染 Widget                         │
│  ├ 桌面端：缩略图 + 画布 + 属性面板          │
│  └ 移动端：滑动浏览 + 单页编辑               │
│                                             │
│  Day 34-37: Agent PPT 生成                   │
│  ├ create_slides Tool 实现                   │
│  ├ 文档 → PPT 内容提炼与结构化               │
│  ├ 自动选择布局模板                          │
│  ├ Speaker Notes 生成                        │
│  └ edit_slides Tool（修改页面/元素）          │
│                                             │
│  Day 38-40: 画布操作                         │
│  ├ 元素拖拽、缩放、旋转                      │
│  ├ 文本框编辑                                │
│  ├ 简单图表渲染                              │
│  └ 演练模式（全屏播放 + 翻页）               │
│                                             │
│  Day 41-42: 集成与同步                       │
│  ├ PPT 多端同步                              │
│  ├ IM → 文档 → PPT 全链路测试                │
│  └ 导出 PDF 功能                             │
└─────────────────────────────────────────────┘

交付物：
✅ 完整的 PPT/画布 编辑器（多端适配）
✅ Agent 驱动的 PPT 自动生成
✅ 文档到 PPT 的自动转化
✅ IM → 文档 → PPT 全链路打通
```

### Phase 4：完善与打磨（Week 7-8）

```
目标：优化体验、添加加分项、准备演示

┌─────────────────────────────────────────────┐
│  Day 43-46: 体验优化                         │
│  ├ 语音输入集成                              │
│  ├ Agent 主动能力（澄清、推荐、总结）        │
│  ├ 进度可视化优化                            │
│  ├ 错误处理与重试机制                        │
│  └ 动画与过渡效果                            │
│                                             │
│  Day 47-49: 加分项                           │
│  ├ 离线支持（本地缓存 + 同步恢复）           │
│  ├ 富媒体支持（图片插入、表格操作）           │
│  └ 导出格式扩展（DOCX、PPTX）               │
│                                             │
│  Day 50-52: 交付与归档模块                   │
│  ├ 分享链接生成                              │
│  ├ 文件导出下载                              │
│  ├ 任务历史记录                              │
│  └ 成果归档                                  │
│                                             │
│  Day 53-56: 演示准备                         │
│  ├ 全链路端到端测试                          │
│  ├ 演示数据准备                              │
│  ├ 演示脚本排练                              │
│  ├ 性能优化                                  │
│  └ Bug 修复                                  │
└─────────────────────────────────────────────┘

交付物：
✅ 完整的 Agent-Pilot 产品
✅ 语音交互支持
✅ 离线支持
✅ 演示脚本与演示数据
```

---

## 十一、项目目录结构

```
agent-pilot/
├── client/                          # Flutter 客户端（移动端 + 桌面端统一代码库）
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app/
│   │   │   ├── app.dart             # App 入口
│   │   │   ├── router/
│   │   │   │   └── app_router.dart  # go_router 路由配置
│   │   │   ├── theme/
│   │   │   │   ├── app_theme.dart
│   │   │   │   └── app_colors.dart
│   │   │   └── di/
│   │   │       └── injection.dart   # 依赖注入
│   │   │
│   │   ├── core/
│   │   │   ├── network/
│   │   │   │   ├── api_client.dart       # dio HTTP 客户端
│   │   │   │   ├── ws_client.dart        # WebSocket 客户端
│   │   │   │   └── interceptors/
│   │   │   ├── sync/
│   │   │   │   ├── sync_engine.dart      # 同步引擎
│   │   │   │   ├── crdt_store.dart       # CRDT 本地存储
│   │   │   │   └── conflict_resolver.dart
│   │   │   ├── storage/
│   │   │   │   ├── local_storage.dart    # Hive/Isar 本地存储
│   │   │   │   └── secure_storage.dart
│   │   │   ├── platform/
│   │   │   │   ├── platform_info.dart    # 平台检测
│   │   │   │   └── adaptive_layout.dart  # 自适应布局
│   │   │   └── utils/
│   │   │
│   │   ├── features/
│   │   │   ├── auth/                     # 登录认证
│   │   │   │   ├── data/
│   │   │   │   ├── domain/
│   │   │   │   └── presentation/
│   │   │   │
│   │   │   ├── im/                       # IM 即时通讯模块
│   │   │   │   ├── data/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── chat.dart
│   │   │   │   │   │   ├── message.dart
│   │   │   │   │   │   └── participant.dart
│   │   │   │   │   ├── repositories/
│   │   │   │   │   │   └── chat_repository.dart
│   │   │   │   │   └── datasources/
│   │   │   │   │       ├── chat_remote_ds.dart
│   │   │   │   │       └── chat_local_ds.dart
│   │   │   │   ├── domain/
│   │   │   │   │   └── usecases/
│   │   │   │   │       ├── send_message.dart
│   │   │   │   │       ├── load_messages.dart
│   │   │   │   │       └── trigger_agent.dart
│   │   │   │   └── presentation/
│   │   │   │       ├── pages/
│   │   │   │       │   ├── chat_list_page.dart
│   │   │   │       │   └── chat_detail_page.dart
│   │   │   │       ├── widgets/
│   │   │   │       │   ├── message_bubble.dart
│   │   │   │       │   ├── agent_card.dart
│   │   │   │       │   ├── voice_input_button.dart
│   │   │   │       │   └── progress_indicator.dart
│   │   │   │       └── providers/
│   │   │   │           ├── chat_list_provider.dart
│   │   │   │           └── chat_detail_provider.dart
│   │   │   │
│   │   │   ├── document/                 # 文档模块
│   │   │   │   ├── data/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── document.dart
│   │   │   │   │   │   └── doc_delta.dart
│   │   │   │   │   └── repositories/
│   │   │   │   │       └── document_repository.dart
│   │   │   │   ├── domain/
│   │   │   │   │   └── usecases/
│   │   │   │   │       ├── create_document.dart
│   │   │   │   │       ├── edit_document.dart
│   │   │   │   │       └── export_document.dart
│   │   │   │   └── presentation/
│   │   │   │       ├── pages/
│   │   │   │       │   ├── document_list_page.dart
│   │   │   │       │   └── document_editor_page.dart
│   │   │   │       ├── widgets/
│   │   │   │       │   ├── rich_text_editor.dart
│   │   │   │       │   ├── outline_panel.dart
│   │   │   │       │   └── ai_assistant_panel.dart
│   │   │   │       └── providers/
│   │   │   │           ├── document_list_provider.dart
│   │   │   │           └── document_editor_provider.dart
│   │   │   │
│   │   │   ├── slides/                   # 演示稿模块
│   │   │   │   ├── data/
│   │   │   │   │   ├── models/
│   │   │   │   │   │   ├── presentation.dart
│   │   │   │   │   │   ├── slide.dart
│   │   │   │   │   │   └── slide_element.dart
│   │   │   │   │   └── repositories/
│   │   │   │   │       └── presentation_repository.dart
│   │   │   │   ├── domain/
│   │   │   │   │   └── usecases/
│   │   │   │   │       ├── create_presentation.dart
│   │   │   │   │       ├── edit_slide.dart
│   │   │   │   │       └── export_presentation.dart
│   │   │   │   └── presentation/
│   │   │   │       ├── pages/
│   │   │   │       │   ├── slides_list_page.dart
│   │   │   │       │   ├── slides_editor_page.dart
│   │   │   │       │   └── presentation_mode_page.dart
│   │   │   │       ├── widgets/
│   │   │   │       │   ├── slide_canvas.dart
│   │   │   │       │   ├── slide_thumbnail.dart
│   │   │   │       │   ├── element_toolbar.dart
│   │   │   │       │   └── speaker_notes_panel.dart
│   │   │   │       └── providers/
│   │   │   │           ├── slides_list_provider.dart
│   │   │   │           └── slides_editor_provider.dart
│   │   │   │
│   │   │   └── agent/                    # Agent 交互模块
│   │   │       ├── data/
│   │   │       │   ├── models/
│   │   │       │   │   ├── task.dart
│   │   │       │   │   ├── task_plan.dart
│   │   │       │   │   └── agent_message.dart
│   │   │       │   └── repositories/
│   │   │       │       └── agent_repository.dart
│   │   │       └── presentation/
│   │   │           ├── widgets/
│   │   │           │   ├── task_progress_card.dart
│   │   │           │   ├── plan_confirmation_dialog.dart
│   │   │           │   └── agent_status_bar.dart
│   │   │           └── providers/
│   │   │               └── agent_task_provider.dart
│   │   │
│   │   └── shared/
│   │       ├── widgets/
│   │       │   ├── adaptive_scaffold.dart
│   │       │   ├── loading_overlay.dart
│   │       │   └── error_widget.dart
│   │       └── extensions/
│   │
│   ├── test/
│   ├── android/
│   ├── ios/
│   ├── macos/
│   ├── windows/
│   └── pubspec.yaml
│
├── server/                              # 后端服务
│   ├── src/
│   │   ├── main.ts                      # 入口
│   │   ├── config/
│   │   │   ├── database.ts
│   │   │   └── llm.ts
│   │   ├── modules/
│   │   │   ├── auth/
│   │   │   ├── chat/
│   │   │   │   ├── chat.controller.ts
│   │   │   │   ├── chat.service.ts
│   │   │   │   ├── chat.gateway.ts      # WebSocket 网关
│   │   │   │   └── chat.model.ts
│   │   │   ├── document/
│   │   │   │   ├── document.controller.ts
│   │   │   │   ├── document.service.ts
│   │   │   │   ├── document.gateway.ts
│   │   │   │   └── document.model.ts
│   │   │   ├── presentation/
│   │   │   │   ├── presentation.controller.ts
│   │   │   │   ├── presentation.service.ts
│   │   │   │   ├── presentation.gateway.ts
│   │   │   │   └── presentation.model.ts
│   │   │   └── sync/
│   │   │       ├── sync.gateway.ts
│   │   │       └── sync.service.ts
│   │   │
│   │   ├── agent/                       # Agent 核心引擎
│   │   │   ├── orchestrator.ts          # 任务编排器
│   │   │   ├── planner.ts              # 任务规划器（LLM）
│   │   │   ├── intent_parser.ts        # 意图解析
│   │   │   ├── executor.ts             # 任务执行器
│   │   │   ├── monitor.ts             # 任务监控
│   │   │   ├── context_memory.ts      # 上下文记忆
│   │   │   └── tools/                  # Agent 工具集
│   │   │       ├── tool_registry.ts
│   │   │       ├── create_document.tool.ts
│   │   │       ├── edit_document.tool.ts
│   │   │       ├── create_slides.tool.ts
│   │   │       ├── edit_slides.tool.ts
│   │   │       ├── summarize_chat.tool.ts
│   │   │       ├── search_context.tool.ts
│   │   │       └── share_deliverable.tool.ts
│   │   │
│   │   └── common/
│   │       ├── llm/
│   │       │   ├── claude_client.ts     # Claude API 封装
│   │       │   └── prompt_templates.ts
│   │       ├── crdt/
│   │       │   └── yjs_adapter.ts
│   │       └── storage/
│   │           └── s3_client.ts
│   │
│   ├── prisma/
│   │   └── schema.prisma               # 数据库 Schema
│   ├── test/
│   ├── package.json
│   └── tsconfig.json
│
├── shared/                              # 前后端共享
│   ├── types/                           # 共享类型定义
│   │   ├── message.types.ts
│   │   ├── document.types.ts
│   │   ├── presentation.types.ts
│   │   └── agent.types.ts
│   └── protocols/                       # WebSocket 协议定义
│       └── ws_protocol.ts
│
├── docs/                                # 文档
│   ├── agent-pilot-workflow.md          # 本文档
│   ├── api-spec.yaml                    # API 规格
│   └── demo-script.md                   # 演示脚本
│
└── README.md
```

---

## 十二、质量保障与验收标准

### 12.1 必须验收项检查清单

| # | 验收项 | 验收标准 | 对应场景 |
|---|--------|---------|---------|
| 1 | 多端协同框架 | 移动端和桌面端数据实时双向同步，延迟 < 1s | E |
| 2 | IM 入口（文本） | 在 IM 中输入文本指令可触发 Agent 任务 | A |
| 3 | IM 入口（语音） | 语音指令可被正确转换并触发任务 | A |
| 4 | 意图理解 | Agent 能正确理解并拆解至少 5 种指令类型 | B |
| 5 | 任务规划 | 显示可执行的任务计划，用户可确认/修改 | B |
| 6 | 文档生成 | Agent 能自动生成结构化文档，包含大纲+内容 | C |
| 7 | 文档编辑 | 用户可在 IM 中通过自然语言修改文档内容 | C |
| 8 | PPT/画布生成 | Agent 能基于文档或指令自动生成演示稿 | D |
| 9 | PPT/画布编辑 | 支持通过指令或直接操作修改演示稿 | D |
| 10 | 三套件串联 | IM → Doc → Slides 能在一次任务中串联完成 | A+B+C+D |
| 11 | 多场景组合 | 至少展示一次多场景组合编排执行 | - |
| 12 | 进度查询 | 用户可在 IM 中查询当前任务进度 | A+B |
| 13 | 交付输出 | 完成后可分享链接和导出文件 | F |

### 12.2 加分项检查清单

| # | 加分项 | 验收标准 |
|---|--------|---------|
| 1 | 离线支持 | 断网后可编辑，恢复后无冲突合并 |
| 2 | Agent 主动澄清 | 信息不足时主动追问 |
| 3 | Agent 推荐下一步 | 完成一步后推荐后续动作 |
| 4 | 富媒体操作 | 支持插入图片、表格、图表 |
| 5 | 讨论自动总结 | Agent 能自动总结群聊讨论 |

### 12.3 性能基线

| 指标 | 目标 |
|------|------|
| IM 消息收发延迟 | < 200ms |
| 多端同步延迟 | < 1s |
| Agent 意图识别响应 | < 2s |
| 文档生成（1000字） | < 30s |
| PPT 生成（10页） | < 60s |
| App 冷启动 | < 3s |
| 内存占用（移动端） | < 200MB |

### 12.4 测试策略

```
单元测试
├ Agent 意图分类准确率 > 90%
├ CRDT 合并正确性测试
├ 数据模型序列化/反序列化
└ Tool 执行逻辑

集成测试
├ IM → Agent → 文档 全链路
├ IM → Agent → PPT 全链路
├ IM → Agent → 文档 → PPT 全链路
├ 多端同步一致性
└ WebSocket 断线重连

端到端测试
├ 演示场景 1 完整走通
├ 演示场景 2 完整走通
└ 演示场景 3 完整走通
```

---

## 附录 A：关键技术难点与解决方案

| 难点 | 方案 |
|------|------|
| LLM 响应延迟导致用户等待 | 流式输出 + 进度条 + 乐观更新 |
| 多端数据冲突 | CRDT 无冲突合并 + 服务端仲裁 |
| Agent 任务失败 | 自动重试 + 降级策略 + 错误通知 |
| 长文档生成内存压力 | 分块生成 + 流式写入 + 分页加载 |
| PPT 布局复杂度 | 预设模板 + 约束布局算法 |
| 语音识别准确率 | 云端 ASR + 上下文校正 |
| 离线/在线切换 | Operation Log + CRDT 合并 + 版本向量 |

## 附录 B：LLM Prompt 模板索引

| 用途 | 调用位置 | 模型级别 |
|------|---------|---------|
| 意图分类 | Intent Parser | Haiku (快) |
| 任务规划 | Planner | Sonnet (标准) |
| 文档大纲生成 | Doc Engine | Sonnet |
| 文档内容填充 | Doc Engine | Sonnet |
| 文档修改指令解析 | Doc Engine | Haiku |
| PPT 结构规划 | Slides Engine | Sonnet |
| PPT 内容提炼 | Slides Engine | Sonnet |
| 对话总结 | Summarizer | Sonnet |
| 主动澄清生成 | Orchestrator | Sonnet |
| 复杂多步骤推理 | Planner (复杂) | Opus (重) |

---

*文档版本: v1.0*
*最后更新: 2026-04-24*
