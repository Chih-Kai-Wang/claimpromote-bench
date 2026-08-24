"""Finite contexts and output contracts for traceable upstream policy revisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from claimpromotebench.hashing import canonical_json

Json = dict[str, Any]
MigrationId = Literal[
    "unique-service-selector-kind-filter",
    "flexvolume-empty-allowlist-blocks-all",
]
Revision = Literal["old", "new"]


@dataclass(frozen=True, slots=True)
class UpstreamPolicyCase:
    """One admission context shared by both sides of an upstream policy revision."""

    pair_id: str
    migration_id: MigrationId
    query: str
    rule_id: str
    input_document: Json
    data_document: Json
    subject: Json
    changed_witnesses: tuple[Json, ...]
    factors: Json


def _resource(kind: str, namespace: str, name: str) -> Json:
    return {"kind": kind, "namespace": namespace, "name": name}


def _service(namespace: str, name: str) -> Json:
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": name, "namespace": namespace},
        "spec": {
            "clusterIP": "10.43.0.1",
            "ports": [{"name": "https", "port": 443, "protocol": "TCP", "targetPort": 6443}],
            "sessionAffinity": "None",
            "type": "ClusterIP",
        },
    }


def _inventory_object(
    kind: str,
    api_version: str,
    namespace: str,
    name: str,
) -> Json:
    base: Json = {
        "apiVersion": api_version,
        "kind": kind,
        "metadata": {"name": name, "namespace": namespace},
    }
    if kind == "NetworkPolicy":
        base["spec"] = {"podSelector": {}, "policyTypes": ["Ingress"]}
    elif kind == "ConfigMap":
        base["data"] = {"mode": "strict"}
    elif kind == "Secret":
        base["type"] = "Opaque"
        base["data"] = {"token": "cmVkYWN0ZWQ="}
    elif kind == "Pod":
        base["spec"] = {"containers": [{"name": "worker", "image": "example/worker:1"}]}
    elif kind == "Ingress":
        base["spec"] = {
            "rules": [
                {
                    "host": "example.invalid",
                    "http": {
                        "paths": [
                            {
                                "path": "/",
                                "pathType": "Prefix",
                                "backend": {
                                    "service": {"name": "frontend", "port": {"number": 80}}
                                },
                            }
                        ]
                    },
                }
            ]
        }
    elif kind == "ResourceQuota":
        base["spec"] = {"hard": {"pods": "10"}}
    else:
        raise ValueError(f"unsupported inventory kind: {kind}")
    return base


def _unique_service_cases() -> tuple[UpstreamPolicyCase, ...]:
    specifications = (
        (
            "upr-unique-01",
            "NetworkPolicy",
            "networking.k8s.io/v1",
            "default",
            "default",
            "kubernetes",
            "kubernetes",
        ),
        (
            "upr-unique-02",
            "ConfigMap",
            "v1",
            "payments",
            "payments",
            "payments-api",
            "runtime-config",
        ),
        (
            "upr-unique-03",
            "Secret",
            "v1",
            "frontend",
            "shared",
            "frontend",
            "frontend",
        ),
        (
            "upr-unique-04",
            "Pod",
            "v1",
            "batch",
            "archive",
            "job-service",
            "job-runner",
        ),
        (
            "upr-unique-05",
            "Ingress",
            "networking.k8s.io/v1",
            "edge",
            "edge",
            "gateway",
            "gateway",
        ),
        (
            "upr-unique-06",
            "ResourceQuota",
            "v1",
            "analytics",
            "platform",
            "query",
            "quota",
        ),
    )
    cases: list[UpstreamPolicyCase] = []
    for (
        pair_id,
        kind,
        api_version,
        service_namespace,
        inventory_namespace,
        service_name,
        inventory_name,
    ) in specifications:
        service = _service(service_namespace, service_name)
        other = _inventory_object(kind, api_version, inventory_namespace, inventory_name)
        data_document = {
            "inventory": {
                "namespace": {
                    inventory_namespace: {
                        api_version: {
                            kind: {
                                inventory_name: other,
                            }
                        }
                    }
                }
            }
        }
        cases.append(
            UpstreamPolicyCase(
                pair_id=pair_id,
                migration_id="unique-service-selector-kind-filter",
                query="data.k8suniqueserviceselector.violation",
                rule_id="UNIQUE_SERVICE_SELECTOR",
                input_document={
                    "review": {
                        "kind": {"kind": "Service", "version": "v1", "group": ""},
                        "namespace": service_namespace,
                        "name": service_name,
                        "object": service,
                    }
                },
                data_document=data_document,
                subject=_resource("Service", service_namespace, service_name),
                changed_witnesses=(_resource(kind, inventory_namespace, inventory_name),),
                factors={
                    "inventory_api_version": api_version,
                    "inventory_kind": kind,
                    "name_relation": ("SAME" if inventory_name == service_name else "DIFFERENT"),
                    "namespace_relation": (
                        "SAME" if inventory_namespace == service_namespace else "DIFFERENT"
                    ),
                },
            )
        )
    return tuple(cases)


def _flex_volume(name: str, driver: str) -> Json:
    return {"name": name, "flexVolume": {"driver": driver}}


def _flexvolume_cases() -> tuple[UpstreamPolicyCase, ...]:
    specifications: tuple[tuple[str, str, str, list[Json]], ...] = (
        (
            "upr-flex-01",
            "apps",
            "web",
            [_flex_volume("cache", "example/lvm")],
        ),
        (
            "upr-flex-02",
            "storage",
            "backup",
            [_flex_volume("archive", "example/cifs")],
        ),
        (
            "upr-flex-03",
            "ml",
            "trainer",
            [
                _flex_volume("scratch", "example/lvm"),
                _flex_volume("dataset", "example/cifs"),
            ],
        ),
        (
            "upr-flex-04",
            "media",
            "transcoder",
            [
                _flex_volume("frames", "vendor/frames"),
                _flex_volume("audio", "vendor/audio"),
                _flex_volume("output", "vendor/archive"),
            ],
        ),
        (
            "upr-flex-05",
            "security",
            "scanner",
            [
                _flex_volume("plugins", "vendor/plugins"),
                {"name": "certs", "secret": {"secretName": "scanner-certs"}},
            ],
        ),
        (
            "upr-flex-06",
            "data",
            "loader",
            [
                _flex_volume("source", "vendor/source"),
                _flex_volume("sink", "vendor/sink"),
                {"name": "tmp", "emptyDir": {}},
            ],
        ),
    )
    cases: list[UpstreamPolicyCase] = []
    for pair_id, namespace, pod_name, volumes in specifications:
        flex_volumes = [volume for volume in volumes if "flexVolume" in volume]
        witnesses = tuple(
            _resource("FlexVolume", "", str(volume["name"])) for volume in flex_volumes
        )
        cases.append(
            UpstreamPolicyCase(
                pair_id=pair_id,
                migration_id="flexvolume-empty-allowlist-blocks-all",
                query="data.k8spspflexvolumes.violation",
                rule_id="FLEXVOLUME_DRIVER",
                input_document={
                    "review": {
                        "object": {
                            "apiVersion": "v1",
                            "kind": "Pod",
                            "metadata": {"name": pod_name, "namespace": namespace},
                            "spec": {
                                "containers": [
                                    {
                                        "name": "main",
                                        "image": "example/workload:1",
                                        "volumeMounts": [
                                            {
                                                "name": str(volume["name"]),
                                                "mountPath": f"/mnt/{volume['name']}",
                                            }
                                            for volume in volumes
                                        ],
                                    }
                                ],
                                "volumes": volumes,
                            },
                        }
                    },
                    "parameters": {"allowedFlexVolumes": []},
                },
                data_document={},
                subject=_resource("Pod", namespace, pod_name),
                changed_witnesses=witnesses,
                factors={
                    "flexvolume_count": len(flex_volumes),
                    "has_non_flexvolume": len(flex_volumes) != len(volumes),
                    "driver_families": sorted(
                        {
                            str(volume["flexVolume"]["driver"]).split("/", maxsplit=1)[0]
                            for volume in flex_volumes
                        }
                    ),
                },
            )
        )
    return tuple(cases)


def upstream_policy_cases() -> tuple[UpstreamPolicyCase, ...]:
    """Return the fixed finite grammar in stable pair-ID order."""

    return tuple(
        sorted((*_unique_service_cases(), *_flexvolume_cases()), key=lambda row: row.pair_id)
    )


def expected_decision(
    case: UpstreamPolicyCase,
    revision: Revision,
    *,
    observed_violation_count: int,
) -> Json:
    """Construct scorer gold after checking the independent OPA oracle count."""

    changed_side: Revision = (
        "old" if case.migration_id == "unique-service-selector-kind-filter" else "new"
    )
    expected_count = len(case.changed_witnesses) if revision == changed_side else 0
    if observed_violation_count != expected_count:
        raise ValueError(
            f"{case.pair_id}/{revision}: OPA produced {observed_violation_count} "
            f"violations; expected {expected_count}"
        )
    if expected_count == 0:
        return {
            "action": "ALLOW",
            "violation_count": 0,
            "subject": case.subject,
            "rule_id": "NONE",
            "witnesses": [],
        }
    return {
        "action": "HOLD",
        "violation_count": expected_count,
        "subject": case.subject,
        "rule_id": case.rule_id,
        "witnesses": list(case.changed_witnesses),
    }


def render_prompt(case: UpstreamPolicyCase, policy_source: str) -> str:
    """Render one model-visible execution request without revision labels or gold."""

    rule_id = case.rule_id
    return (
        "Execute the supplied Rego v0 admission policy on the supplied input and base data.\n"
        f"Evaluate the query {case.query}. HOLD means one or more violation objects; "
        "ALLOW means zero violation objects.\n"
        "Return exactly one JSON object with these fields:\n"
        '- "action": "ALLOW" or "HOLD"\n'
        '- "violation_count": the exact number of distinct violation objects\n'
        '- "subject": the reviewed object as {"kind", "namespace", "name"}\n'
        f'- "rule_id": "{rule_id}" for HOLD and "NONE" for ALLOW\n'
        '- "witnesses": one {"kind", "namespace", "name"} object per violation; '
        'use kind FlexVolume, namespace "", and the volume name for FlexVolume witnesses\n'
        "Use the policy, input, and base data as the complete execution state.\n\n"
        "POLICY SOURCE\n"
        f"{policy_source.rstrip()}\n\n"
        "INPUT JSON\n"
        f"{canonical_json(case.input_document)}\n\n"
        "BASE DATA JSON\n"
        f"{canonical_json(case.data_document)}\n"
    )


def validate_decision_semantics(decision: Json) -> None:
    """Check relations among schema-valid decision fields without consulting gold."""

    action = decision.get("action")
    count = decision.get("violation_count")
    rule_id = decision.get("rule_id")
    witnesses = decision.get("witnesses")
    if not isinstance(count, int) or isinstance(count, bool):
        raise ValueError("violation_count must be an integer")
    if not isinstance(witnesses, list):
        raise ValueError("witnesses must be a list")
    if action == "ALLOW":
        if count != 0 or rule_id != "NONE" or witnesses:
            raise ValueError("ALLOW requires zero violations, rule NONE, and no witnesses")
    elif action == "HOLD":
        if count < 1 or rule_id == "NONE" or len(witnesses) != count:
            raise ValueError(
                "HOLD requires a positive count, a rule, and one witness per violation"
            )
    else:
        raise ValueError("action must be ALLOW or HOLD")
