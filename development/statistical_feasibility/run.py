"""CLI and orchestration for the development-only feasibility smoke run."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import math
from pathlib import Path
import platform
import random
import statistics
import sys
import tempfile
import time
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .betting import (
    ControlledNumericalFailure,
    EmptyConfidenceSet,
    MonotonicityFailure,
    SupportAdmissibilityFailure,
    SupportTerm,
    WealthStep,
    estimate_beta,
    evaluate_running_bound,
)
from .core import ArmSpec, FinitePopulation, SmokeConfig, development_arms, digest_rows, stable_seed
from . import DEVELOPMENT_ONLY_NOTICE, DEV_CODE_VERSION
from .sampling import (
    policy_probabilities,
    replay_pre_reveal_draw,
    select_item_from_variate,
    serialize_pre_reveal_draw,
)
from .scenarios import DETERMINISTIC_FIXTURES, ORDINARY_FIXTURES, generate_fixture


class InvalidDevelopmentRun(RuntimeError):
    pass


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
    return replay_serialized_audits(document)


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
    args = parser.parse_args(argv)
    if bool(args.smoke) == bool(args.replay_artifact):
        parser.error("choose exactly one of --smoke or --replay-artifact")
    if args.replay_artifact:
        try:
            result = replay_artifact(args.replay_artifact)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"INVALID REPLAY ARTIFACT: {error}", file=sys.stderr)
            return 2
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["failure_count"] == 0 else 2
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
