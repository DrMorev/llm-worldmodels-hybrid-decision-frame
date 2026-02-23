# repo_snapshot.md - llm-worldmodels-hybrid-decision-frame (v1.1)

Date: 2026-02-22
Status: publish-ready (docs + runnable prototype scaffold + latency-bound scenario)

## 1) Purpose

Engineering decision framework for choosing between:

- LLM-centric systems
- world-model + planning systems
- hybrid closed-loop systems (LLM + tools/sensors + verification loop; optional world model)

Goal is not AGI.
Goal is architecture selection under cost of error, verification constraints, and latency constraints.

## 2) Repository layout

- `README.md` - entry point (what it is / is not / how to use)
- `docs/`
  - `decision_protocol.md` - selection rules
  - `scope_and_nongoals.md` - boundaries
  - `definitions.md` - strict terminology
  - `limitations.md` - P3 + benchmark/stack limits + drift + bias
  - `commit3_analysis.md` - Commit 3 analysis (FACT / ASSUMPTION / RECOMMENDATION)
- `research/`
  - `context_pack.md` - minimal framing + falsifiable signals P1/P2/P3
  - `core_sources.md` - canon-min sources + 1-line “what it supports” + optional closed-loop sources
- `prototype/` (stdlib-only, Python 3.10+)
  - `__init__.py`
  - `config.py`
  - `invariant_checks.py`
  - `loop_skeleton.py`
  - `example_run.py`
  - `README.md` (disclaimer + run instructions)
  - `scenarios/`
    - `__init__.py`
    - `latency_bound.py` - Commit 3: hybrid-loses latency crossover scenario

## 3) What was implemented

### Documentation pack

- Decision protocol based on:
  - Cost of Error (CoE)
  - Dynamics requirement
  - Explainability requirement
  - Online adaptation requirement
  - Verification availability
  - Latency budget (hard override)

### Critical constraints (must-haves)

1. Verification independence
   Verification must be orthogonal to the planner.
   LLM-based self-verification does not count as STRONG verification.
1. Latency budget
   If Latency Budget < (Inference Time + Loop Time), hybrid loop is disallowed as a controller.
1. World model vs simulator
   Simulator/Oracle is treated as an explicit upper-bound baseline, not learned dynamics.

### Research additions

- Falsifiable signals:
  - P1 (world-model + planning dominates long-horizon control)
  - P2 (closed-loop scaffolding/interface is main lever)
  - P3 (diminishing returns of tools/planning at high scale; open question)
- Incentive mismatch noted as a limitation for P3 testing.
- Optional closed-loop sources kept separate to avoid canon bloat.

### Prototype scaffold (Commit 2)

A runnable toy demonstration that makes the key tradeoff executable:

- `llm_only`: state update uses planner prediction (self-grounding)
- `hybrid`: state update uses observed simulator state (grounding)
  Includes:
- invariant checks (types, bounds, stop condition)
- latency budget check
- fixed configuration and deterministic-ish run
  Run:
- `python -m prototype.example_run`

### Latency-bound scenario (Commit 3)

Demonstrates that hybrid **loses** to LLM-only under tight latency with low task ambiguity.

- Injects per-component delays (plan: 20ms, verify: 15ms, observe: 25ms)
- Sweeps 12 latency budgets (25–120ms), 30 trials each
- Finds crossover point (~70ms): below this, hybrid cannot complete a single step
- Documents results as FACT / ASSUMPTION / RECOMMENDATION
- Provides evidence for decision protocol latency override rule
  Run:
- `python -m prototype.scenarios.latency_bound`

**This is a toy setting, not a general claim.** Delays are simulated. The claim is
that a crossover pattern exists, not that specific thresholds transfer to production.

## 4) Non-goals (locked)

- No consciousness or metaphysics content
- No benchmark leaderboard / SOTA framing
- No claims that the prototype validates general statements
- No CASEF/test-suite content (handled elsewhere)

## 5) Finalization checklist (quick)

- Ensure no URLs contain `utm_source=chatgpt.com` or `oai_citation`
- Ensure `prototype/README.md` states:
  - not validating general claims
  - orthogonal verification requirement
  - latency interlock
  - invariant/stop conditions
  - run commands:
    - `python -m prototype.example_run`
    - `python -m prototype.scenarios.latency_bound`
- Ensure `docs/limitations.md` includes version pinning guidance (model/provider/snapshot/budgets)

## 6) “Done” definition

Repository is finalized when:

1. All docs are consistent with the 3 critical constraints.
1. `python -m prototype.example_run` runs without edits or dependencies.
1. `python -m prototype.scenarios.latency_bound` runs without edits or dependencies.
1. No chat-generated URL artifacts remain.
1. README provides a clean entry path: protocol → limitations → context → prototype.

## 7) One-line identity

Decision framework for architecture selection under risk, using cost-of-error, verification orthogonality, and latency budgets, with a narrow runnable scaffold that exposes tradeoffs — including cases where hybrid loses - without making general claims.
