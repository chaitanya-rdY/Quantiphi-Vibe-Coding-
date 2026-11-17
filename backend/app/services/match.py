"""Tech Stack Compatibility: compare a job description against languages in cached repos.

Method (explainable, deterministic):
1. Extract programming languages the JD asks for - directly ("Python") or via well-known
   frameworks/tools that imply one ("Django" -> Python, "React" -> JavaScript).
2. Weight each required language by how often the JD mentions it.
3. Match % = weighted share of required languages the developer has used in their repos.
"""
from __future__ import annotations

import re
from collections import Counter

# canonical GitHub language name -> regex of case-insensitive aliases
LANGUAGE_ALIASES: dict[str, list[str]] = {
    "Python": [r"python", r"py3"],
    "JavaScript": [r"javascript", r"js", r"ecmascript", r"es6", r"node\.?js", r"nodejs"],
    "TypeScript": [r"typescript", r"ts"],
    "Java": [r"java"],
    "C++": [r"c\+\+", r"cpp"],
    "C#": [r"c#", r"csharp", r"\.net", r"dotnet"],
    "Go": [r"golang"],
    "Rust": [r"rust"],
    "Ruby": [r"ruby"],
    "PHP": [r"php"],
    "Swift": [r"swiftui"],
    "Kotlin": [r"kotlin"],
    "Scala": [r"scala"],
    "Shell": [r"bash", r"shell scripting", r"shell"],
    "HTML": [r"html5?"],
    "CSS": [r"css3?", r"sass", r"scss", r"tailwind"],
    "SQL": [r"sql", r"postgres(?:ql)?", r"mysql"],
    "Jupyter Notebook": [r"jupyter"],
    "Dart": [r"dart", r"flutter"],
    "MATLAB": [r"matlab"],
}

# frameworks / tools that imply a language
IMPLIED: dict[str, list[str]] = {
    "Python": [r"django", r"flask", r"fastapi", r"pandas", r"numpy", r"pytorch", r"tensorflow", r"scikit-learn", r"sklearn"],
    "JavaScript": [r"react(?:\.?js)?", r"vue(?:\.?js)?", r"angular", r"express(?:\.?js)?", r"next\.?js", r"jquery"],
    "Java": [r"spring(?: boot)?", r"hibernate", r"maven", r"jvm"],
    "Ruby": [r"rails", r"ruby on rails"],
    "PHP": [r"laravel", r"symfony"],
    "Kotlin": [r"android"],
    "Swift": [r"ios"],
    "C#": [r"asp\.net", r"unity"],
}

# ambiguous single letters / words matched case-sensitively on the original text
CASE_SENSITIVE: dict[str, str] = {
    "Go": r"(?<![\w.])Go(?![\w.])",
    "C": r"(?<![\w+#.])C(?![\w+#.])",
    "R": r"(?<![\w.])R(?![\w.])",
    "Swift": r"(?<![\w.])Swift(?![\w.])",
}

SOFT_ALIAS = {"HTML": "HTML", "CSS": "CSS"}


def _count(pattern: str, text: str, flags=re.IGNORECASE) -> int:
    return len(re.findall(rf"(?<![\w+#]){pattern}(?![\w+#])", text, flags))


def extract_required_languages(jd: str) -> Counter:
    """Return Counter(language -> weight) of languages the JD asks for."""
    found: Counter = Counter()
    for lang, aliases in LANGUAGE_ALIASES.items():
        n = sum(_count(a, jd) for a in aliases)
        if n:
            found[lang] += n
    for lang, aliases in IMPLIED.items():
        n = sum(_count(a, jd) for a in aliases)
        if n:
            found[lang] += n
    for lang, pattern in CASE_SENSITIVE.items():
        n = len(re.findall(pattern, jd))
        if n:
            found[lang] += n
    return found


def _label(percent: float) -> str:
    if percent >= 75:
        return "Strong Match"
    if percent >= 50:
        return "Good Match"
    if percent >= 25:
        return "Partial Match"
    return "Low Match"


def compute_match(job_description: str, repos: list[dict]) -> dict:
    required = extract_required_languages(job_description)
    user_langs = Counter(r["language"] for r in repos if r.get("language") and not r.get("is_fork"))

    if not required:
        return {
            "percent": None,
            "label": "No languages detected",
            "matched": [],
            "missing": [],
            "bonus": sorted(user_langs),
            "message": "No programming languages were found in the job description.",
        }

    total_weight = sum(required.values())
    matched_weight = sum(w for lang, w in required.items() if lang in user_langs)
    percent = round(matched_weight * 100 / total_weight, 1)

    return {
        "percent": percent,
        "label": _label(percent),
        "matched": [
            {"language": l, "jd_mentions": required[l], "your_repos": user_langs[l]}
            for l in sorted(required, key=required.get, reverse=True)
            if l in user_langs
        ],
        "missing": [
            {"language": l, "jd_mentions": required[l]}
            for l in sorted(required, key=required.get, reverse=True)
            if l not in user_langs
        ],
        "bonus": sorted(l for l in user_langs if l not in required),
        "message": None,
    }
