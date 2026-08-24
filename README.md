# Audit the Verifier

When agreement is not independent evidence

This repository specializes existing finite-population audit machinery to a synthetic primary-model/verifier setting and publishes a reproducible development-stage case around joint dangerous-error estimation inside the confident-agreement region under a fixed oracle budget.

The designated oracle-free proxy did not advance: the frozen 48-of-48 structural-representation gate left the aggregate advancement statistic undefined (`INCONCLUSIVE_BY_DEGENERACY`).

The project does not claim a new statistical method, a novel theory of correlated AI failure, or evidence that directed auditing improves verifier-risk estimation.

## Status

**Development-terminal research artifact**

**C-03: `INCONCLUSIVE_BY_DEGENERACY`**

**No confirmatory result exists.**

C-03 was a development-only execution. No confirmatory preregistration was committed, no confirmatory experiment occurred, and the result is neither an invalid run nor an official negative result. The selected proxy did not satisfy the prospective conditions required to advance into preregistration, so it does not advance in this phase.

## The problem

A primary model can produce an answer or action while a verifier also appears to support it. The operational question is not simply whether the two outputs agree. It is whether their agreement supplies enough independent evidence to justify a particular level of authority.

Shared training data, common evidence, similar representations, or common failure mechanisms can make agreement redundant rather than independent. Two components can therefore agree confidently and still be jointly wrong. This premise is established in adjacent reliability and evaluation literature; the repository does not claim to have discovered it.

The project studies the narrower problem of estimating joint dangerous-error risk among cases where the primary model and verifier already agree confidently. An oracle review reveals whether an audited case is jointly dangerous, but the oracle budget is fixed and smaller than the population.

## Research question

Within cases where the primary model and verifier confidently agree, can a preregistered oracle-free audit strategy improve estimation of their joint dangerous-error risk at a fixed oracle budget compared with random auditing?

The project did not reach the confirmatory stage required to answer this question. C-03 evaluated whether the designated development proxy and frozen design were ready to advance toward preregistration.

## Why this became a statistical auditing problem

The repository began with broad architectural framing. The research question was progressively narrowed from architecture choice to the evidential relationship between a primary component and its verifier, then to authority under possible shared error, and finally to estimation of joint dangerous-error risk inside a finite confident-agreement population.

Once oracle review was treated as scarce, the central comparison became statistical: at the same fixed oracle budget, compare random auditing with auditing guided only by information observable before oracle reveal. The target is valid upper-risk estimation, not merely finding more errors. A policy that discovers errors quickly can still produce unstable or uninformative risk bounds.

## Method lineage

The core finite-population adaptive-sampling, importance-weighting, control-variate, and betting-confidence machinery is inherited. No novelty is claimed for that statistical construction. In particular, the implementation follows the finite-population weighted-sampling lineage represented by Shekhar et al. and is adjacent to active-testing work on sample-efficient evaluation.

This project specializes existing machinery to binary joint dangerous-error risk, uniform population weights, complement-based one-sided upper bounds, a synthetic primary-model/verifier setting, and project-specific observable score hypotheses. The source methods do not guarantee that this project's score-informed policy improves estimation.

The principal development score was a paired perturbation-instability score (repository-internal identifier `PPI`; unrelated to prediction-powered inference). It measures instability of original primary/verifier agreement under a frozen bank of structurally label-preserving transformations. The score uses no oracle label or hidden mechanism field. A confidence-margin score served as a low-cost baseline.

## What was tested

The development experiment used:

* a synthetic generator with known ground truth;
* a finite population restricted to confident primary/verifier agreement;
* a hidden binary joint-dangerous-error outcome;
* observable oracle-free perturbation and confidence-margin scores;
* uniform/random and score-informed without-replacement sampling arms;
* fixed oracle budgets;
* importance-weighted, control-variate, and anytime-valid upper-risk machinery;
* common equal-weight lambda mixtures;
* negative and falsification controls;
* prospective coverage, zero-event, and structural-representation gates.

The scientific comparison was frozen before C-03. Every one of 48 scientific strata had to contain at least one eligible exploration configuration before the aggregate development statistic could be interpreted. This all-or-nothing rule prevented selective interpretation of only convenient regions of the map.

## C-03 result

**Official result: `INCONCLUSIVE_BY_DEGENERACY`**

| Quantity | C-03 value |
|---|---:|
| `population_count` | 2400 |
| `cell_count` | 144 |
| `scientific_stratum_count` | 48 |
| Eligible cells | 108 |
| Ineligible cells | 36 |
| Represented scientific strata | 36 / 48 |
| Unrepresented scientific strata | 12 / 48 |
| `Delta_bar` | undefined |
| `Delta_bar_minus` | undefined |

All 36 ineligible cells failed solely:

`zero_event_proportion_above_0.50`

The 12 unrepresented strata were exactly:

* `p_JDE = 0.01`, `B = 50`, all `pi_H`;
* `p_JDE = 0.003`, `B in {50, 100, 200}`, all `pi_H`.

The frozen 48-of-48 structural-representation gate fired before the aggregate advancement statistic became defined. No official aggregate over only the 108 eligible cells is authorized. The result is not `NEGATIVE`, and C-03 did not answer the canonical research question.

## Descriptive development evidence

**DESCRIPTIVE — NOT THE OFFICIAL AGGREGATE**

Among the 108 eligible cells:

* 97 `Delta_cell` values were negative;
* 11 were positive;
* 0 were zero;
* mean: `-1.3933676212689903`;
* median: `-1.3402708473419773`;
* range: `[-4.814389234158471, 0.015690285931822645]`.

Empty confidence sets across all 144 cells were:

* UP: `0`;
* SP: `271`.

The eligible portion of the development map was descriptively adverse to the paired perturbation-instability path. The SP-only empty-confidence-set pattern is consistent with variance inflation in the implemented importance-weighted score-informed sampling procedure.

These observations do not show that directed auditing generally fails, that score-informed auditing generally fails, or that paired perturbation instability is generally ineffective. They do not replace the undefined official aggregate.

## A second result: decision reachability

C-03 also exposed a process lesson about experimental informativeness. For a baseline sample of size `B` and event prevalence `p`, an elementary approximation is:

```text
P(K = 0) ≈ (1 - p)^B
```

Applied before an expensive run, this operating-characteristics check could have identified the low-prevalence, small-budget region as strongly prone to exclusion by the zero-event gate. Because the design required representation of all 48 scientific strata, those upstream exclusions prevented the experiment from reaching its downstream aggregate decision rule.

This lesson was identified after C-03 evidence existed. It demonstrates that the failure mechanism was prospectively detectable; it does not constitute prospective validation of a later decision-reachability review contour. Method validity and design informativeness are separate review surfaces. The arithmetic is an established operating-characteristics tool, not a statistical discovery made by this repository.

## Related work and positioning

The release position is deliberately bounded. This is a specialization and method-transfer stress test, not a firstness claim. Prior work establishes the relevant statistical, reliability, active-evaluation, inference, and correlated-judge context; citing it does not validate this repository.

1. Shubhanshu Shekhar, Ziyu Xu, Zachary Lipton, Pierre Liang, and Aaditya Ramdas. [“Risk-limiting financial audits via weighted sampling without replacement.”](https://proceedings.mlr.press/v216/shekhar23a.html) UAI 2023, PMLR 216:1932–1941. Peer reviewed.
2. John C. Knight and Nancy G. Leveson. [“An Experimental Evaluation of the Assumption of Independence in Multiversion Programming.”](https://doi.org/10.1109/TSE.1986.6312924) *IEEE Transactions on Software Engineering*, SE-12(1):96–109, 1986. Peer reviewed.
3. Jannik Kossen, Sebastian Farquhar, Yarin Gal, and Tom Rainforth. [“Active Testing: Sample-Efficient Model Evaluation.”](https://proceedings.mlr.press/v139/kossen21a.html) ICML 2021, PMLR 139:5753–5763. Peer reviewed.
4. Anastasios N. Angelopoulos, Stephen Bates, Clara Fannjiang, Michael I. Jordan, and Tijana Zrnic. [“Prediction-powered inference.”](https://doi.org/10.1126/science.adi6000) *Science* 382(6671):669–674, 2023. Peer reviewed. This established adjacent use of “PPI” is distinct from this repository's perturbation-score identifier.
5. Jitian Zhao, Changho Shin, Tzu-Heng Huang, Satya Sai Srinath Namburi GNVV, and Frederic Sala. [“CARE: Confounder-Aware Aggregation for Reliable LLM Evaluation.”](https://arxiv.org/abs/2603.00039) arXiv:2603.00039, 2026. The title also appears on the official ICML 2026 download listing; this release cites it conservatively as a 2026 work/arXiv paper.
6. Guneet Kohli. [“Nine Judges, Two Effective Votes: Correlated Errors Undermine LLM Evaluation Panels.”](https://arxiv.org/abs/2605.29800) arXiv:2605.29800, 2026. Preprint.

## Reproduce / inspect

Two environments must be kept distinct.

**Historical C-03 execution environment:** Python `3.11.15`. This is historical execution evidence.

**R-01 public-command validation environment:** Python `3.14.6`.

The public inspection commands validated during R-01 are:

```bash
python -B -m unittest discover -s tests -v
python -B -m compileall development tests
python -B -m development.statistical_feasibility.run --smoke
```

The unit-test command is the lightweight ordinary inspection path. The `--smoke` command is optional and not lightweight: under Python `3.14.6`, it took approximately 8.5 minutes and wrote approximately 1.36 GB of temporary output during R-01 validation. These observed figures are not runtime or storage guarantees. The smoke command uses an OS temporary directory by default and does not write generated evidence into the repository. Full C-03 execution is substantially more expensive and is not required for ordinary inspection. See [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) for the historical command, environment separation, artifact hashes, and verification guidance.

## What this repository does not establish

This repository establishes none of the following:

* a confirmatory result;
* real-world or real-domain validation;
* a deployment-ready verifier;
* proof that paired perturbation instability is useful;
* proof that directed auditing is generally better or worse;
* general authority thresholds for Advisory, Blocking, or Authorization;
* a new statistical method;
* a novel theory of correlated AI failure;
* safety certification;
* clinical, legal, financial, or regulatory validity;
* production readiness.

## Evidence and provenance

| Event or object | Identity |
|---|---|
| C-03 scientific execution head | `4225b49c6028ae5ddcc879eae1a9b9e6be2960d4` |
| C-03 evidence ZIP SHA-256 | `28021bfb5c095cc2a8424fb0f21300f15aa34e4c49bdbd467ff91e2d4a276610` |
| C-04 canonical-amendment audited head | `5e448d306976567b1e456512317c26f64bc18c0a` |
| Independent terminal-development audit | `PASS` |
| PM/auditor reconciliation | `MATCH — NO MATERIAL DISAGREEMENT` |
| PR #10 merge commit / R-01 base | `2f7aa988cb0f607def899f789ba5f846cb4f21ba` |

The complete C-03 archive has not yet been published through an immutable external archive. No DOI, Zenodo record, release URL, or release tag is asserted here.

## Migration

The active repository identity replaces an earlier architecture-selection framing and retires its unsupported quantitative claims. Historical commits remain available for provenance, but the old prototype is not active scientific evidence. See [MIGRATION.md](MIGRATION.md).

The GitHub repository slug remains `llm-worldmodels-hybrid-decision-frame` in this task. `audit-the-verifier` is the intended future slug, subject to separate authorization.

## Citation / license

Archival citation information will be added after immutable release archive publication.

The code and documentation are provided under the existing [MIT License](LICENSE).
