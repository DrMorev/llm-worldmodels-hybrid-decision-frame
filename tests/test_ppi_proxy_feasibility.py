"""Stage 1 PPI plumbing tests. All fixtures and conclusions are development-only."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from development.statistical_feasibility.betting import (
    ControlledNumericalFailure,
    EmptyConfidenceSet,
    MonotonicityFailure,
    SupportAdmissibilityFailure,
    SupportTerm,
    WealthStep,
    bisect_mixture_lower_bound,
    evaluate_running_mixture_bound,
    log_mixture_wealth,
    stable_logsumexp,
    validate_support_admissibility,
    verify_mixture_monotonicity,
    wealth_multiplier,
)
from development.statistical_feasibility.core import (
    STAGE1_SCENARIOS,
    ObservableScoreItem,
    Stage1Config,
    Stage2Config,
    stable_seed,
    stage2_development_primary_bootstrap_seed,
    stage2_generator_strata,
    stage1_arms,
    stage2_cells,
    stage2_trajectory_arms,
)
from development.statistical_feasibility.proxies import (
    InvalidObservableMagnitude,
    ObservableCaseOutputs,
    StructuralRepresentation,
    compute_confidence_margin,
    compute_ppi,
    frozen_transformation_bank,
    ppi_from_observable_outputs,
)
from development.statistical_feasibility.run import (
    LeanAuditWorkUnit,
    Stage2ControlBoundFailure,
    Stage2PreflightFailureReceipt,
    _stage2_audit_seed_master,
    _stage2_control_g_values,
    _lambda_grid_digest,
    aggregate_stage2_delta,
    build_stage2_control_work_units,
    build_stage2_primary_work_units,
    _iter_stage2_primary_bootstrap_worlds,
    bootstrap_stage2_primary_statistics,
    classify_stage2_development,
    empirical_gamma_nc,
    effective_upper_bound,
    execute_lean_audit_work_units,
    replay_artifact,
    retain_stage1_trace,
    run_ppi_stage1,
    run_stage2_preflight,
    main as run_main,
    simulate_named_audit,
    stage2_manifest,
    stage2_primary_map_manifest,
    stage2_preflight_plan,
    stage2_replay_replicate,
    stage2_structural_representation_complete,
    summarize_stage2_cells,
    type7_percentile,
)
from development.statistical_feasibility.sampling import policy_probabilities
from development.statistical_feasibility.scenarios import (
    STAGE1_ACCEPTANCE_CHECK_SEEDS,
    STAGE1_SCENARIO_SPECS,
    Stage2GeneratorParameters,
    Stage2MarginCalibration,
    calibrate_stage2_margin_normalization,
    calibrate_stage2_risk_parameters,
    generate_stage1_population,
    generate_stage2_population,
    permute_ppi_globally,
    stage2_control_parameters,
    validate_stage1_acceptance,
)


class PPIFormulaTests(unittest.TestCase):
    def test_01_exact_ppi_formula(self):
        result = compute_ppi(1, 1, (1, 0, 1, 0), (1, 0, 0, 1), range(4))
        self.assertEqual(result.score, 0.75)

    def test_02_diagnostics_do_not_alter_ppi(self):
        left = compute_ppi(1, 1, (1, 0), (1, 1), (0, 1))
        right = compute_ppi(1, 1, (1, 1), (1, 0), (0, 1))
        self.assertEqual(left.score, right.score)
        self.assertNotEqual(left.primary_flip_rate, right.primary_flip_rate)

    def test_03_identity_sentinel_zero(self):
        result = compute_ppi(0, 0, (0,) * 8, (0,) * 8, range(8))
        self.assertEqual(result.score, 0.0)

    def test_04_transform_invariance(self):
        rep = StructuralRepresentation(1, 1, 1.0, (1.5,) * 8)
        for transform in frozen_transformation_bank().transformations:
            changed = transform.apply(rep)
            self.assertEqual((changed.canonical_state, changed.truth, changed.robust_feature), (1, 1, 1.0))

    def test_05_hidden_field_isolation_by_api(self):
        fields = ObservableCaseOutputs.__dataclass_fields__
        self.assertNotIn("truth", fields)
        self.assertNotIn("h_i", fields)
        self.assertNotIn("joint_dangerous_error", fields)

    def test_06_bank_digest_is_frozen(self):
        self.assertEqual(frozen_transformation_bank().digest, frozen_transformation_bank().digest)

    def test_07_k8_levels(self):
        output = ObservableCaseOutputs("x", 1, 1, 1.0, 1.0, (1, 0, 1, 0, 1, 0, 1, 0), (1,) * 8)
        score = ppi_from_observable_outputs(output, frozen_transformation_bank(), 8).score
        self.assertEqual(score * 8, round(score * 8))

    def test_08_k4_nested_subset(self):
        bank = frozen_transformation_bank()
        self.assertEqual(bank.indices_for_k(4), (0, 2, 5, 7))
        self.assertTrue(set(bank.indices_for_k(4)).issubset(bank.indices_for_k(8)))

    def test_09_cross_process_ppi_is_deterministic(self):
        code = (
            "from development.statistical_feasibility.proxies import compute_ppi;"
            "print(compute_ppi(1,1,(1,0,1,0),(1,0,0,1),range(4)).score)"
        )
        observed = subprocess.check_output([sys.executable, "-B", "-c", code], text=True).strip()
        self.assertEqual(observed, "0.75")

    def test_10_confidence_margin_formula(self):
        self.assertAlmostEqual(compute_confidence_margin(1.55, 3.0, .1, .1, 3.0, 3.0), 0.5)

    def test_11_invalid_normalization(self):
        with self.assertRaises(InvalidObservableMagnitude):
            compute_confidence_margin(1.0, 1.0, .1, .1, .1, 3.0)

    def test_12_nonfinite_magnitude(self):
        with self.assertRaises(InvalidObservableMagnitude):
            compute_confidence_margin(math.nan, 1.0, .1, .1, 3.0, 3.0)


class Stage1ArmAndBettingTests(unittest.TestCase):
    def test_13_five_conceptual_arm_ids(self):
        self.assertEqual({arm.conceptual_arm for arm in stage1_arms(8, .2)}, {"U0", "UM", "UP", "SM", "SP"})

    def test_14_machine_ids_unique(self):
        ids = [arm.arm_id for k in (8, 4) for arm in stage1_arms(k, .2)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_15_separate_sampling_and_cv_keys(self):
        arms = {arm.conceptual_arm: arm for arm in stage1_arms(8, .2)}
        self.assertIsNone(arms["UP"].sampling_score_key)
        self.assertEqual(arms["UP"].control_variate_score_key, "ppi_k8")

    def test_16_uniform_arm_probabilities(self):
        q, _ = policy_probabilities("uniform", ("a", "b"), {"a": 0.0, "b": 1.0}, None)
        self.assertEqual(q, {"a": .5, "b": .5})

    def test_17_constant_score_reduction(self):
        q, _ = policy_probabilities("score_informed", ("a", "b"), {"a": .3, "b": .3}, .2)
        self.assertEqual(q, {"a": .5, "b": .5})

    def test_18_equal_scores_equal_q(self):
        q, _ = policy_probabilities("score_informed", ("a", "b", "c"), {"a": .2, "b": .2, "c": 1.0}, .2)
        self.assertEqual(q["a"], q["b"])

    def test_19_actual_q_recording(self):
        config = Stage1Config(population_size=12, budget=2, replicates=1, scenario_ids=("constant_ppi",))
        population = generate_stage1_population("constant_ppi", 12, 4, config).population
        audit = simulate_named_audit(population, stage1_arms(8, .2)[-1], 2, 1e-6, 9)
        self.assertEqual(audit["trace"][0]["pre_reveal"]["selected_q"], 1 / 12)

    def test_20_common_lambda_grid_config(self):
        self.assertEqual(Stage1Config().lambda_grid, (.05, .10, .25, .50))

    def test_21_stable_logsumexp(self):
        self.assertAlmostEqual(stable_logsumexp((1000.0, 1000.0)), 1000.0 + math.log(2.0))

    def test_22_mixture_direct_arithmetic(self):
        steps = (WealthStep(.9, 0.0),)
        lambdas = (.05, .1)
        observed = math.exp(log_mixture_wealth(steps, lambdas, .3))
        expected = sum(1 + value * (.9 - .3) for value in lambdas) / 2
        self.assertAlmostEqual(observed, expected)

    def test_23_mixture_monotonicity(self):
        self.assertTrue(verify_mixture_monotonicity((WealthStep(.9, 0.0),), (.05, .1), 1e-12))

    def test_24_mixture_inversion_boundary(self):
        bound = bisect_mixture_lower_bound((WealthStep(.5, 0.0),), (.05, .1), .05, 1e-10)
        self.assertTrue(0.0 <= bound <= 1.0)

    def test_25_no_best_lambda_api(self):
        import development.statistical_feasibility.betting as betting
        self.assertFalse(hasattr(betting, "select_best_lambda"))

    def test_26_no_union_fallback_api(self):
        import development.statistical_feasibility.betting as betting
        self.assertFalse(hasattr(betting, "automatic_union_bound_fallback"))


class ScenarioAndArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = Stage1Config(population_size=20, budget=3, replicates=1)

    def _population(self, name):
        return generate_stage1_population(name, 20, 17, self.config)

    def test_27_null_mechanism_template(self):
        self.assertEqual(STAGE1_SCENARIO_SPECS["no_shared_fragile_mechanism"].pi_h, 0.0)

    def test_28_unrelated_fragility_template(self):
        self.assertTrue(STAGE1_SCENARIO_SPECS["fragility_unrelated_to_error"].unrelated_fragility)

    def test_29_stable_false_belief_template(self):
        generated = self._population("stable_shared_false_belief")
        self.assertTrue(any(case.joint_dangerous_error and case.stable_false_belief for case in generated.causal_cases))
        self.assertEqual(set(generated.population.observable_score_vector("ppi_k8").values()), {0.0})

    def test_30_permuted_control(self):
        generated = self._population("permuted_ppi")
        self.assertTrue(generated.scenario_manifest["permuted_ppi"])

    def test_31_constant_score_control(self):
        generated = self._population("constant_ppi")
        self.assertEqual(len(set(generated.population.observable_score_vector("ppi_k8").values())), 1)

    def test_32_maximally_favourable_template(self):
        generated = self._population("maximally_favourable_fragile_mechanism")
        self.assertEqual(generated.scenario_manifest["pi_H"], 1.0)
        self.assertGreater(generated.population.true_prevalence, 0.0)

    def test_33_collider_diagnostic_present(self):
        diagnostic = self._population("low_shared_fragile_mechanism").collider_diagnostic
        self.assertIn("association_before_agreement", diagnostic)
        self.assertIn("association_after_agreement", diagnostic)

    def test_34_all_eight_templates_exist(self):
        self.assertEqual(set(STAGE1_SCENARIOS), set(STAGE1_SCENARIO_SPECS))

    def test_35_trace_rule_is_deterministic(self):
        self.assertTrue(retain_stage1_trace(0, "valid", True))
        self.assertTrue(retain_stage1_trace(3, "invalid_numerical", True))
        self.assertTrue(retain_stage1_trace(3, "valid", False))
        self.assertFalse(retain_stage1_trace(3, "valid", True))

    def test_36_named_replay_all_channels(self):
        config = Stage1Config(population_size=12, budget=2, replicates=1, scenario_ids=("constant_ppi",))
        pop = generate_stage1_population("constant_ppi", 12, 9, config).population
        audit = simulate_named_audit(pop, stage1_arms(8, .2)[1], 2, 1e-6, 8)
        self.assertTrue(audit["q_replay_passed"])

    def test_37_confirmatory_manifest_rejected(self):
        with self.assertRaises(ValueError):
            Stage1Config(manifest_type="confirmatory").validate()

    def test_38_compact_artifact_and_tamper_rejection(self):
        config = Stage1Config(population_size=12, budget=2, replicates=1, scenario_ids=("constant_ppi",))
        with tempfile.TemporaryDirectory(prefix="ppi-stage1-test-") as folder:
            result = run_ppi_stage1(Path(folder), config)
            rows = Path(result["compact_results"]).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows), 10)
            artifact = Path(result["selected_replay_traces"])
            self.assertEqual(replay_artifact(artifact)["failure_count"], 0)
            document = json.loads(artifact.read_text(encoding="utf-8"))
            document["populations"][0]["items"][0]["observable_scores"]["ppi_k8"] = .875
            artifact.write_text(json.dumps(document), encoding="utf-8")
            self.assertGreater(replay_artifact(artifact)["failure_count"], 0)

    def test_39_fixed_seed_compact_output(self):
        config = Stage1Config(population_size=10, budget=2, replicates=1, scenario_ids=("constant_ppi",))
        with tempfile.TemporaryDirectory(prefix="ppi-stage1-a-") as left, tempfile.TemporaryDirectory(prefix="ppi-stage1-b-") as right:
            a = run_ppi_stage1(Path(left), config)
            b = run_ppi_stage1(Path(right), config)
            self.assertEqual(Path(a["compact_results"]).read_bytes(), Path(b["compact_results"]).read_bytes())

    def test_40_phase1b_legacy_imports_remain(self):
        from development.statistical_feasibility.run import run_smoke
        self.assertTrue(callable(run_smoke))


class Stage1AuditFindingTests(unittest.TestCase):
    """Focused regressions for the independent Stage 1 audit findings."""

    @staticmethod
    def _small_config():
        return Stage1Config(
            population_size=12,
            budget=2,
            replicates=1,
            scenario_ids=("constant_ppi",),
        )

    def _artifact_document(self, folder):
        result = run_ppi_stage1(Path(folder), self._small_config())
        path = Path(result["selected_replay_traces"])
        return path, json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_document(folder, name, document):
        path = Path(folder) / name
        path.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
        return path

    def test_41_genuine_stage1_replay_metadata_passes(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            path, _ = self._artifact_document(folder)
            self.assertEqual(replay_artifact(path)["failure_count"], 0)

    def test_42_shortened_lambda_grids_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            for index, grid in enumerate(((.05, .10), (.05,), (.50,))):
                document = self._artifact_document(folder)[1]
                document["audits"][0]["lambda_grid"] = list(grid)
                document["audits"][0]["lambda_grid_digest"] = _lambda_grid_digest(grid)
                replay = replay_artifact(
                    self._write_document(folder, f"short-{index}.json", document)
                )
                self.assertGreater(replay["failure_count"], 0)

    def test_43_reordered_lambda_grid_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            _, document = self._artifact_document(folder)
            grid = (0.10, 0.05, 0.25, 0.50)
            document["audits"][0]["lambda_grid"] = list(grid)
            document["audits"][0]["lambda_grid_digest"] = _lambda_grid_digest(grid)
            replay = replay_artifact(self._write_document(folder, "reordered.json", document))
            self.assertGreater(replay["failure_count"], 0)

    def test_44_modified_configuration_inconsistent_grid_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            _, document = self._artifact_document(folder)
            grid = (0.05, 0.10, 0.25, 0.40)
            document["audits"][0]["lambda_grid"] = list(grid)
            document["audits"][0]["lambda_grid_digest"] = _lambda_grid_digest(grid)
            replay = replay_artifact(self._write_document(folder, "modified.json", document))
            self.assertGreater(replay["failure_count"], 0)

    def test_45_stale_lambda_digest_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            _, document = self._artifact_document(folder)
            document["audits"][0]["lambda_grid_digest"] = "0" * 64
            replay = replay_artifact(self._write_document(folder, "stale.json", document))
            self.assertGreater(replay["failure_count"], 0)

    def test_46_duplicate_lambda_grid_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            _, document = self._artifact_document(folder)
            grid = (0.05, 0.10, 0.25, 0.25)
            document["audits"][0]["lambda_grid"] = list(grid)
            document["audits"][0]["lambda_grid_digest"] = _lambda_grid_digest(grid)
            replay = replay_artifact(self._write_document(folder, "duplicate.json", document))
            self.assertGreater(replay["failure_count"], 0)

    def test_47_transformation_bank_digest_binding(self):
        with tempfile.TemporaryDirectory(prefix="ppi-audit-findings-") as folder:
            _, document = self._artifact_document(folder)
            reordered_bank_digest = hashlib.sha256(
                json.dumps(
                    list(reversed(document["transformation_bank"]["transformation_ids"])),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            for name, digest in (
                ("zero", "0" * 64),
                ("malformed", "not-a-digest"),
                ("reordered", reordered_bank_digest),
            ):
                forged = copy.deepcopy(document)
                forged["transformation_bank"]["digest"] = digest
                replay = replay_artifact(self._write_document(folder, f"bank-{name}.json", forged))
                self.assertGreater(replay["failure_count"], 0)

    def test_48_fixed_common_stage1_threshold(self):
        config = Stage1Config()
        self.assertEqual((config.tau_primary, config.tau_verifier), (.25, .25))
        self.assertEqual(config.maximum_generated_candidates, 5000)
        for arm in stage1_arms(8, config.epsilon_samp):
            self.assertEqual((config.tau_primary, config.tau_verifier), (.25, .25))
            self.assertIsNotNone(arm.arm_id)

    def test_49_acceptance_only_validation_has_required_nonvacuous_cells(self):
        checks = validate_stage1_acceptance(Stage1Config())
        self.assertEqual({row.seed for row in checks}, set(STAGE1_ACCEPTANCE_CHECK_SEEDS))
        by_scenario = {}
        for row in checks:
            by_scenario.setdefault(row.scenario_id, []).append(row)
        null_rows = by_scenario["no_shared_fragile_mechanism"]
        self.assertTrue(all(row.selection_neutral_null for row in null_rows))
        low_rows = by_scenario["low_shared_fragile_mechanism"]
        self.assertTrue(all(row.acceptance_rate < 1.0 for row in low_rows))
        self.assertGreaterEqual(
            sorted(row.acceptance_rate for row in low_rows)[len(low_rows) // 2], .50
        )
        self.assertLessEqual(
            sorted(row.acceptance_rate for row in low_rows)[len(low_rows) // 2], .95
        )
        additional = [
            rows for scenario, rows in by_scenario.items()
            if scenario not in {"no_shared_fragile_mechanism", "low_shared_fragile_mechanism"}
            and sum(row.acceptance_rate < 1.0 for row in rows) >= 8
            and sorted(row.acceptance_rate for row in rows)[len(rows) // 2] < .95
        ]
        self.assertTrue(additional)
        self.assertTrue(all(row.generated_candidate_count <= 5000 for row in checks))
        self.assertTrue(all(row.accepted_candidate_count == 200 for row in checks))

    def test_50_acceptance_population_and_collider_sets_are_separated(self):
        config = Stage1Config()
        generated = generate_stage1_population("low_shared_fragile_mechanism", 200, 91001, config)
        self.assertEqual(generated.population.size, 200)
        diagnostic = generated.collider_diagnostic
        self.assertGreater(diagnostic["generated_candidate_count"], generated.population.size)
        self.assertEqual(diagnostic["accepted_candidate_count"], 200)
        self.assertEqual(diagnostic["after_association_population_size"], 200)
        self.assertEqual(
            diagnostic["before_association_population_size"],
            diagnostic["generated_candidate_count"],
        )
        self.assertLess(diagnostic["acceptance_rate"], 1.0)
        for case in generated.causal_cases:
            self.assertEqual(case.primary_logit >= 0.0, case.verifier_logit >= 0.0)
            self.assertGreaterEqual(abs(case.primary_logit), .25)
            self.assertGreaterEqual(abs(case.verifier_logit), .25)

    def test_51_acceptance_checks_do_not_serialize_hidden_fields(self):
        fields = set(next(iter(validate_stage1_acceptance(Stage1Config()))).__dataclass_fields__)
        self.assertFalse(fields & {
            "truth", "joint_dangerous_error", "ppi", "h_i", "stable_false_belief",
            "component_error_primary", "component_error_verifier",
        })


def _slow_running_mixture_reference(
    steps,
    lambda_grid=(.05, .10, .25, .50),
    audit_risk=.05,
    inversion_tolerance=1e-10,
    monotonicity_tolerance=1e-10,
):
    """Test-local copy of the accepted pre-optimization prefix algorithm."""

    if not steps:
        return (0.0, 1.0, 1.0, "passed", 0.0, 0.0, 0.0)
    running_lower = 0.0
    min_multiplier = math.inf
    for end in range(1, len(steps) + 1):
        prefix = steps[:end]
        if not verify_mixture_monotonicity(
            prefix, lambda_grid, monotonicity_tolerance, inversion_tolerance
        ):
            raise MonotonicityFailure("reference mixture monotonicity failure")
        try:
            raw_lower = bisect_mixture_lower_bound(
                prefix,
                lambda_grid,
                audit_risk,
                inversion_tolerance,
                inversion_tolerance,
            )
        except EmptyConfidenceSet as error:
            raise EmptyConfidenceSet(f"{error}; prefix_step={end}") from error
        running_lower = max(
            running_lower, raw_lower, prefix[-1].logical_complement_lower
        )
        for fixed_lambda in lambda_grid:
            candidate_min = wealth_multiplier(
                fixed_lambda,
                prefix[-1].constant_term,
                1.0,
                inversion_tolerance,
            )
            if prefix[-1].support_terms or prefix[-1].support_minimum is not None:
                candidate_min = min(
                    candidate_min,
                    validate_support_admissibility(
                        end,
                        prefix[-1].support_terms,
                        fixed_lambda,
                        1.0,
                        inversion_tolerance,
                        prefix[-1].support_minimum,
                    ),
                )
            min_multiplier = min(min_multiplier, candidate_min)
    return (
        running_lower,
        1.0 - running_lower,
        min_multiplier,
        "passed",
        log_mixture_wealth(steps, lambda_grid, 0.0, inversion_tolerance),
        log_mixture_wealth(steps, lambda_grid, 1.0, inversion_tolerance),
        log_mixture_wealth(
            steps, lambda_grid, running_lower, inversion_tolerance
        ),
    )


class MixturePerformanceEquivalenceTests(unittest.TestCase):
    @staticmethod
    def _optimized_tuple(steps):
        result = evaluate_running_mixture_bound(
            steps, (.05, .10, .25, .50), .05, 1e-10, 1e-10
        )
        return (
            result.lower_complement_bound,
            result.upper_error_bound,
            result.min_multiplier,
            result.monotonicity_status,
            result.final_log_wealth_g0,
            result.final_log_wealth_g1,
            result.final_log_wealth_at_bound,
        )

    def assert_reference_equivalent(self, steps):
        reference = _slow_running_mixture_reference(steps)
        optimized = self._optimized_tuple(steps)
        self.assertEqual(reference[3], optimized[3])
        for expected, observed in zip(reference[:3] + reference[4:], optimized[:3] + optimized[4:]):
            if isinstance(expected, str) or isinstance(observed, str):
                self.assertEqual(expected, observed)
            else:
                self.assertLessEqual(abs(expected - observed), 1e-10)

    def test_52_every_prefix_matches_slow_reference_on_generated_audit(self):
        config = Stage1Config(
            population_size=40,
            budget=20,
            replicates=1,
            scenario_ids=("low_shared_fragile_mechanism",),
        )
        population = generate_stage1_population(
            "low_shared_fragile_mechanism", 40, 52001, config
        ).population
        arm = {row.conceptual_arm: row for row in stage1_arms(8, .2)}["SP"]
        audit = simulate_named_audit(population, arm, 20, config.ridge, 52002)
        for end in range(1, len(audit["wealth_steps"]) + 1):
            with self.subTest(prefix=end):
                self.assert_reference_equivalent(audit["wealth_steps"][:end])

    def test_53_deterministic_boundary_trajectories_match_reference(self):
        trajectories = (
            (),
            (WealthStep(.0, .0),),
            (WealthStep(.5, .25), WealthStep(1.25, .50)),
            tuple(WealthStep(.8 + index / 20, index / 20) for index in range(1, 10)),
        )
        for steps in trajectories:
            with self.subTest(length=len(steps)):
                self.assert_reference_equivalent(steps)

    def test_54_empty_confidence_set_status_matches_reference(self):
        steps = (WealthStep(100.0, 0.0),)
        with self.assertRaises(EmptyConfidenceSet):
            _slow_running_mixture_reference(steps)
        with self.assertRaises(EmptyConfidenceSet):
            self._optimized_tuple(steps)

    def test_55_support_admissibility_status_matches_reference(self):
        support = SupportTerm("x", 0, 0.0, 1.0, 0.0, 0.0, -3.0)
        steps = (WealthStep(.5, 0.0, (support,), support, 1),)
        with self.assertRaises(SupportAdmissibilityFailure):
            _slow_running_mixture_reference(steps)
        with self.assertRaises(SupportAdmissibilityFailure):
            self._optimized_tuple(steps)

    def test_56_incremental_monotonicity_protection_is_active(self):
        counter = iter(float(index) for index in range(1000))
        with mock.patch(
            "development.statistical_feasibility.betting.stable_logsumexp",
            side_effect=lambda values: next(counter),
        ):
            with self.assertRaises(MonotonicityFailure):
                self._optimized_tuple((WealthStep(.5, 0.0),))

    def test_57_numerical_failure_status_matches_reference(self):
        steps = (WealthStep(math.inf, 0.0),)
        with self.assertRaises(ControlledNumericalFailure):
            _slow_running_mixture_reference(steps)
        with self.assertRaises(ControlledNumericalFailure):
            self._optimized_tuple(steps)

    def test_58_medium_generated_trajectory_matches_reference(self):
        config = Stage1Config(
            population_size=120,
            budget=80,
            replicates=1,
            scenario_ids=("mixed_fragile_and_stable_failure",),
        )
        population = generate_stage1_population(
            "mixed_fragile_and_stable_failure", 120, 58001, config
        ).population
        arm = {row.conceptual_arm: row for row in stage1_arms(8, .2)}["UP"]
        audit = simulate_named_audit(population, arm, 80, config.ridge, 58002)
        for end in (1, 10, 40, 80):
            with self.subTest(prefix=end):
                self.assert_reference_equivalent(audit["wealth_steps"][:end])

    def test_59_independent_audits_are_execution_order_independent(self):
        config = Stage1Config(
            population_size=50,
            budget=10,
            replicates=1,
            scenario_ids=("low_shared_fragile_mechanism",),
        )
        population = generate_stage1_population(
            "low_shared_fragile_mechanism", 50, 59001, config
        ).population
        arms = {
            row.conceptual_arm: row
            for row in stage1_arms(8, .2)
            if row.conceptual_arm in {"U0", "SP"}
        }
        work_units = tuple(
            (arm_id, stable_seed(59002, "order-independent", arm_id, replicate))
            for arm_id in ("U0", "SP")
            for replicate in range(3)
        )

        def execute(units):
            results = {}
            for arm_id, seed in units:
                audit = simulate_named_audit(
                    population, arms[arm_id], 10, config.ridge, seed
                )
                results[(arm_id, seed)] = (
                    tuple(audit["selection_order"]),
                    audit["errors_observed"],
                    tuple(step.constant_term for step in audit["wealth_steps"]),
                )
            return results

        self.assertEqual(execute(work_units), execute(reversed(work_units)))


class Stage2LeanExecutionTests(unittest.TestCase):
    @staticmethod
    def _population(size=80, budget=30, seed=70001):
        config = Stage1Config(
            population_size=size,
            budget=budget,
            replicates=1,
            scenario_ids=("mixed_fragile_and_stable_failure",),
        )
        population = generate_stage1_population(
            "mixed_fragile_and_stable_failure", size, seed, config
        ).population
        return config, population

    def assert_audits_equivalent(self, replay, lean, tolerance=1e-12):
        self.assertEqual(replay["selection_order"], lean["selection_order"])
        self.assertEqual(replay["errors_observed"], lean["errors_observed"])
        self.assertEqual(replay["warnings"], lean["warnings"])
        self.assertTrue(replay["forensic_replay_performed"])
        self.assertFalse(lean["forensic_replay_performed"])
        self.assertTrue(replay["q_replay_passed"])
        self.assertIsNone(lean["q_replay_passed"])
        scalar_fields = (
            "draw_uniform",
            "selected_item_id",
            "selected_q",
            "minimum_q_at_step",
            "revealed_outcome",
            "expected_control_variate_under_q",
            "u",
            "beta",
            "importance_weight",
            "constant_term",
            "logical_complement_lower",
            "support_term_count",
        )
        for replay_row, lean_row in zip(replay["trace"], lean["trace"]):
            self.assertIsNotNone(replay_row["pre_reveal"])
            self.assertIsNone(lean_row["pre_reveal"])
            for field in scalar_fields:
                left, right = replay_row[field], lean_row[field]
                if isinstance(left, float):
                    self.assertLessEqual(abs(left - right), tolerance, field)
                else:
                    self.assertEqual(left, right, field)
        for replay_step, lean_step in zip(
            replay["wealth_steps"], lean["wealth_steps"]
        ):
            self.assertLessEqual(
                abs(replay_step.constant_term - lean_step.constant_term), tolerance
            )
            self.assertLessEqual(
                abs(
                    replay_step.support_minimum.constant_term
                    - lean_step.support_minimum.constant_term
                ),
                tolerance,
            )
            self.assertEqual(
                replay_step.support_term_count, lean_step.support_term_count
            )
        replay_bound = evaluate_running_mixture_bound(
            replay["wealth_steps"], (.05, .10, .25, .50), .05, 1e-10, 1e-10
        )
        lean_bound = evaluate_running_mixture_bound(
            lean["wealth_steps"], (.05, .10, .25, .50), .05, 1e-10, 1e-10
        )
        self.assertLessEqual(
            abs(replay_bound.upper_error_bound - lean_bound.upper_error_bound),
            1e-10,
        )
        self.assertEqual(
            replay_bound.monotonicity_status, lean_bound.monotonicity_status
        )

    def test_60_all_five_arms_match_replay_grade_path(self):
        config, population = self._population()
        for arm in stage1_arms(8, .2):
            with self.subTest(arm=arm.arm_id):
                seed = stable_seed(70002, arm.arm_id)
                replay = simulate_named_audit(
                    population, arm, 30, config.ridge, seed, "replay_grade"
                )
                lean = simulate_named_audit(
                    population, arm, 30, config.ridge, seed, "lean"
                )
                self.assert_audits_equivalent(replay, lean)

    def test_61_medium_sp_path_matches_replay_grade(self):
        config, population = self._population(500, 200, 71001)
        arm = stage1_arms(8, .2)[-1]
        replay = simulate_named_audit(
            population, arm, 200, config.ridge, 71002, "replay_grade"
        )
        lean = simulate_named_audit(
            population, arm, 200, config.ridge, 71002, "lean"
        )
        self.assert_audits_equivalent(replay, lean)

    def test_62_worker_count_and_completion_order_are_deterministic(self):
        config, population = self._population(60, 20, 72001)
        units = tuple(
            LeanAuditWorkUnit(
                arm.arm_id,
                population,
                arm,
                20,
                config.ridge,
                stable_seed(72002, arm.arm_id),
            )
            for arm in reversed(stage1_arms(8, .2))
        )
        serial = execute_lean_audit_work_units(units, 1)
        parallel = execute_lean_audit_work_units(units, min(4, os.cpu_count() or 1))
        self.assertEqual(serial, parallel)

    def test_63_stage2_design_grid_and_nested_trajectories_are_exact(self):
        config = Stage2Config()
        config.validate()
        cells = stage2_cells(config)
        self.assertEqual(len(cells), 144)
        self.assertEqual({cell.budget for cell in cells}, {50, 100, 200, 500})
        self.assertEqual({cell.pi_h for cell in cells}, {0.0, 0.5, 0.75})
        arms = stage2_trajectory_arms(config)
        self.assertEqual(len(arms), 9)
        self.assertEqual([arm.conceptual_arm for arm in arms[:3]], ["U0", "UM", "UP"])
        self.assertEqual(
            {arm.epsilon_samp for arm in arms if arm.conceptual_arm in {"SM", "SP"}},
            {0.1, 0.2, 0.4},
        )
        with self.assertRaises(ValueError):
            Stage2Config(manifest_type="confirmatory").validate()
        with self.assertRaises(ValueError):
            Stage2Config(replicates=199).validate()
        with self.assertRaises(ValueError):
            Stage2Config(pi_h_values=(0.0, 0.5, 1.0)).validate()

    def test_64_seed_namespaces_and_replay_selection_are_frozen(self):
        config = Stage2Config()
        seeds = {
            config.calibration_master_seed,
            config.negative_control_master_seed,
            config.negative_control_bootstrap_seed,
            config.evaluation_master_seed,
            config.bootstrap_master_seed,
        }
        self.assertEqual(len(seeds), 5)
        replicate = stage2_replay_replicate(config)
        self.assertGreaterEqual(replicate, 0)
        self.assertLess(replicate, config.replicates)
        normalization = Stage2MarginCalibration(3.1, 3.2, .99, 100)
        calibrations = {
            (p_jde, pi_h): Stage2GeneratorParameters(
                p_jde, pi_h, 2.8, 0.01, "primary"
            )
            for p_jde in config.p_jde_targets
            for pi_h in config.pi_h_values
        }
        units = build_stage2_primary_work_units(
            calibrations, normalization, config
        )
        self.assertEqual(len(units), 2400)
        selected = [unit for unit in units if unit.capture_replay_evidence]
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].replicate_id, replicate)
        self.assertEqual(selected[0].parameters.pi_h, 0.75)
        manifest = stage2_manifest(
            config,
            normalization,
            calibrations,
            {
                "gamma_NC": .01,
                "tau_NC": .05,
                "class_bootstrap_q_0_975": {},
            },
            4,
        )
        self.assertTrue(manifest["development_only"])
        self.assertFalse(manifest["confirmatory_manifest"])
        self.assertTrue(manifest["seed_namespaces"]["disjoint"])
        self.assertEqual(manifest["replay_selection_rule"]["pi_H"], 0.75)

    def test_65_margin_calibration_uses_observable_magnitudes(self):
        outputs = tuple(
            ObservableCaseOutputs(
                f"item-{index}", 1, 1, 0.5 + index / 100, 0.6 + index / 100,
                (1,) * 8, (1,) * 8,
            )
            for index in range(100)
        )
        result = calibrate_stage2_margin_normalization(outputs)
        self.assertEqual(result.percentile, .99)
        self.assertEqual(result.observation_count, 100)
        self.assertGreater(result.normalization_primary, .25)
        self.assertGreater(result.normalization_verifier, .25)

    def test_66_risk_calibration_boundary_receives_only_parameters_and_seed(self):
        config = Stage2Config()
        normalization = Stage2MarginCalibration(3.0, 3.0, .99, 10)

        def prevalence_only(parameters, seed, supplied_normalization, supplied_config):
            self.assertIsInstance(parameters, Stage2GeneratorParameters)
            self.assertIsInstance(seed, int)
            self.assertIs(supplied_normalization, normalization)
            self.assertIs(supplied_config, config)
            return max(0.0, (3.0 - parameters.robust_coefficient) * .1)

        with mock.patch(
            "development.statistical_feasibility.scenarios.stage2_prevalence_probe",
            side_effect=prevalence_only,
        ):
            result = calibrate_stage2_risk_parameters(
                .03, .5, (73001, 73002), normalization, config
            )
        self.assertEqual(result.inspected_quantity, "aggregate_true_jde_prevalence_only")
        self.assertEqual(result.calibration_seeds, (73001, 73002))

    def test_67_mandatory_controls_use_only_existing_mechanisms(self):
        base = Stage2GeneratorParameters(.03, .5, 2.8, .01, "primary")
        controls = {
            control_id: stage2_control_parameters(base, control_id)
            for control_id in (
                "pi_h_zero",
                "fragility_unrelated_to_error",
                "stable_shared_false_belief",
                "conditional_permuted_ppi",
                "global_permuted_ppi",
                "constant_ppi",
                "favourable_high_fragility",
            )
        }
        self.assertEqual(controls["pi_h_zero"].pi_h, 0.0)
        self.assertEqual(controls["favourable_high_fragility"].pi_h, 0.75)
        self.assertEqual(controls["constant_ppi"].control_id, "constant_ppi")
        self.assertEqual(
            controls["conditional_permuted_ppi"].control_id,
            "conditional_permuted_ppi",
        )
        self.assertEqual(
            controls["global_permuted_ppi"].control_id,
            "global_permuted_ppi",
        )

    @staticmethod
    def _synthetic_stage2_records(eligible=True):
        config = Stage2Config()
        rows = []
        for p_jde in config.p_jde_targets:
            for budget in config.budgets:
                for pi_h in config.pi_h_values:
                    for replicate in range(config.replicates):
                        shared = {
                            "p_jde_target": p_jde,
                            "pi_H": pi_h,
                            "B": budget,
                            "replicate_id": replicate,
                            "control_id": "primary",
                            "coverage_indicator": eligible,
                            "zero_event": False,
                            "validity_status": "valid",
                            "empty_confidence_set": False,
                        }
                        rows.append({
                            **shared,
                            "conceptual_arm": "UP",
                            "epsilon_samp": None,
                            "final_upper_bound": .5 if eligible else 1.0,
                        })
                        for epsilon in config.epsilon_values:
                            rows.append({
                                **shared,
                                "conceptual_arm": "SP",
                                "epsilon_samp": epsilon,
                                "final_upper_bound": .4 if eligible else 1.0,
                            })
        return rows

    def test_68_eligibility_precedes_delta_and_preserves_every_cell(self):
        eligible = summarize_stage2_cells(self._synthetic_stage2_records(True))
        self.assertEqual(len(eligible), 144)
        self.assertTrue(all(row["eligible"] for row in eligible))
        self.assertTrue(all(abs(row["Delta_cell"] - .2) < 1e-12 for row in eligible))
        self.assertAlmostEqual(aggregate_stage2_delta(eligible), .2)
        ineligible = summarize_stage2_cells(self._synthetic_stage2_records(False))
        self.assertEqual(len(ineligible), 144)
        self.assertTrue(all(not row["eligible"] for row in ineligible))
        self.assertTrue(all(row["Delta_cell"] is None for row in ineligible))
        self.assertTrue(all(row["exclusion_reasons"] for row in ineligible))

    def test_69_negative_control_and_symmetric_classification(self):
        config = Stage2Config()
        cells_by_class = {}
        for control_id in (
            "pi_h_zero",
            "conditional_permuted_ppi",
            "global_permuted_ppi",
            "constant_ppi",
        ):
            cells_by_class[control_id] = [
                {
                    "cell_id": f"{control_id}-{epsilon}-{budget}",
                    "replicate_ids": tuple(range(config.replicates)),
                    "effective_UP": (0.5,) * config.replicates,
                    "effective_SP": (0.49,) * config.replicates,
                    "G_cell": 0.02,
                }
                for epsilon in config.epsilon_values
                for budget in config.budgets
            ]
        gamma = empirical_gamma_nc(cells_by_class, config)
        self.assertAlmostEqual(gamma["gamma_NC"], .02)
        self.assertEqual(set(gamma["class_bootstrap_q_0_975"]), set(cells_by_class))
        self.assertEqual(gamma["bootstrap_replicates"], 10_000)
        cells = self._synthetic_stage2_records(True)
        summaries = summarize_stage2_cells(cells)
        self.assertEqual(
            classify_stage2_development(summaries, .02, .03),
            "POSITIVE_DEVELOPMENT_LEVEL",
        )
        self.assertEqual(
            classify_stage2_development(summaries, .02, .01),
            "INCONCLUSIVE",
        )
        self.assertEqual(
            classify_stage2_development(summaries, .051, .2),
            "INVALID_DEVELOPMENT_SWEEP",
        )

    def test_70_preflight_plan_consumes_no_evaluation_or_bootstrap_namespace(self):
        config = Stage2Config()
        plan = stage2_preflight_plan(config)
        self.assertEqual(
            plan["not_consumed_seed_namespaces"], ["evaluation", "bootstrap"]
        )
        normalization = Stage2MarginCalibration(3.0, 3.0, .99, 10)
        parameters = Stage2GeneratorParameters(.03, .5, 2.5, 0.0, "primary")
        calibration_units = build_stage2_control_work_units(
            parameters,
            normalization,
            plan["negative_control_calibration"]["control_ids"],
            1,
            "negative_control_calibration",
            config,
        )
        preflight_units = build_stage2_control_work_units(
            parameters,
            normalization,
            plan["additional_control_preflight"]["control_ids"],
            1,
            "negative_control_preflight",
            config,
        )
        self.assertEqual(
            {unit.audit_seed_namespace for unit in calibration_units},
            {"negative_control_calibration"},
        )
        self.assertEqual(
            {unit.audit_seed_namespace for unit in preflight_units},
            {"negative_control_preflight"},
        )
        self.assertEqual(
            {_stage2_audit_seed_master(unit) for unit in (*calibration_units, *preflight_units)},
            {config.negative_control_master_seed},
        )
        self.assertNotIn(
            config.evaluation_master_seed,
            {unit.population_seed for unit in (*calibration_units, *preflight_units)},
        )

    def test_71_preflight_plan_is_exactly_the_frozen_stage2_configuration(self):
        config = Stage2Config()
        plan = stage2_preflight_plan(config)
        expected = {
            key: value
            for key, value in config.__dict__.items()
            if key != "bootstrap_master_seed"
        }
        expected["bootstrap_master_seed_status"] = "reserved_not_consumed"
        expected["development_primary_bootstrap_seed"] = (
            stage2_development_primary_bootstrap_seed(config)
        )
        self.assertEqual(plan["configuration"], expected)
        self.assertEqual(plan["negative_control_calibration"]["replicates_per_control"], 200)
        self.assertEqual(plan["additional_control_preflight"]["replicates_per_control"], 5)
        self.assertEqual(
            plan["negative_control_calibration"]["anchor"],
            {"p_jde_target": .03, "pi_H": .5},
        )
        self.assertFalse(plan["full_stage2_evaluation_executed"])

    def test_72_preflight_cli_requires_explicit_safe_options(self):
        output_directory = Path(tempfile.gettempdir()) / "stage2-preflight-cli-test-output"
        with mock.patch(
            "development.statistical_feasibility.run.run_stage2_preflight",
            return_value={"mode": "stage2_preflight"},
        ) as preflight:
            self.assertEqual(
                run_main(
                    [
                        "--stage2-preflight",
                        "--workers",
                        "2",
                        "--output-dir",
                        str(output_directory),
                    ]
                ),
                0,
            )
        self.assertEqual(preflight.call_args.args, (output_directory, 2))
        with self.assertRaises(SystemExit) as missing_workers:
            run_main(["--stage2-preflight", "--output-dir", str(output_directory)])
        self.assertEqual(missing_workers.exception.code, 2)
        with self.assertRaises(SystemExit) as invalid_workers:
            run_main(
                [
                    "--stage2-preflight",
                    "--workers",
                    "0",
                    "--output-dir",
                    str(output_directory),
                ]
            )
        self.assertEqual(invalid_workers.exception.code, 2)

    @staticmethod
    def _control_results(control_id="conditional_permuted_ppi", invalid_rows=()):
        invalid_rows = set(invalid_rows)
        config = Stage2Config()
        results = []
        for replicate in range(config.replicates):
            rows = []
            for budget in config.budgets:
                for arm, epsilon, bound in (
                    ("UP", None, .5),
                    ("SP", .1, .45),
                    ("SP", .2, .44),
                    ("SP", .4, .43),
                ):
                    invalid = (replicate, budget, arm, epsilon) in invalid_rows
                    rows.append({
                        "control_id": control_id,
                        "replicate_id": replicate,
                        "B": budget,
                        "conceptual_arm": arm,
                        "epsilon_samp": epsilon,
                        "final_upper_bound": None if invalid else bound,
                        "validity_status": "invalid_numerical" if invalid else "valid",
                        "empty_confidence_set": False,
                        "coverage_indicator": not invalid,
                        "monotonicity_status": "passed",
                        "support_status": "passed",
                        "warnings": ["forced invalid"] if invalid else [],
                    })
            results.append({"unit_id": f"control-{control_id}-r{replicate:04d}", "rows": rows})
        return results

    def test_73_empty_control_bound_uses_effective_one_without_overwrite(self):
        record = {
            "final_upper_bound": None,
            "validity_status": "empty_confidence_set",
            "empty_confidence_set": True,
            "coverage_indicator": False,
        }
        self.assertEqual(effective_upper_bound(record), 1.0)
        self.assertIsNone(record["final_upper_bound"])
        self.assertFalse(record["coverage_indicator"])
        valid = {**record, "final_upper_bound": .4, "validity_status": "valid", "empty_confidence_set": False}
        self.assertEqual(effective_upper_bound(valid), .4)

    def test_74_genuine_blockers_are_all_preserved(self):
        invalid = {
            (17, 500, "SP", .1),
            (18, 200, "UP", None),
        }
        with self.assertRaises(Stage2ControlBoundFailure) as raised:
            _stage2_control_g_values(
                self._control_results(invalid_rows=invalid),
                ("conditional_permuted_ppi",),
                Stage2Config(),
            )
        record = raised.exception.failure_record
        self.assertEqual(record["blocking_row_count"], 2)
        self.assertEqual(len(record["blocking_rows"]), 2)
        self.assertTrue(all(not row["empty_confidence_set"] for row in record["blocking_rows"]))

    def test_75_control_g_is_ratio_of_means_and_keeps_epsilon_axis(self):
        results = self._control_results()
        results[0]["rows"][0]["final_upper_bound"] = .2
        results[0]["rows"][1]["final_upper_bound"] = .1
        cells = _stage2_control_g_values(
            results, ("conditional_permuted_ppi",), Stage2Config()
        )["conditional_permuted_ppi"]
        self.assertEqual(len(cells), 12)
        target = next(cell for cell in cells if cell["B"] == 50 and cell["epsilon_samp"] == .1)
        expected = 1.0 - sum(target["effective_SP"]) / sum(target["effective_UP"])
        self.assertAlmostEqual(target["G_cell"], expected)
        mean_ratios = sum(
            1.0 - sp / up
            for up, sp in zip(target["effective_UP"], target["effective_SP"])
        ) / 200
        self.assertNotAlmostEqual(target["G_cell"], mean_ratios)

    def test_76_type7_and_structural_degeneracy_rules(self):
        self.assertEqual(type7_percentile((0.0, 10.0), .25), 2.5)
        summaries = summarize_stage2_cells(self._synthetic_stage2_records(True))
        self.assertTrue(stage2_structural_representation_complete(summaries))
        summaries[0]["eligible"] = False
        summaries[1]["eligible"] = False
        summaries[2]["eligible"] = False
        self.assertFalse(stage2_structural_representation_complete(summaries))
        self.assertIsNone(aggregate_stage2_delta(summaries))
        self.assertEqual(
            classify_stage2_development(summaries, .01, .2),
            "INCONCLUSIVE_BY_DEGENERACY",
        )

    def test_77_global_permutation_is_observable_only_and_preserves_multiset(self):
        items = tuple(
            ObservableScoreItem(
                f"item-{index}",
                (("ppi_k8", index / 8), ("ppi_k4", (index % 5) / 4), ("confidence_margin", .5)),
            )
            for index in range(9)
        )
        left = permute_ppi_globally(items, 123)
        right = permute_ppi_globally(items, 123)
        self.assertEqual(left, right)
        self.assertEqual(
            sorted(item.scores()["ppi_k8"] for item in left),
            sorted(item.scores()["ppi_k8"] for item in items),
        )
        self.assertEqual(
            [item.scores()["confidence_margin"] for item in left],
            [item.scores()["confidence_margin"] for item in items],
        )

    def test_78_calibration_and_nc_are_independent_of_reserved_future_seeds(self):
        normalization = Stage2MarginCalibration(3.0, 3.0, .99, 10)
        parameters = Stage2GeneratorParameters(.03, .5, 2.8, 0.0, "conditional_permuted_ppi")
        seed = 81234
        first = generate_stage2_population(parameters, seed, normalization, Stage2Config())
        second = generate_stage2_population(
            parameters,
            seed,
            normalization,
            Stage2Config(evaluation_master_seed=91, bootstrap_master_seed=92),
        )
        self.assertEqual(first.population, second.population)
        self.assertEqual(first.observable_outputs, second.observable_outputs)
        config = Stage2Config()
        self.assertEqual(
            config.negative_control_bootstrap_seed,
            stable_seed(config.negative_control_master_seed, "negative-control-bootstrap"),
        )

    def test_79_empty_replicate_remains_in_control_cell_means(self):
        results = self._control_results()
        target = next(
            row
            for row in results[0]["rows"]
            if row["B"] == 50 and row["conceptual_arm"] == "SP" and row["epsilon_samp"] == .1
        )
        target.update(
            final_upper_bound=None,
            validity_status="empty_confidence_set",
            empty_confidence_set=True,
            coverage_indicator=False,
        )
        cell = next(
            cell
            for cell in _stage2_control_g_values(
                results, ("conditional_permuted_ppi",), Stage2Config()
            )["conditional_permuted_ppi"]
            if cell["B"] == 50 and cell["epsilon_samp"] == .1
        )
        self.assertEqual(len(cell["effective_SP"]), 200)
        self.assertEqual(cell["effective_SP"][0], 1.0)

    def test_80_one_bootstrap_index_vector_is_shared_across_class_cells(self):
        config = Stage2Config()
        object.__setattr__(config, "negative_control_bootstrap_replicates", 1)
        base = {
            "replicate_ids": tuple(range(200)),
            "effective_UP": tuple(.5 + index / 1000 for index in range(200)),
            "effective_SP": tuple(.4 + index / 2000 for index in range(200)),
        }
        cells = {
            control_id: [
                {
                    **base,
                    "cell_id": f"{control_id}-{epsilon}-{budget}",
                    "G_cell": 1.0 - sum(base["effective_SP"]) / sum(base["effective_UP"]),
                }
                for epsilon in config.epsilon_values
                for budget in config.budgets
            ]
            for control_id in (
                "pi_h_zero",
                "conditional_permuted_ppi",
                "global_permuted_ppi",
                "constant_ppi",
            )
        }
        with mock.patch.object(Stage2Config, "validate", return_value=None):
            result = empirical_gamma_nc(cells, config)
        self.assertEqual(result["bootstrap_replicates"], 1)
        self.assertEqual(len(result["class_bootstrap_q_0_975"]), 4)

    def test_81_empty_rate_hold_gate_remains_separate_from_eligibility(self):
        summaries = summarize_stage2_cells(self._synthetic_stage2_records(True))
        self.assertEqual(
            classify_stage2_development(summaries, .01, .2, .051),
            "IMPLEMENTATION_FAILURE_HOLD",
        )

    def test_82_primary_bootstrap_uses_twelve_canonical_generator_strata(self):
        config = Stage2Config()
        worlds = list(_iter_stage2_primary_bootstrap_worlds(config, 2))
        self.assertEqual(len(worlds), 2)
        expected_strata = tuple(
            sorted(
                (p_jde, pi_h)
                for p_jde in config.p_jde_targets
                for pi_h in config.pi_h_values
            )
        )
        self.assertEqual(stage2_generator_strata(config), expected_strata)
        self.assertEqual(
            tuple(stratum for stratum, _ in worlds[0].stratum_indices),
            expected_strata,
        )
        self.assertTrue(
            all(len(indices) == config.replicates for _, indices in worlds[0].stratum_indices)
        )
        rng = random.Random(stage2_development_primary_bootstrap_seed(config))
        expected_first = tuple(rng.randrange(config.replicates) for _ in range(config.replicates))
        self.assertEqual(worlds[0].stratum_indices[0][1], expected_first)

    def test_83_primary_bootstrap_preserves_nested_and_arm_pairing(self):
        records = self._synthetic_stage2_records(True)
        summaries = summarize_stage2_cells(records)
        result = bootstrap_stage2_primary_statistics(
            records, summaries, _bounded_bootstrap_replicates=3
        )
        self.assertEqual(result["status"], "INTERPRETABLE")
        self.assertAlmostEqual(result["Delta_bar"], .2)
        self.assertAlmostEqual(result["Delta_bar_minus"], .2)
        self.assertEqual(result["generator_stratum_count"], 12)
        self.assertTrue(result["shared_delta_and_pooled_empty_worlds"])
        self.assertEqual(len(result["eligible_cell_ids"]), 144)
        self.assertEqual(result["pooled_empty_rate"], 0.0)

    def test_84_primary_bootstrap_freezes_point_eligibility_mask(self):
        records = self._synthetic_stage2_records(True)
        summaries = summarize_stage2_cells(records)
        omitted = [
            row
            for row in summaries
            if row["p_jde_target"] == .003 and row["B"] == 50 and row["pi_H"] == 0.0
        ]
        self.assertEqual(len(omitted), 3)
        for row in omitted:
            row["eligible"] = False
            row["Delta_cell"] = None
        result = bootstrap_stage2_primary_statistics(
            records, summaries, _bounded_bootstrap_replicates=2
        )
        self.assertEqual(result["status"], "INCONCLUSIVE_BY_DEGENERACY")
        self.assertIsNone(result["Delta_bar"])
        self.assertTrue(
            all(row["cell_id"] not in result["eligible_cell_ids"] for row in omitted)
        )

    def test_85_reserved_bootstrap_seed_cannot_change_development_bootstrap(self):
        records = self._synthetic_stage2_records(True)
        summaries = summarize_stage2_cells(records)
        first_config = Stage2Config()
        second_config = Stage2Config(
            bootstrap_master_seed=first_config.bootstrap_master_seed + 997
        )
        first = bootstrap_stage2_primary_statistics(
            records, summaries, first_config, _bounded_bootstrap_replicates=2
        )
        second = bootstrap_stage2_primary_statistics(
            records, summaries, second_config, _bounded_bootstrap_replicates=2
        )
        self.assertEqual(
            json.dumps(first, sort_keys=True, separators=(",", ":")),
            json.dumps(second, sort_keys=True, separators=(",", ":")),
        )
        self.assertNotIn(
            "seed", inspect.signature(bootstrap_stage2_primary_statistics).parameters
        )

    def test_86_primary_manifest_omits_reserved_seed_value(self):
        config = Stage2Config()
        changed = Stage2Config(bootstrap_master_seed=config.bootstrap_master_seed + 997)
        normalization = Stage2MarginCalibration(3.1, 3.2, .99, 100)
        calibrations = {
            stratum: Stage2GeneratorParameters(stratum[0], stratum[1], 2.8, 0.0, "primary")
            for stratum in stage2_generator_strata(config)
        }
        first = stage2_primary_map_manifest(config, normalization, calibrations, 2, {"head": "abc"})
        second = stage2_primary_map_manifest(changed, normalization, calibrations, 2, {"head": "abc"})
        self.assertEqual(first, second)
        self.assertEqual(
            first["seed_namespaces"]["confirmatory_bootstrap"],
            "reserved_not_consumed",
        )
        self.assertEqual(first["primary_bootstrap"]["generator_stratum_count"], 12)

    def test_87_primary_cli_exposes_only_execution_controls(self):
        output_directory = Path(tempfile.gettempdir()) / "stage2-primary-cli-test-output"
        with mock.patch(
            "development.statistical_feasibility.run.run_stage2_primary_map",
            return_value={"mode": "stage2_primary_map"},
        ) as primary:
            self.assertEqual(
                run_main(
                    [
                        "--stage2-primary-map",
                        "--workers",
                        "2",
                        "--output-dir",
                        str(output_directory),
                    ]
                ),
                0,
            )
        self.assertEqual(primary.call_args.args, (output_directory, 2))
        with self.assertRaises(SystemExit) as scientific_knob:
            run_main(
                [
                    "--stage2-primary-map",
                    "--workers",
                    "2",
                    "--output-dir",
                    str(output_directory),
                    "--p-jde",
                    "0.03",
                ]
            )
        self.assertEqual(scientific_knob.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
