from __future__ import annotations

import inspect
import json
import math
import os
import copy
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from development.statistical_feasibility.betting import (
    ControlledNumericalFailure,
    EmptyConfidenceSet,
    MonotonicityFailure,
    SupportAdmissibilityFailure,
    SupportTerm,
    WealthStep,
    bisect_lower_bound,
    estimate_beta,
    evaluate_running_bound,
    log_wealth,
    verify_monotonicity,
    wealth_multiplier,
)
from development.statistical_feasibility.core import (
    ArmSpec,
    SmokeConfig,
    development_arms,
    digest_rows,
    stable_seed,
)
from development.statistical_feasibility.run import (
    _group_records,
    _record_for_lambda,
    default_output_directory,
    inspect_git_provenance,
    replay_artifact,
    run_smoke,
    simulate_audit,
)
from development.statistical_feasibility.sampling import (
    draw_item,
    policy_probabilities,
    replay_pre_reveal_draw,
    serialized_pre_reveal_digest,
    score_informed_probabilities,
    select_item_from_variate,
    serialize_pre_reveal_draw,
    uniform_probabilities,
)
from development.statistical_feasibility.scenarios import generate_fixture


class StatisticalFeasibilityTests(unittest.TestCase):
    def test_01_uniform_probabilities_sum_to_one(self) -> None:
        probabilities = uniform_probabilities(("a", "b", "c"))
        self.assertTrue(math.isclose(math.fsum(probabilities.values()), 1.0))
        self.assertEqual(set(probabilities.values()), {1.0 / 3.0})

    def test_02_score_probabilities_positive_sum_and_uniform_reductions(self) -> None:
        remaining = ("a", "b", "c")
        probabilities, _ = score_informed_probabilities(
            remaining, {"a": 0.1, "b": 0.2, "c": 0.8}, 0.1
        )
        self.assertTrue(math.isclose(math.fsum(probabilities.values()), 1.0))
        self.assertTrue(all(value > 0.0 for value in probabilities.values()))
        uniform = uniform_probabilities(remaining)
        constant, _ = score_informed_probabilities(
            remaining, {"a": 0.5, "b": 0.5, "c": 0.5}, 0.1
        )
        zero, _ = score_informed_probabilities(
            remaining, {"a": 0.0, "b": 0.0, "c": 0.0}, 0.1
        )
        self.assertEqual(constant, uniform)
        self.assertEqual(zero, uniform)

    def test_03_sampling_without_replacement_has_no_duplicates(self) -> None:
        rng = random.Random(7)
        remaining = [f"i-{index}" for index in range(20)]
        selected = []
        while remaining:
            item_id = draw_item(uniform_probabilities(remaining), rng)
            selected.append(item_id)
            remaining.remove(item_id)
        self.assertEqual(len(selected), len(set(selected)))

    def test_04_q_reconstructs_from_pre_reveal_state(self) -> None:
        remaining = ("a", "b", "c")
        scores = {"a": 0.2, "b": 0.4, "c": 0.9}
        first, first_norm = policy_probabilities("score_informed", remaining, scores, 0.5)
        replay, replay_norm = policy_probabilities("score_informed", remaining, scores, 0.5)
        self.assertEqual(tuple(first.items()), tuple(replay.items()))
        self.assertEqual(first_norm, replay_norm)

    def test_04b_serialized_pre_reveal_replay_and_tamper_detection(self) -> None:
        remaining = ("a", "b", "c")
        scores = {"a": 0.2, "b": 0.4, "c": 0.9}
        probabilities, normalization = policy_probabilities(
            "score_informed", remaining, scores, 0.5
        )
        draw_uniform = 0.42
        selected = select_item_from_variate(probabilities, draw_uniform)
        record = serialize_pre_reveal_draw(
            step=1,
            remaining_item_ids=remaining,
            scores=scores,
            sampling_policy="score_informed",
            gamma=0.5,
            probabilities=probabilities,
            normalization=normalization,
            draw_uniform=draw_uniform,
            selected_item_id=selected,
        )
        self.assertTrue(replay_pre_reveal_draw(record).passed)
        mutations = (
            ("remaining_scores", lambda value: value.__setitem__(0, 0.21)),
            ("remaining_item_ids", lambda value: value.reverse()),
            ("gamma", lambda value: 0.1),
            ("q_vector", lambda value: value.__setitem__(0, value[0] + 0.01)),
            ("normalization", lambda value: value.__setitem__("policy_value", value["policy_value"] + 1.0)),
            ("draw_uniform", lambda value: 0.99),
            ("selected_item_id", lambda value: "a" if value != "a" else "b"),
            ("selected_q", lambda value: value / 2.0),
        )
        import copy

        for field, mutate in mutations:
            tampered = copy.deepcopy(record)
            original = tampered[field]
            replacement = mutate(original)
            if replacement is not None:
                tampered[field] = replacement
            self.assertFalse(replay_pre_reveal_draw(tampered).passed, field)

    def test_05_sampling_policy_signature_has_no_outcome_input(self) -> None:
        parameters = inspect.signature(policy_probabilities).parameters
        self.assertNotIn("outcomes", parameters)
        self.assertNotIn("y", parameters)
        self.assertEqual(tuple(parameters), ("policy", "remaining_ids", "scores", "gamma"))

    def test_06_uniform_weight_importance_expectation(self) -> None:
        outcomes = {"a": 1, "b": 0, "c": 1}
        probabilities = {"a": 0.2, "b": 0.3, "c": 0.5}
        expectation = math.fsum(
            probabilities[item_id] * outcomes[item_id] / (3 * probabilities[item_id])
            for item_id in probabilities
        )
        self.assertAlmostEqual(expectation, 2.0 / 3.0)

    def test_07_control_variate_zero_conditional_mean(self) -> None:
        probabilities = {"a": 0.2, "b": 0.3, "c": 0.5}
        scores = {"a": 0.1, "b": 0.5, "c": 0.8}
        expected_score = math.fsum(probabilities[i] * scores[i] for i in probabilities)
        expected_u = math.fsum(
            probabilities[i] * (scores[i] - expected_score) for i in probabilities
        )
        self.assertAlmostEqual(expected_u, 0.0)

    def test_08_constant_scores_produce_zero_u(self) -> None:
        probabilities = uniform_probabilities(("a", "b", "c"))
        scores = {"a": 0.5, "b": 0.5, "c": 0.5}
        expected_score = math.fsum(probabilities[i] * scores[i] for i in probabilities)
        self.assertTrue(all(scores[i] - expected_score == 0.0 for i in probabilities))

    def test_09_beta_is_predictable_delayed_and_clipped(self) -> None:
        self.assertEqual(estimate_beta((), 1e-6).value, 0.0)
        self.assertEqual(estimate_beta(((1.0, 0.2), (2.0, 0.4)), 1e-6).value, 0.0)
        prior = ((1.0, 0.0), (3.0, 0.5), (5.0, 1.0))
        first = estimate_beta(prior, 1e-6)
        self.assertGreaterEqual(first.value, -1.0)
        self.assertLessEqual(first.value, 1.0)
        self.assertEqual(first, estimate_beta(tuple(prior), 1e-6))

    def test_10_smoke_lambdas_have_nonnegative_worst_case_multiplier(self) -> None:
        for fixed_lambda in (0.05, 0.10, 0.25, 0.50):
            self.assertGreaterEqual(wealth_multiplier(fixed_lambda, -1.0, 1.0), 0.0)

    def test_11_log_wealth_is_finite_or_controlled(self) -> None:
        finite = log_wealth((WealthStep(1.5, 0.0),), 0.5, 0.5)
        self.assertTrue(math.isfinite(finite))
        with self.assertRaises(ControlledNumericalFailure):
            wealth_multiplier(0.5, -2.0, 1.0)

    def test_12_wealth_is_monotone_in_complement_candidate(self) -> None:
        steps = (WealthStep(1.2, 0.0), WealthStep(0.7, 0.1))
        self.assertTrue(verify_monotonicity(steps, 0.25, 1e-12))
        self.assertGreaterEqual(log_wealth(steps, 0.25, 0.0), log_wealth(steps, 0.25, 1.0))

    def test_13_bisection_returns_bound_in_unit_interval(self) -> None:
        steps = tuple(WealthStep(2.5, 0.0) for _ in range(5))
        bound = bisect_lower_bound(steps, 0.5, 0.05, 1e-10)
        self.assertGreaterEqual(bound, 0.0)
        self.assertLessEqual(bound, 1.0)

    def test_13b_empty_confidence_set_is_not_a_numeric_bound(self) -> None:
        steps = tuple(WealthStep(3.0, 0.0) for _ in range(5))
        with self.assertRaises(EmptyConfidenceSet):
            bisect_lower_bound(steps, 0.5, 0.05, 1e-10)
        population = generate_fixture("all_correct", 5, 1)
        record = _record_for_lambda(
            "all_correct",
            0,
            population,
            ArmSpec("A", "uniform", False, None),
            "empty-audit",
            {
                "wealth_steps": steps,
                "warnings": [],
                "observations": 5,
                "errors_observed": 0,
                "min_q": 0.2,
                "max_importance_weight": 1.0,
                "q_replay_passed": True,
            },
            0.5,
            SmokeConfig(population_size=5, budget=5, ordinary_replicates=1),
        )
        self.assertEqual(record["validity_status"], "empty_confidence_set")
        self.assertIsNone(record["final_upper_confidence_bound"])
        self.assertFalse(record["coverage_indicator"])
        summary = _group_records([record])[0]
        self.assertEqual(summary["empty_confidence_set_count"], 1)
        self.assertEqual(summary["empty_confidence_set_proportion"], 1.0)
        self.assertEqual(summary["mean_upper_bound"], "")
        self.assertEqual(summary["median_upper_bound"], "")

    def test_14_running_intersection_never_weakens(self) -> None:
        steps = (
            WealthStep(2.0, 0.05),
            WealthStep(0.2, 0.10),
            WealthStep(1.5, 0.15),
        )
        bounds = [
            evaluate_running_bound(steps[:end], 0.25, 0.05, 1e-10, 1e-10).lower_complement_bound
            for end in range(1, len(steps) + 1)
        ]
        self.assertEqual(bounds, sorted(bounds))

    def test_15_upper_error_bound_is_one_minus_lower_complement(self) -> None:
        evaluation = evaluate_running_bound(
            (WealthStep(1.5, 0.1),), 0.25, 0.05, 1e-10, 1e-10
        )
        self.assertEqual(
            evaluation.upper_error_bound, 1.0 - evaluation.lower_complement_bound
        )

    def test_15b_support_wide_check_rejects_unrealized_negative_payoff(self) -> None:
        realized_only = WealthStep(1.0, 0.0)
        self.assertTrue(math.isfinite(log_wealth((realized_only,), 0.5, 1.0)))
        unseen_negative = SupportTerm(
            item_id="unselected-item",
            outcome=0,
            score=1.0,
            probability=0.5,
            control_value=-1.0,
            beta=1.0,
            constant_term=-1.1,
        )
        support_checked = WealthStep(1.0, 0.0, (unseen_negative,))
        self.assertGreaterEqual(
            wealth_multiplier(0.5, realized_only.constant_term, 1.0), 0.0
        )
        with self.assertRaises(SupportAdmissibilityFailure):
            log_wealth((support_checked,), 0.5, 1.0, 1e-10)

    def test_15c_audit_serializes_both_outcomes_for_every_remaining_item(self) -> None:
        population = generate_fixture("tied_score", 7, 19)
        audit = simulate_audit(
            population, ArmSpec("D", "score_informed", True, 0.1), 1, 1e-6, 23
        )
        step = audit["wealth_steps"][0]
        self.assertEqual(step.support_term_count, 2 * population.size)
        self.assertIsNotNone(step.support_minimum)
        self.assertGreater(step.support_minimum.probability, 0.0)

    def test_16_full_census_logical_bound_is_exact(self) -> None:
        population = generate_fixture("independent_score", 20, 11)
        audit = simulate_audit(
            population, ArmSpec("A", "uniform", False, None), 20, 1e-6, 17
        )
        evaluation = evaluate_running_bound(
            audit["wealth_steps"], 0.1, 0.05, 1e-10, 1e-10
        )
        self.assertAlmostEqual(evaluation.upper_error_bound, population.true_prevalence)

    def test_17_extreme_fixtures_have_coherent_bounds(self) -> None:
        for fixture, expected in (("all_correct", 0.0), ("all_error", 1.0)):
            population = generate_fixture(fixture, 10, 3)
            audit = simulate_audit(
                population, ArmSpec("A", "uniform", False, None), 10, 1e-6, 5
            )
            evaluation = evaluate_running_bound(
                audit["wealth_steps"], 0.1, 0.05, 1e-10, 1e-10
            )
            self.assertAlmostEqual(evaluation.upper_error_bound, expected)

    def test_18_paired_arms_share_identical_population(self) -> None:
        population = generate_fixture("tied_score", 30, 13)
        digest = digest_rows(
            (item.item_id, item.score.hex(), item.outcome) for item in population.items
        )
        for arm in (
            ArmSpec("A", "uniform", False, None),
            ArmSpec("B", "uniform", True, None),
            ArmSpec("C", "score_informed", False, 0.1),
            ArmSpec("D", "score_informed", True, 0.1),
        ):
            simulate_audit(population, arm, 5, 1e-6, stable_seed(9, arm.name))
            self.assertEqual(
                digest,
                digest_rows((item.item_id, item.score.hex(), item.outcome) for item in population.items),
            )

    def test_19_same_seed_produces_byte_identical_machine_json(self) -> None:
        config = SmokeConfig(
            population_size=12,
            budget=5,
            ordinary_replicates=1,
            gammas=(0.1,),
            lambdas=(0.1,),
        )
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            first_result = run_smoke(Path(first), config)
            second_result = run_smoke(Path(second), config)
            self.assertEqual(
                Path(first_result["machine_json"]).read_bytes(),
                Path(second_result["machine_json"]).read_bytes(),
            )

    def test_19b_machine_arm_ids_are_unique_per_gamma(self) -> None:
        arms = development_arms((0.1, 0.5))
        self.assertEqual(len({arm.name for arm in arms}), len(arms))
        self.assertEqual(
            {arm.conceptual_label for arm in arms},
            {"A_uniform_no_cv", "B_uniform_cv", "C_score_no_cv", "D_score_cv"},
        )

    def test_19c_monotonicity_status_is_explicit(self) -> None:
        population = generate_fixture("all_correct", 5, 1)
        audit = {
            "wealth_steps": (WealthStep(1.0, 0.0),),
            "warnings": [], "observations": 1, "errors_observed": 0,
            "min_q": 0.2, "max_importance_weight": 1.0, "q_replay_passed": True,
        }
        configuration = SmokeConfig(population_size=5, budget=5, ordinary_replicates=1)
        with patch(
            "development.statistical_feasibility.run.evaluate_running_bound",
            side_effect=MonotonicityFailure("test monotonicity failure"),
        ):
            failed = _record_for_lambda("fixture", 0, population, ArmSpec("A", "uniform", False, None), "a", audit, 0.1, configuration)
        self.assertEqual(failed["monotonicity_status"], "failed")
        support_audit = dict(audit)
        support_audit["wealth_steps"] = (WealthStep(1.0, 0.0, (SupportTerm("i", 0, 1.0, 1.0, -1.0, 1.0, -2.0),)),)
        support = _record_for_lambda("fixture", 0, population, ArmSpec("A", "uniform", False, None), "b", support_audit, 0.5, configuration)
        self.assertEqual(support["monotonicity_status"], "not_evaluated")
        numerical_audit = dict(audit)
        numerical_audit["wealth_steps"] = (WealthStep(float("nan"), 0.0),)
        numerical = _record_for_lambda("fixture", 0, population, ArmSpec("A", "uniform", False, None), "c", numerical_audit, 0.1, configuration)
        self.assertEqual(numerical["monotonicity_status"], "not_evaluated")
        passed = _record_for_lambda("fixture", 0, population, ArmSpec("A", "uniform", False, None), "d", audit, 0.1, configuration)
        self.assertEqual(passed["monotonicity_status"], "passed")

    def test_19d_git_provenance_resolves_directory_worktree_and_detached(self) -> None:
        sha = "a" * 40
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary) / "normal"
            (root / ".git" / "refs" / "heads").mkdir(parents=True)
            (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (root / ".git" / "refs" / "heads" / "main").write_text(sha + "\n", encoding="utf-8")
            normal = inspect_git_provenance(root)
            self.assertEqual(normal["head"], sha)
            self.assertEqual(normal["branch"], "main")
            self.assertFalse(normal["detached"])
            worktree = Path(temporary) / "worktree"
            metadata = Path(temporary) / "metadata"
            (metadata / "refs" / "heads").mkdir(parents=True)
            worktree.mkdir()
            (worktree / ".git").write_text("gitdir: ../metadata\n", encoding="utf-8")
            (metadata / "HEAD").write_text("ref: refs/heads/feature\n", encoding="utf-8")
            (metadata / "refs" / "heads" / "feature").write_text(sha + "\n", encoding="utf-8")
            linked = inspect_git_provenance(worktree)
            self.assertEqual(linked["head"], sha)
            self.assertEqual(linked["branch"], "feature")
            detached_root = Path(temporary) / "detached"
            (detached_root / ".git").mkdir(parents=True)
            (detached_root / ".git" / "HEAD").write_text(sha + "\n", encoding="utf-8")
            detached = inspect_git_provenance(detached_root)
            self.assertEqual(detached["head"], sha)
            self.assertTrue(detached["detached"])
            malformed_root = Path(temporary) / "malformed"
            malformed_root.mkdir()
            (malformed_root / ".git").write_text("not a gitdir\n", encoding="utf-8")
            malformed = inspect_git_provenance(malformed_root)
            self.assertIsNone(malformed["head"])
            self.assertIn("malformed", malformed["warning"])

    def test_19e_selection_order_is_hash_seed_independent(self) -> None:
        code = (
            "import json; from development.statistical_feasibility.core import ArmSpec; "
            "from development.statistical_feasibility.scenarios import generate_fixture; "
            "from development.statistical_feasibility.run import simulate_audit; "
            "p=generate_fixture('tied_score', 20, 31); "
            "a=simulate_audit(p, ArmSpec('C','score_informed',False,0.1), 5, 1e-6, 71); "
            "print(json.dumps(a['selected_item_ids_in_selection_order']))"
        )
        outputs = []
        for hash_seed in ("1", "2"):
            environment = dict(os.environ, PYTHONHASHSEED=hash_seed)
            completed = subprocess.run(
                [sys.executable, "-B", "-c", code],
                cwd=Path(__file__).resolve().parents[1],
                env=environment,
                capture_output=True,
                text=True,
                check=True,
            )
            outputs.append(completed.stdout)
        self.assertEqual(outputs[0], outputs[1])

    def test_19f_artifact_replay_binds_draws_to_serialized_population(self) -> None:
        config = SmokeConfig(population_size=12, budget=4, ordinary_replicates=1, gammas=(0.1,), lambdas=(0.1,))
        with tempfile.TemporaryDirectory() as output:
            result = run_smoke(Path(output), config)
            self.assertEqual(replay_artifact(Path(result["machine_json"]))["failure_count"], 0)
            document = json.loads(Path(result["machine_json"]).read_text(encoding="utf-8"))
            forged = copy.deepcopy(document)
            audit = next(audit for audit in forged["audits"] if audit["policy"] == "score_informed")
            record = audit["trace"][0]["pre_reveal"]
            record["remaining_scores"][0] = 0.75 if record["remaining_scores"][0] != 0.75 else 0.25
            forged_scores = dict(zip(record["remaining_item_ids"], record["remaining_scores"]))
            probabilities, normalization = policy_probabilities(
                record["sampling_policy"], record["remaining_item_ids"], forged_scores, record["gamma"]
            )
            record["normalization"] = {
                "remaining_count": len(record["remaining_item_ids"]),
                "score_sum": math.fsum(record["remaining_scores"]),
                "policy_value": normalization,
            }
            record["q_vector"] = [probabilities[item_id] for item_id in record["remaining_item_ids"]]
            record["selected_item_id"] = select_item_from_variate(probabilities, record["draw_uniform"])
            record["selected_q"] = probabilities[record["selected_item_id"]]
            audit["selection_order"][0] = record["selected_item_id"]
            record["integrity_digest"] = serialized_pre_reveal_digest(record)
            forged_path = Path(output) / "self-consistent-forged-draw.json"
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            forged_replay = replay_artifact(forged_path)
            self.assertGreater(forged_replay["failure_count"], 0)
            self.assertIn("population score mismatch", forged_replay["failures"][0]["reason"])
            digest_tampered = copy.deepcopy(document)
            digest_tampered["populations"][0]["items"][0]["hidden_outcome"] = 1 - digest_tampered["populations"][0]["items"][0]["hidden_outcome"]
            digest_path = Path(output) / "population-digest-tampered.json"
            digest_path.write_text(json.dumps(digest_tampered), encoding="utf-8")
            self.assertIn(
                "serialized population digest mismatch",
                replay_artifact(digest_path)["failures"][0]["reason"],
            )

    def test_20_default_outputs_are_outside_repository(self) -> None:
        output = default_output_directory()
        try:
            repository = Path(__file__).resolve().parents[1]
            self.assertNotEqual(output.resolve(), repository)
            self.assertNotIn(repository.resolve(), output.resolve().parents)
        finally:
            shutil.rmtree(output)


if __name__ == "__main__":
    unittest.main()
