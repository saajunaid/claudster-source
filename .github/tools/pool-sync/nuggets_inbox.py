from __future__ import annotations

from dataclasses import dataclass
import re


DEFAULT_NUGGETS_HEADER = (
    "# Nugget Inbox\n\n"
    "> Auto-captured candidates from CI on prod deploy. These are raw candidates,\n"
    "> not live instruction updates. Run `junai pool nuggets review` to triage\n"
    "> keep-local, promote-to-pool, or discard decisions.\n\n"
)

_CANDIDATE_HEADER_RE = re.compile(
    r"^## CANDIDATE\s+(?P<date>\d{4}-\d{2}-\d{2})\s*(?:-|\u00b7)\s*(?P<version>.+?)\s*$"
)
_FIELD_RE = re.compile(r"^- (?P<key>[^:]+):\s*(?P<value>.*)$")


@dataclass
class NuggetCandidate:
    heading: str
    fields: list[tuple[str, str]]

    @property
    def date(self) -> str | None:
        match = _CANDIDATE_HEADER_RE.match(self.heading.strip())
        return match.group("date") if match else None

    @property
    def version(self) -> str | None:
        match = _CANDIDATE_HEADER_RE.match(self.heading.strip())
        return match.group("version").strip() if match else None

    def get(self, key: str) -> str | None:
        expected = key.strip().lower()
        for current_key, value in self.fields:
            if current_key.strip().lower() == expected:
                return value
        return None

    def set(self, key: str, value: str) -> None:
        expected = key.strip().lower()
        for index, (current_key, _) in enumerate(self.fields):
            if current_key.strip().lower() == expected:
                self.fields[index] = (current_key, value)
                return
        self.fields.append((key, value))

    def render(self) -> str:
        lines = [self.heading.rstrip()]
        lines.extend(f"- {key}: {value}".rstrip() for key, value in self.fields)
        return "\n".join(lines).rstrip() + "\n\n"


@dataclass
class NuggetsInbox:
    header: str
    candidates: list[NuggetCandidate]

    def render(self) -> str:
        header = self.header if self.header else DEFAULT_NUGGETS_HEADER
        if not header.endswith("\n\n"):
            header = header.rstrip("\n") + "\n\n"
        return header + "".join(candidate.render() for candidate in self.candidates)


def parse_nuggets_inbox(text: str) -> NuggetsInbox:
    normalized = text.replace("\r\n", "\n")
    if not normalized.strip():
        return NuggetsInbox(header=DEFAULT_NUGGETS_HEADER, candidates=[])

    matches = list(re.finditer(r"(?m)^## CANDIDATE .+$", normalized))
    if not matches:
        return NuggetsInbox(header=normalized, candidates=[])

    header = normalized[: matches[0].start()]
    candidates: list[NuggetCandidate] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        block = normalized[start:end].strip("\n")
        if not block:
            continue
        candidates.append(_parse_candidate_block(block))

    return NuggetsInbox(header=header or DEFAULT_NUGGETS_HEADER, candidates=candidates)


def _parse_candidate_block(block: str) -> NuggetCandidate:
    lines = block.split("\n")
    heading = lines[0].rstrip()
    fields: list[tuple[str, str]] = []
    for line in lines[1:]:
        match = _FIELD_RE.match(line.rstrip())
        if not match:
            continue
        fields.append((match.group("key").strip(), match.group("value").strip()))
    return NuggetCandidate(heading=heading, fields=fields)
