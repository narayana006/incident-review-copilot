import textwrap

import pytest

from incident_review_copilot.markdown import list_items, prose_lines, split_sections, table_rows
from incident_review_copilot.review import (
    POINTS,
    Finding,
    parse_action_items,
    review_text,
    vague_reason,
)

GOOD = textwrap.dedent("""\
    # Postmortem: cache outage

    ## Summary
    Cache cluster ran out of memory.

    ## Impact
    Page loads were slow for 20 minutes.

    ## Timeline
    - 10:00 Memory alert fired, on-call paged
    - 10:03 On-call acknowledged the page
    - 10:20 Incident resolved after eviction policy change

    ## Root cause
    The eviction policy was set to noeviction.

    ## Lessons learned
    The alert threshold left too little headroom.

    ## Action items
    - Set eviction policy to allkeys-lru in the cache module. Owner: @lee, due 2026-12-01
    - Lower the memory alert threshold from 95% to 80% (owner: @kim, due: 2026-11-20)
    """)


def messages(review, category):
    return [f.message for f in review.findings if f.category == category]


def test_good_postmortem_scores_full_marks():
    review = review_text(GOOD)
    assert review.findings == []
    assert review.score == 100
    assert sum(POINTS.values()) == 100


def test_empty_document_scores_only_blameless_points():
    review = review_text("")
    assert review.score == POINTS["blameless"]
    assert len(messages(review, "sections")) == 6
    assert len(messages(review, "timings")) == 3
    assert messages(review, "action_items") == ["No action items found"]


def test_missing_and_empty_sections():
    text = GOOD.replace("## Impact\nPage loads were slow for 20 minutes.\n", "## Impact\n")
    text = text.replace("## Lessons learned\nThe alert threshold left too little headroom.\n", "")
    review = review_text(text)
    assert messages(review, "sections") == [
        "Section is empty: Impact", "Missing required section: Lessons learned"]
    assert review.breakdown["sections"]["earned"] == 20


def test_section_aliases_and_subsections_count():
    text = GOOD.replace("## Root cause", "## Contributing factors")
    text = text.replace("## Lessons learned\nThe alert threshold left too little headroom.",
                        "## Lessons\n### What went well\nRollback was quick.")
    assert messages(review_text(text), "sections") == []


@pytest.mark.parametrize("line, missing", [
    ("- 10:00 Memory alert fired, on-call paged\n", "detection"),
    ("- 10:03 On-call acknowledged the page\n", "response"),
    ("- 10:20 Incident resolved after eviction policy change\n", "resolution"),
])
def test_each_missing_timing_is_reported(line, missing):
    review = review_text(GOOD.replace(line, ""))
    found = messages(review, "timings")
    assert len(found) == 1 and found[0].startswith(f"No {missing} time found")
    assert review.breakdown["timings"]["earned"] == 13


def test_timing_keyword_without_a_time_does_not_count():
    text = GOOD.replace("- 10:20 Incident resolved after", "- Incident resolved after")
    assert len(messages(review_text(text), "timings")) == 1


def test_durations_count_as_timings():
    text = GOOD.replace("- 10:00 Memory alert fired, on-call paged", "Time to detect: 4 minutes")
    assert messages(review_text(text), "timings") == []


def test_blame_language_is_flagged_with_line_numbers():
    text = GOOD.replace("The eviction policy was set to noeviction.",
                        "Operator error: the engineer forgot to set a policy.\nIt was Bob's fault.")
    review = review_text(text)
    blame = [f for f in review.findings if f.category == "blameless"]
    assert [f.line for f in blame] == [15, 15, 16]
    assert '"Operator error"' in blame[0].message
    assert review.breakdown["blameless"]["earned"] == 0


def test_blameless_wording_and_code_blocks_are_not_flagged():
    text = GOOD.replace(
        "The eviction policy was set to noeviction.",
        "We run blameless reviews. The health check failed to connect.\n"
        "```\nERROR human error: forgot to set policy\n```")
    assert messages(review_text(text), "blameless") == ["Blame language \"failed to\": say what was "
                                                        "missing (checklist, guard rail, alert) rather than who omitted it"]


@pytest.mark.parametrize("text", [
    "Improve monitoring",
    "Look into why the cache filled up so quickly",
    "Be more careful when changing cache settings",
    "Review the cache configuration",
    "Add more tests for the cache layer",
])
def test_vague_action_items(text):
    assert vague_reason(text) is not None


@pytest.mark.parametrize("text", [
    "Set eviction policy to allkeys-lru in the cache module",
    "Review the 3 cache alerts",
    "Fix OPS-1432 in the deploy pipeline",
    "Add a pre-deploy check that rejects configs without a health-check path",
])
def test_specific_action_items(text):
    assert vague_reason(text) is None


def test_list_action_items_owner_and_due_detection():
    sections = split_sections(textwrap.dedent("""\
        ## Action items
        - [ ] Rotate the leaked deploy key in all regions @ops-team by 2026-12-01
        - [x] Add a dashboard panel for queue depth per region. Owner: TBD
        * Replace the cron job by a queue consumer in the billing service (Assignee: Ana Li)
          Due: Dec 5
        """))
    items = parse_action_items(sections[0].lines)
    assert [(i.owner, i.due) for i in items] == [
        ("@ops-team", "2026-12-01"), (None, None), ("Ana Li", "Dec 5")]
    assert items[2].text.startswith("Replace the cron job by a queue consumer in the billing service")
    assert all(i.vague_reason is None for i in items)


def test_table_action_items_and_placeholders():
    text = GOOD.split("## Action items")[0] + textwrap.dedent("""\
        ## Action items
        | Action | Owner | Due date |
        |---|---|---|
        | Set eviction policy to allkeys-lru in the cache module | Lee | 2026-12-01 |
        | Improve alerting | TBD | |
        """)
    review = review_text(text)
    assert [(i.owner, i.due) for i in review.action_items] == [("Lee", "2026-12-01"), (None, None)]
    assert len(messages(review, "action_items")) == 3
    # 5 for having items + half of each of the three 10-point parts
    assert review.breakdown["action_items"]["earned"] == 20


def test_markdown_helpers():
    text = "# A\ntext\n```\n# not a heading\n```\n## B\n- one\n  - nested\n- two\n\n| h1 | h2 |\n| --- | --- |\n| a | b |\n"
    sections = split_sections(text)
    assert [(s.title, s.level) for s in sections] == [("A", 1), ("B", 2)]
    assert all("not a heading" not in l.text for l in prose_lines(text))
    assert [i.text for i in list_items(sections[1].lines)] == ["one nested", "two"]
    assert table_rows(sections[1].lines)[0].cells == {"h1": "a", "h2": "b"}


def test_advisor_adds_suggestions_without_changing_score():
    class FakeAdvisor:
        def __init__(self):
            self.calls = []

        def suggest(self, text, findings):
            self.calls.append((text, findings))
            return [f"{len(findings)} findings to discuss in the review meeting"]

    advisor = FakeAdvisor()
    text = GOOD.replace("Owner: @lee, due 2026-12-01", "")
    plain, advised = review_text(text), review_text(text, advisor=advisor)
    assert advised.score == plain.score
    assert advised.suggestions == ["2 findings to discuss in the review meeting"]
    assert all(isinstance(f, Finding) for f in advisor.calls[0][1])
    assert plain.suggestions == []
