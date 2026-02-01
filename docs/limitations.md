# Limitations

## 1) P3 is not solved here
P3: "If scale alone is sufficient, adding tools/planning should show diminishing returns at large scale."

This repo does not claim P3 is true or false.
It treats P3 as an empirical question requiring protocol-level ablations.

## 2) Why one leaderboard cannot resolve P3
Clean testing requires:
- same task set
- fixed budgets (steps/context/tool access)
- same scaffold, toggling only tools/planning
- multiple model scales
- stable environments

In practice, these conditions are rarely met.

## 3) Structural limits of current evaluations
1) Incentive asymmetry: providers and competitors have incentives in result framing.
2) Closed-model stack opacity: system prompts/routing/tool policies are hidden; strict ablations cannot be verified.
3) Selection bias: benchmarks are curated, not random.
4) Non-stationary environments: web/OS tasks drift over time.
5) Compute constraints: independent evaluators often cannot run large ablation sweeps on frontier systems.
6) Apples-to-oranges: open-weight vs closed models differ in policies and tool access.

## 4) Verification independence is mandatory for safety claims
Constraint: Verification signal must be orthogonal to the planner.
LLM-based self-verification does not count as STRONG verification.

Correlated planner+verifier failure collapses the benefit of a hybrid loop.

## 5) Latency–safety tradeoff (engineering vulnerability)
Hybrid loops are slow by default (inference + tool calls + iteration).
In tight real-time windows, a correct plan can still produce a stale action.

Rule:
If decision window < (Inference Time + Loop Time), do not use an LLM-driven loop as the controller.
Use a fast-path controller (precomputed policy or non-LLM interlock) and keep the LLM offline.

## 6) Version pinning (reproducibility under drift)
For any run or claim, record:
- provider + model name
- snapshot date (or explicit version tag if offered)
- temperature/top-p/seed if applicable
- system/tooling policy if applicable
- budgets: max steps, max context, tool access
Without this, drift can invalidate comparisons quickly.
