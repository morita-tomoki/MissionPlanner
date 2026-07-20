---
name: start-session
description: Begin a MissionCtl development session — restore context from the docs ledger, confirm the green baseline, and pick the next vertical slice. Use at the start of every working session on this project.
---

# Start session

Do these steps in order. Do not skip the baseline check.

1. **Restore context.** Read, in this order:
   - `docs/STATUS.md` — the single next action ("you are here").
   - `docs/ROADMAP.md` — the current milestone and its slices.
   - Skim `docs/QUESTIONS.md` for anything the human may have answered.

2. **Confirm the baseline is green.**
   ```bash
   make check
   ```
   - If green: proceed.
   - If red: **fixing it is the session's top priority.** Do not start new feature
     work on a red baseline. Diagnose, fix, re-run until green.

3. **Pick the next slice.** From `docs/ROADMAP.md`, take the first unchecked item
   under the active milestone (or continue the "Next single action" from STATUS).
   Make sure it is one vertical slice that fits this session and ships a test.

4. **Check for relevant gotchas.** Skim `docs/DISCOVERIES.md` headings that relate
   to the slice (e.g. pymavlink, SITL, tlog).

5. **Declare the plan** in one short paragraph, then create tasks for the slice
   with TaskCreate and begin. Mark the first task in_progress before coding.
