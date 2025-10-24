# watch_all_submissions_refactored.py
# -*- coding: utf-8 -*-

"""
Watch Kaggle competition submissions and post status updates to Slack.
- One unified interval (--interval-min) controls both polling and reporting.
- Slack webhook, competition slug, and interval are CLI args.
- Kaggle authentication uses kaggle.json or environment defaults.
- All comments are in English.
"""

from __future__ import annotations
import argparse
import datetime
from datetime import timezone, timedelta
import time
import os
import json
import requests
from typing import Any, Dict, Optional, List
from kaggle.api.kaggle_api_extended import KaggleApi


# =========================
# Slack
# =========================
def slack_post(webhook_url: str, text: str, blocks: Optional[List[dict]] = None) -> None:
    """Post a message to Slack via incoming webhook."""
    if not webhook_url:
        print("[WARN] Slack webhook not configured:", text)
        return
    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks
    try:
        resp = requests.post(
            webhook_url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        resp.raise_for_status()
    except Exception as e:
        print("[Slack post failed]", e)


# =========================
# Utilities
# =========================
def get_attr(s: Any, *names, default=None):
    """Safely read both underscore and non-underscore attributes."""
    for name in names:
        if hasattr(s, name):
            v = getattr(s, name)
            if v not in (None, "", "-", "—"):
                return v
    d = getattr(s, "__dict__", {})
    for name in names:
        if name in d and d[name] not in (None, "", "-", "—"):
            return d[name]
    return default


def get_ref(s: Any) -> int:
    """Extract integer submission ref."""
    r = get_attr(s, "_ref", "ref")
    try:
        return int(r)
    except Exception:
        rs = str(r)
        digits = "".join(ch for ch in rs if ch.isdigit())
        return int(digits) if digits else -1


def status_text(s: Any) -> str:
    """Normalize status string."""
    st = get_attr(s, "_status", "status", default="")
    try:
        name = st.name
    except AttributeError:
        name = str(st)
    name_lower = name.replace("SubmissionStatus.", "").lower()
    if name_lower in {"completed", "complete"}:
        return "complete"
    if name_lower in {"uploading"}:
        return "pending"
    return name_lower


def score_display(s: Any) -> str:
    """Format score display for Public/Private LB."""
    pub = get_attr(s, "_public_score", "publicScore", "publicScoreDisplay", "scoreDisplay")
    prv = get_attr(s, "_private_score", "privateScore", "privateScoreDisplay")
    pub_str = None if pub in (None, "", "-", "—") else f"{pub}"
    prv_str = None if prv in (None, "", "-", "—") else f"{prv}"
    if pub_str and prv_str:
        return f"Public LB: *{pub_str}* / Private LB: *{prv_str}*"
    if pub_str:
        return f"Public LB: *{pub_str}*"
    if prv_str:
        return f"Private LB: *{prv_str}*"
    return "Public LB: (N/A)"


def fmt_jst(dt_utc_naive: datetime.datetime) -> str:
    """Convert UTC naive datetime to JST formatted string."""
    jst = dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=9)))
    return jst.strftime('%Y-%m-%d %H:%M:%S')


def submission_url(s: Any, competition: str) -> str:
    """Return individual submission URL or fallback to competition page."""
    url_path = get_attr(s, "_url", "url", default=None)
    if url_path:
        return f"https://www.kaggle.com{url_path}"
    return f"https://www.kaggle.com/competitions/{competition}/submissions"


def elapsed_minutes(from_dt: datetime.datetime, to_dt: datetime.datetime) -> int:
    """Return elapsed minutes (>=1)."""
    mins = int((to_dt - from_dt).total_seconds() // 60)
    return max(1, mins)


# =========================
# Core Logic
# =========================
def authenticate_kaggle() -> KaggleApi:
    """Authenticate Kaggle API using kaggle.json or env defaults."""
    api = KaggleApi()
    api.authenticate()
    return api


def run_watcher(
    webhook_url: str,
    competition: str,
    interval_min: int,
) -> None:
    """Main watcher loop for Kaggle submissions."""

    if interval_min < 1:
        raise ValueError("--interval-min must be >= 1")

    interval_sec = interval_min * 60
    api = authenticate_kaggle()

    track: Dict[int, Dict[str, Any]] = {}
    slack_post(webhook_url, f":rocket: Watcher started — *{competition}*\nSubmissions: https://www.kaggle.com/competitions/{competition}/submissions")

    while True:
        # Fetch submissions
        try:
            subs = api.competition_submissions(competition)
        except Exception as e:
            print("[WARN] Kaggle API error:", e)
            time.sleep(interval_sec)
            continue

        # Update tracking
        for s in subs:
            ref = get_ref(s)
            if ref == -1:
                continue
            seen = status_text(s)
            submit_dt = get_attr(s, "_date", "date")
            if submit_dt is None:
                submit_dt = datetime.datetime.now(timezone.utc).replace(tzinfo=None)

            if ref not in track:
                track[ref] = {"submit_time": submit_dt, "last_seen_status": seen, "last_reported_status": None}
                if seen == "complete":
                    track[ref]["last_reported_status"] = "complete"
            else:
                track[ref]["last_seen_status"] = seen

        # Report changed statuses
        now_utc = datetime.datetime.now(timezone.utc).replace(tzinfo=None)
        for s in subs:
            ref = get_ref(s)
            if ref == -1:
                continue
            info = track.get(ref)
            if not info:
                continue

            seen = info["last_seen_status"]
            reported = info["last_reported_status"]
            if seen == reported:
                continue

            submit_time = info["submit_time"]
            el_min = elapsed_minutes(submit_time, now_utc)
            link = submission_url(s, competition)

            if seen in {"pending", "queued", "running"}:
                slack_post(webhook_url, f":hourglass_flowing_sand: `{ref}` → *{seen}* / Elapsed {el_min} min\n<{link}|Open submission>")
            elif seen == "complete":
                score_line = score_display(s)
                blocks = [
                    {"type": "section", "text": {"type": "mrkdwn", "text": ":white_check_mark: *Kaggle Submission Complete*"}},
                    {"type": "section", "fields": [
                        {"type": "mrkdwn", "text": f"*Ref:*\n`{ref}`"},
                        {"type": "mrkdwn", "text": f"*Elapsed (Submit→Now):*\n{el_min} min"},
                        {"type": "mrkdwn", "text": f"*Submitted (JST):*\n{fmt_jst(submit_time)}"},
                    ]},
                    {"type": "section", "text": {"type": "mrkdwn", "text": score_line}},
                    {"type": "context", "elements": [{"type": "mrkdwn", "text": f"<{link}|Open submission>"}]}
                ]
                slack_post(webhook_url, text=f"Submission complete — ref {ref}", blocks=blocks)
            elif seen == "error":
                err = get_attr(s, "_error_description", "errorDescription", default="(no detail)")
                slack_post(webhook_url, f":x: `{ref}` → *error* / Elapsed {el_min} min\n```{err}```\n<{link}|Open submission>")
            else:
                slack_post(webhook_url, f":information_source: `{ref}` → *{seen}* / Elapsed {el_min} min\n<{link}|Open submission>")

            info["last_reported_status"] = seen

        time.sleep(interval_sec)


# =========================
# CLI
# =========================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch Kaggle submissions and send Slack notifications.")
    parser.add_argument("--competition", required=True, help="Kaggle competition slug (e.g., 'jigsaw-agile-community-rules').")
    parser.add_argument("--slack-webhook", default=os.environ.get("SLACK_WEBHOOK_URL", ""), help="Slack incoming webhook URL.")
    parser.add_argument("--interval-min", type=int, default=int(os.environ.get("INTERVAL_MIN", "10")), help="Interval in minutes for polling and reporting.")
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        run_watcher(args.slack_webhook, args.competition, args.interval_min)
    except KeyboardInterrupt:
        slack_post(args.slack_webhook, ":wave: Watcher stopped by user.")
        print("\n[INFO] Stopped by user.")


if __name__ == "__main__":
    main()
