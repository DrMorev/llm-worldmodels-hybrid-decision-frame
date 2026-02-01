# Context Pack: the architectural crossroads

## 1) The core tension
Current AI engineering sits between two paradigms:

A) Scaling (LLM-centric)
Premise: more data + compute yields emergent capabilities.
Strength: broad semantic competence; language as a universal interface.
Risk: reliability ceiling without orthogonal verification; probabilistic truth.

B) Modular control (world models + planning + verification)
Premise: reliability requires explicit search, simulation, and external checks.
Strength: causal/dynamics handling; explicit constraints.
Risk: integration cost; interface mismatch; latency.

This repository exists to decide between these stacks under explicit constraints.

## 2) Why the decision frame matters now
“Chatbots” often have low cost of error.
“Agents” acting in the world have high cost of error.
For high CoE tasks, correctness requires verification channels, not only better prompting.

## 3) P3 hypothesis (open)
P3: if scaling alone is sufficient, tools/planning should have diminishing returns at large scale.
This is testable but hard to test cleanly due to:
- opacity of closed-model stacks
- drift in environments
- budget mismatch across evaluations
- selection bias in task sets

Practical stance:
P3 is tracked as an open question.
The repository remains useful even if P3 is unresolved because the decision protocol applies now.

## 4) Engineering reality check
Architecture sets a ceiling on reliability.
If a system lacks a feedback loop, prompting cannot substitute for missing verification signals.

## 5) Minimal prototype requirement
To avoid “philosophy-only” failure, the prototype folder must contain at least:
- a loop skeleton (plan → act → observe → update)
- a stubbed simulator/oracle or learned model placeholder
- a state invariant check (reject impossible state updates)
Even with placeholders, the scaffold must enforce the core constraints.
