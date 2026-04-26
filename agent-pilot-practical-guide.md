# Agent-Pilot 简化实践指南

> 核心原则：Agent 是灵魂，IM/Doc/Slides 是骨架。骨架够用就行，灵魂要做到位。

---

## 一、总体策略：什么自己做，什么用现成的

| 模块 | 策略 | 理由 |
|------|------|------|
| IM 即时通讯 | **自己做简化版** | 只需消息收发 + @Agent 触发，30% 功能即可 |
| 文档编辑器 | **集成 flutter_quill** | 开源富文本编辑器，拿来即用，Agent 通过 API 写入 |
| PPT/画布 | **自己做简化版** | 用 Flutter Widget 渲染幻灯片，模板化布局 |
| Agent 引擎 | **自己做，核心竞争力** | Claude API + Tool Use，这是比赛重点 |
| 实时同步 | **WebSocket + 简化版 CRDT** | 不需要完整协同编辑，做到多端状态同步即可 |
| 后端 | **Node.js/FastAPI 轻量服务** | 转发 LLM 请求 + 管理状态 + WebSocket 广播 |

### 每个模块需要做到什么程度

```
IM（30% 完成度即可）
├ ✅ 消息列表展示
├ ✅ 发送文本消息
├ ✅ 发送语音消息（录音 → 转文本）
├ ✅ @Agent 触发任务
├ ✅ Agent 回复卡片（进度条、确认按钮、链接）
├ ❌ 不需要：已读回执、消息撤回、表情包、文件传输
└ ❌ 不需要：群管理、好友系统、通讯录

文档（40% 完成度即可）
├ ✅ 创建/打开文档
├ ✅ 富文本编辑（标题、正文、列表、表格）
├ ✅ Agent 可写入/修改内容（通过 API 操作 Quill Delta）
├ ✅ 多端打开同一文档能看到相同内容
├ ❌ 不需要：完整协同光标、评论批注、历史版本对比
└ ❌ 不需要：模板库、导入 Word

PPT/画布（40% 完成度即可）
├ ✅ 幻灯片列表 + 单页渲染
├ ✅ 5-6 种预设布局模板
├ ✅ Agent 可生成/修改幻灯片内容
├ ✅ 全屏演示模式（翻页播放）
├ ✅ 导出为 PDF/图片
├ ❌ 不需要：自由拖拽、动画效果、主题市场
└ ❌ 不需要：复杂图表编辑、视频嵌入
```

---

## 二、简化架构

```
┌──────────────────────────────────────────────┐
│            Flutter App（移动 + 桌面）          │
│                                              │
│  ┌────────┐  ┌────────┐  ┌────────────────┐ │
│  │ IM 页面 │  │文档页面 │  │ PPT/画布 页面  │ │
│  └───┬────┘  └───┬────┘  └───────┬────────┘ │
│      └───────────┼───────────────┘           │
│                  ▼                            │
│         ┌──────────────┐                     │
│         │ AgentService │ ◄── 统一的 Agent 交互层
│         └──────┬───────┘                     │
└────────────────┼─────────────────────────────┘
                 │ HTTP + WebSocket
                 ▼
┌────────────────────────────────────────────────┐
│              轻量后端（一个服务搞定）             │
│                                                │
│  ┌──────────┐  ┌───────────┐  ┌────────────┐  │
│  │ REST API │  │ WebSocket │  │ Agent 引擎  │  │
│  │ 消息/文档 │  │ 实时推送  │  │ Claude API │  │
│  │ /PPT CRUD│  │ 状态同步  │  │ + Tool Use │  │
│  └──────────┘  └───────────┘  └────────────┘  │
│                                                │
│  ┌──────────────────┐  ┌───────────────────┐   │
│  │ SQLite/PostgreSQL │  │ 文件存储（本地）    │   │
│  └──────────────────┘  └───────────────────┘   │
└────────────────────────────────────────────────┘
```

**关键简化：后端只有一个服务，不做微服务拆分。SQLite 开发阶段够用。**

---

## 三、实践步骤（按做的顺序）

### Step 1：项目骨架 + Agent 最小闭环（Day 1-3）

**目标：在 IM 里输入一句话，Agent 能回复。**

这是最重要的一步，验证核心链路。

```
做什么：
1. flutter create agent_pilot
2. 添加依赖：riverpod, go_router, dio, web_socket_channel
3. 搭后端：一个 HTTP 接口 /api/agent/chat
4. 接 Claude API，能收到回复
5. Flutter 端：一个简单聊天界面，发消息 → 收回复

验证标准：
- 在 App 里输入 "帮我写一份产品方案"
- Agent 回复 "好的，我将为你生成产品方案文档..."
```

具体代码结构：

```
lib/
├── main.dart
├── app/
│   └── router.dart
├── features/
│   └── im/
│       ├── chat_page.dart        # 聊天界面
│       ├── message_model.dart    # 消息模型
│       └── chat_provider.dart    # 状态管理
└── core/
    ├── api_client.dart           # HTTP 客户端
    └── agent_service.dart        # Agent 交互封装
```

后端（Node.js 示例）：

```
server/
├── index.ts                      # 入口
├── routes/
│   └── agent.ts                  # /api/agent/chat
└── agent/
    └── claude_client.ts          # Claude API 封装
```

### Step 2：Agent Tool Use + 任务规划（Day 4-6）

**目标：Agent 能理解指令、拆解任务、调用工具。**

```
做什么：
1. 定义 Tool：create_document, create_slides, summarize
2. 在 Claude API 调用中传入 tools 定义
3. 实现 Planner：用户指令 → LLM 返回执行计划 → 展示给用户确认
4. 实现 Executor：按计划逐步调用 Tool
5. 进度通过 WebSocket 推送到 App

验证标准：
- 输入 "帮我写个方案然后做成PPT"
- Agent 返回计划：Step1 生成文档 → Step2 生成PPT
- 用户确认后开始执行
- IM 中能看到进度更新
```

这是整个项目最核心的环节。Agent 引擎代码结构：

```
server/agent/
├── orchestrator.ts      # 编排入口
├── planner.ts           # 调 Claude 生成计划
├── executor.ts          # 按计划执行 Tool
├── tools/
│   ├── registry.ts      # Tool 注册表
│   ├── create_doc.ts    # 生成文档（调 LLM 写内容，存数据库）
│   ├── create_slides.ts # 生成PPT（调 LLM 提炼要点，存数据库）
│   └── summarize.ts     # 总结对话
└── prompts/
    ├── planner.txt      # Planner 的 system prompt
    └── doc_writer.txt   # 文档生成的 prompt
```

Planner 的 Claude 调用示意：

```typescript
const response = await claude.messages.create({
  model: "claude-sonnet-4-6-20250514",
  system: "你是任务规划器。根据用户指令拆解为子任务...",
  messages: [{ role: "user", content: userMessage }],
  tools: [
    {
      name: "create_document",
      description: "创建文档",
      input_schema: { /* ... */ }
    },
    {
      name: "create_slides",
      description: "创建演示稿",
      input_schema: { /* ... */ }
    }
  ]
});
// Claude 会返回 tool_use，告诉你该调哪些工具、什么参数
```

### Step 3：文档模块（Day 7-10）

**目标：Agent 能生成文档，用户能查看和编辑。**

```
做什么：
1. 集成 flutter_quill 到 App
2. 后端 create_doc Tool：调 LLM 生成内容 → 存为 Quill Delta JSON
3. 前端文档页面：加载 Delta → 渲染富文本
4. Agent 修改文档：用户在 IM 说 "加个表格" → Agent 修改 Delta → 推送更新
5. 简单多端同步：文档修改 → 存后端 → WebSocket 通知其他端刷新

关键：文档内容的格式
- 用 Quill Delta（JSON 格式描述富文本）
- Agent 生成 Markdown → 后端转为 Delta → 前端渲染
- 这样 Agent 只需要输出 Markdown，简化 prompt 复杂度
```

文档生成流程：

```
Agent 生成 Markdown
    ↓
后端转换为 Quill Delta JSON
    ↓
存入数据库 (documents 表)
    ↓
WebSocket 通知前端
    ↓
前端 flutter_quill 渲染
    ↓
用户编辑 → Delta 变更 → 存回数据库 → 同步其他端
```

### Step 4：PPT/画布模块（Day 11-15）

**目标：Agent 能从文档生成 PPT，用户能浏览和演示。**

```
做什么：
1. 定义幻灯片数据模型（JSON：页面列表 → 每页有布局+元素）
2. 实现 5 种布局模板 Widget：
   - TitleSlide：标题+副标题
   - ContentSlide：标题+要点列表
   - TwoColumnSlide：双栏对比
   - ImageTextSlide：图+文
   - SummarySlide：总结页
3. create_slides Tool：文档内容 → LLM 提炼 → 分配到模板 → 生成 JSON
4. 前端渲染：读 JSON → 用模板 Widget 渲染每页
5. 演示模式：全屏 + 左右翻页
6. IM 指令修改："第3页标题改成xxx" → Agent 修改 JSON → 推送更新
```

PPT 数据模型（保持简单）：

```json
{
  "id": "ppt_001",
  "title": "产品介绍",
  "slides": [
    {
      "layout": "title",
      "data": {
        "title": "XX 产品介绍",
        "subtitle": "AI 驱动协同办公"
      }
    },
    {
      "layout": "content",
      "data": {
        "title": "核心功能",
        "points": ["功能一：...", "功能二：...", "功能三：..."]
      }
    },
    {
      "layout": "two_column",
      "data": {
        "title": "优势对比",
        "left_title": "传统方式",
        "left_points": ["手动操作", "耗时长"],
        "right_title": "Agent-Pilot",
        "right_points": ["自动生成", "分钟级完成"]
      }
    }
  ]
}
```

PPT 渲染 Widget（简化思路）：

```dart
class SlideRenderer extends StatelessWidget {
  final SlideData slide;

  Widget build(BuildContext context) {
    return switch (slide.layout) {
      'title'      => TitleSlideWidget(slide.data),
      'content'    => ContentSlideWidget(slide.data),
      'two_column' => TwoColumnSlideWidget(slide.data),
      _            => ContentSlideWidget(slide.data),
    };
  }
}
```

### Step 5：多端同步（Day 16-18）

**目标：移动端和桌面端数据实时同步。**

```
做什么：
1. WebSocket 长连接：App 启动时连接后端
2. 资源变更广播：任何资源(消息/文档/PPT)被修改 → 后端广播给所有已连接的端
3. 前端收到广播 → 刷新对应页面数据
4. 简单冲突策略：Last-Writer-Wins（最后写入者胜）

不需要做：
- 不需要完整 CRDT
- 不需要实时光标同步
- 不需要离线队列（先跳过，最后有时间再加）

同步的粒度：
- IM 消息：新消息 → 广播 → 其他端追加
- 文档：整份文档内容替换（简化版）
- PPT：整份 PPT JSON 替换（简化版）
- 任务状态：Agent 进度更新 → 广播 → 所有端刷新
```

WebSocket 消息格式（保持简单）：

```json
{
  "type": "resource_updated",
  "resource": "document | presentation | message | task",
  "resourceId": "doc_001",
  "action": "created | updated | deleted",
  "data": { /* 完整的最新数据 */ },
  "timestamp": "2026-04-24T10:45:00Z"
}
```

### Step 6：语音输入（Day 19-20）

**目标：长按录音 → 语音转文本 → 触发 Agent。**

```
做什么：
1. 集成 speech_to_text 或 record 插件
2. 移动端：长按录音按钮 → 录音 → 发送音频到后端
3. 后端：调语音识别 API（Whisper / 讯飞）→ 转文本
4. 转出的文本走正常 Agent 流程

简化方案（更快）：
- 直接用 speech_to_text 插件在端上做本地识别
- 识别完直接当文本消息发出去
- 省掉音频传输和后端 ASR 环节
```

### Step 7：交付与分享（Day 21-22）

**目标：任务完成后，生成链接/导出文件。**

```
做什么：
1. 文档导出 PDF：flutter_quill 内容 → PDF（用 pdf 包）
2. PPT 导出 PDF：逐页截图 Widget → 拼成 PDF
3. 分享链接：后端生成唯一 URL → 分享到 IM
4. 完成卡片：Agent 在 IM 中发送带链接的完成消息
```

### Step 8：打磨与演示准备（Day 23-28）

```
做什么：
1. UI 美化：统一主题色、字体、间距
2. 桌面端适配：侧边栏布局、多面板
3. 动画：消息出现、进度条、页面切换
4. Agent 主动能力：信息不足时追问、完成后推荐下一步
5. 准备演示数据：预设一些聊天记录和场景
6. 排练演示脚本
7. 修 Bug
```

---

## 四、时间分配一览

```
Day 1-3   ████████░░░░░░░░░░░░░░░░░░░░  骨架 + Agent 基础对话
Day 4-6   ████████░░░░░░░░░░░░░░░░░░░░  Agent Tool Use + 任务规划 ★最核心
Day 7-10  ██████████████░░░░░░░░░░░░░░  文档模块（flutter_quill + Agent 写入）
Day 11-15 ██████████████████░░░░░░░░░░  PPT 模块（模板渲染 + Agent 生成）
Day 16-18 ██████░░░░░░░░░░░░░░░░░░░░░░  多端同步（WebSocket 广播）
Day 19-20 ████░░░░░░░░░░░░░░░░░░░░░░░░  语音输入
Day 21-22 ████░░░░░░░░░░░░░░░░░░░░░░░░  交付与分享
Day 23-28 ████████████░░░░░░░░░░░░░░░░  打磨 + 演示准备
```

**最高优先级：Step 1-2（Agent 核心引擎）。** 如果时间紧张，其他模块可以粗糙，但 Agent 的意图理解和任务编排必须做好——这是评委最看重的。

---

## 五、每个模块的"自己做"vs"接现成"决策细节

### IM：自己做（简化版）

**为什么不接飞书/钉钉：**
- 接第三方 API 需要审批、配 webhook、处理鉴权，流程复杂
- 演示时依赖外部服务，不稳定
- 自己做一个聊天界面只需 1-2 天
- 比赛评的是 Agent 能力，不是 IM 功能丰富度

**自己做什么程度：**

```dart
// 消息模型就这么简单
class Message {
  final String id;
  final String chatId;
  final String senderId;
  final String senderName;
  final String content;       // 文本内容
  final String type;          // text / agent_card / voice
  final Map<String, dynamic>? cardData;  // Agent 卡片数据
  final DateTime timestamp;
}
```

```
聊天界面功能清单（全部需要做）：
✅ 消息列表（ListView 倒序）
✅ 文本输入框 + 发送按钮
✅ 语音录音按钮
✅ Agent 回复气泡（带进度条、按钮的卡片）
✅ 简单的聊天列表页（2-3 个预设聊天）

不需要做的：
❌ 注册登录（预设用户，跳过登录）
❌ 好友/群组管理
❌ 消息搜索
❌ 文件/图片发送
❌ 已读未读
❌ 消息撤回
```

### 文档：集成 flutter_quill + 自己写 Agent 写入逻辑

**为什么用 flutter_quill：**
- 成熟的开源 Flutter 富文本编辑器
- 基于 Quill Delta（JSON 描述富文本，和 Agent 输出对接方便）
- 支持标题、列表、表格、代码块
- 开箱即用，不需要自己写编辑器

**自己做什么部分：**
- Agent 生成 Markdown → 转 Quill Delta（写个转换函数）
- 文档存取 API（后端 CRUD）
- 文档页面布局（桌面端分屏、移动端全屏）
- Agent 修改文档的逻辑（解析用户指令 → 定位段落 → 修改 Delta）

### PPT/画布：自己做（模板化方案）

**为什么不用现成库：**
- Flutter 没有成熟的 PPT 编辑库
- 自己做反而更可控，评委能看到设计能力
- 模板化方案工作量不大

**核心思路：每种布局就是一个 Widget，数据驱动渲染**

```dart
// 标题页模板
class TitleSlideWidget extends StatelessWidget {
  final String title;
  final String subtitle;

  Widget build(BuildContext context) {
    return Container(
      color: theme.primaryColor,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(title, style: TextStyle(fontSize: 42, fontWeight: FontWeight.bold, color: Colors.white)),
          SizedBox(height: 16),
          Text(subtitle, style: TextStyle(fontSize: 20, color: Colors.white70)),
        ],
      ),
    );
  }
}

// 内容页模板
class ContentSlideWidget extends StatelessWidget {
  final String title;
  final List<String> points;

  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(title, style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
        SizedBox(height: 24),
        ...points.map((p) => Padding(
          padding: EdgeInsets.symmetric(vertical: 8),
          child: Row(children: [
            Icon(Icons.circle, size: 8),
            SizedBox(width: 12),
            Expanded(child: Text(p, style: TextStyle(fontSize: 18))),
          ]),
        )),
      ],
    );
  }
}
```

**这就够了。** Agent 输出 JSON → 选模板 → 填数据 → 渲染。不需要 PowerPoint 级别的功能。

### 后端：自己做（一个轻服务）

推荐 **FastAPI（Python）** 或 **Fastify（Node.js）**，别用 Spring Boot 之类的重框架。

```
后端只做四件事：
1. 消息/文档/PPT 的 CRUD（REST API）
2. WebSocket 长连接（消息推送 + 状态同步）
3. 调 Claude API（Agent 引擎核心逻辑）
4. 文件存储（本地文件系统，不需要 S3）
```

### 实时同步：自己做（简化版）

```
不需要 CRDT。简化方案：

1. 每个资源有一个 version 字段
2. 修改时 version + 1，存入数据库
3. 修改后通过 WebSocket 广播 { type, resourceId, version, data }
4. 其他端收到广播，如果 version 比本地大，直接替换
5. 如果两端同时修改（极端情况），后提交的覆盖先提交的（LWW）

对比赛演示来说这足够了。
```

---

## 六、Agent 引擎详细实现指南

这是比赛的核心差异化。

### 6.1 整体流程

```
用户消息
    │
    ▼
┌─────────────────────────────────────────────┐
│ Step 1: 意图分类（一次 LLM 调用）             │
│                                             │
│ 输入：用户消息 + 对话上下文                    │
│ 输出：意图类型                                │
│   - task_create  (创建新任务)                 │
│   - task_modify  (修改进行中的任务)            │
│   - task_query   (查询进度)                   │
│   - general_chat (普通对话)                   │
└─────────────┬───────────────────────────────┘
              ▼
┌─────────────────────────────────────────────┐
│ Step 2: 任务规划（一次 LLM + Tool Use 调用）  │
│                                             │
│ 输入：用户意图 + 完整上下文                    │
│ 输出：Claude 返回 tool_use 列表               │
│ 解析为执行计划 → 发回 IM 让用户确认            │
└─────────────┬───────────────────────────────┘
              ▼ (用户确认)
┌─────────────────────────────────────────────┐
│ Step 3: 逐步执行（循环调用 Tool）              │
│                                             │
│ for each tool_call in plan:                 │
│   result = execute(tool_call)               │
│   push_progress_to_im(result)               │
│                                             │
│ 每步完成后推送进度到所有端                     │
└─────────────┬───────────────────────────────┘
              ▼
┌─────────────────────────────────────────────┐
│ Step 4: 完成交付                              │
│                                             │
│ 汇总所有产出物 → 生成完成消息 → 发送到 IM     │
└─────────────────────────────────────────────┘
```

### 6.2 Claude API 调用示例（核心代码）

```typescript
// planner.ts - 任务规划
async function planTask(userMessage: string, chatHistory: Message[]) {
  const response = await anthropic.messages.create({
    model: "claude-sonnet-4-6-20250514",
    max_tokens: 4096,
    system: `你是 Agent-Pilot 的任务规划器。
根据用户在 IM 中的消息，决定需要使用哪些工具来完成任务。
如果信息不足，使用 ask_clarification 工具向用户提问。
生成文档时先生成大纲，确认后再写内容。`,
    messages: chatHistory.map(m => ({
      role: m.senderId === 'agent' ? 'assistant' : 'user',
      content: m.content
    })),
    tools: [
      {
        name: "create_document",
        description: "创建一份新文档。需要提供标题和内容大纲。",
        input_schema: {
          type: "object",
          properties: {
            title: { type: "string", description: "文档标题" },
            outline: {
              type: "array",
              items: { type: "string" },
              description: "文档大纲，每项是一个章节标题"
            },
            tone: {
              type: "string",
              enum: ["formal", "casual", "technical"],
              description: "文档风格"
            }
          },
          required: ["title", "outline"]
        }
      },
      {
        name: "create_slides",
        description: "基于文档或描述创建演示稿。",
        input_schema: {
          type: "object",
          properties: {
            source_document_id: { type: "string", description: "来源文档 ID" },
            title: { type: "string" },
            num_slides: { type: "integer", description: "幻灯片页数" }
          },
          required: ["title"]
        }
      },
      {
        name: "ask_clarification",
        description: "向用户提出澄清问题。当信息不足以开始任务时使用。",
        input_schema: {
          type: "object",
          properties: {
            question: { type: "string", description: "要问用户的问题" }
          },
          required: ["question"]
        }
      }
    ]
  });

  // 解析 Claude 的响应
  // Claude 会返回 tool_use block，告诉我们该调用哪些工具
  return parseToolCalls(response);
}
```

```typescript
// executor.ts - 任务执行
async function executeTask(plan: ToolCall[], wsClients: WebSocket[]) {
  const results = [];

  for (const step of plan) {
    // 推送进度
    broadcast(wsClients, {
      type: "task_progress",
      step: step.name,
      status: "running",
      message: `正在${step.name === 'create_document' ? '生成文档' : '生成PPT'}...`
    });

    // 执行工具
    let result;
    switch (step.name) {
      case "create_document":
        result = await createDocument(step.input);
        break;
      case "create_slides":
        result = await createSlides(step.input);
        break;
      case "ask_clarification":
        // 发回 IM，等待用户回复
        result = await askAndWait(step.input.question, wsClients);
        break;
    }

    results.push(result);

    // 推送完成
    broadcast(wsClients, {
      type: "task_progress",
      step: step.name,
      status: "completed",
      result: result
    });
  }

  return results;
}
```

```typescript
// tools/create_doc.ts - 文档生成 Tool
async function createDocument(params: { title: string, outline: string[], tone: string }) {
  // 1. 先生成大纲确认（已在 plan 阶段完成）

  // 2. 逐章节调 LLM 生成内容
  let fullMarkdown = `# ${params.title}\n\n`;

  for (const section of params.outline) {
    const content = await anthropic.messages.create({
      model: "claude-sonnet-4-6-20250514",
      max_tokens: 2048,
      system: `你是专业的文档撰写者。按照${params.tone}的风格撰写以下章节内容。
输出纯 Markdown 格式。每个章节 200-400 字。`,
      messages: [{ role: "user", content: `请撰写"${section}"章节。文档标题是"${params.title}"。` }]
    });

    fullMarkdown += `## ${section}\n\n${content.content[0].text}\n\n`;
  }

  // 3. Markdown → Quill Delta
  const delta = markdownToQuillDelta(fullMarkdown);

  // 4. 存入数据库
  const doc = await db.documents.create({
    title: params.title,
    content: delta,
    status: 'draft'
  });

  return { documentId: doc.id, title: doc.title };
}
```

---

## 七、演示关键路径（必须跑通的链路）

按优先级排序，确保至少前 3 个能完整演示：

```
优先级 1（必须）：
IM 文本指令 → Agent 理解 → 生成文档 → 在文档页面查看
时长：~2 分钟

优先级 2（必须）：
文档自动生成 → 基于文档生成 PPT → 在 PPT 页面查看 → 全屏演示
时长：~2 分钟

优先级 3（必须）：
桌面端操作 → 移动端实时看到变化 → 移动端修改 → 桌面端同步
时长：~1 分钟

优先级 4（加分）：
语音指令触发任务
时长：~30 秒

优先级 5（加分）：
Agent 主动追问 "你想面向什么受众？"
时长：~30 秒
```

---

## 八、避坑指南

| 坑 | 怎么避 |
|----|--------|
| 在 IM 功能上花太多时间 | IM 只是入口，够用就停 |
| 追求完美的协同编辑 | LWW 替代 CRDT，演示够用就行 |
| PPT 自由拖拽 | 不做自由拖拽，模板化渲染 |
| 后端架构过度设计 | 一个服务，SQLite，不做微服务 |
| LLM 调用太慢 | 流式输出 + 进度条掩盖延迟 |
| 演示时外部 API 挂了 | 准备离线 mock 数据作为 fallback |
| 多端调试困难 | 先把桌面端做好，移动端只做适配 |
| 忘了 Agent 是主角 | 每个功能都问自己：Agent 在哪里？ |

---

*文档版本: v1.0*
*最后更新: 2026-04-24*
