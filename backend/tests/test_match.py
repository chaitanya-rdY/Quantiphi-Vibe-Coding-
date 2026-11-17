from backend.app.services.match import compute_match, extract_required_languages

REPOS = [
    {"language": "Python", "is_fork": False},
    {"language": "Python", "is_fork": False},
    {"language": "JavaScript", "is_fork": False},
    {"language": "Rust", "is_fork": True},
]


def test_direct_and_implied_languages():
    req = extract_required_languages("We use Python, Django and React. Experience with Go preferred.")
    assert req["Python"] == 2 and req["JavaScript"] == 1 and req["Go"] == 1


def test_english_go_not_counted():
    assert "Go" not in extract_required_languages("We go to market fast and let you go home early")


def test_match_percentage_and_gaps():
    m = compute_match("Python Python Java", REPOS)
    assert m["percent"] == 66.7 and m["label"] == "Good Match"
    assert [x["language"] for x in m["missing"]] == ["Java"]


def test_forks_ignored_and_no_langs():
    assert compute_match("Rust engineer", REPOS)["percent"] == 0.0
    assert compute_match("Great communicator", REPOS)["percent"] is None
