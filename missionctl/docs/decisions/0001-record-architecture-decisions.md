# 1. Record architecture decisions

## Status
Accepted — 2026-07-20

## Context
This project is developed over a long horizon by an agent whose memory resets each
session, plus a solo human. Decisions must survive the people (and sessions) that
made them, or they get silently re-litigated and reversed.

## Decision
Use lightweight Architecture Decision Records (ADRs). One file per decision,
numbered, immutable once accepted (supersede rather than edit). Format:
Status / Context / Decision / Consequences / (Rejected alternatives).

Record a decision as an ADR when it has real trade-offs or shapes the architecture.
Transient gotchas go in `DISCOVERIES.md`; open questions go in `QUESTIONS.md`.

## Consequences
- A new session can read `docs/decisions/` and understand *why* the code is the way
  it is, not just *what* it is.
- Small overhead per decision, paid back the first time it prevents a reversal.
