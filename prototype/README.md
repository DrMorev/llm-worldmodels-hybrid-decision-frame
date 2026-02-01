# Prototype scaffold (narrow closed-loop)

## Purpose
This prototype is not intended to validate general claims.
It exists to make architectural tradeoffs explicit and falsifiable in a narrow setting.

## Terminology note
Simulator / Oracle is treated as a perfect upper-bound baseline for comparison, not as learned dynamics.

## What it demonstrates
- LLM-only baseline vs Hybrid closed-loop under fixed budgets
- Explicit loop: plan → act → observe → update
- Adapter layer: token decisions ↔ state representation (SPOF)

## What it does not claim
- No general proof that “hybrid is better”
- No benchmark victory
- No robustness claims outside the narrow domain

## Mandatory safety constraints
1) Verification must be orthogonal
LLM-based self-verification does not count as STRONG verification.

2) Latency interlock
If Latency Budget < (Inference Time + Loop Time), do not use this loop as a controller.
Use a fast-path controller and keep the LLM offline.

3) State invariant check (required)
Before planning or executing:
- reject impossible state updates
- reject out-of-range values
- reject format violations
If invariants fail → stop and abstain.

4) Stop condition (required)
Stop if:
- observation is missing for a required verification step
- verification contradicts the plan
- uncertainty exceeds a defined threshold for safe action

## Comparison rule
To compare LLM-only vs Hybrid:
- fix task set
- fix step budget
- fix context budget
- fix tool access
Only then compare outcomes and failure modes.
