"""CLI and orchestration for the development-only feasibility smoke run."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import hashlib
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
    SupportAdmissibilityFailure,
    SupportTerm,
    WealthStep,
    estimate_beta,
    evaluate_running_bound,
)
from .core import ArmSpec, FinitePopulation, SmokeConfig, development_arms, digest_rows, stable_seed
from . import DEVELOPMENT_ONLY_NOTICE, DEV_CODE_VERSION
from .sampling import (
    draw_item,
    policy_probabilities,
    remaining_digest,
    score_digest,
    vector_digest,
)
from .scenarios import DETERMINISTIC_FIXTURES, ORDINARY_FIXTURES, generate_fixture


class InvalidDevelopmentRun(RuntimeError):
    pass


def _state_digest(state: object) -> str:
    return hashlib.sha256(repr(state).encode("utf-8")).hexdigest()


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_state(repository_root: Path) -> Dict[str, str]:
    git_dir = repository_root / ".git"
    result = {"branch": "unknown", "head": "unknown"}
    if not git_dir.is_dir():
        return result
    head_text = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    if head_text.startswith("ref: "):
        reference = head_text[5:]
        result["branch"] = reference.rsplit("/", 1)[-1]
        loose_ref = git_dir / Path(reference)
        if loose_ref.exists():
            result["head"] = loose_ref.read_text(encoding="utf-8").strip()
        else:
            packed_refs = git_dir / "packed-refs"
            if packed_refs.exists():
                for line in packed_refs.read_text(encoding="utf-8").splitlines():
                    if line and not line.startswith(("#", "^")):
                        sha, ref_name = line.split(" ", 1)
                        if ref_name == reference:
                            result["head"] = sha
                            break
    else:
        result["head"] = head_text
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
        replay_probabilities, replay_normalization = policy_probabilities(
            arm.policy, tuple(remaining), scores, arm.gamma
        )
        replay_passed = (
            tuple(replay_probabilities.items()) == tuple(probabilities.items())
            and replay_normalization == normalization
        )
        q_replay_passed = q_replay_passed and replay_passed
        pre_reveal = {
            "remaining_count": len(remaining),
            "remaining_ids_digest": remaining_digest(remaining),
            "score_values_digest": score_digest(remaining, scores),
            "policy": arm.policy,
            "gamma": arm.gamma,
            "normalization": normalization,
            "q_vector_digest": vector_digest(probabilities),
            "rng_state_digest": _state_digest(rng.getstate()),
        }
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

        selected = draw_item(probabilities, rng)
        if selected in selected_ids:
            raise InvalidDevelopmentRun("duplicate item selection")
        selected_ids.add(selected)
        selected_probability = probabilities[selected]
        pre_reveal["selected_item_id"] = selected
        pre_reveal["selected_probability"] = selected_probability
        pre_reveal["replay_selected_probability"] = replay_probabilities[selected]
        pre_reveal["q_replay_passed"] = replay_passed
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
        "selected_item_ids": list(selected_ids),
        "selection_order": [row["pre_reveal"]["selected_item_id"] for row in trace],
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
        monotonicity_passed = evaluation.monotonicity_passed
        min_multiplier = evaluation.min_multiplier
        negative_count = evaluation.negative_multiplier_count
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
        monotonicity_passed = True
        min_multiplier = None
        negative_count = 0
        final_log_wealth = {}
    except SupportAdmissibilityFailure as error:
        upper_bound = None
        coverage = False
        status = "invalid_support_admissibility"
        warning_rows = list(audit["warnings"]) + [str(error)]
        monotonicity_passed = True
        min_multiplier = None
        negative_count = 1
        final_log_wealth = {}
    except ControlledNumericalFailure as error:
        upper_bound = None
        coverage = False
        status = "invalid"
        warning_rows = list(audit["warnings"]) + [str(error)]
        monotonicity_passed = "monotone" not in str(error)
        min_multiplier = None
        negative_count = int("negative wealth multiplier" in str(error))
        final_log_wealth = {}
    return {
        "code_version": DEV_CODE_VERSION,
        "fixture": fixture,
        "replicate": replicate,
        "arm": arm.name,
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
        "negative_multiplier_count": negative_count,
        "final_log_wealth": final_log_wealth,
        "q_replay_passed": audit["q_replay_passed"],
        "monotonicity_passed": monotonicity_passed,
        "warnings": warning_rows,
        "validity_status": status,
    }


def _group_records(records: Sequence[dict]) -> List[dict]:
    grouped: Dict[Tuple[object, ...], List[dict]] = {}
    for record in records:
        key = (record["fixture"], record["arm"], record["lambda"], record["gamma"])
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
                "lambda": key[2],
                "gamma": key[3],
                "runs": len(group),
                "empirical_marginal_coverage": math.fsum(bool(row["coverage_indicator"]) for row in group) / len(group),
                "mean_upper_bound": statistics.fmean(bounds) if bounds else "",
                "median_upper_bound": statistics.median(bounds) if bounds else "",
                "mean_oracle_events_found": statistics.fmean(row["errors_observed"] for row in group),
                "zero_event_fraction": math.fsum(row["errors_observed"] == 0 for row in group) / len(group),
                "minimum_q": min(row["minimum_q"] for row in group),
                "maximum_importance_weight": max(row["maximum_importance_weight"] for row in group),
                "negative_multiplier_count": sum(row["negative_multiplier_count"] for row in group),
                "q_replay_failures": sum(not row["q_replay_passed"] for row in group),
                "empty_confidence_set_count": empty_count,
                "empty_confidence_set_proportion": empty_count / len(group),
                "support_admissibility_failures": sum(
                    row["validity_status"] == "invalid_support_admissibility"
                    for row in group
                ),
                "inversion_failures": sum(
                    row["validity_status"] == "invalid" for row in group
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
        "",
    ]
    for row in rows:
        lines.append(
            " | ".join(
                (
                    f"fixture={row['fixture']}",
                    f"arm={row['arm']}",
                    f"lambda={row['lambda']}",
                    f"gamma={row['gamma']}",
                    f"coverage={row['empirical_marginal_coverage']:.6f}",
                    f"mean_upper={row['mean_upper_bound']}",
                    f"median_upper={row['median_upper_bound']}",
                    f"mean_events={row['mean_oracle_events_found']:.6f}",
                    f"zero_event_fraction={row['zero_event_fraction']:.6f}",
                    f"min_q={row['minimum_q']:.12g}",
                    f"max_importance={row['maximum_importance_weight']:.12g}",
                    f"negative_multipliers={row['negative_multiplier_count']}",
                    f"q_replay_failures={row['q_replay_failures']}",
                    f"empty_confidence_sets={row['empty_confidence_set_count']}",
                    f"empty_confidence_set_proportion={row['empty_confidence_set_proportion']:.6f}",
                    f"support_admissibility_failures={row['support_admissibility_failures']}",
                    f"inversion_failures={row['inversion_failures']}",
                )
            )
        )
    lines.extend(("", DEVELOPMENT_ONLY_NOTICE))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


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
        "git_state": _git_state(repository_root),
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
        "negative_multiplier_count": sum(row["negative_multiplier_count"] for row in records),
        "monotonicity_failures": sum(not row["monotonicity_passed"] for row in records),
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
    args = parser.parse_args(argv)
    if not args.smoke:
        parser.error("only --smoke is supported by this development-only prototype")
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
