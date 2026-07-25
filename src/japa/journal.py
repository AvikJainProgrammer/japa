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


def format_journal(journal: list[dict]) -> str:
    """The whole journal, prettily: overall stats, per-mantra totals, then
    every session. Accuracy averages are weighted by chants counted, so a
    108-bead session influences the average more than a 3-bead one."""
    if not journal:
        return "No sessions recorded yet."

    rule = "─" * 70
    total_minutes = sum(s.get("duration_minutes", 0.0) for s in journal)
    total_chants = sum(m["count"] for s in journal for m in s["mantras"])
    time_spent = (f"{total_minutes / 60:.1f} h" if total_minutes >= 90
                  else f"{total_minutes:.0f} min")

    # title -> [chants counted, sessions seen in, score sum weighted by count]
    stats: dict[str, list] = {}
    for session in journal:
        for m in session["mantras"]:
            entry = stats.setdefault(m["title"], [0, 0, 0.0])
            entry[0] += m["count"]
            entry[1] += 1
            entry[2] += m["average_score"] * m["count"]

    lines = [
        rule,
        "JAPA JOURNAL",
        rule,
        f"Sessions:       {len(journal)}   "
        f"({journal[0]['date'][:10]} → {journal[-1]['date'][:10]})",
        f"Time chanting:  {time_spent}",
        f"Chants counted: {total_chants}",
        "",
        "BY MANTRA / NAME  (most chanted first)",
    ]
    width = max(len(title) for title in stats)
    for title, (chants, sessions, weighted) in sorted(
        stats.items(), key=lambda kv: (-kv[1][0], kv[0])
    ):
        accuracy = f"avg {weighted / chants:5.1f}%" if chants else "never counted"
        lines.append(f"  {title:<{width}}  {chants:>5} chant(s) in "
                     f"{sessions:>3} session(s)   {accuracy}")

    lines += ["", "SESSIONS"]
    for session in journal:
        mantras = session["mantras"]
        counted = sum(m["count"] for m in mantras)
        target = sum(m["target"] for m in mantras)
        if len(mantras) > 3:  # e.g. a namavali — don't list all 32 names
            detail = f"{len(mantras)} parts, {counted}/{target} chanted"
        else:
            detail = ", ".join(f"{m['title']} {m['count']}/{m['target']}"
                               for m in mantras)
        if counted:
            avg = sum(m["average_score"] * m["count"] for m in mantras) / counted
            detail += f"  (avg {avg:.1f}%)"
        lines.append(f"{session['date']}  ({session['duration_minutes']} min)  {detail}")
    lines.append(rule)
    return "\n".join(lines)


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
