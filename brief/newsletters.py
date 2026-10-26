"""Read newsletters (and Facebook/Instagram notification emails) forwarded to a dedicated inbox.

Uses IMAP so it works with Gmail (app password) or any other mail provider.
Set IMAP_HOST, IMAP_USER, IMAP_PASSWORD; optionally IMAP_FOLDER (default INBOX).
"""

import email
import imaplib
import os
import re
from datetime import date, timedelta
from email.header import decode_header, make_header
from html import unescape

MAX_BODY_CHARS = 12000


def _text_of(msg: email.message.Message) -> str:
    plain, html = None, None
    for part in msg.walk():
        ctype = part.get_content_type()
        if part.get_content_disposition() == "attachment":
            continue
        if ctype in ("text/plain", "text/html"):
            payload = part.get_payload(decode=True) or b""
            text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
            if ctype == "text/plain" and plain is None:
                plain = text
            elif ctype == "text/html" and html is None:
                html = text
    if plain and plain.strip():
        return plain
    if html:
        html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
        return unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)))
    return ""


def fetch(state: dict, today: date, days: int = 4) -> list[dict]:
    host, user, password = (os.environ.get(k) for k in ("IMAP_HOST", "IMAP_USER", "IMAP_PASSWORD"))
    if not (host and user and password):
        print("newsletters: IMAP not configured, skipping")
        return []

    since = (today - timedelta(days=days)).strftime("%d-%b-%Y")
    seen = set(state["seen_emails"])
    out = []
    with imaplib.IMAP4_SSL(host) as imap:
        imap.login(user, password)
        imap.select(os.environ.get("IMAP_FOLDER", "INBOX"), readonly=True)
        _, data = imap.search(None, f'(SINCE "{since}")')
        for num in data[0].split():
            _, msg_data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(msg_data[0][1])
            msg_id = msg.get("Message-ID") or f"{msg.get('Date')}|{msg.get('Subject')}"
            if msg_id in seen:
                continue
            out.append({
                "from": str(make_header(decode_header(msg.get("From", "")))).replace('"', "'"),
                "subject": str(make_header(decode_header(msg.get("Subject", "")))).replace('"', "'"),
                "body": _text_of(msg)[:MAX_BODY_CHARS],
            })
            state["seen_emails"].append(msg_id)
    print(f"newsletters: {len(out)} new emails")
    return out
