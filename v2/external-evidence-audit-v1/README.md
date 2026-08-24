# External evidence audit v1

This audit searches public, independently authored sources for an existing model-mediated,
versioned policy boundary that can support a source-traceable case study. It consumes no model
quota. The protocol was frozen before the formal searches in `study-plan.json` were executed.

The audit distinguishes four outcomes:

1. `QUALIFYING_ROUTE_REVISION`: a public model-service path, executable or versioned policy,
   downstream action, and historical revision or fault are jointly traceable;
2. `ARCHITECTURE_ONLY`: a public model-policy integration exists, but no admissible historical
   revision or fault is available;
3. `POLICY_REVISION_ONLY`: an independently authored policy revision or fault is traceable, but
   the source does not establish a model-mediated route; and
4. `EXCLUDED`: the source fails provenance, executability, action, history, or licensing criteria.

Only the first class can support a claim that the complete deployment boundary has an external
instance. Architecture-only sources can motivate feasibility, and policy-revision-only sources can
validate policy and verifier fault classes. Neither is counted as external route validation.

The formal searches returned 465 unique public repository seeds and 10 code hits. Eleven explicit
model/policy candidates received source-level review. Two satisfy every frozen criterion:

- Microsoft Agent Governance Toolkit commit `e87b745` fixes a Rego verdict gap at a deterministic
  agent lifecycle policy point. Exact parent/fixed sources score 11/15 and 15/15 on the post-fix
  upstream tests under OPA 1.19.1.
- agentgateway commit `82ab009` fixes a versioned Bedrock guardrail adapter that could misclassify
  interventions and replace multipart model content. All 33 selected offline tests pass at the
  exact change commit under Rust 1.98.0.

These are external boundary-fault instances. Neither is a naturalistic case in which a model
interprets an executable policy revision, and the audit is not a prevalence sample. The decision
is therefore `GO` for external boundary-fault evidence and `NO-GO` for a naturalistic
model-policy-interpretation claim. No hosted-model quota was consumed.

`formal-search-seeds.json` preserves every formal seed and screening reason;
`candidate-registry.json` records the source-level dispositions; `audit-receipt.json` binds the
decision and source checks.
