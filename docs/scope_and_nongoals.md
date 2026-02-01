# Scope and Non-goals

## Scope
We compare three system families:
1) LLM-centric: language model is the primary reasoning/control layer.
2) World-model-centric: predictive environment dynamics + planning/control.
3) Hybrid closed-loop: explicit separation between decision and verification.
   Cycle: plan → act → observe → update.

We focus on engineering tradeoffs under different cost-of-error and latency constraints.

## Non-goals
- No claims about AGI or consciousness.
- No leaderboard competition or SOTA positioning.
- No evaluation claims that depend on closed-model stack internals.
- No general claims derived from a narrow prototype.

## Deliverables
- Decision protocol (`docs/decision_protocol.md`)
- Strict definitions (`docs/definitions.md`)
- Limitations and failure modes (`docs/limitations.md`)
- Minimal context and core sources (`research/`)
- Narrow prototype scaffold (`prototype/`)
