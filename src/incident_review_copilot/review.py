"""The postmortem checks and the rubric that turns them into a score."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from .markdown import (
    Line,
    Section,
    list_items,
    prose_lines,
    section_with_children,
    split_sections,
    table_rows,
)

# --- Rubric -----------------------------------------------------------------
# Points available per category. They add up to 100.
POINTS = {"sections": 30, "timings": 20, "blameless": 15, "action_items": 35}
BLAME_PENALTY = 5  # points lost per blame-language finding, down to zero

# Required sections and the heading words that satisfy each one.
REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "Summary": ("summary", "overview", "tl;dr"),
    "Impact": ("impact",),
    "Timeline": ("timeline", "chronology", "sequence of events"),
    "Root cause": ("root cause", "cause", "contributing factor", "what happened", "trigger"),
    "Lessons learned": ("lesson", "what went well", "what went wrong", "what went poorly",
                        "where we got lucky", "learning"),
    "Action items": ("action item", "action", "follow-up", "follow up", "followup",
                     "corrective", "remediation", "next steps"),
}

# A timing counts as present when one line mentions the milestone *and* a time.
TIMING_KEYWORDS: dict[str, re.Pattern[str]] = {
    "detection": re.compile(
        r"\b(detect\w*|alert\w* (fired|triggered)|paged|page fired|first report\w*|"
        r"time to detect\w*|ttd|mttd|noticed)\b", re.I),
    "response": re.compile(
        r"\b(acknowledg\w*|ack(ed|'d)?|respond\w*|response|engaged|began investigat\w*|"
        r"started investigat\w*|incident declared|time to (acknowledge|respond)|tta|mtta)\b",
        re.I),
    "resolution": re.compile(
        r"\b(resolv\w*|resolution|mitigat\w*|recover\w*|restored|rolled back|rollback (complete|finished)|all clear|"
        r"time to (resolve|recover|mitigate|restore)\w*|ttr|mttr)\b", re.I),
}
TIME_RE = re.compile(
    r"\b\d{1,2}:\d{2}(:\d{2})?\b"                      # 14:02, 14:02:33
    r"|\b\d{4}-\d{2}-\d{2}T\d{2}"                      # ISO timestamp
    r"|\b\d+(\.\d+)?\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|[smh])\b",  # 12 minutes
    re.I,
)

BLAME_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.I), advice)
    for pattern, advice in (
        (r"\b(human|operator|user|engineer|developer) error\b",
         "describe what the system allowed and why the action made sense at the time"),
        (r"\b(careless(ly|ness)?|negligen(t|ce)|incompeten(t|ce)|sloppy|lazy|reckless(ly)?|stupid(ly)?)\b",
         "remove the judgement and describe the conditions that led to the action"),
        (r"\bshould(n't| not)? have (known|caught|noticed|checked|tested|realis\w+|realiz\w+|been more careful)\b",
         "hindsight judgement; ask what would have made the right action easy"),
        (r"\b(forgot|neglected|failed|didn't bother|did not bother) to\b",
         "say what was missing (checklist, guard rail, alert) rather than who omitted it"),
        (r"\b(his|her|their|\w+'s) (fault|mistake)\b|\b(at fault|to blame|mistake by|fault of)\b",
         "attribute the failure to the system, not a person or team"),
        (r"\bblam(e|ed|es|ing) (on|the|him|her|them)\b",
         "attribute the failure to the system, not a person or team"),
    )
)

# Phrases that make an action item impossible to verify as done.
VAGUE_PHRASES = re.compile(
    r"\b(look into|think about|consider|explore|be more careful|pay (more )?attention|"
    r"try to|as needed|if possible|when possible|where possible|at some point|"
    r"better (monitoring|alerting|testing|documentation|communication|process)|"
    r"more (monitoring|alerting|testing|tests|documentation|training)|"
    r"improve (monitoring|alerting|testing|documentation|communication|process(es)?)|"
    r"raise awareness|keep an eye|follow up with|tbd)\b", re.I)
WEAK_VERBS = re.compile(r"^(improve|investigate|review|monitor|ensure|discuss|evaluate|"
                        r"revisit|update|fix|check|address|handle)\b", re.I)
CONCRETE_MARKER = re.compile(r"\d|`[^`]+`|\b[A-Z]{2,}-\d+\b|https?://")
MIN_ACTION_WORDS = 4
WEAK_VERB_MAX_WORDS = 7

MONTHS = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*"
DATE_RE = re.compile(
    rf"\b\d{{4}}-\d{{2}}-\d{{2}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b"
    rf"|\b{MONTHS}\.? \d{{1,2}}\b|\b\d{{1,2}} {MONTHS}\b|\b(Q[1-4]|end of (week|month|quarter|sprint))\b",
    re.I)
OWNER_INLINE_RE = re.compile(
    r"@[\w-]+(?:/[\w-]+)?|\b(?:(?:owners?|assignee|dri)\s*\**\s*[:=]|assigned to)\s*\**\s*(?P<who>[^,;|)\]*]+)",
    re.I)
DUE_INLINE_RE = re.compile(r"\b(?:due|deadline|eta|by|target)\b\s*(?:date)?\s*[:=-]?\s*\**\s*(?P<when>[^,;|)\]*]+)", re.I)
PLACEHOLDER_RE = re.compile(r"^\W*(tbd|tba|todo|n/?a|none|unknown|unassigned|someone|team|\?+|-+)?\W*$", re.I)

OWNER_COLUMNS = ("owner", "assignee", "dri", "who", "assigned to")
DUE_COLUMNS = ("due", "due date", "deadline", "eta", "when", "target date", "by")
ACTION_COLUMNS = ("action", "action item", "item", "description", "task", "what", "follow-up")


@dataclass
class Finding:
    category: str  # sections | timings | blameless | action_items
    message: str
    line: int | None = None


@dataclass
class ActionItem:
    line: int
    text: str
    owner: str | None
    due: str | None
    vague_reason: str | None


@dataclass
class Review:
    score: int
    breakdown: dict[str, dict[str, int]]
    findings: list[Finding] = field(default_factory=list)
    action_items: list[ActionItem] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _is_placeholder(value: str | None) -> bool:
    return value is None or bool(PLACEHOLDER_RE.match(value))


def _find_section(sections: list[Section], aliases: tuple[str, ...]) -> int | None:
    for index, section in enumerate(sections):
        title = section.title.lower()
        if any(alias in title for alias in aliases):
            return index
    return None


def check_sections(sections: list[Section]) -> tuple[list[Finding], int]:
    """Required sections must exist and contain something."""
    findings: list[Finding] = []
    present = 0
    for name, aliases in REQUIRED_SECTIONS.items():
        index = _find_section(sections, aliases)
        if index is None:
            findings.append(Finding("sections", f"Missing required section: {name}"))
        elif not any(l.text.strip() for l in section_with_children(sections, index)):
            findings.append(Finding("sections", f"Section is empty: {sections[index].title}",
                                    sections[index].line))
        else:
            present += 1
    return findings, round(POINTS["sections"] * present / len(REQUIRED_SECTIONS))


def check_timings(lines: list[Line]) -> tuple[list[Finding], int]:
    """Detection, response and resolution each need a line with a time on it."""
    findings: list[Finding] = []
    found = 0
    for name, keyword in TIMING_KEYWORDS.items():
        if any(keyword.search(l.text) and TIME_RE.search(l.text) for l in lines):
            found += 1
        else:
            findings.append(Finding(
                "timings",
                f"No {name} time found: add a timeline entry or duration that says when "
                f"{name} happened"))
    return findings, round(POINTS["timings"] * found / len(TIMING_KEYWORDS))


def check_blame(lines: list[Line]) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    for line in lines:
        for pattern, advice in BLAME_PATTERNS:
            match = pattern.search(line.text)
            if match:
                findings.append(Finding(
                    "blameless", f'Blame language "{match.group(0)}": {advice}', line.number))
    return findings, max(0, POINTS["blameless"] - BLAME_PENALTY * len(findings))


def vague_reason(text: str) -> str | None:
    """Why an action item is too vague to verify, or None if it is specific enough."""
    words = re.findall(r"[\w'-]+", text)
    if len(words) < MIN_ACTION_WORDS:
        return f"only {len(words)} word{'s' if len(words) != 1 else ''}; say what will change"
    match = VAGUE_PHRASES.search(text)
    if match:
        return f'"{match.group(0).lower()}" has no verifiable outcome'
    weak = WEAK_VERBS.match(text)
    if weak and len(words) <= WEAK_VERB_MAX_WORDS and not CONCRETE_MARKER.search(text):
        return f'"{weak.group(0).lower()}" without a concrete target or measure'
    return None


def _column(cells: dict[str, str], names: tuple[str, ...]) -> str | None:
    for name in names:
        if name in cells:
            return cells[name]
    return None


def _strip_metadata(text: str) -> str:
    """Remove owner/due annotations so they do not affect the vagueness check."""
    text = OWNER_INLINE_RE.sub("", text)
    text = DUE_INLINE_RE.sub(lambda m: "" if DATE_RE.search(m.group("when")) else m.group(0), text)
    text = DATE_RE.sub("", text)
    return re.sub(r"[\s(\[\-–—,;:.*_)\]]+$", "", re.sub(r"\(\W*\)|\[\W*\]", "", text)).strip()


def parse_action_items(lines: list[Line]) -> list[ActionItem]:
    """Action items from a pipe table if one exists, otherwise from list items."""
    items: list[ActionItem] = []
    for row in table_rows(lines):
        text = _column(row.cells, ACTION_COLUMNS)
        if text is None:  # no recognisable action column: use the widest cell
            text = max(row.cells.values(), key=len, default="")
        if not text.strip():
            continue
        owner = _column(row.cells, OWNER_COLUMNS)
        due = _column(row.cells, DUE_COLUMNS)
        items.append(ActionItem(
            row.line, text,
            None if _is_placeholder(owner) else owner,
            None if _is_placeholder(due) else due,
            vague_reason(text)))
    if items:
        return items

    for item in list_items(lines):
        owner = due = None
        owner_match = OWNER_INLINE_RE.search(item.text)
        if owner_match:
            who = owner_match.group("who") or owner_match.group(0)
            owner = None if _is_placeholder(who) else who.strip()
        due_match = DUE_INLINE_RE.search(item.text)
        if due_match and DATE_RE.search(due_match.group("when")):
            due = due_match.group("when").strip()
        elif DATE_RE.search(item.text):
            due = DATE_RE.search(item.text).group(0)
        description = _strip_metadata(item.text)
        items.append(ActionItem(item.line, description or item.text, owner, due,
                                vague_reason(description)))
    return items


def check_action_items(sections: list[Section]) -> tuple[list[Finding], int, list[ActionItem]]:
    """Score: 5 for having any, then 10 each for specificity, owners and due dates."""
    index = _find_section(sections, REQUIRED_SECTIONS["Action items"])
    items = parse_action_items(section_with_children(sections, index)) if index is not None else []
    if not items:
        line = sections[index].line if index is not None else None
        return [Finding("action_items", "No action items found", line)], 0, items

    findings: list[Finding] = []
    for item in items:
        label = item.text if len(item.text) <= 60 else item.text[:57] + "..."
        if item.vague_reason:
            findings.append(Finding("action_items", f'Vague action item "{label}": {item.vague_reason}', item.line))
        if not item.owner:
            findings.append(Finding("action_items", f'Action item has no owner: "{label}"', item.line))
        if not item.due:
            findings.append(Finding("action_items", f'Action item has no due date: "{label}"', item.line))

    total = len(items)
    specific = sum(1 for i in items if not i.vague_reason)
    owned = sum(1 for i in items if i.owner)
    dated = sum(1 for i in items if i.due)
    points = 5 + round(10 * specific / total) + round(10 * owned / total) + round(10 * dated / total)
    return findings, points, items


def review_text(text: str, advisor=None) -> Review:
    """Review a Markdown postmortem.

    ``advisor`` is an optional object with ``suggest(text, findings) -> list[str]``
    (see ``advisor.py``). It can add free-text suggestions but never changes the
    score, which is always computed by the deterministic checks above.
    """
    sections = split_sections(text)
    lines = prose_lines(text)

    section_findings, section_points = check_sections(sections)
    timing_findings, timing_points = check_timings(lines)
    blame_findings, blame_points = check_blame(lines)
    action_findings, action_points, items = check_action_items(sections)

    earned = {"sections": section_points, "timings": timing_points,
              "blameless": blame_points, "action_items": action_points}
    findings = section_findings + timing_findings + blame_findings + action_findings
    review = Review(
        score=sum(earned.values()),
        breakdown={name: {"earned": earned[name], "possible": POINTS[name]} for name in POINTS},
        findings=findings,
        action_items=items,
    )
    if advisor is not None:
        review.suggestions = list(advisor.suggest(text, findings))
    return review
