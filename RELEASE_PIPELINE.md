# Release Pipeline

**Status:** ACCEPTED  
**Repository edition:** 2026-08-03  
**Accepted development baseline:** `0aaf49c86dabe42bc04ff5e3d05049c952250577`

This document defines the executable path from the accepted project direction to a tagged release and repository freeze. It governs source authority, preregistration, implementation, review visibility, review independence, development CI, confirmatory execution, deviation handling, result classification, release, and freeze.

This pipeline does not authorize implementation or Git operations by itself.

## Current stage

### Completed

* Phase 0 repository snapshot and historical baseline reconstruction;
* Phase 1B development-only statistical feasibility implementation;
* three independent Phase 1B implementation-audit rounds;
* ordinary merge of PR #3 at `0aaf49c86dabe42bc04ff5e3d05049c952250577`;
* installation and ordinary merge of the four canonical repository documents through PR #4 at `18aaa46c3dab99978f01707d7784624d761669ac`;
* comparative proxy review and methodological adjudication;
* designation of `paired_perturbation_instability` as the sole development primary candidate;
* exclusion of `evidence_path_overlap` from the current experiment;
* retention of confidence margin as the cheap baseline.

### In progress

* synchronization of the accepted PPI development method contract into the canonical repository documents.

### Next gate

* merge the exact method-contract synchronization;
* issue a separate bounded development-only implementation authorization;
* implement and validate Stage 1 plumbing before any Stage 2 feasibility sweep or preregistration drafting.

PPI usefulness has not been demonstrated. The primary proxy has not been frozen for confirmatory use. No confirmatory implementation or execution is authorized.

The merged Phase 1B prototype is development machinery. It is not the confirmatory implementation and does not satisfy the preregistration, CI, confirmatory-run, release, or freeze gates.

---

## 1. Pipeline objective

The current project phase must produce:

1. one approved and committed preregistration;
2. one bounded synthetic experiment;
3. one reproducible confirmatory result or documented invalid run;
4. one independent blind result audit;
5. one public tagged release;
6. one repository freeze.

The release must occur whether the result is:

* positive;
* negative;
* inconclusive;
* invalid.

An unfavourable result is not a reason to:

* restart without authorization;
* retune the generator;
* replace the primary proxy;
* change the endpoint;
* extend the experiment;
* delay release in search of a better result.

---

## 2. Canonical internal document set

Before confirmatory implementation begins, the repository must contain:

1. PROJECT_DIRECTION.md
2. PROJECT_DECISION_REGISTER.md
3. AUDIT_FINDINGS_REGISTER.md
4. RELEASE_PIPELINE.md
5. the approved preregistration document

The canonical documents must not materially contradict one another.

Where exact wording is required, the same sentence must be copied verbatim rather than paraphrased.

Historical sources may explain how a decision emerged.

They must not override the accepted canonical documents.

---

## 3. Canonical research question

The following question must appear verbatim in:

* PROJECT_DIRECTION.md;
* PROJECT_DECISION_REGISTER.md;
* the preregistration;
* the final methods documentation.

Within cases where the primary model and verifier confidently agree, can a preregistered oracle-free audit strategy improve estimation of their joint dangerous-error risk at a fixed oracle budget compared with random auditing?

No alternative phrasing may replace this question in the confirmatory protocol.

Explanatory paraphrases may appear in public-facing documentation only if they do not change:

* the agreement region;
* the risk-estimation estimand;
* the fixed-budget comparison;
* the random-audit baseline.

---

## 4. Canonical primary endpoint

The primary endpoint must be continuous.

At a fixed oracle budget, the experiment compares:

* a statistically valid upper confidence bound on joint dangerous-error risk;
* the width or tightness of that valid bound;
* or another preregistered continuous measure of qualification-relevant estimation performance.

The exact endpoint must be selected and fixed in the preregistration.

The following are secondary operational interpretations:

* whether the Blocking threshold is crossed;
* whether the Authorization threshold is crossed;
* at what oracle budget a threshold is crossed;
* how many dangerous errors are discovered;
* whether a sequential procedure stops before the maximum budget.

Raw error-discovery lift is diagnostic only.

It must not determine verifier qualification.

---

## 5. Retained rationale for the agreement region

The project studies confident agreement because common-cause dangerous errors may remain hidden precisely where the primary model and verifier agree.

High disagreement can reveal:

* inconsistent outputs;
* veto opportunities;
* obvious uncertainty;
* false-positive regimes;
* excessive blocking.

It does not directly solve the harder problem of joint false negatives in which both components produce the same dangerous answer.

A common-cause failure can therefore occur where observable disagreement is low:

D(x) ≈ 0

The agreement region is studied not because agreement proves correctness, but because agreement can conceal correlated failure.

The primary experiment must not be redirected toward disagreement sampling without a new recorded decision.

---

## 6. Source-hygiene gate

Repository and working-source hygiene

Historical material may be archived only after its durable decisions, findings, and provenance have been transferred into accepted repository documents.

Before archival, verify that:

* all material historical findings and corrections remain recorded;
* withdrawn claims and reasons remain visible;
* the agreement-region rationale remains preserved;
* review-process failures and controls remain recorded;
* no unique project decision exists only in an external working file;
* the repository migration note and replacement public README exist before the historical README is retired.

Historical Git commits must not be rewritten or deleted as part of source cleanup.

Working documents outside the repository are provenance inputs, not authority over a later accepted Git commit.

---

## 7. Review-visibility rule

No project-relevant review track may operate invisibly to the Project Manager.

Every review must record:

* exact question;
* reviewer identity and review role;
* materials supplied;
* full response;
* accepted findings;
* rejected findings;
* unresolved findings;
* resulting project decision.

The Project Manager must receive the full review before its conclusions are incorporated.

A verbal or written summary without the underlying review record is not sufficient provenance.

A conclusion from a hidden review track must not be counted as independent validation.

---

## 8. Neutral-review rule

A reviewer must not be assigned a position to defend.

Prohibited request

Defend why directed audit is useful.

Acceptable request

Evaluate whether the proposed audit design validly estimates joint dangerous-error risk, identify failure modes, and state which conclusions would or would not be supported.

The reviewer must not be told which experimental outcome is desired.

This applies to:

* the Lead Architect;
* preregistration reviewers;
* external auditors;
* external AI review systems;
* statistical reviewers;
* claims reviewers.

A response to an advocacy brief may contribute arguments.

It does not constitute independent methodological validation.

---

## 9. Independence of protocol review and result audit

The preregistration reviewer and final result auditor must be different reviewers.

The final result auditor must not:

* have approved the preregistration as its primary reviewer;
* have selected the primary proxy;
* have participated in implementation;
* have selected the confirmatory parameters;
* see the Project Manager’s result classification before producing an independent classification.

The result auditor receives the protocol and evidence but not the Project Manager’s assigned class.

The auditor independently classifies the result as:

* positive;
* negative;
* inconclusive;
* invalid.

After both classifications are recorded, they are compared.

Any disagreement must be:

* logged;
* investigated;
* preserved in the deviation or review record;
* disclosed in the release.

Agreement between the Project Manager and auditor is not treated as independent confirmation unless the required separation was preserved.

---

## 10. Roles

### Project Investigator

The Project Investigator approves project direction, final scope, canonical documents, preregistration, confirmatory-run authorization, commit and push, public release, repository freeze, and any post-release continuation.

### Project Manager

The Project Manager controls source authority, scope, review integration, conflict resolution, stage transitions, stop conditions, protocol-compliance review, preliminary result classification, and release discipline.

The Project Manager does not replace the independent result auditor.

### Lead Architect

The Lead Architect reviews the research question, estimand, endpoint, sampling design, proxy realizability, estimator, sequential baseline, stopping rule, failure/restart rule, and opportunities for researcher discretion.

The Lead Architect does not independently authorize implementation, confirmatory execution, release, or continuation.

### Preregistration reviewer

A neutral preregistration reviewer examines the protocol before commit and must not serve as final result auditor.

### Final result auditor

The final result auditor reviews protocol compliance, inspects confirmatory artifacts, independently classifies the result, evaluates claim-to-evidence alignment, and does not see the Project Manager classification in advance.

### Executor

The Executor may inspect approved files, implement approved specifications, run tests, produce artifacts, maintain the deviation log, and prepare commit packets.

The Executor may not redefine the research question, endpoint, primary proxy, generator parameters, authority thresholds, result classes, scope, release outcome, or commit authority.

---

## 11. Phase 0 — Repository snapshot

Before editing:

1. inspect the current repository;
2. record the remote URL;
3. record all relevant branches;
4. record current HEAD;
5. record working-tree status;
6. record index status;
7. list repository files;
8. run existing public commands;
9. record failures without silently repairing them;
10. scan for credentials and private material;
11. record existing tags, CI, issues, and pull requests.

### Output

A read-only repository snapshot report.

### Stop conditions

Stop if:

* the local repository is not the expected repository;
* uncommitted work exists and ownership is unclear;
* credentials or private data are present;
* the repository state cannot be tied to a commit hash;
* the historical baseline cannot be reconstructed sufficiently for migration.

---

## 12. Phase 1 — Canonical-document synchronization

Before preregistration:

* verify the canonical research question is identical across documents;
* verify the endpoint is continuous;
* verify threshold crossing is secondary;
* verify the agreement-region rationale is preserved;
* verify AF-16 and AF-17 are present;
* verify all withdrawn propositions are recorded;
* verify the sequential baseline is required;
* verify proxy circularity is prohibited;
* verify the four result classes are preserved;
* verify release-before-continuation remains mandatory.

### Required search

Search canonical documents for:

* competing research-question wording;
* discovery language replacing estimation language;
* lift used as an authority rule;
* binary primary-endpoint language;
* missing sequential baseline;
* proxy access to hidden truth;
* old 70 ms claims;
* active P1–P3 claims;
* claims that agreement establishes independence;
* automatic unverified fallback under time pressure.

### Gate

Preregistration drafting must not begin until material contradictions are removed.

---

## 13. Phase 2 — Preregistration requirements

The preregistration must fix:

* canonical research question;
* unit of analysis;
* target population;
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
* fixed-budget random-audit baseline;
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
* positive-result rule;
* negative-result rule;
* inconclusive-result rule;
* invalid-result rule;
* deviation-classification rules;
* blind-audit question.

---

## 14. Failure and restart rule

The preregistration must separately define what happens if a confirmatory run fails operationally.

This is distinct from statistical stopping.

The failure/restart rule must define:

* what counts as an execution failure;
* which failures allow restart;
* which failures invalidate the run;
* whether the same manifest may be reused;
* whether a new manifest is required;
* whether code changes are permitted;
* who authorizes restart;
* how the failure is recorded;
* how partial output is handled;
* whether exposure to partial results prevents a confirmatory restart.

### Default rule

A confirmatory run must not be silently restarted.

A restart requires:

* an applicable preregistered rule;
* a deviation-log entry;
* Project Manager review;
* Project Investigator authorization.

If code or analytical logic changes after partial confirmatory results are observed, the run is invalid unless the preregistration explicitly provided for that exact condition.

---

## 15. Proxy-realizability gate

Before a proxy enters the preregistration, it must pass all six conditions:

1. It is computed only from observable information.
2. It does not use the true label before oracle review.
3. It does not use the hidden common-cause variable.
4. Its relationship to error is not assigned through a direct generator parameter.
5. Its implementation can be described independently of the desired result.
6. It can be reproduced from stored experiment inputs and outputs.

A proxy failing any condition is excluded before preregistration.

A proxy must not be rescued by changing the generator so that the proxy becomes predictive by construction.

There will be one primary proxy.

All other confirmatory proxies are secondary.

---

## 16. Development and confirmatory separation

Development work may use:

* dedicated development seeds;
* development-only scenario manifests;
* synthetic cases designed to expose bugs;
* deliberately easy cases used to test estimator behaviour;
* deliberately adverse cases used to test coverage failure;
* simulated invalid cases used to test result classification.

Development outputs must not enter the confirmatory result.

The confirmatory manifest must remain inaccessible to:

* proxy selection;
* parameter adjustment;
* development CI;
* estimator tuning;
* result-dependent design changes.

The confirmatory manifest may be exposed only after:

* preregistration is committed;
* implementation is complete;
* development CI passes;
* the implementation commit is fixed;
* the Project Investigator authorizes the confirmatory run.

---

## 17. Preregistration review

The preregistration receives at least two reviews before commit.

Lead Architect review

The Lead Architect checks:

* research question;
* endpoint;
* estimand;
* proxy realizability;
* estimator;
* sampling design;
* sequential method;
* stopping rule;
* failure/restart rule;
* result classes;
* opportunities for post hoc movement.

Neutral external preregistration review

The reviewer checks:

* whether the protocol answers the stated question;
* whether the primary endpoint is interpretable;
* whether negative and underpowered results can be distinguished;
* whether generator design predetermines the result;
* whether proxy circularity remains possible;
* whether hidden researcher discretion remains;
* whether the confirmatory run can be reproduced from the committed protocol.

### Gate

All material objections must be:

* accepted and incorporated;
* explicitly rejected with reasons;
* or marked unresolved and treated as a blocker.

The preregistration reviewer must not later serve as final result auditor.

---

## 18. Preregistration commit

The approved preregistration must be committed before confirmatory evaluation.

The commit must contain:

* canonical documents;
* preregistration;
* scenario specification;
* development/confirmatory separation specification;
* parameter manifest specification;
* analysis specification;
* stopping rule;
* failure/restart rule;
* result-classification rules;
* planned tables or result schema;
* deviation-log template.

The commit hash becomes the protocol identifier.

The preregistration document may also receive a content hash.

No confirmatory result may be associated with an uncommitted protocol.

---

## 19. Implementation branch

Experimental implementation occurs on a separate branch or pull request.

The implementation task must specify:

* working directory;
* goal;
* allowed files;
* forbidden files;
* dependencies;
* validation commands;
* expected outputs;
* stop conditions;
* reporting format;
* no-commit/no-push boundary.

No opportunistic refactor is allowed.

No new item may be introduced without a recorded decision, including:

* proxy;
* scenario family;
* model provider;
* application domain;
* major dependency;
* alternative endpoint;
* new authority state.

---

## 20. Development CI gates

Development CI must fail on:

1. Python syntax failure.
2. Import failure.
3. Unit-test failure.
4. Public command failure.
5. Non-deterministic reproduction under a fixed development manifest.
6. Estimator coverage below the preregistered development-test requirement.
7. Invalid inclusion probabilities or weights.
8. Proxy access to forbidden hidden fields.
9. Missing expected result fields.
10. Incorrect stopping behaviour.
11. Incorrect restart-rule handling.
12. Unbalanced Markdown fences in public documentation.
13. Presence of secrets or credential-like files.
14. Presence of generated cache files in tracked content.

### Confirmatory-manifest restriction

Estimator-coverage CI must run only on:

* development scenarios;
* development manifests;
* synthetic unit-test cases.

The confirmatory manifest must remain inaccessible to CI until the Project Investigator authorizes the confirmatory run.

No CI log, cache, artifact, preview, or failure message may reveal confirmatory outcomes before authorization.

---

## 21. Minimum CI jobs

The minimum development CI suite includes:

* syntax and import check;
* unit tests;
* deterministic-seed test;
* paired-scenario test;
* proxy-isolation test;
* inclusion-probability test;
* estimator coverage test using development scenarios only;
* sequential-stopping test;
* restart-rule test;
* public smoke run;
* documentation check;
* sensitive-file scan.

CI demonstrates only that the tested properties passed.

It does not establish real-world safety or domain validity.

---

## 22. Required test classes

The implementation must test:

* deterministic agreement classification;
* joint-dangerous-error labeling;
* random-audit sampling;
* directed-audit sampling;
* sequential baseline behaviour;
* inclusion-probability calculation;
* inverse weighting or other correction;
* upper-bound calculation;
* empirical coverage on development scenarios;
* maximum-budget stopping;
* early stopping;
* inconclusive-result handling;
* invalid-result detection;
* failure/restart handling;
* fixed-seed reproduction;
* paired underlying scenarios;
* proxy isolation from hidden truth;
* absence of automatic unverified fallback;
* expected result-schema generation.

---

## 23. Deviation log

A deviation log is required even if no deviation occurs.

The executor creates and maintains the log.

The Project Manager reviews and confirms it.

Each entry must record

* deviation ID;
* date and time detected;
* stage of the pipeline;
* what the preregistration or pipeline required;
* what actually occurred;
* how the deviation was detected;
* affected files, runs, manifests, or outputs;
* whether confirmatory results had already been exposed;
* whether the primary endpoint may be affected;
* whether secondary outcomes may be affected;
* preliminary severity;
* corrective action;
* restart decision, if relevant;
* Project Manager determination;
* Project Investigator authorization, where required;
* final effect on result classification.

### Empty deviation log

If no deviations occurred, the log must state:

No deviations identified.

The executor signs or identifies the generated record.

The Project Manager confirms the empty log before release.

### Late discovery

A deviation found after the confirmatory run or after preliminary classification must still be recorded.

Late discovery may change the result class to invalid.

A deviation is not waived because it was discovered late.

---

## 24. Pre-confirmatory validation

Before the confirmatory run:

* development CI must pass;
* the working tree must be clean;
* the implementation commit must be identified;
* the preregistration commit must be identified;
* development outputs must be separated;
* the confirmatory manifest must be fixed and sealed;
* no open methodological blocker may remain;
* the deviation log must exist;
* the restart rule must be executable;
* preregistration reviewer and final auditor must be assigned as different reviewers.

### Required review

The Project Manager checks protocol compliance.

The executor reports exact validation output.

The Project Investigator authorizes access to the confirmatory manifest and execution of the run.

---

## 25. Confirmatory-run rule

The confirmatory run must use:

* the committed implementation;
* the committed preregistration;
* the sealed scenario manifest;
* the fixed oracle budget or budgets;
* the fixed primary proxy;
* the fixed secondary proxies;
* the fixed baselines;
* the fixed analysis code;
* the fixed stopping rule;
* the fixed failure/restart rule.

No code or parameter change is permitted during the run.

No secondary proxy may be promoted to primary after seeing results.

A failure during execution triggers:

* a deviation-log entry;
* application of the preregistered failure/restart rule;
* Project Manager review;
* Project Investigator decision where restart is permitted.

It does not authorize silent repair and continuation.

---

## 26. Project Manager result classification

After the confirmatory artifacts are complete, the Project Manager assigns a preliminary result class from preregistered rules.

### Positive

The primary strategy improves the continuous primary endpoint with valid coverage and achieves the preregistered practical effect.

### Negative

The strategy fails to achieve the required advantage, and the experiment has enough precision to exclude that advantage under the tested conditions.

### Inconclusive

The experiment cannot distinguish a practically useful effect from insufficient performance.

### Invalid

The protocol was materially violated, coverage failed, implementation was incorrect, hidden tuning occurred, the manifest was exposed prematurely, or another validity condition failed.

The Project Manager classification is recorded privately before the independent audit.

It is not supplied to the final auditor.

---

## 27. Independent blind result audit

The final auditor must be different from the preregistration reviewer.

The auditor receives:

* preregistration;
* preregistration hash;
* implementation hash;
* confirmatory artifacts;
* CI output;
* analysis report;
* deviation log;
* relevant review records;
* permitted and prohibited claim language.

The auditor does not receive:

* the Project Manager classification;
* a preferred result;
* a request to defend the project;
* an instruction to preserve a positive claim.

The auditor is asked:

Based only on the preregistered protocol and observed evidence, classify the result as positive, negative, inconclusive, or invalid, and identify any claim that exceeds the evidence.

The auditor submits:

* independent result class;
* rationale;
* protocol deviations found;
* evidence-strength assessment;
* permitted public conclusion;
* prohibited overstatement;
* unresolved issues.

---

## 28. Classification reconciliation

After the auditor submits an independent classification, the Project Manager and auditor classes are compared.

If classifications agree

The agreement is recorded.

It is not described as independent validation beyond the scope of the two reviews.

If classifications differ

The disagreement must be:

* logged;
* preserved;
* analyzed against the preregistration;
* disclosed in the release documentation.

The Project Investigator does not select the more favourable class by preference.

The release must state:

* Project Manager classification;
* auditor classification;
* reason for disagreement;
* final release wording;
* unresolved uncertainty.

A disagreement may lead to an invalid or inconclusive release if the protocol does not resolve it.

---

## 29. Release gate

Release requires:

* accepted canonical documents;
* committed preregistration;
* passing development CI;
* completed confirmatory run or documented invalid run;
* reproducible result artifacts;
* completed deviation log;
* Project Manager classification;
* independent auditor classification;
* classification reconciliation;
* final limitations;
* security scan;
* license check;
* approved README;
* migration note;
* release notes;
* immutable tag.

Release does not require a favourable result.

---

## 30. Public release contents

The public repository must contain:

* README;
* project scope and non-goals;
* preregistration;
* methods;
* experiment code;
* tests;
* CI configuration;
* results;
* expected reproduction command;
* limitations;
* related work;
* migration note;
* deviation log;
* result-audit record or summary;
* citation metadata;
* license;
* release tag.

The README must identify:

* result class;
* Project Manager/auditor disagreement, if any;
* preregistration commit;
* implementation or release commit;
* reproduction command;
* validated scope;
* domains not validated;
* prohibited interpretations.

---

## 31. Migration note

The migration note must state that the prior repository identity was retired.

It must record withdrawal of:

* the old latency scenario;
* the approximately 70 ms crossover;
* the P1–P3 evidence claim;
* the old LLM-versus-world-model demonstration;
* the automatic LLM-only fallback under time pressure;
* the old publish-ready status;
* any direct conversion of error-discovery lift into authority qualification.

The migration note must not suggest that the previous project was validated and merely renamed.

---

## 32. Commit and push gate

Before each commit, the executor returns a commit packet containing:

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

No commit or push occurs without the exact Project Investigator approval:

Approved commit and push

After push, the executor returns:

* repository;
* branch;
* commit hash;
* commit message;
* pushed file count;
* validation summary;
* deviations;
* remaining limitations.

---

## 33. Release before continuation

The tagged release must be completed before a new research phase begins.

This applies even after a positive result.

Prohibited before release:

* new primary or secondary proxies;
* real-model testing;
* domain-specific validation;
* product planning;
* new architecture work;
* JEPA;
* world models;
* knowledge graphs;
* additional confirmatory runs intended to improve the result;
* silent amendment of the preregistration.

A positive result creates a decision opportunity.

It does not automatically authorize continuation.

---

## 34. Repository freeze

After release, the repository enters a frozen state for the current phase.

Allowed without a new GO:

* critical security fixes;
* citation corrections;
* reproducibility repairs;
* documentation corrections that do not alter the result;
* environment fixes required to reproduce the tagged release.

Not allowed without a new GO:

* new scientific claims;
* new proxies;
* new datasets;
* real-provider evaluation;
* new domains;
* changed thresholds;
* changed estimands;
* expanded architecture;
* productization.

---

## 35. Stop conditions

The pipeline stops if:

* the research question becomes broader;
* the primary endpoint changes after preregistration;
* the primary proxy changes after preregistration;
* proxy circularity is discovered;
* generator tuning predetermines the result;
* negative and underpowered outcomes cannot be distinguished;
* estimator coverage fails;
* confirmatory data are exposed before authorization;
* CI cannot reproduce the public result;
* implementation diverges from preregistration;
* an unpermitted restart occurs;
* a hidden review track affects decisions;
* a reviewer receives a desired position to defend;
* preregistration reviewer and final auditor are the same reviewer;
* the final auditor sees the Project Manager class before independent classification;
* release claims exceed evidence;
* a serious security, privacy, or licensing issue is found.

Continuation requires:

* a written Project Investigator decision;
* an updated protocol version;
* a new commit hash;
* a clear determination of whether the prior run is invalid.

---

## 36. Terminal state

The phase is complete when:

1. the four canonical internal documents are accepted;
2. the preregistration is committed;
3. implementation is complete;
4. development CI passes;
5. the confirmatory run is completed or classified invalid;
6. the Project Manager classification is recorded;
7. the independent blind audit is completed;
8. classification disagreement is resolved or disclosed;
9. the release is tagged;
10. temporary source files are safely removed;
11. the repository is frozen.

---

## 37. Current authorized next step

1. Complete and merge the canonical PPI development method-contract synchronization.
2. After that merge, prepare one separately authorized bounded development-only implementation task covering only:
   * structural PPI generator plumbing;
   * frozen transformation bank;
   * confidence-margin baseline;
   * five development arms;
   * common equal-weight lambda mixture;
   * compact sweep summaries;
   * bounded replay-grade traces;
   * mandatory negative and falsification controls;
   * Stage 1 plumbing validation.
3. Review Stage 1 evidence before authorizing:
   * Stage 2 development feasibility mapping;
   * parameter calibration;
   * proxy freeze;
   * preregistration drafting.
4. Draft the preregistration only after:
   * the designated proxy passes its development gate;
   * the method parameters required for preregistration are fixed through recorded decisions;
   * a separate authorization is issued.

This pipeline does not itself authorize implementation, Stage 1 execution, Stage 2 execution, preregistration approval, confirmatory implementation, confirmatory execution, repository rename, replacement of the historical root README, creation or exposure of a confirmatory manifest, commit, push, merge, or release.
