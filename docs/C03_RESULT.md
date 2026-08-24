# C-03 development result

Repository: `sergey-morev/llm-worldmodels-hybrid-decision-frame`

Scientific execution head: `4225b49c6028ae5ddcc879eae1a9b9e6be2960d4`

Status: **development-only**

C-03 evidence ZIP SHA-256:

`28021bfb5c095cc2a8424fb0f21300f15aa34e4c49bdbd467ff91e2d4a276610`

## OFFICIAL RESULT

`INCONCLUSIVE_BY_DEGENERACY`

```text
Delta_bar = undefined
Delta_bar_minus = undefined
```

C-03 evaluated 2,400 generated populations across 144 cells and 48 scientific strata. There were 108 eligible cells and 36 ineligible cells. The eligible cells represented 36 of 48 scientific strata; 12 strata were unrepresented.

All 36 ineligible cells failed solely `zero_event_proportion_above_0.50`. The unrepresented strata were exactly:

* `p_JDE = 0.01`, `B = 50`, all `pi_H`;
* `p_JDE = 0.003`, `B in {50, 100, 200}`, all `pi_H`.

The frozen structural rule required at least one eligible epsilon configuration in every one of the 48 scientific strata. Because that rule was not satisfied, the aggregate advancement statistic was not defined and its downstream comparison with `gamma_NC` was not reached.

C-03 was not confirmatory, invalid, or officially negative. No confirmatory preregistration was committed and no confirmatory experiment occurred. No official aggregate over only the 108 eligible cells is authorized.

## DESCRIPTIVE DEVELOPMENT EVIDENCE

The following quantities are descriptive and are not the official aggregate.

Among the 108 eligible cells:

| Quantity | Value |
|---|---:|
| Negative `Delta_cell` values | 97 |
| Positive `Delta_cell` values | 11 |
| Zero `Delta_cell` values | 0 |
| Mean | `-1.3933676212689903` |
| Median | `-1.3402708473419773` |
| Minimum | `-4.814389234158471` |
| Maximum | `0.015690285931822645` |

Empty confidence sets across all cells:

| Arm | Count |
|---|---:|
| UP | 0 |
| SP | 271 |

The eligible portion of the development map was descriptively adverse to the paired perturbation-instability path. The concentration of empty confidence sets in SP is consistent with variance inflation in the implemented importance-weighted score-informed sampling procedure.

This does not show that directed auditing generally fails, that score-informed auditing generally fails, or that paired perturbation instability is generally ineffective. It does not replace the undefined official aggregate.

## RETROSPECTIVE PROCESS LESSON

For a baseline sample of size `B` and event prevalence `p`, the elementary approximation

```text
P(K = 0) ≈ (1 - p)^B
```

would have identified low-prevalence, small-budget portions of the frozen map as prospectively prone to E3 exclusion. Because the design required all 48 strata to be represented, those upstream exclusions prevented the downstream aggregate decision rule from being reached.

This lesson was identified after C-03 evidence existed. It shows that the failure mechanism was prospectively detectable; it is not prospective validation of a later review function and is not a statistical discovery. Method validity and design informativeness are separate review surfaces.

## Scientific artifact hashes

| Artifact | SHA-256 |
|---|---|
| `stage2_compact_results.jsonl` | `5fe0e6806e955a19f33d9cf1ca25da699094f46e12e6814e89c85fae629bf3b1` |
| `stage2_selected_replay_traces.json` | `0cb85ce927fa13b3d975dfffeb8889bf2b920556d511351c1030ea993d8e4dd0` |
| `stage2_manifest.json` | `eda9663e66713f274e614dc809403cddd38a4f86b10095671b69397fe6b56c92` |
| `stage2_feasibility_map.json` | `4e1c277f55164d69d981cbd2d098098bc21d8ee65233ef0cfbd71b413e196996` |
| `stage2_primary_map_report.json` | `6bbb9079abffede72eab2a215e806280a3bbbc107620caaed8ea10da99c72e04` |

## Audit provenance

| Event | Identity or result |
|---|---|
| Canonical-amendment audited head | `5e448d306976567b1e456512317c26f64bc18c0a` |
| Independent terminal-development audit | `PASS` |
| Reconciliation | `MATCH — NO MATERIAL DISAGREEMENT` |
| Merge commit into `main` | `2f7aa988cb0f607def899f789ba5f846cb4f21ba` |

This was an independent repository/evidence audit, not scholarly peer review.

## Archive status

**PUBLISHED**

| Field | Value |
|---|---|
| Zenodo record | [https://zenodo.org/records/22081466](https://zenodo.org/records/22081466) |
| Version-specific DOI | [10.5281/zenodo.22081466](https://doi.org/10.5281/zenodo.22081466) |
| All-versions DOI | [10.5281/zenodo.22081465](https://doi.org/10.5281/zenodo.22081465) |
| Publication date | `2026-08-24` |
| Resource type | Dataset |
| Version | C-03 |
| Creator | Sergey Morev |
| Archive filename | `C03_STAGE2_PRIMARY_MAP_4225b49c.zip` |
| SHA-256 | `28021bfb5c095cc2a8424fb0f21300f15aa34e4c49bdbd467ff91e2d4a276610` |

The Zenodo record archives the development evidence object. Archival publication does not alter the scientific classification and is not scholarly peer review. It does not assert a GitHub release URL or release tag.
