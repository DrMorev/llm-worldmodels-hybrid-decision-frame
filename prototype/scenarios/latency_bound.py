“””
Commit 3 — Scenario: Hybrid loses under tight latency.

Thesis:
When per-step latency budget is tight AND task ambiguity is low,
the overhead from verification + world-model grounding makes hybrid
SLOWER than LLM-only, without meaningful accuracy gain.

```
This falsifies the naive claim "hybrid is always better" and provides
a concrete boundary condition for the decision protocol.
```

Design:
- We extend the existing LineWorld with configurable per-component delays:
* plan_delay_s    — base LLM inference time (both modes pay this)
* verify_delay_s  — invariant checking overhead (hybrid only)
* observe_delay_s — world-model / sensor grounding (hybrid only)
- We sweep latency budgets from very tight to generous.
- At each budget we run N trials and collect:
* completion rate (reached goal / total)
* p50, p90, p95, p99 step latency
* mean steps to goal (if reached)
- The output shows the crossover point where hybrid starts winning.

Key insight:
hybrid_overhead = verify_delay + observe_delay
If latency_budget < plan_delay + hybrid_overhead, hybrid ALWAYS fails on budget.
If latency_budget > plan_delay + hybrid_overhead, hybrid wins on accuracy.

Usage:
cd prototype && python -m scenarios.latency_bound
“””
from **future** import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from ..config import PrototypeConfig
from ..loop_skeleton import LineWorld, DummyPlanner, LoopResult
from ..invariant_checks import check_invariants, InvariantResult

# —————————————————————————

# Extended runner with explicit per-component delay injection

# —————————————————————————

@dataclass
class ComponentTimings:
“”“Simulated wall-clock cost for each pipeline component.”””
plan_delay_s: float = 0.020       # LLM inference (both modes)
verify_delay_s: float = 0.015     # invariant check overhead (hybrid only)
observe_delay_s: float = 0.025    # world-model / sensor grounding (hybrid only)

```
@property
def hybrid_overhead(self) -> float:
    return self.verify_delay_s + self.observe_delay_s

@property
def llm_only_step_cost(self) -> float:
    return self.plan_delay_s

@property
def hybrid_step_cost(self) -> float:
    return self.plan_delay_s + self.hybrid_overhead
```

@dataclass
class StepRecord:
step: int
mode: str
elapsed_s: float
budget_ok: bool
inv_ok: bool
reached_goal: bool

@dataclass
class ScenarioResult:
mode: str
latency_budget_s: float
seed: int
ok: bool
reason: str
steps: int
reached_goal: bool
step_records: List[StepRecord] = field(default_factory=list)

def _simulate_delay(seconds: float) -> None:
“”“Burn wall-clock time to simulate component cost.”””
if seconds <= 0:
return
deadline = time.perf_counter() + seconds
while time.perf_counter() < deadline:
pass  # busy-wait for precise timing

def run_latency_scenario(
*,
mode: str,
env: LineWorld,
planner: DummyPlanner,
cfg: PrototypeConfig,
timings: ComponentTimings,
verbose: bool = False,
) -> ScenarioResult:
“””
Like run_loop from loop_skeleton.py, but injects realistic
per-component delays to expose latency overhead.
“””
assert mode in {“llm_only”, “hybrid”}

```
state = env.reset()
uncertainty = 0.0
records: List[StepRecord] = []

if verbose:
    print(f"\n--- {mode.upper()} | budget={cfg.latency_budget_s*1000:.0f}ms ---")

for step in range(cfg.max_steps):
    t0 = time.perf_counter()

    # --- PLAN (both modes) ---
    action, predicted_next, uncertainty = planner.plan(state)
    _simulate_delay(timings.plan_delay_s)

    # --- ACT + OBSERVE ---
    observed_next = env.step(action)

    if mode == "hybrid":
        # Hybrid pays for grounding (sensor/world-model read)
        _simulate_delay(timings.observe_delay_s)

    # --- UPDATE ---
    if mode == "llm_only":
        new_state = predicted_next
    else:
        new_state = observed_next

    # --- INVARIANTS ---
    if mode == "hybrid":
        _simulate_delay(timings.verify_delay_s)

    inv: InvariantResult = check_invariants(
        action=action,
        state=new_state,
        world_size=env.size,
        step=step,
        max_steps=cfg.max_steps,
        uncertainty=uncertainty,
        uncertainty_stop_threshold=cfg.uncertainty_stop_threshold,
    )

    elapsed = time.perf_counter() - t0
    budget_ok = elapsed <= cfg.latency_budget_s

    rec = StepRecord(
        step=step,
        mode=mode,
        elapsed_s=elapsed,
        budget_ok=budget_ok,
        inv_ok=inv.ok,
        reached_goal=env.is_done(),
    )
    records.append(rec)

    if verbose:
        flag = "OK" if budget_ok else "OVER"
        print(
            f"  step {step+1:02d} | {elapsed*1000:6.1f}ms [{flag:4s}] | "
            f"inv={inv.ok!s:5s} | pos={new_state['pos']}"
        )

    if not budget_ok:
        return ScenarioResult(
            mode=mode,
            latency_budget_s=cfg.latency_budget_s,
            seed=-1,
            ok=False,
            reason=f"latency budget exceeded step {step+1} ({elapsed*1000:.1f}ms > {cfg.latency_budget_s*1000:.0f}ms)",
            steps=step + 1,
            reached_goal=env.is_done(),
            step_records=records,
        )

    if not inv.ok:
        return ScenarioResult(
            mode=mode,
            latency_budget_s=cfg.latency_budget_s,
            seed=-1,
            ok=False,
            reason=f"invariant fail: {inv.reason}",
            steps=step + 1,
            reached_goal=env.is_done(),
            step_records=records,
        )

    state = new_state
    if env.is_done():
        return ScenarioResult(
            mode=mode,
            latency_budget_s=cfg.latency_budget_s,
            seed=-1,
            ok=True,
            reason="goal reached",
            steps=step + 1,
            reached_goal=True,
            step_records=records,
        )

return ScenarioResult(
    mode=mode,
    latency_budget_s=cfg.latency_budget_s,
    seed=-1,
    ok=False,
    reason="step budget exceeded",
    steps=cfg.max_steps,
    reached_goal=env.is_done(),
    step_records=records,
)
```

# —————————————————————————

# Sweep: find the crossover point

# —————————————————————————

@dataclass
class BudgetResult:
budget_ms: float
llm_only_completion_rate: float
hybrid_completion_rate: float
llm_only_mean_steps: float
hybrid_mean_steps: float
llm_only_p95_ms: float
hybrid_p95_ms: float

def percentile(data: List[float], p: float) -> float:
“”“Simple percentile without numpy.”””
if not data:
return 0.0
sorted_d = sorted(data)
k = (len(sorted_d) - 1) * (p / 100.0)
f = int(k)
c = f + 1 if f + 1 < len(sorted_d) else f
d = k - f
return sorted_d[f] + d * (sorted_d[c] - sorted_d[f])

def run_sweep(
*,
budgets_ms: List[float],
n_trials: int = 30,
world_size: int = 6,
hallucination_rate: float = 0.15,  # LOW ambiguity — key for this scenario
timings: ComponentTimings | None = None,
verbose: bool = False,
) -> List[BudgetResult]:
“””
Sweep latency budgets. For each budget, run n_trials with different seeds
in both modes. Collect completion rates and latency stats.
“””
if timings is None:
timings = ComponentTimings()

```
results: List[BudgetResult] = []

for budget_ms in budgets_ms:
    budget_s = budget_ms / 1000.0

    llm_completions = 0
    hybrid_completions = 0
    llm_steps_list: List[int] = []
    hybrid_steps_list: List[int] = []
    llm_latencies: List[float] = []
    hybrid_latencies: List[float] = []

    for trial in range(n_trials):
        seed = trial * 17 + 3  # deterministic but spread

        cfg = PrototypeConfig(
            max_steps=12,
            latency_budget_s=budget_s,
            verification_type="simulator",
            hallucination_rate=hallucination_rate,
            uncertainty_stop_threshold=0.90,
        )

        # LLM-only
        random.seed(seed)
        env1 = LineWorld(size=world_size)
        planner1 = DummyPlanner(cfg=cfg)
        r1 = run_latency_scenario(
            mode="llm_only", env=env1, planner=planner1,
            cfg=cfg, timings=timings, verbose=False,
        )
        if r1.reached_goal:
            llm_completions += 1
            llm_steps_list.append(r1.steps)
        for rec in r1.step_records:
            llm_latencies.append(rec.elapsed_s * 1000)

        # Hybrid
        random.seed(seed)
        env2 = LineWorld(size=world_size)
        planner2 = DummyPlanner(cfg=cfg)
        r2 = run_latency_scenario(
            mode="hybrid", env=env2, planner=planner2,
            cfg=cfg, timings=timings, verbose=False,
        )
        if r2.reached_goal:
            hybrid_completions += 1
            hybrid_steps_list.append(r2.steps)
        for rec in r2.step_records:
            hybrid_latencies.append(rec.elapsed_s * 1000)

    br = BudgetResult(
        budget_ms=budget_ms,
        llm_only_completion_rate=llm_completions / n_trials,
        hybrid_completion_rate=hybrid_completions / n_trials,
        llm_only_mean_steps=(sum(llm_steps_list) / len(llm_steps_list)) if llm_steps_list else float('inf'),
        hybrid_mean_steps=(sum(hybrid_steps_list) / len(hybrid_steps_list)) if hybrid_steps_list else float('inf'),
        llm_only_p95_ms=percentile(llm_latencies, 95) if llm_latencies else 0.0,
        hybrid_p95_ms=percentile(hybrid_latencies, 95) if hybrid_latencies else 0.0,
    )
    results.append(br)

return results
```

# —————————————————————————

# Main: run the full scenario and print analysis

# —————————————————————————

def main() -> None:
print(”=” * 78)
print(“COMMIT 3 — SCENARIO: HYBRID LOSES UNDER TIGHT LATENCY”)
print(”=” * 78)

```
timings = ComponentTimings(
    plan_delay_s=0.020,      # 20ms LLM inference
    verify_delay_s=0.015,    # 15ms invariant overhead
    observe_delay_s=0.025,   # 25ms world-model grounding
)

print(f"\nComponent timings:")
print(f"  plan (both modes):    {timings.plan_delay_s*1000:.0f}ms")
print(f"  verify (hybrid only): {timings.verify_delay_s*1000:.0f}ms")
print(f"  observe (hybrid only):{timings.observe_delay_s*1000:.0f}ms")
print(f"  => LLM-only step:     ~{timings.llm_only_step_cost*1000:.0f}ms")
print(f"  => Hybrid step:       ~{timings.hybrid_step_cost*1000:.0f}ms")
print(f"  => Hybrid overhead:   +{timings.hybrid_overhead*1000:.0f}ms per step")

# Sweep from very tight (25ms) to generous (120ms)
budgets = [25, 30, 35, 40, 45, 50, 55, 60, 70, 80, 100, 120]

print(f"\nSweeping {len(budgets)} latency budgets, 30 trials each, hallucination_rate=0.15 (low ambiguity)...")
print()

results = run_sweep(
    budgets_ms=budgets,
    n_trials=30,
    world_size=6,
    hallucination_rate=0.15,
    timings=timings,
)

# --- Print table ---
print(f"{'Budget':>8s}  {'LLM-only':>10s}  {'Hybrid':>10s}  {'LLM p95':>8s}  {'Hyb p95':>8s}  {'Winner':>10s}")
print(f"{'(ms)':>8s}  {'compl%':>10s}  {'compl%':>10s}  {'(ms)':>8s}  {'(ms)':>8s}  {'':>10s}")
print("-" * 68)

crossover_budget = None

for r in results:
    if r.llm_only_completion_rate > r.hybrid_completion_rate:
        winner = "LLM-only"
    elif r.hybrid_completion_rate > r.llm_only_completion_rate:
        winner = "Hybrid"
        if crossover_budget is None:
            crossover_budget = r.budget_ms
    else:
        winner = "Tie"

    print(
        f"{r.budget_ms:8.0f}  "
        f"{r.llm_only_completion_rate:10.1%}  "
        f"{r.hybrid_completion_rate:10.1%}  "
        f"{r.llm_only_p95_ms:8.1f}  "
        f"{r.hybrid_p95_ms:8.1f}  "
        f"{winner:>10s}"
    )

# --- Analysis ---
print("\n" + "=" * 78)
print("ANALYSIS")
print("=" * 78)

print(f"""
```

[FACT] Hybrid overhead per step = {timings.hybrid_overhead*1000:.0f}ms
(verify={timings.verify_delay_s*1000:.0f}ms + observe={timings.observe_delay_s*1000:.0f}ms)

[FACT] LLM-only minimum step cost = ~{timings.llm_only_step_cost*1000:.0f}ms
Hybrid minimum step cost    = ~{timings.hybrid_step_cost*1000:.0f}ms

[FACT] For budgets < {timings.hybrid_step_cost*1000:.0f}ms, hybrid CANNOT complete a single step.
LLM-only can still operate down to ~{timings.llm_only_step_cost*1000:.0f}ms.

[FACT] At low ambiguity (hallucination_rate=0.15), the accuracy benefit of
grounding is small — LLM-only is usually correct anyway.
“””)

```
if crossover_budget is not None:
    print(f"[FINDING] Crossover point: hybrid starts winning at ~{crossover_budget:.0f}ms budget.")
    print(f"          Below {crossover_budget:.0f}ms → LLM-only is the correct architecture choice.")
else:
    print("[FINDING] Hybrid never outperformed LLM-only in this low-ambiguity scenario.")
    print("          This is expected: overhead doesn't pay off when accuracy delta is small.")

print(f"""
```

[RECOMMENDATION FOR DECISION PROTOCOL]
IF task_ambiguity < LOW_THRESHOLD
AND latency_budget < {timings.hybrid_step_cost*1000:.0f}ms
THEN → LLM-only (hybrid overhead not justified)

IF task_ambiguity >= HIGH_THRESHOLD
OR cost_of_error >= HIGH
THEN → Hybrid (even with latency cost, grounding is worth it)

[HONEST LIMITATION]
These timings are simulated, not measured from real LLM inference.
Real-world overhead depends on: model size, verification complexity,
sensor latency, network round-trips. The PATTERN (crossover exists)
is the claim, not the specific millisecond values.
“””)

```
# --- Single verbose demo ---
print("=" * 78)
print("DETAILED DEMO: budget=35ms (hybrid should lose)")
print("=" * 78)

cfg_tight = PrototypeConfig(
    max_steps=12,
    latency_budget_s=0.035,
    verification_type="simulator",
    hallucination_rate=0.15,
    uncertainty_stop_threshold=0.90,
)

random.seed(42)
env_a = LineWorld(size=6)
p_a = DummyPlanner(cfg=cfg_tight)
run_latency_scenario(
    mode="llm_only", env=env_a, planner=p_a,
    cfg=cfg_tight, timings=timings, verbose=True,
)

random.seed(42)
env_b = LineWorld(size=6)
p_b = DummyPlanner(cfg=cfg_tight)
run_latency_scenario(
    mode="hybrid", env=env_b, planner=p_b,
    cfg=cfg_tight, timings=timings, verbose=True,
)
```

if **name** == “**main**”:
main()
