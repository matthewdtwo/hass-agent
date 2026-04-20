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

Dashboard Management:
- When modifying dashboards, always fetch the current config first with \
  get_dashboard_config to see the complete structure.
- Provide the COMPLETE updated config when saving — omitted fields will \
  be removed from the dashboard.
- To add a card: append it to the views[N]["cards"] array.
- To update a card: modify the card object in place.
- To remove a card: delete from the views[N]["cards"] array by index.
- Always validate that entity IDs exist before adding them to cards.
- Card types include: 'entities', 'weather', 'gauge', 'history-graph', \
  'markdown', 'picture', 'thermostat', 'glance', 'map'. Custom cards use \
  'custom:card-name' format.
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
    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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
    try:
        history = await ctx.deps.ha.get_history(entity_id, hours=hours)
    except Exception as e:
        return {"error": f"Failed to fetch history for '{entity_id}': {e}"}
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
    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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
    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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
async def create_automation(
    ctx: RunContext[AgentDeps],
    alias: str,
    triggers: list[dict],
    actions: list[dict],
    description: str = "",
    conditions: list[dict] | None = None,
    mode: str = "single",
) -> dict:
    """Create a new Home Assistant automation.

    Args:
        alias: Short friendly name (2-3 words, e.g. 'Motion Lights', 'Night Lock').
        triggers: List of trigger configurations. Each trigger needs a 'trigger'
            key (formerly 'platform') and trigger-specific keys. Example:
            [{"trigger": "state", "entity_id": "binary_sensor.motion", "to": "on"}]
        actions: List of action configurations. Example:
            [{"action": "light.turn_on", "target": {"entity_id": "light.living_room"}}]
        description: Optional description of what the automation does.
        conditions: Optional list of condition configurations.
        mode: Execution mode — 'single', 'restart', 'queued', or 'parallel' (default 'single').
    """
    config = {
        "alias": alias,
        "description": description,
        "mode": mode,
        "triggers": triggers,
        "conditions": conditions or [],
        "actions": actions,
    }
    try:
        result = await ctx.deps.ha.create_automation(config)
        return {"alias": alias, **result}
    except Exception as e:
        return {"error": f"Failed to create automation: {e}"}


@agent.tool
async def get_automation_config(
    ctx: RunContext[AgentDeps],
    entity_id: str,
) -> dict:
    """Get the full editable configuration of an existing automation.
    Use this before update_automation to see the current triggers, conditions,
    and actions.

    Args:
        entity_id: The automation entity ID (e.g. 'automation.turn_on_lights').
    """
    try:
        state = await ctx.deps.ha.get_entity_state(entity_id)
    except Exception:
        return {"error": f"Automation '{entity_id}' not found"}

    automation_id = state.get("attributes", {}).get("id")
    if not automation_id:
        return {"error": f"Could not resolve config ID for '{entity_id}'"}

    try:
        config = await ctx.deps.ha.get_automation_config(automation_id)
        return {"entity_id": entity_id, "automation_id": automation_id, "config": config}
    except Exception as e:
        return {"error": f"Failed to fetch config for '{entity_id}': {e}"}


@agent.tool
async def update_automation(
    ctx: RunContext[AgentDeps],
    entity_id: str,
    alias: str,
    triggers: list[dict],
    actions: list[dict],
    description: str = "",
    conditions: list[dict] | None = None,
    mode: str = "single",
) -> dict:
    """Update an existing Home Assistant automation. You must provide the
    complete automation config — any fields you omit will be removed.
    Use get_automation_config first to see the current config.

    Args:
        entity_id: The automation entity ID (e.g. 'automation.turn_on_lights').
        alias: Friendly name for the automation.
        triggers: Complete list of trigger configurations.
        actions: Complete list of action configurations.
        description: Optional description of what the automation does.
        conditions: Optional list of condition configurations.
        mode: Execution mode — 'single', 'restart', 'queued', or 'parallel' (default 'single').
    """
    try:
        state = await ctx.deps.ha.get_entity_state(entity_id)
    except Exception:
        return {"error": f"Automation '{entity_id}' not found"}

    automation_id = state.get("attributes", {}).get("id")
    if not automation_id:
        return {"error": f"Could not resolve config ID for '{entity_id}'"}

    config = {
        "alias": alias,
        "description": description,
        "mode": mode,
        "triggers": triggers,
        "conditions": conditions or [],
        "actions": actions,
    }
    try:
        result = await ctx.deps.ha.update_automation(automation_id, config)
        return {"entity_id": entity_id, **result}
    except Exception as e:
        return {"error": f"Failed to update automation: {e}"}


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
    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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
# Dashboard/Lovelace tools
# ------------------------------------------------------------------


@agent.tool
async def list_dashboards(ctx: RunContext[AgentDeps]) -> dict:
    """List all available dashboards.

    Returns:
        A list of dashboard IDs, titles, and icons that can be used with
        other dashboard tools.
    """
    try:
        dashboards = await ctx.deps.ha.get_dashboards()
    except Exception as e:
        return {"error": f"Failed to fetch dashboards: {e}"}

    results = []
    for d in dashboards:
        results.append({
            "id": d.get("id"),
            "title": d.get("title"),
            "icon": d.get("icon"),
        })

    return {"dashboards": results, "total": len(results)}


@agent.tool
async def get_dashboard_config(
    ctx: RunContext[AgentDeps],
    dashboard_id: str,
) -> dict:
    """Get the full configuration of a dashboard for inspection or modification.

    This returns the complete dashboard structure including all views and cards.
    Use this before update_dashboard_config to see the current layout.

    Args:
        dashboard_id: The dashboard ID (e.g., 'lovelace-1').

    Returns:
        The dashboard configuration with views and cards. Each card includes
        its type, entities, and other configuration.
    """
    try:
        config = await ctx.deps.ha.get_dashboard_config(dashboard_id)
    except Exception as e:
        return {"error": f"Failed to fetch dashboard config for '{dashboard_id}': {e}"}

    # Summarize the config to keep token usage reasonable
    summary = {"dashboard_id": dashboard_id}
    if "views" in config:
        views_summary = []
        for i, view in enumerate(config["views"]):
            view_info = {
                "index": i,
                "title": view.get("title", "Untitled"),
                "icon": view.get("icon"),
                "card_count": len(view.get("cards", [])),
                "cards": []
            }
            for j, card in enumerate(view.get("cards", [])):
                card_info = {
                    "index": j,
                    "type": card.get("type"),
                    "title": card.get("title"),
                }
                # Include entity references
                if "entity" in card:
                    card_info["entity"] = card["entity"]
                if "entities" in card:
                    card_info["entities"] = card["entities"]
                view_info["cards"].append(card_info)
            views_summary.append(view_info)
        summary["views"] = views_summary

    # Also include the raw config for reference
    summary["raw_config"] = config
    return summary


@agent.tool
async def update_dashboard_config(
    ctx: RunContext[AgentDeps],
    dashboard_id: str,
    config: dict,
) -> dict:
    """Update a dashboard's configuration. You must provide the complete
    configuration — any fields you omit will be removed.

    Always use get_dashboard_config first to fetch the current config, then
    modify it, then save with this tool. This prevents accidental data loss.

    Args:
        dashboard_id: The dashboard ID (e.g., 'lovelace-1').
        config: The complete dashboard configuration object with all views
                and cards. Must include the views array.

    Returns:
        Confirmation of the update or an error message.
    """
    try:
        result = await ctx.deps.ha.update_dashboard_config(dashboard_id, config)
        return {
            "dashboard_id": dashboard_id,
            "updated": True,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Failed to update dashboard '{dashboard_id}': {e}"}


@agent.tool
async def delete_dashboard(
    ctx: RunContext[AgentDeps],
    dashboard_id: str,
) -> dict:
    """Delete a dashboard. This action is permanent.

    Args:
        dashboard_id: The dashboard ID to delete (e.g., 'lovelace-1').

    Returns:
        Confirmation of deletion or an error message.
    """
    try:
        result = await ctx.deps.ha.delete_dashboard(dashboard_id)
        return {
            "dashboard_id": dashboard_id,
            "deleted": True,
            "result": result,
        }
    except Exception as e:
        return {"error": f"Failed to delete dashboard '{dashboard_id}': {e}"}


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
    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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

    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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

    try:
        states = await ctx.deps.ha.get_states()
    except Exception as e:
        return {"error": f"Failed to fetch states: {e}"}
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
    try:
        log = await ctx.deps.ha.get_error_log()
    except Exception as e:
        return {"error": f"Failed to fetch error log: {e}"}
    log_lines = log.strip().split("\n")
    return {"lines": log_lines[-lines:], "total_lines": len(log_lines)}


# ------------------------------------------------------------------
# Service discovery tools
# ------------------------------------------------------------------


@agent.tool
async def list_services(
    ctx: RunContext[AgentDeps],
    domain: str | None = None,
) -> dict:
    """List available Home Assistant services. With no domain filter returns a
    summary of service counts per domain. With a domain filter returns all
    services and their fields for that domain.

    Args:
        domain: Filter by domain (e.g. 'light', 'automation', 'notify').
    """
    try:
        services = await ctx.deps.ha.get_services()
    except Exception as e:
        return {"error": f"Failed to fetch services: {e}"}

    if not domain:
        summary = {s["domain"]: len(s.get("services", {})) for s in services}
        return {"total_domains": len(summary), "domains": summary}

    for s in services:
        if s["domain"] == domain:
            compact = {}
            for name, info in s.get("services", {}).items():
                entry: dict = {"description": info.get("description", "")}
                fields = info.get("fields", {})
                if fields:
                    entry["fields"] = {
                        k: v.get("description", "")
                        for k, v in fields.items()
                    }
                compact[name] = entry
            return {"domain": domain, "services": compact}

    return {"error": f"Domain '{domain}' not found"}


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
    try:
        result = await ctx.deps.ha.render_template(template)
        return {"template": template, "result": result}
    except Exception as e:
        return {"error": f"Template rendering failed: {e}"}


@agent.tool
async def check_config(ctx: RunContext[AgentDeps]) -> dict:
    """Validate the Home Assistant configuration files."""
    try:
        return await ctx.deps.ha.check_config()
    except Exception as e:
        return {"error": f"Config check failed: {e}"}


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
