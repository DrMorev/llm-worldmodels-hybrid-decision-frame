"""CLI and orchestration for the development-only feasibility smoke run."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import statistics
import sys
import tempfile
import time
from typing import Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

from .betting import (
    ControlledNumericalFailure,
    EmptyConfidenceSet,
    MonotonicityFailure,
    SupportAdmissibilityFailure,
    SupportTerm,
    WealthStep,
    estimate_beta,
    evaluate_running_bound,
    evaluate_running_mixture_bound,
)
from .core import (
    ArmSpec,
    FinitePopulation,
    NamedFinitePopulation,
    ObservableScoreItem,
    SmokeConfig,
    Stage1ArmSpec,
    Stage1Config,
    Stage2Cell,
    Stage2Config,
    development_arms,
    digest_rows,
    stable_seed,
    stage2_development_primary_bootstrap_seed,
    stage2_generator_strata,
    stage1_arms,
    stage2_cells,
    stage2_trajectory_arms,
)
from . import DEVELOPMENT_ONLY_NOTICE, DEV_CODE_VERSION, STAGE1_CODE_VERSION
from .proxies import (
    ObservableCaseOutputs,
    compute_confidence_margin,
    frozen_transformation_bank,
    observable_outputs_digest,
    ppi_from_observable_outputs,
    score_channel_digest,
)
from .sampling import (
    policy_probabilities,
    replay_named_pre_reveal_draw,
    replay_pre_reveal_draw,
    select_item_from_variate,
    serialize_named_pre_reveal_draw,
    serialize_pre_reveal_draw,
)
from .scenarios import (
    DETERMINISTIC_FIXTURES,
    ORDINARY_FIXTURES,
    generate_fixture,
    generate_stage1_population,
    generate_stage2_population,
    calibrate_stage2_margin_normalization,
    calibrate_stage2_risk_parameters,
    permute_ppi_within_observable_strata,
    stage2_control_parameters,
    Stage2GeneratorParameters,
    Stage2MarginCalibration,
)


class InvalidDevelopmentRun(RuntimeError):
    pass


class Stage2ControlBoundFailure(InvalidDevelopmentRun):
    """A control G value cannot be formed without discarding or imputing data."""

    def __init__(self, failure_record: Mapping[str, object]):
        self.failure_record = dict(failure_record)
        blockers = list(self.failure_record.get("blocking_rows", ()))
        representative = blockers[0] if blockers else self.failure_record
        super().__init__(
            "control G has an undefined "
            f"{representative['bound_role']}: "
            f"control_id={representative['control_id']}, "
            f"replicate_id={representative['replicate_id']}, "
            f"arm={representative['conceptual_arm']}, "
            f"epsilon_samp={representative['epsilon_samp']}, "
            f"B={representative['B']}; blockers={len(blockers) or 1}"
        )


class Stage2PreflightFailureReceipt(InvalidDevelopmentRun):
    """Controlled nonzero preflight outcome with an external evidence receipt."""

    def __init__(self, failure_record: Mapping[str, object], artifacts: Mapping[str, object]):
        self.failure_record = dict(failure_record)
        self.artifacts = dict(artifacts)
        super().__init__(
            "Stage 2 preflight stopped before gamma_NC calibration; "
            f"failure receipt: {self.artifacts['report_path']}; "
            f"control_id={self.failure_record['control_id']}, "
            f"replicate_id={self.failure_record['replicate_id']}, "
            f"arm={self.failure_record['conceptual_arm']}"
        )


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_git_directory(repository_root: Path) -> Path:
    """Resolve a normal ``.git`` directory or a linked-worktree gitdir file."""

    marker = repository_root / ".git"
    if marker.is_dir():
        return marker
    if not marker.is_file():
        raise FileNotFoundError(f"Git metadata marker is absent: {marker}")
    content = marker.read_text(encoding="utf-8").strip()
    if not content.startswith("gitdir: "):
        raise ValueError("malformed .git file: expected 'gitdir: <path>'")
    target = Path(content[len("gitdir: ") :])
    git_directory = target if target.is_absolute() else (marker.parent / target).resolve()
    if not git_directory.is_dir():
        raise FileNotFoundError(f"linked-worktree gitdir is unavailable: {git_directory}")
    return git_directory


def _read_git_reference(git_directory: Path, reference: str) -> Optional[str]:
    loose_reference = git_directory / Path(reference)
    if loose_reference.is_file():
        value = loose_reference.read_text(encoding="utf-8").strip()
        return value or None
    packed_references = git_directory / "packed-refs"
    if packed_references.is_file():
        for line in packed_references.read_text(encoding="utf-8").splitlines():
            if line and not line.startswith(("#", "^")):
                try:
                    sha, ref_name = line.split(" ", 1)
                except ValueError:
                    continue
                if ref_name == reference:
                    return sha
    return None


def inspect_git_provenance(repository_root: Path) -> Dict[str, object]:
    """Read local Git metadata without a network operation or mutable Git call."""

    result: Dict[str, object] = {
        "head": None,
        "branch": None,
        "detached": None,
        "warning": None,
    }
    try:
        git_directory = _resolve_git_directory(repository_root)
        head_text = (git_directory / "HEAD").read_text(encoding="utf-8").strip()
        if head_text.startswith("ref: "):
            reference = head_text[5:]
            head = _read_git_reference(git_directory, reference)
            if not head:
                raise ValueError(f"HEAD reference cannot be resolved: {reference}")
            result["head"] = head
            result["branch"] = (
                reference[len("refs/heads/") :]
                if reference.startswith("refs/heads/")
                else reference
            )
            result["detached"] = False
        elif len(head_text) == 40 and all(character in "0123456789abcdefABCDEF" for character in head_text):
            result["head"] = head_text
            result["detached"] = True
        else:
            raise ValueError("malformed HEAD metadata")
    except (OSError, ValueError) as error:
        result["warning"] = f"Git provenance unavailable: {error}"
    return result


def default_output_directory() -> Path:
    return Path(tempfile.mkdtemp(prefix="llm-worldmodels-phase1b-dev-"))


def _ensure_external_output(path: Path, repository_root: Path) -> None:
    resolved = path.resolve()
    repository = repository_root.resolve()
    if resolved == repository or repository in resolved.parents:
        raise ValueError("development output directory must be outside the repository")


def _serialize_population(population: FinitePopulation, replicate: int, seed: int) -> dict:
    rows = [
        (item.item_id, item.score.hex(), item.outcome, item.scenario_label)
        for item in population.items
    ]
    return {
        "fixture": population.fixture,
        "replicate": replicate,
        "seed": seed,
        "population_digest": digest_rows(rows),
        "items": [
            {
                "item_id": item.item_id,
                "score": item.score,
                "hidden_outcome": item.outcome,
                "scenario_label": item.scenario_label,
            }
            for item in population.items
        ],
    }


def simulate_audit(
    population: FinitePopulation,
    arm: ArmSpec,
    budget: int,
    ridge: float,
    rng_seed: int,
) -> dict:
    if budget > population.size:
        raise InvalidDevelopmentRun("budget exceeds population size")
    remaining = list(population.item_ids())
    scores = population.observable_scores()
    oracle = population.hidden_outcomes()
    rng = random.Random(rng_seed)
    selected_ids = set()
    selection_order: List[str] = []
    beta_history: List[Tuple[float, float]] = []
    wealth_steps: List[WealthStep] = []
    trace = []
    warnings: List[str] = []
    observed_errors = 0
    observed_complements = 0
    min_q = math.inf
    max_importance_weight = 0.0
    q_replay_passed = True

    for step_number in range(1, budget + 1):
        if not remaining:
            raise InvalidDevelopmentRun("remaining population became empty before budget")
        probabilities, normalization = policy_probabilities(
            arm.policy, remaining, scores, arm.gamma
        )
        expected_score = math.fsum(
            probabilities[item_id] * scores[item_id] for item_id in remaining
        )
        if not math.isfinite(expected_score):
            raise InvalidDevelopmentRun("non-finite control-variate input")
        if arm.use_control_variate:
            beta_estimate = estimate_beta(beta_history, ridge)
            beta_value = beta_estimate.value
            if beta_estimate.warning:
                warnings.append(f"step {step_number}: {beta_estimate.warning}")
        else:
            beta_estimate = estimate_beta((), ridge)
            beta_value = 0.0

        support_minimum = None
        support_term_count = 0
        for item_id in remaining:
            probability = probabilities[item_id]
            support_control_value = (
                scores[item_id] - expected_score if arm.use_control_variate else 0.0
            )
            if not math.isfinite(support_control_value):
                raise InvalidDevelopmentRun("non-finite support control-variate input")
            for support_outcome in (0, 1):
                support_complement = 1 - support_outcome
                support_z = support_complement / (population.size * probability)
                support_constant = (
                    support_z
                    + beta_value * support_control_value
                    + observed_complements / population.size
                )
                if not math.isfinite(support_constant):
                    raise InvalidDevelopmentRun("non-finite support payoff")
                support_term = SupportTerm(
                    item_id=item_id,
                    outcome=support_outcome,
                    score=scores[item_id],
                    probability=probability,
                    control_value=support_control_value,
                    beta=beta_value,
                    constant_term=support_constant,
                )
                support_term_count += 1
                if (
                    support_minimum is None
                    or support_term.constant_term < support_minimum.constant_term
                ):
                    support_minimum = support_term

        draw_uniform = rng.random()
        selected = select_item_from_variate(probabilities, draw_uniform)
        if selected in selected_ids:
            raise InvalidDevelopmentRun("duplicate item selection")
        selected_ids.add(selected)
        selection_order.append(selected)
        pre_reveal = serialize_pre_reveal_draw(
            step=step_number,
            remaining_item_ids=remaining,
            scores=scores,
            sampling_policy=arm.policy,
            gamma=arm.gamma,
            probabilities=probabilities,
            normalization=normalization,
            draw_uniform=draw_uniform,
            selected_item_id=selected,
        )
        replay = replay_pre_reveal_draw(pre_reveal)
        q_replay_passed = q_replay_passed and replay.passed
        if not replay.passed:
            raise InvalidDevelopmentRun(f"serialized q replay failed: {replay.reason}")
        selected_probability = probabilities[selected]
        control_value = (
            scores[selected] - expected_score if arm.use_control_variate else 0.0
        )

        outcome = oracle[selected]
        complement = 1 - outcome
        importance_weight = 1.0 / (population.size * selected_probability)
        z_value = complement * importance_weight
        if not math.isfinite(importance_weight) or not math.isfinite(z_value):
            raise InvalidDevelopmentRun("non-finite importance-weight calculation")
        constant_term = (
            z_value + beta_value * control_value + observed_complements / population.size
        )
        if not math.isfinite(constant_term):
            raise InvalidDevelopmentRun("non-finite wealth constant term")
        observed_errors += outcome
        observed_complements += complement
        logical_lower = observed_complements / population.size
        wealth_steps.append(
            WealthStep(
                constant_term,
                logical_lower,
                (),
                support_minimum,
                support_term_count,
            )
        )
        if arm.use_control_variate:
            beta_history.append((z_value, control_value))
        min_q = min(min_q, min(probabilities.values()))
        max_importance_weight = max(max_importance_weight, importance_weight)
        trace.append(
            {
                "step": step_number,
                "pre_reveal": pre_reveal,
                "revealed_outcome": outcome,
                "complement": complement,
                "importance_weight": importance_weight,
                "z_complement": z_value,
                "expected_score_under_q": expected_score,
                "u": control_value,
                "beta": beta_value,
                "beta_covariance": beta_estimate.covariance,
                "beta_variance": beta_estimate.variance,
                "cumulative_complements_before": observed_complements - complement,
                "constant_term": constant_term,
                "logical_complement_lower": logical_lower,
            }
        )
        remaining.remove(selected)

    return {
        "rng_seed": rng_seed,
        "selected_item_ids_in_selection_order": selection_order,
        "selection_order": selection_order,
        "trace": trace,
        "wealth_steps": wealth_steps,
        "observations": budget,
        "errors_observed": observed_errors,
        "min_q": min_q,
        "max_importance_weight": max_importance_weight,
        "q_replay_passed": q_replay_passed,
        "warnings": warnings,
    }


def _record_for_lambda(
    fixture: str,
    replicate: int,
    population: FinitePopulation,
    arm: ArmSpec,
    audit_id: str,
    audit: Mapping[str, object],
    fixed_lambda: float,
    config: SmokeConfig,
) -> dict:
    try:
        evaluation = evaluate_running_bound(
            audit["wealth_steps"],
            fixed_lambda,
            config.audit_risk,
            config.inversion_tolerance,
            config.monotonicity_tolerance,
        )
        upper_bound = evaluation.upper_error_bound
        coverage = upper_bound + config.inversion_tolerance >= population.true_prevalence
        status = "valid"
        warning_rows = list(audit["warnings"])
        monotonicity_status = evaluation.monotonicity_status
        min_multiplier = evaluation.min_multiplier
        multiplier_failure_present = False
        final_log_wealth = {
            "candidate_g_0": evaluation.final_log_wealth_g0,
            "candidate_g_1": evaluation.final_log_wealth_g1,
            "reported_lower_g_bound": evaluation.final_log_wealth_at_bound,
        }
    except EmptyConfidenceSet as error:
        upper_bound = None
        coverage = False
        status = "empty_confidence_set"
        warning_rows = list(audit["warnings"]) + [str(error)]
        monotonicity_status = "not_evaluated"
        min_multiplier = None
        multiplier_failure_present = False
        final_log_wealth = {}
    except SupportAdmissibilityFailure as error:
        upper_bound = None
        coverage = False
        status = "invalid_support_admissibility"
        warning_rows = list(audit["warnings"]) + [str(error)]
        monotonicity_status = "not_evaluated"
        min_multiplier = None
        multiplier_failure_present = True
        final_log_wealth = {}
    except MonotonicityFailure as error:
        upper_bound = None
        coverage = False
        status = "invalid_monotonicity"
        warning_rows = list(audit["warnings"]) + [str(error)]
        monotonicity_status = "failed"
        min_multiplier = None
        multiplier_failure_present = False
        final_log_wealth = {}
    except ControlledNumericalFailure as error:
        upper_bound = None
        coverage = False
        status = "invalid"
        warning_rows = list(audit["warnings"]) + [str(error)]
        monotonicity_status = "not_evaluated"
        min_multiplier = None
        multiplier_failure_present = False
        final_log_wealth = {}
    return {
        "code_version": DEV_CODE_VERSION,
        "fixture": fixture,
        "replicate": replicate,
        "arm": arm.name,
        "conceptual_arm": arm.conceptual_label,
        "lambda": fixed_lambda,
        "gamma": arm.gamma,
        "audit_id": audit_id,
        "true_prevalence": population.true_prevalence,
        "oracle_observations": audit["observations"],
        "errors_observed": audit["errors_observed"],
        "final_upper_confidence_bound": upper_bound,
        "coverage_indicator": coverage,
        "minimum_q": audit["min_q"],
        "maximum_importance_weight": audit["max_importance_weight"],
        "minimum_wealth_multiplier": min_multiplier,
        "multiplier_failure_present": multiplier_failure_present,
        "final_log_wealth": final_log_wealth,
        "q_replay_passed": audit["q_replay_passed"],
        "monotonicity_status": monotonicity_status,
        "warnings": warning_rows,
        "validity_status": status,
    }


def _group_records(records: Sequence[dict]) -> List[dict]:
    grouped: Dict[Tuple[object, ...], List[dict]] = {}
    for record in records:
        key = (
            record["fixture"],
            record["arm"],
            record["conceptual_arm"],
            record["lambda"],
            record["gamma"],
        )
        grouped.setdefault(key, []).append(record)
    rows = []
    for key in sorted(grouped, key=lambda value: tuple("" if part is None else str(part) for part in value)):
        group = grouped[key]
        bounds = [
            row["final_upper_confidence_bound"]
            for row in group
            if row["validity_status"] == "valid"
            and row["final_upper_confidence_bound"] is not None
        ]
        empty_count = sum(
            row["validity_status"] == "empty_confidence_set" for row in group
        )
        rows.append(
            {
                "fixture": key[0],
                "arm": key[1],
                "conceptual_arm": key[2],
                "lambda": key[3],
                "gamma": key[4],
                "runs": len(group),
                "empirical_marginal_coverage": math.fsum(bool(row["coverage_indicator"]) for row in group) / len(group),
                "mean_upper_bound": statistics.fmean(bounds) if bounds else "",
                "median_upper_bound": statistics.median(bounds) if bounds else "",
                "mean_oracle_events_found": statistics.fmean(row["errors_observed"] for row in group),
                "zero_event_fraction": math.fsum(row["errors_observed"] == 0 for row in group) / len(group),
                "minimum_q": min(row["minimum_q"] for row in group),
                "maximum_importance_weight": max(row["maximum_importance_weight"] for row in group),
                "records_with_multiplier_failure": sum(
                    bool(row["multiplier_failure_present"]) for row in group
                ),
                "records_with_multiplier_failure_proportion": math.fsum(
                    bool(row["multiplier_failure_present"]) for row in group
                ) / len(group),
                "q_replay_failures": sum(not row["q_replay_passed"] for row in group),
                "empty_confidence_set_count": empty_count,
                "empty_confidence_set_proportion": empty_count / len(group),
                "support_admissibility_failures": sum(
                    row["validity_status"] == "invalid_support_admissibility"
                    for row in group
                ),
                "inversion_or_numerical_failures": sum(
                    row["validity_status"] == "invalid" for row in group
                ),
                "monotonicity_failures": sum(
                    row["monotonicity_status"] == "failed" for row in group
                ),
            }
        )
    return rows


def _write_csv(path: Path, rows: Sequence[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, rows: Sequence[dict], runtime_seconds: float) -> None:
    lines = [
        DEVELOPMENT_ONLY_NOTICE,
        "",
        f"Runtime seconds: {runtime_seconds:.6f}",
        "Empirical coverage below is marginal per development group, not confirmatory evidence.",
        "Exit code 0 means this development run completed; it does not pass a scientific or preregistered coverage gate.",
        "Multiplier-failure counts are result-record counts; their denominator is runs in the group.",
        "",
    ]
    for row in rows:
        lines.append(
            " | ".join(
                (
                    f"fixture={row['fixture']}",
                    f"arm={row['arm']}",
                    f"conceptual_arm={row['conceptual_arm']}",
                    f"lambda={row['lambda']}",
                    f"gamma={row['gamma']}",
                    f"coverage={row['empirical_marginal_coverage']:.6f}",
                    f"mean_upper={row['mean_upper_bound']}",
                    f"median_upper={row['median_upper_bound']}",
                    f"mean_events={row['mean_oracle_events_found']:.6f}",
                    f"zero_event_fraction={row['zero_event_fraction']:.6f}",
                    f"min_q={row['minimum_q']:.12g}",
                    f"max_importance={row['maximum_importance_weight']:.12g}",
                    f"records_with_multiplier_failure={row['records_with_multiplier_failure']}",
                    f"records_with_multiplier_failure_proportion={row['records_with_multiplier_failure_proportion']:.6f}",
                    f"q_replay_failures={row['q_replay_failures']}",
                    f"empty_confidence_sets={row['empty_confidence_set_count']}",
                    f"empty_confidence_set_proportion={row['empty_confidence_set_proportion']:.6f}",
                    f"support_admissibility_failures={row['support_admissibility_failures']}",
                    f"inversion_or_numerical_failures={row['inversion_or_numerical_failures']}",
                    f"monotonicity_failures={row['monotonicity_failures']}",
                )
            )
        )
    lines.extend(("", DEVELOPMENT_ONLY_NOTICE))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _authoritative_population_for_audit(
    document: Mapping[str, object], audit: Mapping[str, object]
) -> Tuple[List[str], Dict[str, float]]:
    """Validate and expose the one serialized population referenced by an audit.

    Hidden outcomes participate only in the audit-level digest reconstruction,
    because that is the representation used when the population was written.
    They are never used to validate a draw's pre-reveal state.
    """

    populations = document.get("populations")
    if not isinstance(populations, list):
        raise ValueError("artifact has no populations list")
    required = ("fixture", "replicate", "population_digest")
    if any(field not in audit for field in required):
        raise ValueError("audit lacks population identity fields")
    matches = [
        population
        for population in populations
        if isinstance(population, Mapping)
        and population.get("fixture") == audit["fixture"]
        and population.get("replicate") == audit["replicate"]
        and population.get("population_digest") == audit["population_digest"]
    ]
    if len(matches) != 1:
        raise ValueError("audit does not identify exactly one serialized population")
    population = matches[0]
    items = population.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("serialized population has no non-empty items list")
    try:
        rows = [
            (
                item["item_id"],
                float(item["score"]).hex(),
                item["hidden_outcome"],
                item.get("scenario_label"),
            )
            for item in items
            if isinstance(item, Mapping)
        ]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"malformed serialized population item: {error}") from error
    if len(rows) != len(items):
        raise ValueError("serialized population contains a non-object item")
    recomputed_digest = digest_rows(rows)
    if recomputed_digest != population["population_digest"]:
        raise ValueError("serialized population digest mismatch")
    ordered_ids = [str(row[0]) for row in rows]
    if len(set(ordered_ids)) != len(ordered_ids):
        raise ValueError("serialized population has duplicate item IDs")
    scores = {
        str(item["item_id"]): float(item["score"])
        for item in items
        if isinstance(item, Mapping)
    }
    if any(not math.isfinite(score) or not 0.0 <= score <= 1.0 for score in scores.values()):
        raise ValueError("serialized population has invalid observable score")
    return ordered_ids, scores


def replay_serialized_audits(document: Mapping[str, object]) -> dict:
    """Replay draws against their authoritative serialized audit populations."""

    audits = document.get("audits")
    if not isinstance(audits, list):
        raise ValueError("artifact has no audits list")
    failures = []
    checked_draws = 0
    for audit in audits:
        if not isinstance(audit, Mapping):
            failures.append({"audit_id": None, "step": None, "reason": "malformed audit"})
            continue
        audit_id = audit.get("audit_id")
        try:
            remaining, authoritative_scores = _authoritative_population_for_audit(
                document, audit
            )
        except ValueError as error:
            failures.append({"audit_id": audit_id, "step": None, "reason": str(error)})
            continue
        trace = audit.get("trace")
        if not isinstance(trace, list):
            failures.append({"audit_id": audit_id, "step": None, "reason": "malformed trace"})
            continue
        selection_order = audit.get("selection_order")
        if not isinstance(selection_order, list) or len(selection_order) != len(trace):
            failures.append({"audit_id": audit_id, "step": None, "reason": "selection-order length mismatch"})
            continue
        for position, row in enumerate(trace, start=1):
            if not isinstance(row, Mapping):
                failures.append({"audit_id": audit_id, "step": None, "reason": "malformed trace row"})
                continue
            pre_reveal = row.get("pre_reveal")
            if not isinstance(pre_reveal, Mapping):
                failures.append({"audit_id": audit_id, "step": row.get("step"), "reason": "missing pre-reveal record"})
                continue
            checked_draws += 1
            if row.get("step") != position or pre_reveal.get("step") != position:
                failures.append({"audit_id": audit_id, "step": row.get("step"), "reason": "non-chronological step record"})
                continue
            recorded_ids = pre_reveal.get("remaining_item_ids")
            recorded_scores = pre_reveal.get("remaining_scores")
            if not isinstance(recorded_ids, list) or recorded_ids != remaining:
                failures.append({"audit_id": audit_id, "step": position, "reason": "remaining population order mismatch"})
                continue
            if not isinstance(recorded_scores, list) or len(recorded_scores) != len(remaining):
                failures.append({"audit_id": audit_id, "step": position, "reason": "remaining score vector length mismatch"})
                continue
            score_mismatch = next(
                (
                    item_id
                    for item_id, score in zip(remaining, recorded_scores)
                    if float(score).hex() != authoritative_scores[item_id].hex()
                ),
                None,
            )
            if score_mismatch is not None:
                failures.append({"audit_id": audit_id, "step": position, "reason": f"population score mismatch for {score_mismatch}"})
                continue
            expected_selected = selection_order[position - 1]
            if pre_reveal.get("selected_item_id") != expected_selected:
                failures.append({"audit_id": audit_id, "step": position, "reason": "selection history mismatch"})
                continue
            replay = replay_pre_reveal_draw(pre_reveal)
            if not replay.passed:
                failures.append(
                    {
                        "audit_id": audit_id,
                        "step": row.get("step"),
                        "reason": replay.reason,
                    }
                )
                continue
            if replay.reconstructed_item_id != expected_selected:
                failures.append({"audit_id": audit_id, "step": position, "reason": "replayed selection history mismatch"})
                continue
            if expected_selected not in remaining:
                failures.append({"audit_id": audit_id, "step": position, "reason": "duplicate or unknown selected item"})
                continue
            remaining.remove(expected_selected)
    return {
        "checked_audits": len(audits),
        "checked_draws": checked_draws,
        "failure_count": len(failures),
        "failures": failures,
    }


def replay_artifact(path: Path) -> dict:
    """Load a JSON artifact and replay it without constructing live simulations."""

    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, Mapping):
        raise ValueError("artifact root must be an object")
    if document.get("schema_version") in {
        "ppi-stage1-replay-v1",
        "ppi-stage1-replay-v2",
        "ppi-stage2-replay-v1",
    }:
        return replay_stage1_artifact_document(document)
    return replay_serialized_audits(document)


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stage1_population_record(generated: object, replicate: int, seed: int) -> dict:
    population = generated.population
    score_channels = population.all_observable_scores()
    output_rows = [asdict(row) for row in generated.observable_outputs]
    items = []
    outcomes = population.hidden_outcomes()
    for item in population.items:
        items.append(
            {
                "item_id": item.item_id,
                "observable_scores": dict(item.score_channels),
                "hidden_outcome": outcomes[item.item_id],
            }
        )
    population_digest = digest_rows(
        (
            row["item_id"],
            tuple(
                (key, float(row["observable_scores"][key]).hex())
                for key in sorted(row["observable_scores"])
            ),
            row["hidden_outcome"],
        )
        for row in items
    )
    return {
        "scenario_id": population.scenario_id,
        "replicate_id": replicate,
        "seed": seed,
        "population_digest": population_digest,
        "observable_score_digests": {
            key: score_channel_digest(score_channels[key]) for key in sorted(score_channels)
        },
        "observable_outputs_digest": observable_outputs_digest(generated.observable_outputs),
        "items": items,
        "observable_outputs": output_rows,
        "scenario_manifest": generated.scenario_manifest,
        "collider_diagnostic": generated.collider_diagnostic,
        "component_evaluation_count": generated.component_evaluation_count,
        "identity_sentinel_passed": generated.identity_sentinel_passed,
        "structural_invariance_passed": generated.structural_invariance_passed,
    }


def simulate_named_audit(
    population: NamedFinitePopulation,
    arm: Stage1ArmSpec,
    budget: int,
    ridge: float,
    rng_seed: int,
    execution_mode: str = "replay_grade",
) -> dict:
    """Audit from named observable scores; hidden outcomes enter only at reveal.

    ``replay_grade`` preserves the accepted Stage 1 forensic record and its
    immediate independent replay.  ``lean`` performs the identical sampling
    and statistical calculation without constructing those large serialized
    vectors.  The scalar trace retained by both modes is sufficient for bulk
    Stage 2 aggregation and direct equivalence tests.
    """

    arm.validate()
    if execution_mode not in {"replay_grade", "lean"}:
        raise ValueError("named audit execution mode must be replay_grade or lean")
    replay_grade = execution_mode == "replay_grade"
    if budget > population.size:
        raise InvalidDevelopmentRun("budget exceeds named population size")
    remaining = list(population.item_ids())
    channels = population.all_observable_scores()
    zero_scores = {item_id: 0.0 for item_id in remaining}
    sampling_scores = (
        zero_scores
        if arm.sampling_score_key is None
        else channels[arm.sampling_score_key]
    )
    cv_scores = (
        zero_scores
        if arm.control_variate_score_key is None
        else channels[arm.control_variate_score_key]
    )
    oracle = population.hidden_outcomes()
    rng = random.Random(rng_seed)
    beta_history: List[Tuple[float, float]] = []
    wealth_steps: List[WealthStep] = []
    trace: List[dict] = []
    selection_order: List[str] = []
    selected_items = set()
    observed_errors = 0
    observed_complements = 0
    min_q = math.inf
    max_importance_weight = 0.0
    warnings: List[str] = []

    for step_number in range(1, budget + 1):
        probabilities, normalization = policy_probabilities(
            arm.sampling_policy,
            remaining,
            sampling_scores,
            arm.epsilon_samp,
        )
        expected_cv = math.fsum(
            probabilities[item_id] * cv_scores[item_id] for item_id in remaining
        )
        if arm.control_variate_score_key is None:
            beta_estimate = estimate_beta((), ridge)
            beta_value = 0.0
        else:
            beta_estimate = estimate_beta(beta_history, ridge)
            beta_value = beta_estimate.value
            if beta_estimate.warning:
                warnings.append(f"step {step_number}: {beta_estimate.warning}")
        support_minimum = None
        support_term_count = 2 * len(remaining)
        if replay_grade:
            for item_id in remaining:
                probability = probabilities[item_id]
                support_u = (
                    cv_scores[item_id] - expected_cv
                    if arm.control_variate_score_key is not None
                    else 0.0
                )
                for support_outcome in (0, 1):
                    support_z = (1 - support_outcome) / (
                        population.size * probability
                    )
                    support_constant = (
                        support_z
                        + beta_value * support_u
                        + observed_complements / population.size
                    )
                    support_term = SupportTerm(
                        item_id=item_id,
                        outcome=support_outcome,
                        score=cv_scores[item_id],
                        probability=probability,
                        control_value=support_u,
                        beta=beta_value,
                        constant_term=support_constant,
                    )
                    if (
                        support_minimum is None
                        or support_constant < support_minimum.constant_term
                    ):
                        support_minimum = support_term
        else:
            # For fixed item/q/CV state, outcome=1 has support_z=0 while
            # outcome=0 adds the strictly positive 1/(N*q).  Therefore the
            # exact support-wide minimum is attained among outcome=1 terms.
            for item_id in remaining:
                probability = probabilities[item_id]
                support_u = (
                    cv_scores[item_id] - expected_cv
                    if arm.control_variate_score_key is not None
                    else 0.0
                )
                support_constant = (
                    beta_value * support_u
                    + observed_complements / population.size
                )
                if (
                    support_minimum is None
                    or support_constant < support_minimum.constant_term
                ):
                    support_minimum = SupportTerm(
                        item_id=item_id,
                        outcome=1,
                        score=cv_scores[item_id],
                        probability=probability,
                        control_value=support_u,
                        beta=beta_value,
                        constant_term=support_constant,
                    )
        draw_uniform = rng.random()
        selected = select_item_from_variate(probabilities, draw_uniform)
        if selected in selected_items:
            raise InvalidDevelopmentRun("duplicate named item selection")
        pre_reveal = None
        if replay_grade:
            pre_reveal = serialize_named_pre_reveal_draw(
                step=step_number,
                remaining_item_ids=remaining,
                sampling_score_key=arm.sampling_score_key,
                sampling_scores=sampling_scores,
                control_variate_score_key=arm.control_variate_score_key,
                control_variate_scores=cv_scores,
                sampling_policy=arm.sampling_policy,
                epsilon_samp=arm.epsilon_samp,
                probabilities=probabilities,
                normalization=normalization,
                draw_uniform=draw_uniform,
                selected_item_id=selected,
            )
            replay = replay_named_pre_reveal_draw(pre_reveal, channels, remaining)
            if not replay.passed:
                raise InvalidDevelopmentRun(
                    f"named serialized replay failed: {replay.reason}"
                )
        probability = probabilities[selected]
        step_min_q = min(probabilities.values())
        u_value = (
            cv_scores[selected] - expected_cv
            if arm.control_variate_score_key is not None
            else 0.0
        )
        outcome = oracle[selected]
        complement = 1 - outcome
        importance_weight = 1.0 / (population.size * probability)
        z_value = complement * importance_weight
        constant_term = z_value + beta_value * u_value + observed_complements / population.size
        observed_errors += outcome
        observed_complements += complement
        wealth_steps.append(
            WealthStep(
                constant_term,
                observed_complements / population.size,
                (),
                support_minimum,
                support_term_count,
            )
        )
        if arm.control_variate_score_key is not None:
            beta_history.append((z_value, u_value))
        selection_order.append(selected)
        selected_items.add(selected)
        min_q = min(min_q, step_min_q)
        max_importance_weight = max(max_importance_weight, importance_weight)
        trace.append(
            {
                "step": step_number,
                "pre_reveal": pre_reveal,
                "draw_uniform": draw_uniform,
                "selected_item_id": selected,
                "selected_q": probability,
                "minimum_q_at_step": step_min_q,
                "revealed_outcome": outcome,
                "complement": complement,
                "importance_weight": importance_weight,
                "z_complement": z_value,
                "expected_control_variate_under_q": expected_cv,
                "u": u_value,
                "beta": beta_value,
                "beta_covariance": beta_estimate.covariance,
                "beta_variance": beta_estimate.variance,
                "cumulative_complements_before": observed_complements - complement,
                "constant_term": constant_term,
                "logical_complement_lower": observed_complements / population.size,
                "support_term_count": support_term_count,
            }
        )
        remaining.remove(selected)
    return {
        "rng_seed": rng_seed,
        "selection_order": selection_order,
        "trace": trace,
        "wealth_steps": wealth_steps,
        "observations": budget,
        "errors_observed": observed_errors,
        "min_q": min_q,
        "max_importance_weight": max_importance_weight,
        "q_replay_passed": True if replay_grade else None,
        "forensic_replay_performed": replay_grade,
        "execution_mode": execution_mode,
        "warnings": warnings,
    }


def _stage1_mixture_result(audit: Mapping[str, object], population: NamedFinitePopulation, config: Stage1Config) -> dict:
    status = "valid"
    upper_bound = None
    empty = False
    multiplier_failure = False
    monotonicity_status = "not_evaluated"
    warning_rows = list(audit["warnings"])
    evaluation = None
    try:
        evaluation = evaluate_running_mixture_bound(
            audit["wealth_steps"],
            config.lambda_grid,
            config.alpha_cs,
            config.inversion_tolerance,
            config.monotonicity_tolerance,
        )
        upper_bound = evaluation.upper_error_bound
        monotonicity_status = evaluation.monotonicity_status
    except EmptyConfidenceSet as error:
        status = "empty_confidence_set"
        empty = True
        warning_rows.append(str(error))
    except SupportAdmissibilityFailure as error:
        status = "invalid_support_admissibility"
        multiplier_failure = True
        warning_rows.append(str(error))
    except MonotonicityFailure as error:
        status = "invalid_monotonicity"
        monotonicity_status = "failed"
        warning_rows.append(str(error))
    except ControlledNumericalFailure as error:
        status = "invalid_numerical"
        warning_rows.append(str(error))
    return {
        "validity_status": status,
        "empty_confidence_set": empty,
        "final_upper_bound": upper_bound,
        "coverage_indicator": (
            upper_bound is not None
            and upper_bound + config.inversion_tolerance >= population.true_prevalence
        ),
        "monotonicity_status": monotonicity_status,
        "multiplier_failure_present": multiplier_failure,
        "minimum_wealth_multiplier": None if evaluation is None else evaluation.min_multiplier,
        "final_log_mixture_wealth": {} if evaluation is None else {
            "candidate_g_0": evaluation.final_log_wealth_g0,
            "candidate_g_1": evaluation.final_log_wealth_g1,
            "reported_lower_g_bound": evaluation.final_log_wealth_at_bound,
        },
        "warnings": warning_rows,
    }


STAGE2_CODE_VERSION = "phase1h-ppi-stage2-primary-map-v1"

STAGE2_PREFLIGHT_MARGIN_REPLICATES = 3
STAGE2_PREFLIGHT_NEGATIVE_CONTROL_REPLICATES = 200
STAGE2_PREFLIGHT_ADDITIONAL_CONTROL_REPLICATES = 5
STAGE2_PREFLIGHT_CONTROL_ANCHOR = (3e-2, 0.5)
STAGE2_PREFLIGHT_NEGATIVE_CONTROLS = (
    "pi_h_zero",
    "conditional_permuted_ppi",
    "global_permuted_ppi",
    "constant_ppi",
)
STAGE2_PREFLIGHT_ADDITIONAL_CONTROLS = (
    "fragility_unrelated_to_error",
    "stable_shared_false_belief",
    "favourable_high_fragility",
)


@dataclass(frozen=True)
class Stage2PopulationWorkUnit:
    unit_id: str
    parameters: Stage2GeneratorParameters
    replicate_id: int
    population_seed: int
    normalization: Stage2MarginCalibration
    config: Stage2Config
    capture_replay_evidence: bool = False
    audit_seed_namespace: str = "evaluation"


def stage2_replay_replicate(config: Stage2Config | None = None) -> int:
    """Outcome-independent identity for the two paired forensic traces."""

    config = config or Stage2Config()
    config.validate()
    return stable_seed(
        config.evaluation_master_seed,
        "stage2-replay-evidence",
        "p_jde=0.003",
        "pi_h=0.75",
        "B=500",
        "UP+SP-epsilon=0.2",
    ) % config.replicates


def _stage2_population_digest(population: NamedFinitePopulation) -> str:
    channels = population.all_observable_scores()
    outcomes = population.hidden_outcomes()
    return digest_rows(
        (
            item_id,
            tuple((key, channels[key][item_id]) for key in sorted(channels)),
            outcomes[item_id],
        )
        for item_id in population.item_ids()
    )


def _stage2_mixture_result(
    wealth_steps: Sequence[WealthStep],
    population: NamedFinitePopulation,
    config: Stage2Config,
) -> dict:
    status = "valid"
    upper_bound = None
    empty = False
    monotonicity_status = "not_evaluated"
    support_status = "passed"
    warnings: List[str] = []
    try:
        evaluation = evaluate_running_mixture_bound(
            wealth_steps,
            config.lambda_grid,
            config.alpha_cs,
            config.inversion_tolerance,
            config.monotonicity_tolerance,
        )
        upper_bound = evaluation.upper_error_bound
        monotonicity_status = evaluation.monotonicity_status
    except EmptyConfidenceSet as error:
        status = "empty_confidence_set"
        empty = True
        warnings.append(str(error))
    except SupportAdmissibilityFailure as error:
        status = "invalid_support_admissibility"
        support_status = "failed"
        warnings.append(str(error))
    except MonotonicityFailure as error:
        status = "invalid_monotonicity"
        monotonicity_status = "failed"
        warnings.append(str(error))
    except ControlledNumericalFailure as error:
        status = "invalid_numerical"
        warnings.append(str(error))
    raw = {
        "validity_status": status,
        "empty_confidence_set": empty,
        "final_upper_bound": upper_bound,
        "coverage_indicator": (
            upper_bound is not None
            and upper_bound + config.inversion_tolerance
            >= population.true_prevalence
        ),
        "monotonicity_status": monotonicity_status,
        "support_status": support_status,
        "warnings": warnings,
    }
    raw["effective_upper_bound"] = effective_upper_bound(raw)
    return raw


def effective_upper_bound(record: Mapping[str, object]) -> float:
    """Return the sole Stage 2 aggregation bound without rewriting raw evidence."""

    raw = record.get("final_upper_bound")
    status = str(record.get("validity_status"))
    empty = bool(record.get("empty_confidence_set"))
    if empty or status == "empty_confidence_set":
        if raw is not None or not (empty and status == "empty_confidence_set"):
            raise ValueError("empty confidence-set record has inconsistent raw fields")
        return 1.0
    if status == "valid" and raw is not None:
        value = float(raw)
        if math.isfinite(value) and 0.0 <= value <= 1.0:
            return value
    raise ValueError("non-empty Stage 2 bound is genuinely undefined or invalid")


@dataclass(frozen=True)
class LeanAuditWorkUnit:
    work_unit_id: str
    population: NamedFinitePopulation
    arm: Stage1ArmSpec
    budget: int
    ridge: float
    rng_seed: int
    lambda_grid: Tuple[float, ...] = (0.05, 0.10, 0.25, 0.50)
    alpha_cs: float = 0.05
    inversion_tolerance: float = 1e-10
    monotonicity_tolerance: float = 1e-10


def _execute_lean_audit_work_unit(work_unit: LeanAuditWorkUnit) -> dict:
    audit = simulate_named_audit(
        work_unit.population,
        work_unit.arm,
        work_unit.budget,
        work_unit.ridge,
        work_unit.rng_seed,
        execution_mode="lean",
    )
    evaluation = evaluate_running_mixture_bound(
        audit["wealth_steps"],
        work_unit.lambda_grid,
        work_unit.alpha_cs,
        work_unit.inversion_tolerance,
        work_unit.monotonicity_tolerance,
    )
    return {
        "work_unit_id": work_unit.work_unit_id,
        "rng_seed": work_unit.rng_seed,
        "selection_order": audit["selection_order"],
        "draw_uniforms": [row["draw_uniform"] for row in audit["trace"]],
        "selected_q": [row["selected_q"] for row in audit["trace"]],
        "revealed_outcomes": [
            row["revealed_outcome"] for row in audit["trace"]
        ],
        "validity_status": "valid",
        "upper_bound": evaluation.upper_error_bound,
        "minimum_q": audit["min_q"],
        "maximum_importance_weight": audit["max_importance_weight"],
    }


def execute_lean_audit_work_units(
    work_units: Sequence[LeanAuditWorkUnit],
    workers: int,
) -> List[dict]:
    """Execution-order invariant bounded worker primitive used by Stage 2."""

    if workers <= 0:
        raise ValueError("lean audit worker count must be positive")
    units = tuple(sorted(work_units, key=lambda unit: unit.work_unit_id))
    if len({unit.work_unit_id for unit in units}) != len(units):
        raise ValueError("lean audit work-unit IDs must be unique")
    if workers == 1:
        results = [_execute_lean_audit_work_unit(unit) for unit in units]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_execute_lean_audit_work_unit, units))
    return sorted(results, key=lambda result: result["work_unit_id"])


def _stage2_prefix_record(
    work_unit: Stage2PopulationWorkUnit,
    generated: object,
    population_digest: str,
    arm: Stage1ArmSpec,
    audit: Mapping[str, object],
    budget: int,
    audit_seed: int,
) -> dict:
    prefix_trace = audit["trace"][:budget]
    mixture = _stage2_mixture_result(
        audit["wealth_steps"][:budget], generated.population, work_unit.config
    )
    selected_q = [float(row["selected_q"]) for row in prefix_trace]
    importance_weights = [float(row["importance_weight"]) for row in prefix_trace]
    errors = sum(int(row["revealed_outcome"]) for row in prefix_trace)
    return {
        "schema_version": work_unit.config.schema_version,
        "code_version": STAGE2_CODE_VERSION,
        "unit_id": work_unit.unit_id,
        "p_jde_target": work_unit.parameters.p_jde_target,
        "p_jde_realized": generated.population.true_prevalence,
        "pi_H": work_unit.parameters.pi_h,
        "control_id": work_unit.parameters.control_id,
        "replicate_id": work_unit.replicate_id,
        "population_seed": work_unit.population_seed,
        "population_digest": population_digest,
        "audit_seed": audit_seed,
        "arm_id": arm.arm_id,
        "conceptual_arm": arm.conceptual_arm,
        "B": budget,
        "epsilon_samp": arm.epsilon_samp,
        "K": 8,
        "lambda_grid": list(work_unit.config.lambda_grid),
        "observed_event_count": errors,
        "zero_event": errors == 0,
        "final_upper_bound": mixture["final_upper_bound"],
        "effective_upper_bound": mixture["effective_upper_bound"],
        "coverage_indicator": mixture["coverage_indicator"],
        "minimum_q": min(float(row["minimum_q_at_step"]) for row in prefix_trace),
        "minimum_selected_q": min(selected_q),
        "maximum_importance_weight": max(importance_weights),
        "validity_status": mixture["validity_status"],
        "empty_confidence_set": mixture["empty_confidence_set"],
        "monotonicity_status": mixture["monotonicity_status"],
        "support_status": mixture["support_status"],
        "warnings": mixture["warnings"],
        "collider_before": generated.collider_diagnostic[
            "association_before_agreement"
        ],
        "collider_after": generated.collider_diagnostic[
            "association_after_agreement"
        ],
        "forensic_replay_performed": audit["forensic_replay_performed"],
    }


def _stage2_audit_seed_master(work_unit: Stage2PopulationWorkUnit) -> int:
    """Resolve the declared namespace without falling back to evaluation seeds."""

    audit_seed_masters = {
        "evaluation": work_unit.config.evaluation_master_seed,
        "evaluation_controls": work_unit.config.evaluation_master_seed,
        "negative_control_calibration": work_unit.config.negative_control_master_seed,
        "negative_control_preflight": work_unit.config.negative_control_master_seed,
    }
    try:
        return audit_seed_masters[work_unit.audit_seed_namespace]
    except KeyError as error:
        raise ValueError("unknown Stage 2 audit seed namespace") from error


def _run_stage2_population_work_unit(
    work_unit: Stage2PopulationWorkUnit,
) -> dict:
    """Generate one population and all nine nested-budget audit trajectories."""

    work_unit.config.validate()
    generated = generate_stage2_population(
        work_unit.parameters,
        work_unit.population_seed,
        work_unit.normalization,
        work_unit.config,
    )
    population = generated.population
    population_digest = _stage2_population_digest(population)
    rows: List[dict] = []
    replay_audits: List[dict] = []
    population_record = None
    audit_seed_master = _stage2_audit_seed_master(work_unit)
    for arm in stage2_trajectory_arms(work_unit.config):
        selected_forensic_arm = (
            work_unit.capture_replay_evidence
            and (
                arm.conceptual_arm == "UP"
                or (
                    arm.conceptual_arm == "SP"
                    and arm.epsilon_samp == 0.2
                )
            )
        )
        execution_mode = "replay_grade" if selected_forensic_arm else "lean"
        audit_seed = stable_seed(
            audit_seed_master,
            work_unit.audit_seed_namespace,
            work_unit.parameters.p_jde_target,
            work_unit.parameters.pi_h,
            work_unit.parameters.control_id,
            work_unit.replicate_id,
            arm.arm_id,
            "stage2-audit",
        )
        audit = simulate_named_audit(
            population,
            arm,
            max(work_unit.config.budgets),
            work_unit.config.ridge,
            audit_seed,
            execution_mode=execution_mode,
        )
        for budget in work_unit.config.budgets:
            rows.append(
                _stage2_prefix_record(
                    work_unit,
                    generated,
                    population_digest,
                    arm,
                    audit,
                    budget,
                    audit_seed,
                )
            )
        if selected_forensic_arm:
            if population_record is None:
                population_record = _stage1_population_record(
                    generated,
                    work_unit.replicate_id,
                    work_unit.population_seed,
                )
            replay_audits.append(
                {
                    "audit_id": f"{work_unit.unit_id}:{arm.arm_id}",
                    "scenario_id": population.scenario_id,
                    "replicate_id": work_unit.replicate_id,
                    "k": 8,
                    "arm": asdict(arm),
                    "rng_seed": audit_seed,
                    "selection_order": audit["selection_order"],
                    "trace": audit["trace"],
                    "lambda_grid": list(work_unit.config.lambda_grid),
                    "lambda_grid_digest": _lambda_grid_digest(
                        work_unit.config.lambda_grid
                    ),
                    "mixture_result": _stage2_mixture_result(
                        audit["wealth_steps"], population, work_unit.config
                    ),
                }
            )
    rows.sort(
        key=lambda row: (
            row["p_jde_target"],
            row["pi_H"],
            row["replicate_id"],
            row["arm_id"],
            row["B"],
        )
    )
    return {
        "unit_id": work_unit.unit_id,
        "rows": rows,
        "replay_population": population_record,
        "replay_audits": replay_audits,
        "identity_sentinel_passed": generated.identity_sentinel_passed,
        "structural_invariance_passed": generated.structural_invariance_passed,
    }


def execute_stage2_work_units(
    work_units: Sequence[Stage2PopulationWorkUnit],
    workers: int = 1,
) -> List[dict]:
    """Execute deterministic independent units and canonically sort output."""

    if workers <= 0:
        raise ValueError("Stage 2 worker count must be positive")
    units = tuple(sorted(work_units, key=lambda unit: unit.unit_id))
    if len({unit.unit_id for unit in units}) != len(units):
        raise ValueError("Stage 2 work-unit identities must be unique")
    if workers == 1:
        results = [_run_stage2_population_work_unit(unit) for unit in units]
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            results = list(executor.map(_run_stage2_population_work_unit, units))
    return sorted(results, key=lambda result: result["unit_id"])


def build_stage2_primary_work_units(
    calibrations: Mapping[Tuple[float, float], Stage2GeneratorParameters],
    normalization: Stage2MarginCalibration,
    config: Stage2Config | None = None,
) -> Tuple[Stage2PopulationWorkUnit, ...]:
    config = config or Stage2Config()
    config.validate()
    expected = {
        (p_jde, pi_h)
        for p_jde in config.p_jde_targets
        for pi_h in config.pi_h_values
    }
    if set(calibrations) != expected:
        raise ValueError("Stage 2 risk calibration map is incomplete")
    replay_replicate = stage2_replay_replicate(config)
    units = []
    for p_jde, pi_h in sorted(expected):
        parameters = calibrations[(p_jde, pi_h)]
        for replicate in range(config.replicates):
            unit_id = f"p{p_jde:.12g}-h{pi_h:.12g}-r{replicate:04d}"
            units.append(
                Stage2PopulationWorkUnit(
                    unit_id=unit_id,
                    parameters=parameters,
                    replicate_id=replicate,
                    population_seed=stable_seed(
                        config.evaluation_master_seed,
                        p_jde,
                        pi_h,
                        replicate,
                        "stage2-population",
                    ),
                    normalization=normalization,
                    config=config,
                    capture_replay_evidence=(
                        p_jde == 3e-3
                        and pi_h == 0.75
                        and replicate == replay_replicate
                    ),
                )
            )
    return tuple(units)


def build_stage2_control_work_units(
    base_parameters: Stage2GeneratorParameters,
    normalization: Stage2MarginCalibration,
    control_ids: Sequence[str],
    replicate_count: int,
    seed_namespace: str,
    config: Stage2Config | None = None,
) -> Tuple[Stage2PopulationWorkUnit, ...]:
    """Build only the accepted controls using a declared development namespace."""

    config = config or Stage2Config()
    config.validate()
    if seed_namespace not in {
        "negative_control_calibration",
        "negative_control_preflight",
        "evaluation_controls",
    }:
        raise ValueError("unknown Stage 2 control seed namespace")
    if replicate_count <= 0:
        raise ValueError("Stage 2 control replicate count must be positive")
    master_seed = (
        config.negative_control_master_seed
        if seed_namespace in {
            "negative_control_calibration",
            "negative_control_preflight",
        }
        else config.evaluation_master_seed
    )
    units = []
    for control_id in control_ids:
        parameters = stage2_control_parameters(base_parameters, control_id)
        for replicate in range(replicate_count):
            unit_id = f"control-{control_id}-r{replicate:04d}"
            units.append(
                Stage2PopulationWorkUnit(
                    unit_id,
                    parameters,
                    replicate,
                    stable_seed(
                        master_seed,
                        seed_namespace,
                        control_id,
                        replicate,
                        "stage2-control-population",
                    ),
                    normalization,
                    config,
                    False,
                    seed_namespace,
                )
            )
    return tuple(units)


def _proportion(rows: Sequence[Mapping[str, object]], field: str) -> float:
    if not rows:
        raise ValueError("cannot summarize an empty Stage 2 record group")
    return math.fsum(bool(row[field]) for row in rows) / len(rows)


def type7_percentile(values: Sequence[float], probability: float) -> float:
    """Deterministic Hyndman-Fan type-7 percentile."""

    ordered = sorted(float(value) for value in values)
    if not ordered or not 0.0 <= probability <= 1.0:
        raise ValueError("percentile inputs are invalid")
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("percentile values must be finite")
    position = probability * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = int(math.ceil(position))
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return math.fsum(((1.0 - weight) * ordered[lower], weight * ordered[upper]))


def _binomial_cdf(successes: int, trials: int, probability: float) -> float:
    return math.fsum(
        math.comb(trials, index)
        * probability**index
        * (1.0 - probability) ** (trials - index)
        for index in range(successes + 1)
    )


def clopper_pearson_upper(
    successes: int, trials: int, alpha: float = 0.05
) -> float:
    """One-sided exact binomial upper limit, used only as a diagnostic."""

    if not 0 <= successes <= trials or trials <= 0 or not 0.0 < alpha < 1.0:
        raise ValueError("Clopper-Pearson inputs are invalid")
    if successes == trials:
        return 1.0
    low, high = successes / trials, 1.0
    for _ in range(80):
        midpoint = (low + high) / 2.0
        if _binomial_cdf(successes, trials, midpoint) > alpha:
            low = midpoint
        else:
            high = midpoint
    return high


@dataclass(frozen=True)
class Stage2PrimaryBootstrapWorld:
    """One resampled development world, indexed only by generator stratum."""

    bootstrap_replicate: int
    stratum_indices: Tuple[Tuple[Tuple[float, float], Tuple[int, ...]], ...]

    def indices_for(self, p_jde_target: float, pi_h: float) -> Tuple[int, ...]:
        key = (float(p_jde_target), float(pi_h))
        for stratum, indices in self.stratum_indices:
            if stratum == key:
                return indices
        raise KeyError(f"unknown Stage 2 bootstrap generator stratum: {key}")


def _iter_stage2_primary_bootstrap_worlds(
    config: Stage2Config,
    bootstrap_replicates: int,
) -> Iterator[Stage2PrimaryBootstrapWorld]:
    """Yield the single authoritative primary-bootstrap RNG stream.

    The replicate-count argument is private and exists only for bounded tests.
    The public execution path always supplies the frozen 10,000 count.
    """

    config.validate()
    if bootstrap_replicates <= 0:
        raise ValueError("primary bootstrap replicate count must be positive")
    rng = random.Random(stage2_development_primary_bootstrap_seed(config))
    strata = stage2_generator_strata(config)
    for bootstrap_replicate in range(bootstrap_replicates):
        yield Stage2PrimaryBootstrapWorld(
            bootstrap_replicate,
            tuple(
                (
                    stratum,
                    tuple(rng.randrange(config.replicates) for _ in range(config.replicates)),
                )
                for stratum in strata
            ),
        )


def summarize_stage2_cells(
    records: Sequence[Mapping[str, object]],
    config: Stage2Config | None = None,
) -> List[dict]:
    """Apply eligibility before computing the SP-versus-UP contrast."""

    config = config or Stage2Config()
    config.validate()
    summaries: List[dict] = []
    for cell in stage2_cells(config):
        up = [
            row
            for row in records
            if row["p_jde_target"] == cell.p_jde_target
            and row["pi_H"] == cell.pi_h
            and row["B"] == cell.budget
            and row["conceptual_arm"] == "UP"
            and row["control_id"] == "primary"
        ]
        sp = [
            row
            for row in records
            if row["p_jde_target"] == cell.p_jde_target
            and row["pi_H"] == cell.pi_h
            and row["B"] == cell.budget
            and row["conceptual_arm"] == "SP"
            and row["epsilon_samp"] == cell.epsilon_samp
            and row["control_id"] == "primary"
        ]
        if len(up) != config.replicates or len(sp) != config.replicates:
            raise ValueError(
                f"Stage 2 cell {cell.cell_id} lacks the required paired replicates"
            )
        coverage_up = _proportion(up, "coverage_indicator")
        coverage_sp = _proportion(sp, "coverage_indicator")
        zero_up = _proportion(up, "zero_event")
        zero_sp = _proportion(sp, "zero_event")
        invalid_count = sum(str(row["validity_status"]).startswith("invalid") for row in (*up, *sp))
        if invalid_count:
            raise InvalidDevelopmentRun(
                f"Stage 2 cell {cell.cell_id} contains a genuine invalid bound"
            )
        empty_up = sum(bool(row["empty_confidence_set"]) for row in up)
        empty_sp = sum(bool(row["empty_confidence_set"]) for row in sp)
        effective_up = [effective_upper_bound(row) for row in up]
        effective_sp = [effective_upper_bound(row) for row in sp]
        mean_up = math.fsum(effective_up) / len(effective_up)
        mean_sp = math.fsum(effective_sp) / len(effective_sp)
        exclusion_reasons = []
        if coverage_up < 0.94:
            exclusion_reasons.append("coverage_UP_below_0.94")
        if coverage_sp < 0.94:
            exclusion_reasons.append("coverage_SP_below_0.94")
        if max(zero_up, zero_sp) > 0.50:
            exclusion_reasons.append("zero_event_proportion_above_0.50")
        if mean_up >= 1.0:
            exclusion_reasons.append("mean_effective_UP_not_below_1")
        eligible = not exclusion_reasons
        delta = None
        if eligible:
            if mean_up <= 0.0:
                raise ValueError("eligible Stage 2 cell has an undefined Delta denominator")
            delta = 1.0 - mean_sp / mean_up
        summaries.append(
            {
                "cell_id": cell.cell_id,
                "p_jde_target": cell.p_jde_target,
                "B": cell.budget,
                "pi_H": cell.pi_h,
                "epsilon_samp": cell.epsilon_samp,
                "replicate_count": config.replicates,
                "coverage_UP": coverage_up,
                "coverage_SP": coverage_sp,
                "zero_event_proportion_UP": zero_up,
                "zero_event_proportion_SP": zero_sp,
                "invalid_count": invalid_count,
                "empty_confidence_set_count_UP": empty_up,
                "empty_confidence_set_count_SP": empty_sp,
                "empty_cs_rate_UP": empty_up / len(up),
                "empty_cs_rate_SP": empty_sp / len(sp),
                "empty_cs_rate_UP_cp95_upper": clopper_pearson_upper(empty_up, len(up)),
                "empty_cs_rate_SP_cp95_upper": clopper_pearson_upper(empty_sp, len(sp)),
                "mean_effective_upper_bound_UP": mean_up,
                "mean_effective_upper_bound_SP": mean_sp,
                "eligible": eligible,
                "exclusion_reasons": exclusion_reasons,
                "Delta_cell": delta,
            }
        )
    return summaries


def empirical_gamma_nc(
    cells_by_class: Mapping[str, Sequence[Mapping[str, object]]],
    config: Stage2Config | None = None,
) -> dict:
    """Cluster-bootstrap the four class aggregates and return one gamma_NC."""

    config = config or Stage2Config()
    config.validate()
    required = {
        "pi_h_zero",
        "conditional_permuted_ppi",
        "global_permuted_ppi",
        "constant_ppi",
    }
    if set(cells_by_class) != required:
        raise ValueError("negative-control calibration classes are incomplete")
    class_quantiles = {}
    class_points = {}
    cell_quantiles = {}
    for control_id in sorted(required):
        cells = list(cells_by_class[control_id])
        if len(cells) != len(config.epsilon_values) * len(config.budgets):
            raise ValueError("negative-control class must contain exactly 12 cells")
        replicate_ids = tuple(cells[0]["replicate_ids"])
        if len(replicate_ids) != config.replicates:
            raise ValueError("negative-control cell replicate count is incomplete")
        if any(tuple(cell["replicate_ids"]) != replicate_ids for cell in cells):
            raise ValueError("negative-control class cells are not population-paired")
        class_points[control_id] = math.fsum(float(cell["G_cell"]) for cell in cells) / len(cells)
        constant_cells = all(
            len(set(cell["effective_UP"])) == 1
            and len(set(cell["effective_SP"])) == 1
            for cell in cells
        )
        if constant_cells:
            per_cell_bootstrap = [[float(cell["G_cell"])] for cell in cells]
            class_bootstrap = [class_points[control_id]]
        else:
            rng = random.Random(stable_seed(config.negative_control_bootstrap_seed, control_id))
            class_bootstrap = []
            per_cell_bootstrap = [[] for _ in cells]
            for _ in range(config.negative_control_bootstrap_replicates):
                indices = [rng.randrange(len(replicate_ids)) for _ in replicate_ids]
                boot_cells = []
                for cell_index, cell in enumerate(cells):
                    up = cell["effective_UP"]
                    sp = cell["effective_SP"]
                    mean_up = math.fsum(float(up[index]) for index in indices) / len(indices)
                    mean_sp = math.fsum(float(sp[index]) for index in indices) / len(indices)
                    if mean_up <= 0.0:
                        raise InvalidDevelopmentRun("negative-control bootstrap denominator is zero")
                    value = 1.0 - mean_sp / mean_up
                    per_cell_bootstrap[cell_index].append(value)
                    boot_cells.append(value)
                class_bootstrap.append(math.fsum(boot_cells) / len(boot_cells))
        class_quantiles[control_id] = type7_percentile(class_bootstrap, 0.975)
        cell_quantiles[control_id] = {
            str(cell["cell_id"]): type7_percentile(values, 0.975)
            for cell, values in zip(cells, per_cell_bootstrap)
        }
    gamma = max(class_quantiles.values())
    return {
        "gamma_NC": gamma,
        "tau_NC": config.tau_nc,
        "validity_gate_passed": gamma <= config.tau_nc,
        "class_point_estimates": class_points,
        "class_bootstrap_q_0_975": class_quantiles,
        "cell_bootstrap_q_0_975": cell_quantiles,
        "bootstrap_replicates": config.negative_control_bootstrap_replicates,
        "percentile_type": 7,
        "bootstrap_seed": config.negative_control_bootstrap_seed,
    }


def classify_stage2_development(
    cell_summaries: Sequence[Mapping[str, object]],
    gamma_nc: float,
    delta_lower: Optional[float],
    pooled_empty_rate_lower: float = 0.0,
    config: Stage2Config | None = None,
) -> str:
    config = config or Stage2Config()
    config.validate()
    if pooled_empty_rate_lower > config.alpha_cs:
        return "IMPLEMENTATION_FAILURE_HOLD"
    if gamma_nc > config.tau_nc:
        return "INVALID_DEVELOPMENT_SWEEP"
    if not stage2_structural_representation_complete(cell_summaries, config):
        return "INCONCLUSIVE_BY_DEGENERACY"
    if delta_lower is None:
        raise ValueError("interpretable Stage 2 classification requires Delta lower limit")
    if delta_lower > gamma_nc:
        return "POSITIVE_DEVELOPMENT_LEVEL"
    if delta_lower > 0.0:
        return "INCONCLUSIVE"
    return "NEGATIVE_PPI_PATH_REJECTED"


def stage2_structural_representation_complete(
    cell_summaries: Sequence[Mapping[str, object]],
    config: Stage2Config | None = None,
) -> bool:
    config = config or Stage2Config()
    expected = {
        (p_jde, budget, pi_h)
        for p_jde in config.p_jde_targets
        for budget in config.budgets
        for pi_h in config.pi_h_values
    }
    represented = {
        (float(row["p_jde_target"]), int(row["B"]), float(row["pi_H"]))
        for row in cell_summaries
        if bool(row["eligible"])
    }
    return represented == expected


def bootstrap_stage2_primary_statistics(
    records: Sequence[Mapping[str, object]],
    cell_summaries: Sequence[Mapping[str, object]],
    config: Stage2Config | None = None,
    *,
    _bounded_bootstrap_replicates: Optional[int] = None,
) -> dict:
    """Bootstrap Delta and pooled empties from the same 12-stratum worlds.

    Eligibility is consumed as a point-estimate mask and never recomputed.  The
    private bounded override supports unit fixtures only; normal execution is
    fixed to ``config.primary_bootstrap_replicates``.
    """

    config = config or Stage2Config()
    config.validate()
    bootstrap_replicates = (
        config.primary_bootstrap_replicates
        if _bounded_bootstrap_replicates is None
        else _bounded_bootstrap_replicates
    )
    if bootstrap_replicates <= 0:
        raise ValueError("primary bootstrap replicate count must be positive")
    if len(cell_summaries) != len(stage2_cells(config)):
        raise ValueError("Stage 2 bootstrap requires the complete 144-cell summary")

    eligible = tuple(row for row in cell_summaries if bool(row["eligible"]))
    eligibility_mask = tuple(str(row["cell_id"]) for row in eligible)
    interpretable = stage2_structural_representation_complete(cell_summaries, config)

    primary_records = [row for row in records if row["control_id"] == "primary"]
    clusters: Dict[Tuple[float, float, int], List[Mapping[str, object]]] = {}
    for row in primary_records:
        key = (
            float(row["p_jde_target"]),
            float(row["pi_H"]),
            int(row["replicate_id"]),
        )
        clusters.setdefault(key, []).append(row)
    expected_cluster_count = len(stage2_generator_strata(config)) * config.replicates
    if len(clusters) != expected_cluster_count:
        raise InvalidDevelopmentRun("primary bootstrap population clusters are incomplete")

    cluster_empty_counts: Dict[Tuple[float, float], Tuple[int, ...]] = {}
    cluster_row_counts: Dict[Tuple[float, float], Tuple[int, ...]] = {}
    for stratum in stage2_generator_strata(config):
        stratum_clusters = [clusters[(stratum[0], stratum[1], r)] for r in range(config.replicates)]
        cluster_empty_counts[stratum] = tuple(
            sum(bool(row["empty_confidence_set"]) for row in cluster)
            for cluster in stratum_clusters
        )
        cluster_row_counts[stratum] = tuple(len(cluster) for cluster in stratum_clusters)

    observed_empty = math.fsum(
        math.fsum(values) for values in cluster_empty_counts.values()
    ) / math.fsum(math.fsum(values) for values in cluster_row_counts.values())

    cell_vectors = []
    if interpretable:
        for cell in eligible:
            stratum = (float(cell["p_jde_target"]), float(cell["pi_H"]))
            budget = int(cell["B"])
            epsilon = float(cell["epsilon_samp"])
            up_by_replicate: List[Optional[float]] = [None] * config.replicates
            sp_by_replicate: List[Optional[float]] = [None] * config.replicates
            for row in primary_records:
                if (
                    float(row["p_jde_target"]) != stratum[0]
                    or float(row["pi_H"]) != stratum[1]
                    or int(row["B"]) != budget
                ):
                    continue
                replicate = int(row["replicate_id"])
                if row["conceptual_arm"] == "UP":
                    up_by_replicate[replicate] = effective_upper_bound(row)
                elif (
                    row["conceptual_arm"] == "SP"
                    and float(row["epsilon_samp"]) == epsilon
                ):
                    sp_by_replicate[replicate] = effective_upper_bound(row)
            if any(value is None for value in (*up_by_replicate, *sp_by_replicate)):
                raise InvalidDevelopmentRun("eligible Delta bootstrap cell is incomplete")
            cell_vectors.append(
                (
                    stratum,
                    tuple(float(value) for value in up_by_replicate),
                    tuple(float(value) for value in sp_by_replicate),
                )
            )

    delta_bootstrap: List[float] = []
    empty_bootstrap: List[float] = []
    world_digest = hashlib.sha256()
    for world in _iter_stage2_primary_bootstrap_worlds(config, bootstrap_replicates):
        world_digest.update(
            _canonical_json_bytes(
                {
                    "bootstrap_replicate": world.bootstrap_replicate,
                    "strata": [
                        [list(stratum), list(indices)]
                        for stratum, indices in world.stratum_indices
                    ],
                }
            )
        )
        selected_empty = 0
        selected_rows = 0
        for stratum in stage2_generator_strata(config):
            indices = world.indices_for(*stratum)
            empty_counts = cluster_empty_counts[stratum]
            row_counts = cluster_row_counts[stratum]
            selected_empty += sum(empty_counts[index] for index in indices)
            selected_rows += sum(row_counts[index] for index in indices)
        empty_bootstrap.append(selected_empty / selected_rows)
        if interpretable:
            cell_deltas = []
            for stratum, up, sp in cell_vectors:
                indices = world.indices_for(*stratum)
                mean_up = math.fsum(up[index] for index in indices) / len(indices)
                mean_sp = math.fsum(sp[index] for index in indices) / len(indices)
                if mean_up <= 0.0:
                    raise InvalidDevelopmentRun("primary bootstrap Delta denominator is zero")
                cell_deltas.append(1.0 - mean_sp / mean_up)
            delta_bootstrap.append(math.fsum(cell_deltas) / len(cell_deltas))

    result = {
        "development_primary_bootstrap_seed": stage2_development_primary_bootstrap_seed(config),
        "bootstrap_replicates": bootstrap_replicates,
        "percentile_type": 7,
        "generator_strata": [list(stratum) for stratum in stage2_generator_strata(config)],
        "generator_stratum_count": len(stage2_generator_strata(config)),
        "resampling_unit": "generated_population_replicate",
        "shared_delta_and_pooled_empty_worlds": True,
        "bootstrap_world_digest": world_digest.hexdigest(),
        "eligibility_mask_source": "frozen_point_estimate_cell_summaries",
        "eligible_cell_ids": list(eligibility_mask),
        "pooled_empty_rate": observed_empty,
        "pooled_empty_cluster_bootstrap_95_lower": type7_percentile(empty_bootstrap, 0.05),
        "cluster_count": expected_cluster_count,
    }
    if not interpretable:
        return result | {
            "Delta_bar": None,
            "Delta_bar_minus": None,
            "status": "INCONCLUSIVE_BY_DEGENERACY",
        }
    return result | {
        "Delta_bar": aggregate_stage2_delta(cell_summaries),
        "Delta_bar_minus": type7_percentile(delta_bootstrap, 0.05),
        "status": "INTERPRETABLE",
    }


def aggregate_stage2_delta(
    cell_summaries: Sequence[Mapping[str, object]],
) -> Optional[float]:
    if not stage2_structural_representation_complete(cell_summaries):
        return None
    values = [float(row["Delta_cell"]) for row in cell_summaries if row["eligible"]]
    return None if not values else math.fsum(values) / len(values)


def stage2_manifest(
    config: Stage2Config,
    normalization: Stage2MarginCalibration,
    calibrations: Mapping[Tuple[float, float], Stage2GeneratorParameters],
    gamma_nc: Mapping[str, object],
    workers: int,
) -> dict:
    config.validate()
    if workers <= 0:
        raise ValueError("Stage 2 manifest worker count must be positive")
    return {
        "schema_version": config.schema_version,
        "code_version": STAGE2_CODE_VERSION,
        "manifest_type": config.manifest_type,
        "development_only": True,
        "configuration": _stage2_development_configuration(config),
        "margin_normalization": asdict(normalization),
        "risk_calibrations": [
            {
                "p_jde_target": key[0],
                "pi_H": key[1],
                **asdict(calibrations[key]),
            }
            for key in sorted(calibrations)
        ],
        "gamma_NC": gamma_nc["gamma_NC"],
        "negative_control_calibration": dict(gamma_nc),
        "seed_namespaces": {
            "margin_and_risk_calibration": config.calibration_master_seed,
            "negative_control_calibration": config.negative_control_master_seed,
            "negative_control_bootstrap": config.negative_control_bootstrap_seed,
            "evaluation": config.evaluation_master_seed,
            "development_primary_bootstrap": stage2_development_primary_bootstrap_seed(config),
            "confirmatory_bootstrap": "reserved_not_consumed",
            "disjoint": True,
        },
        "worker_count": workers,
        "worker_count_is_execution_only": True,
        "nested_budget_rule": "one B=500 trajectory; report prefixes 50,100,200,500",
        "replay_selection_rule": {
            "p_jde_target": 3e-3,
            "pi_H": 0.75,
            "B": 500,
            "paired_arms": ["UP", "SP"],
            "SP_epsilon_samp": 0.2,
            "replicate_id": stage2_replay_replicate(config),
            "selection_is_outcome_independent": True,
        },
        "confirmatory_manifest": False,
    }


def _stage2_development_configuration(config: Stage2Config) -> dict:
    """Serialize development configuration without exposing the reserved seed."""

    configuration = {
        name: getattr(config, name)
        for name in config.__dataclass_fields__
        if name != "bootstrap_master_seed"
    }
    configuration["bootstrap_master_seed_status"] = "reserved_not_consumed"
    configuration["development_primary_bootstrap_seed"] = (
        stage2_development_primary_bootstrap_seed(config)
    )
    return configuration


def stage2_primary_map_manifest(
    config: Stage2Config,
    normalization: Stage2MarginCalibration,
    calibrations: Mapping[Tuple[float, float], Stage2GeneratorParameters],
    workers: int,
    provenance: Mapping[str, object],
) -> dict:
    """Frozen, development-only manifest for the public primary-map path."""

    config.validate()
    if workers <= 0:
        raise ValueError("Stage 2 primary-map worker count must be positive")
    expected = set(stage2_generator_strata(config))
    if set(calibrations) != expected:
        raise ValueError("Stage 2 primary-map calibration map is incomplete")
    return {
        "schema_version": "ppi-stage2-primary-map-v1",
        "code_version": STAGE2_CODE_VERSION,
        "manifest_type": config.manifest_type,
        "development_only": True,
        "confirmatory_manifest": False,
        "configuration": _stage2_development_configuration(config),
        "margin_normalization": asdict(normalization),
        "risk_calibrations": [
            {"p_jde_target": key[0], "pi_H": key[1], **asdict(calibrations[key])}
            for key in sorted(calibrations)
        ],
        "gamma_NC": config.gamma_nc,
        "tau_NC": config.tau_nc,
        "git_provenance": dict(provenance),
        "environment": _execution_environment(),
        "seed_namespaces": {
            "calibration": config.calibration_master_seed,
            "evaluation": config.evaluation_master_seed,
            "development_primary_bootstrap": stage2_development_primary_bootstrap_seed(config),
            "confirmatory_bootstrap": "reserved_not_consumed",
        },
        "primary_bootstrap": {
            "generator_strata": [list(stratum) for stratum in stage2_generator_strata(config)],
            "generator_stratum_count": 12,
            "interpretation_stratum_count": 48,
            "replicates": config.primary_bootstrap_replicates,
            "rng": "random.Random",
            "draw_primitive": "randrange",
            "eligibility_mask": "frozen_from_point_estimate_summaries",
            "shared_delta_and_pooled_empty_worlds": True,
        },
        "worker_count": workers,
        "worker_count_is_execution_only": True,
        "nested_budget_rule": "one B=500 trajectory; report prefixes 50,100,200,500",
        "replay_selection_rule": {
            "p_jde_target": 3e-3,
            "pi_H": 0.75,
            "B": 500,
            "paired_arms": ["UP", "SP"],
            "SP_epsilon_samp": 0.2,
            "replicate_id": stage2_replay_replicate(config),
            "selection_is_outcome_independent": True,
        },
    }


def stage2_preflight_plan(config: Stage2Config | None = None) -> dict:
    """Return the frozen, development-only control-preflight plan.

    This deliberately contains no evaluation or bootstrap work units.  The
    values are manifest material rather than command-line scientific knobs.
    """

    config = config or Stage2Config()
    config.validate()
    return {
        "manifest_type": "development_only_stage2_control_preflight",
        "configuration": _stage2_development_configuration(config),
        "margin_calibration": {
            "replicates": STAGE2_PREFLIGHT_MARGIN_REPLICATES,
            "seed_namespace": "margin_and_risk_calibration",
            "observable_inputs_only": True,
        },
        "risk_calibration": {
            "seed_count": 10,
            "seed_namespace": "margin_and_risk_calibration",
            "inspected_quantity": "aggregate_true_jde_prevalence_only",
            "cell_count": len(config.p_jde_targets) * len(config.pi_h_values),
        },
        "negative_control_calibration": {
            "control_ids": list(STAGE2_PREFLIGHT_NEGATIVE_CONTROLS),
            "replicates_per_control": STAGE2_PREFLIGHT_NEGATIVE_CONTROL_REPLICATES,
            "seed_namespace": "negative_control_calibration",
            "gamma_percentile": 0.975,
            "bootstrap_replicates": config.negative_control_bootstrap_replicates,
            "bootstrap_percentile_type": 7,
            "bootstrap_seed": config.negative_control_bootstrap_seed,
            "tau_NC": config.tau_nc,
            "estimand": "cell ratio of means; equal-weight class mean; max class q0.975",
            "anchor": {
                "p_jde_target": STAGE2_PREFLIGHT_CONTROL_ANCHOR[0],
                "pi_H": STAGE2_PREFLIGHT_CONTROL_ANCHOR[1],
            },
        },
        "additional_control_preflight": {
            "control_ids": list(STAGE2_PREFLIGHT_ADDITIONAL_CONTROLS),
            "replicates_per_control": STAGE2_PREFLIGHT_ADDITIONAL_CONTROL_REPLICATES,
            "seed_namespace": "negative_control_preflight",
        },
        "not_consumed_seed_namespaces": ["evaluation", "bootstrap"],
        "full_stage2_evaluation_executed": False,
    }


def _stage2_margin_calibration(
    config: Stage2Config,
) -> Tuple[Stage2MarginCalibration, Tuple[int, ...]]:
    """Calibrate M only from original observable magnitudes on reserved seeds."""

    provisional = Stage2MarginCalibration(3.0, 3.0, config.margin_percentile, 0)
    parameters = Stage2GeneratorParameters(3e-2, 0.5, 2.5, 0.0, "primary")
    seeds = tuple(
        stable_seed(config.calibration_master_seed, "margin-calibration", index)
        for index in range(STAGE2_PREFLIGHT_MARGIN_REPLICATES)
    )
    observable_outputs: List[ObservableCaseOutputs] = []
    for seed in seeds:
        generated = generate_stage2_population(parameters, seed, provisional, config)
        observable_outputs.extend(generated.observable_outputs)
    return (
        calibrate_stage2_margin_normalization(
            observable_outputs, config.tau_primary, config.tau_verifier
        ),
        seeds,
    )


def _stage2_risk_calibrations(
    normalization: Stage2MarginCalibration,
    config: Stage2Config,
) -> Tuple[Dict[Tuple[float, float], Stage2GeneratorParameters], Tuple[int, ...]]:
    """Calibrate every frozen risk/mechanism cell before control execution."""

    seeds = tuple(
        stable_seed(config.calibration_master_seed, "risk-calibration", index)
        for index in range(10)
    )
    calibrations: Dict[Tuple[float, float], Stage2GeneratorParameters] = {}
    for p_jde_target in config.p_jde_targets:
        for pi_h in config.pi_h_values:
            calibration = calibrate_stage2_risk_parameters(
                p_jde_target, pi_h, seeds, normalization, config
            )
            calibrations[(p_jde_target, pi_h)] = calibration.parameters
    return calibrations, seeds


def _stage2_control_g_values(
    results: Sequence[Mapping[str, object]],
    control_ids: Sequence[str],
    config: Stage2Config,
) -> Dict[str, List[dict]]:
    """Form one ratio-of-means G for every (class, epsilon, B) null cell."""

    expected = set(control_ids)
    grouped: Dict[Tuple[str, float, int], Dict[int, Tuple[float, float]]] = {}
    blockers: List[dict] = []

    def bound_or_block(
        control_id: str, row: Mapping[str, object], bound_role: str
    ) -> Optional[float]:
        try:
            value = effective_upper_bound(row)
            if bound_role == "UP denominator" and value <= 0.0:
                raise ValueError("zero denominator")
            return value
        except ValueError:
            blockers.append(
                {
                    "failure_class": "undefined_control_bound",
                    "bound_role": bound_role,
                    "control_id": control_id,
                    "replicate_id": row["replicate_id"],
                    "conceptual_arm": row["conceptual_arm"],
                    "epsilon_samp": row["epsilon_samp"],
                    "B": row["B"],
                    "validity_status": row["validity_status"],
                    "empty_confidence_set": row["empty_confidence_set"],
                    "monotonicity_status": row["monotonicity_status"],
                    "support_status": row["support_status"],
                    "warnings": row["warnings"],
                }
            )
            return None

    for result in results:
        rows = list(result["rows"])
        if not rows:
            raise InvalidDevelopmentRun("control work unit has no rows")
        control_id = str(rows[0]["control_id"])
        if control_id not in expected or any(str(row["control_id"]) != control_id for row in rows):
            raise InvalidDevelopmentRun("control work-unit identity is inconsistent")
        replicate_id = int(rows[0]["replicate_id"])
        for budget in config.budgets:
            budget_rows = [row for row in rows if row["B"] == budget]
            up_rows = [row for row in budget_rows if row["conceptual_arm"] == "UP"]
            sp_rows = [row for row in budget_rows if row["conceptual_arm"] == "SP"]
            if len(up_rows) != 1 or len(sp_rows) != len(config.epsilon_values):
                raise InvalidDevelopmentRun("control work unit lacks paired UP/SP trajectories")
            up_value = bound_or_block(control_id, up_rows[0], "UP denominator")
            for row in sp_rows:
                sp_value = bound_or_block(control_id, row, "SP numerator")
                if up_value is not None and sp_value is not None:
                    key = (control_id, float(row["epsilon_samp"]), budget)
                    grouped.setdefault(key, {})[replicate_id] = (up_value, sp_value)
    if blockers:
        representative = blockers[0]
        raise Stage2ControlBoundFailure(
            {
                **representative,
                "reason": "gamma_NC was not calibrated because required non-empty "
                "control bounds are genuinely undefined; no replicate was excluded "
                "or numerically substituted",
                "blocking_rows": blockers,
                "blocking_row_count": len(blockers),
            }
        )
    cells_by_class: Dict[str, List[dict]] = {control_id: [] for control_id in control_ids}
    for control_id in control_ids:
        for epsilon in config.epsilon_values:
            for budget in config.budgets:
                paired = grouped.get((control_id, epsilon, budget), {})
                replicate_ids = tuple(sorted(paired))
                if len(replicate_ids) != config.replicates:
                    raise InvalidDevelopmentRun(
                        f"control {control_id} cell has an incomplete population sample"
                    )
                up = tuple(paired[index][0] for index in replicate_ids)
                sp = tuple(paired[index][1] for index in replicate_ids)
                mean_up = math.fsum(up) / len(up)
                mean_sp = math.fsum(sp) / len(sp)
                cells_by_class[control_id].append(
                    {
                        "cell_id": f"{control_id}-e{epsilon:.12g}-b{budget}",
                        "control_id": control_id,
                        "epsilon_samp": epsilon,
                        "B": budget,
                        "replicate_ids": replicate_ids,
                        "effective_UP": up,
                        "effective_SP": sp,
                        "G_cell": 1.0 - mean_sp / mean_up,
                    }
                )
    return cells_by_class


def _execution_environment() -> dict:
    """Portable, non-sensitive execution context retained with development output."""

    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "os_cpu_count": os.cpu_count(),
    }


def _write_stage2_preflight_artifacts(
    output_directory: Path,
    manifest: Mapping[str, object],
    results: Sequence[Mapping[str, object]],
    report: Mapping[str, object],
) -> dict:
    """Write only compact control-preflight evidence, never evaluation traces."""

    _ensure_external_output(output_directory, _repository_root())
    output_directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "manifest": output_directory / "stage2_preflight_manifest.json",
        "records": output_directory / "stage2_preflight_control_records.jsonl",
        "report": output_directory / "stage2_preflight_report.json",
    }
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Stage 2 preflight output directory already contains an artifact")
    ordered_rows = [
        row
        for result in sorted(results, key=lambda item: str(item["unit_id"]))
        for row in result["rows"]
    ]
    record_bytes = b"".join(_canonical_json_bytes(row) for row in ordered_rows)
    manifest_bytes = _canonical_json_bytes(manifest)
    report_bytes = _canonical_json_bytes(report)
    paths["manifest"].write_bytes(manifest_bytes)
    paths["records"].write_bytes(record_bytes)
    paths["report"].write_bytes(report_bytes)
    return {
        f"{name}_path": str(path)
        for name, path in paths.items()
    } | {
        "manifest_size_bytes": len(manifest_bytes),
        "manifest_sha256": _sha256_bytes(manifest_bytes),
        "records_size_bytes": len(record_bytes),
        "records_sha256": _sha256_bytes(record_bytes),
        "records_count": len(ordered_rows),
        "report_size_bytes": len(report_bytes),
        "report_sha256": _sha256_bytes(report_bytes),
    }


def _stage2_preflight_manifest(
    config: Stage2Config,
    provenance: Mapping[str, object],
    plan: Mapping[str, object],
    normalization: Stage2MarginCalibration,
    margin_seeds: Sequence[int],
    risk_seeds: Sequence[int],
    calibrations: Mapping[Tuple[float, float], Stage2GeneratorParameters],
    workers: int,
    gamma_nc: Optional[Mapping[str, object]],
    failure_record: Optional[Mapping[str, object]] = None,
) -> dict:
    """Build a complete preflight manifest for either success or a controlled stop."""

    return {
        "schema_version": "ppi-stage2-control-preflight-v3",
        "notice": DEVELOPMENT_ONLY_NOTICE,
        "code_version": STAGE2_CODE_VERSION,
        "git_provenance": dict(provenance),
        "environment": _execution_environment(),
        "plan": dict(plan),
        "margin_normalization": asdict(normalization),
        "margin_calibration_seeds": list(margin_seeds),
        "risk_calibration_seeds": list(risk_seeds),
        "risk_calibrations": [
            {"p_jde_target": key[0], "pi_H": key[1], **asdict(calibrations[key])}
            for key in sorted(calibrations)
        ],
        "gamma_NC": None if gamma_nc is None else gamma_nc["gamma_NC"],
        "negative_control_calibration": None if gamma_nc is None else dict(gamma_nc),
        "gamma_nc_status": "not_calibrated" if gamma_nc is None else "calibrated",
        "gamma_nc_not_calibrated_reason": (
            None
            if failure_record is None
            else failure_record["reason"]
        ),
        "failure": None if failure_record is None else dict(failure_record),
        "workers": workers,
        "evaluation_or_bootstrap_work_executed": False,
    }


def _stage2_preflight_report(
    phase_runtimes: Mapping[str, Optional[float]],
    work_unit_counts: Mapping[str, int],
    gamma_nc: Optional[Mapping[str, object]],
    failure_record: Optional[Mapping[str, object]] = None,
) -> dict:
    """Report completed work faithfully, including a non-imputed G failure."""

    return {
        "schema_version": "ppi-stage2-control-preflight-report-v3",
        "phase_runtimes_seconds": dict(phase_runtimes),
        "work_unit_counts": dict(work_unit_counts),
        "gamma_NC": None if gamma_nc is None else gamma_nc["gamma_NC"],
        "negative_control_calibration": None if gamma_nc is None else dict(gamma_nc),
        "gamma_nc_status": "not_calibrated" if gamma_nc is None else "calibrated",
        "gamma_nc_not_calibrated_reason": (
            None
            if failure_record is None
            else failure_record["reason"]
        ),
        "failure": None if failure_record is None else dict(failure_record),
        "evaluation_or_bootstrap_work_executed": False,
    }


def run_stage2_preflight(output_directory: Path, workers: int) -> dict:
    """Run only the frozen Stage 2 calibration and mandatory control preflight.

    The entrypoint intentionally has no evaluation or bootstrap switch.  Its
    work units use calibration/negative-control namespaces only, and it writes
    an execution manifest before returning a compact, external receipt.
    """

    config = Stage2Config()
    config.validate()
    if workers <= 0:
        raise ValueError("Stage 2 preflight worker count must be positive")
    _ensure_external_output(output_directory, _repository_root())
    provenance = inspect_git_provenance(_repository_root())
    if not provenance.get("head"):
        raise InvalidDevelopmentRun(
            "Stage 2 preflight requires resolvable Git HEAD provenance"
        )
    plan = stage2_preflight_plan(config)
    total_started = time.perf_counter()
    margin_started = time.perf_counter()
    normalization, margin_seeds = _stage2_margin_calibration(config)
    margin_seconds = time.perf_counter() - margin_started
    risk_started = time.perf_counter()
    calibrations, risk_seeds = _stage2_risk_calibrations(normalization, config)
    risk_seconds = time.perf_counter() - risk_started
    base_parameters = calibrations[STAGE2_PREFLIGHT_CONTROL_ANCHOR]
    negative_started = time.perf_counter()
    negative_units = build_stage2_control_work_units(
        base_parameters,
        normalization,
        STAGE2_PREFLIGHT_NEGATIVE_CONTROLS,
        STAGE2_PREFLIGHT_NEGATIVE_CONTROL_REPLICATES,
        "negative_control_calibration",
        config,
    )
    negative_results = execute_stage2_work_units(negative_units, workers)
    try:
        gamma_nc = empirical_gamma_nc(
            _stage2_control_g_values(
                negative_results, STAGE2_PREFLIGHT_NEGATIVE_CONTROLS, config
            ),
            config,
        )
    except Stage2ControlBoundFailure as failure:
        negative_seconds = time.perf_counter() - negative_started
        phase_runtimes = {
            "margin_calibration": margin_seconds,
            "risk_calibration": risk_seconds,
            "negative_control_calibration": negative_seconds,
            "additional_control_preflight": None,
            "total": time.perf_counter() - total_started,
        }
        work_unit_counts = {
            "negative_control_calibration": len(negative_units),
            "additional_control_preflight": 0,
        }
        manifest = _stage2_preflight_manifest(
            config,
            provenance,
            plan,
            normalization,
            margin_seeds,
            risk_seeds,
            calibrations,
            workers,
            None,
            failure.failure_record,
        )
        report = _stage2_preflight_report(
            phase_runtimes, work_unit_counts, None, failure.failure_record
        )
        artifacts = _write_stage2_preflight_artifacts(
            output_directory, manifest, negative_results, report
        )
        raise Stage2PreflightFailureReceipt(
            failure.failure_record, artifacts
        ) from failure
    negative_seconds = time.perf_counter() - negative_started
    additional_started = time.perf_counter()
    additional_units = build_stage2_control_work_units(
        base_parameters,
        normalization,
        STAGE2_PREFLIGHT_ADDITIONAL_CONTROLS,
        STAGE2_PREFLIGHT_ADDITIONAL_CONTROL_REPLICATES,
        "negative_control_preflight",
        config,
    )
    additional_results = execute_stage2_work_units(additional_units, workers)
    additional_seconds = time.perf_counter() - additional_started
    all_results = [*negative_results, *additional_results]
    if not all(
        bool(result["identity_sentinel_passed"])
        and bool(result["structural_invariance_passed"])
        for result in all_results
    ):
        raise InvalidDevelopmentRun("Stage 2 mandatory structural control failed")
    phase_runtimes = {
        "margin_calibration": margin_seconds,
        "risk_calibration": risk_seconds,
        "negative_control_calibration": negative_seconds,
        "additional_control_preflight": additional_seconds,
        "total": time.perf_counter() - total_started,
    }
    work_unit_counts = {
        "negative_control_calibration": len(negative_units),
        "additional_control_preflight": len(additional_units),
    }
    manifest = _stage2_preflight_manifest(
        config,
        provenance,
        plan,
        normalization,
        margin_seeds,
        risk_seeds,
        calibrations,
        workers,
        gamma_nc,
    )
    report = _stage2_preflight_report(
        phase_runtimes, work_unit_counts, gamma_nc
    )
    artifacts = _write_stage2_preflight_artifacts(
        output_directory, manifest, all_results, report
    )
    return {
        "mode": "stage2_preflight",
        "development_only": True,
        "git_head": provenance["head"],
        "gamma_NC": gamma_nc["gamma_NC"],
        "negative_control_calibration": gamma_nc,
        "phase_runtimes_seconds": report["phase_runtimes_seconds"],
        "work_unit_counts": report["work_unit_counts"],
        "evaluation_or_bootstrap_work_executed": False,
        "artifacts": artifacts,
    }


def write_stage2_execution_artifacts(
    output_directory: Path,
    results: Sequence[Mapping[str, object]],
    manifest: Mapping[str, object],
    config: Stage2Config,
) -> dict:
    """Write compact bulk rows and exactly two predeclared forensic traces."""

    _ensure_external_output(output_directory, _repository_root())
    output_directory.mkdir(parents=True, exist_ok=True)
    ordered_results = sorted(results, key=lambda result: str(result["unit_id"]))
    compact_path = output_directory / "stage2_compact_results.jsonl"
    compact_hash = hashlib.sha256()
    compact_size = 0
    compact_record_count = 0
    replay_populations = []
    replay_audits = []
    with compact_path.open("wb") as stream:
        for result in ordered_results:
            for row in result["rows"]:
                encoded = _canonical_json_bytes(row)
                stream.write(encoded)
                compact_hash.update(encoded)
                compact_size += len(encoded)
                compact_record_count += 1
            population = result.get("replay_population")
            if population is not None:
                replay_populations.append(population)
            replay_audits.extend(result.get("replay_audits", ()))
    if len(replay_audits) != 2 or len(replay_populations) != 1:
        raise InvalidDevelopmentRun(
            "Stage 2 evidence selection must yield one population and two paired traces"
        )
    replay_document = {
        "schema_version": "ppi-stage2-replay-v1",
        "notice": DEVELOPMENT_ONLY_NOTICE,
        "code_version": STAGE2_CODE_VERSION,
        "configuration": _stage2_development_configuration(config),
        "lambda_grid_digest": _lambda_grid_digest(config.lambda_grid),
        "transformation_bank": {
            "bank_id": frozen_transformation_bank().bank_id,
            "digest": frozen_transformation_bank().digest,
            "k4_indices": list(frozen_transformation_bank().k4_indices),
            "transformation_ids": [
                row.transformation_id
                for row in frozen_transformation_bank().transformations
            ],
        },
        "trace_selection_rule": manifest["replay_selection_rule"],
        "populations": replay_populations,
        "audits": replay_audits,
    }
    replay_bytes = _canonical_json_bytes(replay_document)
    replay_path = output_directory / "stage2_selected_replay_traces.json"
    replay_path.write_bytes(replay_bytes)
    replay_result = replay_stage1_artifact_document(replay_document)
    if replay_result["failure_count"]:
        raise InvalidDevelopmentRun("selected Stage 2 trace replay failed")
    manifest_path = output_directory / "stage2_manifest.json"
    manifest_bytes = _canonical_json_bytes(manifest)
    manifest_path.write_bytes(manifest_bytes)
    return {
        "compact_path": str(compact_path),
        "compact_record_count": compact_record_count,
        "compact_size_bytes": compact_size,
        "compact_sha256": compact_hash.hexdigest(),
        "replay_path": str(replay_path),
        "replay_trace_count": len(replay_audits),
        "replay_size_bytes": len(replay_bytes),
        "replay_sha256": _sha256_bytes(replay_bytes),
        "replay_result": replay_result,
        "manifest_path": str(manifest_path),
        "manifest_size_bytes": len(manifest_bytes),
        "manifest_sha256": _sha256_bytes(manifest_bytes),
    }


def run_stage2_primary_map(output_directory: Path, workers: int) -> dict:
    """Execute the frozen development primary map through the supported CLI.

    This is deliberately not called by tests or preflight.  It is the sole
    public path that consumes the Stage 2 evaluation namespace.
    """

    config = Stage2Config()
    config.validate()
    if workers <= 0:
        raise ValueError("Stage 2 primary-map worker count must be positive")
    _ensure_external_output(output_directory, _repository_root())
    provenance = inspect_git_provenance(_repository_root())
    if not provenance.get("head"):
        raise InvalidDevelopmentRun("Stage 2 primary map requires resolvable Git provenance")

    started = time.perf_counter()
    normalization, _ = _stage2_margin_calibration(config)
    calibrations, _ = _stage2_risk_calibrations(normalization, config)
    calibration_seconds = time.perf_counter() - started

    units = build_stage2_primary_work_units(calibrations, normalization, config)
    evaluation_started = time.perf_counter()
    results = execute_stage2_work_units(units, workers)
    evaluation_seconds = time.perf_counter() - evaluation_started
    records = [row for result in results for row in result["rows"]]
    summaries = summarize_stage2_cells(records, config)

    bootstrap_started = time.perf_counter()
    bootstrap = bootstrap_stage2_primary_statistics(records, summaries, config)
    bootstrap_seconds = time.perf_counter() - bootstrap_started
    classification = classify_stage2_development(
        summaries,
        config.gamma_nc,
        bootstrap["Delta_bar_minus"],
        bootstrap["pooled_empty_cluster_bootstrap_95_lower"],
        config,
    )
    manifest = stage2_primary_map_manifest(
        config, normalization, calibrations, workers, provenance
    )
    report = {
        "schema_version": "ppi-stage2-primary-map-report-v1",
        "development_only": True,
        "classification": classification,
        "gamma_NC": config.gamma_nc,
        "tau_NC": config.tau_nc,
        "cell_count": len(summaries),
        "scientific_stratum_count": 48,
        "structural_representation_complete": stage2_structural_representation_complete(
            summaries, config
        ),
        "bootstrap": bootstrap,
        "phase_runtimes_seconds": {
            "calibration": calibration_seconds,
            "evaluation": evaluation_seconds,
            "primary_bootstrap": bootstrap_seconds,
            "total_before_artifact_write": time.perf_counter() - started,
        },
        "confirmatory": False,
    }
    artifacts = write_stage2_execution_artifacts(
        output_directory, results, manifest, config
    )
    map_path = output_directory / "stage2_feasibility_map.json"
    report_path = output_directory / "stage2_primary_map_report.json"
    if map_path.exists() or report_path.exists():
        raise FileExistsError("Stage 2 primary-map summary artifact already exists")
    map_bytes = _canonical_json_bytes({"cells": summaries})
    report_bytes = _canonical_json_bytes(report)
    map_path.write_bytes(map_bytes)
    report_path.write_bytes(report_bytes)
    artifacts.update(
        {
            "feasibility_map_path": str(map_path),
            "feasibility_map_size_bytes": len(map_bytes),
            "feasibility_map_sha256": _sha256_bytes(map_bytes),
            "report_path": str(report_path),
            "report_size_bytes": len(report_bytes),
            "report_sha256": _sha256_bytes(report_bytes),
        }
    )
    return {
        "mode": "stage2_primary_map",
        "development_only": True,
        "classification": classification,
        "cell_count": len(summaries),
        "population_count": len(units),
        "gamma_NC": config.gamma_nc,
        "bootstrap": bootstrap,
        "artifacts": artifacts,
    }


def _deserialize_stage1_population(record: Mapping[str, object]) -> Tuple[List[str], Dict[str, Dict[str, float]], Dict[str, int]]:
    items = record.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("Stage 1 replay population is missing items")
    ids: List[str] = []
    channels: Dict[str, Dict[str, float]] = {}
    outcomes: Dict[str, int] = {}
    rows = []
    for item in items:
        if not isinstance(item, Mapping):
            raise ValueError("Stage 1 population item is malformed")
        item_id = str(item["item_id"])
        if item_id in outcomes:
            raise ValueError("Stage 1 population has duplicate item IDs")
        score_row = item.get("observable_scores")
        if not isinstance(score_row, Mapping):
            raise ValueError("Stage 1 population lacks named observable scores")
        ordered_scores = tuple(
            (str(key), float(score_row[key])) for key in sorted(score_row)
        )
        outcome = int(item["hidden_outcome"])
        if outcome not in (0, 1):
            raise ValueError("Stage 1 population outcome is not binary")
        ids.append(item_id)
        outcomes[item_id] = outcome
        for key, value in ordered_scores:
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError("Stage 1 authoritative score is invalid")
            channels.setdefault(key, {})[item_id] = value
        rows.append((item_id, tuple((key, value.hex()) for key, value in ordered_scores), outcome))
    if digest_rows(rows) != record.get("population_digest"):
        raise ValueError("Stage 1 population digest mismatch")
    for key, expected in record.get("observable_score_digests", {}).items():
        if key not in channels or score_channel_digest(channels[key]) != expected:
            raise ValueError(f"Stage 1 observable score digest mismatch: {key}")
    return ids, channels, outcomes


def _validate_stage1_observable_outputs(record: Mapping[str, object], channels: Mapping[str, Mapping[str, float]]) -> None:
    raw_outputs = record.get("observable_outputs")
    if not isinstance(raw_outputs, list):
        raise ValueError("Stage 1 replay population lacks observable outputs")
    outputs = tuple(ObservableCaseOutputs(**row) for row in raw_outputs)
    if observable_outputs_digest(outputs) != record.get("observable_outputs_digest"):
        raise ValueError("Stage 1 observable-output digest mismatch")
    bank = frozen_transformation_bank()
    manifest = record.get("scenario_manifest")
    if not isinstance(manifest, Mapping):
        raise ValueError("Stage 1 replay population lacks scenario manifest")
    confidence = manifest.get("confidence_constants")
    if not isinstance(confidence, Mapping):
        raise ValueError("Stage 1 manifest lacks confidence constants")
    expected_items = []
    for output in outputs:
        expected_k8 = ppi_from_observable_outputs(output, bank, 8).score
        expected_k4 = ppi_from_observable_outputs(output, bank, 4).score
        expected_margin = compute_confidence_margin(
            output.original_primary_magnitude,
            output.original_verifier_magnitude,
            float(confidence["tau_primary"]),
            float(confidence["tau_verifier"]),
            float(confidence["normalization_primary"]),
            float(confidence["normalization_verifier"]),
        )
        expected_items.append(
            ObservableScoreItem(
                output.item_id,
                (("ppi_k8", expected_k8), ("ppi_k4", expected_k4), ("confidence_margin", expected_margin)),
            )
        )
    if record.get("scenario_id") == "permuted_ppi":
        expected_items = list(permute_ppi_within_observable_strata(expected_items, outputs))
    for item in expected_items:
        expected_scores = item.scores()
        if channels["ppi_k8"][item.item_id].hex() != expected_scores["ppi_k8"].hex():
            raise ValueError("Stage 1 PPI K=8 channel/output inconsistency")
        if channels["ppi_k4"][item.item_id].hex() != expected_scores["ppi_k4"].hex():
            raise ValueError("Stage 1 PPI K=4 channel/output inconsistency")
        if channels["confidence_margin"][item.item_id].hex() != expected_scores["confidence_margin"].hex():
            raise ValueError("Stage 1 confidence-margin channel/output inconsistency")


def _validated_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _validated_lambda_grid(value: object, field: str) -> Tuple[float, ...]:
    # Serialized JSON uses a list; the in-memory self-replay path retains the
    # frozen configuration tuple.  Both preserve ordered numeric semantics.
    if not isinstance(value, (list, tuple)) or not value:
        raise ValueError(f"{field} must be a non-empty ordered sequence")
    if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value):
        raise ValueError(f"{field} contains a malformed lambda")
    grid = tuple(float(item) for item in value)
    if any(not math.isfinite(item) or not 0.0 < item <= 0.50 for item in grid):
        raise ValueError(f"{field} contains an inadmissible lambda")
    if len(set(grid)) != len(grid):
        raise ValueError(f"{field} contains duplicate lambdas")
    return grid


def replay_stage1_artifact_document(document: Mapping[str, object]) -> dict:
    """Replay selected traces only from the serialized Stage 1 artifact."""

    populations = document.get("populations")
    audits = document.get("audits")
    if not isinstance(populations, list) or not isinstance(audits, list):
        raise ValueError("Stage 1 artifact lacks populations or audits")
    try:
        configuration = document.get("configuration")
        if not isinstance(configuration, Mapping):
            raise ValueError("Stage 1 artifact lacks configuration")
        configuration_grid = _validated_lambda_grid(
            configuration.get("lambda_grid"), "configuration lambda_grid"
        )
        configuration_digest = _validated_sha256(
            document.get("lambda_grid_digest"), "configuration lambda_grid_digest"
        )
        if configuration_digest != _lambda_grid_digest(configuration_grid):
            raise ValueError("configuration lambda-grid digest mismatch")
        bank_record = document.get("transformation_bank")
        if not isinstance(bank_record, Mapping):
            raise ValueError("Stage 1 artifact lacks transformation-bank record")
        bank_digest = _validated_sha256(
            bank_record.get("digest"), "transformation-bank digest"
        )
        if bank_digest != frozen_transformation_bank().digest:
            raise ValueError("transformation-bank digest does not match the frozen bank")
    except (TypeError, ValueError) as error:
        return {
            "checked_audits": len(audits),
            "checked_draws": 0,
            "failure_count": 1,
            "failures": [{"audit_id": None, "reason": str(error)}],
        }
    population_map = {}
    failures = []
    for population in populations:
        try:
            if not isinstance(population, Mapping):
                raise ValueError("Stage 1 population record is malformed")
            key = (population.get("scenario_id"), population.get("replicate_id"))
            if key in population_map:
                raise ValueError("duplicate Stage 1 replay population")
            ids, channels, outcomes = _deserialize_stage1_population(population)
            _validate_stage1_observable_outputs(population, channels)
            population_map[key] = (population, ids, channels, outcomes)
        except (KeyError, TypeError, ValueError) as error:
            failures.append(
                {
                    "audit_id": None,
                    "reason": f"authoritative population rejected: {error}",
                }
            )
    checked_draws = 0
    for audit in audits:
        audit_id = audit.get("audit_id") if isinstance(audit, Mapping) else None
        try:
            if not isinstance(audit, Mapping):
                raise ValueError("malformed Stage 1 audit")
            key = (audit.get("scenario_id"), audit.get("replicate_id"))
            if key not in population_map:
                raise ValueError("Stage 1 audit lacks authoritative population")
            population, remaining, channels, outcomes = population_map[key]
            remaining = list(remaining)
            selection_order = list(audit["selection_order"])
            trace = list(audit["trace"])
            if len(selection_order) != len(trace):
                raise ValueError("Stage 1 selection-order length mismatch")
            audit_grid = _validated_lambda_grid(
                audit.get("lambda_grid"), "audit lambda_grid"
            )
            audit_digest = _validated_sha256(
                audit.get("lambda_grid_digest"), "audit lambda_grid_digest"
            )
            if audit_grid != configuration_grid:
                raise ValueError("audit lambda grid differs from configuration grid")
            if audit_digest != _lambda_grid_digest(audit_grid):
                raise ValueError("audit lambda-grid digest mismatch")
            if audit_digest != configuration_digest:
                raise ValueError("audit lambda-grid digest differs from configuration digest")
            reconstructed_steps: List[WealthStep] = []
            observed_complements = 0
            for position, row in enumerate(trace, start=1):
                pre_reveal = row["pre_reveal"]
                replay = replay_named_pre_reveal_draw(pre_reveal, channels, remaining)
                checked_draws += 1
                if not replay.passed:
                    raise ValueError(f"step {position}: {replay.reason}")
                selected = selection_order[position - 1]
                if replay.reconstructed_item_id != selected:
                    raise ValueError(f"step {position}: selection history mismatch")
                outcome = outcomes[selected]
                if int(row["revealed_outcome"]) != outcome:
                    raise ValueError(f"step {position}: revealed outcome mismatch")
                probabilities = {
                    item_id: float(value)
                    for item_id, value in zip(remaining, pre_reveal["q_vector"])
                }
                cv_key = pre_reveal.get("control_variate_score_key")
                expected_cv = math.fsum(
                    probabilities[item_id] * (0.0 if cv_key is None else channels[cv_key][item_id])
                    for item_id in remaining
                )
                beta = float(row["beta"])
                probability = probabilities[selected]
                complement = 1 - outcome
                u_value = 0.0 if cv_key is None else channels[cv_key][selected] - expected_cv
                z_value = complement / (len(population["items"]) * probability)
                constant = z_value + beta * u_value + observed_complements / len(population["items"])
                support_minimum = None
                support_count = 0
                for item_id in remaining:
                    support_u = 0.0 if cv_key is None else channels[cv_key][item_id] - expected_cv
                    for possible_outcome in (0, 1):
                        candidate = SupportTerm(
                            item_id,
                            possible_outcome,
                            0.0 if cv_key is None else channels[cv_key][item_id],
                            probabilities[item_id],
                            support_u,
                            beta,
                            (1 - possible_outcome) / (len(population["items"]) * probabilities[item_id])
                            + beta * support_u
                            + observed_complements / len(population["items"]),
                        )
                        support_count += 1
                        if support_minimum is None or candidate.constant_term < support_minimum.constant_term:
                            support_minimum = candidate
                if not math.isclose(constant, float(row["constant_term"]), rel_tol=1e-12, abs_tol=1e-12):
                    raise ValueError(f"step {position}: mixture wealth input mismatch")
                observed_complements += complement
                reconstructed_steps.append(
                    WealthStep(constant, observed_complements / len(population["items"]), (), support_minimum, support_count)
                )
                remaining.remove(selected)
            expected = audit.get("mixture_result")
            if not isinstance(expected, Mapping):
                raise ValueError("selected replay audit lacks a stored mixture result")
            replayed_status = "valid"
            replayed_upper = None
            try:
                evaluation = evaluate_running_mixture_bound(
                    reconstructed_steps,
                    audit_grid,
                    float(configuration["alpha_cs"]),
                    float(configuration["inversion_tolerance"]),
                    float(configuration["monotonicity_tolerance"]),
                )
                replayed_upper = evaluation.upper_error_bound
            except EmptyConfidenceSet:
                replayed_status = "empty_confidence_set"
            except SupportAdmissibilityFailure:
                replayed_status = "invalid_support_admissibility"
            except MonotonicityFailure:
                replayed_status = "invalid_monotonicity"
            except ControlledNumericalFailure:
                replayed_status = "invalid_numerical"
            if replayed_status != expected.get("validity_status"):
                raise ValueError(
                    "Stage 1 replayed mixture status mismatch: "
                    f"{replayed_status} != {expected.get('validity_status')}"
                )
            if replayed_status == "valid" and not math.isclose(
                replayed_upper,
                float(expected["final_upper_bound"]),
                rel_tol=1e-12,
                abs_tol=1e-12,
            ):
                raise ValueError("Stage 1 replayed mixture bound mismatch")
        except (KeyError, TypeError, ValueError, ControlledNumericalFailure) as error:
            failures.append({"audit_id": audit_id, "reason": str(error)})
    return {
        "checked_audits": len(audits),
        "checked_draws": checked_draws,
        "failure_count": len(failures),
        "failures": failures,
    }


def _lambda_grid_digest(values: Sequence[float]) -> str:
    return _sha256_bytes(_canonical_json_bytes([float(value).hex() for value in values]))


def _manifest_digest(config: Stage1Config, bank_digest: str) -> str:
    payload = {
        "configuration": asdict(config),
        "transformation_bank_digest": bank_digest,
        "purpose": "development-only Stage 1 plumbing",
    }
    return _sha256_bytes(_canonical_json_bytes(payload))


def retain_stage1_trace(
    replicate: int, validity_status: str, q_replay_passed: bool
) -> bool:
    """Predeclared trace rule; never consults a contrast or bound direction."""

    return replicate == 0 or validity_status != "valid" or not q_replay_passed


def run_ppi_stage1(
    output_directory: Optional[Path] = None,
    config: Optional[Stage1Config] = None,
) -> dict:
    """Run the bounded Stage 1 vertical slice; never a scientific evaluation."""

    config = config or Stage1Config()
    config.validate()
    repository_root = _repository_root()
    output_directory = output_directory or Path(
        tempfile.mkdtemp(prefix="llm-worldmodels-ppi-stage1-dev-")
    )
    _ensure_external_output(output_directory, repository_root)
    output_directory.mkdir(parents=True, exist_ok=True)
    projected_trace_bytes = (
        len(config.scenario_ids)
        * len(config.ks)
        * 5
        * config.budget
        * config.population_size
        * 55
    )
    if projected_trace_bytes > config.trace_limit_bytes:
        raise InvalidDevelopmentRun(
            f"projected replay trace exceeds configured limit: {projected_trace_bytes}"
        )
    started = time.perf_counter()
    bank = frozen_transformation_bank()
    manifest_digest = _manifest_digest(config, bank.digest)
    lambda_digest = _lambda_grid_digest(config.lambda_grid)
    provenance = inspect_git_provenance(repository_root)
    compact_records: List[dict] = []
    replay_populations: Dict[Tuple[str, int], dict] = {}
    replay_audits: List[dict] = []
    scenario_counts: Dict[str, int] = {}
    q_replay_failures = 0
    total_draws = 0
    all_q_positive = True
    all_common_lambda = True
    constant_uniform_passed = True
    acceptance_by_scenario: Dict[str, List[Mapping[str, object]]] = {}

    for scenario_id in config.scenario_ids:
        scenario_counts[scenario_id] = 0
        for replicate in range(config.replicates):
            population_seed = stable_seed(
                config.master_seed, scenario_id, replicate, "stage1-population"
            )
            generated = generate_stage1_population(
                scenario_id, config.population_size, population_seed, config, bank
            )
            acceptance_by_scenario.setdefault(scenario_id, []).append(
                generated.collider_diagnostic
            )
            population_record = _stage1_population_record(
                generated, replicate, population_seed
            )
            population = generated.population
            for k in config.ks:
                for arm in stage1_arms(k, config.epsilon_samp):
                    audit_seed = stable_seed(
                        config.master_seed,
                        scenario_id,
                        replicate,
                        k,
                        arm.arm_id,
                        "stage1-audit",
                    )
                    audit = simulate_named_audit(
                        population, arm, config.budget, config.ridge, audit_seed
                    )
                    mixture_result = _stage1_mixture_result(audit, population, config)
                    audit_id = f"{scenario_id}:{replicate}:k{k}:{arm.arm_id}"
                    retain_trace = retain_stage1_trace(
                        replicate,
                        mixture_result["validity_status"],
                        audit["q_replay_passed"],
                    )
                    trace_reference = audit_id if retain_trace else None
                    if retain_trace:
                        replay_populations[(scenario_id, replicate)] = population_record
                        replay_audits.append(
                            {
                                "audit_id": audit_id,
                                "scenario_id": scenario_id,
                                "replicate_id": replicate,
                                "k": k,
                                "arm": asdict(arm),
                                "rng_seed": audit_seed,
                                "selection_order": audit["selection_order"],
                                "trace": audit["trace"],
                                "lambda_grid": list(config.lambda_grid),
                                "lambda_grid_digest": lambda_digest,
                                "mixture_result": mixture_result,
                            }
                        )
                    score_channels = population.all_observable_scores()
                    component_evaluations = 2 * population.size * (1 + k)
                    record = {
                        "schema_version": config.schema_version,
                        "code_version": STAGE1_CODE_VERSION,
                        "code_head": provenance["head"],
                        "development_manifest_digest": manifest_digest,
                        "scenario_id": scenario_id,
                        "replicate_id": replicate,
                        "N": population.size,
                        "B": config.budget,
                        "K": k,
                        "epsilon_samp": arm.epsilon_samp,
                        "lambda_grid_digest": lambda_digest,
                        "lambda_grid": list(config.lambda_grid),
                        "alpha_CS": config.alpha_cs,
                        "tau_primary": config.tau_primary,
                        "tau_verifier": config.tau_verifier,
                        "maximum_generated_candidates": config.maximum_generated_candidates,
                        "arm_id": arm.arm_id,
                        "conceptual_arm": arm.conceptual_arm,
                        "sampling_policy": arm.sampling_policy,
                        "sampling_score_key": arm.sampling_score_key,
                        "control_variate_score_key": arm.control_variate_score_key,
                        "transformation_bank_digest": bank.digest,
                        "population_digest": population_record["population_digest"],
                        "observable_score_digests": {
                            key: score_channel_digest(score_channels[key])
                            for key in sorted(score_channels)
                        },
                        "true_evaluator_prevalence": population.true_prevalence,
                        "final_upper_bound": mixture_result["final_upper_bound"],
                        "coverage_indicator_diagnostic_only": mixture_result["coverage_indicator"],
                        "validity_status": mixture_result["validity_status"],
                        "empty_confidence_set": mixture_result["empty_confidence_set"],
                        "zero_event": audit["errors_observed"] == 0,
                        "discovered_error_count_diagnostic_only": audit["errors_observed"],
                        "minimum_q": audit["min_q"],
                        "maximum_importance_weight": audit["max_importance_weight"],
                        "component_evaluation_count": component_evaluations,
                        "inference_cost": {
                            "original_component_evaluations": 2 * population.size,
                            "incremental_transformed_component_evaluations": 2 * k * population.size,
                            "oracle_observations": config.budget,
                            "fixed_oracle_budget_does_not_fix_inference_cost": True,
                        },
                        "collider_diagnostic": generated.collider_diagnostic,
                        "agreement_selection": generated.scenario_manifest[
                            "agreement_selection"
                        ],
                        "selected_replay_trace_reference": trace_reference,
                        "q_replay_passed": audit["q_replay_passed"],
                        "mixture_monotonicity_status": mixture_result["monotonicity_status"],
                        "warnings": mixture_result["warnings"],
                    }
                    compact_records.append(record)
                    scenario_counts[scenario_id] += 1
                    total_draws += audit["observations"]
                    q_replay_failures += int(not audit["q_replay_passed"])
                    all_q_positive = all_q_positive and audit["min_q"] > 0.0
                    all_common_lambda = all_common_lambda and record["lambda_grid_digest"] == lambda_digest
                    if scenario_id == "constant_ppi" and arm.conceptual_arm == "SP":
                        uniform_q = 1.0 / population.size
                        first_q = audit["trace"][0]["pre_reveal"]["q_vector"]
                        constant_uniform_passed = constant_uniform_passed and all(
                            value.hex() == uniform_q.hex() for value in first_q
                        )

    compact_path = output_directory / "compact_results.jsonl"
    compact_bytes = b"".join(_canonical_json_bytes(row) for row in compact_records)
    if len(compact_bytes) > config.compact_limit_bytes:
        raise InvalidDevelopmentRun("compact Stage 1 output exceeds configured limit")
    compact_path.write_bytes(compact_bytes)
    replay_document = {
        "schema_version": "ppi-stage1-replay-v2",
        "notice": DEVELOPMENT_ONLY_NOTICE,
        "code_version": STAGE1_CODE_VERSION,
        "git_provenance": provenance,
        "configuration": asdict(config),
        "lambda_grid_digest": lambda_digest,
        "development_manifest_digest": manifest_digest,
        "transformation_bank": {
            "bank_id": bank.bank_id,
            "digest": bank.digest,
            "k4_indices": list(bank.k4_indices),
            "transformation_ids": [row.transformation_id for row in bank.transformations],
        },
        "trace_selection_rule": "replicate 0 for every scenario x arm x K; plus every invalid run and replay failure",
        "populations": [replay_populations[key] for key in sorted(replay_populations)],
        "audits": replay_audits,
    }
    replay_path = output_directory / "selected_replay_traces.json"
    replay_bytes = _canonical_json_bytes(replay_document)
    if len(replay_bytes) > config.trace_limit_bytes:
        raise InvalidDevelopmentRun("Stage 1 replay traces exceed configured limit")
    replay_path.write_bytes(replay_bytes)
    replay_result = replay_stage1_artifact_document(replay_document)
    if replay_result["failure_count"]:
        raise InvalidDevelopmentRun("selected Stage 1 trace replay failed")
    report = {
        "schema_version": "ppi-stage1-summary-v2",
        "notice": DEVELOPMENT_ONLY_NOTICE,
        "scientific_classification_performed": False,
        "configuration": asdict(config),
        "development_manifest_digest": manifest_digest,
        "scenario_run_counts": scenario_counts,
        "agreement_selection_summary": {
            scenario_id: {
                "selection_neutral_null": scenario_id == "no_shared_fragile_mechanism",
                "acceptance_rates": [
                    row["acceptance_rate"] for row in diagnostics
                ],
                "generated_candidate_counts": [
                    row["generated_candidate_count"] for row in diagnostics
                ],
                "accepted_candidate_counts": [
                    row["accepted_candidate_count"] for row in diagnostics
                ],
            }
            for scenario_id, diagnostics in sorted(acceptance_by_scenario.items())
        },
        "scenario_count": len(scenario_counts),
        "replicate_count_per_scenario": config.replicates,
        "arm_configurations_per_replicate": len(config.ks) * 5,
        "audit_count": len(compact_records),
        "draw_count": total_draws,
        "replay_trace_count": len(replay_audits),
        "q_replay_failures": q_replay_failures,
        "all_q_positive": all_q_positive,
        "constant_score_reduced_to_uniform": constant_uniform_passed,
        "common_lambda_grid_everywhere": all_common_lambda,
        "invalid_status_count": sum(row["validity_status"].startswith("invalid") for row in compact_records),
        "empty_confidence_set_count": sum(row["empty_confidence_set"] for row in compact_records),
        "zero_event_count": sum(row["zero_event"] for row in compact_records),
        "valid_status_count": sum(row["validity_status"] == "valid" for row in compact_records),
        "compact_sha256": _sha256_bytes(compact_bytes),
        "replay_sha256": _sha256_bytes(replay_bytes),
        "replay_result": replay_result,
    }
    summary_path = output_directory / "stage1_summary.json"
    summary_bytes = _canonical_json_bytes(report)
    summary_path.write_bytes(summary_bytes)
    runtime_seconds = time.perf_counter() - started
    return {
        "output_directory": str(output_directory),
        "compact_results": str(compact_path),
        "selected_replay_traces": str(replay_path),
        "summary": str(summary_path),
        "runtime_seconds": runtime_seconds,
        "compact_size_bytes": len(compact_bytes),
        "replay_size_bytes": len(replay_bytes),
        "summary_size_bytes": len(summary_bytes),
        "compact_sha256": report["compact_sha256"],
        "replay_sha256": report["replay_sha256"],
        "summary_sha256": _sha256_bytes(summary_bytes),
        **{key: report[key] for key in (
            "scenario_count", "replicate_count_per_scenario", "audit_count", "draw_count",
            "replay_trace_count", "q_replay_failures", "all_q_positive",
            "constant_score_reduced_to_uniform", "common_lambda_grid_everywhere",
            "invalid_status_count", "empty_confidence_set_count", "zero_event_count",
            "valid_status_count",
        )},
    }


def run_smoke(
    output_directory: Optional[Path] = None,
    config: Optional[SmokeConfig] = None,
) -> dict:
    config = config or SmokeConfig()
    config.validate()
    repository_root = _repository_root()
    output_directory = output_directory or default_output_directory()
    _ensure_external_output(output_directory, repository_root)
    output_directory.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    populations = []
    audits = []
    records = []
    for fixture in (*ORDINARY_FIXTURES, *DETERMINISTIC_FIXTURES):
        replicate_count = config.ordinary_replicates if fixture in ORDINARY_FIXTURES else 1
        for replicate in range(replicate_count):
            population_seed = stable_seed(config.master_seed, fixture, replicate, "population")
            population = generate_fixture(fixture, config.population_size, population_seed)
            population_row = _serialize_population(population, replicate, population_seed)
            population_digest = population_row["population_digest"]
            populations.append(population_row)
            for arm in development_arms(config.gammas):
                rng_seed = stable_seed(
                    config.master_seed, fixture, replicate, arm.name, arm.gamma, "sampling"
                )
                audit = simulate_audit(population, arm, config.budget, config.ridge, rng_seed)
                audit_id = f"{fixture}:{replicate}:{arm.name}:{arm.gamma}"
                audits.append(
                    {
                        "audit_id": audit_id,
                        "population_digest": population_digest,
                        "fixture": fixture,
                        "replicate": replicate,
                        "arm": arm.name,
                        "conceptual_arm": arm.conceptual_label,
                        "policy": arm.policy,
                        "control_variate": arm.use_control_variate,
                        "gamma": arm.gamma,
                        "rng_seed": rng_seed,
                        "selection_order": audit["selection_order"],
                        "trace": audit["trace"],
                        "q_replay_passed": audit["q_replay_passed"],
                    }
                )
                for fixed_lambda in config.lambdas:
                    records.append(
                        _record_for_lambda(
                            fixture,
                            replicate,
                            population,
                            arm,
                            audit_id,
                            audit,
                            fixed_lambda,
                            config,
                        )
                    )
    grouped = _group_records(records)
    machine_path = output_directory / "results.json"
    csv_path = output_directory / "summary.csv"
    report_path = output_directory / "report.txt"
    machine_document = {
        "notice": DEVELOPMENT_ONLY_NOTICE,
        "code_version": DEV_CODE_VERSION,
        "git_provenance": inspect_git_provenance(repository_root),
        "python_version": platform.python_version(),
        "configuration": asdict(config),
        "populations": populations,
        "audits": audits,
        "results": records,
    }
    machine_path.write_text(
        json.dumps(machine_document, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    _write_csv(csv_path, grouped)
    runtime_seconds = time.perf_counter() - started
    _write_report(report_path, grouped, runtime_seconds)
    failures = {
        "invalid_runs": sum(row["validity_status"] == "invalid" for row in records),
        "empty_confidence_sets": sum(
            row["validity_status"] == "empty_confidence_set" for row in records
        ),
        "support_admissibility_failures": sum(
            row["validity_status"] == "invalid_support_admissibility"
            for row in records
        ),
        "q_replay_failures": sum(not row["q_replay_passed"] for row in records),
        "records_with_multiplier_failure": sum(
            bool(row["multiplier_failure_present"]) for row in records
        ),
        "monotonicity_failures": sum(
            row["monotonicity_status"] == "failed" for row in records
        ),
    }
    return {
        "output_directory": str(output_directory),
        "machine_json": str(machine_path),
        "summary_csv": str(csv_path),
        "report_txt": str(report_path),
        "runtime_seconds": runtime_seconds,
        "record_count": len(records),
        "audit_count": len(audits),
        "group_count": len(grouped),
        "failures": failures,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=DEVELOPMENT_ONLY_NOTICE)
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="run the bounded development-only smoke configuration",
    )
    parser.add_argument(
        "--ppi-stage1",
        action="store_true",
        help="run the bounded development-only PPI Stage 1 plumbing configuration",
    )
    parser.add_argument(
        "--stage2-preflight",
        action="store_true",
        help=(
            "run only frozen Stage 2 calibration and mandatory-control preflight; "
            "never runs evaluation or bootstrap workloads"
        ),
    )
    parser.add_argument(
        "--stage2-primary-map",
        action="store_true",
        help=(
            "run the frozen development-only 144-cell Stage 2 primary map; "
            "scientific parameters are not exposed as CLI options"
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="optional external output directory; defaults to the OS temporary directory",
    )
    parser.add_argument(
        "--replay-artifact",
        type=Path,
        default=None,
        help="replay serialized pre-reveal draws from an existing JSON artifact only",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="required positive process count for Stage 2 execution modes only",
    )
    args = parser.parse_args(argv)
    selected_modes = sum(
        bool(value)
        for value in (
            args.smoke,
            args.ppi_stage1,
            args.stage2_preflight,
            args.stage2_primary_map,
            args.replay_artifact,
        )
    )
    if selected_modes != 1:
        parser.error(
            "choose exactly one of --smoke, --ppi-stage1, --stage2-preflight, "
            "--stage2-primary-map, or --replay-artifact"
        )
    if args.workers is not None and not (
        args.stage2_preflight or args.stage2_primary_map
    ):
        parser.error("--workers is supported only with Stage 2 execution modes")
    if args.replay_artifact:
        try:
            result = replay_artifact(args.replay_artifact)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"INVALID REPLAY ARTIFACT: {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["failure_count"] == 0 else 2
    if args.ppi_stage1:
        print(DEVELOPMENT_ONLY_NOTICE)
        print(
            "PPI Stage 1 engineering defaults: N=200, B=20, replicates=10, "
            "K=(8,4), epsilon_samp=0.20, lambda=(0.05,0.10,0.25,0.50)."
        )
        try:
            result = run_ppi_stage1(args.output_dir)
        except (InvalidDevelopmentRun, ControlledNumericalFailure, ValueError) as error:
            print(f"INVALID DEVELOPMENT RUN: {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    if args.stage2_preflight:
        if args.output_dir is None:
            parser.error("--stage2-preflight requires --output-dir outside the repository")
        if args.workers is None or args.workers <= 0:
            parser.error("--stage2-preflight requires --workers with a positive value")
        print(DEVELOPMENT_ONLY_NOTICE)
        print(
            "Stage 2 preflight runs frozen calibration and mandatory controls only; "
            "it does not execute evaluation or bootstrap workloads."
        )
        try:
            result = run_stage2_preflight(args.output_dir, args.workers)
        except (
            InvalidDevelopmentRun,
            ControlledNumericalFailure,
            OSError,
            ValueError,
        ) as error:
            print(f"INVALID STAGE 2 PREFLIGHT: {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    if args.stage2_primary_map:
        if args.output_dir is None:
            parser.error("--stage2-primary-map requires --output-dir outside the repository")
        if args.workers is None or args.workers <= 0:
            parser.error("--stage2-primary-map requires --workers with a positive value")
        print(DEVELOPMENT_ONLY_NOTICE)
        print(
            "Stage 2 primary-map execution is development-only; it uses the frozen "
            "144-cell design and does not execute confirmatory work."
        )
        try:
            result = run_stage2_primary_map(args.output_dir, args.workers)
        except (
            InvalidDevelopmentRun,
            ControlledNumericalFailure,
            OSError,
            ValueError,
        ) as error:
            print(f"INVALID STAGE 2 PRIMARY MAP: {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    print(DEVELOPMENT_ONLY_NOTICE)
    print("Smoke defaults: N=200, B=50, risk=0.05, ordinary replicates=50,")
    print("gamma=(0.10, 0.50), ridge=1e-6, lambda=(0.05, 0.10, 0.25, 0.50).")
    try:
        result = run_smoke(args.output_dir)
    except (InvalidDevelopmentRun, ControlledNumericalFailure, ValueError) as error:
        print(f"INVALID DEVELOPMENT RUN: {error}", file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    engineering_failures = {
        key: value
        for key, value in result["failures"].items()
        if key != "empty_confidence_sets"
    }
    if any(engineering_failures.values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
