from pydantic import BaseModel


class ChatMessage(BaseModel):
    message: str
    model: str


class WSEvent(BaseModel):
    type: str
    content: str = ""
    name: str = ""
    args: dict | None = None


class ModelInfo(BaseModel):
    id: str
    provider: str
    name: str
