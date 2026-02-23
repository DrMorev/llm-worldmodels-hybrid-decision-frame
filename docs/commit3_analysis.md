# Commit 3: When Hybrid Loses - Latency-Bound Analysis

## Summary

This commit demonstrates a scenario where the hybrid closed-loop architecture
**loses to LLM-only** under tight latency constraints with low task ambiguity.

This is not a bug - it is a **design boundary** of the decision framework.

A framework that always recommends one architecture is not a framework.
It is advertising.

## Experimental parameters (exact)

|Parameter                   |Value                                              |Notes                                     |
|----------------------------|---------------------------------------------------|------------------------------------------|
|Environment                 |LineWorld, size=6                                  |1D, goal at pos 6                         |
|`hallucination_rate`        |0.15                                               |Low ambiguity (planner usually correct)   |
|`uncertainty_stop_threshold`|0.90                                               |Invariant trips above this                |
|`max_steps`                 |12                                                 |Per-trial step budget                     |
|`n_trials`                  |30                                                 |Per budget level                          |
|Seed policy                 |`seed = trial * 17 + 3`                            |Deterministic, spread                     |
|Budgets swept               |25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 100, 120 ms|12 levels                                 |
|`plan_delay_s`              |20ms                                               |Simulated LLM inference (both modes)      |
|`verify_delay_s`            |15ms                                               |Simulated invariant check (hybrid only)   |
|`observe_delay_s`           |25ms                                               |Simulated sensor/world-model (hybrid only)|

**Completion** = trial where `env.is_done()` returns True (agent reached goal position).
Trials that terminate on invariant failure, latency budget exceeded, or step budget
exceeded are counted as non-completions.

**This is a toy setting, not a general claim.** Component delays are injected via
busy-wait, not measured from real inference. The claim is that the crossover pattern
exists, not that specific millisecond thresholds transfer to production.

## Results

```
Budget    LLM-only    Hybrid     Winner
25ms       46.7%       0.0%     LLM-only
30ms       46.7%       0.0%     LLM-only
35ms       46.7%       0.0%     LLM-only
40ms       46.7%       0.0%     LLM-only
45ms       46.7%       0.0%     LLM-only
50ms       46.7%       0.0%     LLM-only
55ms       46.7%       0.0%     LLM-only
60ms       46.7%       0.0%     LLM-only
70ms       46.7%      50.0%     Hybrid
80ms       46.7%      50.0%     Hybrid
100ms      46.7%      50.0%     Hybrid
120ms      46.7%      50.0%     Hybrid
```

**Crossover point: ~70ms.** Below this, hybrid cannot complete a single step.

## Why hybrid lost

### Facts (observed from this scenario)

1. Hybrid overhead = 40ms/step (verify + observe). This is a fixed cost
   that hybrid pays regardless of whether grounding helps.
1. At `hallucination_rate=0.15`, LLM-only is correct ~85% of the time.
   The accuracy delta from grounding is small.
1. For any budget below 60ms, hybrid fails immediately on latency -
   it never even gets to demonstrate its accuracy advantage.
1. The crossover at 70ms is sharp: hybrid goes from 0% to 50% completion
   as soon as it can fit one full step within budget.

### Assumptions (not proven here)

1. Component timings are simulated. Real-world LLM inference, sensor latency,
   and verification cost will differ. The pattern (crossover exists) is the
   claim, not the specific millisecond thresholds.
1. “Low ambiguity” maps to `hallucination_rate=0.15`. In production, ambiguity
   depends on task domain, prompt quality, and model capability. There is no
   universal threshold.
1. We assume verification overhead is constant per step. In practice,
   verification cost may scale with state complexity.

### Recommendations (for decision protocol)

1. **Add latency override to decision protocol:**
   If `latency_budget < hybrid_step_cost` → skip hybrid, use LLM-only
   regardless of cost-of-error. Document this as an explicit fast-path rule.
1. **Add ambiguity qualifier:**
   If `task_ambiguity < LOW` AND `latency_budget < generous` → LLM-only.
   Hybrid overhead is only justified when grounding provides meaningful
   accuracy gain.
1. **Publish crossover analysis template:**
   Teams should measure their own component timings and compute their
   crossover point before choosing architecture.

## Implications for P1, P2, P3

- **P1 (world models essential):** This scenario shows world models are
  NOT essential for low-ambiguity tasks - they add cost without benefit.
- **P2 (closed-loop is the lever):** True, but only above the latency
  threshold. Below it, the loop itself becomes the bottleneck.
- **P3 (scale alone sufficient):** This scenario is EVIDENCE FOR P3 in
  the narrow case: when the LLM is good enough (low hallucination),
  scaling its speed matters more than adding verification.

## Files

- `prototype/scenarios/latency_bound.py` — runnable scenario with sweep
- `docs/commit3_analysis.md` - this document

## How to run

```bash
cd prototype
python -m scenarios.latency_bound
```

No dependencies. No API keys. Python 3.10+.
