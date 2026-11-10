"""Optional hook for extra, non-scoring suggestions.

The linter is fully rule-based. An ``Advisor`` lets you plug in anything that
can read the postmortem and the findings and return extra free-text advice
(a language model, an internal style guide checker, ...). No advisor is used
unless you pass one to ``review_text``; nothing in this package calls a network.
"""

from __future__ import annotations

from typing import Protocol

from .review import Finding


class Advisor(Protocol):
    def suggest(self, text: str, findings: list[Finding]) -> list[str]:
        """Return extra suggestions for the author. Must not raise on empty input."""
        ...
