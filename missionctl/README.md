# MissionCtl

A ground-up, multiplatform rewrite of the **command & control ("管制") layer** of
MissionPlanner — Python + Qt Quick (QML), built to be developed and maintained
primarily by Claude Code over a long horizon, by a solo engineer, on macOS.

## Why this exists

The legacy MissionPlanner C2 stack has three ~5–7k-line god-classes
(`MAVLinkInterface`, `CurrentState`, `MainV2`), a hand-rolled thread+lock model,
sync-over-async blocking calls, and ~2900 references to a single global static.
It is Windows/WinForms-bound and effectively untested. This project rebuilds only
the C2 core with a clean, testable, multi-vehicle-ready architecture.

## Design in one paragraph

A **pure-Python asyncio core that never imports Qt** (transport → codec → router →
per-vehicle actors → immutable SI-unit state), with a thin Qt/QML presentation layer
at the edge. Each vehicle is its own asyncio task (actor) with a private inbox, so
**multi-vehicle control is the default, not a bolt-on**. `pymavlink` is used as a
codec only (no I/O). See `docs/ARCHITECTURE.md`.

## Getting started (macOS)

```bash
uv sync --extra dev        # core + test tooling (no Qt needed to test)
make check                 # lint + typecheck + import contracts + tests
uv sync --extra gui        # add Qt when you want to run the app
make run
```

## For Claude Code

Read `CLAUDE.md` first — it is the operating contract. Every session starts by
reading `docs/STATUS.md` and running `make check`, and ends with the `/end-session`
skill. The docs ledger (`docs/`) is the project's externalized memory.
