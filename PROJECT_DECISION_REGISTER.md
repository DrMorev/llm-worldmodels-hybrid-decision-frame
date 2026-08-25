# Project Decision Register

**Status:** ACCEPTED  
**Repository edition:** 2026-08-03  
**Accepted development baseline:** `0aaf49c86dabe42bc04ff5e3d05049c952250577`

This register records accepted decisions governing project direction, experimental boundaries, review structure, source authority, and execution controls.

It is not a public research paper, a preregistration, or evidence that the proposed experiment works. Its purpose is to prevent silent scope changes, restoration of withdrawn claims, uncontrolled executor behavior, and post hoc movement of the confirmatory experiment.

---

## 1. Authority model

### Decision

The project distinguishes between:

1. normative authority — what the project has decided to do;
2. descriptive ground truth — what currently exists and runs in the repository.

Normative authority

For project direction and planned work, use the following order:

1. accepted `PROJECT_DIRECTION.md`;
2. accepted `PROJECT_DECISION_REGISTER.md`;
3. accepted and committed preregistration;
4. accepted `RELEASE_PIPELINE.md`;
5. accepted `AUDIT_FINDINGS_REGISTER.md`;
6. approved release documentation;
7. historical audits, external-review records, and archived planning materials.

Descriptive ground truth

For claims about what currently exists or works, use:

1. inspected repository state at an identified branch, tag, or commit;
2. actual execution output, tests, CI, and generated artifacts;
3. accepted Git commit history;
4. repository documentation;
5. planning documents and historical discussion.

### Clarification

A canonical document may authorize future implementation. It does not prove that the implementation already exists.

Repository state may show what exists. It does not independently redefine project purpose.

### Reversal condition

This authority model may change only through an explicit Project Investigator decision recorded in this register.

---

## 2. Repository fate

### Decision

Proceed with the bounded release direction:

Conduct one preregistered synthetic experiment in the existing repository, release the result regardless of outcome, and then freeze the repository.

**Execution-state clarification:** this was the original prospective Path-A plan. C-03 instead reached the accepted development-terminal Path B before preregistration; the active operation is release, tag, final verification, and freeze of that exact outcome.

### Rationale

A cosmetic cleanup would leave the project largely as prose.

An open-ended expansion into hybrid architectures, JEPA, graphs, real-model evaluation, or product development would exceed the available evidence and bounded scope.

The restricted experiment gives the project one controlled opportunity to produce a defensible result.

### Alternatives rejected

* Release the current repository after cosmetic cleanup only.
* Begin an open-ended research programme.
* Build a general hybrid AI architecture.
* Create a new repository for LLM, JEPA, graph, and world-model integration.
* Turn the project into a commercial product before evidence exists.

### Uncertainty

The experiment may produce a:

* positive;
* negative;
* inconclusive;
* invalid

result.

No useful effect is guaranteed.

### Reversal condition

Further research after the mandatory release requires a separate GO decision.

A positive result does not automatically authorize continuation.

---

## 3. Existing repository versus new repository

### Decision

Use the existing Git repository as the historical base.

Do not create a new GitHub repository for the current experiment.

### Rationale

The new direction evolved from the original project’s concern with:

* costly errors;
* independent verification;
* abstention;
* external evidence;
* latency;
* action constraints.

Preserving Git history provides an inspectable record of:

* the original project;
* the failed evidence;
* the research pivot;
* the withdrawn claims;
* the replacement experiment.

### Implementation consequence

The active repository may be substantially rewritten, including:

* repository name;
* README;
* description;
* documentation structure;
* prototype code;
* tests;
* CI;
* experimental claims.

Historical commits must not be rewritten or deleted.

### Reversal condition

A new repository may be considered only after the mandatory release if a later project has a materially different question, artifact, and audience.

---

## 4. Project identity

### Decision

The repository is no longer primarily about:

* LLM versus world-model architectures;
* JEPA;
* AGI;
* general hybrid systems;
* architectural forecasting.

The active project studies:

When an AI verifier has enough evidence to be allowed to advise, block, or authorize an action.

### Rationale

The previous architectural question was too broad.

Many of its components belong to existing research fields.

The remaining operational problem is narrower and testable.

Rejected identities

* General hybrid decision framework.
* Path to AGI.
* LLM plus world-model architecture.
* Graph-augmented hybrid intelligence.
* Universal AI verification framework.

### Reversal condition

The old identity must not return without:

* a separate proposal;
* a new literature review;
* a new scope decision;
* a separate GO.

---

## 5. Repository rename

### Decision

The repository will receive a new name before public release.

### Rationale

The current name implies that LLMs, world models, and hybrid architectures remain the central subject.

That would misrepresent the active project.

### Naming requirement

The new name should communicate one or more of:

* verifier qualification;
* evidence for verifier authority;
* independent verification;
* Advisory, Blocking, and Authorization;
* audit-based qualification.

### Prohibited naming

The name must not imply:

* guaranteed safety;
* validated authorization;
* clinical readiness;
* universal applicability;
* AGI;
* a new neural architecture.

### Historical restriction

Repository rename is not authorized before the preregistration and migration plan establish the final public structure.

This restriction records the earlier pre-C-03 development plan. C-03 subsequently took the accepted development-terminal Path B before preregistration, and the repository was renamed to `sergey-morev/audit-the-verifier` under separate authorization.

### Reversal condition

The existing name may remain during internal development but not as the intended final release identity.

---

## 6. Core practical problem

### Decision

The project concerns systems with:

* a primary AI component;
* a second component acting as verifier;
* consequential actions or decisions;
* incomplete evidence that the verifier is independent.

Agreement between the two components is not proof of correctness.

### Rationale

The components may share:

* model family;
* training data;
* provider;
* architecture;
* prompts;
* tools;
* information sources;
* latent assumptions;
* failure causes.

### Reversal condition

None. This is a core project premise.

---

## 7. Verifier authority levels

### Decision

Verifier authority is divided into three states:

1. Advisory
2. Blocking
3. Authorization

### Advisory

The verifier may provide:

* an opinion;
* a warning;
* a recommendation;
* an escalation signal.

It does not directly control execution.

### Blocking

The verifier may:

* stop;
* delay;
* veto;
* escalate an action.

### Authorization

The verifier may confirm that an action is permitted to proceed.

### Rationale

False blocking and false authorization have different consequences.

A verifier that is adequate for advice may not be adequate for blocking.

A verifier that is adequate for blocking may not be adequate for authorization.

### Rejected alternative

A single binary state such as:

trusted verifier

### Reversal condition

Additional authority states may be introduced only if the experiment demonstrates that the three-state model is insufficient.

---

## 8. Asymmetric qualification

### Decision

Blocking and Authorization must not automatically use the same:

* risk threshold;
* evidence requirement;
* sample requirement;
* upper confidence boundary;
* qualification rule.

### Rationale

A false authorization may directly permit a dangerous action.

A false block usually prevents or delays action.

The losses are not automatically symmetric.

### Implementation consequence

The preregistration must define separate qualification conditions for Blocking and Authorization.

### Reversal condition

A shared rule is allowed only if a specific application demonstrates symmetric loss and explicitly justifies that symmetry.

---

## 9. Canonical research question

### Decision

The active research question is:

Within cases where the primary model and verifier confidently agree, can a preregistered oracle-free audit strategy improve estimation of their joint dangerous-error risk at a fixed oracle budget compared with random auditing?

Exact-wording rule

This sentence must appear verbatim in:

* PROJECT_DIRECTION.md;
* this register;
* the preregistration;
* final methods documentation.

It must not be replaced by a confirmatory-protocol paraphrase.

### Operational interpretation

The experiment asks whether observable pre-oracle information can allocate a limited expert-review budget in a way that improves qualification-relevant risk estimation.

Rejected formulations

* At what correlation does verification stop paying off?
* Can hidden dependence be detected?
* Does agreement increase while safety decreases?
* Can common-cause failures exist?
* Can unknown unknowns be found?
* Is directed auditing always better than random auditing?

### Reversal condition

The question may be narrowed before preregistration approval.

It must not be broadened after confirmatory evidence is observed.

---

## 10. Why the experiment studies agreement

### Decision

The primary population is the deterministically defined confident-agreement region.

### Rationale

High disagreement can reveal:

* conflict;
* uncertainty;
* veto opportunities;
* false-positive regimes;
* excessive blocking.

The more difficult joint-dangerous-error regime can occur when both components share a failure cause and produce the same wrong answer.

In that regime:

D(x) ≈ 0

where D(x) is an observable disagreement measure.

The agreement region is therefore studied not because agreement proves correctness, but because agreement can conceal correlated failure.

Rejected direction

Using high disagreement as the natural primary target for common-cause joint false negatives.

### Reversal condition

Redirecting the primary experiment toward disagreement requires a new recorded decision.

---

## 11. Primary endpoint

### Decision

The primary endpoint must be a continuous statistical quantity.

It must measure qualification-relevant estimation performance at a fixed oracle budget.

Candidate forms include:

* a valid upper confidence bound on joint dangerous-error risk;
* the width or tightness of that valid bound;
* another equivalent continuous measure justified before preregistration approval.

### Current open decision

The exact continuous primary endpoint has not yet been selected.

It must be fixed in the preregistration.

### Rationale

A binary qualification result depends excessively on threshold placement.

If both strategies pass or both fail, a meaningful difference in estimation quality could be hidden.

A continuous endpoint is also needed for simulation-based design of N_eval.

### Secondary operational outcomes

* Whether the Blocking threshold is crossed.
* Whether the Authorization threshold is crossed.
* At what budget a threshold is crossed.
* Whether a sequential procedure stops early.
* How many dangerous errors are discovered.

Rejected primary endpoint

Raw error-discovery lift.

### Reversal condition

The selected endpoint may change only before preregistration approval and only if the replacement:

* measures qualification-relevant estimation;
* supports uncertainty quantification;
* supports precision or power analysis;
* does not depend on post hoc threshold placement.

---

## 12. Error-discovery lift

### Decision

Error-discovery lift may be reported only as a diagnostic or explanatory metric.

It must not directly determine verifier qualification.

### Rationale

Finding more errors and estimating population risk are different estimands.

Directed sampling may improve discovery while:

* changing inclusion probabilities;
* increasing variance;
* introducing bias if uncorrected;
* producing invalid confidence bounds.

Withdrawn formula

No formula of the form:

L_min = N_auth / B

may be used as the primary decision rule.

### Reversal condition

Discovery lift may become primary only in a separate project specifically about incident discovery rather than risk qualification.

---

## 13. Separate budget and sample quantities

### Decision

The project must keep separate:

* B: operational oracle or expert-review budget;
* qualification thresholds and evidence requirements for Blocking and Authorization;
* N_eval: evaluation size required to compare methods with adequate precision.

### Rationale

These quantities answer different questions.

Operational affordability is not statistical power.

Qualification evidence is not evaluation sample size.

### Reversal condition

None.

---

## 14. Oracle budget

### Decision

The operational oracle budget must be fixed before the primary experiment.

### Rationale

Changing the budget after observing results would allow the qualification boundary to move toward a preferred conclusion.

### Clarification

The operational budget is a scenario property.

It is not selected solely through a power calculation.

### Reversal condition

Multiple budgets may be preregistered as separate scenarios.

No new primary budget may be introduced after confirmatory results are examined.

---

## 15. Evaluation size

### Decision

N_eval must be selected using simulation-based precision or power analysis appropriate to the final estimator and endpoint.

### Rationale

The experiment must distinguish:

* evidence that a proxy is insufficient;
* insufficient precision caused by an undersized evaluation.

Required substantive interpretations

* Sufficient.
* Insufficient.
* Inconclusive.

Rejected interpretation

Failure to cross a qualification threshold is not automatically a negative result.

### Reversal condition

Evaluation size may change after preregistration only under a predefined blinded precision or stopping rule.

---

## 16. Synthetic primary experiment

### Decision

The primary experiment will use synthetic data with known ground truth and explicit causal structure.

### Rationale

Synthetic data permit direct knowledge of:

* true labels;
* joint errors;
* common-cause variables;
* population risk;
* estimator bias;
* confidence-bound coverage.

This keeps the primary experiment:

* bounded;
* provider-independent;
* free of private or patient data;
* reproducible in principle;
* separate from unsupported real-domain claims.

### Rejected alternatives

* Clinical data as the primary release experiment.
* Proprietary commercial LLM evaluation.
* Human expert labelling as a release prerequisite.
* A benchmark requiring several paid model providers.

### Limitation

Synthetic evidence does not establish:

* operational safety;
* clinical validity;
* financial validity;
* legal validity;
* transfer to deployed systems.

### Reversal condition

Real-data evaluation requires a separate post-release protocol and GO decision.

---

## 17. Anti-circular proxy rule

### Decision

Every audit proxy must be computed only from information observable to the audit policy before oracle review.

### Allowed inputs

Depending on the preregistration:

* canonical model outputs;
* exposed confidence values;
* deterministic input features;
* output-consistency features;
* observable execution traces;
* other explicitly available signals.

### Forbidden inputs

A proxy may not use:

* the true label before oracle review;
* the hidden common-cause variable;
* a generator field directly revealing joint error;
* privileged information unavailable in the intended audit setting;
* a separate generator parameter that directly assigns the proxy an error relationship.

### Six-part realizability gate

A proxy must satisfy all six conditions:

1. It uses only observable information.
2. It does not use the true label before oracle review.
3. It does not use the hidden common-cause variable.
4. Its relationship to error is not directly assigned by the generator.
5. Its implementation can be specified independently of the desired result.
6. It can be reproduced from stored experiment inputs and outputs.

### Exclusion rule

A proxy failing any condition is removed before preregistration.

It must not be rescued by modifying the generator to make it predictive.

### Reversal condition

None for the primary experiment.

---

## 18. Generator controls

### Decision

The preregistration must specify:

* frozen parameters;
* varied parameters;
* allowed ranges;
* development scenarios;
* confirmatory scenarios;
* stress scenarios;
* holdout scenarios, if used;
* hidden causal variables;
* observable variables.

### Rationale

Without a fixed separation, robustness can be manufactured after results are observed.

Prohibited action

Generator parameters must not be retuned after confirmatory results are inspected to obtain a preferred conclusion.

### Reversal condition

Post hoc scenarios may be reported only as exploratory.

They cannot change the primary conclusion.

---

## 19. Agreement-region definition

### Decision

The agreement region must be defined deterministically.

Preferred forms

* binary decisions;
* fixed categories;
* canonical structured fields;
* normalized JSON;
* deterministic action codes.

Prohibited primary method

A probabilistic LLM judge must not determine whether the primary model and verifier agree.

### Rationale

A third model judge would introduce another unqualified and potentially correlated component.

### Reversal condition

Semantic agreement judged by a model may be studied only in a later real-model protocol with separate validation.

---

## 20. Required baselines

### Decision

The experiment must include at least:

1. fixed-budget random auditing within the agreement region;
2. one preregistered primary proxy strategy;
3. a sequential statistical baseline based on Wald SPRT or another explicitly justified anytime-valid method.

### Rationale

Random sampling is the basic comparator.

A sequential baseline is required because the operational problem includes evidence accumulation and possible early stopping.

### Reversal condition

SPRT may be replaced before preregistration by a better-matched sequential procedure with written justification.

---

## 21. Primary proxy and multiple comparisons

### Decision

There must be exactly one primary proxy.

Additional confirmatory proxies, if retained, are secondary.

### Development primary candidate

The sole designated development primary-proxy candidate was:

`paired_perturbation_instability`

It did not pass the accepted development preregistration-advancement gate specified in section 53 and was never frozen as the confirmatory primary proxy. It does not advance in this phase.

### Other candidates

* `evidence_path_overlap` is excluded from the current experiment and retained only as a possible post-release architecture-specific candidate requiring a separate GO.
* `confidence_floor_margin` was retained as a cheap development baseline, not as a second primary proxy.

### Comparisons

Primary development contrast:

* SP vs UP.

The planned confirmatory secondary contrasts, which were never entered because the project did not enter preregistration, were:

* SP vs SM;
* UP vs UM.

Had the project entered preregistration, the two confirmatory secondary contrasts would have used preregistered Holm correction.

All other C-03 contrasts remain descriptive. No contrast may now be promoted into an official C-03 aggregate or confirmatory result.

Multiple-comparison rule

Confirmatory secondary comparisons must use a preregistered correction.

Holm correction is the current default.

Exploratory proxies

A proxy invented, modified, or selected after seeing confirmatory results must be labelled exploratory.

It cannot determine the primary conclusion.

### Reversal condition

There is no reversal within this phase before release and freeze. Any later proxy-development programme requires a separate explicit post-release PI GO and a new prospective design identity.

---

## 22. Statistical validity

### Decision

A strategy is not considered useful unless its risk estimate or bound has acceptable empirical validity.

### Required checks

The synthetic evaluation must examine:

* estimator bias;
* empirical coverage;
* interval or bound width;
* stability across preregistered scenarios;
* qualification decisions at predefined thresholds.

### Principle

A narrower invalid bound is worse than a wider valid bound.

Directed sampling must account for its inclusion probabilities or use another preregistered correction appropriate to its sampling design.

### Reversal condition

None.

---

## 23. Sequential stopping

### Decision

Every sequential stopping rule must be fixed before the confirmatory run.

### Required specification

The preregistration must define:

* hypotheses or risk boundaries;
* update rule;
* stopping conditions;
* maximum budget;
* treatment of inconclusive runs;
* error-control guarantee.

### Rationale

An informal rule such as “stop when enough evidence appears” permits hidden researcher discretion.

### Reversal condition

None after preregistration.

---

## 24. Failure and restart rule

### Decision

The preregistration must contain a failure/restart rule separate from the statistical stopping rule.

### Required contents

* What counts as an execution failure.
* Which failures permit restart.
* Which failures invalidate the run.
* Whether the same manifest may be reused.
* Whether a new manifest is required.
* Whether code changes are permitted.
* Who authorizes restart.
* How partial output is treated.
* Whether exposure to partial results prevents a confirmatory restart.

### Default rule

A confirmatory run must not be silently restarted.

A permitted restart requires:

* an applicable preregistered rule;
* a deviation-log entry;
* Project Manager review;
* Project Investigator authorization.

### Reversal condition

None after preregistration.

---

## 25. Preregistration

### Decision

The complete experimental protocol must be approved and committed before confirmatory evaluation.

### Required contents

The preregistration must fix:

* canonical research question;
* unit of analysis;
* target population;
* estimand;
* continuous primary endpoint;
* secondary endpoints;
* agreement-region definition;
* scenario family;
* hidden causal variables;
* generator controls;
* development scenarios;
* confirmatory scenarios;
* holdout scenarios, if used;
* oracle budget;
* Blocking threshold;
* Authorization threshold;
* one primary proxy;
* secondary proxies;
* proxy-realizability rule;
* random-audit baseline;
* sequential baseline;
* inclusion probabilities;
* weighting or bias correction;
* estimator;
* confidence-bound method;
* empirical coverage requirement;
* multiple-comparison procedure;
* N_eval design;
* stopping rule;
* failure/restart rule;
* deviation-classification rules;
* positive-result rule;
* negative-result rule;
* inconclusive-result rule;
* invalid-result rule;
* blind-audit question.

### Integrity mechanism

The preregistration must have:

* a Git commit hash;
* a document hash if required;
* a reference from result artifacts to the preregistration commit.

### Reversal condition

A substantive change after preregistration creates a new protocol version.

The original confirmatory run becomes invalid unless the change was explicitly allowed in advance.

---

## 26. Four result classes

### Decision

The release must allow four result classes.

### Positive

The primary strategy improves the preregistered continuous endpoint with valid coverage and achieves the predefined practical effect under the tested conditions.

### Negative

The primary strategy fails to provide the required practical advantage, and the experiment has sufficient precision to exclude that advantage under the tested conditions.

### Inconclusive

The experiment cannot distinguish a practically useful effect from insufficient performance.

### Invalid

The implementation or analysis violates the preregistration, statistical validity fails, hidden tuning occurs, the confirmatory manifest is exposed prematurely, or another material validity condition fails.

### Rationale

Collapsing these classes into success/failure would encourage overclaiming and conceal underpowered or invalid work.

### Reversal condition

None.

---

## 27. Mandatory release

### Decision

The repository must be released after the bounded experiment whether the result is:

* positive;
* negative;
* inconclusive;
* invalid.

### Clarification

An invalid result may be released as a documented methodological case study without a positive scientific claim.

### Rationale

The experiment must not become an indefinite search for a favourable outcome.

Permitted release blockers

Release may be stopped only for:

* security or privacy exposure;
* licensing violation;
* irreparable artifact corruption;
* a finding that publication would materially misrepresent the work.

An unfavourable result is not a release blocker.

### Reversal condition

None.

---

## 28. Release before continuation

### Decision

The tagged release must be completed before any new research phase begins.

This applies even after a positive result.

Prohibited before release

* New proxies.
* Real-model testing.
* New domains.
* Product planning.
* JEPA.
* World models.
* Knowledge graphs.
* Additional confirmatory runs intended to improve the result.
* Silent amendment of the preregistration.

### Reversal condition

None.

---

## 29. Repository freeze

### Decision

After release, the repository enters a frozen state for the current phase.

Allowed without a new GO

* Critical security fixes.
* Citation corrections.
* Reproducibility repairs.
* Clear documentation corrections that do not alter the result.
* Environment repairs needed to reproduce the tagged release.

Not allowed without a new GO

* New scientific claims.
* New proxies.
* New datasets.
* Real-provider evaluation.
* New domains.
* Changed thresholds.
* Changed estimands.
* Expanded architecture.
* Productization.

### Reversal condition

A new phase requires a separate recorded GO decision.

---

## 30. Real model providers and external AI review

### Decision

Real models from multiple providers are not experimental subjects in the primary experiment.

External AI review systems may assist with neutral protocol review, adversarial methodology review, documentation quality control, and blind claim review.

Agreement among AI reviewers is not independent scientific evidence.

Real-model evaluation requires a separate post-release protocol, scope decision, and GO authorization.

### Reversal condition

None before the bounded release.

---

## 31. Review visibility and neutral framing

### Decision

Every project-relevant review must be visible to the Project Manager and attributable.

Each review record must include:

* exact question;
* reviewer identity and review role;
* materials provided;
* permitted scope;
* full response;
* accepted findings;
* rejected findings;
* unresolved findings;
* resulting project decision.

Neutrality rule

A reviewer must be asked to evaluate a proposition or protocol.

The reviewer must not be assigned a position to defend.

Prohibited form

Defend why directed audit is useful.

Acceptable form

Evaluate whether the proposed audit design validly estimates joint dangerous-error risk, identify failure modes, and state which conclusions would or would not be supported.

### Rationale

A previous parallel review track created provenance gaps and encouraged position-defending responses.

### Reversal condition

None.

---

## 32. Independence of protocol review and result audit

### Decision

The preregistration reviewer and final result auditor must be different reviewers.

The final result auditor must not:

* approve the preregistration as its primary reviewer;
* select the primary proxy;
* participate in implementation;
* select confirmatory parameters;
* see the Project Manager’s classification before producing an independent classification.

Classification procedure

The Project Manager records a preliminary result class privately.

The final auditor independently assigns:

* positive;
* negative;
* inconclusive;
* invalid.

Only after both classifications are recorded are they compared.

### Disagreement rule

Any disagreement must be:

* logged;
* analysed against the preregistration;
* preserved;
* disclosed in the release.

The Project Investigator must not select the more favourable class by preference.

### Reversal condition

None.

---

## 33. Roles

### Project Investigator

The Project Investigator owns:

* project purpose;
* final scope;
* preregistration approval;
* confirmatory-run authorization;
* commit and push authorization;
* public release;
* repository freeze;
* continuation or termination.

### Project Manager

The Project Manager owns:

* scope control;
* decision integration;
* source hierarchy;
* conflict resolution;
* stage transitions;
* stop/go recommendations;
* protocol-compliance review;
* preliminary result classification;
* release discipline.

### Lead Architect

The Lead Architect provides:

* methodological attack;
* endpoint and estimand critique;
* proxy-realizability review;
* sampling-design review;
* estimator review;
* stopping-rule review;
* failure/restart-rule review;
* preregistration review.

The Lead Architect does not authorize implementation, release, or continuation.

### Preregistration reviewer

A neutral reviewer evaluates the protocol before commit. This reviewer must not serve as final result auditor.

### Final result auditor

The final auditor:

* reviews protocol compliance;
* inspects confirmatory artifacts;
* independently classifies the result;
* evaluates claim-to-evidence alignment;
* does not see the Project Manager classification in advance.

### Executor

The Executor may:

* inspect approved files;
* edit within approved scope;
* implement approved specifications;
* run checks;
* produce artifacts;
* maintain the deviation log;
* prepare commit packets.

The Executor may not independently redefine:

* project meaning;
* research question;
* endpoint;
* primary proxy;
* generator parameters;
* authority thresholds;
* result classes;
* dependencies;
* scope;
* release outcome;
* commit authority.

---

## 34. Commit and push control

### Decision

No executor may commit or push without explicit Project Investigator approval.

Required commit packet

Before commit, the executor must report:

* repository and remote;
* branch;
* current HEAD;
* sync status;
* changed files;
* excluded files;
* proposed staging list;
* validation output;
* dependency changes;
* sensitive-file scan;
* proposed commit message;
* risks;
* limitations;
* open deviations.

Canonical approval phrase

Approved commit and push

Without this exact phrase, the executor must not:

* stage;
* commit;
* push.

Canonical state

Local work is provisional.

The accepted Git commit hash is canon.

### Reversal condition

The approval phrase may change only through a recorded Project Investigator decision.

---

## 35. Git branch strategy

### Decision

The major rewrite and experimental implementation must occur on a separate Git branch or pull request.

Direct-to-main may be considered only for

* small documentation corrections;
* typographical fixes;
* source-register updates;
* .gitignore;
* non-substantive metadata changes.

Even these changes still require:

* bounded scope;
* validation;
* commit packet;
* Project Investigator approval.

### Rationale

The repository is undergoing an identity and methodology change, not a minor patch.

### Reversal condition

None for core experimental logic.

---

## 36. MCP, APIs, tools, and agents

### Decision

Tool use is not automatically independent verification.

### Principle

A tool contributes trust only to the extent that it:

* is independent of the relevant failure cause;
* checks the relevant property;
* has known failure modes;
* returns inspectable evidence;
* is current and appropriately scoped.

Examples

* A calculator may verify arithmetic.
* A compiler may verify syntax or build success.
* An API may provide external data but may be stale or wrong.
* A sensor may observe state but may fail.
* Another LLM may provide review but may share the same failure.
* A human may provide independent judgment but is not error-free.

README consequence

The public README must explain:

More agents, tokens, tools, MCP calls, or API calls do not automatically create stronger evidence.

### Reversal condition

None.

---

## 37. Applicable domains

### Decision

The underlying problem may occur in:

* medicine;
* finance;
* law;
* software;
* cybersecurity;
* industrial control;
* tool-using agents;
* other consequential systems.

### Limitation

The primary experiment validates none of these domains.

Documentation rule

Domain examples may be used only with explicit non-validation language.

### Rejected alternative

Presenting the project as a validated multi-domain solution.

### Reversal condition

Domain-specific claims require domain-specific evidence and a separate release decision.

---

## 38. AGI

### Decision

Remove AGI positioning from the active project.

### Rationale

AGI is not needed to formulate or test verifier qualification.

It broadens the project without strengthening the experiment.

Prohibited uses

* AGI as motivation.
* AGI as novelty claim.
* AGI as marketing language.
* AGI as a release keyword.

### Reversal condition

None for the current phase.

---

## 39. World models, JEPA, graphs, and GNNs

### Decision

Do not include the following in the current experiment:

* learned world models;
* JEPA;
* GNNs;
* knowledge graphs;
* GraphRAG;
* LangGraph as a research contribution;
* graph-based hybrid architecture.

### Rationale

These components do not automatically solve the active question and would create scope expansion.

Historical treatment

They may appear only in:

* migration history;
* rejected alternatives;
* discussion of the previous project identity.

### Reversal condition

Future inclusion requires:

* a concrete unresolved problem;
* evidence that a simpler approach is insufficient;
* separate scope;
* separate preregistration;
* separate GO.

---

## 40. Old latency experiment

### Decision

The old latency_bound.py experiment and claimed crossover near 70 ms are withdrawn as evidence.

### Rationale

The file was not a valid runnable experiment.

The published numerical result was not reproducible from the repository.

Active treatment

* Do not repair the file merely to preserve the old claim.
* Do not cite the crossover as a result.
* Preserve the failure in the audit and migration records.
* Do not reuse the number as an assumption or target.

Remaining principle

Latency and action windows are legitimate operational constraints.

They are not the primary axis of the current experiment.

### Reversal condition

A future latency study requires a new preregistration and implementation.

---

## 41. Negative case: verification removed under time pressure

### Decision

The old fallback to LLM-only behaviour under insufficient verification time must remain documented as a negative case.

### Principle

Insufficient time does not make an unverified action safe.

A time limit may disqualify a verification path.

It does not qualify an unverified path.

Acceptable alternatives

Depending on the application:

* abstain;
* stop;
* defer;
* escalate;
* use a separately qualified fast path;
* use a deterministic safety controller.

### Reversal condition

The old code path may be removed.

The lesson must remain in the migration note and limitations.

---

## 42. Anti-overclaim rules

### Decision

The project may describe itself, when supported, as:

* exploratory;
* synthetic;
* preregistered;
* narrow;
* research-oriented;
* a reference implementation;
* a methodological case study.

### Current restriction

The repository must not yet be described as reproducible merely because reproducibility is planned.

Prohibited unsupported language

* safe;
* validated;
* production-ready;
* clinically reliable;
* generally proven;
* universal framework;
* novel method before review;
* authorization system ready for deployment.

### Rationale

Claim strength must follow evidence strength.

### Reversal condition

Stronger wording requires proportionally stronger evidence.

---

## 43. Novelty

### Decision

Scientific novelty is currently unproven.

Potentially underexplored combination

The project may investigate the combination of:

* verifier authority levels;
* fixed oracle budget;
* joint-error risk estimation;
* directed versus random auditing;
* asymmetric qualification;
* sequential evidence accumulation.

Prohibited novelty claims

Do not claim to be first to discover:

* correlated errors;
* false agreement;
* common-cause failure;
* hidden dependence;
* selective prediction;
* unknown-unknown auditing;
* sequential testing;
* verifier cost;
* weak-supervision dependence.

Novelty gate

Before public novelty language, conduct focused related-work review against:

* ensemble diversity;
* common-cause reliability;
* weak supervision;
* unknown-unknown auditing;
* selective prediction;
* LLM-as-judge dependence;
* verifier tax;
* budget-aware routing;
* sequential testing.

### Reversal condition

Novelty wording may be strengthened only after the final protocol and result survive related-work and claims review.

---

## 44. Scientific value

### Decision

The project’s potential scientific contribution is a bounded experimental result, not a general theory.

Valid contribution forms

* Positive result showing improved qualification-relevant estimation.
* Negative result showing no practically useful advantage.
* Inconclusive result identifying evidence limits.
* Invalid-result case study showing why the design failed.

### Rationale

A careful negative, inconclusive, or invalid result may be more valuable than an inflated framework claim.

### Reversal condition

None.

---

## 45. Engineering value

### Decision

The engineering value is to help teams distinguish:

* advice;
* blocking authority;
* authorization authority;
* available evidence;
* valid risk estimation;
* required abstention or escalation.

Core warning

Agreement between AI components is not automatically independent evidence.

### Reversal condition

None.

---

## 46. Portfolio value

### Decision

The repository is a supporting portfolio artifact.

It is not automatically the project owner’s primary flagship project.

Intended demonstration

It should show:

* problem narrowing;
* willingness to withdraw claims;
* preregistration;
* statistical discipline;
* reproducibility work;
* tolerance for negative results;
* explicit limitations;
* traceable governance.

Rejected objective

Optimizing primarily for:

* stars;
* social attention;
* promotional packaging;
* a large roadmap.

### Reversal condition

Its portfolio role may increase after external reproduction, use, citation, or substantive review.

---

## 47. README and evidence map

### Decision

The future README must include:

* current artifact status;
* practical problem;
* intended audience;
* scope and non-goals;
* Advisory, Blocking, and Authorization;
* the canonical research question;
* implemented versus planned work;
* experiment summary;
* evidence and validation status;
* public reproduction command;
* result class;
* limitations;
* applicable-domain examples with non-validation language;
* migration note;
* role and limits of models, APIs, MCP, tools, sensors, rules, and humans.

Rule

The README must describe current repository state, not project ambition.

### Reversal condition

None.

---

## 48. Canonical documentation set

### Decision

The active canonical set is:

1. `PROJECT_DIRECTION.md`;
2. `PROJECT_DECISION_REGISTER.md`;
3. `AUDIT_FINDINGS_REGISTER.md`;
4. `RELEASE_PIPELINE.md`;
5. the approved preregistration, once committed.

### Rationale

These documents preserve direction, decisions, defects, execution discipline, and experimental commitments.

Additional canonical documents require a concrete unmet need and an explicit decision.

### Rejected alternative

A large management-document system detached from implementation.

### Reversal condition

Additional canonical files require an explicit recorded decision.

---

## 49. Stop conditions

### Decision

The project must stop, narrow, or classify the result invalid if:

* the primary result follows trivially from generator design;
* a proxy encodes hidden truth;
* proxy validity requires circular generator tuning;
* estimator coverage fails;
* useful performance appears only after tuning;
* negative and underpowered outcomes cannot be distinguished;
* confirmatory data are exposed prematurely;
* implementation diverges from preregistration;
* an unpermitted restart occurs;
* the protocol duplicates established work without operational distinction;
* implementation expands into real-model evaluation;
* release cannot be reproduced;
* claims exceed evidence;
* scope expands before the first release;
* a hidden review track affects decisions;
* the same reviewer evaluates both protocol and final result;
* the final auditor sees the Project Manager classification before independent review.

### Rationale

Stop conditions prevent endless rescue attempts and identity attachment to a preferred outcome.

### Reversal condition

Continuation after a stop condition requires:

* a written Project Investigator decision;
* an updated protocol;
* a new commit hash;
* explicit treatment of the prior run.

---

## 50. Definition of completion

### Decision

The current phase is complete when:

1. the four canonical project documents are accepted;
2. the preregistration is approved and committed;
3. implementation is complete;
4. development CI passes;
5. the confirmatory run is completed or classified invalid;
6. the Project Manager classification is recorded;
7. the independent result audit is complete;
8. classification disagreement is resolved or disclosed;
9. the repository is released with an immutable tag;
10. temporary source files are safely removed;
11. the repository is frozen.

### Reversal condition

None.

---

## 51. Phase 1B development prototype adoption

### Decision

Accept merge commit `0aaf49c86dabe42bc04ff5e3d05049c952250577` as the repository's development-only Phase 1B statistical feasibility prototype.

The accepted implementation head contained by that merge is `a3d486e987d43063ba271cfe5f095f0f9a4b9545`. PR #3 used an ordinary merge commit, preserving all three independently audited feature commits in Git history.

### Evidence

The implementation underwent three independent audit rounds:

1. initial implementation audit;
2. bounded correction-delta audit;
3. final replay-consistency and Source Verification conformance audit.

The final audit verdict was `PASS — READY FOR Project Manager MERGE REVIEW`.

The final audit found:

* M1 fixed;
* N1–N6, N8, and N9 fixed;
* citation and attribution fixed;
* empty-confidence-set interpretation fixed;
* no new BLOCKER, MAJOR, or MINOR finding;
* no statistical regression from the final replay correction.

### Accepted boundary

This merge establishes only a development statistical feasibility prototype.

It does not establish that:

* the score-informed policy is useful;
* directed auditing outperforms uniform auditing;
* the estimator satisfies a future preregistered coverage gate;
* any verifier qualifies for Advisory, Blocking, or Authorization;
* the implementation is confirmatory;
* a primary endpoint, proxy, budget, beta rule, lambda rule, or scenario grid has been selected.

### Remaining engineering limitations

N7 remains deferred. The full development smoke JSON is approximately 1.3 GB. Artifacts remain outside Git and bounded replay and cleanup are feasible, but larger sweeps require a separate storage and serialization decision.

The final audit also recorded a non-blocking note: the current implementation uses the one-sided logical lower-bound component required for its one-sided upper dangerous-error bound. A future two-sided confidence-set formulation would require reconsideration of the complete two-sided logical intersection.

### Reversal condition

A new audit finding, a reproducibility failure, or evidence that the accepted implementation diverges from its documented development-only boundary requires a new recorded decision.

---

## 52. Current project status

**Status:** C-03 DEVELOPMENT-TERMINAL OUTCOME; PREREGISTRATION NOT ENTERED

### Established

* The old project identity and unsupported claims are retired.
* The canonical research question and release discipline are accepted.
* A development-only statistical feasibility prototype is merged at `0aaf49c86dabe42bc04ff5e3d05049c952250577`.
* The prototype has 29 independently reproduced tests and passed the final bounded implementation audit.
* The replay boundary and its lack of cryptographic authenticity are documented accurately.
* C-03 executed the frozen Stage 2 development map at `4225b49c6028ae5ddcc879eae1a9b9e6be2960d4`.
* The exact C-03 classification is `INCONCLUSIVE_BY_DEGENERACY`.
* PPI did not satisfy the prospective conditions required to advance into preregistration and does not advance in this phase.
* The canonical terminal-contract amendment at `5e448d306976567b1e456512317c26f64bc18c0a` passed independent terminal-development audit.
* Project Manager and independent-auditor reconciliation was `MATCH — NO MATERIAL DISAGREEMENT`.
* PR #10 merged the audited amendment into `main` at `2f7aa988cb0f607def899f789ba5f846cb4f21ba`.
* Focused release-positioning related-work review is complete and does not support broad novelty claims.

### Not established

* That any proxy improves audit allocation.
* That directed auditing outperforms random auditing.
* That the final estimator can validly qualify Blocking or Authorization.
* That development parameters are suitable for preregistration.
* That the method transfers to a real domain.
* That the repository is release-ready or scientifically novel.
* Any confirmatory result: no confirmatory preregistration was committed and no confirmatory run occurred.

---

## 53. PPI development method contract

### 53.1 Proxy definition

Inside the deterministically defined original agreement region:

```text
A_i = A_P(x_i) = A_V(x_i)
```

For a frozen ordered bank of K structurally label-preserving transformations:

```text
S_PPI(i) =
    1 - (1 / K) *
        sum_j I[
            A_P(T_j(x_i)) =
            A_V(T_j(x_i)) =
            A_i
        ]
```

The score may use only:

* original primary output;
* original verifier output;
* transformed primary outputs;
* transformed verifier outputs;
* frozen transformation-bank identity;
* frozen K.

The following are diagnostic only:

* primary flip rate;
* verifier flip rate;
* perturbed disagreement rate.

They must not alter, weight, or replace `S_PPI`.

### 53.2 Generator structure

The accepted minimal development structure is:

* latent canonical state determines truth;
* robust information is invariant under transformations;
* fragile surface information is changed by transformations;
* `H_i in {0,1}` is binary shared-fragile-mechanism membership;
* `pi_H` is the scenario-cell mixture axis;
* `pi_H = 0` is a mandatory null mechanism;
* `pi_H = 0.75` is the high-fragility reference condition: the largest shared-fragility level jointly realizable with the frozen joint-dangerous-error prevalence targets under the accepted generator and calibration structure;
* `pi_H = 0.75` is not a mathematical maximum; behaviour at complete shared fragility `pi_H = 1` is outside this experiment's evidence;
* stable shared false belief is a separate transformation-invariant mechanism;
* component-specific error terms remain separate;
* joint dangerous error and PPI are both derived outcomes;
* the generator must never sample correctness, joint error, or error probability conditional on completed PPI.

The primary and verifier fragile-feature coefficients must be:

* equal;
* constant;
* frozen across development cells.

Variation in fragile-mechanism contribution must occur through `pi_H`, not through separately tuning primary and verifier fragile coefficients.

Required collider diagnostic:

* report the association between component-specific error terms before selection into the agreement region;
* report it again after selection;
* report it by scenario cell;
* do not use it in the endpoint.

This diagnostic exists because conditioning on agreement may induce dependence even when component-specific terms are independent before selection.

### 53.3 Transformation bank and K

The accepted treatment is:

`K8_PRIMARY_K4_SENSITIVITY`

Requirements:

1. canonical state, truth, and robust feature remain exactly invariant;
2. bank order is frozen;
3. the K=4 subset is a fixed nested subset identified before outcome inspection;
4. no transformation may be added, removed, or replaced after observing errors;
5. bank content and order receive a reproducible digest;
6. every transformation changes exactly one designated fragile-surface component by the same fixed magnitude;
7. transformations are mutually non-identical on the development population;
8. identity is a separate sentinel and is not counted among K.

K=8 is primary because it provides finer score granularity.

K=4 is not statistically invalid merely because it creates five score levels. Equal scores receive equal factual sampling probabilities, and all actual inclusion probabilities remain recorded.

K=4 remains sensitivity only.

### 53.4 Confidence-margin baseline

Population-relative midrank normalization is rejected.

Use:

```text
m_c(i) =
    clip(
        (abs(L_ci) - tau_c) /
        (M_c - tau_c),
        0,
        1
    )
```

for `c in {P,V}`, and:

```text
S_M(i) = 1 - min(m_P(i), m_V(i))
```

where:

* `L_ci` is the observable original decision magnitude;
* `tau_c` is the frozen agreement-region confidence threshold;
* `M_c` is a frozen normalization constant;
* `M_c > tau_c` is mandatory;
* `M_c` is selected from reserved development information and fixed once for the study;
* it is not recomputed by scenario cell or replicate;
* correctness and hidden mechanism state are forbidden inputs.

Missing, nonfinite, or invalid magnitudes cause an explicit invalid condition.

Any scale-sensitivity check must use a frozen transformation of `L`, `tau`, and `M`. The method does not claim invariance to arbitrary monotone transformations when normalized distances are not preserved.

### 53.5 Development arms

| ID | Sampling | Control variate |
|---|---|---|
| U0 | uniform | none |
| UM | uniform | confidence margin |
| UP | uniform | PPI |
| SM | confidence-margin informed | confidence margin |
| SP | PPI-informed | PPI |

Every nonuniform arm must use:

* predictable probabilities;
* full support;
* positive exploration weight;
* factual recorded inclusion probabilities;
* the accepted IPW and betting construction.

No prop-MS performance guarantee is inherited.

### 53.6 Lambda aggregation

Let one common frozen finite grid be:

```text
Lambda = {lambda_1, ..., lambda_m}
```

The grid must be identical:

* across all arms;
* across all scenario cells;
* across all replicates.

For each candidate risk value `q`, construct the existing single-lambda e-process:

```text
W_t^(lambda)(q)
```

Define the equal-weight mixture:

```text
W_mix,t(q) =
    (1 / m) *
    sum_{lambda in Lambda} W_t^(lambda)(q)
```

The confidence set is obtained from:

```text
C_mix,t =
    { q in [0,1] :
      W_mix,t(q) < 1 / alpha_CS }
```

The existing logical bounds and running-intersection treatment are retained.

Numerical evaluation should use a stable log-sum-exp equivalent.

The following are forbidden:

* choosing one lambda after observing results;
* allowing lambda or the lambda grid to differ by arm;
* allowing lambda or the lambda grid to differ by cell;
* taking the minimum of uncorrected single-lambda bounds;
* selecting the grid using the direction or magnitude of SP vs UP.

Development may select only the common grid range and resolution.

The development selection criterion must be specified before examining the primary contrast and must include:

* acceptable empirical coverage in every arm;
* nondegenerate behaviour in UP;
* numerical stability.

A union-bound construction using `alpha_CS / m` per lambda may be considered only if the equal-weight mixture fails its development validity gate.

There is no automatic fallback.

Using the union-bound alternative requires a separate recorded PM/PI decision before it becomes active.

No mathematical modification of the accepted single-lambda betting factors is authorized by this decision.

For Stage 2 aggregation define the derived effective upper bound:

```text
U_tilde = final_upper_bound, when the confidence set is non-empty
U_tilde = 1.0, when the confidence set is empty
```

On an empty confidence set, raw `final_upper_bound` remains `null`, raw `validity_status` remains `empty_confidence_set`, and raw `coverage_indicator` remains `false`. `U_tilde` is written alongside the raw evidence and is the only bound entering `Delta`, `G`, or `gamma_NC`. No replicate is deleted and no raw field is overwritten.

### 53.7 Endpoint hierarchy

#### Level 1 — feasibility and validity gate

A cell is eligible only if all conditions hold before examining its proxy contrast:

* E1: empirical running-intersection coverage is at least 0.94 at nominal 0.95 in both UP and SP;
* E2: `mean_r(U_tilde_UP) < 1`;
* E3: the zero-revealed-dangerous-error replicate proportion is at most 0.50 in either compared arm.

Every ineligible cell remains in the feasibility map with an explicit exclusion reason.

Empty-confidence-set rate is a non-gating diagnostic reported per arm with a one-sided 95% Clopper-Pearson upper limit. At project level, pool the trajectory-level empty rate cluster-robustly by population. If its one-sided 95% lower limit exceeds `alpha_CS = 0.05`, hold the sweep for implementation investigation.

#### Level 2 — conditional proxy endpoint

For each eligible cell:

```text
Delta_cell =
    1 -
    mean_r(U_tilde_SP(B; r)) /
    mean_r(U_tilde_UP(B; r))
```

Aggregate:

```text
Delta =
    equal-weight mean of Delta_cell
    across eligible cells
```

Negative values remain in the analysis and mean directed sampling performed worse.

No cell is weighted by perceived realism or by replicate count.

The number and identity of eligible cells must be reported. All 48 scientific strata `(p_JDE, B, pi_H)` must contain at least one eligible epsilon configuration. If any stratum has none, aggregate `Delta` is not interpreted and the result is `INCONCLUSIVE_BY_DEGENERACY`; the full feasibility map remains reported. All eligible epsilon cells receive equal weight; no best-epsilon selection is permitted.

The feasibility map is always reported across all cells.

Blocking and Authorization threshold crossings remain secondary operational interpretations.

### 53.8 Negative and falsification controls

The following controls are mandatory:

1. identity transformation;
2. structural label invariance;
3. `pi_H = 0`;
4. fragility unrelated to error;
5. stable shared false belief;
6. conditional-permuted PPI;
7. constant PPI;
8. `pi_H = 0.75` high-fragility reference condition at the highest preregistered `p_JDE`;
9. global-permuted PPI.

Distinct notation is mandatory:

* sampling exploration weight: `epsilon_samp`;
* negative-control tolerance: `gamma_NC`;
* confidence-sequence error level: `alpha_CS`;
* true joint-dangerous-error prevalence: `p_JDE`.

One symbol must not represent more than one of these quantities.

For each null cell `k = (c, epsilon_samp, B)` define:

```text
G_k =
    1 -
    mean_r(U_tilde_SP(c, epsilon_samp, B, r)) /
    mean_r(U_tilde_UP(c, B, r))
```

`G_k` is a ratio of means, not a mean of per-replicate ratios. Epsilon remains a cell axis. For every null class, `K_c` contains all three epsilon values and all four budgets, for 12 cells, and:

```text
G_bar_c = equal-weight mean of G_k over K_c
```

The four null classes are:

* `pi_H = 0`;
* conditional-permuted PPI;
* global-permuted PPI;
* constant PPI.

Conditional permutation preserves the observable primary-output and confidence-margin stratum structure and tests whether PPI adds case-level information beyond those strata. It does not destroy between-stratum association. Global permutation assigns the existing PPI multiset by a deterministic uniform population-wide permutation without strata or hidden outcomes. It preserves the marginal score multiset and randomizes score assignment independently of hidden error; no claim of exact zero empirical correlation in a finite sample is made.

Within each class, bootstrap the population replicate index. One bootstrap index vector is reused across every epsilon/budget cell in that class, preserving shared denominators, nested budgets, and within-population arm correlation. Use 10,000 replicates and the type-7 linear-interpolation percentile. No additional pairing or variance correction is permitted.

```text
gamma_NC = max_c Q_0.975[bootstrap(G_bar_c)]
tau_NC = 0.05
```

`gamma_NC` is one project scalar. Its bootstrap seed derives solely from the negative-control namespace and must not consume evaluation or confirmatory-bootstrap seeds.

Classifications, in order:

* pooled empty-rate lower limit above `alpha_CS`: implementation failure; hold for investigation;
* `gamma_NC > tau_NC`: `INVALID_DEVELOPMENT_SWEEP`; PPI does not advance;
* any of the 48 scientific strata lacks an eligible epsilon: `INCONCLUSIVE_BY_DEGENERACY`; do not interpret aggregate `Delta`;
* otherwise let `Delta_bar_minus` be the one-sided 95% lower cluster-bootstrap limit of the equal-weight aggregate over eligible cells;
* `gamma_NC <= tau_NC` and `Delta_bar_minus > gamma_NC`: positive development-level result;
* `gamma_NC <= tau_NC` and `0 < Delta_bar_minus <= gamma_NC`: inconclusive;
* `gamma_NC <= tau_NC` and `Delta_bar_minus <= 0`: negative; reject the PPI path.

These are development classifications, not confirmatory claims.

### 53.9 Development stages

#### Stage 1 — plumbing validation only

Initial engineering scale may use:

* `N_A = 200`;
* `B = 20`;
* K=8, with K=4 sensitivity;
* five arms;
* 50 development replicates;
* bounded exploration candidates;
* all mandatory causal and control templates;
* the additional `pi_H = 1` high-prevalence cell.

Stage 1 cannot establish:

* proxy usefulness;
* estimator coverage adequacy;
* practical effect;
* preregistration readiness;
* superiority over random auditing.

Fifty replicates are insufficient for a scientific coverage conclusion.

#### Stage 2 — development feasibility map

Before fixing `delta`, `epsilon_samp`, `gamma_NC`, `N_eval`, or preregistration parameters, the development design must include at least:

```text
p_JDE in {
    1e-1,
    3e-2,
    1e-2,
    3e-3
}

B in {
    50,
    100,
    200,
    500
}
```

with:

* `N_A >= 5000`;
* `pi_H in {0, 0.5, 0.75}`;
* at least 200 replicates per evaluated cell;
* `epsilon_samp` candidates including `{0.1, 0.2, 0.4}`;
* the common lambda-mixture construction;
* reserved calibration seeds separated from evaluation seeds.

The negative-control bootstrap seed is derived solely from the negative-control namespace. Evaluation and confirmatory-bootstrap namespaces remain untouched until their separately authorized uses.

This is a minimum development candidate grid, not a frozen confirmatory grid.

Development outputs are used to determine:

* the feasibility and eligibility map;
* the common lambda grid;
* exploration weight;
* `gamma_NC`;
* practical threshold `delta`;
* required `N_eval`;
* whether PPI survives the development gate.

Confirmatory seeds, manifests, cell composition, and outcomes remain inaccessible.

#### Pre-evaluation `pi_H` grid repair — 2026-08-20

Reserved calibration evidence in `C-01 stage2_preflight_manifest.json` (SHA-256 `ff2b1072da3687ba5e3443873730f735898ab6a6253075649d41334eacdf3e17`) showed that `pi_H = 1` could not realize the frozen joint-dangerous-error targets under the accepted calibration structure, while `pi_H = 0.75` realized those targets in reserved development calibration. No evaluation or bootstrap workload had been executed. The favourable edge of the feasibility map is therefore `0.75`, not `1`; this record does not support claims about complete shared fragility.

### 53.10 Development primary-map bootstrap

The development primary-map bootstrap resamples generated population replicates. Populations are indexed by `(p_JDE, pi_H, replicate_id)`, giving exactly 12 generator strata in canonical ascending `(p_JDE, pi_H)` order. The 48 `(p_JDE, B, pi_H)` scientific strata are interpretation and structural-representation strata only; `B` is not a bootstrap-resampling axis.

The derived runtime seed is:

```text
development_primary_bootstrap_seed =
    stable_seed(
        evaluation_master_seed,
        "stage2_development_primary_bootstrap",
    )
```

This is not a new literal seed. The implementation uses one standard-library `random.Random(development_primary_bootstrap_seed)` instance and `rng.randrange(R)`, where `R = 200`. It must not reference, derive from, or consume the reserved confirmatory `bootstrap_master_seed`.

For bootstrap replicate `b = 0,...,9999`, in ascending order, the implementation visits all 12 generator strata in canonical ascending order and draws exactly `R` population-replicate indices with replacement for each stratum. The one index vector for a generator stratum is reused across all four nested budgets, UP, and every epsilon-specific SP arm. No draw is made by budget, epsilon, or arm.

The same 12-stratum bootstrap world supplies both the aggregate-Delta statistic and the pooled empty-confidence-set-rate statistic. Independent RNG streams for those two statistics are forbidden.

Eligibility E1/E2/E3 is evaluated once from the original point-estimate cell summaries. That eligibility mask is frozen before bootstrap resampling and is not recomputed within a bootstrap replicate. Each bootstrap world recomputes eligible-cell mean effective UP and SP bounds, `Delta_cell`, and their equal-weight aggregate. The pooled empty-confidence-set statistic uses the full map independently of eligibility, while consuming the same bootstrap-world indices.

The development primary bootstrap uses 10,000 replicates, a one-sided 95% lower confidence limit, deterministic type-7 percentile interpolation, and the generated population as the cluster/resampling unit. The 48-of-48 structural-representation rule remains unchanged.

### 53.11 Non-claims and stop rule

This contract does not establish:

* that PPI is useful;
* that directed auditing improves estimation;
* that the generator represents a real deployment;
* that any verifier qualifies for Blocking or Authorization;
* that the lambda mixture has passed empirical coverage;
* that K=8 is operationally affordable in a real system;
* that a confirmatory protocol is ready.

Stop or reject the PPI path if:

* proxy access to hidden fields is detected;
* the score-error relationship is directly assigned;
* mixture coverage fails and no separately authorized fallback exists;
* negative controls fail;
* PPI fails the frozen development gate at the high-fragility reference condition with adequate precision;
* useful performance appears only after tuning;
* implementation requires expansion into retrieval, real providers, or additional domains.

A rejected PPI path may not be rescued through post hoc generator retuning.

Any replacement proxy requires a new recorded decision before implementation.

---

## 54. Current authorized next step

### Current authorized next stage

The repository rename to `sergey-morev/audit-the-verifier` and public-identity cleanup were completed through PR #13, merged into `main` at `07998737f877a4ba52b3a79349bbafa7264034f1`. Complete the final release-hygiene closure, then seek separate authorization for the immutable release tag, GitHub Release publication, final verification, and repository freeze. The unchanged C-03 evidence package is archived on Zenodo with version-specific DOI `10.5281/zenodo.22081466`.

### Not authorized by the register itself

The register does not itself authorize:

* a C-03 rerun;
* modification of E1, E2, E3, the 48-of-48 rule, `gamma_NC`, `tau_NC`, or the frozen Stage 2 grid;
* an unofficial aggregate over the 108 eligible cells;
* PPI rescue, retuning, PPI-2, or replacement proxy search;
* preregistration;
* confirmatory manifest creation;
* confirmatory execution;
* any further repository rename or metadata change;
* replacement of the historical root README;
* commit;
* push;
* merge;
* release.

---

## 55. C-03 development-terminal phase decision

### Decision

The selected PPI development path terminated at C-03 because the prospectively defined 48-of-48 structural-representation gate prevented the development aggregate from being defined. The downstream scientific advancement test `Delta_bar_minus > gamma_NC` was therefore not reached.

This phase ends as **development-stage termination after failure of the preregistration-advancement gate**. The terminal machine classification remains exactly:

`INCONCLUSIVE_BY_DEGENERACY`

C-03 was development-only. No confirmatory preregistration was committed, no confirmatory run occurred, and C-03 is not confirmatory evidence. It is not an invalid run and is not reclassified as `NEGATIVE`. `Delta_bar` and `Delta_bar_minus` remain undefined/null. No unofficial aggregate over the 108 eligible cells is authorized.

PPI failed to satisfy the prospective conditions required to advance into preregistration and therefore does not advance. The repository may release this development-stage outcome without pretending that preregistration or confirmatory execution occurred.

No new PPI proxy search, rescue, retuning, grid revision, or replacement primary proxy is authorized in this repository before release and freeze. Any further proxy-development programme requires a separate explicit post-release PI GO and a new prospective design identity. Existing confirmatory requirements remain fully binding for any future phase that actually enters preregistration.

### Descriptive development evidence

The C-03 execution identity is Git head `4225b49c6028ae5ddcc879eae1a9b9e6be2960d4`. It produced 2,400 populations and 144 cells across 48 scientific strata. There were 108 eligible cells and 36 ineligible cells; 36 of 48 scientific strata were represented and 12 were unrepresented.

All 36 ineligible cells failed solely `zero_event_proportion_above_0.50`. The 12 unrepresented strata were:

* `p_JDE = 0.01`, `B = 50`, all `pi_H`;
* `p_JDE = 0.003`, `B in {50, 100, 200}`, all `pi_H`.

Among the 108 eligible cells, `Delta_cell` was negative in 97, positive in 11, and zero in 0. Its descriptive distribution was: mean `-1.3933676212689903`, median `-1.3402708473419773`, minimum `-4.814389234158471`, and maximum `0.015690285931822645`.

Empty confidence sets across all 144 cells were 0 for UP and 271 for SP. The pooled observed empty-confidence-set rate was `0.00474537037037037`; its pooled cluster-bootstrap one-sided 95% lower limit was `0.004027777777777778`. The frozen negative-control values were `gamma_NC = 0.014751154135125344` and `tau_NC = 0.05`.

These quantities are descriptive development evidence only. They do not define or replace the official endpoint. The eligible portion of the map is descriptively adverse to the PPI path. The concentration of empty confidence sets in SP is consistent with variance inflation in the implemented importance-weighted, score-informed sampling procedure. It does not prove that directed sampling in general fails, that low-prevalence directed sampling always causes variance inflation, or that C-03 establishes a general theory of directed auditing.

### Evidence publication contract

Large raw C-03 JSON artifacts must not be committed directly into Git. Repository-facing release evidence must contain or reference the feasibility map, manifest, primary report, runner stdout/stderr, a SHA-256 manifest for all scientific artifacts, and reproduction instructions.

The complete unchanged C-03 evidence ZIP is intended for immutable external archival publication, with Zenodo as the intended archival surface. Its SHA-256 is `28021bfb5c095cc2a8424fb0f21300f15aa34e4c49bdbd467ff91e2d4a276610`. Before final release, the archive must be externally versioned and immutable and its final DOI or reference must be inserted into release-facing documentation. No DOI, Zenodo record ID, GitHub Release URL, or publication date is asserted by this decision.

### Future decision-reachability control

Before any future expensive evidence-producing experimental design is frozen or executed after a separately authorized post-release GO, the Project Manager must ensure that decision reachability and operating characteristics have been assessed prospectively for the exact design. The control asks: assuming the scientific method is correct, can the exact proposed design reach its own decision rule with informative data?

Use the cheapest sufficient analysis: elementary arithmetic or analytic sanity checks first, exact finite calculations where required, and bounded prospective simulation only when simpler analysis is insufficient. This function diagnoses informativeness; it must not maximize the probability of a positive result, remove difficult regimes merely to improve reachability, weaken validity safeguards, or alter the design after protected target evidence is observed. It is not a new permanent project role, and C-03 does not prospectively validate it.

### Rationale

The frozen C-03 rules were applied as specified. Retaining the exact development classification and terminating before preregistration preserves prospective discipline, avoids result-dependent rescue, and permits an honest release of the state actually reached.

### Rejected alternatives

The following are rejected for this phase:

* post-C-03 modification or weakening of E3;
* removal of low-prevalence or low-budget cells;
* weakening the 48-of-48 structural-representation rule;
* best-epsilon selection;
* another evaluation seed or C-03 rerun;
* calculation of an unofficial aggregate over the 108 eligible cells;
* immediate PPI-2 or replacement-proxy search;
* describing C-03 as confirmatory;
* reclassifying C-03 as invalid or negative.

### Uncertainty

C-03 does not determine whether a differently designed future experiment could produce an informative or favourable PPI result. It establishes only that this frozen development design did not satisfy its prospective advancement conditions. The descriptive adverse pattern does not replace the undefined aggregate endpoint.

### Reversal condition

Before release and freeze, none. After release, further proxy development requires a separate explicit PI GO, a new prospective design identity, prospective decision-reachability review, and full compliance with any confirmatory requirements of that future phase.

## 56. Release contribution and claim boundary

### Decision

The completed release-positioning related-work review does not support a broad novelty claim.

The public release must not claim:

* a novel statistical method;
* a new general theory of verifier independence;
* firstness for verifier qualification;
* novelty of correlated-error or common-mode concerns;
* novelty of standard operating-characteristics or decision-reachability analysis.

The repository may describe its narrower contribution as:

* specialization of existing finite-population auditing machinery to the joint dangerous-error estimand for a synthetic primary/verifier pair inside a confident-agreement population;
* a fixed-oracle-budget research artifact;
* a reproducible development-terminal case study;
* a method-transfer stress test;
* a documented case in which a prospectively frozen structural gate terminated the selected development path before preregistration.

C-03 did not establish official aggregate superiority or inferiority of directed auditing. `INCONCLUSIVE_BY_DEGENERACY` remains the exact terminal scientific class.

Public documentation must distinguish the repository-internal paired perturbation-instability terminology from prediction-powered inference.

Related-work wording must explicitly credit inherited machinery and must not treat citation of prior work as validation of this repository.

### Rationale

Broad component claims are substantially represented in prior literature, whereas the repository's defensible value is narrower and lies in the exact specialization, implemented artifact, development evidence, and preserved failure path.

### Alternatives rejected

* broad novelty claim;
* firstness claim;
* describing C-03 as an official negative result;
* describing the method transfer as invention of the source machinery;
* omitting related-work qualification from the public release.

### Uncertainty

The bounded review does not prove that no closer work exists.

Absence of an identified exact predecessor is not a firstness claim.

### Reversal condition

A stronger novelty claim requires materially new external evidence or later post-release scientific evidence, together with a new explicit PI decision.

Discovery of materially closer prior work may further narrow, but may not silently strengthen, the public claim.
