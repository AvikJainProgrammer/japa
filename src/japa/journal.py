"""Session persistence — a simple JSON japa journal in ~/.japa/journal.json."""

import json
import time
from pathlib import Path

JOURNAL_PATH = Path.home() / ".japa" / "journal.json"


def load_journal() -> list[dict]:
    if not JOURNAL_PATH.exists():
        return []
    try:
        return json.loads(JOURNAL_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_session(mantra_results: list[dict], started_at: float) -> None:
    """Append one session record; each entry in mantra_results is
    {"title", "count", "target", "average_score"}."""
    journal = load_journal()
    journal.append(
        {
            "date": time.strftime("%Y-%m-%d %H:%M", time.localtime(started_at)),
            "duration_minutes": round((time.time() - started_at) / 60, 1),
            "mantras": mantra_results,
        }
    )
    JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL_PATH.write_text(json.dumps(journal, ensure_ascii=False, indent=2))


def format_history(journal: list[dict], limit: int = 10) -> str:
    if not journal:
        return "No sessions recorded yet."
    lines = []
    for session in journal[-limit:]:
        parts = ", ".join(
            f"{m['title']} {m['count']}/{m['target']}" for m in session["mantras"]
        )
        lines.append(
            f"{session['date']}  ({session['duration_minutes']} min)  {parts}"
        )
    return "\n".join(lines)
