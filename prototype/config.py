cat > prototype/config.py <<'EOF'
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VerificationType = Literal["none", "invariants_only", "simulator"]


@dataclass(frozen=True)
class PrototypeConfig:
    # Hard safety budgets
    max_steps: int = 12
    max_context: int = 2048  # TODO: wire into planner context tracking (future commit)
    latency_budget_s: float = 0.250  # per-step time budget (seconds)

    # Verification / grounding
    verification_type: VerificationType = "simulator"

    # Behavior controls for the dummy "LLM"
    hallucination_rate: float = 0.30  # probability planner produces wrong predicted state
    uncertainty_stop_threshold: float = 0.80  # stop if uncertainty rises above this
EOF
