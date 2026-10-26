"""Find fresh local news and upcoming events, then turn them into structured items."""

from datetime import date, timedelta

from . import llm

RESEARCH_SYSTEM = """You are a local-news scout for someone who just moved to {town} and keeps \
missing community events. Your job is to find what is genuinely new or coming up, not to write prose.

Check the seed sources below with web_fetch, then use web_search to fill gaps (events in \
neighbouring towns within ~20 minutes count if they are notable). Prefer primary pages \
(organizer, village, library) over aggregators when dates conflict.

Report, as plain notes:
- EVENTS happening between {today} and {horizon}: name, date(s), time, place, cost/registration, URL.
- LAST CALLS: anything ending or closing soon (final market day, registration deadlines, \
volunteer sign-ups, seasonal closures).
- NEWS from the last 3 days that affects daily life in town.

Skip anything already in the "already known" list unless its details changed. \
Never invent a date; if a page gives no year or the date is unclear, say so."""

EXTRACT_SYSTEM = """Convert local-news research notes and newsletter emails into structured items. \
Today is {today}. Resolve relative dates ("this Saturday") against today and output ISO dates. \
Drop items that are already over, ads, and anything not local to {town} and nearby. \
If an item matches one in the known list, set existing_id to that id; otherwise null."""

ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "kind": {"type": "string", "enum": ["event", "deadline", "news"]},
                    "summary": {"type": "string", "description": "One or two spoken-friendly sentences."},
                    "event_date": {"type": ["string", "null"], "description": "YYYY-MM-DD start, null for news"},
                    "end_date": {"type": ["string", "null"], "description": "YYYY-MM-DD last day if multi-day"},
                    "time": {"type": ["string", "null"]},
                    "location": {"type": ["string", "null"]},
                    "source": {"type": "string"},
                    "url": {"type": ["string", "null"]},
                    "importance": {"type": "integer", "description": "1 (trivia) to 5 (do not miss)"},
                    "existing_id": {"type": ["string", "null"]},
                },
                "required": ["title", "kind", "summary", "event_date", "end_date", "time",
                             "location", "source", "url", "importance", "existing_id"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["items"],
    "additionalProperties": False,
}


def _known_list(state: dict) -> str:
    rows = [f"{i['id']} | {i.get('event_date') or '-'} | {i['title']}" for i in state["items"].values()]
    return "\n".join(rows) or "(none yet)"


def research(cfg: dict, state: dict, today: date) -> str:
    horizon = today + timedelta(days=cfg["event_lookahead_days"])
    sources = "\n".join(f"- {s['name']}: {s['url']}" for s in cfg["sources"])
    interests = "\n".join(f"- {i}" for i in cfg["interests"])
    tools = [
        {
            "type": "web_search_20260209",
            "name": "web_search",
            "max_uses": 10,
            "user_location": {"type": "approximate", **cfg["location"], "timezone": cfg["timezone"]},
        },
        {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 12},
    ]
    prompt = (
        f"Today is {today:%A, %B %d, %Y}.\n\nSeed sources:\n{sources}\n\n"
        f"What I care about:\n{interests}\n\nAlready known (id | date | title):\n{_known_list(state)}"
    )
    system = RESEARCH_SYSTEM.format(town=cfg["town"], today=today, horizon=horizon)
    return llm.call(cfg["model"], system, [{"role": "user", "content": prompt}], tools=tools)


def extract(cfg: dict, state: dict, today: date, notes: str, emails: list[dict]) -> list[dict]:
    parts = [f"<research_notes>\n{notes}\n</research_notes>"]
    for e in emails:
        parts.append(f"<newsletter from=\"{e['from']}\" subject=\"{e['subject']}\">\n{e['body']}\n</newsletter>")
    parts.append(f"<known_items>\n{_known_list(state)}\n</known_items>")
    system = EXTRACT_SYSTEM.format(today=today.isoformat(), town=cfg["town"])
    result = llm.call(cfg["model"], system, [{"role": "user", "content": "\n\n".join(parts)}],
                      effort="low", schema=ITEM_SCHEMA)
    known = set(state["items"])
    for item in result["items"]:
        if item["existing_id"] not in known:
            item["existing_id"] = None
    return result["items"]
