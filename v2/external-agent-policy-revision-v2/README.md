# External agent-policy revision replacement

This v2 study is the frozen replacement for the unscored v1 infrastructure abort. The v1 runner
stopped in its first group because its shared run-record schema omitted the disclosed
`Undisclosed OX Alpha` family. The v1 journal and void receipt remain immutable; no v1 output was
inspected or scored.

The replacement preserves the two pinned public `AGENTS.md` histories, ten author-constructed
pairs, prompts, eight route configurations, three repetitions, one request per cell, and zero
client retries. It changes the study and lane identifiers, uses a dedicated run-record schema that
admits the OX disclosure label, and adds the v1 eight-request upper bound to its quota accounting.
The combined conservative five-hour bound is 11.4540446 dollars for the factor-complete study, the
void attempt, and all 480 replacement cells.

Six pairs prescribe an action change and four are stable controls. Upstream maintainers authored
the policy revisions; the scenarios, action mapping, labels, and precedence rule are author-defined
and frozen before replacement inference. The design estimates source-anchored route robustness.
It contains no human annotation, agreement statistic, deployment telemetry, prevalence estimate,
model-family ranking, or causal ablation.

`study-plan.json`, `request-schedule.json`, `prompt-packet.json`, the source receipt, and the dataset
form the frozen pre-inference record. Do not rerun or partially resume the schedule after execution.
Only the privacy-safe `results/` derivative is eligible for an anonymous or future public artifact.

## Completed result

The frozen schedule completed all 480 cells with zero client retries. It produced 399 valid
decisions and 81 terminal failures: 9 JSON-syntax, 46 semantic, and 26 transport failures. The
predesignated first replication produced 132/160 valid decisions, 128/160 correct items, and 52/80
correct pairs end to end. Among 55 complete pairs, 52 were correct. Changed-policy pairs account
for 23/48 correct pairs end to end (23/26 conditional on both decisions); stable controls account
for 29/32 (29/29 conditional). Three of the 26 complete changed-policy pairs returned the same
action across policy versions.

The route-level first-replication item scores range from 12/20 to 18/20 and pair scores from 4/10
to 9/10. The rare `DEMOTE` item is recovered by six routes and missed by OX Alpha and Qwen Plus.
Across all three repetitions, HY3 has the largest all-three correct count at 17/20 items and 7/10
pairs. These are descriptive route-stack observations on ten frozen author-mapped pairs. The
public result files omit prompts, raw responses, provider response identifiers, hidden reasoning,
credentials, and account identifiers; `privacy-receipt.json` and the offline validator bind this
claim to the released bytes.

## Post-hoc route identity disclosure

On 2026-08-26, after this schedule had completed, Z.ai disclosed that GLM-5.3-Flash had been tested
anonymously as `ox-alpha` on OpenCode and OpenRouter in its official release announcement:
<https://z.ai/blog/glm-5.3-flash>. The OX rows are therefore labeled GLM-5.3-Flash (OX) in the
current manuscript. This does not alter the exact requested route ID, historical disclosure status,
provider or serving-state boundary, frozen records, or scores. The OX condition remains separate
from the study's GLM 5.3 route and was not rerun.
