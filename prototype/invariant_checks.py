from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class InvariantResult:
    ok: bool
    reason: str = ""
    stop: bool = False


def reject_format_violations(action: Any) -> InvariantResult:
    if not isinstance(action, str):
        return InvariantResult(False, "action must be a string", stop=True)
    if action not in {"LEFT", "RIGHT"}:
        return InvariantResult(False, f"unknown action '{action}'", stop=True)
    return InvariantResult(True)


def reject_impossible_state(state: Dict[str, Any], world_size: int) -> InvariantResult:
    if not isinstance(state, dict):
        return InvariantResult(False, "state must be a dict", stop=True)

    if "pos" not in state or "goal" not in state:
        return InvariantResult(False, "state missing required keys", stop=True)

    pos = state.get("pos")
    goal = state.get("goal")

    if not isinstance(pos, int) or not isinstance(goal, int):
        return InvariantResult(False, "pos and goal must be ints", stop=True)

    if not (0 <= pos <= world_size):
        return InvariantResult(False, f"pos out of bounds: {pos}", stop=True)

    if goal != world_size:
        return InvariantResult(False, f"goal must equal world_size ({world_size})", stop=True)

    return InvariantResult(True)


def stop_condition(
    step: int,
    max_steps: int,
    uncertainty: float,
    uncertainty_stop_threshold: float,
) -> InvariantResult:
    if step >= max_steps:
        return InvariantResult(False, "step budget exceeded", stop=True)
    if uncertainty >= uncertainty_stop_threshold:
        return InvariantResult(False, f"uncertainty too high ({uncertainty:.2f})", stop=True)
    return InvariantResult(True)


def check_invariants(
    *,
    action: Any,
    state: Dict[str, Any],
    world_size: int,
    step: int,
    max_steps: int,
    uncertainty: float,
    uncertainty_stop_threshold: float,
) -> InvariantResult:
    r = reject_format_violations(action)
    if not r.ok:
        return r

    r = reject_impossible_state(state, world_size)
    if not r.ok:
        return r

    r = stop_condition(step, max_steps, uncertainty, uncertainty_stop_threshold)
    if not r.ok:
        return r

    return InvariantResult(True)
