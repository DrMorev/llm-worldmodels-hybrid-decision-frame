# Operational Definitions

To avoid semantic drift, we use strict definitions.

## 1) System components

### LLM (Large Language Model)
A probabilistic model trained primarily for next-token prediction.
- Typical role: interface, reasoning scaffolding, plan generation, text-level synthesis.
- Constraint: no internal ground truth; outputs are probabilistic and may be confidently incorrect.

### World Model (Learned)
A model that learns a compressed representation of environment dynamics and predicts future state given current state and action:
s_{t+1} ~ f(s_t, a_t)
Two common forms:
- Pixel/observation-space prediction: predicts future observations; typically high compute.
- Latent/representation-space prediction (JEPA-style): predicts future representations, filtering irrelevant noise; often preferred for control.

### Simulator / Oracle (Explicit)
A rule-based engine encoding known physics or logic (e.g., chess engine, physics sim, API sandbox).
- Role: provides deterministic or high-fidelity transitions.
- Use in this repo: treated as a perfect upper-bound baseline for comparison, not as learned dynamics.

### Hybrid Closed-Loop
An architecture separating decision from validation.
- Decision: planner (often an LLM) proposes actions.
- Validation: external signal checks consequences or constraints.
- Cycle: plan → act → observe → compare/update.
- Requirement: must include an abstention/stop condition.

## 2) Control concepts

### Planning
Search or optimization over predicted futures before executing actions.
Examples: MCTS, MPC, iterative plan-refine loops.

### State vs Observation
- State (s): complete system configuration (often hidden).
- Observation (o): partial/noisy signal accessible to the agent.
Hybrid implication: must estimate state (or sufficient belief) from observation history.

### Grounding / Verification
Checking model outputs against an external authority.
- Weak verification: format/syntax checks.
- Strong verification: execution results, sensor feedback, simulator constraints, external APIs with independent truth signals.

Constraint: Verification signal must be orthogonal to the planner.
LLM-based self-verification does not count as STRONG verification.

## 3) Error categories

### Hallucination
Plausible but incorrect generation due to probabilistic sampling.

### OOD failure (Out-of-Distribution)
Failure under inputs or dynamics outside training/validation conditions.

### Drift
Change in environment dynamics over time (API updates, UI changes, policy changes) that invalidates prior assumptions.

### Correlated verifier failure
Failure when verifier shares the same bias/error mode as the planner (e.g., LLM judging LLM).
This collapses the safety benefit of a hybrid loop.
