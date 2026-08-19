#!/usr/bin/env python3
"""Build and validate the frozen 20-item ClaimPromoteBench external audit kit."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from claimpromotebench.dataset import (  # noqa: E402
    load_json,
    load_jsonl,
    validate_dataset,
    validate_with_schema,
)
from claimpromotebench.hashing import canonical_json, sha256_bytes, sha256_file  # noqa: E402
from claimpromotebench.policy import load_policy  # noqa: E402

Json = dict[str, Any]

CONFIG = ROOT / "configs" / "external-review-v1.json"
PACKET_FILENAME = "packet.jsonl"
MANIFEST_FILENAME = "packet-manifest.json"
PRIVATE_KEY_FILENAME = "private-key.json"
PUBLIC_ZIP = "SEND_THIS_TO_REVIEWER.zip"
PRIVATE_ZIP = "DO_NOT_SEND_PRIVATE.zip"
HIDDEN_PACKET_FIELDS = {"id", "pair_id", "split", "family", "gold"}
ACTIONS = {"ALLOW", "HOLD", "DEMOTE", "ESCALATE"}


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, values: list[Json]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{canonical_json(value)}\n" for value in values),
        encoding="utf-8",
        newline="\n",
    )


def review_payload(item: Json) -> Json:
    payload = json.loads(json.dumps(item))
    for field in HIDDEN_PACKET_FIELDS:
        payload.pop(field, None)
    return payload


def blind_secret(config: Json, dataset_manifest_sha: str) -> bytes:
    label = f"{config['audit_id']}|{dataset_manifest_sha}|procedural-blinding-v1"
    return hashlib.sha256(label.encode("utf-8")).digest()


def blind_id(secret: bytes, item_id: str) -> str:
    digest = hmac.new(secret, item_id.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"review-{digest[:32]}"


def packet_identity(manifest: Json) -> Json:
    return {
        key: manifest[key]
        for key in (
            "schema_version",
            "dataset_manifest_sha256",
            "policy_sha256",
            "evaluation_time",
            "item_count",
            "packet_file",
            "packet_sha256",
            "blinding_method",
        )
    }


def load_context() -> tuple[Json, Path, Json, list[Json], list[Json], list[Json]]:
    config = load_json(CONFIG)
    dataset_dir = ROOT / str(config["source_dataset"])
    validate_dataset(dataset_dir, ROOT)
    manifest = load_json(dataset_dir / "manifest.json")
    inputs = load_jsonl(dataset_dir / "inputs.jsonl")
    gold = load_jsonl(dataset_dir / "gold.jsonl")
    pairs = load_json(dataset_dir / "pairs.json")
    policy_path = ROOT / "policies" / str(manifest["policy_file"])
    policy = load_policy(policy_path)
    if not isinstance(config, dict) or not isinstance(manifest, dict):
        raise RuntimeError("review config and dataset manifest must be objects")
    if not isinstance(pairs, list):
        raise RuntimeError("pairs.json must be an array")
    return config, dataset_dir, policy, inputs, gold, pairs


def frozen_selection(
    config: Json,
    inputs: list[Json],
    gold: list[Json],
    pairs: list[Json],
) -> tuple[list[Json], Json]:
    selected_ids = [str(value) for value in config["selected_item_ids"]]
    if len(selected_ids) != int(config["item_count"]) or len(set(selected_ids)) != len(
        selected_ids
    ):
        raise RuntimeError("selected_item_ids must be unique and match item_count")
    inputs_by_id = {str(item["id"]): item for item in inputs}
    gold_by_id = {str(item["id"]): item for item in gold}
    pair_by_member: dict[str, str] = {}
    for pair in pairs:
        pair_id = str(pair["pair_id"])
        for item_id in pair["member_ids"]:
            pair_by_member[str(item_id)] = pair_id

    missing = sorted(set(selected_ids) - set(inputs_by_id))
    if missing:
        raise RuntimeError(f"selected review items are missing from source dataset: {missing}")
    selected_pairs = [pair_by_member[item_id] for item_id in selected_ids]
    if len(set(selected_pairs)) != len(pairs) or len(selected_pairs) != len(pairs):
        raise RuntimeError("external audit must select exactly one item from every controlled pair")

    action_counts: Counter[str] = Counter()
    reason_lengths: Counter[int] = Counter()
    for item_id in selected_ids:
        decision = gold_by_id[item_id]["decision"]
        action_counts[str(decision["action"])] += 1
        reason_lengths[len(decision["reason_codes"])] += 1

    target = config["target_gold_balance"]
    allow_count = action_counts["ALLOW"]
    non_allow_count = len(selected_ids) - allow_count
    if allow_count != int(target["ALLOW"]) or non_allow_count != int(target["NON_ALLOW"]):
        raise RuntimeError(
            f"gold balance mismatch: ALLOW={allow_count}, NON_ALLOW={non_allow_count}"
        )
    required_non_allow = {str(value) for value in config["required_non_allow_actions"]}
    if not required_non_allow.issubset(set(action_counts)):
        raise RuntimeError(
            "selected cohort misses required non-ALLOW actions: "
            f"{sorted(required_non_allow - set(action_counts))}"
        )
    if reason_lengths != Counter({1: len(selected_ids)}):
        raise RuntimeError(
            "the low-burden audit requires exactly one gold reason code per selected item"
        )
    selection = [inputs_by_id[item_id] for item_id in selected_ids]
    freeze = {
        "audit_id": config["audit_id"],
        "source_dataset": config["source_dataset"],
        "selected_item_ids": selected_ids,
        "selected_pair_ids": selected_pairs,
        "action_distribution": dict(sorted(action_counts.items())),
        "gold_reason_count_distribution": {
            str(key): value for key, value in sorted(reason_lengths.items())
        },
        "selection_config_sha256": sha256_file(CONFIG),
    }
    return selection, freeze


def build_packet(out_dir: Path) -> Json:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    config, dataset_dir, policy, inputs, gold, pairs = load_context()
    selection, freeze = frozen_selection(config, inputs, gold, pairs)
    dataset_manifest = load_json(dataset_dir / "manifest.json")
    dataset_manifest_sha = sha256_file(dataset_dir / "manifest.json")
    policy_path = ROOT / "policies" / str(dataset_manifest["policy_file"])
    policy_sha = sha256_file(policy_path)
    secret = blind_secret(config, dataset_manifest_sha)

    mapping = [
        {
            "review_item_id": blind_id(secret, str(item["id"])),
            "item_id": str(item["id"]),
        }
        for item in selection
    ]
    mapping.sort(key=lambda row: row["review_item_id"])
    selected_by_id = {str(item["id"]): item for item in selection}
    packet = [
        {
            "review_item_id": row["review_item_id"],
            "payload": review_payload(selected_by_id[row["item_id"]]),
        }
        for row in mapping
    ]
    packet_path = out_dir / PACKET_FILENAME
    write_jsonl(packet_path, packet)
    for row in packet:
        validate_with_schema(
            row,
            ROOT / "schemas" / "review-packet-item.schema.json",
            row["review_item_id"],
        )

    manifest: Json = {
        "schema_version": "1.0.0",
        "dataset_manifest_sha256": dataset_manifest_sha,
        "policy_sha256": policy_sha,
        "evaluation_time": dataset_manifest["evaluation_time"],
        "item_count": len(packet),
        "packet_file": PACKET_FILENAME,
        "packet_sha256": sha256_file(packet_path),
        "blinding_method": "HMAC-SHA256-128-PROCEDURAL",
    }
    manifest["packet_id"] = sha256_bytes(
        canonical_json(packet_identity(manifest)).encode("utf-8")
    )
    write_json(out_dir / MANIFEST_FILENAME, manifest)

    private_key = {
        "schema_version": "1.0.0",
        "packet_id": manifest["packet_id"],
        "packet_sha256": manifest["packet_sha256"],
        "dataset_manifest_sha256": dataset_manifest_sha,
        "policy_sha256": policy_sha,
        "blinding_secret_hex": secret.hex(),
        "mapping": mapping,
    }
    write_json(out_dir / PRIVATE_KEY_FILENAME, private_key)
    freeze.update(
        {
            "dataset_manifest_sha256": dataset_manifest_sha,
            "policy_sha256": policy_sha,
            "packet_id": manifest["packet_id"],
            "packet_sha256": manifest["packet_sha256"],
            "item_count": len(packet),
            "reviewer_count_at_freeze": int(config["reviewer_count_current"]),
        }
    )
    write_json(out_dir / "FREEZE.json", freeze)

    shutil.copy2(policy_path, out_dir / "policy.json")
    write_json(
        out_dir / "submission-template.json",
        {
            "schema_version": "1.0.0",
            "reviewer_id": "reviewer-XX",
            "packet_id": manifest["packet_id"],
            "packet_sha256": manifest["packet_sha256"],
            "policy_sha256": manifest["policy_sha256"],
            "completed_at": None,
            "attestation": {
                "independent": False,
                "no_gold_access": False,
                "no_model_outputs": False,
                "no_collaboration": False,
                "public_release_after_unblinding": False,
            },
            "decisions": [
                {
                    "review_item_id": row["review_item_id"],
                    "action": None,
                    "reason_codes": [],
                    "confidence": None,
                    "rationale": "",
                }
                for row in packet
            ],
        },
    )
    (out_dir / "START_HERE_zh-TW.md").write_text(start_here_text(), encoding="utf-8")
    (out_dir / "POLICY_CHEATSHEET_zh-TW.md").write_text(
        policy_cheatsheet_text(), encoding="utf-8"
    )
    (out_dir / "review.html").write_text(
        reviewer_html(packet, manifest, policy),
        encoding="utf-8",
    )
    make_archives(out_dir)
    return freeze


def start_here_text() -> str:
    return """# ClaimPromoteBench 正式外部盲審

這份資料會正式計入研究的 supplementary external audit，不是練習題。

## 需要多久

- 先讀規則：約 10 分鐘。
- 正式 20 題：約 30–50 分鐘。
- 可以分段完成；瀏覽器會把進度存在本機。

## 最簡單的做法

1. 解壓縮整個資料夾。
2. 用 Chrome / Edge / Firefox 打開 `review.html`。
3. 輸入我給你的匿名 reviewer ID（例如 `reviewer-01`）。
4. 每題選：
   - `ALLOW`：證據足夠，允許升級；
   - `HOLD`：目前不足，先不要升級；
   - `DEMOTE`：現在既有狀態的證據基礎已失效，需要降級；
   - `ESCALATE`：存在有效、尚未解決的矛盾，需要升級處理。
5. 選一個主要 reason code。
6. 填 1–5 的 confidence。
7. rationale 可留空；只有覺得規則或案例模糊時才寫。
8. 最後勾選五個獨立作答聲明，按「匯出 JSON」。
9. 把下載的 JSON 檔原封不動傳回。

## 請不要做

- 不要搜尋這個 benchmark 的 GitHub repo、gold label 或模型結果。
- 不要問作者某一題「答案是什麼」。
- 不要和另一位 reviewer 對答案。
- 不需要證明數學、不需要讀 Lean、不需要跑程式。

你的姓名不需要公開；研究可以只寫 broad background。
"""


def policy_cheatsheet_text() -> str:
    return """# Policy 速查

核心問題只有一個：**目前登記的 evidence，是否足以允許 requested transition？**

## Action

- `ALLOW`：所有必要條件都滿足。reason 選 `POLICY_SATISFIED`。
- `HOLD`：缺證據、scope 不符、runtime/verification 失敗、證據過期、provenance 不符等。
- `DEMOTE`：`current_state` 已經處於較高狀態，但支撐該狀態的 current-state basis 失效。
- `ESCALATE`：存在符合權威條件、仍為 OPEN 的 contradiction。

## 常見 HOLD 檢查

1. Dependency：根 evidence 的 dependency closure 是否完整、已執行、已驗證。
2. Identity：evidence 的 claim_id / statement_sha256 是否與 claim 完全一致。
3. Runtime：tool_exit 是否為 0；verifier_result 是否為 PASS；run 是否真的完成。
4. Freshness：evaluation time 固定；證據不得來自未來，且不得超過 max age。
5. Numerical：protocol/version、repetitions、preregistered、precision、domain coverage。
6. Formal：必須是正確 formal certificate、Lean verifier、固定 trust base、工具 provenance。
7. Independent review：reviewer 不能是作者本人、環境不能相同、必須 cold start。

若所有相關規則都通過，才 `ALLOW`。不要因為「看起來大概對」而升級。
"""


def reviewer_html(packet: list[Json], manifest: Json, policy: Json) -> str:
    packet_json = json.dumps(packet, ensure_ascii=False).replace("</", "<\\/")
    reasons = [str(value) for value in policy["reason_precedence"]]
    reasons_json = json.dumps(reasons, ensure_ascii=False)
    manifest_json = json.dumps(manifest, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ClaimPromoteBench 外部盲審</title>
<style>
body{{font-family:system-ui,-apple-system,sans-serif;max-width:1100px;margin:0 auto;padding:24px;line-height:1.5}}
.card{{border:1px solid #bbb;border-radius:12px;padding:18px;margin:18px 0}}
pre{{white-space:pre-wrap;word-break:break-word;background:#f6f6f6;padding:12px;border-radius:8px}}
label{{display:block;margin:8px 0}}
select,input,textarea{{font:inherit;padding:6px}}
textarea{{width:100%;min-height:60px}}
.top{{position:sticky;top:0;background:white;padding:10px 0;border-bottom:1px solid #ddd;z-index:2}}
button{{font:inherit;padding:10px 16px;margin-right:8px}}
small{{color:#555}}
</style>
</head>
<body>
<div class="top">
<b>ClaimPromoteBench 正式外部盲審 — 20 題</b>
<span id="progress"></span>
</div>
<p>請先讀 <code>START_HERE_zh-TW.md</code> 與 <code>POLICY_CHEATSHEET_zh-TW.md</code>。本頁不含 gold label 或模型答案。</p>
<label>Reviewer ID：<input id="reviewer" placeholder="reviewer-01"></label>
<div id="items"></div>
<div class="card">
<h3>最後聲明</h3>
<label><input type="checkbox" id="a1"> 我獨立完成判斷。</label>
<label><input type="checkbox" id="a2"> 我沒有查看 gold labels。</label>
<label><input type="checkbox" id="a3"> 我沒有查看 model outputs。</label>
<label><input type="checkbox" id="a4"> 我沒有和其他人協作決定答案。</label>
<label><input type="checkbox" id="a5"> 我同意 review 關閉並 unblind 後，匿名結果可用於研究報告。</label>
<button onclick="exportReview()">匯出 JSON</button>
<button onclick="clearSaved()">清除本機進度</button>
<p><small>作答會自動保存在這台瀏覽器的 localStorage，不會上傳到任何伺服器。</small></p>
</div>
<script>
const packet={packet_json};
const reasons={reasons_json};
const manifest={manifest_json};
const key="cpb-external-audit-v1";
let saved=JSON.parse(localStorage.getItem(key)||"{{}}");
function esc(x){{return String(x).replace(/[&<>\"]/g,c=>({{"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}}[c]));}}
function render(){{
 const root=document.getElementById("items"); root.innerHTML="";
 packet.forEach((row,i)=>{{
   const s=saved[row.review_item_id]||{{}};
   const div=document.createElement("div"); div.className="card";
   div.innerHTML=`<h3>${{i+1}} / ${{packet.length}}</h3>
   <pre>${{esc(JSON.stringify(row.payload,null,2))}}</pre>
   <label>Action <select data-id="${{row.review_item_id}}" data-k="action">
   <option value="">--請選--</option>${{["ALLOW","HOLD","DEMOTE","ESCALATE"].map(x=>`<option ${{s.action===x?"selected":""}}>${{x}}</option>`).join("")}}</select></label>
   <label>主要 reason <select data-id="${{row.review_item_id}}" data-k="reason">
   <option value="">--請選--</option>${{reasons.map(x=>`<option ${{s.reason===x?"selected":""}}>${{x}}</option>`).join("")}}</select></label>
   <label>Confidence 1–5 <select data-id="${{row.review_item_id}}" data-k="confidence">
   <option value="">--請選--</option>${{[1,2,3,4,5].map(x=>`<option ${{String(s.confidence)===String(x)?"selected":""}}>${{x}}</option>`).join("")}}</select></label>
   <label>Rationale（可留空）<textarea data-id="${{row.review_item_id}}" data-k="rationale">${{esc(s.rationale||"")}}</textarea></label>`;
   root.appendChild(div);
 }});
 document.querySelectorAll("[data-id]").forEach(el=>el.addEventListener("change",save));
 document.querySelectorAll("textarea[data-id]").forEach(el=>el.addEventListener("input",save));
 updateProgress();
}}
function save(e){{
 const id=e.target.dataset.id, k=e.target.dataset.k;
 saved[id]=saved[id]||{{}};
 saved[id][k]=e.target.value;
 localStorage.setItem(key,JSON.stringify(saved)); updateProgress();
}}
function updateProgress(){{
 const n=packet.filter(r=>{{const s=saved[r.review_item_id]||{{}};return s.action&&s.reason&&s.confidence;}}).length;
 document.getElementById("progress").textContent=` — 已完成 ${{n}}/${{packet.length}}`;
}}
function exportReview(){{
 const reviewer=document.getElementById("reviewer").value.trim();
 if(!/^[A-Za-z0-9][A-Za-z0-9._-]{{2,63}}$/.test(reviewer)){{alert("請填 reviewer ID，例如 reviewer-01");return;}}
 const decisions=[];
 for(const row of packet){{
  const s=saved[row.review_item_id]||{{}};
  if(!s.action||!s.reason||!s.confidence){{alert("還有題目未完成 action / reason / confidence");return;}}
  if(s.action==="ALLOW"&&s.reason!=="POLICY_SATISFIED"){{alert("ALLOW 的 reason 必須是 POLICY_SATISFIED");return;}}
  if(s.action!=="ALLOW"&&s.reason==="POLICY_SATISFIED"){{alert("非 ALLOW 不可使用 POLICY_SATISFIED");return;}}
  decisions.push({{review_item_id:row.review_item_id,action:s.action,reason_codes:[s.reason],confidence:Number(s.confidence),rationale:s.rationale||""}});
 }}
 const checks=["a1","a2","a3","a4","a5"].map(id=>document.getElementById(id).checked);
 if(checks.some(x=>!x)){{alert("請完成最後五個聲明");return;}}
 const out={{
  schema_version:"1.0.0",reviewer_id:reviewer,packet_id:manifest.packet_id,
  packet_sha256:manifest.packet_sha256,policy_sha256:manifest.policy_sha256,
  completed_at:new Date().toISOString(),
  attestation:{{independent:true,no_gold_access:true,no_model_outputs:true,no_collaboration:true,public_release_after_unblinding:true}},
  decisions
 }};
 const blob=new Blob([JSON.stringify(out,null,2)+"\\n"],{{type:"application/json"}});
 const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=reviewer+"-submission.json";a.click();URL.revokeObjectURL(a.href);
}}
function clearSaved(){{if(confirm("確定清除本機作答進度？")){{localStorage.removeItem(key);saved={{}};render();}}}}
render();
</script>
</body></html>
"""


def make_archives(out_dir: Path) -> None:
    public_names = [
        PACKET_FILENAME,
        MANIFEST_FILENAME,
        "policy.json",
        "START_HERE_zh-TW.md",
        "POLICY_CHEATSHEET_zh-TW.md",
        "review.html",
        "submission-template.json",
    ]
    with zipfile.ZipFile(out_dir / PUBLIC_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in public_names:
            archive.write(out_dir / name, arcname=name)
    with zipfile.ZipFile(out_dir / PRIVATE_ZIP, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in (PRIVATE_KEY_FILENAME, "FREEZE.json"):
            archive.write(out_dir / name, arcname=name)


def validate_submission(package_dir: Path, submission_path: Path) -> Json:
    config, _dataset_dir, policy, inputs, gold, pairs = load_context()
    _selection, _freeze = frozen_selection(config, inputs, gold, pairs)
    manifest = load_json(package_dir / MANIFEST_FILENAME)
    packet_path = package_dir / PACKET_FILENAME
    if sha256_file(packet_path) != manifest["packet_sha256"]:
        raise RuntimeError("packet hash mismatch")
    submission = load_json(submission_path)
    validate_with_schema(
        submission,
        ROOT / "schemas" / "review-submission.schema.json",
        str(submission_path),
    )
    for key in ("packet_id", "packet_sha256", "policy_sha256"):
        if submission[key] != manifest[key]:
            raise RuntimeError(f"submission {key} does not match frozen packet")
    packet = load_jsonl(packet_path)
    expected_ids = {str(row["review_item_id"]) for row in packet}
    observed_ids = {str(row["review_item_id"]) for row in submission["decisions"]}
    if observed_ids != expected_ids or len(observed_ids) != len(submission["decisions"]):
        raise RuntimeError("submission item coverage is incomplete or duplicated")
    allowed_reasons = {str(value) for value in policy["reason_precedence"]}
    for decision in submission["decisions"]:
        action = str(decision["action"])
        reasons = [str(value) for value in decision["reason_codes"]]
        if action not in ACTIONS:
            raise RuntimeError(f"unknown action: {action}")
        if not set(reasons).issubset(allowed_reasons):
            raise RuntimeError("submission contains an unknown reason code")
        if action == "ALLOW" and reasons != ["POLICY_SATISFIED"]:
            raise RuntimeError("ALLOW must use only POLICY_SATISFIED")
        if action != "ALLOW" and "POLICY_SATISFIED" in reasons:
            raise RuntimeError("non-ALLOW may not use POLICY_SATISFIED")
    return {
        "status": "PASS",
        "reviewer_id": submission["reviewer_id"],
        "items": len(observed_ids),
        "submission_sha256": sha256_file(submission_path),
        "packet_id": manifest["packet_id"],
    }


def analyze(package_dir: Path, submissions: list[Path], out_path: Path) -> Json:
    config, _dataset_dir, _policy, inputs, gold, pairs = load_context()
    _selection, freeze = frozen_selection(config, inputs, gold, pairs)
    manifest = load_json(package_dir / MANIFEST_FILENAME)
    private_key = load_json(package_dir / PRIVATE_KEY_FILENAME)
    mapping = {
        str(row["review_item_id"]): str(row["item_id"])
        for row in private_key["mapping"]
    }
    gold_by_id = {str(row["id"]): row["decision"] for row in gold}
    reviewer_rows: list[Json] = []
    normalized: dict[str, dict[str, str]] = {}
    for submission_path in submissions:
        validation = validate_submission(package_dir, submission_path)
        submission = load_json(submission_path)
        decisions = {
            str(row["review_item_id"]): row for row in submission["decisions"]
        }
        action_correct = 0
        reason_correct = 0
        confidence_total = 0
        normalized[str(submission["reviewer_id"])] = {}
        disagreements: list[Json] = []
        for review_id, item_id in mapping.items():
            observed = decisions[review_id]
            expected = gold_by_id[item_id]
            normalized[str(submission["reviewer_id"])][review_id] = str(observed["action"])
            action_ok = observed["action"] == expected["action"]
            reason_ok = observed["reason_codes"] == expected["reason_codes"]
            action_correct += int(action_ok)
            reason_correct += int(reason_ok)
            confidence_total += int(observed["confidence"])
            if not action_ok or not reason_ok:
                disagreements.append(
                    {
                        "review_item_id": review_id,
                        "gold_action": expected["action"],
                        "review_action": observed["action"],
                        "gold_reasons": expected["reason_codes"],
                        "review_reasons": observed["reason_codes"],
                    }
                )
        n = len(mapping)
        reviewer_rows.append(
            {
                **validation,
                "action_agreement": action_correct / n,
                "exact_reason_agreement": reason_correct / n,
                "mean_confidence": confidence_total / n,
                "disagreements": disagreements,
            }
        )
    pairwise: list[Json] = []
    reviewer_ids = sorted(normalized)
    for i, left in enumerate(reviewer_ids):
        for right in reviewer_ids[i + 1 :]:
            agree = sum(
                normalized[left][item_id] == normalized[right][item_id]
                for item_id in mapping
            )
            pairwise.append(
                {
                    "reviewer_a": left,
                    "reviewer_b": right,
                    "raw_action_agreement": agree / len(mapping),
                }
            )
    report = {
        "schema_version": "external-audit-report-v1",
        "audit_id": config["audit_id"],
        "packet_id": manifest["packet_id"],
        "packet_sha256": manifest["packet_sha256"],
        "freeze": freeze,
        "reviewers": reviewer_rows,
        "pairwise": pairwise,
    }
    write_json(out_path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--out", type=Path, required=True)
    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--package", type=Path, required=True)
    validate_parser.add_argument("--submission", type=Path, required=True)
    analyze_parser = sub.add_parser("analyze")
    analyze_parser.add_argument("--package", type=Path, required=True)
    analyze_parser.add_argument("--submission", type=Path, action="append", required=True)
    analyze_parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "build":
        result = build_packet(args.out)
    elif args.command == "validate":
        result = validate_submission(args.package, args.submission)
    else:
        result = analyze(args.package, args.submission, args.out)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
