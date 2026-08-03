# Development-only statistical feasibility prototype

This directory is disposable development machinery. Its synthetic fixtures,
seeds, outputs, and summaries are **not confirmatory evidence**. They do not
show that perturbation instability is useful, do not show that directed
auditing outperforms uniform auditing, and do not select a final endpoint,
budget, or confirmatory parameter.

The implementation uses only the Python standard library and supports four
arms on the same immutable finite population:

1. uniform sampling without a control variate;
2. uniform sampling with a control variate;
3. score-informed sampling without a control variate;
4. score-informed sampling with a control variate.

For remaining set `R`, uniform sampling assigns `1 / len(R)`. The
development-only score policy assigns

```text
q(i) = gamma / len(R) + (1 - gamma) * S(i) / sum(S(j) for j in R).
```

If the score sum is zero, it uses uniform sampling. This policy is not called
`prop-MS`, and no performance guarantee is inherited from the paper. Sampling
functions receive item IDs and observable scores, never the hidden outcome
vector.

## Control variate

Before draw `t`, the code computes

```text
U_t = S(I_t) - sum(q_t(i) * S(i) for i in R_t).
```

`beta` is zero until three earlier `(Z, U)` pairs exist. Thereafter, for `n`
strictly prior observations, the prototype uses population-moment definitions

```text
mean_Z = sum(Z_k) / n
mean_U = sum(U_k) / n
Cov_past(Z,U) = sum((Z_k - mean_Z) * (U_k - mean_U)) / n
Var_past(U)   = sum((U_k - mean_U)**2) / n
beta_t = clip(-Cov_past(Z,U) / (Var_past(U) + ridge), -1, 1).
```

An undefined or non-finite calculation falls back to zero and emits a warning.
This is a predictable development candidate, not a preregistered choice.

## One-sided upper bound and fixed betting family

The upper bound for dangerous-error prevalence is constructed through the
complement `g_i = 1 - y_i`. Positive fixed bets produce a lower confidence
bound `L_g` for the complement mean. The reported dangerous-error upper bound
is exactly

```text
U_y = 1 - L_g.
```

No simultaneous two-sided coverage is claimed. Smoke-test fixed bet values are
`0.05`, `0.10`, `0.25`, and `0.50`. Each multiplier is checked for finiteness
and nonnegativity. Log wealth must be nonincreasing in candidate complement
mean. A deterministic bisection on `[0, 1]` with tolerance `1e-10` performs the
inversion; this is intersected with the logical finite-population lower bound
and a running intersection.

## Fixtures

All fixtures are explicit synthetic development stress tests:

- `constant_score`: score `0.5`, outcome probability `0.10`;
- `independent_score`: independent uniform score and outcome probability `0.10`;
- `informative_score`: constructed favourable case with outcome probability
  `0.02 + 0.46 * score`;
- `anti_informative_score`: constructed adverse case with outcome probability
  `0.02 + 0.46 * (1 - score)`;
- `tied_score`: five score levels and outcome probability `0.10`;
- `all_correct`: all outcomes are zero;
- `all_error`: all outcomes are one.

Every fixture uses local `random.Random` instances derived from development
master seed `20260803`. No module-global RNG is used.

## Run

From the repository root:

```text
python -B -m unittest discover -s tests -p "test_statistical_feasibility.py" -v
python -B -m development.statistical_feasibility.run --smoke
python -B -m compileall development/statistical_feasibility tests/test_statistical_feasibility.py
```

Smoke defaults are `N=200`, `B=50`, audit risk `0.05`, 50 replicates per
ordinary stochastic fixture, gamma values `0.10` and `0.50`, ridge `1e-6`, and
the four fixed lambda values above. These are development defaults, not
confirmatory selections.

The four entries above are conceptual arms.  Their machine identifiers are
unique instantiated configurations: the score-informed entries include gamma
in the identifier (for example, `C_score_no_cv_gamma_0p1`).  Thus the smoke
run instantiates six configurations, not six scientific factors.

By default, `results.json`, `summary.csv`, and `report.txt` are written to a
new operating-system temporary directory outside the repository. JSON records
the full development populations, independently derived arm RNG seeds, and
per-step pre-reveal records: ordered remaining IDs and scores, policy, gamma,
normalization inputs, the full ordered `q_t` vector, one pre-reveal uniform
draw variate, and selected ID and probability. Replay uses only those
serialized values to reconstruct every vector and selection; matching only
the selected probability is not accepted. A digest is an additional integrity
field, not a substitute for that reconstruction.

`selection_order` and `selected_item_ids_in_selection_order` mean the actual
chronological draw sequence. They are not derived from set iteration.

The full smoke run is a development audit run, not a quick unit test. It may
take several minutes because it enumerates support-wide payoffs, and its JSON
artifact may exceed 100 MB. Process exit code `0` means the development run
completed; it does not mean estimator coverage passed a scientific or
preregistered gate. Empty confidence sets remain coverage failures in their
coverage denominators even though their numeric bounds are null and excluded
from valid-bound mean and median summaries.

The report's `records_with_multiplier_failure` is a count of result records
with a detected support-admissibility multiplier failure; its denominator is
the group's number of runs. It is not a count of individual negative factors.

## Empty confidence sets and support-wide admissibility

An empty inverted confidence set is not converted into a numeric bound. The
machine record uses `validity_status=empty_confidence_set`,
`coverage_indicator=false`, and `final_upper_confidence_bound=null`. Summary
mean and median bounds include only records with `validity_status=valid`; empty
sets are counted and reported separately. An empty-CS count is a statistical
coverage-event counter, not by itself an engineering process failure.

For each fixed lambda and every candidate complement mean evaluated during
monotonicity checks or bisection, the implementation checks

```text
1 + lambda * modified_payoff >= -1e-10
```

for every remaining item and both possible binary outcomes before accepting
the candidate. The support terms use the actual `q_t`, score, centred CV term,
and predictable beta. A value below this documented tolerance invalidates that
lambda configuration and records the step, item, outcome, candidate mean, and
multiplier. A negative value within tolerance is represented as exact zero
solely to make logarithms numerically well-defined.

The implementation enumerates the full support once per step. Because lambda
is positive and all support multipliers have the same candidate mean, the
smallest enumerated payoff is the worst factor for every candidate evaluated
later; retaining that item/outcome and the full support count makes repeated
inversion checks exact rather than a realised-path shortcut.

## Statistical basis and attribution

Shubhanshu Shekhar, Ziyu Xu, Zachary Lipton, Pierre Liang, and Aaditya Ramdas.
“Risk-limiting Financial Audits via Weighted Sampling without Replacement.”
Proceedings of the Thirty-Ninth Conference on Uncertainty in Artificial
Intelligence, PMLR 216:1932–1941, 2023.

Official record: <https://proceedings.mlr.press/v216/shekhar23a.html>

From that paper, this prototype uses the general statistical ingredients of
finite-population adaptive randomized sampling without replacement,
importance-weighted observations, betting-based wealth, confidence-sequence
inversion, finite-population logical bounds, and centred control variates.

This project specializes those ingredients to a binary joint-dangerous-error
outcome, uniform population weights, and the complement transformation
`g_i = 1 - y_i` for reporting a one-sided upper bound.

The paper does not establish this prototype's development-only choices: gamma
mixture values or exact score-informed policy, the fixed-lambda candidate grid,
the concrete beta estimator/clipping/ridge/history rule, deterministic
bisection implementation, synthetic fixtures, or its reporting and replay
schema. No novelty is claimed for the statistical construction. The paper does
not guarantee benefit from this project's score-informed policy; usefulness is
empirical and unresolved.
