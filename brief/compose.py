"""Pick what's worth hearing today and write it as a short spoken brief."""

from datetime import date

from . import llm

SYSTEM = """You write a morning audio brief for someone driving to work in {town}. They moved \
here recently and want to stop missing local events. It is read aloud by text-to-speech, so:
- Write plain spoken sentences. No lists, symbols, URLs, emoji or headings.
- Say dates as a listener would want them: "this Saturday", "tomorrow", "Thursday the 6th".
- Open with "Good morning" and today's day, then go straight to content.

Order: (1) anything happening today or tomorrow, or closing/ending within 3 days; \
(2) new upcoming events, soonest first; (3) new news. Skip trivia (importance 1-2) unless it's \
a slow day. Never repeat something already briefed unless it's now within 3 days; then one \
short reminder line is enough.

Length: at most {max_words} words, and much shorter when there is little new. On a day with \
nothing new say so in one or two sentences, with the next upcoming event if there is one. \
List in mentioned_ids every item id you referenced."""

SCHEMA = {
    "type": "object",
    "properties": {
        "script": {"type": "string"},
        "mentioned_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["script", "mentioned_ids"],
    "additionalProperties": False,
}


def _line(item: dict, today: date) -> str:
    when = ""
    if item.get("event_date"):
        days = (date.fromisoformat(item["event_date"]) - today).days
        when = f" | {item['event_date']} ({days:+d} days)"
        if item.get("end_date"):
            when += f" to {item['end_date']}"
    heard = f" | briefed {len(item['briefed_on'])}x, last {item['briefed_on'][-1]}" if item["briefed_on"] else " | NEW"
    extras = " | ".join(x for x in (item.get("time"), item.get("location")) if x)
    return (f"[{item['id']}] {item['kind']} | importance {item['importance']}{when}{heard}\n"
            f"  {item['title']} — {item['summary']} {extras}".rstrip())


def write(cfg: dict, state: dict, today: date) -> dict:
    items = sorted(state["items"].values(),
                   key=lambda i: (i.get("event_date") or "9999", -i["importance"]))
    listing = "\n".join(_line(i, today) for i in items) or "(no items)"
    system = SYSTEM.format(town=cfg["town"], max_words=cfg["brief_max_words"])
    prompt = f"Today is {today:%A, %B %d, %Y}.\n\nItems:\n{listing}"
    return llm.call(cfg["model"], system, [{"role": "user", "content": prompt}], schema=SCHEMA)
