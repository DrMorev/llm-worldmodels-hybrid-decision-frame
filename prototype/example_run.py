from __future__ import annotations

import random

from .config import PrototypeConfig
from .loop_skeleton import DummyPlanner, LineWorld, run_loop


def main() -> None:
    # Deterministic-ish demo. Change seed to see different hallucination patterns.
    random.seed(7)

    cfg = PrototypeConfig(
        max_steps=10,
        latency_budget_s=0.250,
        verification_type="simulator",
        hallucination_rate=0.35,
        uncertainty_stop_threshold=0.90,
    )

    env1 = LineWorld(size=6)
    env2 = LineWorld(size=6)

    planner = DummyPlanner(cfg=cfg)

    r1 = run_loop(mode="llm_only", env=env1, planner=planner, cfg=cfg, verbose=True)
    r2 = run_loop(mode="hybrid", env=env2, planner=planner, cfg=cfg, verbose=True)

    print("\n=== SUMMARY ===")
    print(f"LLM-only: ok={r1.ok} steps={r1.steps} reached_goal={r1.reached_goal} reason={r1.reason}")
    print(f"Hybrid:   ok={r2.ok} steps={r2.steps} reached_goal={r2.reached_goal} reason={r2.reason}")

    print("\nNotes:")
    print("- LLM-only 'updates' from its own prediction, so hallucinated transitions can silently drift state.")
    print("- Hybrid grounds on simulator observation; invariants can stop the loop when uncertainty spikes.")
    print("- This is a toy scaffold to make tradeoffs explicit; it is not a benchmark and not a general claim.")


if __name__ == "__main__":
    main()
