# Caz Morning Brief

Every morning a GitHub Action searches Cazenovia news sites, event calendars and your
newsletter inbox. Claude keeps a rolling 14-day memory of what it found (upcoming events are
kept until they happen) and writes a short spoken brief. The brief contains only what's new,
plus reminders for anything happening in the next few days. The brief is turned into an MP3
and published. When your phone connects to the car's Bluetooth, it plays the brief.

```
GitHub Actions, 6:30 AM ──► newsletters (IMAP) ─┐
                         ├► Claude + web search ┴► items.json (14-day store) ──► Claude writes brief
                         └──────────────────────────────────────────────────────► edge-tts ──► docs/latest.mp3
Phone: car Bluetooth connects ──► Tasker downloads latest.mp3 ──► plays through car speakers
```

## Setup (about 20 minutes)

### 1. Claude API key
1. Sign up at https://console.anthropic.com.
2. Add credit under **Billing**. Also set a monthly **spend limit**, for example $15.
3. Go to **API Keys → Create Key** and copy the key (`sk-ant-...`).

Cost: Opus 5.5 with web search is probably a few tens of cents per day. Check the Usage
page after the first week. To cut cost roughly in half, set `"model": "claude-sonnet-5-5"`
in `config.json`.

### 2. GitHub repo
1. Create a **public** repo (this one is `psvlnandu/caz-breif`). GitHub Pages is free only on public repos,
   and the content is public local news anyway.
2. Push this folder to it.
3. Go to **Settings → Secrets and variables → Actions** and add the secret
   `ANTHROPIC_API_KEY`.
4. Go to **Actions → Morning brief → Run workflow** to do a first run. It should finish in a
   few minutes and commit `docs/`.
5. Go to **Settings → Pages**, choose *Deploy from a branch*, then `main` / `/docs`.
6. Your brief is now at `https://psvlnandu.github.io/caz-breif/`. That page also
   lists all upcoming events.

### 3. Newsletters, Facebook and Instagram (optional, recommended)
1. Create a new Gmail address just for this, for example `caz.brief.you@gmail.com`.
2. Subscribe it to local newsletters: the Chamber, the library, the village, race clubs and
   so on.
3. For Facebook and Instagram, turn on email notifications for the pages and groups you
   follow, and send them to this address, either directly or by auto-forwarding from your
   main email. Event posts then arrive as emails the brief can read. This avoids scraping,
   which Meta blocks.
4. Turn on 2-Step Verification for that Gmail account, then create an **App password** at
   https://myaccount.google.com/apppasswords.
5. Add these repo secrets:
   - `IMAP_HOST` = `imap.gmail.com`
   - `IMAP_USER` = the address
   - `IMAP_PASSWORD` = the app password

### 4. Android: play when the car connects
This uses **Tasker**, a one-time purchase on the Play Store.

Create a **Profile**: *State → Net → BT Connected*, and set *Name* to your car's Bluetooth
name. Then create a **Task** with these actions:

1. **Stop**, with the condition *If* `%TIME` *>* `11`. This makes it play in the morning
   only.
2. **Stop**, with the condition *If* `%CAZ_PLAYED` *~* `%DATE`. This prevents a replay if
   you reconnect.
3. **HTTP Request**: GET `https://psvlnandu.github.io/caz-breif/latest.mp3`, with
   *File / Directory To Save With Output* set to `Download/caz-brief.mp3`.
4. **Wait** 4 seconds, so the car's audio has time to connect.
5. **Music Play**: File `Download/caz-brief.mp3`.
6. **Variable Set**: `%CAZ_PLAYED` to `%DATE`.

## Tuning
Everything you'd want to change is in `config.json`:
- `sources`: add the URL of any site the brief should always check, for example a
  church calendar or the school district page.
- `interests`: what to look for.
- `brief_max_words`: 300 words is about 2 minutes. On a quiet day the brief is much shorter.
- `voice`: any edge-tts voice. Run `edge-tts --list-voices` to see them all, for example
  `en-US-GuyNeural`.
- `retention_days` and `event_lookahead_days`: how far back to remember and how far ahead to
  look.

## Running locally
```
pip install -r requirements.txt
set ANTHROPIC_API_KEY=sk-ant-...
python -m brief --dry-run     # prints today's script without saving or publishing
```
