import io
import json
from pathlib import Path

from incident_review_copilot.cli import main

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "postmortems"
WEAK = str(EXAMPLES / "2026-11-01-api-outage.md")
STRONG = str(EXAMPLES / "2026-10-12-queue-backlog.md")


def test_weak_example_fails_with_exit_code_1(capsys):
    assert main(["review", WEAK]) == 1
    out = capsys.readouterr().out
    assert "(FAIL, minimum 70)" in out
    assert "Missing required section: Lessons learned" in out
    assert 'line 21: Blame language "human error"' in out


def test_strong_example_passes(capsys):
    assert main(["review", STRONG]) == 0
    out = capsys.readouterr().out
    assert "**Score: 100/100** (PASS, minimum 70)" in out
    assert "No issues found." in out


def test_min_score_changes_the_exit_code(capsys):
    assert main(["review", WEAK, "--min-score", "10"]) == 0
    assert main(["review", STRONG, "--min-score", "101"]) == 1
    capsys.readouterr()


def test_json_output_for_multiple_files(capsys):
    assert main(["review", WEAK, STRONG, "--format", "json"]) == 1
    data = json.loads(capsys.readouterr().out)
    assert [d["file"] for d in data] == [WEAK, STRONG]
    assert [d["passed"] for d in data] == [False, True]
    assert data[0]["score"] == sum(c["earned"] for c in data[0]["breakdown"].values())
    assert {"category", "message", "line"} == set(data[0]["findings"][0])


def test_stdin(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO(Path(STRONG).read_text()))
    assert main(["review", "-"]) == 0
    assert "# Postmortem review: <stdin>" in capsys.readouterr().out


def test_missing_file_exits_2(capsys):
    assert main(["review", "does-not-exist.md"]) == 2
    assert "cannot read does-not-exist.md" in capsys.readouterr().err
