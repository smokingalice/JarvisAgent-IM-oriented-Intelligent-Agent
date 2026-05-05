import traceback
from config import ANTHROPIC_BASE_URL, ANTHROPIC_DEFAULT_SONNET_MODEL


def extract_response_text(response) -> str:
    parts = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    if parts:
        return "\n".join(parts).strip()
    raise ValueError(f"LLM 响应中没有可读取的 text 内容：{getattr(response, 'content', None)!r}")


def log_llm_error(stage: str, error: Exception):
    print("\n========== LLM 调用失败，已切换到降级模式 ==========")
    print(f"阶段: {stage}")
    print(f"Base URL: {ANTHROPIC_BASE_URL}")
    print(f"Model: {ANTHROPIC_DEFAULT_SONNET_MODEL}")
    print(f"错误类型: {type(error).__name__}")
    print(f"错误信息: {repr(error)}")
    traceback.print_exception(type(error), error, error.__traceback__)
    print("=================================================\n")
