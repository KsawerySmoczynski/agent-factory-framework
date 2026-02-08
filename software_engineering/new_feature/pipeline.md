# Step 1: Raw Input

**Input:** Nothing formal.

**Output:** `raw_prompt.md`

Brain dump. Unordered, messy, stream-of-consciousness. All requirements, constraints, behaviors, edge cases, performance expectations, aesthetic preferences, things you're unsure about. Don't self-edit. The goal is maximum information extraction from your head, not coherence. Coherence is the next step's job.

Include anything that *might* matter: related components in the existing system, modules this feature will touch, deployment constraints, user-facing behaviors, non-functional requirements, things you explicitly do *not* want.

# Step 2: Specification Refinement

**Input:** `raw_prompt.md`, `refined_prompt_template.md` (predefined headers), surrounding system context (relevant `__init__.py` manifests, interface files of adjacent modules).

**Output:** `refined_prompt.md`

**Agent role:** Spec Refiner

**Decision maker:** Human approves final refined prompt.

The agent's job is adversarial clarification. It receives the raw prompt and the template headers, then:

1. **Gap analysis.** Identify every header the template demands that the raw prompt does not address. Surface these as explicit questions, not assumptions.
2. **Ambiguity detection.** For each requirement stated in the raw prompt, ask: could two competent engineers read this and build different things? If yes, force a disambiguation question.
3. **Conflict detection.** Flag requirements that contradict each other or contradict known properties of adjacent modules (drawn from provided context).
4. **Fill the template.** Only after the Q&A round resolves, the agent populates `refined_prompt.md` against the predefined headers.

The agent learns across sessions: it accumulates knowledge about *which questions yielded the most specification-changing answers* in prior refinement rounds, and prioritizes those question types in future sessions. Persistent memory is mandatory for this agent.

**What the refined prompt must contain (minimum viable headers):**

- Functional requirements (what it does)
- Non-functional requirements (latency, throughput, resource bounds)
- Interface boundary expectations (what modules it talks to, via what contracts)
- Scope exclusions (what it explicitly does *not* do)
- Acceptance criteria (how we know it's done)

# Step 3: Structural Analysis

**Input:** `refined_prompt.md`, relevant codebase context.

**Output:** `structural_analysis.md`

**Decision maker:** Human approves structural understanding before interface design proceeds.

This step has two modes depending on context:

**Greenfield:** The agent receives the refined prompt and the manifest-level context (Tier 0 — see below) of related components. It produces a structural analysis document: proposed module boundaries, identified integration points with existing system, dependency direction, data flow sketch. This is a *thinking* artifact, not code.

**Refactor:** The agent additionally receives the existing implementation. It performs a **throwaway exploratory pass** — reading code, tracing call graphs, identifying coupling and tangling. The exploratory implementation is discarded; its only purpose is to produce the structural analysis document with added insight: what's tangled, what's clean, what can be preserved, what must be rebuilt.

In both cases, the output is the same shape: a document describing the structural landscape the interface design must navigate.

# Step 4: Interface Design

**Input:** `refined_prompt.md`, `structural_analysis.md`, Tier 0 context of adjacent modules.

**Output:** Module interface files (`base.py`), stub implementations raising `NotImplementedError`, updated `__init__.py` manifests. Delivered as a **merge request**.

**Agent role:** Interface Designer

**Decision maker:** Human reviews and merges.

The agent designs the public surface of the module(s). Principles:

- **Composition over inheritance.** Always.
- **Objects hold state; methods orchestrate pure functions.** The object layer is a thin stateful shell. All logic lives in a fully functional API underneath.
- **Encapsulation is non-negotiable.** If it's not in the public interface, it doesn't exist to other modules.

**Module structure convention:**

```
module/
├── __init__.py          # Manifest: description of module, each submodule,
│                        #   public API surface. An agent reading ONLY this
│                        #   file knows what the module does and how to use it.
├── base.py              # Interface (abstract base, protocols, type contracts)
├── implementation_v1/
│   ├── __init__.py      # Describes this implementation variant
│   ├── impl.py          # Stateful object, methods call into utils/
│   └── utils/
│       ├── __init__.py  # Describes each function file and grouping rationale
│       ├── grouped_functions/
│       │   └── g1_func.py
│       ├── function_1.py   # Single pure function per file
│       └── function_2.py

```

Every `__init__.py` is a **manifest**, not boilerplate. It describes what each child contains and what it does. An agent reading only `__init__.py` files can navigate the full project without opening any implementation file. This is the foundation of the tiered context model.

Stub implementations must be syntactically valid, type-annotated, and raise `NotImplementedError` with a docstring describing the intended behavior. The stubs *are* the spec in code form — they tell the test-writing agent what to test against without revealing implementation strategy.

# Step 5: Specification Tests

**Input:** `refined_prompt.md`, interface files (`base.py`), stubs.

**Output:** Test suite. Delivered as a **merge request**.

**Agent role:** Test Formalizer

**Decision maker:** Human reviews and merges.

These tests formalize the requirements stated in the refined prompt. They are written **before any implementation exists** and must pass against any correct implementation. They are the *contract*, not the verification of a specific solution.

Two categories, with fundamentally different failure semantics:

### 5a. Behavioral Tests → On failure: fix the implementation

Unit tests, property-based tests, and mutation tests. These encode: "given input X, module produces output Y" or "for all inputs satisfying predicate P, output satisfies predicate Q."

- **Unit tests:** Concrete input/output pairs derived directly from requirements.
- **Property-based tests:** Invariants that must hold across input distributions. These catch the cases the spec author didn't think of.
- **Mutation tests:** Verify that the test suite is actually discriminating — that small perturbations to a correct implementation cause test failures. A test suite that passes all mutations is vacuous.

### 5b. Integration Contract Tests → On failure: escalate to human

These encode: "module A communicates with module B via interface W, sending data shaped like X and receiving data shaped like Y."

**Why the escalation difference matters:** A behavioral test failure means the implementation is wrong relative to a fixed interface. An integration contract failure means the *interfaces themselves* are inconsistent — the architectural design has a flaw. Agents should not attempt to fix architectural flaws autonomously. The cost of a wrong architectural patch compounds across the entire system. Escalate early; don't force a rewrite.

**Escalation protocol:** When an integration contract fails, the agent halts, emits a diagnostic (which contracts failed, what the expected vs. actual interface shapes are, and a hypothesis about the root cause), and hands control to the human. The human decides whether to revise interfaces (rolling back to Step 4), adjust the contract (revising Step 5), or override.

# Step 6: Implementation

**Input:** `refined_prompt.md`, interface files, test suite, structural analysis.

**Output:** Working implementation passing all Step 5 tests. Delivered as a **merge request**.

**Agent role:** Implementer (one per module in cross-module features)

**Decision maker:** Human reviews and merges.

### Tiered Context Model

The implementing agent does *not* see the entire codebase. Context is stratified to minimize pollution and maximize focused reasoning:

- **Tier 0 — Manifest graph.** What exists, how it connects. Fits in any context window. Lives in `__init__.py` files. This is the map. An orchestrator agent operates at Tier 0 to decide which modules need work and how to delegate.
- **Tier 1 — Interfaces + docstrings + contract tests.** Enough to implement *against* without seeing internals. The implementing agent sees Tier 1 for all modules it must *interact with*.
- **Tier 2 — Full source.** Loaded only by the agent that *owns* that module. The implementing agent sees Tier 2 only for the module it is actively implementing. No other agent ever sees this.

For cross-module features: the orchestrator operates at Tier 0, delegates to per-module implementers at Tier 1 boundary, each implementer loads Tier 2 only for its own module. This is information-theoretic access control — agents can't hallucinate interactions with internals they never saw.

### Failure Handling During Implementation

When behavioral tests (5a) fail:

- The agent retries implementation. But **retries are budgeted** — define a maximum number of attempts (recommend 3). If the agent cannot pass behavioral tests within the retry budget, it **escalates to human** with a diagnostic: which tests fail, what it tried, and its hypothesis about why the spec may be under-constrained or contradictory. Don't let agents spin in unbounded retry loops.

When integration contract tests (5b) fail:

- **Immediate escalation.** The agent does not attempt to fix integration failures. It emits a diagnostic and halts. The human decides the resolution path.

### Rollback Semantics

This is critical. When implementation fails and the root cause traces back to interface design:

1. The agent **must not modify tests to match a broken implementation.** Tests from Step 5 are upstream contracts; they are immutable during Step 6.
2. The agent **must not silently modify interfaces.** Interface changes require rolling back to Step 4, which invalidates Steps 5 and 6.
3. The only legal moves during Step 6 are: (a) change implementation code, (b) escalate to human.
4. If escalation leads the human to revise interfaces, the pipeline re-enters at Step 4. All downstream artifacts (tests, implementation) from the prior run are invalidated and regenerated. Merge requests from invalidated steps are closed.

This is forward-only execution with escalation as the only backward path. The human owns all backward transitions.

### Semantic Diffs

After implementation, the agent emits a **structured semantic diff** — not a git diff, but a declaration of intent:

```
ADDED: method `solve(problem: Problem) -> Solution` to class `Solver`
  RATIONALE: decomposition of monolithic `run()` method per refined_prompt §3.2
  TOUCHES: interfaces [Solver], tests [test_solver_decomposition]

MODIFIED: return type of `Preprocessor.transform()` from `List[Token]` to `TokenStream`
  RATIONALE: streaming requirement from refined_prompt §4.1
  TOUCHES: interfaces [Preprocessor, Pipeline], contract tests [test_pipeline_integration]

```

This creates an auditable trail reviewable at the *intent* level. It is the substitute for human code review of implementation details — the reviewer reads what was done and why, not character-level diffs.

# Step 7: Implementation-Derived Tests

**Input:** Completed implementation from Step 6, existing test suite from Step 5.

**Output:** Extended test suite. Delivered as a **merge request**.

**Agent role:** Test Extender

**Decision maker:** Human reviews and merges.

Step 5 tests verify the software meets the *specification*. Step 7 tests verify properties of the *actual implementation* — paths, edge cases, and behaviors that only become visible after the code exists.

These include:

- Tests for internal helper functions and utilities that emerged during implementation
- Edge case tests derived from actual branching logic in the code
- Performance regression tests calibrated against measured implementation characteristics
- Defensive tests for error paths that the spec didn't enumerate but the implementation must handle

**The distinction is epistemological.** Step 5 tests are derived from *what we want*. Step 7 tests are derived from *what we built*. Both are necessary. Step 5 catches requirement violations. Step 7 catches implementation fragility.

# Step 8: Documentation & Reconciliation

**Input:** All prior artifacts.

**Output:** Updated documentation, optional refactoring MR. Delivered as a **merge request**.

**Agent role:** Reconciler

**Decision maker:** Human reviews and merges.

The agent performs a full read-through of the completed work and:

1. **Enhances `__init__.py` manifests** to reflect what was actually built, not what was planned. The Tier 0 map must be accurate post-implementation.
2. **Updates interface documentation and docstrings** to match the implementation's actual behavior, especially where implementation decisions refined ambiguities in the spec.
3. **Identifies spec-vs-result mismatches.** Where did the implementation deviate from the refined prompt? These deviations are not necessarily bugs — they're learning. Document them explicitly so future pipeline runs benefit.
4. **Proposes refactoring candidates.** Functions that should be extracted and generalized for reuse across implementations. Utility files that should be combined or split. Dead code. But: **does not execute refactors in this step.** Proposals only, as a separate MR or annotated document. Refactoring is a separate pipeline run.
