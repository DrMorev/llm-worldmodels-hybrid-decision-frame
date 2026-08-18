"""Stage 1 PPI plumbing tests. All fixtures and conclusions are development-only."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
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
    Stage1Config,
    stable_seed,
    stage1_arms,
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
    _lambda_grid_digest,
    replay_artifact,
    retain_stage1_trace,
    run_ppi_stage1,
    simulate_named_audit,
)
from development.statistical_feasibility.sampling import policy_probabilities
from development.statistical_feasibility.scenarios import (
    STAGE1_ACCEPTANCE_CHECK_SEEDS,
    STAGE1_SCENARIO_SPECS,
    generate_stage1_population,
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


if __name__ == "__main__":
    unittest.main()
