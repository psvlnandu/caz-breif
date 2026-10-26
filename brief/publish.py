"""Render the brief to MP3 and write the static files served by GitHub Pages."""

import asyncio
import html
import json
from datetime import date
from pathlib import Path

import edge_tts

SITE = Path(__file__).resolve().parent.parent / "docs"


def speak(text: str, voice: str, path: Path) -> None:
    asyncio.run(edge_tts.Communicate(text, voice, rate="+5%").save(str(path)))


def site(cfg: dict, state: dict, today: date, script: str) -> None:
    SITE.mkdir(exist_ok=True)
    speak(script, cfg["voice"], SITE / "latest.mp3")
    (SITE / "latest.txt").write_text(script, encoding="utf-8")
    # Phones check this to avoid replaying yesterday's brief.
    (SITE / "latest.json").write_text(json.dumps({"date": today.isoformat()}), encoding="utf-8")

    upcoming = sorted(
        (i for i in state["items"].values() if i.get("event_date") and i["event_date"] >= today.isoformat()),
        key=lambda i: i["event_date"],
    )
    rows = "\n".join(
        f"<li><b>{html.escape(i['event_date'])}</b> {html.escape(i['title'])}"
        + (f' — <a href="{html.escape(i["url"])}">details</a>' if i.get("url") else "")
        + f"<br><small>{html.escape(i['summary'])}</small></li>"
        for i in upcoming
    )
    (SITE / "index.html").write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Caz Morning Brief</title>
<style>body{{font:16px/1.5 system-ui,sans-serif;max-width:640px;margin:0 auto;padding:16px}}
li{{margin-bottom:10px}} audio{{width:100%}}</style></head><body>
<h1>Caz Morning Brief</h1><p>{today:%A, %B %d, %Y}</p>
<audio controls src="latest.mp3"></audio>
<p>{html.escape(script)}</p>
<h2>Coming up</h2><ul>{rows or "<li>Nothing scheduled yet.</li>"}</ul>
</body></html>""", encoding="utf-8")
