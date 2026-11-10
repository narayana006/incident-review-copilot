# incident-review-copilot

A linter for Markdown postmortems: it scores each document against a fixed rubric and lists the specific things to fix (missing timings, blame language, vague or unowned action items).

**Status:** early but usable (v0.1.0). The rubric score, required-section check, detection / response / resolution time check, blame-language check and action-item checks all work today from the command line. The packaged GitHub Action is not built yet.

## Why

Postmortems vary wildly in quality, and weak ones tend to precede a repeat of the same incident. This tool gives reviewers a consistent first pass, so review time goes on the analysis rather than on "who owns this action item?".

## Install

Requires Python 3.10 or newer. No runtime dependencies.

```bash
git clone https://github.com/narayana006/incident-review-copilot.git
cd incident-review-copilot
pip install .
```

## Quick start

The repository ships two sample postmortems. The weak one:

```bash
incident-review-copilot review examples/postmortems/2026-11-01-api-outage.md
```

Output (exit status 1, because the score is below the default minimum of 70):

```markdown
# Postmortem review: examples/postmortems/2026-11-01-api-outage.md

**Score: 46/100** (FAIL, minimum 70)

| Category | Score |
| --- | --- |
| Required sections | 25/30 |
| Detection / response / resolution times | 7/20 |
| Blameless language | 0/15 |
| Action items | 14/35 |

## Required sections

- Missing required section: Lessons learned

## Detection / response / resolution times

- No detection time found: add a timeline entry or duration that says when detection happened
- No response time found: add a timeline entry or duration that says when response happened

## Blameless language

- line 21: Blame language "human error": describe what the system allowed and why the action made sense at the time
- line 21: Blame language "should have checked": hindsight judgement; ask what would have made the right action easy
- line 22: Blame language "forgot to": say what was missing (checklist, guard rail, alert) rather than who omitted it

## Action items

- line 26: Vague action item "Improve monitoring": only 2 words; say what will change
- line 26: Action item has no owner: "Improve monitoring"
- line 26: Action item has no due date: "Improve monitoring"
- line 27: Vague action item "Be more careful with load balancer changes": "be more careful" has no verifiable outcome
- line 27: Action item has no due date: "Be more careful with load balancer changes"
- line 29: Vague action item "Look into canary deploys for edge config": "look into" has no verifiable outcome
- line 29: Action item has no owner: "Look into canary deploys for edge config"
- line 29: Action item has no due date: "Look into canary deploys for edge config"
```

The other sample, `examples/postmortems/2026-10-12-queue-backlog.md`, scores 100/100 and exits 0.

## Usage

```text
incident-review-copilot review [--format {markdown,json}] [--min-score N] FILE [FILE ...]
```

- `FILE` is a Markdown postmortem. Pass several files to review them in one run, or `-` to read from stdin.
- `--format json` prints a JSON array with one object per file: `file`, `passed`, `min_score`, `score`, `breakdown`, `findings` (category, message, line) and the parsed `action_items` (text, owner, due, vague_reason).
- `--min-score N` sets the pass mark (default 70).

Exit status: `0` when every file meets the minimum score, `1` when any file falls below it, `2` when a file cannot be read or the arguments are invalid. That makes it usable as a CI step or pre-commit check as it is.

## What is checked

The score is out of 100.

| Category | Points | How it is scored |
| --- | --- | --- |
| Required sections | 30 | Summary, Impact, Timeline, Root cause, Lessons learned, Action items. Each must exist as a heading and have content. Common alternatives are accepted, for example "Contributing factors" for root cause, "What went well" for lessons learned, "Follow-ups" for action items. |
| Timings | 20 | Detection, response and resolution each need at least one line that mentions the milestone (for example "alert fired", "acknowledged", "resolved") together with a clock time, ISO timestamp or duration. |
| Blameless language | 15 | 5 points lost per finding. Flags phrases such as "human error", "should have checked", "forgot to", "careless", "X's fault". |
| Action items | 35 | 5 for having any; then 10 each, pro rata, for items that are specific, have an owner, and have a due date. |

Action items are read from the action-items section, either as a list or as a table:

```markdown
- Add a CI step that runs `lb-validate` on every config pull request. Owner: @sam, due 2026-11-15
```

```markdown
| Action | Owner | Due |
| --- | --- | --- |
| Alert when the autoscaler has received no metric data for 5 minutes | @marcus | 2026-10-23 |
```

An owner is an `@handle`, an `Owner:` / `Assignee:` / `DRI:` annotation, "assigned to ...", or an Owner/Assignee column. A due date is a date such as `2026-11-15`, `Nov 15` or `15/11/2026`, or a Due/Deadline/ETA column. Placeholders such as `TBD` count as missing. An item is vague when it has fewer than four words, uses a phrase with no verifiable outcome ("look into", "be more careful", "improve monitoring"), or is a short weak-verb item ("Review the cache configuration") with no number, ticket reference or code reference in it.

Text inside fenced code blocks is ignored by every check.

### Use as a library

```python
from incident_review_copilot import review_text

review = review_text(open("postmortem.md").read())
print(review.score, [f.message for f in review.findings])
```

`review_text` also accepts an optional `advisor` object with a `suggest(text, findings)` method that returns extra free-text suggestions (see `src/incident_review_copilot/advisor.py`). It is off by default, the package ships no implementation of it, and it never changes the score.

## Features

- [x] Rubric score for each postmortem
- [x] Detects missing detection / response / resolution times
- [x] Flags blame language
- [x] Flags vague action items and missing owners or due dates
- [x] Markdown and JSON output, exit status for CI
- [ ] GitHub Action that reviews postmortem PRs

## Limitations

- The checks are keyword and pattern based. They do not understand the incident: a postmortem can score 100 and still have a wrong root cause.
- English only.
- Blame detection is a phrase list. It will miss blame phrased in other ways and can flag an innocent sentence such as "the health check failed to connect"; treat findings as prompts for the reviewer.
- A timing counts only if the milestone word and the time are on the same line. Whether the times are plausible or in order is not checked.
- Section names and the rubric weights are fixed in `src/incident_review_copilot/review.py`; there is no configuration file yet.
- Only Markdown input is supported (no Google Docs, Confluence or PDF).

## Related

- [ai-incident-management-companion](https://github.com/narayana006/ai-incident-management-companion)

## Contributing

Issues and pull requests are welcome, especially real-world phrasing that the checks miss or flag wrongly. To work on the code:

```bash
pip install -e ".[dev]"
pytest
```

## Author

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
