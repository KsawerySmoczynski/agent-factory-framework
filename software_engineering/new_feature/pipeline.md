# Step 1: Raw Input (Human)

**Input:** Nothing formal.

**Output:** `.current_session/raw_prompt.md`

This step is entirely manual — no agent involved. Create the `.current_session/` directory and write `raw_prompt.md` there.

Brain dump. Unordered, messy, stream-of-consciousness. All requirements, constraints, behaviors, edge cases, performance expectations, aesthetic preferences, things you're unsure about. Don't self-edit. The goal is maximum information extraction from your head, not coherence. Coherence is the next step's job.

Include anything that *might* matter: related components in the existing system, modules this feature will touch, deployment constraints, user-facing behaviors, non-functional requirements, things you explicitly do *not* want.

# Step 2: Specification Refinement

**Input:** `.current_session/` (containing `raw_prompt.md`), `refined_prompt_template.md` (predefined headers), surrounding system context (relevant `__init__.py` manifests, interface files of adjacent modules).

**Output:** `refined_prompt.md`, question artifacts — all written to `.current_session/`, `index.md` initialized and populated.

**Session bootstrap:** This is the first agent step. Initialize `index.md` in `.current_session/` — register `raw_prompt.md` as the first entry, then append your own artifacts as you produce them.

**Agent role:** Spec Refiner

**Decision maker:** Human approves final refined prompt.

The agent's job is adversarial clarification. It receives the raw prompt and the template headers, then:

1. **Gap analysis.** Identify every header the template demands that the raw prompt does not address. Surface these as explicit questions, not assumptions. Template headers that do not apply to this feature may be marked "N/A — [justification]".
2. **Ambiguity detection.** For each requirement stated in the raw prompt, ask: could two competent engineers read this and build different things? If yes, force a disambiguation question.
3. **Conflict detection.** Flag requirements that contradict each other or contradict known properties of adjacent modules (drawn from provided context).
4. **Fill the template.** Only after the Q&A round resolves, the agent populates `refined_prompt.md` against the predefined headers.

The agent learns across sessions: it accumulates knowledge about *which questions yielded the most specification-changing answers* in prior refinement rounds, and prioritizes those question types in future sessions. Persistent memory is mandatory for this agent.

**What the refined prompt must contain (minimum viable headers):**

- Functional requirements (what it does) — always mandatory
- Non-functional requirements (latency, throughput, resource bounds) — N/A when no quantitative performance constraints exist
- Interface boundary expectations (what modules it talks to, via what contracts) — N/A for changes internal to a single module
- Scope exclusions (what it explicitly does *not* do) — can be brief or N/A for tightly scoped changes
- Acceptance criteria (how we know it's done) — always mandatory

# Step 3: Structural Analysis

**Input:** `.current_session/` (containing `refined_prompt.md` and prior artifacts), relevant codebase context.

**Output:** `structural_analysis.md` — written to `.current_session/`, `index.md` updated.

**Decision maker:** Human approves structural understanding before interface design proceeds.

**Scope calibration:** If the refined prompt describes a change confined to a single module with clear boundaries, produce a brief structural note (1-2 paragraphs) instead of the full integration matrix + risk register + data flow diagrams. State the chosen mode (LIGHT or FULL) and justification at the top of output.

This step has two modes depending on context:

**Greenfield:** The agent receives the refined prompt and the manifest-level context (Tier 0 — see below) of related components. It produces a structural analysis document: proposed module boundaries, identified integration points with existing system, dependency direction, data flow sketch. This is a *thinking* artifact, not code.

**Refactor:** The agent additionally receives the existing implementation. It performs a **throwaway exploratory pass** — reading code, tracing call graphs, identifying coupling and tangling. The exploratory implementation is discarded; its only purpose is to produce the structural analysis document with added insight: what's tangled, what's clean, what can be preserved, what must be rebuilt.

In both cases, the output is the same shape: a document describing the structural landscape the interface design must navigate. In LIGHT mode, the output is a brief structural note covering proposed changes and any non-obvious risks.

# Step 4: Interface Design

**Input:** `.current_session/` (containing `refined_prompt.md`, `structural_analysis.md` if present, and prior artifacts), Tier 0 context of adjacent modules.

**Output:** Module interface files (`base.py`), stub implementations raising `NotImplementedError`, updated `__init__.py` manifests — written to their codebase locations. Thinking artifacts written to `.current_session/`, `index.md` updated. Part of the **requirements phase MR**.

**Agent role:** Interface Designer

**Decision maker:** Human reviews and merges.

If structural analysis was reduced (LIGHT mode) or absent, the interface designer works from `refined_prompt.md` alone, deriving module boundaries directly from the specification.

The agent designs the public surface of the module(s). Principles:

- **Composition over inheritance.** Always.
- **Objects hold state; methods orchestrate pure functions.** The object layer is a thin stateful shell. All logic lives in a fully functional API underneath.
- **Encapsulation is non-negotiable.** If it's not in the public interface, it doesn't exist to other modules.

**Deliberate overspecification of docstrings:** Docstrings at this step are intentionally verbose — full behavioral contracts, pre/post-conditions, edge case expectations, acceptance criteria cross-references. This is by design. These serve as the implementation blueprint for Step 6. Step 8 will trim them to match actual complexity after implementation is complete.

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

**Input:** `.current_session/` (prior thinking artifacts) and interface files, stubs from their codebase locations.

**Output:** Test suite written to codebase test directories. Thinking artifacts (traceability matrix) written to `.current_session/`, `index.md` updated. Part of the **requirements phase MR**.

**Agent role:** Test Formalizer

**Decision maker:** Human reviews and merges.

These tests formalize the requirements stated in the refined prompt. They are written **before any implementation exists** and must pass against any correct implementation. They are the *contract*, not the verification of a specific solution.

**Anti-pattern:** Do NOT write integration contract tests that merely verify type shapes already enforced by mypy, Pydantic validators, or linter rules. Integration tests must test semantic contracts — behavioral expectations that static analysis cannot verify.

Two categories, with fundamentally different failure semantics:

### 5a. Behavioral Tests → On failure: fix the implementation

Unit tests, property-based tests, and mutation tests. These encode: "given input X, module produces output Y" or "for all inputs satisfying predicate P, output satisfies predicate Q."

- **Unit tests:** Concrete input/output pairs derived directly from requirements. Always produced.
- **Property-based tests:** Invariants that must hold across input distributions. These catch the cases the spec author didn't think of. Contextual — skip with a single-sentence justification if no invariants apply.
- **Mutation tests:** Verify that the test suite is actually discriminating — that small perturbations to a correct implementation cause test failures. A test suite that passes all mutations is vacuous. Contextual — skip with a single-sentence justification if not warranted.

### 5b. Integration Contract Tests → On failure: escalate to human

These encode: "module A communicates with module B via interface W, sending data shaped like X and receiving data shaped like Y."

**If no cross-module boundaries exist, skip integration tests entirely.** A single module with no external dependencies does not need integration contract tests.

**Why the escalation difference matters:** A behavioral test failure means the implementation is wrong relative to a fixed interface. An integration contract failure means the *interfaces themselves* are inconsistent — the architectural design has a flaw. Agents should not attempt to fix architectural flaws autonomously. The cost of a wrong architectural patch compounds across the entire system. Escalate early; don't force a rewrite.

**Escalation protocol:** When an integration contract fails, the agent halts, emits a diagnostic (which contracts failed, what the expected vs. actual interface shapes are, and a hypothesis about the root cause), and hands control to the human. The human decides whether to revise interfaces (rolling back to Step 4), adjust the contract (revising Step 5), or override.

# Step 6: Implementation

**Input:** `.current_session/` (all prior thinking artifacts).

**Output:** Working implementation passing all Step 5 tests, semantic diff. Thinking artifacts written to `.current_session/`, `index.md` updated. Part of the **implementation phase MR**.

**Agent role:** Implementer (one per module in cross-module features)

**Decision maker:** Human reviews and merges.

**Minimal Diff Principle:** Produce the smallest code change that satisfies the specification and passes all tests. Do not add abstractions for hypothetical future use, create utility functions for one-off operations, or add error handling for scenarios not required by the spec. Docstrings from Step 4 interfaces are the implementation blueprint — do not add new documentation beyond what the interfaces already specify.

**Graceful handling of missing artifacts:** If structural analysis is absent or light, work from `refined_prompt.md` and interfaces. If specific test categories were skipped, focus on passing the tests that exist.

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

**Input:** `.current_session/` and all prior artifacts including completed implementation and Step 5 tests.

**Output:** Extended test suite. Thinking artifacts written to `.current_session/`, `index.md` updated. Part of the **implementation phase MR**.

**Agent role:** Test Extender

**Decision maker:** Human reviews and merges.

**Scope calibration:** If the implementation is trivial (single function, no branching logic, no state management, no complex error paths), produce only edge case tests. Skip internal unit tests, performance regression, and change sensitivity categories with brief justification. This step may be skipped entirely for truly trivial implementations with justification written to `.current_session/`.

Step 5 tests verify the software meets the *specification*. Step 7 tests verify properties of the *actual implementation* — paths, edge cases, and behaviors that only become visible after the code exists.

These include:

- Tests for internal helper functions and utilities that emerged during implementation
- Edge case tests derived from actual branching logic in the code
- Performance regression tests calibrated against measured implementation characteristics
- Defensive tests for error paths that the spec didn't enumerate but the implementation must handle

**The distinction is epistemological.** Step 5 tests are derived from *what we want*. Step 7 tests are derived from *what we built*. Both are necessary. Step 5 catches requirement violations. Step 7 catches implementation fragility.

# Step 8: Documentation & Reconciliation

**Input:** `.current_session/` (all prior thinking artifacts), implementation files and tests.

**Output:** Updated documentation, reconciliation artifacts. Written to `.current_session/`, `index.md` updated. Part of the **implementation phase MR**.

**Agent role:** Reconciler

**Decision maker:** Human reviews and merges.

The agent performs a full read-through of the completed work and:

1. **Enhances `__init__.py` manifests** to reflect what was actually built, not what was planned. The Tier 0 map must be accurate post-implementation.
2. **Trims docstrings to match actual complexity.** Step 4 deliberately overspecified docstrings to serve as implementation blueprints. Now that implementation is complete, trim them to match actual implementation complexity — remove redundant pre/post-conditions that merely restate what the code obviously does, align verbosity with the code's actual complexity, improve information density. This is the entropy-reduction pass.
3. **Identifies spec-vs-result mismatches.** Where did the implementation deviate from the refined prompt? These deviations are not necessarily bugs — they're learning. Document them explicitly so future pipeline runs benefit.
4. **Proposes refactoring candidates.** Functions that should be extracted and generalized for reuse across implementations. Utility files that should be combined or split. Dead code. But: **does not execute refactors in this step.** Proposals only, as a separate MR or annotated document. Refactoring is a separate pipeline run.

**Proportionality:** Scale output to feature complexity. For small features: `SPEC_VS_RESULT.md` can be a brief table. Skip `REFACTOR_PROPOSALS.md`, `oncall_notes.md`, and `STRUCTURAL_RETROSPECTIVE.md` if nothing warrants them. `PIPELINE_FEEDBACK.md` is always produced (even if brief) — it feeds process improvement.

**Non-duplication:** Do not reproduce analysis already present in `.current_session/` artifacts. Reference them by filename and section. Your job is to reconcile and surface gaps, not to summarize what already exists.
