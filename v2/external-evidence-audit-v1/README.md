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

The completed audit will preserve the search results, fixed source coordinates, screening reasons,
and a machine-checkable receipt. No source content will be copied beyond its license.
