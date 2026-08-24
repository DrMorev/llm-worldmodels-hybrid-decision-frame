# Project Direction

**Status:** ACCEPTED  
**Repository edition:** 2026-08-03  
**Accepted development baseline:** `0aaf49c86dabe42bc04ff5e3d05049c952250577`

This document defines the active direction of the repository. It replaces the previous project identity centered on LLM-versus-world-model architectures, JEPA, AGI debates, general hybrid architectures, and architectural forecasting.

Historical Git commits remain intact. The active repository surface is being migrated in bounded stages. The repository has not yet been renamed, and the current development prototype is not a preregistered or confirmatory result.

---

## 1. Project in one sentence

This project studies when an AI verifier has enough independent evidence to be allowed to advise, block, or authorize an action.

---

## 2. The practical problem

A system uses two AI components:

* a primary model proposes a decision or action;
* a verifier reviews it.

The two components may agree.

Agreement does not prove that the result is correct.

They may share:

* training data;
* model family;
* architecture;
* provider;
* prompts;
* tools;
* external sources;
* latent assumptions;
* failure causes.

The primary model and verifier can therefore make the same dangerous mistake.

The operational question is not simply:

Do the models agree?

It is:

Is there enough evidence to give the verifier real authority?

---

## 3. Verifier authority levels

The project separates three levels of authority.

### Advisory

The verifier may provide:

* an opinion;
* a warning;
* a recommendation;
* an escalation signal.

Its output does not directly control execution.

### Blocking

The verifier may:

* stop;
* delay;
* veto;
* escalate an action.

A false block may waste time or resources, but it does not directly authorize the dangerous action being reviewed.

### Authorization

The verifier may confirm that an action is permitted to proceed.

This requires the strongest evidence because a false authorization can directly expose the system to harm.

Blocking and Authorization must not automatically use the same:

* risk threshold;
* evidence requirement;
* confidence boundary;
* qualification rule.

---

## 4. Canonical research question

The canonical research question is:

Within cases where the primary model and verifier confidently agree, can a preregistered oracle-free audit strategy improve estimation of their joint dangerous-error risk at a fixed oracle budget compared with random auditing?

This wording must appear verbatim in:

* this document;
* PROJECT_DECISION_REGISTER.md;
* the preregistration;
* the final methods documentation.

It must not be replaced by a paraphrase in the confirmatory protocol.

---

## 5. Why the experiment studies agreement

The project studies confident agreement because common-cause dangerous errors may remain hidden precisely where the primary model and verifier agree.

High disagreement can reveal:

* inconsistent outputs;
* veto opportunities;
* obvious uncertainty;
* false-positive regimes;
* excessive blocking.

It does not directly solve the harder problem of joint false negatives in which both components produce the same dangerous answer.

The project therefore focuses on the agreement region not because agreement is evidence of correctness, but because agreement can conceal correlated failure.

Redirecting the primary experiment toward disagreement sampling requires a new recorded decision.

---

## 6. What the experiment will do

The project will use a synthetic generator with known ground truth and an explicit causal structure.

The generator will create:

* tasks;
* primary-model outputs;
* verifier outputs;
* independent errors;
* shared-cause errors;
* observable input and output features;
* hidden true outcomes.

The audit policy will not see:

* the hidden common-cause variable;
* the true label before oracle review;
* generator fields that directly reveal whether the two components are jointly wrong;
* privileged information unavailable in the intended audit setting.

Every audit proxy must be computed only from observable information.

A proxy that cannot be implemented without hidden truth, privileged variables, or a directly encoded relationship to error will not enter the experiment.

---

## 7. Compared audit strategies

The development strategies operated under the frozen oracle-budget grid.

The sole designated development primary-proxy candidate was:

`paired_perturbation_instability`

It did not pass the accepted development preregistration-advancement gate and was never frozen as a confirmatory primary proxy. It does not advance in this phase.

`confidence_floor_margin` was retained as a cheap development baseline, not as a second primary proxy.

`evidence_path_overlap` is excluded from the current experiment. Any later use would require a separate post-release architecture-specific GO decision.

The frozen development comparison included uniform and directed auditing within the agreement region using the accepted anytime-valid statistical machinery. Its primary contrast was PPI-informed sampling with PPI as a control variate against uniform sampling with PPI as a control variate. The structural-representation gate prevented the aggregate advancement statistic from being defined.

No confirmatory primary proxy exists for this phase. No replacement proxy is authorized before release and freeze.

---

## 8. Primary endpoint

The primary endpoint is continuous.

The accepted development-method hierarchy is:

1. a feasibility and statistical-validity eligibility gate applied before examining proxy contrasts;
2. a conditional relative-reduction endpoint comparing SP with UP only in eligible cells;
3. a feasibility map reported across all cells, including ineligible cells and their exclusion reasons.

At a fixed oracle budget, the conditional endpoint compares statistically valid upper confidence bounds on joint dangerous-error risk. Negative effects remain part of the analysis.

No confirmatory numerical values were fixed because the project did not enter preregistration. The frozen C-03 development values remain historical execution parameters and are not retroactively changed.

The endpoint design must support:

* uncertainty quantification;
* simulation-based evaluation-size design;
* comparison at equal budget;
* distinction between a negative result and an underpowered result.

Raw error-discovery lift is diagnostic only.

It must not determine verifier qualification.

---

## 9. Secondary operational outcomes

The following are secondary interpretations:

* whether the Blocking threshold is crossed;
* whether the Authorization threshold is crossed;
* at what oracle budget a threshold is crossed;
* how many dangerous errors are discovered;
* whether sequential evidence accumulation stops before the maximum budget.

A threshold-crossing result is operationally important, but it is not the primary statistical endpoint.

A binary pass/fail result alone would be too dependent on where the threshold was placed.

---

## 10. Statistical validity requirement

A strategy is not considered useful merely because it finds more errors.

Its risk estimate must remain statistically valid.

The synthetic evaluation must examine:

* estimator bias;
* empirical coverage;
* bound width or tightness;
* stability across preregistered scenarios;
* qualification decisions at predefined thresholds.

A narrower invalid bound is worse than a wider valid bound.

Directed sampling must account for its inclusion probabilities or use another preregistered correction appropriate to the sampling design.

---

## 11. Why synthetic data are used

Synthetic data allow the experiment to know:

* the true outcome;
* whether both components are wrong;
* whether an error has a common cause;
* the true population risk;
* estimator bias;
* confidence-bound coverage.

This makes it possible to test whether the audit procedure itself is valid.

Synthetic data also keep the first experiment:

* bounded;
* reproducible;
* provider-independent;
* free from private or patient data;
* separate from unsupported domain claims.

The synthetic experiment is not evidence that a real deployed system is safe.

---

## 12. Applicable domains

The underlying problem may occur wherever AI systems influence consequential actions, including medical, financial, legal, software, cybersecurity, industrial, and tool-using-agent settings.

The first experiment validates none of these domains.

Any domain-specific claim requires domain-specific evidence and a separate decision.

---

## 13. Tools, APIs, MCP, agents, and external checks

An additional tool call does not automatically provide independent verification.

Possible evidence sources include:

* another LLM;
* an MCP server;
* an API;
* a database;
* a calculator;
* a compiler;
* a rule engine;
* a sensor;
* a human reviewer.

Each source verifies only particular properties.

Examples:

* a calculator may verify arithmetic;
* a compiler may verify parsing or build success;
* an API may provide external data but may be stale, incomplete, or incorrect;
* a sensor may observe external state but may fail;
* another LLM may provide another opinion but may share the same failure cause;
* a human may provide independent judgment but is not error-free.

The project therefore treats verification as an evidence question, not as a count of:

* models;
* agents;
* tokens;
* API requests;
* MCP calls;
* tools.

More components do not automatically produce more independent evidence.

---

## 14. What the project is

The project is intended to become:

* a narrow research artifact;
* a preregistered synthetic experiment;
* a reproducible reference implementation;
* a verifier-qualification protocol;
* a case study in separating Advisory, Blocking, and Authorization authority;
* a bounded investigation that can publish a positive, negative, inconclusive, or invalid result.

---

## 15. What the project is not

The project is not:

* a new neural-network architecture;
* an AGI project;
* a theory of intelligence;
* a universal AI-safety framework;
* a production verifier;
* an authorization system ready for deployment;
* a clinical validation study;
* a benchmark of commercial LLM providers;
* a comparison of GPT, Claude, Gemini, or other platforms;
* a JEPA implementation;
* a GNN implementation;
* a knowledge-graph implementation;
* a world-model implementation;
* proof that multiple models are safe;
* proof that directed auditing always works;
* proof that random auditing is always optimal;
* proof that tool use creates independent verification.

---

## 16. Relationship to the previous repository

The existing repository will be retained as the historical Git base but substantially rewritten.

The active migration includes:

* the accepted canonical research question;
* the merged Phase 1B development prototype and tests;
* a future preregistration;
* confirmatory implementation after preregistration;
* development CI;
* a new repository name and root README before release;
* explicit limitations and non-claims;
* a migration note.

The following old elements will not remain part of the active scientific claim:

* AGI framing;
* LLM versus JEPA positioning;
* the P1–P3 hypothesis structure;
* the old LLM-versus-world-model demonstration;
* the broken latency scenario;
* the claimed crossover near 70 ms;
* the previous publish-ready status;
* automatic fallback to LLM-only when verification exceeds the time budget.

The old fallback remains a documented negative case:

Insufficient time does not make an unverified action safe.

A time constraint may disqualify a verification path.

It does not qualify an unverified path.

Depending on the application, the acceptable response may instead be:

* abstain;
* stop;
* defer;
* escalate;
* use a separately qualified fast path;
* use a deterministic safety controller.

### Current repository state

C-03 executed the frozen Stage 2 development feasibility map at Git head `4225b49c6028ae5ddcc879eae1a9b9e6be2960d4`.

Its exact development classification is `INCONCLUSIVE_BY_DEGENERACY`. The prospective 48-of-48 structural-representation gate was not satisfied, so `Delta_bar` and `Delta_bar_minus` remain undefined/null and no unofficial aggregate over the 108 eligible cells is authorized.

C-03 was development-only. It was not an invalid run, it is not reclassified as negative, no confirmatory preregistration was committed, and no confirmatory run occurred. PPI did not satisfy the prospective conditions required to advance into preregistration and therefore does not advance in this phase.

The repository may release this development-stage terminal outcome with explicit non-claims and immutable evidence references. The historical root README and repository name remain temporary migration surfaces until that release-facing structure is approved.

---

## 17. Expected scientific value

The project does not claim a new general theory.

Its potential scientific value is narrower:

* connect verifier qualification to actual authority levels;
* estimate joint dangerous-error risk inside the agreement region;
* compare random and directed auditing under a fixed oracle budget;
* evaluate valid confidence bounds rather than only error discovery;
* distinguish Blocking evidence from Authorization evidence;
* evaluate sequential evidence accumulation;
* publish a valid negative, inconclusive, or invalid result if the proposed approach does not work.

Scientific novelty is currently unproven.

A focused related-work review and independent claims audit are required before any public novelty claim.

---

## 18. Expected engineering value

The resulting artifact may help a team ask:

* Is the verifier only advisory?
* May it block an action?
* May it authorize an action?
* What property is the verifier actually checking?
* How independent is the available evidence?
* How much oracle review is available?
* Does the audit design produce a valid risk estimate?
* Does the available evidence support the required authority level?
* Must the system abstain or escalate?

The central practical warning is:

Agreement between AI components is not automatically independent evidence.

---

## 19. Expected portfolio value

The repository should demonstrate:

* problem narrowing;
* falsifiable experimental design;
* preregistration;
* statistical discipline;
* explicit non-claims;
* tolerance for negative results;
* reproducibility;
* correction of earlier unsupported claims;
* traceable project governance;
* decision-making under asymmetric risk.

Its value does not depend on:

* becoming a commercial product;
* receiving GitHub stars;
* supporting every possible domain;
* producing a positive result.

---

## 20. External AI review systems

External AI review systems may assist with:

* neutral review of the preregistration;
* adversarial review of the methodology;
* documentation quality control;
* blind review of final claims.

Agreement among AI reviewers is not independent scientific evidence.

The final result auditor must be separate from the reviewer who evaluated the preregistration.

Any future experiment using real model providers requires a separate post-release protocol and GO decision.

---

## 21. Preregistration requirement

Before implementation of the confirmatory experiment, the preregistration must fix:

* the canonical research question;
* unit of analysis;
* estimand;
* continuous primary endpoint;
* secondary endpoints;
* agreement-region definition;
* synthetic scenario family;
* hidden causal variables;
* frozen generator parameters;
* varied parameters and ranges;
* development scenarios;
* confirmatory scenarios;
* holdout scenarios, if used;
* oracle budget B;
* Blocking risk threshold;
* Authorization risk threshold;
* one primary proxy;
* secondary proxies;
* proxy realizability rule;
* random-audit baseline;
* sequential baseline;
* inclusion probabilities;
* weighting or bias correction;
* estimator;
* confidence-bound method;
* empirical coverage requirement;
* multiple-comparison correction;
* simulation-based N_eval;
* stopping rule;
* failure and restart rule;
* positive result;
* negative result;
* inconclusive result;
* invalid result;
* blind-audit question.

The preregistration must be committed and identified by hash before the confirmatory experiment is run.

---

## 22. Development and confirmatory separation

Development may use:

* dedicated development seeds;
* development-only scenarios;
* deliberately easy validation cases;
* synthetic cases designed to expose implementation defects.

Development outputs must not enter the confirmatory result.

The confirmatory manifest must remain inaccessible to:

* result-dependent tuning;
* development CI;
* proxy selection;
* parameter adjustment;

until:

* the preregistration is committed;
* implementation is complete;
* development CI passes;
* the confirmatory run is explicitly authorized.

Coverage testing before authorization must use development scenarios only.

### Future decision-reachability control

Before any future expensive evidence-producing experimental design is frozen or executed after a separately authorized post-release GO, the Project Manager must ensure that decision reachability and operating characteristics have been assessed prospectively for the exact design.

The required question is:

Assuming the scientific method is correct, can the exact proposed design reach its own decision rule with informative data?

Use the cheapest sufficient analysis in this order:

1. elementary arithmetic and analytic sanity checks;
2. exact finite calculations where required;
3. bounded prospective simulation only when simpler analysis is insufficient.

This function is diagnostic, not an optimization mandate. It must not maximize the probability of a positive result, remove difficult scientific regimes merely to improve reachability, weaken validity safeguards, or alter a design after protected target evidence is observed. It is a required function when triggered, not a new permanent project role, and C-03 does not prospectively validate it.

---

## 23. Possible outcomes

Positive result

The preregistered primary strategy improves the continuous primary endpoint with valid statistical coverage and achieves the predefined practical effect under the tested conditions.

Any Blocking or Authorization threshold crossing is reported as a secondary operational consequence.

The repository is released with this limited result.

Negative result

The preregistered primary strategy fails to provide the predefined useful advantage, and the experiment has sufficient precision to exclude that advantage under the tested conditions.

The repository is released with the negative result.

Inconclusive result

The experiment cannot distinguish a practically useful effect from insufficient performance.

Examples include:

* inadequate precision;
* an interval or bound spanning the operationally relevant region;
* instability across preregistered scenarios.

The experiment is not silently extended or retuned.

The repository is released with the inconclusive result.

Invalid result

The result is classified as invalid if:

* the implementation violates the preregistration;
* the estimator fails the preregistered coverage requirement;
* a proxy accesses forbidden information;
* post hoc tuning contaminates the confirmatory analysis;
* an unpermitted restart occurs;
* the confirmatory manifest is exposed prematurely;
* another material protocol violation occurs.

The scientific claim is withdrawn.

The repository may still be released as a documented methodological case study.

Development-terminal result

A prospectively defined development advancement gate may prevent the project from entering preregistration. In that case, the exact development classification and evidence identity are preserved, no confirmatory result is claimed, an independent terminal-development result audit is completed, and the repository may release and freeze through the development-terminal route defined in the Release Pipeline.

For C-03, the exact class is `INCONCLUSIVE_BY_DEGENERACY`. It is not confirmatory evidence, an invalid run, or an official negative result.

---

## 24. Current non-claims

The project has not yet shown that:

* the primary proxy is useful;
* directed auditing is superior to random auditing;
* the sequential baseline is inferior or superior;
* joint dangerous-error risk can be estimated adequately under the selected budget;
* the verifier can safely block actions;
* the verifier can safely authorize actions;
* the synthetic scenarios represent a real deployment distribution;
* the method transfers to medicine, finance, law, software, cybersecurity, industrial systems, or autonomous agents;
* the project is scientifically novel;
* the repository is reproducible;
* the repository is production-ready.

---

## 25. Terminal state

The current project phase ends through exactly one of two mutually exclusive terminal routes:

* a confirmatory route that preserves preregistration, confirmatory isolation, independent blind result audit, classification reconciliation, immutable release, and freeze;
* a development-terminal route used only when a prospectively defined development advancement gate prevents entry into preregistration.

C-03 follows the development-terminal route. That route requires exact evidence identity and hashes, explicit development classification, an explicit statement that no confirmatory result exists, Project Manager terminal interpretation, independent terminal-development result audit, reconciliation, release documentation, immutable archival evidence reference, release tag, and repository freeze.

Further development requires a separate explicit GO decision.

A positive result does not automatically authorize continuation.

---

## 26. Current direction decision

Proceed to release and freeze the exact C-03 development-stage terminal outcome without entering preregistration or confirmatory execution.

The official classification remains `INCONCLUSIVE_BY_DEGENERACY`. PPI does not advance. No replacement primary proxy, PPI rescue, retuning, grid revision, or new proxy-development loop is authorized in this repository before release and freeze.

Do not expand before that release into:

* additional architectures;
* real-model provider evaluations;
* new application domains;
* JEPA;
* world models;
* knowledge graphs;
* clinical validation;
* product development.

---

## 27. Current authorized next step

Synchronize the C-03 development-terminal governance contract, obtain an independent terminal-development result audit, prepare release-facing documentation and immutable external archival evidence, then seek separate release authorization.

This document does not authorize:

* a C-03 rerun;
* PPI rescue, retuning, grid revision, PPI-2, or replacement proxy search;
* calculation of `Delta_bar`, `Delta_bar_minus`, or an unofficial 108-cell aggregate;
* preregistration;
* confirmatory implementation;
* confirmatory execution;
* creation or exposure of a confirmatory manifest;
* public release.
