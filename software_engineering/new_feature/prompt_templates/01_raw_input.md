# Step 1 — Raw Input (Human)

This step is entirely manual — no agent involved.

## Procedure

1. **Create the `.current_session/` directory** for this pipeline run.
2. **Write `raw_prompt.md`** — your unstructured brain dump. Include everything: requirements, constraints, behaviors, edge cases, performance expectations, aesthetic preferences, things you're unsure about. Don't self-edit. Coherence is the next step's job.
3. **Save `raw_prompt.md` to `.current_session/`**.

That's it. The first agent (Step 2 — Spec Refiner) will initialize `index.md` and begin structured artifact tracking.
