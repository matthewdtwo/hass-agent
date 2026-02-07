from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.db import (
    create_session,
    delete_session,
    get_display_messages,
    get_session,
    list_sessions,
    update_session_title,
)
from app.models import (
    CreateSessionRequest,
    SessionDetail,
    SessionInfo,
    UpdateSessionRequest,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.get("", response_model=list[SessionInfo])
async def list_sessions_endpoint(request: Request) -> list[dict]:
    return await list_sessions(request.app.state.db)


@router.post("", response_model=SessionInfo, status_code=201)
async def create_session_endpoint(
    request: Request, body: CreateSessionRequest | None = None
) -> dict:
    title = (body.title if body and body.title else "New chat")
    return await create_session(request.app.state.db, title)


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session_endpoint(session_id: str, request: Request) -> dict:
    session = await get_session(request.app.state.db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = await get_display_messages(request.app.state.db, session_id)
    return {**session, "messages": messages}


@router.patch("/{session_id}", response_model=SessionInfo)
async def update_session_endpoint(
    session_id: str, body: UpdateSessionRequest, request: Request
) -> dict:
    session = await get_session(request.app.state.db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await update_session_title(request.app.state.db, session_id, body.title)
    session["title"] = body.title
    return session


@router.delete("/{session_id}", status_code=204)
async def delete_session_endpoint(session_id: str, request: Request) -> None:
    await delete_session(request.app.state.db, session_id)
