# HOW TO MAKE MY AGENT ONE SHOT EVERYTHING Building a Feature: Agent-Orchestrated Development Pipeline

## Description
Files in `prompt_templates` dir contain description what should happen during this stage and prompt templates for agents at each stage.

## Philosophy

Architecture is the product; code is ephemeral. The durable engineering artifact is the specification — interface graphs, invariant declarations, contract test suites, module manifests. Implementations are regenerable from specs. Version control tracks *specification changes*; code is a derived artifact.

Each pipeline step is an **independent agent session** with its own instruction prompt, cleared context, and bounded scope. A human operator validates outputs and decides transitions. An orchestrator retrieves the appropriate step prompt and feeds it the artifacts produced by prior steps. In the current iteration, the human *is* the orchestrator. Future iterations will progressively replace human gating with agent-driven decisions, but that is out of scope here.

**Optionality Principle.** Every step self-assesses the appropriate depth of its output based on the feature's actual scope and complexity. A single-module refactor does not receive the same structural analysis as a cross-cutting architectural change. Downstream steps handle missing or reduced upstream artifacts gracefully — they work from what exists in `.current_session/`, not from a fixed expectation of what *should* exist. No step produces artifacts that parody the feature's actual complexity.

**Proportionality Principle.** Code diffs are minimal — the smallest change that satisfies the specification and passes tests. Thinking artifacts (analysis, questions, risk registers) stay verbose where warranted but never duplicate information already present in `.current_session/`. Docstrings follow a deliberate arc: overspecified at interface design (Step 4) to serve as implementation blueprints, then trimmed to match actual complexity at reconciliation (Step 8). This is the entropy-reduction pass.

The pipeline produces **two merge requests**: Steps 1-5 (requirements definition phase) and Steps 6-8 (implementation & housekeeping phase). This enforces reviewability at phase boundaries and creates natural rollback points.

## Tiered Context Model

Agent context windows are finite and expensive. The pipeline uses a **tiered context model** to minimize context pollution while maximizing agent reasoning quality. Agents load context progressively — cheapest first, drilling deeper only when needed.

| Tier | What | Vehicle | Cost per Module | How Loaded |
| --- | --- | --- | --- | --- |
| 0 | Project map: modules, API signatures, dependencies, errors | Root `CLAUDE.md` | ~15-25 tokens | Auto-loaded at session start (FREE) |
| 0.5 | Compressed interfaces: signatures + types, no behavioral contracts | `/interface <module>` or `tools/inspect_interface.py` | ~100 tokens | On-demand via tool |
| 1 | Full behavioral contracts: pre/post-conditions, invariants, error semantics | `base.py` files | ~300-800 tokens | Read on demand |
| 2 | Full source code | Implementation files | ~1,500-3,000 tokens | Read only for owned module |

**Tier 0 in `CLAUDE.md`:** Claude Code auto-loads the project's `CLAUDE.md` at session start. The Module Map section gives every agent the complete project inventory — module names, one-line API signatures, dependency graph, error types — at zero tool-call cost. This replaces the previous approach of reading `__init__.py` manifests.

**Tier 0.5 via structured docstrings:** Every `base.py` starts with a strict-template module docstring (Module, Responsibility, Interfaces, Error Types, Domain Types, Dependencies, Design Notes). This format enables automated extraction via `tools/inspect_interface.py` and Grep multiline patterns, giving agents compressed Tier 1 context without reading the full file.

**Step 0 generates `CLAUDE.md`.** Step 8 re-validates it after each pipeline run.

## Tools

| Tool | Purpose | Usage |
| --- | --- | --- |
| `tools/inspect_interface.py` | AST-based interface metadata extraction | `python tools/inspect_interface.py <path> [--depth=0\|1\|2] [--only-base] [--module-doc] [--verify=CLAUDE.md]` |
| `/interface` skill | Claude Code skill wrapping the above | `/interface <path> [options]` |
| LSP MCP server | Point queries: hover, definition, references | Install from MCP marketplace; provides native tool integration |

See `prompt_templates/skills/interface_skill.md` for `/interface` registration and usage details.

## `.current_session/` Directory

Each pipeline run operates within a `.current_session/` directory that stores **thinking artifacts only** — specifications, analysis documents, question sets, semantic diffs, strategy declarations, reconciliation reports. Code files, test files, interface files, stubs, and manifest updates go to their proper codebase locations.

The human creates this directory in Step 1 and drops `raw_prompt.md` there. The first agent (Step 2 — Spec Refiner) initializes `index.md` using a structured format (artifact table with estimated token costs, requirements map, key decisions) and begins structured artifact tracking. Every subsequent agent reads the session directory on startup to discover prior thinking artifacts, writes its own thinking artifacts there, and appends entries to `index.md`. The structured format enables downstream agents to selectively load artifacts based on what they need, rather than reading everything.

## Test Structure

Tests live in `tests/` mirroring the repository structure:
- `tests/unit/` — Behavioral tests (Step 5a, Step 7). On failure: fix the implementation.
- `tests/integration/` — Contract tests (Step 5b). On failure: escalate to human.
- Test files follow `test_<module_name>.py` naming.

## Agent Design Principles (Cross-Cutting)

Every agent in this pipeline must answer two questions at design time:

1. **What should it do?** (Scoped precisely per step above.)
2. **What should it learn across sessions?** Persistent memory is mandatory. The Spec Refiner learns which questions yield the highest-information answers. The Implementer learns which architectural patterns succeed in this codebase. The Test Formalizer learns which test strategies catch the most bugs per test.

All agents receive their step-specific instruction prompt from the orchestrator, along with the `.current_session/` directory containing all prior artifacts. No agent inherits conversational context from a prior step. Context isolation is a feature, not a limitation — it prevents cascading hallucination. Each agent reads `.current_session/` and `index.md` to discover what prior steps produced, then determines appropriate depth for its own output based on what it finds.

**Context Loading Protocol:** All agents follow the same progressive loading pattern — Tier 0 (CLAUDE.md, free) → Tier 0.5 (`/interface`, ~100 tokens) → Tier 1 (Read `base.py`, ~500 tokens) → Tier 2 (Read implementation, ~2000 tokens). Agents should never load a higher tier when a lower one suffices. See individual step templates for step-specific loading guidance.

---

## Pipeline Summary

| Step | Name | Input | Output | Contextual? | Phase |
| --- | --- | --- | --- | --- | --- |
| 0 | CLAUDE.md Generation | Existing codebase | Root `CLAUDE.md` (Tier 0 map) | One-time setup, re-validated at Step 8 | Setup |
| 1 | Raw Input (Human) | Human brain | `.current_session/raw_prompt.md` | No — manual step | Requirements |
| 2 | Spec Refinement | `.current_session/`, template, system context | `index.md` init; `refined_prompt.md`, questions → `.current_session/` | Sub-steps: interrogation depth scales with scope | Requirements |
| 3 | Structural Analysis | `.current_session/`, CLAUDE.md (Tier 0) | `structural_analysis.md` → `.current_session/` | **Yes** — LIGHT mode for single-module changes | Requirements |
| 4 | Interface Design | `.current_session/`, Tier 0 + Tier 0.5 context | Code (`base.py`, stubs, `__init__.py`) → codebase; thinking → `.current_session/` | Handles reduced/absent structural analysis | Requirements |
| 5 | Specification Tests | `.current_session/` + codebase interfaces | Tests → codebase; thinking → `.current_session/` | **Yes** — integration skip when no cross-module boundaries | Requirements |
| 6 | Implementation | `.current_session/` + codebase interfaces/tests | Code → codebase; thinking (strategy, semantic diff) → `.current_session/` | Handles missing artifacts gracefully | Implementation |
| 7 | Implementation Tests | `.current_session/` + codebase code/tests | Tests → codebase; thinking (report) → `.current_session/` | **Yes** — trivial implementations get edge case tests only | Implementation |
| 8 | Documentation & Reconciliation | `.current_session/` + codebase + CLAUDE.md | CLAUDE.md/docstring updates → codebase; reconciliation → `.current_session/` | **Yes** — scales output to feature complexity | Implementation |

**Deliverables:** Steps 1-5 produce a single MR (requirements definition phase). Steps 6-8 produce a single MR (implementation & housekeeping phase).

**Transition rule:** Human validates output, decides proceed / revise / abort. Forward-only execution. Backward transitions only via explicit human decision, re-entering at the target step with all downstream artifacts invalidated. When a step produces N/A or reduced output, downstream steps adapt — they work from what exists, not from what was expected.
