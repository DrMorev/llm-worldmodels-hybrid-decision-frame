# Audit Findings Register

**Status:** ACCEPTED  
**Repository edition:** 2026-08-03  
**Historical audited base:** `78625876d4b36fbaf8a6da5b9f0b28bb27bac694`  
**Accepted development merge:** `0aaf49c86dabe42bc04ff5e3d05049c952250577`

This register consolidates verified historical defects, methodological failures, process failures, corrections, withdrawn claims, retained lessons, and the closure state of the Phase 1B development implementation.

Historical findings describe the identified snapshot or process. They are not silently promoted into claims about the current repository without fresh evidence.

## Purpose

The previous repository is being substantially redirected.

Most of its old code and scientific claims will not remain active.

The audit remains relevant because it shows how the previous project failed at:

* reproducibility;
* claim control;
* fair comparison;
* documentation-to-code consistency;
* release qualification;
* fail-closed reasoning;
* review independence;
* review provenance;
* separation of discovery from risk estimation.

The purpose of this register is not to repair every historical file.

The purpose is to prevent the same failure classes from entering the new experiment.

Deleting an affected file does not by itself close a finding.

---

## Source and evidence boundary

This register draws from:

* the original repository audit;
* the independent Git and release audit;
* the meta-review correcting overstatements in the first audit;
* the accepted Project Direction;
* the accepted Project Decision Register;
* the approved release-pipeline design;
* recorded review-process failures from the research round.

Repository findings describe the audited snapshot, not an assumed current repository state.

Process findings describe the documented review process, not Git runtime behaviour.

A fresh repository inspection remains mandatory before each new implementation stage or current-state claim.

---

## Audited repository snapshot

The independent Git audit reported:

* repository: sergey-morev/llm-worldmodels-hybrid-decision-frame;
* branch: main;
* audited HEAD: 78625876d4b36fbaf8a6da5b9f0b28bb27bac694;
* working tree: clean;
* index: clean;
* local main matched origin/main;
* git fsck --full passed;
* no release tag existed;
* no CI or status checks were attached to HEAD;
* the historical commit-3-latency branch was already merged into main.

No files were edited, committed, or pushed during those audits.

### Limitation

These observations apply only to the audited snapshot.

They must not be presented as the repository’s current condition after later changes.

---

## Evidence and lifecycle labels

VERIFIED

Directly observed in repository contents, Git history, or runtime execution.

REPRODUCED

Observed through a documented command or repeated run.

SUPPORTED

Strongly supported by code, documentation, or review-record inspection but not independently reproduced across environments.

CONTESTED

The underlying issue is real, but part of the original wording was too broad, too absolute, or inaccurate.

WITHDRAWN CLAIM

A previous public or internal claim is no longer accepted as evidence.

PROCESS FINDING

A defect in review framing, independence, visibility, provenance, or decision integration.

HISTORICAL LESSON

The original implementation or process may be removed, but its failure mode must remain documented.

OPEN

The issue remains relevant to the new project and requires a preventive or corrective control.

RETIRED

The old component will not be repaired or retained as an active artifact.

CLOSED

The required evidence has been produced and independently checked.

A finding is not closed merely because:

* a file was deleted;
* wording was softened;
* a limitation was added;
* a replacement was proposed;
* the team agreed that the defect mattered.

---

## Retained rationale: why the experiment studies agreement

This rationale is a durable intellectual result of the research round.

Let D(x) represent an observable measure of disagreement or output divergence between the primary model and verifier.

A tempting strategy is to audit cases with high D(x).

That strategy may be useful for detecting:

* inconsistent outputs;
* veto opportunities;
* false-positive regimes;
* excessive blocking;
* obvious model conflict.

It does not directly target the hardest dangerous-error regime.

A common-cause joint false negative can occur when:

* both components share the same failure cause;
* both produce the same wrong answer;
* both express high confidence;
* observable disagreement remains low;
* D(x) ≈ 0.

Therefore:

Common-cause dangerous failure can remain concentrated inside the confident-agreement region rather than the high-disagreement region.

High disagreement is often useful for discovering conflict.

It is not automatically the best region for estimating joint dangerous-error risk.

The primary experiment studies agreement because agreement can conceal correlated failure.

Redirecting the experiment toward disagreement sampling requires a new recorded decision and must not occur through an informal reinterpretation of the proxy.

---

## Summary verdict

The old repository was Git-clean but not release-ready.

Its documentation presented a disciplined architectural framework, but executable evidence did not support several central claims.

The most serious failures were:

1. a public experiment file was never valid Python;
2. numerical results were presented without a reproducible generator;
3. the main demonstration did not reliably demonstrate its assigned mechanism;
4. the compared modes did not receive controlled equivalent random inputs;
5. a latency experiment was interpreted as evidence about model scaling;
6. safety documentation and execution order conflicted;
7. release readiness was claimed without tests, CI, tags, or functioning public entry points;
8. time pressure was treated as a possible reason to remove verification;
9. error discovery was conflated with population-risk estimation;
10. review independence and review visibility were not adequately controlled.

The active project must not inherit any scientific result from the old prototype.

---

Repository and methodology findings

## AF-01 — The latency scenario was not executable

### Severity

BLOCKER

### Status

VERIFIED / WITHDRAWN CLAIM / RETIRED

### Affected file

prototype/scenarios/latency_bound.py

### Observed condition

The file was not valid Python.

The audits identified:

* typographic quotation marks;
* Markdown fences inside the module;
* malformed from __future__ import annotations;
* lost indentation;
* syntax failure at the first line.

Git-history inspection indicated that the file was invalid in the commit that introduced it.

No known valid historical version existed in the audited repository.

### Impact

The documented latency experiment could not be executed.

Any result attributed to that file lacked a reproducible implementation.

### Current disposition

Do not repair the file merely to preserve the old claim.

The scenario is retired from the active scientific project.

Git history remains as provenance.

### Closure criterion

Closed for the new release only when:

* the scenario is absent from the active run path;
* no public documentation presents it as functioning evidence;
* the migration note states that it was withdrawn;
* the new experiment has a tested entry point.

---

## AF-02 — The approximately 70 ms crossover was unsupported

### Severity

BLOCKER

### Status

VERIFIED / WITHDRAWN CLAIM

### Affected material

docs/commit3_analysis.md and any surface repeating the crossover.

### Observed condition

The documentation reported:

* completion values around 46.7% and 50%;
* a crossover near 70 ms.

The file presented as generating those results was not executable and had never been valid in the audited history.

### Impact

A precise quantitative conclusion was presented without a reproducible evidence path.

### Current disposition

The approximately 70 ms result is withdrawn.

It must not be:

* restored in the new README;
* cited elsewhere as a reproducible empirical result;
* described as a measured architectural threshold;
* recreated by adjusting code to fit the old table;
* reused as an input or target for the new experiment.

The general principle that verification consumes time remains valid.

The old number does not.

### Closure criterion

Closed when:

* active documentation removes the number;
* historical mentions are labeled withdrawn and non-reproducible;
* the new experiment does not use it.

---

## AF-03 — Public run instructions were inconsistent

### Severity

MAJOR

### Status

VERIFIED / CONTESTED

### Observed condition

The public execution surface was inconsistent:

* python -m prototype.example_run executed;
* python -m prototype.scenarios.latency_bound failed;
* docs/commit3_analysis.md supplied a cd prototype form incompatible with the relative imports.

### Correction

The first audit overstated how many documents contained the wrong command.

Specifically:

* prototype/README.md did not contain the claimed command;
* docs/repo_snapshot.md contained the root-level form;
* the incompatible cd prototype form appeared in docs/commit3_analysis.md.

The core finding remains valid: the repository did not provide one consistently functioning public run path.

### Current disposition

Old run instructions will be retired with the old prototype.

### Closure criterion

Closed when:

* every active documented command runs in clean CI;
* commands execute from the repository root;
* README, tests, and expected output agree;
* no obsolete command remains active.

---

## AF-04 — README contained an unclosed code fence

### Severity

MINOR technically / MAJOR for publication hygiene

### Status

VERIFIED / CONTESTED

### Observed condition

The old README opened a fenced code block in Quick Run without closing it.

### Correction

The first audit said GitHub rendering would necessarily break.

That was too absolute.

GitHub may implicitly close a final code fence.

The supported finding is:

* the Markdown was malformed;
* rendering could be misleading;
* the README did not meet publication-quality standards.

### Current disposition

The old README will be replaced.

### Closure criterion

Closed when:

* the new README renders correctly;
* fenced blocks are balanced;
* public commands can be copied directly;
* the rendered GitHub page is checked before release.

---

## AF-05 — The main demonstration did not reliably show its stated mechanism

### Severity

MAJOR

### Status

REPRODUCED / WITHDRAWN CLAIM / RETIRED

### Affected material

prototype/example_run.py and related documentation.

### Claimed mechanism

The prototype was intended to show:

* LLM-only mode silently drifting from its own predicted state;
* hybrid mode grounding itself through observation.

### Observed behaviour

The uncertainty rule frequently stopped both modes before that contrast could emerge.

The deep audit reported that across 300 hybrid-mode seeds:

* 245 runs stopped through uncertainty too high;
* 55 reached the target.

The default example showed both modes failing early for substantially the same reason.

### Impact

The script executed but did not reliably demonstrate the thesis assigned to it.

### Rejected correction

Do not alter a few constants until the preferred visual result appears.

That would fit the demonstration to the conclusion.

### Current disposition

The demonstration is retired.

### Closure criterion

Closed when the new experiment:

* defines expected properties before implementation;
* separates development and confirmatory scenarios;
* freezes generator parameters;
* permits positive, negative, inconclusive, and invalid results;
* is not tuned to manufacture a preferred result.

---

## AF-06 — Mode comparison used an uncontrolled random sequence

### Severity

MAJOR

### Status

VERIFIED / RETIRED

### Affected file

prototype/example_run.py

### Observed condition

A single global seed was set before sequential execution of:

1. llm_only;
2. hybrid.

The second mode consumed a later segment of the random-number stream.

The modes therefore did not receive paired equivalent stochastic conditions.

### Impact

Observed differences could reflect different random draws rather than the architecture being compared.

### Current disposition

The old comparison is not accepted as evidence.

The new project must use:

* explicit local random generators;
* paired latent scenarios;
* recorded seed manifests;
* deterministic reruns;
* separation of development and confirmatory seeds.

### Closure criterion

Closed when tests show that:

* compared strategies receive the same underlying case;
* no uncontrolled global RNG state is shared;
* fixed manifests reproduce identical output.

---

## AF-07 — The P3 claim was not supported by the experiment

### Severity

MAJOR

### Status

VERIFIED / WITHDRAWN CLAIM

### Affected material

docs/commit3_analysis.md and the P1–P3 framing.

### Observed condition

The limitations document treated P3 as unresolved.

The analysis nevertheless described the latency scenario as evidence for P3.

P3 concerned scaling and diminishing marginal benefit from tools or planning.

The experiment varied latency, not scale.

### Impact

The manipulated variable did not match the hypothesis.

A latency sweep cannot establish a scale claim without a scale axis.

### Current disposition

P1, P2, and P3 are removed from the active project identity.

### Closure criterion

Closed when:

* P3 is absent from active scientific claims;
* the migration note records its withdrawal;
* no latency result is converted into a scale conclusion.

---

## AF-08 — Invariant checks occurred after the action

### Severity

MAJOR / SAFETY-RELEVANT

### Status

VERIFIED / HISTORICAL LESSON

### Affected material

* prototype/README.md;
* prototype/loop_skeleton.py.

### Observed condition

The documentation required invariants to be checked before an action.

The implementation called env.step() before performing the documented checks.

### Impact

A state-changing operation could occur before the system determined that the action violated an invariant.

### Retained principle

A control described as pre-action authorization must execute before the protected action.

Post-action observation may detect harm.

It is not pre-action authorization.

### Current disposition

The old loop will not be reused as the active architecture.

### Closure criterion

Closed when the new implementation:

* distinguishes selection, audit, oracle review, qualification, and action;
* tests the intended order;
* does not describe post-action detection as a pre-action gate.

---

## AF-09 — Configuration fields did not control behaviour

### Severity

MODERATE

### Status

VERIFIED / RETIRED

### Affected elements

* PrototypeConfig.max_context;
* verification_type.

### Observed condition

max_context was declared but unused.

verification_type was passed through multiple locations but did not switch the verification mechanism.

Behaviour was controlled through a separate hard-coded mode.

### Impact

The interface implied configurability that the implementation did not possess.

### Current disposition

Do not carry the old configuration classes into the new project.

### Closure criterion

Closed when:

* unused public parameters are absent;
* configuration-to-behaviour mapping is tested;
* every documented parameter has an observable effect.

---

## AF-10 — The latency interlock was nominal rather than demonstrated

### Severity

MODERATE

### Status

SUPPORTED / CONTESTED / RETIRED

### Affected file

prototype/loop_skeleton.py

### Observed condition

The loop compared toy-code execution time with an approximately 250 ms budget.

The normal demo did not meaningfully exercise the interlock.

The dedicated latency scenario was invalid.

### Correction

The first audit said the interlock could not activate in principle.

That wording was too absolute.

The supported finding is:

* no test demonstrated the intended behaviour;
* the normal demo did not meaningfully exercise it;
* measured toy execution time did not represent a validated end-to-end action window.

### Current disposition

The old interlock is retired.

Latency is not a primary variable in the new experiment.

### Closure criterion

Closed when:

* the active README does not claim a tested latency gate;
* any future latency experiment uses explicit end-to-end timing and separate preregistration.

---

## AF-11 — The repository lacked minimum automated release checks

### Severity

MAJOR FOR RELEASE READINESS

### Status

VERIFIED / OPEN

### Observed condition

The audited snapshot lacked:

* .gitignore;
* automated tests;
* CI;
* status checks;
* a release tag.

Running the repository could create tracked-environment noise such as __pycache__.

### Impact

A syntax error in a documented public entry point reached a state described as release-ready.

### Current disposition

The new release must include:

* .gitignore;
* syntax and import checks;
* unit tests;
* deterministic reproduction tests;
* proxy-isolation tests;
* estimator coverage tests on development scenarios;
* a public smoke test;
* CI;
* an immutable release tag.

Confirmatory manifests must not be exposed to development CI.

### Closure criterion

Closed when:

* CI passes from a clean checkout;
* all active public entry points run;
* public test commands are documented;
* the release commit is green;
* the release has an immutable tag.

---

## AF-12 — “Publish-ready” and version claims were unsupported

### Severity

MAJOR FOR CLAIM HYGIENE

### Status

VERIFIED / WITHDRAWN CLAIM

### Affected material

docs/repo_snapshot.md

### Observed condition

The snapshot described the repository as:

* v1.1;
* publish-ready.

At the same time:

* no corresponding tag existed;
* one public entry point failed;
* CI and tests were absent;
* documentation and implementation conflicted.

### Impact

The maturity label exceeded the evidence.

### Current disposition

The old readiness and version claims are withdrawn.

The current project status remains:

SEED moving toward preregistered BUILD.

The word reproducible must not describe the active repository until a technically competent external reader can reproduce the tagged result from a clean checkout.

### Closure criterion

Closed when:

* status is tied to a commit and tag;
* acceptance criteria pass;
* README maturity language matches observed evidence.

---

## AF-13 — Research bibliography was incomplete

### Severity

MODERATE / BLOCKER FOR STRONG NOVELTY CLAIMS

### Status

SUPPORTED / OPEN

### Affected file

research/core_sources.md

### Observed condition

Most listed sources lacked complete identifiers such as:

* DOI;
* arXiv ID;
* official publication URL;
* full bibliographic information.

### Impact

Readers could not reliably determine which source supported which proposition.

### Current disposition

The old source file will not automatically define the new related-work section.

The new project requires a focused review tied to the final question.

Each retained source should record:

* full citation;
* stable identifier;
* publication status;
* exact proposition supported;
* proposition not established;
* unresolved limitations.

### Closure criterion

Closed when:

* material research claims have traceable sources;
* identifiers are complete;
* unsupported novelty language is removed;
* citation residue generated by AI systems is absent.

---

## AF-14 — The old hypotheses were inconsistently defined

### Severity

MODERATE

### Status

SUPPORTED / RETIRED

### Observed condition

P1 and P2 appeared in several documents but were strictly defined only in an internal snapshot.

P3 was formalized elsewhere.

The repository did not expose one stable hypothesis surface.

### Impact

A reader could not determine which exact formulation the analysis tested.

### Current disposition

The P1–P3 structure is retired.

The new project has one canonical research question.

### Closure criterion

Closed when the preregistration consistently defines:

* unit of analysis;
* estimand;
* endpoint;
* baselines;
* qualification thresholds;
* result classes.

---

## AF-15 — Verification could be removed under time pressure

### Severity

CRITICAL ARCHITECTURAL LESSON

### Status

HISTORICAL LESSON / OPEN

### Source status

This finding was elevated during the later architecture and Project Manager review.

It was not the central finding of the two initial repository audits.

### Observed design problem

The old reasoning allowed fallback to LLM-only operation when the verified or hybrid path exceeded the latency budget.

### Why this is unsafe

A time constraint can disqualify a verification path.

It does not qualify an unverified path.

The system must not reason:

There is not enough time to verify, therefore the unverified action is permitted.

### Accepted alternatives

Depending on the intended application:

* abstain;
* stop;
* defer;
* escalate;
* use a separately qualified fast path;
* use a deterministic safety controller.

### Current disposition

The old code path may be deleted.

The negative lesson must remain in the migration note and limitations.

### Closure criterion

Closed when:

* no automatic unverified fallback exists in the active project;
* the README states the principle;
* applicable fail-closed behaviour is tested.

---

Review-process findings

## AF-16 — The adversarial brief assigned a position to defend

### Severity

MAJOR PROCESS DEFECT

### Status

PROCESS FINDING / HISTORICAL LESSON / OPEN

### Observed process

An external or adversarial review was framed around defending an assigned position rather than neutrally evaluating the project question.

The reviewer was effectively asked to argue for a conclusion.

### Impact

The resulting response could demonstrate that a position was defensible.

It could not serve as independent evidence that the position was correct.

The framing increased the probability of:

* confirmation bias;
* selective argument;
* omission of disconfirming evidence;
* false appearance of adversarial validation.

### Retained principle

A reviewer must be asked to evaluate:

* whether the protocol answers the question;
* where it fails;
* what outcome would be supported;
* what outcome would not be supported.

The reviewer must not be told which conclusion the project wants.

### Current disposition

The old brief is not accepted as independent validation.

Any useful arguments from it must stand on their own evidence.

### Closure criterion

Closed when:

* preregistration and result-review prompts are neutral;
* the exact question and full response are preserved;
* accepted and rejected findings are logged;
* no assigned-position review is counted as independent confirmation.

---

## AF-17 — A parallel review track operated without Project Manager visibility

### Severity

MAJOR GOVERNANCE AND PROVENANCE DEFECT

### Status

PROCESS FINDING / HISTORICAL LESSON / OPEN

### Observed process

A project-relevant review track occurred without full visibility to the Project Manager.

The Project Manager did not have complete access to:

* the exact brief;
* the materials supplied;
* the full response;
* the reviewer’s role;
* the reasoning behind accepted or rejected conclusions.

### Impact

This created:

* incomplete decision provenance;
* risk of incorporating conclusions without their limitations;
* hidden conflict between review tracks;
* inability to distinguish independent evidence from summarized advocacy;
* dependence on one person’s retelling of another review system’s result.

### Retained principle

No review affecting project scope, method, claims, or release classification may remain invisible to the Project Manager.

A summary is not a substitute for the underlying review record.

### Current disposition

No conclusion from a hidden review track is treated as independently validated unless its full provenance is reconstructed.

### Closure criterion

Closed when every project-relevant review records:

* exact question;
* reviewer identity and review role;
* role;
* materials provided;
* full response;
* accepted points;
* rejected points;
* unresolved points.

---

Seven propositions that must not be resurrected

The first five are the canonicalized withdrawn propositions from the latest methodological round.

The final two are older repository claims already withdrawn by AF-02 and AF-07.

WP-01 — High disagreement is the natural primary target for common-cause dangerous errors

Claim state

WITHDRAWN

Reason

High disagreement may expose conflict, false positives, or veto opportunities.

A joint dangerous false negative caused by a shared failure can instead produce:

* the same output;
* similar confidence;
* low observable divergence;
* D(x) ≈ 0.

The common-cause failure problem is therefore not solved by auditing only high-disagreement cases.

Permitted wording

Disagreement sampling may identify conflict, but common-cause joint errors can remain hidden inside agreement.

---

WP-02 — Agreement between the primary model and verifier is evidence of independent correctness

Claim state

WITHDRAWN

Reason

The components may share:

* training data;
* architecture;
* provider;
* prompt assumptions;
* tools;
* sources;
* failure causes.

Agreement is an observed relationship between outputs.

It is not proof of independent evidence.

Permitted wording

Agreement may increase apparent confidence while leaving correlated error unresolved.

---

WP-03 — A proxy that discovers more errors automatically estimates population risk better

Claim state

WITHDRAWN

Reason

Error discovery and population-risk estimation are different estimands.

Directed sampling may:

* enrich audited cases for errors;
* change inclusion probabilities;
* introduce bias if uncorrected;
* increase estimator variance;
* produce invalid confidence bounds.

A higher discovery rate does not automatically yield a valid or tighter risk estimate.

Permitted wording

Error-discovery lift is diagnostic unless the sampling design supports valid population-risk estimation.

---

WP-04 — Binary qualification-threshold crossing is sufficient as the primary endpoint

Claim state

WITHDRAWN

Reason

A binary endpoint depends strongly on threshold placement.

A loose threshold may allow both methods to pass.

A strict threshold may cause both to fail.

Either outcome can hide a meaningful difference in estimation quality.

A binary outcome also provides a weak basis for simulation-based design of N_eval.

Permitted wording

Threshold crossing is a secondary operational interpretation of a continuous qualification-relevant endpoint.

---

WP-05 — Required proxy lift can be calculated as L_min = N_auth / B

Claim state

WITHDRAWN

Reason

The formula conflates three separate quantities:

* B: available oracle budget;
* evidence requirements for Blocking or Authorization;
* N_eval: sample size required to evaluate the method.

It also conflates:

* error discovery;
* evidence accumulation;
* population-risk estimation;
* authority qualification.

A discovery-lift ratio does not directly establish a valid upper risk bound.

Permitted wording

Oracle budget, authority thresholds, evaluation size, and discovery lift must be defined separately.

---

WP-06 — The old approximately 70 ms crossover was an empirical repository result

Claim state

WITHDRAWN

Reason

The attributed experiment was never valid executable Python.

The numerical result was not reproducible from the repository.

---

WP-07 — The latency experiment provided evidence for P3

Claim state

WITHDRAWN

Reason

The experiment varied latency rather than model scale.

The manipulated variable did not match the hypothesis.

---

Cross-audit corrections

## C-01 — Number of documents with the broken command

The first audit said four documents promised the broken command.

Correction:

* prototype/README.md did not contain the claimed command;
* docs/repo_snapshot.md used the root-level form;
* docs/commit3_analysis.md contained the incompatible cd prototype form.

The public-run inconsistency remains valid.

---

## C-02 — README rendering

The first audit said the unclosed fence would necessarily break GitHub rendering.

Correction:

* the Markdown was malformed;
* GitHub may implicitly close a final fence;
* visual breakage was possible, not guaranteed.

---

## C-03 — Latency-interlock wording

The first audit said the interlock could not trigger in principle.

Correction:

* that wording was too absolute;
* the supported finding is that the audited demo did not meaningfully exercise it.

---

## C-04 — Parameter tuning

The first audit suggested adjusting a small number of constants so the demo would show its intended mechanism.

Correction:

* expected properties and fair paired-seed comparison must be defined first;
* tuning toward a desired demonstration risks circular evidence.

---

## C-05 — Licensing recommendation

The first audit suggested separate licensing for code and prose.

Correction:

* this may be a reasonable governance decision;
* it is not an audit finding;
* no licensing change is authorized by this register.

---

Old elements not carried into the active scientific claim

The following are withdrawn or retired rather than repaired:

* the LLM-versus-world-model comparison;
* the P1–P3 hypothesis structure;
* the LineWorld-style mechanism demonstration;
* the latency crossover table;
* the approximately 70 ms result;
* the old latency scenario;
* any claim that the prototype supports a general architecture recommendation;
* the old publish-ready or v1.1 status;
* the claim that high disagreement is the main common-cause detector;
* any direct conversion of discovery lift into authority qualification.

They may remain visible in Git history.

They are not active evidence.

---

Findings retained as design controls

The following controls transfer to the new project:

1. A public command must run from a clean checkout.
2. Documentation cannot outrank runtime evidence.
3. A working script must demonstrate the mechanism assigned to it.
4. Compared methods must receive controlled equivalent inputs.
5. Randomness must be explicitly managed.
6. A hypothesis must match the variable actually manipulated.
7. Pre-action controls must execute before the protected action.
8. Public configuration fields must affect tested behaviour.
9. Precise numerical claims require reproducible generation.
10. Publish-ready is an evidence state, not a writing style.
11. Time pressure does not authorize removal of verification.
12. Negative, inconclusive, and invalid outcomes remain publishable.
13. Confirmatory parameters must not be retuned after results are observed.
14. Synthetic evidence does not validate a real domain.
15. Discovery lift does not automatically establish valid risk estimation.
16. Agreement does not establish evidence independence.
17. Reviewers must not receive a conclusion to defend.
18. Review tracks affecting decisions must be visible to the Project Manager.
19. The preregistration reviewer and final result auditor must be different reviewers.
20. The final auditor must classify the result without seeing the Project Manager’s classification.

---

Requirements inherited by the new release

The new release must include:

* a new project identity;
* a migration note;
* a committed preregistration;
* deterministic generator controls;
* a non-circular proxy rule;
* random and sequential baselines;
* controlled seed handling;
* valid inclusion-probability treatment;
* estimator coverage checks;
* unit tests;
* smoke tests;
* CI;
* one canonical public run path;
* expected output;
* explicit non-claims;
* a deviation log;
* separate protocol and result reviewers;
* independent result classification;
* an immutable release tag;
* a reference from results to the preregistration hash.

---

## Phase 1B development implementation audit closure

### Audited surface

* canonical base before Phase 1B: `78625876d4b36fbaf8a6da5b9f0b28bb27bac694`;
* initial implementation head: `a5a9a730af773b9c4196291ab5283acddf089084`;
* first correction head: `9e5dbefb4e8a72d772f11016485e50509472c76f`;
* final implementation head: `a3d486e987d43063ba271cfe5f095f0f9a4b9545`;
* accepted merge commit: `0aaf49c86dabe42bc04ff5e3d05049c952250577`.

### Closure result

| Finding | Final status |
|---|---|
| M1 — replay binding | CLOSED / FIXED |
| N1 — irreversible RNG-state digest | CLOSED / FIXED through full serialized replay |
| N2 — arm-name collision | CLOSED / FIXED |
| N3 — monotonicity status | CLOSED / FIXED |
| N4 — multiplier-field semantics | CLOSED / FIXED |
| N5 — generated Python caches | CLOSED / FIXED |
| N6 — Git provenance | CLOSED / FIXED |
| N8 — deterministic selection order | CLOSED / FIXED |
| N9 — runtime and artifact-size disclosure | CLOSED / FIXED |
| Citation and attribution | CLOSED / FIXED |
| Empty-confidence-set interpretation | CLOSED / FIXED |
| N7 — artifact size | OPEN / DEFERRED / NON-BLOCKING FOR THE DEVELOPMENT PROTOTYPE |

N7 remains open because the full replayable smoke artifact is approximately 1.3 GB. It is generated outside the repository and removed after use. The current format must not be scaled mechanically to a larger sweep.

### Replay boundary

The accepted replay mechanism provides:

* deterministic reconstruction;
* internal consistency against the serialized audit-level population;
* detection of accidental and inconsistent alteration;
* rejection of a self-consistent forged draw when the authoritative serialized population remains unchanged.

It does not provide cryptographic authenticity against complete coordinated rewriting of the entire artifact. The development README states this limitation explicitly.

### Non-blocking technical note T-1

The current implementation uses the one-sided logical lower-bound component required for its one-sided upper dangerous-error bound. For this declared one-sided target, omission of the opposite logical boundary does not change the inferred lower endpoint or coverage indicator. A future two-sided confidence-set formulation must reconsider the full two-sided logical intersection and empty-set classification.

### Scientific status

The audits establish implementation conformance for the bounded development prototype. They do not establish:

* scientific utility of the score;
* superiority of directed auditing;
* preregistration suitability of development parameters;
* confirmatory coverage;
* real-domain validity;
* verifier qualification.

## Current disposition of historical findings

| Finding | Current disposition after Phase 1B |
|---|---|
| AF-01 Broken latency file | Retired; migration note pending |
| AF-02 Unsupported approximately 70 ms result | Withdrawn; migration note pending |
| AF-03 Inconsistent historical run instructions | Historical defect retained; new public run path pending |
| AF-04 Historical README fence | Open until root README replacement |
| AF-05 Demo did not show its thesis | Historical demo retired |
| AF-06 Uncontrolled RNG | Closed for Phase 1B development prototype; confirmatory manifest controls still pending |
| AF-07 Unsupported P3 claim | Withdrawn |
| AF-08 Invariant ordering | Retained as an architectural control; not exercised as an action gate by Phase 1B |
| AF-09 Non-functional configuration | Historical configuration retired; Phase 1B configuration behavior is tested |
| AF-10 Nominal latency interlock | Historical interlock retired |
| AF-11 Missing tests and release checks | Partially closed: `.gitignore` and 29 tests exist; CI, status checks, and release tag remain open |
| AF-12 Unsupported readiness claim | Withdrawn |
| AF-13 Incomplete bibliography | Open for release-facing related work |
| AF-14 Inconsistent hypotheses | Old structure retired; canonical question fixed |
| AF-15 Unsafe unverified fallback | Retained as a negative architectural rule; no such fallback exists in Phase 1B |
| AF-16 Position-defending review brief | Preventive neutral-review control adopted and followed in Phase 1B |
| AF-17 Invisible review track | Review-visibility control adopted and followed in Phase 1B |

The repository is not release-ready. The root README, migration note, preregistration, development CI, confirmatory result, independent result classification, tag, and freeze remain outstanding.

## Current authorized next step

Neutral proxy review has produced one designated development primary-proxy candidate: `paired_perturbation_instability`.

PPI usefulness remains unproven. The method contract is a specification, not evidence that the proxy improves audit allocation or that directed auditing outperforms uniform auditing.

After canonical synchronization, the next possible stage is a separately authorized, bounded, development-only implementation task.

Mandatory development controls include:

* proxy-field isolation;
* structural transformation invariance;
* equal-weight lambda-mixture coverage;
* null-mechanism controls;
* permutation and constant-score controls;
* stable shared-false-belief falsification.

No implementation-dependent finding is closed by adoption of the method contract.

This register does not authorize development implementation, confirmatory implementation, confirmatory execution, preregistration approval, repository rename, deletion of the historical root README, public release, commit, push, or merge by itself.
