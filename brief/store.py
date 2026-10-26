"""Rolling store of local items, persisted to data/items.json and committed by CI."""

import hashlib
import json
import re
from datetime import date, timedelta
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "items.json"


def load() -> dict:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {"items": {}, "seen_emails": [], "last_brief": None}


def save(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


def item_id(title: str, event_date: str | None) -> str:
    """Stable id so the same event found on two sites collapses to one entry."""
    words = re.sub(r"[^a-z0-9 ]", "", title.lower()).split()
    key = " ".join(sorted(w for w in words if len(w) > 2)) + "|" + (event_date or "")
    return hashlib.sha1(key.encode()).hexdigest()[:12]


def merge(state: dict, new_items: list[dict], today: date) -> int:
    """Add or update items. Returns how many were genuinely new."""
    added = 0
    for item in new_items:
        iid = item.get("existing_id") or item_id(item["title"], item.get("event_date"))
        existing = state["items"].get(iid)
        if existing:
            # Keep briefing history and first_seen; refresh the facts.
            existing.update({k: v for k, v in item.items() if v and k != "existing_id"})
            continue
        item.pop("existing_id", None)
        item["id"] = iid
        item["first_seen"] = today.isoformat()
        item["briefed_on"] = []
        state["items"][iid] = item
        added += 1
    return added


def prune(state: dict, today: date, retention_days: int) -> None:
    """Keep the last `retention_days` of news, plus any event that hasn't happened yet."""
    cutoff = (today - timedelta(days=retention_days)).isoformat()
    keep = {}
    for iid, item in state["items"].items():
        last_day = item.get("end_date") or item.get("event_date")
        upcoming = last_day is not None and last_day >= today.isoformat()
        if upcoming or item["first_seen"] >= cutoff:
            keep[iid] = item
    state["items"] = keep
    state["seen_emails"] = state["seen_emails"][-500:]
