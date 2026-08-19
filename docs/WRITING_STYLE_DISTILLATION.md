# Writing Style Notes for ClaimPromoteBench

This document records presentation choices for the submission-facing manuscript. The reference papers are used to learn **structure and information order**, not vocabulary or sentence templates. Scientific claims still come from the ClaimPromoteBench study artifacts, and wording should not be copied from any paper in the reference set.

## Reference set

The review included recent computer-science work on benchmarks, evaluation, agents, software engineering, scientific agents, and negative results from venues such as ACL, NeurIPS, ICML, and ICLR. Representative examples included DeepFact, AgencyBench, AgentGym2, SWE-bench Goes Live, SWE-rebench, SWE-smith, AlgoTune, tinyBenchmarks, SWE-agent, ScienceAgentBench, CORE-Bench, and related evaluation papers.

The point of reading these papers is to learn what information readers expect to see early, how results are separated from interpretation, and how limitations are reported. It is **not** to imitate their diction.

## Writing rules

### 1. Prefer ordinary technical English

Use the simplest wording that preserves the scientific meaning. Prefer phrases such as `fixed policy`, `model decision`, `final action`, `output coverage`, and `the gate follows the policy` over internally useful but unusual phrases such as `artifact-bound`, `fail-closed`, `enforcement-consistency property`, or `conditional enforcement boundary`.

Technical terms that are part of the task itself---for example `claim-state transition`, `false promotion rate`, `controlled pair`, and `FORMAT_ERROR`---should remain when they are needed for precision.

### 2. Use reference papers for organization, not voice

Useful structural patterns include:

- explain the failure before introducing the benchmark;
- state the research question clearly;
- show the main empirical result early;
- keep raw model behavior separate from deterministic gate behavior;
- put coverage next to conditional performance numbers;
- state limitations next to the claims they constrain.

Do not reproduce a paper's characteristic phrasing, rhythm, metaphors, or stock expressions.

### 3. Vary sentence length naturally

Avoid paragraphs in which every sentence has the same shape. Short sentences are useful for key findings. Longer sentences are appropriate when a qualification belongs with the claim it limits. Do not force every paragraph into a claim--evidence--implication template.

### 4. Keep signposting light

Headings should help navigation, but the prose should not read like a generated outline. Use lists only when the items really need to be scanned independently. Results should normally be explained in paragraphs around the tables rather than repeated as a numbered list.

### 5. State negative results plainly

Say what failed and give the number. Do not apologize for the result, but do not turn an engineering safeguard into a model-capability claim. For ClaimPromoteBench, the important distinction is simple: the models often fail to return usable structured decisions, their parseable raw decisions are all `ALLOW`, and the deterministic gate changes final actions only on cases that reach it.

### 6. Keep the gate claim narrow

The gate applies the same fixed policy used to define benchmark labels. Its perfect conditional scores mainly show that the implementation follows that rule on parseable cases. They do not show that the model learned the policy or reasoned better.

### 7. Keep limitations concrete

Prefer direct statements such as:

- only two small Qwen3 models were tested;
- the benchmark uses synthetic controlled pairs;
- free-form text for earlier parse failures was not retained;
- three runs recorded a different Python patch version;
- the human audit contains only 20 items and two reviewers.

Avoid abstract labels when the concrete limitation can be stated directly.

### 8. Keep reproducibility details readable

The paper should identify the scored run, recovery run, and study hash, but long identifiers belong in the repository when a shortened form is enough in prose. Reproducibility text should explain what was fixed before inference and what was changed later, in ordinary language.

### 9. Use cautious, common verbs

Prefer `shows`, `finds`, `reports`, `measures`, `supports`, and `is consistent with`.

Avoid `solves`, `guarantees`, `first`, `unprecedented`, `state of the art`, or `safe` unless the exact claim is established. Also avoid unusual substitute phrases merely to sound academic.

### 10. Keep AI assistance transparent but proportionate

The disclosure should say what AI tools assisted with and what decisions remained the author's responsibility. It should not hide material AI use, but it also should not describe the project as if AI systems were the researchers. The manuscript itself should read as a coherent paper written and revised under human authorship, not as a collection of generated templates.

## ClaimPromoteBench-specific constraints

- Do not describe gate catches as improved model reasoning or calibration.
- Do not treat `FORMAT_ERROR` as an implicit `HOLD`.
- Do not report effective FPR without nearby coverage.
- Do not claim that the benchmark determines theorem truth or scientific truth.
- Do not imply that the two-reviewer audit validates a universal human gold standard.
- Do not hide the Python patch-version mismatch or regroup the affected runs after seeing results.
- Do not generalize the v1 result to larger or API-hosted systems without new evidence.
- Do not rerun or rewrite the frozen v1 model outputs to improve the result after unblinding.

## Preferred manuscript flow

The paper should move in a natural order: problem and research question, benchmark definition, construction and protocol, raw model results, gate behavior, human audit, interpretation, limitations, reproducibility, and conclusion. The exact paragraph structure can vary; it should not be forced into a fixed template if a simpler presentation reads better.
