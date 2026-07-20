---
name: end-session
description: Close a MissionCtl development session cleanly — verify green, update the docs ledger (STATUS, JOURNAL, DISCOVERIES, ADRs), and commit. Use before you stop working on this project, every time.
---

# End session

Never end a session on a red baseline or with stale docs. Do all steps.

1. **Verify green.**
   ```bash
   make check
   ```
   Must pass. If it can't, either finish the fix or revert the incomplete change so
   `main`/the branch stays green, and record the situation in STATUS + JOURNAL.

2. **Update `docs/STATUS.md`** — keep it tiny:
   - `Done`: what this session completed.
   - `Now`: anything left in progress (or "nothing").
   - `Next single action`: the one concrete next step for the following session.

3. **Append to `docs/JOURNAL.md`** — a dated entry at the top: what changed, why,
   and what's next. Short.

4. **Capture knowledge:**
   - New gotcha / fact learned the hard way → add to `docs/DISCOVERIES.md`.
   - New decision with trade-offs → create the next-numbered ADR in
     `docs/decisions/` (use the `record-decision` skill).
   - Blocking ambiguity → add to `docs/QUESTIONS.md` and pick another slice.

5. **Update the roadmap.** Tick the slice's box in `docs/ROADMAP.md` if merged+green.

6. **Commit** with a Conventional Commit message. If the slice is complete, open or
   refresh the PR. Confirm the tree is clean (`git status`).
