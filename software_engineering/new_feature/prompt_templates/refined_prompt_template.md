# Refined Prompt Template

> This file defines the mandatory structure for every refined specification.
> All headers must be populated. No header may be left empty or marked "TBD."
> The Spec Refiner (Step 2) fills this template after completing the interrogation phase.

---

## Feature: [Feature Name]

**Date:** [YYYY-MM-DD]
**Author:** [Human author]
**Refiner session:** [Session ID or iteration number]

---

## 1. Functional Requirements

> Each requirement is numbered, atomic (one behavior), and testable (there exists a scenario
> that distinguishes "met" from "not met"). Use the format below.

**FR-1:** [Requirement statement]
- **Testable scenario:** [Concrete scenario: given X, when Y, then Z]
- **Notes:** [Any clarification from the interrogation phase]

**FR-2:** [...]

---

## 2. Non-Functional Requirements

> Each requirement has a measurable threshold. "Fast" is not a requirement.

**NFR-1:** [Requirement statement with numeric threshold]
- **Metric:** [What is measured — e.g., p99 latency, peak memory, RPS]
- **Threshold:** [Pass/fail boundary — e.g., < 200ms, < 512MB, >= 1000 RPS]
- **Measurement conditions:** [Load profile, data size, concurrency level under which this threshold applies]

**NFR-2:** [...]

---

## 3. Interface Boundary Expectations

> For each module this feature interacts with.

### Boundary: [This Feature] ↔ [Module Name]

- **Direction:** [Who calls whom — e.g., "This feature calls ModuleX.process()"]
- **Data contract (input):** [Shape/type of data sent across boundary]
- **Data contract (output):** [Shape/type of data received]
- **Error contract:** [What failures can propagate across this boundary and in what form]
- **Reference:** [Specific interface file — e.g., `module_x/base.py::InterfaceName`]

---

## 4. Scope Exclusions

> What this feature explicitly does NOT do. Each exclusion prevents scope creep and anchors negative test space.

- **EX-1:** [Explicit exclusion statement — e.g., "This feature does not handle batch processing. Batch mode is a separate feature."]
- **EX-2:** [...]

---

## 5. Acceptance Criteria

> Human-level "definition of done." These map onto but are not identical to tests.

- **AC-1:** [Acceptance criterion — e.g., "A user can submit a query and receive results within the latency budget under normal load."]
- **AC-2:** [...]

---

## 6. Assumptions & Defaults

> Anything assumed or defaulted during specification. Every assumption is a potential landmine — make them explicit.

- **AS-1:** [Assumption — e.g., "Assumed max input size of 10MB based on current system limits. Not stated in raw prompt."]
- **AS-2:** [...]

---

## 7. Open Questions (Deferred)

> Minor questions that were defaulted. The human may revisit these during later steps.

- **OQ-1:** [Question — current default — rationale for deferral]
- **OQ-2:** [...]