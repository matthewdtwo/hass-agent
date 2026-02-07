from __future__ import annotations

import logging
import re
from collections import Counter
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from app.ha_client import HAClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a Home Assistant maintenance assistant. You help users understand, \
audit, and improve their smart home setup.

You have tools to query a Home Assistant instance. Use them to answer \
questions about entities, automations, areas, and system health.

Guidelines:
- Always use tools to look up real data — never guess entity IDs or states.
- When listing items, use filtered queries with specific domains/keywords \
  rather than fetching everything.
- Start broad (summaries/counts) then drill into specifics as needed.
- For maintenance tasks, explain what you found and suggest concrete fixes.
- Be concise. Use markdown tables or lists for structured data.
"""


@dataclass
class AgentDeps:
    ha: HAClient


agent = Agent(
    deps_type=AgentDeps,
    system_prompt=SYSTEM_PROMPT,
)


# ------------------------------------------------------------------
# Entity tools
# ------------------------------------------------------------------


@agent.tool
async def list_entities(
    ctx: RunContext[AgentDeps],
    domain: str | None = None,
    state: str | None = None,
    keyword: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """List entities with optional filters. With no filters returns a domain
    summary (counts per domain). With filters returns a paginated compact list.

    Args:
        domain: Filter by entity domain (e.g. 'light', 'sensor', 'switch').
        state: Filter by current state value (e.g. 'on', 'off', 'unavailable').
        keyword: Filter by name or entity_id substring.
        limit: Max results to return (default 25).
        offset: Pagination offset.
    """
    states = await ctx.deps.ha.get_states()
    has_filter = any([domain, state, keyword])

    results = []
    for s in states:
        eid: str = s["entity_id"]
        if domain and not eid.startswith(f"{domain}."):
            continue
        if state and s["state"] != state:
            continue
        name = s.get("attributes", {}).get("friendly_name", eid)
        if keyword and keyword.lower() not in f"{eid} {name}".lower():
            continue
        results.append({"entity_id": eid, "name": name, "state": s["state"]})

    if not has_filter:
        counter: Counter[str] = Counter()
        for r in results:
            d = r["entity_id"].split(".")[0]
            counter[d] += 1
        return {
            "total": len(results),
            "summary": dict(counter.most_common()),
        }

    total = len(results)
    page = results[offset : offset + limit]
    return {"results": page, "total": total, "showing": len(page), "offset": offset}


@agent.tool
async def get_entity_details(
    ctx: RunContext[AgentDeps],
    entity_id: str,
) -> dict:
    """Get full details for a single entity including state and attributes.

    Args:
        entity_id: The entity ID (e.g. 'light.living_room').
    """
    try:
        state = await ctx.deps.ha.get_entity_state(entity_id)
    except Exception:
        return {"error": f"Entity '{entity_id}' not found"}

    return {
        "entity_id": state["entity_id"],
        "state": state["state"],
        "attributes": state.get("attributes", {}),
        "last_changed": state.get("last_changed"),
        "last_updated": state.get("last_updated"),
    }


@agent.tool
async def get_entity_history(
    ctx: RunContext[AgentDeps],
    entity_id: str,
    hours: int = 24,
) -> dict:
    """Get recent state history for an entity.

    Args:
        entity_id: The entity ID.
        hours: Number of hours of history to retrieve (default 24).
    """
    history = await ctx.deps.ha.get_history(entity_id, hours=hours)
    if not history or not history[0]:
        return {"entity_id": entity_id, "changes": []}

    entries = history[0]
    changes = [
        {"state": e["state"], "last_changed": e.get("last_changed")}
        for e in entries[-50:]
    ]
    return {
        "entity_id": entity_id,
        "hours": hours,
        "total_changes": len(entries),
        "changes": changes,
    }


@agent.tool
async def search_entities(
    ctx: RunContext[AgentDeps],
    query: str,
    limit: int = 25,
) -> dict:
    """Search entities by name or entity_id substring.

    Args:
        query: Search term to match against entity IDs and friendly names.
        limit: Max results (default 25).
    """
    states = await ctx.deps.ha.get_states()
    q = query.lower()
    results = []
    for s in states:
        eid = s["entity_id"]
        name = s.get("attributes", {}).get("friendly_name", eid)
        if q in f"{eid} {name}".lower():
            results.append({"entity_id": eid, "name": name, "state": s["state"]})

    return {"results": results[:limit], "total": len(results), "query": query}


# ------------------------------------------------------------------
# Automation & script tools
# ------------------------------------------------------------------


@agent.tool
async def list_automations(
    ctx: RunContext[AgentDeps],
    keyword: str | None = None,
    state: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """List automations with optional filters.

    Args:
        keyword: Filter by automation name/alias substring.
        state: Filter by state ('on' or 'off').
        limit: Max results (default 25).
        offset: Pagination offset.
    """
    states = await ctx.deps.ha.get_states()
    automations = [s for s in states if s["entity_id"].startswith("automation.")]

    results = []
    for a in automations:
        attrs = a.get("attributes", {})
        alias = attrs.get("friendly_name", a["entity_id"])
        if keyword and keyword.lower() not in alias.lower():
            continue
        if state and a["state"] != state:
            continue
        results.append({
            "entity_id": a["entity_id"],
            "alias": alias,
            "state": a["state"],
            "last_triggered": attrs.get("last_triggered"),
        })

    total = len(results)
    page = results[offset : offset + limit]
    return {"results": page, "total": total, "showing": len(page), "offset": offset}


@agent.tool
async def list_scripts(
    ctx: RunContext[AgentDeps],
    keyword: str | None = None,
    limit: int = 25,
    offset: int = 0,
) -> dict:
    """List scripts with optional filters.

    Args:
        keyword: Filter by script name substring.
        limit: Max results (default 25).
        offset: Pagination offset.
    """
    states = await ctx.deps.ha.get_states()
    scripts = [s for s in states if s["entity_id"].startswith("script.")]

    results = []
    for s in scripts:
        name = s.get("attributes", {}).get("friendly_name", s["entity_id"])
        if keyword and keyword.lower() not in name.lower():
            continue
        results.append({
            "entity_id": s["entity_id"],
            "name": name,
            "state": s["state"],
        })

    total = len(results)
    page = results[offset : offset + limit]
    return {"results": page, "total": total, "showing": len(page), "offset": offset}


# ------------------------------------------------------------------
# Analysis tools
# ------------------------------------------------------------------


@agent.tool
async def find_unavailable_entities(
    ctx: RunContext[AgentDeps],
    domain: str | None = None,
    limit: int = 50,
) -> dict:
    """Find entities currently in 'unavailable' or 'unknown' state.

    Args:
        domain: Optionally limit to a specific domain.
        limit: Max results (default 50).
    """
    states = await ctx.deps.ha.get_states()
    results = []
    for s in states:
        eid = s["entity_id"]
        if domain and not eid.startswith(f"{domain}."):
            continue
        if s["state"] in ("unavailable", "unknown"):
            results.append({
                "entity_id": eid,
                "name": s.get("attributes", {}).get("friendly_name", eid),
                "state": s["state"],
            })

    return {"results": results[:limit], "total": len(results)}


@agent.tool
async def find_stale_entities(
    ctx: RunContext[AgentDeps],
    domain: str | None = None,
    hours: int = 48,
    limit: int = 50,
) -> dict:
    """Find entities that haven't changed state in a given number of hours.
    Useful for detecting stuck or abandoned sensors/entities.

    Args:
        domain: Optionally limit to a specific domain.
        hours: Consider entities stale if unchanged for this many hours (default 48).
        limit: Max results (default 50).
    """
    from datetime import datetime, timezone

    states = await ctx.deps.ha.get_states()
    cutoff = datetime.now(timezone.utc).isoformat()
    threshold = datetime.now(timezone.utc) - __import__("datetime").timedelta(hours=hours)

    results = []
    for s in states:
        eid = s["entity_id"]
        if domain and not eid.startswith(f"{domain}."):
            continue
        # Skip domains where not changing is normal
        d = eid.split(".")[0]
        if d in ("automation", "script", "scene", "zone", "person",
                 "persistent_notification", "input_boolean", "input_number",
                 "input_select", "input_text", "input_datetime"):
            continue

        last_changed = s.get("last_changed")
        if not last_changed:
            continue
        try:
            changed_dt = datetime.fromisoformat(last_changed)
            if changed_dt < threshold:
                results.append({
                    "entity_id": eid,
                    "name": s.get("attributes", {}).get("friendly_name", eid),
                    "state": s["state"],
                    "last_changed": last_changed,
                })
        except (ValueError, TypeError):
            continue

    return {"results": results[:limit], "total": len(results), "hours": hours}


@agent.tool
async def find_unused_automations(
    ctx: RunContext[AgentDeps],
    days: int = 30,
    limit: int = 25,
) -> dict:
    """Find automations that haven't triggered recently or are disabled.

    Args:
        days: Consider automations unused if not triggered in this many days (default 30).
        limit: Max results (default 25).
    """
    from datetime import datetime, timezone, timedelta

    states = await ctx.deps.ha.get_states()
    threshold = datetime.now(timezone.utc) - timedelta(days=days)
    automations = [s for s in states if s["entity_id"].startswith("automation.")]

    results = []
    for a in automations:
        attrs = a.get("attributes", {})
        alias = attrs.get("friendly_name", a["entity_id"])
        last_triggered = attrs.get("last_triggered")

        if a["state"] == "off":
            results.append({
                "entity_id": a["entity_id"],
                "alias": alias,
                "reason": "disabled (state=off)",
                "last_triggered": last_triggered,
            })
            continue

        if last_triggered:
            try:
                triggered_dt = datetime.fromisoformat(last_triggered)
                if triggered_dt < threshold:
                    results.append({
                        "entity_id": a["entity_id"],
                        "alias": alias,
                        "reason": f"not triggered in {days}+ days",
                        "last_triggered": last_triggered,
                    })
            except (ValueError, TypeError):
                pass

    return {"results": results[:limit], "total": len(results), "days": days}


@agent.tool
async def get_error_log(
    ctx: RunContext[AgentDeps],
    lines: int = 50,
) -> dict:
    """Get recent Home Assistant error log entries.

    Args:
        lines: Number of lines to return (default 50).
    """
    log = await ctx.deps.ha.get_error_log()
    log_lines = log.strip().split("\n")
    return {"lines": log_lines[-lines:], "total_lines": len(log_lines)}


# ------------------------------------------------------------------
# Utility tools
# ------------------------------------------------------------------


@agent.tool
async def render_template(
    ctx: RunContext[AgentDeps],
    template: str,
) -> dict:
    """Render a Home Assistant Jinja2 template.

    Args:
        template: The Jinja2 template string to evaluate.
    """
    result = await ctx.deps.ha.render_template(template)
    return {"template": template, "result": result}


@agent.tool
async def check_config(ctx: RunContext[AgentDeps]) -> dict:
    """Validate the Home Assistant configuration files."""
    return await ctx.deps.ha.check_config()


@agent.tool
async def remove_entity(
    ctx: RunContext[AgentDeps],
    entity_id: str,
) -> dict:
    """Remove an entity from the Home Assistant entity registry. This is
    permanent — the entity will be re-created only if its integration
    re-discovers it.

    Args:
        entity_id: The entity ID to remove (e.g. 'sensor.old_device_temperature').
    """
    try:
        return await ctx.deps.ha.remove_entity(entity_id)
    except Exception as e:
        return {"error": f"Failed to remove '{entity_id}': {e}"}
