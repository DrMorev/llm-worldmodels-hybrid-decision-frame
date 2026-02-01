# llm-worldmodels-hybrid-decision-frame

Engineering decision framework for choosing between:
- LLM-centric systems
- world-model + planning systems
- hybrid closed-loop systems (LLM + tools/sensors + verification loop; optional world model)

This repository is not about proving AGI.  
It exists to reduce error risk and self-deception when the cost of failure differs across tasks.

## What this repository is
- A decision protocol: cost-of-error + constraints → architecture choice
- Strict operational definitions to prevent semantic drift
- A research capsule: minimal context + core sources + open question (P3)
- A narrow prototype scaffold to make tradeoffs explicit (not a product, not a proof)

## What this repository is not
- Not a benchmark leaderboard
- Not a general validation of claims about intelligence
- Not a consciousness discussion
- Not a production agent framework

## Who should read it
Engineering decision-makers and applied researchers choosing architecture under risk, latency constraints, and verification constraints.

## How to use
1) Read `docs/decision_protocol.md` and apply it to your task.
2) Use `docs/definitions.md` to keep terms strict.
3) Check `docs/limitations.md` before drawing conclusions from any demo.
4) Use `research/context_pack.md` and `research/core_sources.md` as the minimal canon.
5) Use `prototype/README.md` only as a narrow scaffold for making tradeoffs falsifiable.

## Repository map
- `docs/` decision protocol, scope, definitions, limitations
- `research/` context pack + core sources map
- `prototype/` narrow closed-loop scaffold (not validating general claims)
