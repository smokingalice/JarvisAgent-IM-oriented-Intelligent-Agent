import uuid
import json
from datetime import datetime
from anthropic import AsyncAnthropic
from config import ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL, ANTHROPIC_MODEL
from database import get_db

RICH_CONTENT_PROMPT = """You are a document editor assistant. Based on the user's instruction, generate the appropriate rich content in Markdown format.

For tables: Generate a well-structured Markdown table with headers and rows.
For images: Generate an image placeholder in the format ![description](placeholder_url) with a descriptive alt text.
For layout changes: Reorganize the content with appropriate headings, columns (using HTML div), and spacing.

Output ONLY the Markdown content to be inserted. No explanations."""


async def insert_rich_content_tool(params: dict, chat_id: str = "") -> dict:
    action = params.get("action", "insert_table")
    instruction = params.get("instruction", "")
    document_id = params.get("document_id")

    content = await _generate_rich_content(action, instruction)

    if document_id:
        db = await get_db()
        cursor = await db.execute("SELECT content FROM documents WHERE id = ?", (document_id,))
        row = await cursor.fetchone()
        if row:
            existing = dict(row).get("content", "")
            new_content = existing + "\n\n" + content
            await db.execute(
                "UPDATE documents SET content = ?, updated_at = ? WHERE id = ?",
                (new_content, datetime.utcnow().isoformat(), document_id)
            )
            await db.commit()
        await db.close()
        return {
            "document_id": document_id,
            "action": action,
            "message": f"已在文档中插入{_action_label(action)}",
            "inserted_content": content,
            "artifact": {
                "type": "document",
                "id": document_id,
                "title": "已更新文档",
            }
        }

    doc_id = f"doc_{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    title = f"富媒体内容 - {_action_label(action)}"

    db = await get_db()
    await db.execute("""
        INSERT INTO documents (id, title, content, status, created_by, created_at, updated_at)
        VALUES (?, ?, ?, 'draft', 'agent', ?, ?)
    """, (doc_id, title, content, now, now))
    await db.commit()
    await db.close()

    return {
        "document_id": doc_id,
        "action": action,
        "message": f"已创建包含{_action_label(action)}的文档",
        "artifact": {
            "type": "document",
            "id": doc_id,
            "title": title,
        }
    }


async def _generate_rich_content(action: str, instruction: str) -> str:
    if not ANTHROPIC_API_KEY:
        return _fallback_rich_content(action, instruction)

    try:
        client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL)
        prompt = f"Action: {action}\nInstruction: {instruction}\n\nGenerate the appropriate Markdown content."
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=RICH_CONTENT_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception:
        return _fallback_rich_content(action, instruction)


def _fallback_rich_content(action: str, instruction: str) -> str:
    if action == "insert_table":
        return _generate_table(instruction)
    elif action == "insert_image":
        return _generate_image_placeholder(instruction)
    elif action == "adjust_layout":
        return _generate_layout(instruction)
    return ""


def _generate_table(instruction: str) -> str:
    if "对比" in instruction or "比较" in instruction:
        return """## 对比分析

| 维度 | 方案 A | 方案 B | 说明 |
|------|--------|--------|------|
| 性能 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 方案A在并发场景更优 |
| 成本 | ⭐⭐ | ⭐⭐⭐⭐ | 方案B成本更低 |
| 易用性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 方案B学习曲线更低 |
| 扩展性 | ⭐⭐⭐⭐ | ⭐⭐⭐ | 方案A架构更灵活 |
| 维护性 | ⭐⭐⭐ | ⭐⭐⭐⭐ | 方案B代码更简洁 |
"""
    if "时间" in instruction or "计划" in instruction or "进度" in instruction:
        return """## 项目进度表

| 阶段 | 时间范围 | 负责人 | 状态 | 关键交付物 |
|------|----------|--------|------|------------|
| 需求分析 | 第1-2周 | 产品组 | ✅ 完成 | 需求文档 |
| 技术设计 | 第2-3周 | 技术组 | ✅ 完成 | 设计文档 |
| 开发实现 | 第3-6周 | 开发组 | 🔄 进行中 | 代码实现 |
| 测试验证 | 第6-7周 | 测试组 | ⏳ 待开始 | 测试报告 |
| 上线部署 | 第8周 | 运维组 | ⏳ 待开始 | 上线检查单 |
"""
    return """## 数据概览

| 项目 | 数值 | 变化 | 备注 |
|------|------|------|------|
| 指标一 | 1,234 | ↑ 12% | 环比上月 |
| 指标二 | 5,678 | ↑ 8% | 持续增长 |
| 指标三 | 890 | ↓ 3% | 需关注 |
| 指标四 | 2,345 | → 0% | 保持稳定 |
"""


def _generate_image_placeholder(instruction: str) -> str:
    desc = "示意图"
    if "架构" in instruction:
        desc = "系统架构图"
    elif "流程" in instruction:
        desc = "业务流程图"
    elif "界面" in instruction or "UI" in instruction:
        desc = "界面原型图"
    elif "数据" in instruction or "图表" in instruction:
        desc = "数据可视化图表"

    return f"""## {desc}

```
┌─────────────────────────────────────────────────┐
│                                                 │
│              [ {desc} ]                         │
│                                                 │
│   ┌─────────┐    ┌─────────┐    ┌─────────┐   │
│   │  模块A  │───▶│  模块B  │───▶│  模块C  │   │
│   └─────────┘    └─────────┘    └─────────┘   │
│        │                              │         │
│        ▼                              ▼         │
│   ┌─────────┐                   ┌─────────┐   │
│   │  模块D  │                   │  模块E  │   │
│   └─────────┘                   └─────────┘   │
│                                                 │
└─────────────────────────────────────────────────┘
```

*图：{desc} — {instruction}*
"""


def _generate_layout(instruction: str) -> str:
    return """## 内容布局

---

### 📋 左栏：核心要点

- 要点一：基础框架搭建
- 要点二：核心功能实现
- 要点三：测试与优化

---

### 📊 右栏：数据指标

| 指标 | 目标值 | 当前值 |
|------|--------|--------|
| 完成率 | 100% | 75% |
| 质量分 | 90+ | 88 |
| 响应时间 | <200ms | 150ms |

---

### 📝 底部：补充说明

> 以上内容根据当前项目进度整理，将持续更新。关键里程碑和风险点已标注。
"""


def _action_label(action: str) -> str:
    labels = {
        "insert_table": "表格",
        "insert_image": "图片/图表",
        "adjust_layout": "布局调整",
    }
    return labels.get(action, "富媒体内容")
