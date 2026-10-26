"""Daily pipeline: gather -> store -> compose -> speak -> publish.

    python -m brief            full run
    python -m brief --dry-run  print the script, don't save state or publish
"""

import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from . import compose, gather, newsletters, publish, store

CONFIG = Path(__file__).resolve().parent.parent / "config.json"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    today = datetime.now(ZoneInfo(cfg["timezone"])).date()
    state = store.load()

    emails = newsletters.fetch(state, today)
    notes = gather.research(cfg, state, today)
    items = gather.extract(cfg, state, today, notes, emails)
    added = store.merge(state, items, today)
    store.prune(state, today, cfg["retention_days"])
    print(f"gather: {len(items)} items found, {added} new, {len(state['items'])} in store")

    brief = compose.write(cfg, state, today)
    print("\n" + brief["script"] + "\n")
    if args.dry_run:
        return

    for iid in brief["mentioned_ids"]:
        if iid in state["items"]:
            state["items"][iid]["briefed_on"].append(today.isoformat())
    state["last_brief"] = today.isoformat()
    publish.site(cfg, state, today, brief["script"])
    store.save(state)


if __name__ == "__main__":
    main()
