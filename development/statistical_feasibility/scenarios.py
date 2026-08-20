"""Deterministic synthetic development fixtures; not models of verifier behavior."""

from __future__ import annotations

from dataclasses import dataclass, replace
import math
import random
from typing import Dict, List, Mapping, Sequence, Tuple

from .core import (
    FinitePopulation,
    NamedFinitePopulation,
    ObservableScoreItem,
    PopulationItem,
    Stage1Config,
    Stage2Config,
    stable_seed,
)
from .proxies import (
    FrozenTransformationBank,
    ObservableCaseOutputs,
    StructuralRepresentation,
    compute_confidence_margin,
    frozen_transformation_bank,
    ppi_from_observable_outputs,
)


ORDINARY_FIXTURES: Tuple[str, ...] = (
    "constant_score",
    "independent_score",
    "informative_score",
    "anti_informative_score",
    "tied_score",
)
DETERMINISTIC_FIXTURES: Tuple[str, ...] = ("all_correct", "all_error")
ALL_FIXTURES = ORDINARY_FIXTURES + DETERMINISTIC_FIXTURES


def _bernoulli(rng: random.Random, probability: float) -> int:
    return int(rng.random() < probability)


def generate_fixture(name: str, population_size: int, seed: int) -> FinitePopulation:
    if name not in ALL_FIXTURES:
        raise ValueError(f"unknown fixture: {name}")
    if population_size <= 0:
        raise ValueError("population_size must be positive")
    score_rng = random.Random(stable_seed(seed, name, "scores"))
    outcome_rng = random.Random(stable_seed(seed, name, "outcomes"))
    items = []
    for index in range(population_size):
        if name == "constant_score":
            score = 0.5
            probability = 0.10
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "independent_score":
            score = score_rng.random()
            probability = 0.10
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "informative_score":
            score = score_rng.random()
            probability = 0.02 + 0.46 * score
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "anti_informative_score":
            score = score_rng.random()
            probability = 0.02 + 0.46 * (1.0 - score)
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "tied_score":
            score = (0.0, 0.25, 0.5, 0.75, 1.0)[score_rng.randrange(5)]
            probability = 0.10
            outcome = _bernoulli(outcome_rng, probability)
        elif name == "all_correct":
            score = score_rng.random()
            outcome = 0
        else:
            score = score_rng.random()
            outcome = 1
        items.append(
            PopulationItem(
                item_id=f"item-{index:04d}",
                score=score,
                outcome=outcome,
                scenario_label=f"development-only:{name}",
            )
        )
    return FinitePopulation(name, tuple(items))


FRAGILE_WEIGHTS: Tuple[float, ...] = (0.08, 0.12, 0.16, 0.20, 0.24, 0.28, 0.32, 0.36)
ROBUST_COEFFICIENT = 2.50
FRAGILE_COEFFICIENT = 1.00
STABLE_FALSE_BELIEF_COEFFICIENT = 4.80
COMPONENT_ERROR_HALF_RANGE = 0.05
FRAGILE_BASE_MAGNITUDE = 1.55


@dataclass(frozen=True)
class Stage1ScenarioSpec:
    scenario_id: str
    pi_h: float
    stable_false_belief_rate: float
    unrelated_fragility: bool = False
    permute_ppi: bool = False


STAGE1_SCENARIO_SPECS: Mapping[str, Stage1ScenarioSpec] = {
    "no_shared_fragile_mechanism": Stage1ScenarioSpec(
        "no_shared_fragile_mechanism", 0.0, 0.10
    ),
    "fragility_unrelated_to_error": Stage1ScenarioSpec(
        "fragility_unrelated_to_error", 0.50, 0.0, unrelated_fragility=True
    ),
    "stable_shared_false_belief": Stage1ScenarioSpec(
        "stable_shared_false_belief", 0.0, 0.40
    ),
    "constant_ppi": Stage1ScenarioSpec("constant_ppi", 0.0, 0.20),
    "permuted_ppi": Stage1ScenarioSpec(
        "permuted_ppi", 0.50, 0.10, permute_ppi=True
    ),
    "low_shared_fragile_mechanism": Stage1ScenarioSpec(
        "low_shared_fragile_mechanism", 0.25, 0.0
    ),
    "mixed_fragile_and_stable_failure": Stage1ScenarioSpec(
        "mixed_fragile_and_stable_failure", 0.50, 0.25
    ),
    "maximally_favourable_fragile_mechanism": Stage1ScenarioSpec(
        "maximally_favourable_fragile_mechanism", 1.0, 0.0
    ),
}

STAGE1_ACCEPTANCE_CHECK_SEEDS: Tuple[int, ...] = (
    91001, 91002, 91003, 91004, 91005,
    91006, 91007, 91008, 91009, 91010,
)


@dataclass(frozen=True)
class Stage1CausalCase:
    """Generator/evaluator-only record; never passed to sampling or CV APIs."""

    item_id: str
    representation: StructuralRepresentation
    h_i: int
    stable_false_belief: int
    primary_error_term: float
    verifier_error_term: float
    primary_logit: float
    verifier_logit: float
    agreement_region: bool
    joint_dangerous_error: int


@dataclass(frozen=True)
class GeneratedStage1Population:
    population: NamedFinitePopulation
    causal_cases: Tuple[Stage1CausalCase, ...]
    observable_outputs: Tuple[ObservableCaseOutputs, ...]
    collider_diagnostic: Mapping[str, object]
    scenario_manifest: Mapping[str, object]
    component_evaluation_count: int
    identity_sentinel_passed: bool
    structural_invariance_passed: bool


@dataclass(frozen=True)
class Stage1AcceptanceCheck:
    """Acceptance-only validation record; it intentionally exposes no hidden fields."""

    scenario_id: str
    seed: int
    accepted_candidate_count: int
    generated_candidate_count: int
    acceptance_rate: float
    selection_neutral_null: bool


def _component_logit(
    representation: StructuralRepresentation,
    h_i: int,
    stable_false_belief: int,
    component_error: float,
    robust_coefficient: float = ROBUST_COEFFICIENT,
) -> float:
    truth_sign = 1.0 if representation.truth == 1 else -1.0
    fragile_value = math.fsum(
        weight * value
        for weight, value in zip(FRAGILE_WEIGHTS, representation.fragile_surface)
    )
    return (
        robust_coefficient * representation.robust_feature
        + h_i * FRAGILE_COEFFICIENT * fragile_value
        - stable_false_belief * STABLE_FALSE_BELIEF_COEFFICIENT * truth_sign
        + component_error
    )


def _binary_output(logit: float) -> int:
    if not math.isfinite(logit):
        raise ValueError("component logit must be finite")
    return int(logit >= 0.0)


def _pearson_association(pairs: Sequence[Tuple[float, float]]) -> float:
    if len(pairs) < 2:
        return 0.0
    left_mean = math.fsum(left for left, _ in pairs) / len(pairs)
    right_mean = math.fsum(right for _, right in pairs) / len(pairs)
    covariance = math.fsum(
        (left - left_mean) * (right - right_mean) for left, right in pairs
    )
    left_variance = math.fsum((left - left_mean) ** 2 for left, _ in pairs)
    right_variance = math.fsum((right - right_mean) ** 2 for _, right in pairs)
    denominator = math.sqrt(left_variance * right_variance)
    return 0.0 if denominator == 0.0 else covariance / denominator


def _observable_stratum(
    item: ObservableScoreItem, outputs: ObservableCaseOutputs
) -> Tuple[int, int]:
    confidence = item.scores()["confidence_margin"]
    confidence_bucket = min(3, int(confidence * 4.0))
    return outputs.original_primary_output, confidence_bucket


def permute_ppi_within_observable_strata(
    items: Sequence[ObservableScoreItem],
    outputs: Sequence[ObservableCaseOutputs],
) -> Tuple[ObservableScoreItem, ...]:
    """Rotate PPI within strata defined only by observable output and margin."""

    if len(items) != len(outputs):
        raise ValueError("items and observable outputs must align")
    groups: Dict[Tuple[int, int], List[int]] = {}
    for index, (item, output) in enumerate(zip(items, outputs)):
        groups.setdefault(_observable_stratum(item, output), []).append(index)
    replacements: Dict[int, Tuple[float, float]] = {}
    for indices in groups.values():
        ordered = sorted(indices, key=lambda index: items[index].item_id)
        source = ordered[-1:] + ordered[:-1]
        for destination, source_index in zip(ordered, source):
            source_scores = items[source_index].scores()
            replacements[destination] = (
                source_scores["ppi_k8"],
                source_scores["ppi_k4"],
            )
    result = []
    for index, item in enumerate(items):
        ppi_k8, ppi_k4 = replacements[index]
        result.append(
            ObservableScoreItem(
                item.item_id,
                (
                    ("ppi_k8", ppi_k8),
                    ("ppi_k4", ppi_k4),
                    ("confidence_margin", item.scores()["confidence_margin"]),
                ),
            )
        )
    return tuple(result)


def permute_ppi_globally(
    items: Sequence[ObservableScoreItem], seed: int
) -> Tuple[ObservableScoreItem, ...]:
    """Permute the observable PPI multiset without strata or hidden fields."""

    source_indices = list(range(len(items)))
    random.Random(stable_seed(seed, "global-permuted-ppi")).shuffle(source_indices)
    result = []
    for item, source_index in zip(items, source_indices):
        source_scores = items[source_index].scores()
        result.append(
            ObservableScoreItem(
                item.item_id,
                (
                    ("ppi_k8", source_scores["ppi_k8"]),
                    ("ppi_k4", source_scores["ppi_k4"]),
                    ("confidence_margin", item.scores()["confidence_margin"]),
                ),
            )
        )
    return tuple(result)


def stage1_engineering_constants(
    robust_coefficient: float = ROBUST_COEFFICIENT,
    classification: str = "engineering-only; not Stage 2 or confirmatory values",
) -> Mapping[str, object]:
    return {
        "robust_coefficient": robust_coefficient,
        "fragile_coefficient_primary": FRAGILE_COEFFICIENT,
        "fragile_coefficient_verifier": FRAGILE_COEFFICIENT,
        "stable_false_belief_coefficient": STABLE_FALSE_BELIEF_COEFFICIENT,
        "component_error_half_range": COMPONENT_ERROR_HALF_RANGE,
        "fragile_base_magnitude": FRAGILE_BASE_MAGNITUDE,
        "fragile_weights": list(FRAGILE_WEIGHTS),
        "classification": classification,
    }


def generate_stage1_population(
    scenario_id: str,
    population_size: int,
    seed: int,
    config: Stage1Config,
    bank: FrozenTransformationBank | None = None,
    scenario_spec: Stage1ScenarioSpec | None = None,
    robust_coefficient: float = ROBUST_COEFFICIENT,
    constant_ppi: bool = False,
    manifest_classification: str = "Stage 1 engineering-only",
) -> GeneratedStage1Population:
    """Generate structural outputs first, then derive PPI and hidden error labels."""

    config.validate()
    if scenario_spec is None and scenario_id not in STAGE1_SCENARIO_SPECS:
        raise ValueError(f"unknown Stage 1 scenario: {scenario_id}")
    if population_size <= 0:
        raise ValueError("Stage 1 population size must be positive")
    spec = scenario_spec or STAGE1_SCENARIO_SPECS[scenario_id]
    if not math.isfinite(robust_coefficient) or robust_coefficient <= 0.0:
        raise ValueError("robust coefficient must be finite and positive")
    bank = bank or frozen_transformation_bank()
    rng = random.Random(stable_seed(seed, scenario_id, "causal-generator"))
    selected_cases: List[Stage1CausalCase] = []
    selected_outputs: List[ObservableCaseOutputs] = []
    selected_items: List[ObservableScoreItem] = []
    all_error_pairs: List[Tuple[float, float]] = []
    selected_error_pairs: List[Tuple[float, float]] = []
    candidate_index = 0
    identity_passed = True
    invariance_passed = True
    while len(selected_cases) < population_size:
        if candidate_index >= config.maximum_generated_candidates:
            raise RuntimeError("could not construct the requested agreement population")
        canonical_state = 1 if rng.random() < 0.5 else -1
        truth = int(canonical_state == 1)
        truth_sign = float(canonical_state)
        robust_feature = truth_sign
        h_i = int(rng.random() < spec.pi_h)
        stable_false = int(rng.random() < spec.stable_false_belief_rate)
        primary_error = rng.uniform(-COMPONENT_ERROR_HALF_RANGE, COMPONENT_ERROR_HALF_RANGE)
        verifier_error = rng.uniform(-COMPONENT_ERROR_HALF_RANGE, COMPONENT_ERROR_HALF_RANGE)
        all_error_pairs.append((primary_error, verifier_error))
        if spec.unrelated_fragility:
            surface_sign = 1.0 if rng.random() < 0.5 else -1.0
        else:
            surface_sign = -truth_sign
        fragile_surface = tuple(
            surface_sign * (FRAGILE_BASE_MAGNITUDE + 0.01 * ((candidate_index + index) % 3))
            for index in range(8)
        )
        representation = StructuralRepresentation(
            canonical_state=canonical_state,
            truth=truth,
            robust_feature=robust_feature,
            fragile_surface=fragile_surface,
        )
        primary_logit = _component_logit(
            representation, h_i, stable_false, primary_error, robust_coefficient
        )
        verifier_logit = _component_logit(
            representation, h_i, stable_false, verifier_error, robust_coefficient
        )
        primary_output = _binary_output(primary_logit)
        verifier_output = _binary_output(verifier_logit)
        transformed_primary = []
        transformed_verifier = []
        transformed_representations = []
        for transformation in bank.transformations:
            transformed = transformation.apply(representation)
            transformed_representations.append(transformed)
            invariance_passed = invariance_passed and (
                transformed.canonical_state == representation.canonical_state
                and transformed.truth == representation.truth
                and transformed.robust_feature == representation.robust_feature
            )
            transformed_primary.append(
                _binary_output(
                    _component_logit(
                        transformed,
                        h_i,
                        stable_false,
                        primary_error,
                        robust_coefficient,
                    )
                )
            )
            transformed_verifier.append(
                _binary_output(
                    _component_logit(
                        transformed,
                        h_i,
                        stable_false,
                        verifier_error,
                        robust_coefficient,
                    )
                )
            )
        if len(set(item.fragile_surface for item in transformed_representations)) != 8:
            raise AssertionError("frozen transformations are not mutually non-identical")
        identity = bank.identity(representation)
        identity_passed = identity_passed and identity == representation
        agreement_region = (
            primary_output == verifier_output
            and abs(primary_logit) >= config.tau_primary
            and abs(verifier_logit) >= config.tau_verifier
        )
        if agreement_region:
            item_id = f"{scenario_id}-item-{len(selected_cases):04d}"
            observable = ObservableCaseOutputs(
                item_id=item_id,
                original_primary_output=primary_output,
                original_verifier_output=verifier_output,
                original_primary_magnitude=abs(primary_logit),
                original_verifier_magnitude=abs(verifier_logit),
                transformed_primary_outputs=tuple(transformed_primary),
                transformed_verifier_outputs=tuple(transformed_verifier),
            )
            ppi_k8 = ppi_from_observable_outputs(observable, bank, 8).score
            ppi_k4 = ppi_from_observable_outputs(observable, bank, 4).score
            confidence_margin = compute_confidence_margin(
                observable.original_primary_magnitude,
                observable.original_verifier_magnitude,
                config.tau_primary,
                config.tau_verifier,
                config.normalization_primary,
                config.normalization_verifier,
            )
            dangerous_error = int(primary_output != truth)
            selected_cases.append(
                Stage1CausalCase(
                    item_id=item_id,
                    representation=representation,
                    h_i=h_i,
                    stable_false_belief=stable_false,
                    primary_error_term=primary_error,
                    verifier_error_term=verifier_error,
                    primary_logit=primary_logit,
                    verifier_logit=verifier_logit,
                    agreement_region=True,
                    joint_dangerous_error=dangerous_error,
                )
            )
            selected_outputs.append(observable)
            selected_items.append(
                ObservableScoreItem(
                    item_id,
                    (
                        ("ppi_k8", ppi_k8),
                        ("ppi_k4", ppi_k4),
                        ("confidence_margin", confidence_margin),
                    ),
                )
            )
            selected_error_pairs.append((primary_error, verifier_error))
        candidate_index += 1
    if spec.permute_ppi:
        selected_items = list(
            permute_ppi_within_observable_strata(selected_items, selected_outputs)
        )
    if constant_ppi:
        selected_items = [
            ObservableScoreItem(
                item.item_id,
                (
                    ("ppi_k8", 0.0),
                    ("ppi_k4", 0.0),
                    ("confidence_margin", item.scores()["confidence_margin"]),
                ),
            )
            for item in selected_items
        ]
    population = NamedFinitePopulation(
        scenario_id=scenario_id,
        items=tuple(selected_items),
        evaluator_outcomes=tuple(
            (case.item_id, case.joint_dangerous_error) for case in selected_cases
        ),
    )
    collider = {
        "association_before_agreement": _pearson_association(all_error_pairs),
        "association_after_agreement": _pearson_association(selected_error_pairs),
        "candidate_count_before_selection": candidate_index,
        "agreement_population_count": population_size,
        "generated_candidate_count": candidate_index,
        "accepted_candidate_count": population_size,
        "acceptance_rate": population_size / candidate_index,
        "before_association_population_size": len(all_error_pairs),
        "after_association_population_size": len(selected_error_pairs),
        "diagnostic_only": True,
    }
    manifest = {
        "scenario_id": scenario_id,
        "pi_H": spec.pi_h,
        "stable_false_belief_rate": spec.stable_false_belief_rate,
        "unrelated_fragility": spec.unrelated_fragility,
        "permuted_ppi": spec.permute_ppi,
        "permutation_strata": ["original_agreed_output", "confidence_margin_quartile"],
        "confidence_constants": {
            "tau_primary": config.tau_primary,
            "tau_verifier": config.tau_verifier,
            "normalization_primary": config.normalization_primary,
            "normalization_verifier": config.normalization_verifier,
            "classification": manifest_classification,
        },
        "agreement_selection": {
            "tau_stage1": config.tau_primary,
            "maximum_generated_candidates": config.maximum_generated_candidates,
            "accepted_candidate_count": population_size,
            "generated_candidate_count": candidate_index,
            "acceptance_rate": population_size / candidate_index,
            "engineering_only": True,
            "selection_neutral_null": scenario_id == "no_shared_fragile_mechanism",
        },
        "constants": stage1_engineering_constants(
            robust_coefficient,
            "Stage 2 development-only calibrated value"
            if manifest_classification.startswith("Stage 2")
            else "engineering-only; not Stage 2 or confirmatory values",
        ),
        "constant_ppi": constant_ppi,
    }
    return GeneratedStage1Population(
        population=population,
        causal_cases=tuple(selected_cases),
        observable_outputs=tuple(selected_outputs),
        collider_diagnostic=collider,
        scenario_manifest=manifest,
        component_evaluation_count=candidate_index * 18,
        identity_sentinel_passed=identity_passed,
        structural_invariance_passed=invariance_passed,
    )


def validate_stage1_acceptance(
    config: Stage1Config,
    seeds: Sequence[int] = STAGE1_ACCEPTANCE_CHECK_SEEDS,
) -> Tuple[Stage1AcceptanceCheck, ...]:
    """Run reserved acceptance-only checks without returning truth or score data."""

    config.validate()
    if tuple(seeds) != STAGE1_ACCEPTANCE_CHECK_SEEDS:
        raise ValueError("Stage 1 acceptance validation requires the reserved seed set")
    checks = []
    for scenario_id in config.scenario_ids:
        for seed in seeds:
            generated = generate_stage1_population(
                scenario_id, config.population_size, seed, config
            )
            diagnostic = generated.collider_diagnostic
            accepted = int(diagnostic["accepted_candidate_count"])
            candidate_count = int(diagnostic["generated_candidate_count"])
            checks.append(
                Stage1AcceptanceCheck(
                    scenario_id=scenario_id,
                    seed=seed,
                    accepted_candidate_count=accepted,
                    generated_candidate_count=candidate_count,
                    acceptance_rate=accepted / candidate_count,
                    selection_neutral_null=scenario_id == "no_shared_fragile_mechanism",
                )
            )
    return tuple(checks)


@dataclass(frozen=True)
class Stage2GeneratorParameters:
    """Frozen existing-mechanism parameters for one Stage 2 risk/pi_H cell."""

    p_jde_target: float
    pi_h: float
    robust_coefficient: float
    stable_false_belief_rate: float
    control_id: str = "primary"

    def validate(self) -> None:
        if self.p_jde_target not in (1e-1, 3e-2, 1e-2, 3e-3):
            raise ValueError("unknown Stage 2 p_JDE target")
        if self.pi_h not in (0.0, 0.5, 0.75):
            raise ValueError("unknown Stage 2 pi_H value")
        if not math.isfinite(self.robust_coefficient) or self.robust_coefficient <= 0:
            raise ValueError("Stage 2 robust coefficient must be finite and positive")
        if not 0.0 <= self.stable_false_belief_rate <= 1.0:
            raise ValueError("Stage 2 stable-false-belief rate is invalid")
        if self.control_id not in {
            "primary",
            "pi_h_zero",
            "fragility_unrelated_to_error",
            "stable_shared_false_belief",
            "conditional_permuted_ppi",
            "global_permuted_ppi",
            "constant_ppi",
            "favourable_high_fragility",
        }:
            raise ValueError("unknown Stage 2 control identity")


@dataclass(frozen=True)
class Stage2MarginCalibration:
    normalization_primary: float
    normalization_verifier: float
    percentile: float
    observation_count: int


@dataclass(frozen=True)
class Stage2RiskCalibration:
    parameters: Stage2GeneratorParameters
    realized_calibration_prevalence: float
    calibration_seeds: Tuple[int, ...]
    inspected_quantity: str = "aggregate_true_jde_prevalence_only"


def _empirical_percentile(values: Sequence[float], probability: float) -> float:
    if not values or not 0.0 <= probability <= 1.0:
        raise ValueError("empirical percentile inputs are invalid")
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("empirical percentile values must be finite")
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return math.fsum(
        ((1.0 - weight) * ordered[lower], weight * ordered[upper])
    )


def calibrate_stage2_margin_normalization(
    observable_outputs: Sequence[ObservableCaseOutputs],
    tau_primary: float = 0.25,
    tau_verifier: float = 0.25,
) -> Stage2MarginCalibration:
    """Use only observable original magnitudes from reserved development data."""

    if not observable_outputs:
        raise ValueError("Stage 2 margin calibration requires observable outputs")
    primary = [row.original_primary_magnitude for row in observable_outputs]
    verifier = [row.original_verifier_magnitude for row in observable_outputs]
    normalization_primary = _empirical_percentile(primary, 0.99)
    normalization_verifier = _empirical_percentile(verifier, 0.99)
    if normalization_primary <= tau_primary or normalization_verifier <= tau_verifier:
        raise ValueError("Stage 2 calibrated normalization must exceed tau")
    return Stage2MarginCalibration(
        normalization_primary,
        normalization_verifier,
        0.99,
        len(observable_outputs),
    )


def _stage2_scenario_spec(parameters: Stage2GeneratorParameters) -> Stage1ScenarioSpec:
    parameters.validate()
    control_id = parameters.control_id
    pi_h = parameters.pi_h
    stable_rate = parameters.stable_false_belief_rate
    unrelated = control_id == "fragility_unrelated_to_error"
    permuted = control_id == "conditional_permuted_ppi"
    if control_id in {"pi_h_zero", "stable_shared_false_belief"}:
        pi_h = 0.0
    if control_id == "favourable_high_fragility":
        pi_h = 0.75
    return Stage1ScenarioSpec(
        scenario_id=f"stage2-{control_id}",
        pi_h=pi_h,
        stable_false_belief_rate=stable_rate,
        unrelated_fragility=unrelated,
        permute_ppi=permuted,
    )


def generate_stage2_population(
    parameters: Stage2GeneratorParameters,
    seed: int,
    normalization: Stage2MarginCalibration,
    config: Stage2Config | None = None,
    bank: FrozenTransformationBank | None = None,
) -> GeneratedStage1Population:
    """Reuse the accepted causal mechanism with frozen Stage 2 cell parameters."""

    config = config or Stage2Config()
    config.validate()
    parameters.validate()
    scenario_id = (
        f"stage2-{parameters.control_id}-p{parameters.p_jde_target:.12g}-"
        f"h{parameters.pi_h:.12g}"
    )
    generator_config = Stage1Config(
        population_size=config.population_size,
        budget=0,
        replicates=1,
        ks=(8,),
        epsilon_samp=0.2,
        lambda_grid=config.lambda_grid,
        alpha_cs=config.alpha_cs,
        ridge=config.ridge,
        tau_primary=config.tau_primary,
        tau_verifier=config.tau_verifier,
        normalization_primary=normalization.normalization_primary,
        normalization_verifier=normalization.normalization_verifier,
        inversion_tolerance=config.inversion_tolerance,
        monotonicity_tolerance=config.monotonicity_tolerance,
        maximum_generated_candidates=config.maximum_generated_candidates,
    )
    generated = generate_stage1_population(
        scenario_id,
        config.population_size,
        seed,
        generator_config,
        bank,
        scenario_spec=_stage2_scenario_spec(parameters),
        robust_coefficient=parameters.robust_coefficient,
        constant_ppi=parameters.control_id == "constant_ppi",
        manifest_classification="Stage 2 development-only; never confirmatory",
    )
    if parameters.control_id == "global_permuted_ppi":
        permuted_items = permute_ppi_globally(generated.population.items, seed)
        manifest = dict(generated.scenario_manifest)
        manifest.update(
            {
                "global_permuted_ppi": True,
                "global_permutation_uses_hidden_outcomes": False,
            }
        )
        generated = replace(
            generated,
            population=NamedFinitePopulation(
                generated.population.scenario_id,
                permuted_items,
                generated.population.evaluator_outcomes,
            ),
            scenario_manifest=manifest,
        )
    return generated


def stage2_prevalence_probe(
    parameters: Stage2GeneratorParameters,
    seed: int,
    normalization: Stage2MarginCalibration,
    config: Stage2Config,
) -> float:
    """Risk calibrator boundary: expose only aggregate evaluator prevalence."""

    return generate_stage2_population(
        parameters, seed, normalization, config
    ).population.true_prevalence


def calibrate_stage2_risk_parameters(
    p_jde_target: float,
    pi_h: float,
    calibration_seeds: Sequence[int],
    normalization: Stage2MarginCalibration,
    config: Stage2Config | None = None,
) -> Stage2RiskCalibration:
    """Tune only existing difficulty parameters using aggregate prevalence.

    For the pi_H=0 null, the existing stable-shared-belief mixture is varied.
    For pi_H>0, its rate is fixed at zero and the existing common robust
    coefficient is varied.  No score, arm, bound, or contrast enters selection.
    """

    config = config or Stage2Config()
    config.validate()
    seeds = tuple(int(seed) for seed in calibration_seeds)
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("risk calibration seeds must be non-empty and unique")

    def evaluate(robust: float, stable_rate: float) -> float:
        parameters = Stage2GeneratorParameters(
            p_jde_target, pi_h, robust, stable_rate, "primary"
        )
        return math.fsum(
            stage2_prevalence_probe(parameters, seed, normalization, config)
            for seed in seeds
        ) / len(seeds)

    best = None
    if pi_h == 0.0:
        low, high = 0.0, min(0.5, max(0.20, 4.0 * p_jde_target))
        robust = ROBUST_COEFFICIENT
        for _ in range(18):
            midpoint = (low + high) / 2.0
            realized = evaluate(robust, midpoint)
            candidate = (abs(realized - p_jde_target), midpoint, realized)
            best = candidate if best is None or candidate < best else best
            if realized < p_jde_target:
                low = midpoint
            else:
                high = midpoint
        _, stable_rate, realized = best
    else:
        low, high = 2.40, 3.20
        stable_rate = 0.0
        for _ in range(18):
            midpoint = (low + high) / 2.0
            realized = evaluate(midpoint, stable_rate)
            candidate = (abs(realized - p_jde_target), midpoint, realized)
            best = candidate if best is None or candidate < best else best
            if realized > p_jde_target:
                low = midpoint
            else:
                high = midpoint
        _, robust, realized = best
    parameters = Stage2GeneratorParameters(
        p_jde_target, pi_h, robust, stable_rate, "primary"
    )
    return Stage2RiskCalibration(parameters, realized, seeds)


def stage2_control_parameters(
    base: Stage2GeneratorParameters,
    control_id: str,
) -> Stage2GeneratorParameters:
    """Apply one accepted control identity without adding a mechanism."""

    base.validate()
    if control_id == "pi_h_zero":
        return Stage2GeneratorParameters(
            base.p_jde_target,
            0.0,
            base.robust_coefficient,
            base.stable_false_belief_rate,
            control_id,
        )
    if control_id == "stable_shared_false_belief":
        return Stage2GeneratorParameters(
            base.p_jde_target,
            0.0,
            base.robust_coefficient,
            max(base.stable_false_belief_rate, base.p_jde_target),
            control_id,
        )
    if control_id == "favourable_high_fragility":
        return Stage2GeneratorParameters(
            base.p_jde_target,
            0.75,
            base.robust_coefficient,
            base.stable_false_belief_rate,
            control_id,
        )
    if control_id in {
        "fragility_unrelated_to_error",
        "conditional_permuted_ppi",
        "global_permuted_ppi",
        "constant_ppi",
    }:
        return Stage2GeneratorParameters(
            base.p_jde_target,
            base.pi_h,
            base.robust_coefficient,
            base.stable_false_belief_rate,
            control_id,
        )
    raise ValueError("unknown mandatory Stage 2 control")
