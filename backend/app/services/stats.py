"""Pure computation helpers (no I/O) — all dashboard math lives server-side."""
from __future__ import annotations

from collections import Counter
from datetime import date, timedelta


def language_breakdown(repos: list[dict]) -> list[dict]:
    """Share of repos per primary language (forks excluded), sorted desc."""
    langs = Counter(r["language"] for r in repos if r.get("language") and not r.get("is_fork"))
    total = sum(langs.values())
    if not total:
        return []
    return [
        {"language": lang, "repos": n, "percent": round(n * 100 / total, 1)}
        for lang, n in langs.most_common()
    ]


def repo_totals(repos: list[dict]) -> dict:
    own = [r for r in repos if not r.get("is_fork")]
    return {
        "total_stars": sum(r["stars"] for r in own),
        "total_forks": sum(r["forks"] for r in own),
        "repo_count": len(own),
    }


def intensity_level(count: int, max_count: int) -> int:
    """Map a daily count to a 0-4 heatmap level (quartiles of the busiest day)."""
    if count <= 0 or max_count <= 0:
        return 0
    ratio = count / max_count
    if ratio <= 0.25:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.75:
        return 3
    return 4


def contribution_stats(days: list[dict], today: date | None = None) -> dict:
    """Streaks, totals and heatmap levels from [{date, count}, ...]."""
    today = today or date.today()
    by_date = {d["date"]: d["count"] for d in days}
    max_count = max(by_date.values(), default=0)

    levelled = [
        {"date": d["date"], "count": d["count"], "level": intensity_level(d["count"], max_count)}
        for d in sorted(days, key=lambda x: x["date"])
    ]

    # longest streak
    longest = run = 0
    prev: date | None = None
    for d in sorted(by_date):
        if by_date[d] <= 0:
            run, prev = 0, None
            continue
        cur = date.fromisoformat(d)
        run = run + 1 if prev and (cur - prev).days == 1 else 1
        longest = max(longest, run)
        prev = cur

    # current streak: ends today, or yesterday (today may not be over yet)
    cursor = today if by_date.get(today.isoformat(), 0) > 0 else today - timedelta(days=1)
    current = 0
    while by_date.get(cursor.isoformat(), 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    busiest = max(by_date.items(), key=lambda kv: kv[1], default=(None, 0))
    return {
        "days": levelled,
        "total": sum(by_date.values()),
        "active_days": sum(1 for v in by_date.values() if v > 0),
        "current_streak": current,
        "longest_streak": longest,
        "busiest_day": {"date": busiest[0], "count": busiest[1]} if busiest[0] else None,
    }
