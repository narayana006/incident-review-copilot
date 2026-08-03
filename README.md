# incident-review-copilot

> Score and review postmortems: flags missing timings, blame language, vague or unowned action items.

**Status:** 🚧 Early stage — design and roadmap published, implementation in progress. Stars, issues and ideas welcome.

## Why

Postmortems vary wildly in quality and weak ones repeat the same incident months later.

## Planned features

- [ ] Rubric score for each postmortem
- [ ] Detects missing detection / response / resolution times
- [ ] Flags blame language
- [ ] Flags vague action items and missing owners or due dates
- [ ] GitHub Action that reviews postmortem PRs

## Intended usage

```
incident-review-copilot review postmortems/2026-11-01-api-outage.md
```

_The interface above is the target design and may change._

## Roadmap

1. Core implementation of the first feature set
2. Examples and tests
3. CI and first tagged release
4. Docs and integrations

## Related

- [ai-incident-management-companion](https://github.com/narayana006/ai-incident-management-companion)

## Contributing

Contributions are welcome. Open an issue to discuss an idea or pick an unchecked item from the feature list.

## License

[MIT](LICENSE)
