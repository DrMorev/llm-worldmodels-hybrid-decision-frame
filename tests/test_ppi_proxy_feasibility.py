"""Stage 1 PPI plumbing tests. All fixtures and conclusions are development-only."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from development.statistical_feasibility.betting import (
    WealthStep,
    bisect_mixture_lower_bound,
    log_mixture_wealth,
    stable_logsumexp,
    verify_mixture_monotonicity,
)
from development.statistical_feasibility.core import (
    STAGE1_SCENARIOS,
    Stage1Config,
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
    replay_artifact,
    retain_stage1_trace,
    run_ppi_stage1,
    simulate_named_audit,
)
from development.statistical_feasibility.sampling import policy_probabilities
from development.statistical_feasibility.scenarios import (
    STAGE1_SCENARIO_SPECS,
    generate_stage1_population,
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


if __name__ == "__main__":
    unittest.main()
