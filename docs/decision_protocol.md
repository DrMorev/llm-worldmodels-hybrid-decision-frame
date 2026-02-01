# Decision Protocol: architecture choice under cost of error

## Inputs
Score each as LOW / MED / HIGH unless specified otherwise.

1) Cost of Error (CoE)
- LOW: wrong output is tolerable.
- HIGH: wrong action can cause harm, loss, irreversible outcomes.

2) Dynamics / causality requirement
- LOW: mostly static transformation.
- HIGH: outcomes depend on state transitions and actions.

3) Explainability requirement
- LOW: internal tooling, low stakes.
- HIGH: justification required (clinical/legal/ops).

4) Online adaptation requirement
- LOW: one-shot assistance.
- HIGH: iterated action in changing state.

5) Verification availability (NONE / WEAK / STRONG)
- NONE: no external checks exist.
- WEAK: partial checks (format, heuristics, weak signals).
- STRONG: orthogonal external signal (execution, sensors, simulator constraints, independent APIs).

Constraint: Verification signal must be orthogonal to the planner.
LLM-based self-verification does not count as STRONG verification.

6) Latency Budget / Time Constraint (TIGHT / RELAXED)
- TIGHT: real-time (<1s). Hybrid loops forbidden.
- RELAXED: asynchronous (>5s). Hybrid loops viable.

## Default selection rules

### Rule A — Low CoE
If CoE is LOW:
- Prefer LLM-centric.
- Add tools only when they provide orthogonal verification or reduce obvious error.

### Rule B — High CoE + weak verification
If CoE is HIGH and Verification is NONE/WEAK:
- Prefer world-model-centric only if a validated simulator/dynamics model exists.
- Otherwise narrow the task until a strong verification channel exists.
- If you cannot add verification, choose abstention/handoff.

### Rule C — High CoE + strong verification (default for action)
If CoE is HIGH and Verification is STRONG:
- Prefer Hybrid closed-loop as default.
- Require explicit loop: plan → act → observe → update.
- Require explicit stop/abstention on contradiction or uncertainty.

### Rule D — High dynamics requirement
If Dynamics is HIGH:
- Prefer world-model-centric when a usable learned world model exists.
- Otherwise Hybrid with a narrow simulator/state estimator is acceptable, but must enforce verification and stop rules.

### Latency override (critical)
If Latency Budget < (Inference Time + Loop Time):
- Hybrid is disallowed regardless of CoE.
- Use a fast-path controller (precomputed policy, classical control, cached solver) and treat LLM as offline analysis only.

## Hard constraints
- No action execution without an orthogonal verification channel when CoE is HIGH.
- Fix budgets (steps/context/tool access) when comparing architectures.
- Do not claim general validation from narrow demos.

## Output template
Decision:
- CoE:
- Dynamics:
- Explainability:
- Online adaptation:
- Verification:
- Latency budget:

Selected architecture:
- LLM-centric / World-model-centric / Hybrid closed-loop / Abstain

Justification (max 3 bullets):
- ...
