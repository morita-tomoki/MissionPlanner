# MissionCtl — Claude operating contract

You are the primary developer of this project, working mostly **alone** over a
**long horizon**. Your memory resets between sessions. This repo's `docs/` ledger
is your externalized memory. Trust it, and keep it current.

## Read this first, every session (the `/start-session` ritual)

1. Read `docs/STATUS.md` — this is "you are here" and the single next action.
2. Run `make check` — confirm the baseline is **green**. If it is red, fixing it
   is the highest priority before anything else.
3. Open `docs/ROADMAP.md`, pick the next unchecked vertical slice.
4. Before touching code, skim `docs/DISCOVERIES.md` for relevant gotchas.

## Architectural invariants (CI enforces these — do not violate)

- **`missionctl.core` must never import Qt** (PySide6 / qasync / `missionctl.qt`).
  Enforced by import-linter. The core is headless and testable without a display.
- **No synchronous blocking APIs.** Everything I/O is `async`. Never wrap async in
  `.result()` / `run_until_complete()` to fake a sync call. (This was a top cause
  of freezes in the legacy code.)
- **One vehicle = one asyncio task (actor) with a private inbox.** No shared mutable
  state between vehicles, no locks. Multi-vehicle is the default.
- **State is immutable, `@dataclass(frozen=True, slots=True)`, in SI units only.**
  Unit conversion, speech, and UI banners belong in `missionctl.qt`, never in core.
- **`pymavlink` is a codec only** — parse/pack bytes. It must not own any socket
  or serial handle. Transport lives behind `missionctl.core.link`.
- **Every behavioural change ships with a test** that runs headless (tlog replay
  or SITL). If you cannot test it headlessly, say so in the PR and in QUESTIONS.

## Layer dependency direction (low → high; never import upward)

`link → codec → state → protocols → router → vehicle → fleet → qt`

## Commands (stable names — skills and CI depend on them)

- `make check` — lint + typecheck + import contracts + tests (the gate)
- `make test` / `make typecheck` / `make lint` / `make contracts`
- `make sitl` — SITL smoke scenario (see `/run-sitl`)
- `make run` — launch the GUI (needs `uv sync --extra gui`)

## Working discipline

- **One vertical slice per session.** Small enough to fit context, end-to-end,
  with a test, leaving `main` green. If a slice is too big, split it and record
  the split in `docs/STATUS.md`.
- Conventional Commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- Keep files small and cohesive. Never recreate the 6900-line god-class — one
  protocol per file, one concern per module.

## When to stop and ask vs. proceed

- Proceed on anything reversible and within the established architecture.
- If a decision is **ambiguous, irreversible, or changes the architecture**,
  append it to `docs/QUESTIONS.md`, pick a different slice, and keep moving.
  Do not block the whole project waiting for an answer.

## The `/end-session` ritual (mandatory before you stop)

1. `make check` is green (never end a session red).
2. Update `docs/STATUS.md` (Done / Now / Next single action).
3. Append a dated entry to `docs/JOURNAL.md` (what, why, next).
4. New gotcha → `docs/DISCOVERIES.md`; new decision → new ADR in `docs/decisions/`.
5. Commit (and open/refresh a PR if the slice is complete).
