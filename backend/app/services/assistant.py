"""Chatbot-style extras, grounded strictly in the cached portfolio data.

1. Ask-the-Portfolio chat: intent-based Q&A a recruiter can use ("what is their top language?").
2. Bio & Pitch generator: writes a professional summary and, if a job description was
   analysed, a tailored pitch. Deterministic (no external LLM) so it works offline and
   every sentence is traceable to real data.
"""
from __future__ import annotations

SUGGESTIONS = [
    "What are their top languages?",
    "What is their most popular project?",
    "How consistent are they?",
    "How well do they fit the job?",
    "Give me a summary",
]


def _top_langs(p: dict, n: int = 3) -> list[str]:
    return [l["language"] for l in p["languages"][:n]]


def _join(items: list[str]) -> str:
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " and " + items[-1]


def generate_bio(p: dict, match: dict | None = None) -> dict:
    prof, contrib = p["profile"], p["contributions"]
    langs = _top_langs(p)
    name = prof["name"]
    headline = f"{_join(langs)} developer" if langs else "Software developer"
    parts = [
        f"{name} is a {headline} with {prof['repo_count']} public repositories "
        f"and {prof['total_stars']} stars earned across them."
    ]
    if p["repos"]:
        top = p["repos"][0]
        parts.append(
            f"Their standout project is {top['name']}"
            + (f" ({top['language']})" if top.get("language") else "")
            + f", with {top['stars']} stars and {top['forks']} forks."
        )
    if contrib["active_days"]:
        parts.append(
            f"They were active on {contrib['active_days']} days recently, with a longest streak of "
            f"{contrib['longest_streak']} days."
        )
    highlights = [f"{prof['followers']} followers", f"{prof['total_stars']} total stars"]
    if langs:
        highlights.append(f"Primary stack: {_join(langs)}")

    pitch = None
    if match and match.get("percent") is not None:
        have = _join([m["language"] for m in match["matched"]]) or "none of the listed languages"
        pitch = f"For this role, {name} matches {match['percent']}% of the required stack ({have})."
        if match["missing"]:
            pitch += f" Gaps to close: {_join([m['language'] for m in match['missing']])}."
    return {"headline": headline.title(), "bio": " ".join(parts), "highlights": highlights, "pitch": pitch}


def answer(question: str, p: dict, match: dict | None = None) -> dict:
    q = question.lower()
    prof, contrib = p["profile"], p["contributions"]
    langs = p["languages"]

    def has(*words: str) -> bool:
        return any(w in q for w in words)

    if has("fit", "match", "job", "role", "compat"):
        if not match or match.get("percent") is None:
            text = "Paste a job description into the Tech Stack Compatibility box first, then ask me again."
        else:
            text = generate_bio(p, match)["pitch"]
    elif has("language", "stack", "skill", "tech", "know"):
        text = (
            "Top languages by repo share: " + ", ".join(f"{l['language']} ({l['percent']}%)" for l in langs[:5]) + "."
            if langs else "No language data found in their public repositories."
        )
    elif has("popular", "best", "top project", "starred", "famous", "standout", "most"):
        if p["repos"]:
            r = p["repos"][0]
            text = f"{r['name']} is their most starred repo with {r['stars']} stars and {r['forks']} forks. {r['description']}".strip()
        else:
            text = "They have no public non-fork repositories yet."
    elif has("streak", "consisten", "active", "commit", "contribut", "frequen"):
        if contrib["days"]:
            text = (
                f"{contrib['total']} contributions across {contrib['active_days']} active days; "
                f"current streak {contrib['current_streak']} days, longest {contrib['longest_streak']} days."
            )
        else:
            text = "Contribution data is unavailable (a GitHub token is needed for the full calendar)."
    elif has("follow", "popular", "star", "fork", "reputation"):
        text = f"{prof['followers']} followers, {prof['total_stars']} total stars and {prof['total_forks']} forks."
    elif has("how many repo", "repos", "repositories", "projects"):
        text = f"{prof['repo_count']} public non-fork repositories."
    elif has("summary", "who", "about", "introduce", "bio", "tell me"):
        text = generate_bio(p, match)["bio"]
    else:
        return {
            "answer": "I can answer questions about languages, top projects, consistency, popularity and job fit.",
            "suggestions": SUGGESTIONS,
        }
    return {"answer": text, "suggestions": SUGGESTIONS}
