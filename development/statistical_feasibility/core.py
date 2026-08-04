"""Core immutable data structures for the development-only prototype."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from types import MappingProxyType
from typing import Dict, Iterable, Mapping, Optional, Sequence, Tuple


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


STAGE1_SCENARIOS: Tuple[str, ...] = (
    "no_shared_fragile_mechanism",
    "fragility_unrelated_to_error",
    "stable_shared_false_belief",
    "constant_ppi",
    "permuted_ppi",
    "low_shared_fragile_mechanism",
    "mixed_fragile_and_stable_failure",
    "maximally_favourable_fragile_mechanism",
)
STAGE1_SCORE_KEYS: Tuple[str, ...] = ("ppi_k8", "ppi_k4", "confidence_margin")


@dataclass(frozen=True)
class ObservableScoreItem:
    """One audit-policy item with named observable scores and no hidden fields."""

    item_id: str
    score_channels: Tuple[Tuple[str, float], ...]

    def __post_init__(self) -> None:
        if not self.item_id:
            raise ValueError("item_id must be non-empty")
        keys = tuple(key for key, _ in self.score_channels)
        if len(set(keys)) != len(keys):
            raise ValueError("observable score-channel keys must be unique")
        if set(keys) != set(STAGE1_SCORE_KEYS):
            raise ValueError("Stage 1 observable score channels are incomplete")
        for key, value in self.score_channels:
            if not key or not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("observable scores must be finite and lie in [0, 1]")

    def scores(self) -> Mapping[str, float]:
        return MappingProxyType(dict(self.score_channels))


@dataclass(frozen=True)
class NamedFinitePopulation:
    """Paired Stage 1 population with policy-visible scores and runner-only outcomes."""

    scenario_id: str
    items: Tuple[ObservableScoreItem, ...]
    evaluator_outcomes: Tuple[Tuple[str, int], ...]

    def __post_init__(self) -> None:
        if not self.scenario_id or not self.items:
            raise ValueError("named population must have a scenario and items")
        item_ids = tuple(item.item_id for item in self.items)
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("named population item IDs must be unique")
        outcome_ids = tuple(item_id for item_id, _ in self.evaluator_outcomes)
        if outcome_ids != item_ids:
            raise ValueError("runner-only outcomes must follow the observable item order")
        if any(value not in (0, 1) for _, value in self.evaluator_outcomes):
            raise ValueError("runner-only outcomes must be binary")

    @property
    def size(self) -> int:
        return len(self.items)

    @property
    def true_prevalence(self) -> float:
        return sum(value for _, value in self.evaluator_outcomes) / self.size

    def item_ids(self) -> Tuple[str, ...]:
        return tuple(item.item_id for item in self.items)

    def observable_score_vector(self, key: str) -> Mapping[str, float]:
        if key not in STAGE1_SCORE_KEYS:
            raise ValueError(f"unknown observable score channel: {key}")
        return MappingProxyType(
            {item.item_id: item.scores()[key] for item in self.items}
        )

    def all_observable_scores(self) -> Mapping[str, Mapping[str, float]]:
        return MappingProxyType(
            {key: self.observable_score_vector(key) for key in STAGE1_SCORE_KEYS}
        )

    def hidden_outcomes(self) -> Mapping[str, int]:
        """Runner-only oracle map; never pass this object to score or sampling APIs."""

        return MappingProxyType(dict(self.evaluator_outcomes))


@dataclass(frozen=True)
class Stage1ArmSpec:
    arm_id: str
    conceptual_arm: str
    sampling_policy: str
    sampling_score_key: Optional[str]
    control_variate_score_key: Optional[str]
    epsilon_samp: Optional[float]

    def validate(self) -> None:
        if self.conceptual_arm not in {"U0", "UM", "UP", "SM", "SP"}:
            raise ValueError("unknown Stage 1 conceptual arm")
        if self.sampling_policy == "uniform":
            if self.sampling_score_key is not None or self.epsilon_samp is not None:
                raise ValueError("uniform arms must not declare a sampling score or epsilon")
        elif self.sampling_policy == "score_informed":
            if self.sampling_score_key not in STAGE1_SCORE_KEYS:
                raise ValueError("score-informed arms require a named observable score")
            if self.epsilon_samp is None or not 0.0 < self.epsilon_samp <= 1.0:
                raise ValueError("score-informed arms require positive exploration")
        else:
            raise ValueError("unknown Stage 1 sampling policy")
        if (
            self.control_variate_score_key is not None
            and self.control_variate_score_key not in STAGE1_SCORE_KEYS
        ):
            raise ValueError("unknown control-variate score channel")


@dataclass(frozen=True)
class Stage1Config:
    """Engineering-only Stage 1 plumbing configuration; never confirmatory."""

    population_size: int = 200
    budget: int = 20
    replicates: int = 10
    ks: Tuple[int, ...] = (8, 4)
    epsilon_samp: float = 0.20
    lambda_grid: Tuple[float, ...] = (0.05, 0.10, 0.25, 0.50)
    alpha_cs: float = 0.05
    ridge: float = 1e-6
    tau_primary: float = 0.25
    tau_verifier: float = 0.25
    normalization_primary: float = 3.0
    normalization_verifier: float = 3.0
    master_seed: int = 20260804
    inversion_tolerance: float = 1e-10
    monotonicity_tolerance: float = 1e-10
    scenario_ids: Tuple[str, ...] = STAGE1_SCENARIOS
    compact_limit_bytes: int = 100 * 1024 * 1024
    trace_limit_bytes: int = 250 * 1024 * 1024
    maximum_generated_candidates: int = 5000
    manifest_type: str = "development_only_ppi_stage1"
    schema_version: str = "ppi-stage1-v2"

    def validate(self) -> None:
        if self.manifest_type != "development_only_ppi_stage1":
            raise ValueError("confirmatory or unknown manifests are forbidden")
        if self.population_size <= 0 or not 0 <= self.budget <= self.population_size:
            raise ValueError("Stage 1 population and budget are invalid")
        if self.replicates <= 0:
            raise ValueError("Stage 1 replicates must be positive")
        if not self.ks or any(k not in (4, 8) for k in self.ks):
            raise ValueError("Stage 1 K must be 8 or 4")
        if len(set(self.ks)) != len(self.ks):
            raise ValueError("Stage 1 K values must be unique")
        if not 0.0 < self.epsilon_samp <= 1.0:
            raise ValueError("epsilon_samp must lie in (0, 1]")
        if not self.lambda_grid or any(
            not math.isfinite(value) or not 0.0 < value <= 0.50
            for value in self.lambda_grid
        ):
            raise ValueError("Stage 1 lambda grid is invalid")
        if len(set(self.lambda_grid)) != len(self.lambda_grid):
            raise ValueError("Stage 1 lambda values must be unique")
        if not 0.0 < self.alpha_cs < 1.0:
            raise ValueError("alpha_cs must lie in (0, 1)")
        if self.ridge <= 0.0 or not math.isfinite(self.ridge):
            raise ValueError("ridge must be finite and positive")
        if self.tau_primary != self.tau_verifier:
            raise ValueError("Stage 1 requires one common agreement threshold")
        for threshold, normalization in (
            (self.tau_primary, self.normalization_primary),
            (self.tau_verifier, self.normalization_verifier),
        ):
            if not all(math.isfinite(value) for value in (threshold, normalization)):
                raise ValueError("confidence constants must be finite")
            if normalization <= threshold:
                raise ValueError("confidence normalization must exceed threshold")
        if not self.scenario_ids or any(
            scenario_id not in STAGE1_SCENARIOS for scenario_id in self.scenario_ids
        ):
            raise ValueError("unknown Stage 1 scenario")
        if len(set(self.scenario_ids)) != len(self.scenario_ids):
            raise ValueError("Stage 1 scenario IDs must be unique")
        if self.compact_limit_bytes <= 0 or self.trace_limit_bytes <= 0:
            raise ValueError("artifact limits must be positive")
        if self.maximum_generated_candidates < self.population_size:
            raise ValueError("generated-candidate ceiling must cover the population")
        for tolerance in (self.inversion_tolerance, self.monotonicity_tolerance):
            if tolerance <= 0.0 or not math.isfinite(tolerance):
                raise ValueError("Stage 1 tolerances must be finite and positive")


def stage1_arms(k: int, epsilon_samp: float) -> Tuple[Stage1ArmSpec, ...]:
    if k not in (4, 8):
        raise ValueError("Stage 1 arm K must be 8 or 4")
    ppi_key = f"ppi_k{k}"
    epsilon_identifier = f"{epsilon_samp:.12g}".replace(".", "p")
    arms = (
        Stage1ArmSpec(f"U0_k{k}", "U0", "uniform", None, None, None),
        Stage1ArmSpec(
            f"UM_k{k}", "UM", "uniform", None, "confidence_margin", None
        ),
        Stage1ArmSpec(f"UP_k{k}", "UP", "uniform", None, ppi_key, None),
        Stage1ArmSpec(
            f"SM_k{k}_epsilon_{epsilon_identifier}",
            "SM",
            "score_informed",
            "confidence_margin",
            "confidence_margin",
            epsilon_samp,
        ),
        Stage1ArmSpec(
            f"SP_k{k}_epsilon_{epsilon_identifier}",
            "SP",
            "score_informed",
            ppi_key,
            ppi_key,
            epsilon_samp,
        ),
    )
    for arm in arms:
        arm.validate()
    return arms
