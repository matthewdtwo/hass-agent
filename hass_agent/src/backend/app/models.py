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


# ------------------------------------------------------------------
# Session models
# ------------------------------------------------------------------


class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str
    token_usage: dict[str, int] | None = None


class DisplayMessage(BaseModel):
    id: int
    role: str
    content: str
    tool_calls: list[dict] | None = None
    created_at: str


class SessionDetail(SessionInfo):
    messages: list[DisplayMessage]


class CreateSessionRequest(BaseModel):
    title: str | None = None


class UpdateSessionRequest(BaseModel):
    title: str
