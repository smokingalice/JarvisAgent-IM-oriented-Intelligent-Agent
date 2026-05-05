import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_DEFAULT_OPUS_MODEL = os.getenv("ANTHROPIC_DEFAULT_OPUS_MODEL", "claude-3-opus-latest")
ANTHROPIC_DEFAULT_SONNET_MODEL = os.getenv("ANTHROPIC_DEFAULT_SONNET_MODEL", "claude-sonnet-4-20250514")
ANTHROPIC_DEFAULT_HAIKU_MODEL = os.getenv("ANTHROPIC_DEFAULT_HAIKU_MODEL", "claude-3-haiku-20240307")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/jarvis_agent.db")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

