---
name: record-decision
description: Create a new Architecture Decision Record (ADR) in docs/decisions. Use when you make a design choice with real trade-offs or one that shapes the architecture, so future sessions don't re-litigate it.
---

# Record an architecture decision

1. Find the next number: list `docs/decisions/` and take `max + 1`, zero-padded to
   four digits.

2. Create `docs/decisions/NNNN-<kebab-title>.md` with this template:
   ```markdown
   # N. <Title>

   ## Status
   Accepted — <YYYY-MM-DD>   (or: Proposed / Superseded by ADR-XXXX)

   ## Context
   The forces at play — the problem, constraints, what made this a real decision.

   ## Decision
   What we chose, stated plainly.

   ## Consequences
   What becomes easier, and what we accept as the cost (be honest about trade-offs).

   ## Rejected alternatives
   What else was considered and why it lost.
   ```

3. ADRs are **immutable once accepted.** To change a decision, write a new ADR and
   mark the old one `Superseded by ADR-XXXX` — do not edit history.

4. Reference the ADR number from code comments / other docs where relevant, and
   note it in the JOURNAL entry.

Use this for decisions with trade-offs. Transient facts go in DISCOVERIES.md;
unresolved choices go in QUESTIONS.md.
