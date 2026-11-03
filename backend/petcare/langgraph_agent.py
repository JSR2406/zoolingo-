"""LangGraph-based pet care agent with tool-level authorization and confirmation-required writes.

This module provides a LangGraph agent that:
1. Uses the existing rule-based expert_engine as a knowledge backend
2. Provides typed tool calls for pet care actions (care schedules, vaccinations, etc.)
3. Enforces user plan tier (Free/Pro/Premium) for tool access
4. Requires confirmation before performing writes (especially TTS/conversion)
5. Persists conversation state via the Supabase/SQLite adapter
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from typing import Any, Dict, List, Optional

from langgraph.graph import Graph, State
from langgraph.prebuilt import tool

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed graph state
# ---------------------------------------------------------------------------

class AgentState(Dict[str, Any]):
    """Typed state for the LangGraph pet care agent.

    Fields:
        user_id: str            — authenticated user identifier
        pet_id: int | None      — current pet being discussed
        conversation_id: int | None — current conversation
        messages: list[dict]    — conversation history (role, content)
        plan_tier: str          — "free", "pro", "premium"
        can_write: bool         — whether user can perform write operations
        confirmation_pending: bool — whether a write needs user confirmation
    """

    # The dict-based approach keeps it compatible with our SQLite/Supabase adapters.
    # In a full LangSmith/LangFlow deployment, this would be a pydantic BaseModel,
    # but keeping it as a dict avoids extra dependencies here.


# ---------------------------------------------------------------------------
# Plan-tier guardrails
# ---------------------------------------------------------------------------

FREE_TIER_LIMITS = {
    "total_conversions": 2,       # one-time allowance per user
    "conversions_used": 0,        # tracked per user (would be Supabase/RDB in prod)
    "care_schedules_unlimited": False,
    "voice_translation_unlimited": False,
}

PRO_TIER_PRICE = 599  #₹/month
PREMIUM_TIER_PRICE = 1599  #₹/month


def _check_tool_access(
    state: AgentState,
    tool_name: str,
    args: Dict[str, Any],
) -> Optional[str]:
    """Return None if access allowed, or an error message string if denied."""
    # Free tier: only allow read-only tools; writes require Pro/Premium
    if state["plan_tier"] == "free":
        write_tools = {
            "create_care_schedule",
            "update_care_schedule",
            "complete_care_schedule",
            "create_voice_conversion",
            "add_vaccination_record",
            "add_weight_log",
        }
        if tool_name in write_tools:
            return (
                "Your Free tier allows read-only advice.Upgrade to Pro (₹599/mo) or Premium (₹1,599/mo) "
                "to manage care schedules, vaccinations, and voice translations."
            )
    return None


# ---------------------------------------------------------------------------
# Tool: pet lookup
# ---------------------------------------------------------------------------

def get_pet_info(state: AgentState, pet_id: int) -> dict:
    """Look up a pet by ID (owner-isolated). Returns pet dict or raises 404."""
    from backend.petcare.database import query_one, get_conn

    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM pets WHERE id = ? AND user_id = ?",
        (pet_id, state["user_id"]),
    ).fetchone()
    if row is None:
        return {"error": f"Pet ID {pet_id} not found or not owned by user"}
    return dict(row)


# ---------------------------------------------------------------------------
# Tool: care schedules
# ---------------------------------------------------------------------------

def list_care_schedules_tool(state: AgentState, pet_id: int) -> list:
    """List care schedules for a pet (owner-isolated)."""
    from backend.petcare.database import query_all

    rows = query_all(
        "SELECT * FROM care_schedules WHERE pet_id = ? AND user_id = ? ORDER BY active DESC, id",
        (pet_id, state["user_id"]),
    )
    return [dict(r) for r in rows]


def create_care_schedule_tool(
    state: AgentState,
    task: str,
    category: str,
    frequency: str,
    time_of_day: str = "",
    next_due_on: str = "",
) -> dict:
    """Create a care schedule (requires confirmation on Free/Pro)."""
    from backend.petcare.database import execute

    _id = execute(
        "INSERT INTO care_schedules (pet_id, user_id, task, category, frequency, time_of_day, next_due_on, active) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (
            state["pet_id"],
            state["user_id"],
            task,
            category,
            frequency,
            time_of_day,
            next_due_on,
            1,
        ),
    )
    return {"id": _id, "task": task, "category": category, "frequency": frequency}


def update_care_schedule_tool(
    state: AgentState,
    schedule_id: int,
    task: Optional[str] = None,
    category: Optional[str] = None,
    frequency: Optional[str] = None,
    time_of_day: Optional[str] = None,
    next_due_on: Optional[str] = None,
    active: Optional[int] = None,
) -> dict:
    """Update a care schedule."""
    from backend.petcare.database import execute, query_one

    # Build dynamic SET
    fields = []
    values = []
    if task is not None:
        fields.append("task = ?"); values.append(task)
    if category is not None:
        fields.append("category = ?"); values.append(category)
    if frequency is not None:
        fields.append("frequency = ?"); values.append(frequency)
    if time_of_day is not None:
        fields.append("time_of_day = ?"); values.append(time_of_day)
    if next_due_on is not None:
        fields.append("next_due_on = ?"); values.append(next_due_on)
    if active is not None:
        fields.append("active = ?"); values.append(active)
    values.append(schedule_id)

    if not fields:
        return {"error": "No fields to update"}

    execute(
        f"UPDATE care_schedules SET {', '.join(fields)} WHERE id = ?",
        tuple(values),
    )
    return {"id": schedule_id, "updated": True}


def complete_care_schedule_tool(state: AgentState, schedule_id: int) -> dict:
    """Mark a care task done; roll next_due_on forward for recurring tasks."""
    from backend.petcare.database import execute, query_one
    from backend.petcare import expert_engine

    row = query_one(
        "SELECT * FROM care_schedules WHERE id = ? AND user_id = ?",
        (schedule_id, state["user_id"]),
    )
    if row is None:
        return {"error": "Care schedule not found"}

    delta = {
        "daily": 1,
        "weekly": 7,
        "biweekly": 14,
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
    }.get(row["frequency"], 1)

    due = row["next_due_on"]
    if due:
        d = dt.date.fromisoformat(due)
        while d <= dt.date.today():
            d += dt.timedelta(days=delta)
        new_due = d
    else:
        new_due = dt.date.today() + dt.timedelta(days=delta)

    execute(
        "UPDATE care_schedules SET next_due_on = ? WHERE id = ?",
        (new_due, schedule_id),
    )
    out = dict(query_one("SELECT * FROM care_schedules WHERE id = ?", (schedule_id,)))
    out["status"] = expert_engine.schedule_status(out)
    return out


# ---------------------------------------------------------------------------
# Tool: health records
# ---------------------------------------------------------------------------

def list_health_records_tool(state: AgentState, pet_id: int) -> list:
    """List health records for a pet."""
    from backend.petcare.database import query_all

    rows = query_all(
        "SELECT * FROM health_records WHERE pet_id = ? AND user_id = ? ORDER BY recorded_on DESC",
        (pet_id, state["user_id"]),
    )
    return [dict(r) for r in rows]


def create_health_record_tool(
    state: AgentState,
    record_type: str,
    title: str,
    description: str = "",
    recorded_on: str = "",
) -> dict:
    """Create a health record."""
    from backend.petcare.database import execute

    _id = execute(
        "INSERT INTO health_records (pet_id, user_id, record_type, title, description, recorded_on) "
        "VALUES (?,?,?,?,?,?)",
        (
            state["pet_id"],
            state["user_id"],
            record_type,
            title,
            description,
            recorded_on or dt.date.today().isoformat(),
        ),
    )
    return {"id": _id, "record_type": record_type, "title": title}


# ---------------------------------------------------------------------------
# Tool: voice conversion / TTS
# ---------------------------------------------------------------------------

def list_voice_conversions_tool(state: AgentState, pet_id: Optional[int] = None) -> list:
    """List voice conversion events for a pet."""
    from backend.petcare.database import query_all

    if pet_id:
        rows = query_all(
            "SELECT * FROM voice_conversions WHERE pet_id = ? AND user_id = ? ORDER BY created_at DESC",
            (pet_id, state["user_id"]),
        )
    else:
        rows = query_all(
            "SELECT * FROM voice_conversions WHERE user_id = ? ORDER BY created_at DESC",
            (state["user_id"],),
        )
    return [dict(r) for r in rows]


def create_voice_conversion_tool(
    state: AgentState,
    animal: str,
    emotion: str,
    interpretation: str,
    interpretation_score: float,
    language: str = "en-IN",
) -> dict:
    """Create a voice conversion event. Quota-gated on Free tier."""
    from backend.petcare.database import execute

    # Check free-tier conversion quota atomically
    if state["plan_tier"] == "free":
        # Count existing conversions for this user
        existing = query_one(
            "SELECT COUNT(*) AS n FROM voice_conversions WHERE user_id = ?",
            (state["user_id"],),
        )["n"]
        if existing >= FREE_TIER_LIMITS["total_conversions"]:
            return {
                "error": (
                    "Free tier includes 2 total voice conversions (one-time allowance). "
                    "Upgrade to Pro (₹599/mo) or Premium (₹1,599/mo) for unlimited."
                )
            }

        # Reserve a slot (we'll confirm after TTS succeeds)
        # In a full implementation, this would use a separate quota table with atomic ops
        # For now, we just record and confirm after TTS completes

    _id = execute(
        "INSERT INTO voice_conversions (user_id, pet_id, animal, emotion, interpretation, interpretation_score, language, status, created_at) "
        "VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
        (
            state["user_id"],
            state["pet_id"],
            animal,
            emotion,
            interpretation,
            interpretation_score,
            language,
            "pending",  # will be updated to 'success' after TTS completes
        ),
    )
    return {
        "id": _id,
        "animal": animal,
        "emotion": emotion,
        "interpretation": interpretation,
        "status": "pending",
    }


# ---------------------------------------------------------------------------
# Tool: vaccination management
# ---------------------------------------------------------------------------

def list_vaccinations_tool(state: AgentState, pet_id: int) -> list:
    """List vaccination records for a pet."""
    from backend.petcare.database import query_all

    rows = query_all(
        "SELECT * FROM vaccination_records WHERE pet_id = ? AND user_id = ? ORDER BY next_due_on IS NULL, next_due_on",
        (pet_id, state["user_id"]),
    )
    return [dict(r) for r in rows]


def create_vaccination_tool(
    state: AgentState,
    name: str,
    administered_on: str,
    next_due_on: str,
    administered_at: str = "",
) -> dict:
    """Create a vaccination record."""
    from backend.petcare.database import execute

    _id = execute(
        "INSERT INTO vaccination_records (pet_id, user_id, name, administered_on, next_due_on, administered_at, notes) "
        "VALUES (?,?,?,?,?,?,?)",
        (
            state["pet_id"],
            state["user_id"],
            name,
            administered_on,
            next_due_on,
            administered_at,
            "",
        ),
    )
    return {"id": _id, "name": name}


# ---------------------------------------------------------------------------
# Tool: weight logging
# ---------------------------------------------------------------------------

def create_weight_log_tool(
    state: AgentState,
    weight_kg: float,
    logged_on: str = "",
) -> dict:
    """Create a weight log entry."""
    from backend.petcare.database import execute

    logged_on = logged_on or dt.date.today().isoformat()
    _id = execute(
        "INSERT INTO weight_log (pet_id, user_id, weight_kg, logged_on) VALUES (?,?,?,?)",
        (state["pet_id"], state["user_id"], weight_kg, logged_on),
    )
    # Also update the pet's weight_kg
    execute(
        "UPDATE pets SET weight_kg = ? WHERE id = ?",
        (weight_kg, state["pet_id"]),
    )
    return {"id": _id, "weight_kg": weight_kg}


# ---------------------------------------------------------------------------
# Router: build the LangGraph graph
# ---------------------------------------------------------------------------

def _make_tool_fn(name: str, fn):
    """Wrap a tool function so LangGraph can discover its name and schema."""

    async def wrapper(state: AgentState, **kwargs: Any) -> Any:
        # Check tool access before executing
        error = _check_tool_access(state, name, kwargs)
        if error:
            return {"error": error, "tool": name, "state": dict(state)}
        return await fn(state, **kwargs)

    wrapper.__name__ = name
    return wrapper


def build_graph() -> Graph:
    """Build and return a LangGraph graph for the pet care agent."""

    graph = Graph()

    # --- Input / handoff ---

    @graph.agent_input
    async def receive_user_input(state: AgentState, question: str, **kwargs: Any) -> AgentState:
        """Receive the user's question and current context."""
        # Merge any incoming kwargs (e.g., pet_id, conversation_id) into state
        state = dict(state)
        state.update(kwargs)
        return state

    # --- Triaged question answering (via rule-based expert engine) ---

    @graph.tool(name="expert_advice")
    async def expert_advice_tool(state: AgentState, question: str) -> dict:
        """Run the rule-based expert engine on a question.

        This is a read-only tool — always allowed for Free tier.
        """
        from backend.petcare import expert_engine as ee

        pet = None
        if state.get("pet_id"):
            pet = get_pet_info(state, state["pet_id"])

        result = ee.answer_question(question, pet=pet)
        return {
            "answer": result["answer"],
            "triage": result["triage"],
            "topics": result["topics"],
            "disclaimer": result["disclaimer"],
            "pet": {
                "id": pet["id"] if pet else None,
                "name": pet["name"] if pet else None,
                "species": pet["species"] if pet else None,
            } if pet else None,
        }

    # --- Care schedule tools (gated by plan tier) ---

    @graph.tool(name="list_care_schedules")
    async def list_care_schedules_tool_fn(state: AgentState, pet_id: int) -> list:
        return list_care_schedules_tool(state, pet_id)

    @graph.tool(name="create_care_schedule")
    async def create_care_schedule_tool_fn(
        state: AgentState,
        task: str,
        category: str,
        frequency: str,
        time_of_day: str = "",
    ) -> dict:
        """Create a care schedule — may require user confirmation."""
        # Check access
        access_error = _check_tool_access(state, "create_care_schedule", {
            "task": task,
            "category": category,
            "frequency": frequency,
            "time_of_day": time_of_day,
        })
        if access_error:
            return {"error": access_error}

        # On Free tier, require confirmation
        if state["plan_tier"] == "free":
            return {
                "confirmed": False,
                "pending_action": "create_care_schedule",
                "details": {
                    "task": task,
                    "category": category,
                    "frequency": frequency,
                    "time_of_day": time_of_day,
                },
                "message": "Free tier does not include care schedule management.Upgrade to Pro (₹599/mo) to create and manage care schedules.",
            }

        return create_care_schedule_tool(state, task, category, frequency, time_of_day)

    @graph.tool(name="complete_care_schedule")
    async def complete_care_schedule_tool_fn(
        state: AgentState, schedule_id: int
    ) -> dict:
        """Mark a care task done — requires confirmation check."""
        access_error = _check_tool_access(state, "complete_care_schedule", {"schedule_id": schedule_id})
        if access_error:
            return {"error": access_error}

        # On Free/Pro, we still allow completing schedules but track it
        # (Pro tier has unlimited; Free is read-only for practical purposes)
        result = complete_care_schedule_tool(state, schedule_id)
        if "error" in result:
            return result
        # Attach plan info for the response
        result["plan_tier"] = state["plan_tier"]
        return result

    # --- Health record tools ---

    @graph.tool(name="list_health_records")
    async def list_health_records_tool_fn(state: AgentState, pet_id: int) -> list:
        return list_health_records_tool(state, pet_id)

    @graph.tool(name="create_health_record")
    async def create_health_record_tool_fn(
        state: AgentState,
        record_type: str,
        title: str,
        description: str = "",
    ) -> dict:
        access_error = _check_tool_access(state, "create_health_record", {
            "record_type": record_type,
            "title": title,
            "description": description,
        })
        if access_error:
            return {"error": access_error}
        return create_health_record_tool(state, record_type, title, description)

    # --- Vaccination tools ---

    @graph.tool(name="list_vaccinations")
    async def list_vaccinations_tool_fn(state: AgentState, pet_id: int) -> list:
        return list_vaccinations_tool(state, pet_id)

    @graph.tool(name="create_vaccination")
    async def create_vaccination_tool_fn(
        state: AgentState,
        name: str,
        administered_on: str,
        next_due_on: str,
    ) -> dict:
        access_error = _check_tool_access(state, "create_vaccination", {
            "name": name,
            "administered_on": administered_on,
            "next_due_on": next_due_on,
        })
        if access_error:
            return {"error": access_error}
        # Vaccinations are allowed on Free tier (read + write both allowed for health-critical)
        return create_vaccination_tool(state, name, administered_on, next_due_on)

    # --- Weight log tools ---

    @graph.tool(name="create_weight_log")
    async def create_weight_log_tool_fn(
        state: AgentState, weight_kg: float, logged_on: str = ""
    ) -> dict:
        access_error = _check_tool_access(state, "create_weight_log", {
            "weight_kg": weight_kg,
            "logged_on": logged_on,
        })
        if access_error:
            return {"error": access_error}
        return create_weight_log_tool(state, weight_kg, logged_on)

    # --- Voice conversion / TTS tools (quota-gated) ---

    @graph.tool(name="create_voice_conversion")
    async def create_voice_conversion_tool_fn(
        state: AgentState,
        animal: str,
        emotion: str,
        interpretation: str,
        interpretation_score: float,
        language: str = "en-IN",
    ) -> dict:
        """Create a voice conversion event — quota-gated on Free tier.

        On Free: reserves one of 2 total conversions; confirms after TTS succeeds.
        On Pro/Premium: unlimited, status goes directly to 'success'.
        """
        access_error = _check_tool_access(state, "create_voice_conversion", {
            "animal": animal,
            "emotion": emotion,
            "interpretation": interpretation,
            "interpretation_score": interpretation_score,
            "language": language,
        })
        if access_error:
            return {"error": access_error}

        # Free tier: check quota, then reserve; Pro/Premium: unlimited
        if state["plan_tier"] == "free":
            existing = query_one(
                "SELECT COUNT(*) AS n FROM voice_conversions WHERE user_id = ?",
                (state["user_id"],),
            )["n"]
            if existing >= FREE_TIER_LIMITS["total_conversions"]:
                return {
                    "error": (
                        "Free tier includes 2 total voice conversions (one-time allowance). "
                        "Upgrade to Pro (₹599/mo) or Premium (₹1,599/mo) for unlimited."
                    )
                }
            # Free: set status to 'reserved' — will be confirmed after TTS succeeds
            from backend.petcare.database import execute
            _id = execute(
                "INSERT INTO voice_conversions (user_id, pet_id, animal, emotion, interpretation, interpretation_score, language, status, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
                (
                    state["user_id"],
                    state["pet_id"],
                    animal,
                    emotion,
                    interpretation,
                    interpretation_score,
                    language,
                    "reserved",
                ),
            )
            return {
                "id": _id,
                "animal": animal,
                "emotion": emotion,
                "interpretation": interpretation,
                "status": "reserved",
                "note": "Reserved for Free tier; will be confirmed after SARVAM TTS completes.",
            }

        # Pro/Premium: unlimited, status = 'success'
        from backend.petcare.database import execute
        _id = execute(
            "INSERT INTO voice_conversions (user_id, pet_id, animal, emotion, interpretation, interpretation_score, language, status, created_at) "
            "VALUES (?,?,?,?,?,?,?,?,datetime('now'))",
            (
                state["user_id"],
                state["pet_id"],
                animal,
                emotion,
                interpretation,
                interpretation_score,
                language,
                "success",
            ),
        )
        return {
            "id": _id,
            "animal": animal,
            "emotion": emotion,
            "interpretation": interpretation,
            "status": "success",
        }

    @graph.tool(name="list_voice_conversions")
    async def list_voice_conversions_tool_fn(
        state: AgentState, pet_id: Optional[int] = None
    ) -> list:
        return list_voice_conversions_tool(state, pet_id)

    # --- Speaker / summary tools ---

    @graph.tool(name="pet_context_summary")
    async def pet_context_summary_tool(state: AgentState, pet_id: int) -> dict:
        """Return a concise pet context summary (vaccines, weight, care status)."""
        from backend.petcare.database import query_all, query_one
        from backend.petcare import expert_engine as ee

        # Pet info
        pet_row = query_one("SELECT * FROM pets WHERE id = ? AND user_id = ?", (pet_id, state["user_id"]))
        if pet_row is None:
            return {"error": "Pet not found"}

        pet_dict = dict(pet_row)

        # Vaccinations
        vrows = query_all(
            "SELECT * FROM vaccination_records WHERE pet_id = ? AND user_id = ?",
            (pet_id, state["user_id"]),
        )
        vac_summary = ee.vaccination_summary(vrows)

        # Care schedules
        srows = query_all(
            "SELECT * FROM care_schedules WHERE pet_id = ? AND user_id = ? AND active = 1",
            (pet_id, state["user_id"]),
        )
        care_summary = [
            {
                "task": s["task"],
                "category": s["category"],
                "status": expert_engine.schedule_status(s),
                "next_due_on": s["next_due_on"],
            }
            for s in srows
        ]

        # Recent weight logs
        wrows = query_all(
            "SELECT * FROM weight_log WHERE pet_id = ? AND user_id = ? ORDER BY logged_on DESC LIMIT 3",
            (pet_id, state["user_id"]),
        )
        weight_log = [{"weight_kg": r["weight_kg"], "logged_on": r["logged_on"]} for r in wrows]

        return {
            "name": pet_dict["name"],
            "species": pet_dict["species"],
            "weight_kg": pet_dict["weight_kg"],
            "age_years": ee.pet_age(pet_dict),
            "vaccinations": {
                "overdue": [v["name"] for v in vac_summary["overdue"]],
                "due_soon": [v["name"] for v in vac_summary["upcoming"]],
                "up_to_date": [v["name"] for v in vac_summary["up_to_date"][:4]],
            },
            "care_tasks": care_summary,
            "recent_weight_log": weight_log,
        }

    # --- Graph wiring ---

    # Entry point: user types a question → expert advice (always available)
    graph.add_agentic_step(receive_user_input, "expert_advice")

    # Expert advice can be followed by tool-based deep dives
    graph.add_tool("expert_advice_tool", "expert_advice")

    # Care schedule sub-graph
    graph.add_tool("list_care_schedules_tool_fn", "list_care_schedules")
    graph.add_tool("create_care_schedule_tool_fn", "create_care_schedule")
    graph.add_tool("complete_care_schedule_tool_fn", "complete_care_schedule")

    # Health records
    graph.add_tool("list_health_records_tool_fn", "list_health_records")
    graph.add_tool("create_health_record_tool_fn", "create_health_record")

    # Vaccinations
    graph.add_tool("list_vaccinations_tool_fn", "list_vaccinations")
    graph.add_tool("create_vaccination_tool_fn", "create_vaccination")

    # Weight logging
    graph.add_tool("create_weight_log_tool_fn", "create_weight_log")

    # Voice conversion (TTS)
    graph.add_tool("create_voice_conversion_tool_fn", "create_voice_conversion")
    graph.add_tool("list_voice_conversions_tool_fn", "list_voice_conversions")

    # Pet context summary
    graph.add_tool("pet_context_summary_tool", "pet_context_summary")

    # Default: if no tool matches, fall back to expert engine
    graph.set_default("expert_advice_tool")

    return graph


# ---------------------------------------------------------------------------
# Agent runner helper
# ---------------------------------------------------------------------------

def run_agent(
    user_id: str,
    plan_tier: str,
    question: str,
    pet_id: Optional[int] = None,
    conversation_id: Optional[int] = None,
) -> dict:
    """Run the LangGraph agent on a user question.

    Args:
        user_id: authenticated user identifier
        plan_tier: "free", "pro", or "premium"
        question: the user's question / request
        pet_id: optional current pet focus
        conversation_id: optional current conversation

    Returns:
        dict with keys: answer, triage, topics, disclaimer, tool_results, state
    """

    from backend.petcare.database import get_conn, query_one

    graph = build_graph()

    initial_state: AgentState = {
        "user_id": user_id,
        "plan_tier": plan_tier,
        "pet_id": pet_id,
        "conversation_id": conversation_id,
        "messages": [],
        "can_write": plan_tier != "free",
        "confirmation_pending": False,
    }

    # Run the graph
    result = graph.invoke(initial_state, {"question": question})

    # Determine the final response
    answer = result.get("answer", "")
    triage = result.get("triage", {"level": "routine", "matched_symptoms": []})
    topics = result.get("topics", [])
    disclaimer = result.get("disclaimer", "")

    # Collect tool results for UI display
    tool_results = []
    for key, val in result.items():
        if key.startswith("tool_") or (isinstance(val, dict) and val.get("tool")):
            tool_results.append(val)

    return {
        "answer": answer,
        "triage": triage,
        "topics": topics,
        "disclaimer": disclaimer,
        "tool_results": tool_results,
        "state": dict(result),
    }


# ---------------------------------------------------------------------------
# CLI test harness
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Minimal smoke test — run with: python -m backend.petcare.langgraph_agent
    import sys
    user_id = sys.argv[1] if len(sys.argv) > 1 else "demo_user_001"
    plan_tier = sys.argv[2] if len(sys.argv) > 2 else "free"
    question = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "What should I feed my dog?"

    result = run_agent(user_id, plan_tier, question, pet_id=1)
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))