"""Policy-difference compilation over a finite context grammar.

The compiler is domain-agnostic: callers supply two deterministic policy evaluators, a finite
context collection, and the authored rule differences witnessed by each context.  It emits only
contexts on which the prescribed actions differ.  Coverage and minimum-suite claims are therefore
relative to the supplied grammar and rule inventory.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import TypeVar

ContextT = TypeVar("ContextT")
PolicyEvaluator = Callable[[ContextT], str]
RuleWitnesses = Callable[[ContextT], Iterable[str]]
ContextIdentifier = Callable[[ContextT], str]


class PolicyDifferenceError(ValueError):
    """Raised when a finite policy-difference specification is inconsistent."""


@dataclass(frozen=True, slots=True)
class PolicyDifference:
    """One context on which two deterministic policies prescribe different actions."""

    context_id: str
    left_action: str
    right_action: str
    witnessed_rules: frozenset[str]

    @property
    def edge(self) -> tuple[str, str]:
        return (self.left_action, self.right_action)


@dataclass(frozen=True, slots=True)
class Adequacy:
    """Rule and directed-action-edge coverage for a selected difference suite."""

    covered_rules: frozenset[str]
    required_rules: frozenset[str]
    covered_edges: frozenset[tuple[str, str]]
    required_edges: frozenset[tuple[str, str]]

    @property
    def rule_fraction(self) -> float:
        return len(self.covered_rules) / len(self.required_rules) if self.required_rules else 1.0

    @property
    def edge_fraction(self) -> float:
        return len(self.covered_edges) / len(self.required_edges) if self.required_edges else 1.0

    @property
    def complete(self) -> bool:
        return (
            self.covered_rules == self.required_rules and self.covered_edges == self.required_edges
        )


def compile_policy_differences(
    contexts: Iterable[ContextT],
    *,
    left_policy: PolicyEvaluator[ContextT],
    right_policy: PolicyEvaluator[ContextT],
    context_id: ContextIdentifier[ContextT],
    rule_witnesses: RuleWitnesses[ContextT],
) -> tuple[PolicyDifference, ...]:
    """Execute two policies on every context and retain their behavioral difference set."""

    differences: list[PolicyDifference] = []
    seen_ids: set[str] = set()
    for context in contexts:
        identifier = context_id(context)
        if not identifier or identifier in seen_ids:
            raise PolicyDifferenceError(f"context identifier is empty or repeated: {identifier!r}")
        seen_ids.add(identifier)
        left_action = left_policy(context)
        right_action = right_policy(context)
        if not left_action or not right_action:
            raise PolicyDifferenceError(f"policy returned an empty action: {identifier}")
        if left_action == right_action:
            continue
        rules = frozenset(str(rule) for rule in rule_witnesses(context))
        if not rules:
            raise PolicyDifferenceError(f"difference has no authored rule witness: {identifier}")
        differences.append(
            PolicyDifference(
                context_id=identifier,
                left_action=left_action,
                right_action=right_action,
                witnessed_rules=rules,
            )
        )
    return tuple(sorted(differences, key=lambda row: row.context_id))


def directed_nonself_edges(actions: Iterable[str]) -> frozenset[tuple[str, str]]:
    """Return the complete directed non-self edge universe for an action vocabulary."""

    ordered = tuple(dict.fromkeys(str(action) for action in actions))
    if len(ordered) < 2 or any(not action for action in ordered):
        raise PolicyDifferenceError("the action vocabulary needs at least two nonempty actions")
    return frozenset((left, right) for left in ordered for right in ordered if left != right)


def adequacy(
    suite: Iterable[PolicyDifference],
    *,
    required_rules: Iterable[str],
    required_edges: Iterable[tuple[str, str]],
) -> Adequacy:
    """Measure a suite against declared rule and reachable-edge inventories."""

    rows = tuple(suite)
    rules = frozenset(str(rule) for rule in required_rules)
    edges = frozenset((str(left), str(right)) for left, right in required_edges)
    covered_rules = frozenset(rule for row in rows for rule in row.witnessed_rules) & rules
    covered_edges = frozenset(row.edge for row in rows) & edges
    return Adequacy(
        covered_rules=covered_rules,
        required_rules=rules,
        covered_edges=covered_edges,
        required_edges=edges,
    )


def absent_edges(
    differences: Iterable[PolicyDifference], actions: Iterable[str]
) -> frozenset[tuple[str, str]]:
    """Return action directions absent from the supplied finite context grammar."""

    observed = frozenset(row.edge for row in differences)
    return directed_nonself_edges(actions) - observed


def minimum_lower_bound_witness(
    candidates: Sequence[PolicyDifference],
    *,
    required_rules: Iterable[str],
    required_edges: Iterable[tuple[str, str]],
) -> tuple[PolicyDifference, ...] | None:
    """Find a joint-complete suite that attains the one-context-per-edge lower bound.

    Every context realizes one directed action edge.  A suite covering ``k`` required edges needs
    at least ``k`` contexts.  This dynamic program selects exactly one candidate per edge and asks
    whether that lower bound can also cover every required rule.  A returned suite is therefore
    globally minimum.  ``None`` means only that the lower bound is unattainable; a larger complete
    suite may still exist.
    """

    rules = tuple(sorted(set(str(rule) for rule in required_rules)))
    edges = tuple(sorted(set((str(left), str(right)) for left, right in required_edges)))
    if not edges:
        raise PolicyDifferenceError("at least one required edge is needed")
    rule_bits = {rule: 1 << index for index, rule in enumerate(rules)}
    full_mask = (1 << len(rules)) - 1
    groups: dict[tuple[str, str], list[PolicyDifference]] = defaultdict(list)
    identifiers: set[str] = set()
    for row in candidates:
        if row.context_id in identifiers:
            raise PolicyDifferenceError(f"candidate identifier repeats: {row.context_id}")
        identifiers.add(row.context_id)
        if row.edge in edges:
            groups[row.edge].append(row)
    missing = [edge for edge in edges if not groups[edge]]
    if missing:
        raise PolicyDifferenceError(f"required edges have no candidates: {missing}")

    states: dict[int, tuple[str, ...]] = {0: ()}
    by_id = {row.context_id: row for row in candidates}
    for edge in edges:
        next_states: dict[int, tuple[str, ...]] = {}
        for prior_mask, prior_ids in states.items():
            for row in sorted(groups[edge], key=lambda value: value.context_id):
                mask = prior_mask
                for rule in row.witnessed_rules:
                    if rule in rule_bits:
                        mask |= rule_bits[rule]
                candidate_ids = (*prior_ids, row.context_id)
                current = next_states.get(mask)
                if current is None or candidate_ids < current:
                    next_states[mask] = candidate_ids
        states = next_states
    selected_ids = states.get(full_mask)
    if selected_ids is None:
        return None
    selected = tuple(by_id[identifier] for identifier in selected_ids)
    report = adequacy(selected, required_rules=rules, required_edges=edges)
    if len(selected) != len(edges) or not report.complete:
        raise PolicyDifferenceError("internal minimum-witness certificate failed")
    return selected


def minimum_complete_suite(
    candidates: Sequence[PolicyDifference],
    *,
    required_rules: Iterable[str],
    required_edges: Iterable[tuple[str, str]],
) -> tuple[PolicyDifference, ...] | None:
    """Find a smallest suite that covers every declared rule and edge.

    Unlike :func:`minimum_lower_bound_witness`, this exact dynamic program can return more than
    one context for an edge when no one-context-per-edge selection covers all required rules.  It
    minimizes suite cardinality and then chooses the lexicographically smallest context-ID tuple.
    ``None`` means that the candidate pool cannot satisfy the declared adequacy target.
    """

    rules = tuple(sorted(set(str(rule) for rule in required_rules)))
    edges = tuple(sorted(set((str(left), str(right)) for left, right in required_edges)))
    if not edges:
        raise PolicyDifferenceError("at least one required edge is needed")

    identifiers: set[str] = set()
    ordered_candidates = tuple(sorted(candidates, key=lambda row: row.context_id))
    for row in ordered_candidates:
        if not row.context_id or row.context_id in identifiers:
            raise PolicyDifferenceError(
                f"candidate identifier is empty or repeats: {row.context_id}"
            )
        identifiers.add(row.context_id)

    edge_bits = {edge: 1 << index for index, edge in enumerate(edges)}
    rule_offset = len(edges)
    rule_bits = {rule: 1 << (rule_offset + index) for index, rule in enumerate(rules)}
    full_mask = (1 << (len(edges) + len(rules))) - 1
    candidate_masks: list[tuple[PolicyDifference, int]] = []
    observed_edges: set[tuple[str, str]] = set()
    observed_rules: set[str] = set()
    for row in ordered_candidates:
        mask = edge_bits.get(row.edge, 0)
        if mask:
            observed_edges.add(row.edge)
        for rule in row.witnessed_rules:
            bit = rule_bits.get(rule)
            if bit is not None:
                mask |= bit
                observed_rules.add(rule)
        if mask:
            candidate_masks.append((row, mask))

    missing_edges = sorted(set(edges) - observed_edges)
    if missing_edges:
        raise PolicyDifferenceError(f"required edges have no candidates: {missing_edges}")
    if set(rules) - observed_rules:
        return None

    states: dict[int, tuple[str, ...]] = {0: ()}
    by_id = {row.context_id: row for row in ordered_candidates}
    for row, row_mask in candidate_masks:
        next_states = dict(states)
        for prior_mask, prior_ids in states.items():
            mask = prior_mask | row_mask
            candidate_ids = (*prior_ids, row.context_id)
            current = next_states.get(mask)
            if current is None or (len(candidate_ids), candidate_ids) < (len(current), current):
                next_states[mask] = candidate_ids
        states = next_states

    selected_ids = states.get(full_mask)
    if selected_ids is None:
        return None
    selected = tuple(by_id[identifier] for identifier in selected_ids)
    report = adequacy(selected, required_rules=rules, required_edges=edges)
    if not report.complete:
        raise PolicyDifferenceError("internal minimum-suite certificate failed")
    return selected


def differences_from_records(
    rows: Iterable[Mapping[str, object]],
    *,
    id_key: str = "context_id",
    left_action_key: str = "left_action",
    right_action_key: str = "right_action",
    rules_key: str = "witnessed_rules",
) -> tuple[PolicyDifference, ...]:
    """Load compiler-ready differences from plain mappings without domain dependencies."""

    differences: list[PolicyDifference] = []
    for row in rows:
        raw_rules = row.get(rules_key)
        if not isinstance(raw_rules, (list, tuple, set, frozenset)):
            raise PolicyDifferenceError(f"{rules_key} must be a sequence")
        differences.append(
            PolicyDifference(
                context_id=str(row[id_key]),
                left_action=str(row[left_action_key]),
                right_action=str(row[right_action_key]),
                witnessed_rules=frozenset(str(rule) for rule in raw_rules),
            )
        )
    return tuple(differences)
