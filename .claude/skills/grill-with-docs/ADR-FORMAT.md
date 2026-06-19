# ADR Format

ADRs live in `docs/adr/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, etc.

Create the `docs/adr/` directory lazily — only when the first ADR is needed.

This template is based on [MADR 4.0.0](https://adr.github.io/madr/).

## Template

```md
---
title: "[ADR-NNNN] [DECISION TITLE]"
type: adr
status: draft
author: "[AUTHOR NAME]"
date: YYYY-MM-DD
sidebar_label: ADR
tags:
  - adr
  - "[PROJECT_TAG]"
audience: "[TARGET AUDIENCE, e.g., engineering, architecture]"
---

# [ADR-NNNN] [DECISION TITLE]

## Context and Problem Statement

[Describe the architectural challenge, the forces at play, and why a decision is needed now. Use free-form text or the format: "In the context of [use case / component], facing [concern], we decided [direction] to achieve [quality / goal], accepting [downside]."]

## Decision Drivers

- [Driver 1, e.g., performance requirements]
- [Driver 2, e.g., team expertise]
- [Driver 3, e.g., time-to-market constraints]
- [Driver 4, e.g., long-term maintainability]

## Considered Options

1. [Option 1]
2. [Option 2]
3. [Option 3]

## Decision Outcome

**Chosen option:** "[Option N]", because [justification. Refer back to decision drivers to explain why this option best satisfies them.]

### Consequences

#### Positive

- [Positive consequence 1]
- [Positive consequence 2]

#### Negative

- [Negative consequence 1, with mitigation strategy if applicable]
- [Negative consequence 2]

#### Neutral

- [Neutral consequence, if any]

## Pros and Cons of the Options

### [Option 1]

[Brief description of Option 1 and how it addresses the problem.]

- **Pro:** [Advantage]
- **Con:** [Disadvantage]

### [Option 2]

[Brief description of Option 2 and how it addresses the problem.]

- **Pro:** [Advantage]
- **Con:** [Disadvantage]

### [Option 3]

[Brief description of Option 3 and how it addresses the problem.]

- **Pro:** [Advantage]
- **Con:** [Disadvantage]

## Links

- [Link type] [Link to ADR or resource]
  <!-- Example: Refined by [ADR-0005](0005-example.md) -->
  <!-- Example: Supersedes [ADR-0001](0001-example.md) -->

---

| Version | Date       | Author  | Changes                     |
|---------|------------|---------|-----------------------------|
| 0.1     | YYYY-MM-DD | [Name]  | Initial draft               |
```

## Frontmatter fields

- **title** — `[ADR-NNNN] [DECISION TITLE]`, where `NNNN` is the zero-padded sequential number.
- **type** — always `adr`.
- **status** — one of `draft | proposed | accepted | deprecated | superseded by ADR-NNNN`.
- **author** — person who drove the decision.
- **date** — ISO date (`YYYY-MM-DD`) of the decision or last status change.
- **tags** — always include `adr`; add a project tag for filtering.
- **audience** — intended readers (e.g., `engineering`, `architecture`).

## Sections — what each one is for

- **Context and Problem Statement** — what's the situation, what forces are at play, why decide now. The reader should understand the problem before seeing the answer.
- **Decision Drivers** — the criteria options are evaluated against. These are the levers that swung the decision.
- **Considered Options** — every real alternative. Including the rejected ones is the point — it stops "why didn't you just do X?" from being asked again in six months.
- **Decision Outcome** — the chosen option and the justification, tied back to the drivers.
- **Consequences** — positive, negative, and neutral. Be honest about the downsides; that's what makes the ADR trustworthy later.
- **Pros and Cons of the Options** — per-option analysis. Lets a future reader see the trade-off space, not just the winner.
- **Links** — related ADRs (refines, supersedes, related-to), issues, external resources.
- **Document History** — bumps the version on each material change to status or content.

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one. Use four-digit zero-padded form (`0001`, `0042`).

## When to offer an ADR

All three of these must be true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will look at the code and wonder "why on earth did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If a decision is easy to reverse, skip it — you'll just reverse it. If it's not surprising, nobody will wonder why. If there was no real alternative, there's nothing to record beyond "we did the obvious thing."

### What qualifies

- **Architectural shape.** "We're using a monorepo." "The write model is event-sourced, the read model is projected into Postgres."
- **Integration patterns between contexts.** "Ordering and Billing communicate via domain events, not synchronous HTTP."
- **Technology choices that carry lock-in.** Database, message bus, auth provider, deployment target. Not every library — just the ones that would take a quarter to swap out.
- **Boundary and scope decisions.** "Customer data is owned by the Customer context; other contexts reference it by ID only." The explicit no-s are as valuable as the yes-s.
- **Deliberate deviations from the obvious path.** "We're using manual SQL instead of an ORM because X." Anything where a reasonable reader would assume the opposite. These stop the next engineer from "fixing" something that was deliberate.
- **Constraints not visible in the code.** "We can't use AWS because of compliance requirements." "Response times must be under 200ms because of the partner API contract."
- **Rejected alternatives when the rejection is non-obvious.** If you considered GraphQL and picked REST for subtle reasons, record it — otherwise someone will suggest GraphQL again in six months.
