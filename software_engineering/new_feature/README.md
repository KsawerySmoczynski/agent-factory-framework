# HOW TO MAKE MY AGENT ONE SHOT EVERYTHING Building a Feature: Agent-Orchestrated Development Pipeline

## Descrition
Files in `prompt_templates` dir contain description what should happen during this stage and prompt templates for agents at each stage.

## Philosophy

Architecture is the product; code is ephemeral. The durable engineering artifact is the specification — interface graphs, invariant declarations, contract test suites, module manifests. Implementations are regenerable from specs. Version control tracks *specification changes*; code is a derived artifact.

Each pipeline step is an **independent agent session** with its own instruction prompt, cleared context, and bounded scope. A human operator validates outputs and decides transitions. An orchestrator retrieves the appropriate step prompt and feeds it the artifacts produced by prior steps. In the current iteration, the human *is* the orchestrator. Future iterations will progressively replace human gating with agent-driven decisions, but that is out of scope here.

Every step from Interface Design onward produces a **merge request** as its deliverable. This enforces atomic reviewability and creates natural rollback points.


## Agent Design Principles (Cross-Cutting)

Every agent in this pipeline must answer two questions at design time:

1. **What should it do?** (Scoped precisely per step above.)
2. **What should it learn across sessions?** Persistent memory is mandatory. The Spec Refiner learns which questions yield the highest-information answers. The Implementer learns which architectural patterns succeed in this codebase. The Test Formalizer learns which test strategies catch the most bugs per test.

All agents receive their step-specific instruction prompt from the orchestrator, along with explicitly enumerated input artifacts. No agent inherits conversational context from a prior step. Context isolation is a feature, not a limitation — it prevents cascading hallucination.

---

## Pipeline Summary

| Step | Name | Input Artifacts | Output Artifacts | Deliverable |
| --- | --- | --- | --- | --- |
| 1 | Raw Input | Human brain | `raw_prompt.md` | File |
| 2 | Spec Refinement | `raw_prompt.md`, template, system context | `refined_prompt.md` | File |
| 3 | Structural Analysis | `refined_prompt.md`, codebase context | `structural_analysis.md` | File |
| 4 | Interface Design | `refined_prompt.md`, `structural_analysis.md` | `base.py`, stubs, manifests | **MR** |
| 5 | Specification Tests | `refined_prompt.md`, interfaces, stubs | Test suite | **MR** |
| 6 | Implementation | All above | Working code, semantic diff | **MR** |
| 7 | Implementation Tests | Implementation, `refined_prompt.md`Step 5 tests | Extended test suite | **MR** |
| 8 | Documentation & Reconciliation | All artifacts | Updated docs, refactor proposals | **MR** |

**Transition rule:** Human validates output, decides proceed / revise / abort. Forward-only execution. Backward transitions only via explicit human decision, re-entering at the target step with all downstream artifacts invalidated.