"""Render a review as Markdown or JSON."""

from __future__ import annotations

import json

from .review import Review

CATEGORY_TITLES = {
    "sections": "Required sections",
    "timings": "Detection / response / resolution times",
    "blameless": "Blameless language",
    "action_items": "Action items",
}


def to_json(reviews: dict[str, Review], min_score: int) -> str:
    payload = [
        {"file": name, "passed": review.score >= min_score, "min_score": min_score,
         **review.to_dict()}
        for name, review in reviews.items()
    ]
    return json.dumps(payload, indent=2)


def to_markdown(name: str, review: Review, min_score: int) -> str:
    verdict = "PASS" if review.score >= min_score else "FAIL"
    out = [
        f"# Postmortem review: {name}",
        "",
        f"**Score: {review.score}/100** ({verdict}, minimum {min_score})",
        "",
        "| Category | Score |",
        "| --- | --- |",
    ]
    for key, title in CATEGORY_TITLES.items():
        part = review.breakdown[key]
        out.append(f"| {title} | {part['earned']}/{part['possible']} |")
    out.append("")

    if not review.findings:
        out.append("No issues found.")
    for key, title in CATEGORY_TITLES.items():
        findings = [f for f in review.findings if f.category == key]
        if not findings:
            continue
        out += [f"## {title}", ""]
        for finding in findings:
            where = f"line {finding.line}: " if finding.line else ""
            out.append(f"- {where}{finding.message}")
        out.append("")
    if review.suggestions:
        out += ["## Suggestions", ""] + [f"- {s}" for s in review.suggestions] + [""]
    return "\n".join(out).rstrip() + "\n"
