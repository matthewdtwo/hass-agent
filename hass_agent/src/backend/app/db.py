from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from pydantic_ai.messages import ModelMessagesTypeAdapter

_SCHEMA = """\
CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT UNIQUE NOT NULL,
    name       TEXT NOT NULL,
    picture    TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id             TEXT PRIMARY KEY,
    user_id        TEXT REFERENCES users(id),
    title          TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL,
    model_history  TEXT NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_sessions_user
    ON sessions(user_id, updated_at);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    tool_calls  TEXT,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_session
    ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS access_tokens (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    name       TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    last_used  TEXT
);

CREATE INDEX IF NOT EXISTS idx_tokens_user ON access_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_tokens_hash ON access_tokens(token_hash);
"""


async def init_db(path: str) -> aiosqlite.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = await aiosqlite.connect(path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    await db.executescript(_SCHEMA)
    # Migrate existing DBs: add user_id column if missing
    try:
        await db.execute("ALTER TABLE sessions ADD COLUMN user_id TEXT REFERENCES users(id)")
        await db.commit()
    except Exception:
        pass  # Column already exists
    await db.commit()
    return db


async def close_db(db: aiosqlite.Connection) -> None:
    await db.close()


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------


async def get_or_create_user(
    db: aiosqlite.Connection,
    email: str,
    name: str,
    picture: str | None = None,
) -> dict[str, Any]:
    cursor = await db.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = await cursor.fetchone()
    if row:
        # Update name/picture on each login
        await db.execute(
            "UPDATE users SET name = ?, picture = ? WHERE id = ?",
            (name, picture, row["id"]),
        )
        await db.commit()
        return {"id": row["id"], "email": email, "name": name, "picture": picture}
    uid = uuid.uuid4().hex
    now = _now()
    await db.execute(
        "INSERT INTO users (id, email, name, picture, created_at) VALUES (?, ?, ?, ?, ?)",
        (uid, email, name, picture, now),
    )
    await db.commit()
    return {"id": uid, "email": email, "name": name, "picture": picture}


# ------------------------------------------------------------------
# Sessions
# ------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(
    db: aiosqlite.Connection, title: str, user_id: str | None = None
) -> dict[str, Any]:
    sid = uuid.uuid4().hex
    now = _now()
    await db.execute(
        "INSERT INTO sessions (id, user_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (sid, user_id, title, now, now),
    )
    await db.commit()
    return {"id": sid, "title": title, "created_at": now, "updated_at": now}


async def list_sessions(
    db: aiosqlite.Connection, user_id: str | None = None
) -> list[dict[str, Any]]:
    if user_id:
        cursor = await db.execute(
            "SELECT id, title, created_at, updated_at FROM sessions "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        )
    else:
        cursor = await db.execute(
            "SELECT id, title, created_at, updated_at FROM sessions ORDER BY updated_at DESC"
        )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def get_session(db: aiosqlite.Connection, session_id: str) -> dict[str, Any] | None:
    cursor = await db.execute(
        "SELECT id, user_id, title, created_at, updated_at FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def update_session_title(
    db: aiosqlite.Connection, session_id: str, title: str
) -> None:
    await db.execute(
        "UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
        (title, _now(), session_id),
    )
    await db.commit()


async def delete_session(db: aiosqlite.Connection, session_id: str) -> None:
    await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    await db.commit()


async def touch_session(db: aiosqlite.Connection, session_id: str) -> None:
    await db.execute(
        "UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id)
    )
    await db.commit()


# ------------------------------------------------------------------
# PydanticAI message history (opaque blob)
# ------------------------------------------------------------------


async def get_message_history(db: aiosqlite.Connection, session_id: str) -> list:
    cursor = await db.execute(
        "SELECT model_history FROM sessions WHERE id = ?", (session_id,)
    )
    row = await cursor.fetchone()
    if not row or not row["model_history"]:
        return []
    return ModelMessagesTypeAdapter.validate_json(row["model_history"])


async def save_message_history(
    db: aiosqlite.Connection, session_id: str, messages: list
) -> None:
    blob = ModelMessagesTypeAdapter.dump_json(messages).decode()
    await db.execute(
        "UPDATE sessions SET model_history = ?, updated_at = ? WHERE id = ?",
        (blob, _now(), session_id),
    )
    await db.commit()


# ------------------------------------------------------------------
# Display messages
# ------------------------------------------------------------------


async def get_display_messages(
    db: aiosqlite.Connection, session_id: str
) -> list[dict[str, Any]]:
    cursor = await db.execute(
        "SELECT id, role, content, tool_calls, created_at "
        "FROM messages WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    rows = await cursor.fetchall()
    results = []
    for r in rows:
        d = dict(r)
        if d["tool_calls"]:
            d["tool_calls"] = json.loads(d["tool_calls"])
        results.append(d)
    return results


async def save_display_message(
    db: aiosqlite.Connection,
    session_id: str,
    role: str,
    content: str,
    tool_calls: list[dict] | None = None,
) -> None:
    tc_json = json.dumps(tool_calls) if tool_calls else None
    await db.execute(
        "INSERT INTO messages (session_id, role, content, tool_calls, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (session_id, role, content, tc_json, _now()),
    )
    await db.commit()


# ------------------------------------------------------------------
# Access tokens
# ------------------------------------------------------------------


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


async def create_access_token(
    db: aiosqlite.Connection, user_id: str, name: str
) -> tuple[dict[str, Any], str]:
    """Create a new access token. Returns (token_info, raw_token)."""
    token_id = uuid.uuid4().hex
    raw = "haa_" + secrets.token_hex(32)
    now = _now()
    await db.execute(
        "INSERT INTO access_tokens (id, user_id, name, token_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (token_id, user_id, name, _hash_token(raw), now),
    )
    await db.commit()
    return {"id": token_id, "name": name, "created_at": now, "last_used": None}, raw


async def list_access_tokens(
    db: aiosqlite.Connection, user_id: str
) -> list[dict[str, Any]]:
    cursor = await db.execute(
        "SELECT id, name, created_at, last_used FROM access_tokens "
        "WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,),
    )
    return [dict(r) for r in await cursor.fetchall()]


async def delete_access_token(
    db: aiosqlite.Connection, token_id: str, user_id: str
) -> bool:
    cursor = await db.execute(
        "DELETE FROM access_tokens WHERE id = ? AND user_id = ?",
        (token_id, user_id),
    )
    await db.commit()
    return cursor.rowcount > 0


async def get_user_by_token(
    db: aiosqlite.Connection, raw_token: str
) -> dict[str, Any] | None:
    """Look up a user by raw bearer token. Updates last_used on hit."""
    h = _hash_token(raw_token)
    cursor = await db.execute(
        "SELECT u.id, u.email, u.name, u.picture, t.id AS token_id "
        "FROM access_tokens t JOIN users u ON t.user_id = u.id "
        "WHERE t.token_hash = ?",
        (h,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    await db.execute(
        "UPDATE access_tokens SET last_used = ? WHERE id = ?",
        (_now(), row["token_id"]),
    )
    await db.commit()
    return {"id": row["id"], "email": row["email"], "name": row["name"], "picture": row["picture"]}
