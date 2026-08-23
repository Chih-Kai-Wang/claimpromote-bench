# Policy-difference compiler

ClaimPromoteBench exposes a domain-independent core for compiling two deterministic policies into
controlled regression tests. A caller provides:

- two executable policies with a shared finite action vocabulary;
- a finite, typed context grammar;
- a stable identifier for each context; and
- the authored policy-difference rules witnessed by each context.

The compiler executes both policies on every context and retains the behavioral difference set

\[
\Delta(P_a,P_b;\mathcal X)=\{c\in\mathcal X:\pi_{P_a}(c)\ne\pi_{P_b}(c)\}.
\]

Each retained context has one directed action edge and one or more rule witnesses. The reusable
interface in `src/claimpromotebench/policy_difference.py` reports rule and edge coverage, identifies
action directions absent from the supplied grammar, and exposes two deterministic suite searches.
`minimum_lower_bound_witness` asks whether one context per edge can also cover every rule. If it
returns a suite for $k$ required edges, the suite is globally minimum because no context can realize
more than one directed edge. `minimum_complete_suite` solves the general finite candidate-pool
problem: when the lower bound is unattainable, it can select additional contexts and returns a
smallest complete suite with a stable lexical tie break. It returns `None` only when the candidate
pool cannot satisfy the declared joint target.

For $n$ candidates, $r$ required rules, and $k$ required edges, the exact search performs
$O(n2^{r+k})$ state updates. After each candidate, it retains a shortest selected-ID tuple for every
reachable joint coverage mask. This invariant proves that the tuple stored at the full mask has
minimum cardinality; lexical comparison makes equal-size solutions deterministic. The specialized
lower-bound search uses at most $2^r$ rule masks while selecting one context from each edge group.

The implementation has no SLSA, research-evidence, model, provider, or prompt dependency. A
cross-check test loads the 60 frozen software-policy candidates and independently reproduces the
published ten-pair witness. That witness covers all ten reachable edges and all 12 authored rule
differences.

## Interpretation boundary

Compilation is exhaustive only over the supplied finite grammar. An absent edge is not globally
impossible unless the policy author also supplies a semantic unreachability argument. The compiler
does not infer policy legitimacy, natural input prevalence, fault prevalence, or deployment safety.
Its output is a regression-test specification; evaluated routes remain subject to the paper's
failure-aware end-to-end scoring.
