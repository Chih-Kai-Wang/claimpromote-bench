# Ox Alpha minimum-route smoke replay

This auxiliary study replays the preexisting ten-pair minimum policy-migration witness on the
time-stamped OpenCode Go route labeled `ox-alpha-free`. The route was selected after the earlier
ClaimPromoteBench results were known, but the plan, request bodies, item order, failure rule, and
strict pass criterion were committed before the first Ox Alpha call. Ox Alpha is a stealth label;
the study makes no claim about its developer, weights, architecture, or model family.

The run made 20 application requests with zero client retries and no incremental cash cost. It
returned 13 valid decisions, all of which had the correct policy action. Six pairs were complete and
all six were correct. Decision and pair coverage were therefore 13/20 and 6/10. End-to-end item and
pair accuracy were 13/20 and 6/10, whereas the corresponding conditional accuracies were 13/13 and
6/6. The route failed the fixed 20/20-item and 10/10-pair smoke criterion.

The seven invalid outcomes comprise three HTTP 503 endpoint-unavailable responses, three semantic
failures in which `proposed_state` conflicted with the declared action, and one length-terminated
JSON syntax failure. Their contents are not reproduced in the public aggregate. They remain in the
end-to-end denominators.

`private-results/` and `journal/` retain the private terminal evidence. They must not enter an
anonymous or public release. `results/aggregate.json` contains the full confusion matrix, action
recalls, coverage, conditional scores, and end-to-end scores without raw response text, provider
response identifiers, hidden reasoning, credentials, or account identity.

This 20-item replay is a structural route smoke test with one context per reachable edge. It does
not estimate temporal reliability, production error rates, policy-family generalization, or a
causal model or provider effect.
