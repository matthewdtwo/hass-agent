from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.auth import require_user
from app.db import create_access_token, delete_access_token, list_access_tokens

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


class CreateTokenRequest(BaseModel):
    name: str


class TokenInfo(BaseModel):
    id: str
    name: str
    created_at: str
    last_used: str | None


class CreateTokenResponse(TokenInfo):
    token: str


def _user_id(request: Request) -> str:
    return require_user(request)["id"]


@router.get("", response_model=list[TokenInfo])
async def list_tokens_endpoint(request: Request) -> list[dict]:
    return await list_access_tokens(request.app.state.db, _user_id(request))


@router.post("", response_model=CreateTokenResponse, status_code=201)
async def create_token_endpoint(request: Request, body: CreateTokenRequest) -> dict:
    info, raw = await create_access_token(
        request.app.state.db, _user_id(request), body.name
    )
    return {**info, "token": raw}


@router.delete("/{token_id}", status_code=204)
async def delete_token_endpoint(token_id: str, request: Request) -> None:
    deleted = await delete_access_token(
        request.app.state.db, token_id, _user_id(request)
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Token not found")
