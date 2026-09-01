# incident-review-copilot

Score and review postmortems: flags missing timings, blame language, vague or unowned action items.

> **Project status: planning. There is no working code in this repository yet.**
> This README describes what the project will do. Nothing below can be installed or run today.
> Features are ticked off in the checklist as they are built.

## What it is

A command-line tool and GitHub Action.

**The problem it solves:** Postmortems vary wildly in quality and weak ones repeat the same incident months later.

## Who it is for

SRE leads and reviewers who want every postmortem to meet the same bar.

## How it will work

1. You run the tool on a postmortem document, or let the GitHub Action run it on postmortem pull requests.
2. It checks for missing timings, blame language, vague action items and actions without an owner or due date.
3. It returns a score and a list of specific things to fix.

## Planned features

Unticked items are not built yet.

- [ ] Rubric score for each postmortem
- [ ] Detects missing detection / response / resolution times
- [ ] Flags blame language
- [ ] Flags vague action items and missing owners or due dates
- [ ] GitHub Action that reviews postmortem PRs

## Planned usage

This is the intended interface, shown so you can judge the design. **It does not work yet**, and names may change before the first release.

```bash
incident-review-copilot review postmortems/2026-11-01-api-outage.md
```

## Related

- [ai-incident-management-companion](https://github.com/narayana006/ai-incident-management-companion)

## Contributing

Feedback on the design is the most useful contribution right now. Open an issue to suggest a feature, question an approach or describe your use case. Code contributions are welcome once the first version lands.

## Author

Built and maintained by [Narayana Vemburaj](https://github.com/narayana006).

## License

[MIT](LICENSE)
