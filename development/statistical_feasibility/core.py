"""Core immutable data structures for the development-only prototype."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from types import MappingProxyType
from typing import Iterable, Mapping, Optional, Sequence, Tuple


@dataclass(frozen=True)
class PopulationItem:
    item_id: str
    score: float
    outcome: int
    scenario_label: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must be non-empty")
        if not math.isfinite(self.score) or not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be finite and lie in [0, 1]")
        if self.outcome not in (0, 1):
            raise ValueError("outcome must be binary")


@dataclass(frozen=True)
class FinitePopulation:
    fixture: str
    items: Tuple[PopulationItem, ...]

    def __post_init__(self) -> None:
        if not self.items:
            raise ValueError("population must be non-empty")
        item_ids = tuple(item.item_id for item in self.items)
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("item IDs must be unique")

    @property
    def size(self) -> int:
        return len(self.items)

    @property
    def true_prevalence(self) -> float:
        return sum(item.outcome for item in self.items) / self.size

    def item_ids(self) -> Tuple[str, ...]:
        return tuple(item.item_id for item in self.items)

    def observable_scores(self) -> Mapping[str, float]:
        return MappingProxyType({item.item_id: item.score for item in self.items})

    def hidden_outcomes(self) -> Mapping[str, int]:
        """Runner-only oracle map; sampling functions never receive this mapping."""
        return MappingProxyType({item.item_id: item.outcome for item in self.items})


@dataclass(frozen=True)
class ArmSpec:
    """One instantiated configuration in the four-arm development design."""

    name: str
    policy: str
    use_control_variate: bool
    gamma: Optional[float]
    conceptual_label: str = ""


@dataclass(frozen=True)
class SmokeConfig:
    population_size: int = 200
    budget: int = 50
    audit_risk: float = 0.05
    ordinary_replicates: int = 50
    gammas: Tuple[float, ...] = (0.10, 0.50)
    ridge: float = 1e-6
    lambdas: Tuple[float, ...] = (0.05, 0.10, 0.25, 0.50)
    master_seed: int = 20260803
    inversion_tolerance: float = 1e-10
    probability_tolerance: float = 1e-12
    monotonicity_tolerance: float = 1e-10

    def validate(self) -> None:
        if self.population_size <= 0:
            raise ValueError("population_size must be positive")
        if self.budget < 0 or self.budget > self.population_size:
            raise ValueError("budget must lie in [0, population_size]")
        if not 0.0 < self.audit_risk < 1.0:
            raise ValueError("audit_risk must lie in (0, 1)")
        if self.ordinary_replicates <= 0:
            raise ValueError("ordinary_replicates must be positive")
        if self.ridge <= 0.0 or not math.isfinite(self.ridge):
            raise ValueError("ridge must be finite and positive")
        for gamma in self.gammas:
            if not 0.0 < gamma <= 1.0:
                raise ValueError("gamma must lie in (0, 1]")
        for fixed_lambda in self.lambdas:
            if not 0.0 < fixed_lambda <= 0.50:
                raise ValueError("fixed lambda must lie in (0, 0.50]")
        for tolerance in (
            self.inversion_tolerance,
            self.probability_tolerance,
            self.monotonicity_tolerance,
        ):
            if tolerance <= 0.0 or not math.isfinite(tolerance):
                raise ValueError("tolerances must be finite and positive")


def development_arms(gammas: Sequence[float]) -> Tuple[ArmSpec, ...]:
    arms = [
        ArmSpec("A_uniform_no_cv", "uniform", False, None, "A_uniform_no_cv"),
        ArmSpec("B_uniform_cv", "uniform", True, None, "B_uniform_cv"),
    ]
    for gamma in gammas:
        gamma_identifier = f"{gamma:.12g}".replace(".", "p")
        arms.extend(
            (
                ArmSpec(
                    f"C_score_no_cv_gamma_{gamma_identifier}",
                    "score_informed",
                    False,
                    gamma,
                    "C_score_no_cv",
                ),
                ArmSpec(
                    f"D_score_cv_gamma_{gamma_identifier}",
                    "score_informed",
                    True,
                    gamma,
                    "D_score_cv",
                ),
            )
        )
    return tuple(arms)


def stable_seed(master_seed: int, *parts: object) -> int:
    material = "|".join((str(master_seed), *(str(part) for part in parts)))
    return int.from_bytes(hashlib.sha256(material.encode("utf-8")).digest()[:8], "big")


def digest_rows(rows: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(repr(row).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()
