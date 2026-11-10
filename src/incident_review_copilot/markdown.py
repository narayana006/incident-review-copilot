"""Minimal Markdown parsing: just enough structure to lint a postmortem.

We only need headings, list items and pipe tables, so a full Markdown parser
would be overkill. Fenced code blocks are skipped so that sample commands and
log excerpts are never mistaken for prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LIST_ITEM_RE = re.compile(r"^(\s*)(?:[-*+]|\d+[.)])\s+(.*)$")
CHECKBOX_RE = re.compile(r"^\[[ xX]\]\s*")
TABLE_DIVIDER_RE = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


@dataclass
class Line:
    number: int  # 1-based line number in the source document
    text: str


@dataclass
class Section:
    title: str
    level: int
    line: int
    lines: list[Line] = field(default_factory=list)

    @property
    def body(self) -> str:
        return "\n".join(l.text for l in self.lines).strip()


def prose_lines(text: str) -> list[Line]:
    """Return every line outside fenced code blocks, with its line number."""
    out: list[Line] = []
    in_fence = False
    for number, raw in enumerate(text.splitlines(), start=1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if not in_fence:
            out.append(Line(number, raw))
    return out


def split_sections(text: str) -> list[Section]:
    """Split a document into sections, one per heading of any level."""
    sections: list[Section] = []
    current: Section | None = None
    for line in prose_lines(text):
        match = HEADING_RE.match(line.text)
        if match:
            current = Section(match.group(2).strip(), len(match.group(1)), line.number)
            sections.append(current)
        elif current is not None:
            current.lines.append(line)
    return sections


def section_with_children(sections: list[Section], index: int) -> list[Line]:
    """Lines of a section plus any deeper-level subsections that follow it."""
    parent = sections[index]
    lines = list(parent.lines)
    for child in sections[index + 1:]:
        if child.level <= parent.level:
            break
        lines.extend(child.lines)
    return lines


def split_table_row(text: str) -> list[str]:
    row = text.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


@dataclass
class ListItem:
    line: int
    text: str


def list_items(lines: list[Line]) -> list[ListItem]:
    """Top-level list items; indented continuation and sub-bullets are folded in."""
    items: list[ListItem] = []
    base_indent: int | None = None
    for line in lines:
        match = LIST_ITEM_RE.match(line.text)
        if match:
            indent = len(match.group(1).expandtabs(4))
            if base_indent is None or indent <= base_indent:
                base_indent = indent
                items.append(ListItem(line.number, CHECKBOX_RE.sub("", match.group(2)).strip()))
                continue
            items[-1].text += " " + CHECKBOX_RE.sub("", match.group(2)).strip()
        elif items and line.text.strip() and line.text[:1] in (" ", "\t"):
            items[-1].text += " " + line.text.strip()
        elif not line.text.strip():
            continue
        else:
            base_indent = None  # a paragraph ends the list
    return items


@dataclass
class TableRow:
    line: int
    cells: dict[str, str]  # lower-cased header -> cell text


def table_rows(lines: list[Line]) -> list[TableRow]:
    """Rows of every pipe table in ``lines``, keyed by lower-cased header."""
    rows: list[TableRow] = []
    header: list[str] | None = None
    previous: Line | None = None
    for line in lines:
        if "|" not in line.text:
            header, previous = None, None
            continue
        if TABLE_DIVIDER_RE.match(line.text) and previous is not None:
            header = [h.lower() for h in split_table_row(previous.text)]
        elif header is not None:
            cells = split_table_row(line.text)
            cells += [""] * (len(header) - len(cells))
            rows.append(TableRow(line.number, dict(zip(header, cells))))
        previous = line
    return rows
