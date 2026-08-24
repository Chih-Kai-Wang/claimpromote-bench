# Final zero-context isolated review

- Date: 2026-08-24
- Candidate commit: `ddcc1d0987517154173d63b2caacb663767ac730`
- Reviewer context: isolated, read-only, no prior review narratives or author defenses

# ICLR 2027 isolated review

**Recommendation: Weak Reject**

The submission presents an unusually careful, replayable artifact for constructing paired tests from executable policy revisions. Its accounting of invalid responses, exact finite-suite minimization, source binding, and released matrices are strong. However, the current manuscript does not establish that model-mediated executable-policy revision is a consequential deployed problem, describes a finite enumerator over author-supplied witnesses as a more general “compiler,” and bases its central hosted result almost entirely on output-envelope compliance rather than semantic policy-version following. These are scientific claim-boundary issues, not cosmetic objections.

I found no Fatal issue, three Major issues, several Moderate issues, and several Minor/editorial issues.

## Strengths

- The Gatekeeper, Trivy, and Cosign revisions are bound to valid upstream primary sources. The described behavioral changes agree with the official commits: [Gatekeeper FlexVolume](https://github.com/open-policy-agent/gatekeeper-library/commit/102bd7704077cb8f22967b2a75aba2aed4046b02), [Gatekeeper selector](https://github.com/open-policy-agent/gatekeeper-library/commit/749ebacafb023738aa95ce468b0503a88d3e2d75), [Trivy KCV0030](https://github.com/aquasecurity/trivy-checks/commit/e4defae1e4c6e346104f41e70489503069ad1b90), and [Cosign Rego verification](https://github.com/sigstore/cosign/commit/3b597b999ad083afd2ce0dba68fa2715ddec0f06).
- End-to-end item and pair denominators retain transport, syntax, schema, and semantic failures. The distinction between strict action, contract action, and full decision is concrete and useful.
- My independent recomputation agrees with the headline counts, action recalls, confusion matrices, and invalid-response totals.
- The exact dynamic program and lower-bound certificates are sound for the declared finite candidate and coverage inventories.
- The anonymous bundle replays successfully under Python 3.11: all 25 selected tests pass, deterministic evidence checks recompute, and the Lean build/check succeeds. This confirms internal reproducibility, although it does not independently validate the scientific framing.
- The limitations are more candid than is typical: authored labels, finite-grammar scope, route confounds, the non-evaluable 401 lane, and absent naturalistic validity are disclosed.

## Ranked findings

### Major 1 — The paper establishes real policy bugs and a synthetic model interface, but not a real consequential model-mediated policy boundary

**Evidence-backed defect.**

The Introduction documents consequential deterministic policy and verifier revisions on manuscript p. 1, §1 ([main.tex:46](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:46)). It then asserts that “some applications” place a language-model service between structured evidence and a downstream action, but gives no deployed example, incident, measurement, or citation for that architecture ([main.tex:57](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:57)). The paper itself says that a deterministic policy executor should be used directly whenever possible.

The central model task is consequently a synthetic Rego-interpreter interface constructed around two authored mappings. The upstream commits validate that policies matter; they do not validate that anyone routes those policies through an LLM service or that such a route has caused failures. The paper concedes that prevalence is unmeasured on p. 1 ([main.tex:54](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:54)) and that population and naturalistic validity remain open on p. 7, §7 ([main.tex:421](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:421), [main.tex:427](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:427)).

**Consequence.** ICLR readers are asked to care about a deployment boundary whose existence and magnitude are asserted rather than evidenced. The work currently demonstrates a prospective testing construction, not a validated practical failure mode.

**Concrete safe fix.**

- Reframe the title, abstract, and Introduction around a *prospective test construction for model-mediated structured decisions*.
- Explicitly separate two propositions: real executable-policy revisions exist; the evaluated model-service boundary is author-constructed.
- Remove general deployment language unless supported by a concrete public integration or incident.
- If the stronger problem claim is retained, add at least one real model-mediated policy-maintenance workflow and show that version sensitivity or contract failure changes a consequential downstream action. This part requires new evidence; prose alone cannot close it.

### Major 2 — “Compiler” and novelty claims exceed what the implementation performs

**Evidence-backed defect.**

The abstract and contribution list say that ClaimPromoteBench “compiles two executable policy versions and a finite grammar” and “turns an executable policy revision” into certified tests on pp. 1–2 ([main.tex:30](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:30), [main.tex:70](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:70), [main.tex:88](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:88)). The implementation instead requires callers to supply:

- both deterministic evaluators;
- a finite context collection;
- stable context identifiers;
- authored changed-rule witnesses for every context.

Those obligations are explicit in [policy_difference.py:1](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/src/claimpromotebench/policy_difference.py:1) and its API at [policy_difference.py:64](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/src/claimpromotebench/policy_difference.py:64). The compiler executes both evaluators, retains unequal actions, and attaches the supplied witnesses; it does not parse arbitrary policy sources, infer changed rules, synthesize the grammar, or derive semantic witnesses. Adequacy is measured against caller-declared inventories ([policy_difference.py:110](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/src/claimpromotebench/policy_difference.py:110)). In the Gatekeeper construction, rule identifiers are attached manually and the required rule/edge sets are derived from those same rows ([build_upstream_policy_revision_study.py:296](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/scripts/build_upstream_policy_revision_study.py:296), [build_upstream_policy_revision_study.py:319](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/scripts/build_upstream_policy_revision_study.py:319)).

The closest novelty boundary is also incomplete. The Related Work cites Margrave and Cirg, but says Cirg generates and reduces “policy regression tests” on p. 2 ([main.tex:106](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:106)). The primary Cirg paper describes generating tests for a policy using change-impact analysis and synthesized policy versions; “regression tests” is a misleading characterization of its output. See the [University of Illinois primary record](https://experts.illinois.edu/en/publications/automated-test-generation-for-access-control-policies-via-change-/).

More importantly, the text omits several close boundaries even though some are already present in the bibliography:

- test generation and conformance over labelled transition systems ([Tretmans](https://research.utwente.nl/en/publications/conformance-testing-with-labelled-transition-systems-implementati/); also [references.bib:212](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/references.bib:212));
- FSM conformance testing;
- semantic differencing of test-design models ([IBM Research](https://research.ibm.com/publications/syntactic-and-semantic-differencing-for-combinatorial-models-of-test-designs); [references.bib:281](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/references.bib:281));
- prompt regression testing for evolving LLM APIs;
- nearby rule/specification-following evaluations such as [RuleArena](https://aclanthology.org/2025.acl-long.27/) and SpecEval.

**Consequence.** The technically novel part is smaller than “policy-difference compilation”: it is the integration of finite executable differencing, policy-version paired model-service records, joint rule/transition suite minimization, and failure-inclusive scoring. Without a sharper boundary, reviewers can reasonably regard the method as a well-engineered composition of established semantic differencing, contrast/metamorphic testing, conformance testing, and set cover.

**Concrete safe fix.**

- Rename the component a “finite policy-difference enumerator and suite reducer over registered witnesses,” or define “compiler” narrowly at first use.
- Put caller obligations beside the headline claim, including authored grammar completeness and witness correctness.
- Correct Cirg to “policy tests,” then explain the different direction of its construction.
- Add LTS/FSM conformance, semantic test-model differencing, and prompt regression to Related Work.
- State the novelty as an integration claim, not a new general semantic-differencing algorithm.

### Major 3 — The central hosted experiment measures exact-envelope reliability, not semantic policy regression

**Evidence-backed defect.**

The paper itself reports that every extracted Gatekeeper action is correct on p. 5, §5.2 ([main.tex:288](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:288)). Across 144 calls:

- DeepSeek Flash has 53/72 strict actions and 21/36 strict pairs;
- Qwen has 10/72 strict actions and 0/36 strict pairs;
- all 63 strictly extracted actions are semantically correct;
- the 81 losses are 12 read timeouts and 69 envelope/serialization violations.

The failure breakdown is explicit at [main.tex:296](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:296). Qwen’s dominant failure is 62 Markdown-fenced objects rejected by direct top-level `json.loads`. The parser implementation confirms that no fence extraction or object recovery is attempted ([upstream_route_repetition.py:91](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/scripts/upstream_route_repetition.py:91)).

Therefore, no observed extractable response chooses the old policy action, ignores the version, or otherwise makes a semantic action error. The central result validates brittle exact-JSON completion and service availability, not the advertised semantic regression risk.

There is also a factual route-description problem. The paper states that the two central routes use different “model, serving, and adapter stacks” on p. 4 ([main.tex:246](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:246)). The frozen configuration shows the same provider, base URL, OpenAI-compatible API, prompt-only output mode, and adapter settings; only the model ID/family differs ([upstream_route_repetition.py:41](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/scripts/upstream_route_repetition.py:41)). The serving internals are opaque, while the adapter is plainly shared.

**Consequence.** The main model comparison can be explained by response-envelope behavior. It does not show that one route follows policy revisions better once an action is recoverable. Calling the endpoint “safe action extraction” also suggests a safety interpretation unsupported by rejecting otherwise recoverable fenced JSON.

**Concrete safe fix.**

- Lead with the actual finding: the central study finds an exact-interface reliability gap and zero observed semantic action errors among extracted responses.
- Replace “different serving and adapter stacks” with “two model IDs accessed through the same provider/API configuration.”
- Rename “safe action extraction” to “strict top-level JSON action extraction.”
- If the frozen responses permit it, add a clearly labelled, content-free sensitivity analysis that strips only a single Markdown fence. Keep the preregistered strict score primary.
- Promote the released policy-aware/profile-blind controls: the profile-blind control reaches 0/60 pairs while the aware control reaches 47/60 in the hosted record. This is much more direct evidence that the pair endpoint detects policy-version invariance.
- A stronger claim about semantic model regression requires additional real revisions or models that produce extractable but wrong/version-invariant actions.

## Moderate findings

1. **The public challenge is internally frozen but not independently “preregistered” for an anonymous reviewer.**  
   The manuscript calls it preregistered and says cases and predictions were public before analysis ([main.tex:239](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:239), [main.tex:259](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:259), [main.tex:407](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:407)). The anonymous bundle proves byte consistency but withholds the source workflow identity and public timestamp, so temporal priority is not independently checkable. Call it an “author-created, publicly frozen challenge” unless an anonymous timestamped commitment can be supplied.

2. **The challenge is not hidden or externally naturalistic.**  
   It is authored, public, and shares an ontology with r6; the manuscript discloses this on p. 7 ([main.tex:444](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:444)). Its results support robustness on known cases, not generalization. Different route prompting/output constraints also make cross-route comparisons descriptive, not causal.

3. **The strongest shortcut control is omitted, while a weak Naive Bayes “row” is discussed but not shown.**  
   The Discussion refers to a “weak Naive Bayes row” ([main.tex:413](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:413)), but no such row or score appears in the paper’s tables. Conversely, the released policy-aware/profile-blind control directly tests the pair construction and is absent. The style memo even says the paper identifies profile-blind models as controls ([PAPER_STYLE_DISTILLATION_2026-08-23.md:132](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/docs/PAPER_STYLE_DISTILLATION_2026-08-23.md:132)), indicating a manuscript/artifact mismatch.

4. **Minimum-suite certificates establish structural coverage, not stochastic fault-detection power.**  
   The 10-pair/20-call suite is exactly minimum for the declared rule and observed-edge universe, and both local routes fail it ([main.tex:279](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:279)). It is not shown that this smoke suite preserves the full suite’s ability to detect stochastic regressions or future unseen faults. The paper should call it a minimum structural coverage suite rather than implying a sufficient release gate.

5. **The naturalistic zero-case audit is not interpretable as evidence about magnitude.**  
   Twelve candidates were considered and none admitted, but the paper provides too little information about candidate selection, search frame, rejection reasons by candidate, or whether the pool is representative ([main.tex:427](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:427)). This belongs in artifact documentation or a brief limitation, not as a substantive naturalistic audit.

6. **The main evidence hierarchy is blurred.**  
   Table 1 places real Gatekeeper revisions, Trivy/Cosign reproductions, authored SLSA policies, r6, and the public challenge in one flat table ([main.tex:224](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:224)). Those instruments answer different questions and have different external-validity levels. Separate source validity, central route evaluation, and auxiliary diagnostics.

## Evaluation audit and recomputation

The numerical accounting is largely correct.

- **Central Gatekeeper repetitions:** Flash strict items are 15/24, 19/24, and 19/24, totaling 53/72; full decisions total 52/72. Strict pairs total 21/36 and full pairs 20/36. Qwen totals 10/72 items and 0/36 pairs for both reported endpoints.
- **Failure accounting:** Flash has 12 timeouts, three fenced objects, three non-JSON prefixes/envelopes, and one length-terminated non-JSON response. Qwen has 62 fenced objects. These sum to the reported 12 timeouts and 69 envelope violations.
- **Dual-endpoint audit:** The 1,320 released item records contain 69 actions outside the full contract; 49 are correct and create 40 additional correct pairs. Invalid cells remain in the end-to-end denominator.
- **Challenge:** Flash strict/contract scores recompute to 105/180 versus 90/180 items and 19/90 versus 13/90 pairs. Qwen is 132/180 and 48/90 under both endpoints.
- **SLSA:** Qwen moves from 120/120 items and 60/60 pairs under strict action to 88/120 and 28/60 under contract action. Flash moves from 110/120 and 51/60 to 108/120 and 49/60.
- **Action recalls:** r6 Qwen has 143/150 ALLOW, 110/134 HOLD, 0/8 DEMOTE, and 5/8 ESCALATE. Challenge Qwen has 79/90, 26/30, 4/30, and 23/30; Flash has 68/90, 9/30, 0/30, and 13/30.
- **Old Flash 401 lane:** All 300 requests fail before model output. The paper correctly treats model efficacy as non-evaluable and makes no causal comparison with later routes ([main.tex:383](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:383)). Its detailed metrics are nevertheless reader-irrelevant operational history and can move to the appendix.
- **Definitional ceiling:** Calling the deterministic SLSA executor an oracle/definition rather than an empirical baseline is correct ([main.tex:252](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:252)).
- **Invalid-response handling:** Complete matrices retain a separate `N` outcome, and conditional denominators are locally defined. This is a substantive strength.

## Literature validity and novelty boundary

I found no fabricated or invalid material citation. The cited works are primary papers, official proceedings, institutional publication records, standards, or upstream commits. Most characterizations are accurate.

- **Behavioral testing and contrasts:** CheckList is accurately characterized as capability-organized behavioral testing ([ACL](https://aclanthology.org/2020.acl-main.442/)); contrast sets as controlled local decision-boundary probes ([ACL](https://aclanthology.org/2020.findings-emnlp.117/)); and metamorphic testing as relations among transformed executions ([HKUST primary record](https://researchportal.hkust.edu.hk/en/publications/application-of-metamorphic-testing-in-numerical-analysis/)).
- **Policy differencing/testing:** Margrave’s semantic policy comparison and witness role are fairly described ([Brown University primary source](https://static.cs.brown.edu/~sk/Publications/Papers/Published/fkmt-verif-change-impact-xacml/)). Cirg is the one material wording error: it generates access-control policy tests using change-impact analysis and synthesized versions; calling its outputs “policy regression tests” overstates alignment with the present setting. Policy mutation and suite reduction are valid precedents ([Illinois mutation-testing record](https://experts.illinois.edu/en/publications/a-fault-model-and-mutation-testing-of-access-control-policies/), [ACM suite-reduction paper](https://dl.acm.org/doi/10.1145/174146.154034)).
- **Evolving guidelines/specifications:** GuideBench’s rule-update characterization is supported ([ACL](https://aclanthology.org/2025.acl-long.557/)). TDAD and Policy-to-Tests are primary preprints and are described within their stated scopes ([TDAD](https://arxiv.org/abs/2603.08806), [Policy-to-Tests](https://arxiv.org/abs/2512.04408)).
- **Structured output:** PICARD, grammar-constrained decoding, JSONSchemaBench, and BFCL are valid primary sources for constrained generation and structured/tool-call evaluation ([PICARD](https://aclanthology.org/2021.emnlp-main.779/), [grammar-constrained decoding](https://aclanthology.org/2023.emnlp-main.674/), [JSONSchemaBench](https://arxiv.org/abs/2501.10868), [BFCL](https://proceedings.mlr.press/v267/patil25a.html)).
- **Selective prediction:** The reject-option characterization is accurate ([NeurIPS selective classification](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html), [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a.html)). The paper appropriately keeps policy action `HOLD` distinct from transport/parser failure.
- **Research agents:** ScienceAgentBench, CORE-Bench, and POPPER are correctly characterized as broader scientific-work, reproducibility, and falsification evaluations ([ScienceAgentBench](https://proceedings.iclr.cc/paper_files/paper/2025/hash/f12b4df26344f3be803c06b555252efe-Abstract-Conference.html), [CORE-Bench](https://openreview.net/forum?id=BsMMc4MEGS), [POPPER](https://proceedings.mlr.press/v267/huang25n.html)).
- **Policy-evolution motivation:** The content-moderation references directly support policy updates, sparse current labels, and old/new rule conflicts ([Mullick et al.](https://aclanthology.org/2023.acl-industry.54/), [ARGUS](https://aclanthology.org/2026.acl-industry.8/)). Inferring from those settings to executable model-service enforcement is the authors’ inference, not direct support.
- **Standards:** The authored SLSA instrument cites the appropriate official [SLSA 1.2 specification](https://slsa.dev/spec/v1.2/) and [in-toto attestation specification](https://github.com/in-toto/attestation/tree/v1.2.0).

The strongest plausible novelty is therefore an integration: policy-version paired testing at a model-service boundary, with joint rule/action-transition minimization and failure-inclusive item/pair/contract endpoints. The paper earns that integration claim. It does not earn novelty for semantic policy differencing, behavioral contrasts, metamorphic/conformance testing, set-cover minimization, structured-output evaluation, abstention, or research-agent evaluation individually.

## Wording, style, and concision

The prose is generally claim-first, concrete, and calibrated. Technical terms and denominator semantics are mostly stable. I found no recurring avoidable “not X but Y,” “rather than,” or “does not merely” pivot pattern in the manuscript itself.

The main style problems are density and evidence prioritization:

- The abstract ([main.tex:27](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:27)) contains too many secondary fractions: central repetitions, dual-endpoint audit, r6, challenge conditional scores, and rare-action recalls. It buries the question and novelty boundary.
- The conclusion repeats much of the abstract’s metric sequence ([main.tex:451](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:451)), contrary to the distilled guidance that a conclusion should synthesize rather than replay metrics ([style distillation:101](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/docs/PAPER_STYLE_DISTILLATION_2026-08-23.md:101)).
- The 300-call obsolete 401 chronology and much of the reproducibility inventory are operational diary rather than scientific argument.
- The full r6 detail, zero-case audit, and some appendix matrices can be artifact-only if page pressure is material. Keep the complete matrices available, but the main paper needs only the discriminating rows.
- Higher-value missing explanations are: exactly what the caller must author for compilation; why a real system would use this model boundary; semantic versus serialization failures; and the profile-aware/profile-blind control.

## Human-reviewer usability, PDF, anonymity, and replay

A reviewer can find the method and denominator definitions quickly, especially on p. 3, §3.2 ([main.tex:170](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:170)). Limitations are also easy to find and unusually explicit. The novelty boundary is harder: the most accurate statement—“an integration of semantic policy differencing with model-service evaluation”—appears only in the Discussion on p. 6 ([main.tex:391](/Users/wangzhikai/Documents/ChatGPT/claimpromotebranch投稿/claimpromote-bench/technical-report/main.tex:391)). That sentence should appear in the Introduction.

The 11-page PDF is generally legible and anonymous. I found no author identity in the PDF metadata or anonymous ZIP. Table 1 has awkward narrow-column hyphenation, Table 3 is small, and the complete appendix tables on pp. 10–11 require substantial zoom.

The replay path is clear in the bundle README and works end to end. The PDF does not print the short replay command, and the README should state Python 3.11+ explicitly: the project declares that requirement, while the unqualified command fails under the machine’s default Python 3.9.

## ICLR fit and smallest acceptance-improving revision

The topic fits ICLR at the intersection of evaluation, reliable model interfaces, and behavioral testing, but the present evidence is closer to a strong software-engineering artifact paper than a convincing ICLR empirical contribution. The benchmark’s methodological care helps; the narrow, mostly authored scope and missing deployment evidence hurt.

The smallest high-impact revision is:

1. Reframe the problem and compiler claims to their exact finite, author-supplied scope.
2. Make the central result explicitly about exact-interface reliability; correct the shared route-stack description and foreground policy-aware versus profile-blind controls.
3. Repair Related Work around Cirg, LTS/FSM conformance, semantic test-model differencing, and LLM regression testing.
4. Cut r6/401 chronology and repeated fractions; use the space for one concrete deployment example and caller-obligation diagram.
5. If stronger acceptance odds are needed beyond safe manuscript changes, add one naturalistic model-mediated policy revision with extractable semantic errors or version-invariant behavior.

## Required bottom line

- **One-sentence contribution:** ClaimPromoteBench enumerates action-changing contexts from two executable policies over a finite authored grammar, packages them as policy-version paired model-service tests, minimizes joint rule/transition coverage, and scores all scheduled calls at strict-action, contract-action, and full-decision levels.
- **Strongest novelty supported:** A source-traceable integration of finite executable policy differencing with policy-version paired model-service records, joint rule/action-transition suite minimization, and failure-inclusive pair-level structured-output evaluation.
- **Top three rejection risks:** the model-mediated problem is not evidenced as a real consequential deployment; the compiler/novelty language overstates an enumerator over authored witnesses; and the central hosted result is dominated by exact-output envelopes and timeouts, with zero semantic errors among extracted actions.
- **Score:** **4/10 — Weak Reject.**
- **Confidence:** **4/5.**
- **Safely improvable major issue remains:** **Yes.** Compiler scope, novelty positioning, route-stack wording, endpoint naming, control selection, and evidence prioritization are safely fixable. The largest problem-validity gap is not fully fixable by editing and likely requires a real deployment or naturalistic model-mediated revision.

