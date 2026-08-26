# Counterfactual policy-profile study

This study asks whether a route changes its action when the applicable policy changes while the
evidence snapshot, current state, requested state, and artifact remain fixed. Each pair switches
only `active_policy_profile`. Exactly one of the two author-defined profiles treats the isolated
failed check or authenticated conflict as binding, so every pair contains one `ALLOW` member and
one `HOLD`, `DEMOTE`, or `ESCALATE` member.

The profiles are counterfactual test instruments. SLSA and in-toto ground the evidence vocabulary,
but neither profile is a SLSA certification, standard interpretation, or deployment recommendation.
The task measures execution of the published author policy.

The prospective freeze must bind the dataset, prompt packet, two development-trained Random Forest
comparators, service configurations, request schedule, analysis, and zero-retry rule before any
scored model call. One comparator observes the active profile; the feature-ablated comparator does
not. Because the latter receives identical features for both pair members, its pair accuracy tests
the registered shortcut boundary rather than serving as a competitive policy-aware method.
