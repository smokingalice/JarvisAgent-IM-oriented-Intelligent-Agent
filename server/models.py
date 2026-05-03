from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class User(BaseModel):
    id: str
    name: str
    avatar: str = ""
    status: str = "online"


class Message(BaseModel):
    id: str
    chat_id: str
    sender_id: str
    content: str
    msg_type: str = "text"
    reply_to_id: Optional[str] = None
    card_data: Optional[dict] = None
    created_at: str = ""
    recalled_at: Optional[str] = None


class SendMessageRequest(BaseModel):
    content: str
    msg_type: str = "text"
    reply_to_id: Optional[str] = None


class Chat(BaseModel):
    id: str
    type: str = "private"
    name: str = ""
    last_message: Optional[Message] = None
    unread_count: int = 0


class Document(BaseModel):
    id: str
    title: str
    content: str = ""
    outline: List[str] = []
    status: str = "draft"
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class SlideData(BaseModel):
    layout: str
    data: dict


class Presentation(BaseModel):
    id: str
    title: str
    slides: List[SlideData] = []
    template: str = "default"
    source_doc_id: Optional[str] = None
    task_id: Optional[str] = None
    created_by: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


class TaskPlan(BaseModel):
    id: str
    name: str
    tool: str
    params: dict = {}
    depends_on: List[str] = []
    status: str = "pending"


class AgentTask(BaseModel):
    id: str
    chat_id: str
    user_id: str
    intent: str = ""
    plan: List[TaskPlan] = []
    status: str = "pending"
    progress: int = 0
    result: Optional[dict] = None
    created_at: str = ""
    updated_at: str = ""


class AgentRequest(BaseModel):
    message: str
    chat_id: str
    user_id: str = "alice"
