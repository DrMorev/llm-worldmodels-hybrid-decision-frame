cat > prototype/loop_skeleton.py <<'EOF'
from __future__ import annotations

import random
import time
from dataclasses import dataclass
from typing import Dict, Tuple

from config import PrototypeConfig
from invariant_checks import InvariantResult, check_invariants


# --- Toy environment (acts as Simulator/Oracle) --------------------------------

@dataclass
class LineWorld:
    """1D world: position 0..N, goal at N."""
    size: int
    pos: int = 0

    def reset(self) -> Dict[str, int]:
        self.pos = 0
        return {"pos": self.pos, "goal": self.size}

    def step(self, action: str) -> Dict[str, int]:
        if action == "LEFT":
            self.pos = max(0, self.pos - 1)
        elif action == "RIGHT":
            self.pos = min(self.size, self.pos + 1)
        else:
            raise ValueError(f"Invalid action: {action}")
        return {"pos": self.pos, "goal": self.size}

    def is_done(self) -> bool:
        return self.pos >= self.size


# --- Dummy planner (stand-in for "LLM") ----------------------------------------

@dataclass
class DummyPlanner:
    """Produces an action and a *predicted* next state, with optional hallucinations."""
    cfg: PrototypeConfig

    def plan(self, state: Dict[str, int]) -> Tuple[str, Dict[str, int], float]:
        """
        Returns:
          action: LEFT/RIGHT
          predicted_next_state: what planner *thinks* will happen
          uncertainty: float in [0,1]
        """
        pos = state["pos"]
        goal = state["goal"]
        remaining = max(0, goal - pos)

        # Simple intention: move RIGHT until goal.
        action = "RIGHT" if remaining > 0 else "LEFT"

        # Toy uncertainty: increases with remaining steps; spikes on hallucination.
        uncertainty = min(1.0, 0.15 + (0.05 * remaining))

        # Predicted next state (can hallucinate)
        predicted = {"pos": pos, "goal": goal}
        predicted["pos"] = min(goal, pos + 1) if action == "RIGHT" else max(0, pos - 1)

        # Hallucination: sometimes claim a wrong state transition.
        # Example: "I moved RIGHT by +2" or "I already reached goal".
        if random.random() < self.cfg.hallucination_rate:
            uncertainty = min(1.0, uncertainty + 0.60)
            if random.random() < 0.5:
                predicted["pos"] = min(goal, pos + 2)
            else:
                predicted["pos"] = goal  # premature success claim

        return action, predicted, uncertainty


# --- Loop skeleton -------------------------------------------------------------

@dataclass
class LoopResult:
    ok: bool
    reason: str
    steps: int
    reached_goal: bool


def run_loop(
    *,
    mode: str,
    env: LineWorld,
    planner: DummyPlanner,
    cfg: PrototypeConfig,
    verbose: bool = True,
) -> LoopResult:
    """
    mode:
      - "llm_only": uses planner's predicted state as truth (self-grounding).
      - "hybrid": uses simulator observation as truth (grounding), with invariants.
    """
    assert mode in {"llm_only", "hybrid"}

    state = env.reset()
    uncertainty = 0.0

    if verbose:
        print(f"\n=== RUN: {mode.upper()} ===")
        print(f"init state: {state}")

    for step in range(cfg.max_steps):
        t0 = time.perf_counter()

        # PLAN
        action, predicted_next, uncertainty = planner.plan(state)

        # ACT + OBSERVE
        observed_next = env.step(action)

        # UPDATE (key difference)
        if mode == "llm_only":
            # Self-grounding: treat prediction as truth, ignoring observation.
            new_state = predicted_next
        else:
            # Grounding: observed state is truth source.
            new_state = observed_next

        # CHECK INVARIANTS
        inv: InvariantResult = check_invariants(
            action=action,
            state=new_state,
            world_size=env.size,
            step=step,
            max_steps=cfg.max_steps,
            uncertainty=uncertainty,
            uncertainty_stop_threshold=cfg.uncertainty_stop_threshold,
        )

        # LATENCY BUDGET
        elapsed = time.perf_counter() - t0
        if elapsed > cfg.latency_budget_s:
            return LoopResult(
                ok=False,
                reason=f"latency budget exceeded ({elapsed:.3f}s > {cfg.latency_budget_s:.3f}s)",
                steps=step + 1,
                reached_goal=env.is_done(),
            )

        if verbose:
            print(
                f"step {step+1:02d} | action={action:5s} | "
                f"pred={predicted_next['pos']:2d} | obs={observed_next['pos']:2d} | "
                f"use={'pred' if mode=='llm_only' else 'obs':3s} -> state={new_state['pos']:2d} | "
                f"uncert={uncertainty:.2f} | inv_ok={inv.ok}"
            )
            if not inv.ok:
                print(f"  invariant fail: {inv.reason}")

        if not inv.ok:
            return LoopResult(
                ok=False,
                reason=f"invariant fail: {inv.reason}",
                steps=step + 1,
                reached_goal=env.is_done(),
            )

        state = new_state

        if env.is_done():
            return LoopResult(
                ok=True,
                reason="goal reached",
                steps=step + 1,
                reached_goal=True,
            )

    return LoopResult(
        ok=False,
        reason="step budget exceeded",
        steps=cfg.max_steps,
        reached_goal=env.is_done(),
    )
EOF
