---
description: 'Create an Architectural Decision Record (ADR) to document a significant technical decision'
---

# Create Architectural Decision Record

Generate an ADR document for a technical decision using the standard ADR format.

## Instructions

1. If the decision title, context, or chosen approach is not clear from the conversation, ask before proceeding.
2. Create the ADR file at `docs/adr/adr-NNNN-<title-slug>.md`, where `NNNN` is the next sequential number.
3. Follow the template below exactly. Fill in every section with clear, unambiguous language.

## ADR Template

```markdown
---
title: "ADR-NNNN: <Decision Title>"
status: "Proposed"
date: "<YYYY-MM-DD>"
authors: "<author names or roles>"
tags: ["architecture", "decision"]
supersedes: ""
superseded_by: ""
---

# ADR-NNNN: <Decision Title>

## Status

**Proposed** | Accepted | Rejected | Superseded | Deprecated

## Context

<Problem statement, technical constraints, business requirements, and environmental
factors that make this decision necessary. Be specific about what forces are at play.>

## Decision

<The chosen solution and the rationale for selecting it over the alternatives.>

## Consequences

### Positive

- <Beneficial outcome or advantage>
- <Performance, maintainability, or scalability improvement>
- <Alignment with architectural principles or team goals>

### Negative

- <Trade-off, limitation, or drawback>
- <Technical debt or added complexity>
- <Risk or future challenge>

## Alternatives Considered

### <Alternative 1 Name>

- **Description**: <Brief technical description>
- **Rejection Reason**: <Why this was not selected>

### <Alternative 2 Name>

- **Description**: <Brief technical description>
- **Rejection Reason**: <Why this was not selected>

## Implementation Notes

- <Key implementation considerations>
- <Migration or rollout strategy, if applicable>
- <Monitoring and success criteria>

## References

- <Related ADRs, external docs, or standards referenced>
```

## Quality Checklist

Before finalizing the ADR, verify:

- [ ] Title clearly identifies the decision
- [ ] Context explains **why** this decision is needed
- [ ] Decision states **what** was chosen and **why**
- [ ] At least two alternatives are documented with rejection reasons
- [ ] Both positive and negative consequences are listed
- [ ] Implementation notes are actionable
- [ ] Status is set to "Proposed" (author will change later)
