#!/usr/bin/env python3
# ruff: noqa: E501,RUF001
"""Build a single-file, human-readable UI for a frozen external review packet.

This script changes presentation only. It does not alter packet.jsonl, policy.json,
packet-manifest.json, item selection, or any gold label.
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any

Json = dict[str, Any]

REASON_ZH = {
    "CURRENT_STATE_BASIS_INVALID": "現有較高狀態的證據基礎已失效",
    "UNRESOLVED_CONTRADICTION": "存在尚未解決且有效的矛盾證據",
    "MISSING_DEPENDENCY": "依賴的證據未提供",
    "DEPENDENCY_CYCLE": "證據依賴形成循環",
    "DEPENDENCY_RUNTIME_FAILURE": "依賴證據的執行失敗",
    "DEPENDENCY_NOT_VERIFIED": "依賴證據未通過驗證",
    "CLAIM_ID_MISMATCH": "證據對應的 Claim ID 不一致",
    "STATEMENT_HASH_MISMATCH": "證據對應的命題版本／指紋不一致",
    "TOOL_EXIT_NONZERO": "工具執行失敗（exit code 非 0）",
    "RUN_INCOMPLETE": "工具執行尚未完成",
    "VERIFIER_NOT_PASS": "驗證器結果不是 PASS",
    "EVIDENCE_FROM_FUTURE": "證據時間晚於固定評估時間",
    "EVIDENCE_STALE": "證據已超過有效期限",
    "COMPUTATION_EVIDENCE_REQUIRED": "缺少計算證據",
    "COMPUTATION_BASIS_TYPE_MISMATCH": "升級計算狀態時指定的根證據類型不對",
    "NUMERICAL_PROTOCOL_MISMATCH": "數值驗證 protocol/version 不符",
    "INSUFFICIENT_REPETITIONS": "重複次數不足",
    "PREREGISTRATION_REQUIRED": "該數值驗證沒有預先登記",
    "INSUFFICIENT_PRECISION": "數值精度不足",
    "DOMAIN_NOT_COVERED": "證據沒有涵蓋要求的定義域",
    "FORMAL_CERTIFICATE_REQUIRED": "缺少形式化證明憑證",
    "FORMAL_BASIS_TYPE_MISMATCH": "升級 formal 狀態的根證據類型不對",
    "FORMAL_PROVENANCE_NOT_TOOL": "formal certificate 不是由工具產生",
    "UNTRUSTED_FORMAL_VERIFIER": "formal verifier 不是指定的驗證器",
    "UNTRUSTED_TOOLCHAIN": "工具鏈版本／鎖定指紋不符",
    "RESEARCH_STATUS_TRANSITION_NOT_SUPPORTED_BY_ALPHA_POLICY": "研究狀態轉移不在本 policy 支援範圍",
    "INDEPENDENT_REVIEW_REQUIRED": "缺少獨立審查證據",
    "REVIEW_BASIS_TYPE_MISMATCH": "升級 review 狀態的根證據類型不對",
    "REVIEWER_ROLE_NOT_INDEPENDENT": "審查證據的角色不是獨立 reviewer",
    "REVIEWER_NOT_INDEPENDENT": "審查者身份與作者相同",
    "REVIEW_ENVIRONMENT_NOT_INDEPENDENT": "審查環境與作者相同",
    "REVIEW_NOT_COLD_START": "審查不是 cold start",
    "POLICY_SATISFIED": "所有必要條件皆符合",
}

STATE_ZH = {
    "OPEN": "研究中",
    "NONE": "無",
    "COMPUTATIONAL": "已有計算證據",
    "FORMALLY_CERTIFIED": "形式化驗證通過",
    "UNREVIEWED": "未獨立審查",
    "INDEPENDENTLY_VERIFIED": "已有獨立審查",
}

AXIS_ZH = {
    "research_status": "研究狀態",
    "computation_status": "計算狀態",
    "formal_status": "形式化驗證狀態",
    "review_status": "獨立審查狀態",
}

EVIDENCE_ZH = {
    "COMPUTATION": "數值／計算證據",
    "FORMAL_CERTIFICATE": "形式化證明憑證",
    "DEPENDENCY": "依賴證據",
    "REVIEW": "獨立審查證據",
    "CONTRADICTION": "矛盾證據",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[Json]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def js(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def build(package_dir: Path, out: Path) -> None:
    packet = load_jsonl(package_dir / "packet.jsonl")
    manifest = load_json(package_dir / "packet-manifest.json")
    policy = load_json(package_dir / "policy.json")
    if len(packet) != int(manifest["item_count"]):
        raise SystemExit("packet item count does not match manifest")

    payload = {
        "packet": packet,
        "manifest": manifest,
        "policy": policy,
        "reasonZh": REASON_ZH,
        "stateZh": STATE_ZH,
        "axisZh": AXIS_ZH,
        "evidenceZh": EVIDENCE_ZH,
    }

    document = TEMPLATE.replace("__DATA__", js(payload))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8", newline="\n")
    print(json.dumps({"status": "PASS", "items": len(packet), "out": str(out), "packet_id": manifest["packet_id"]}, ensure_ascii=False))


TEMPLATE = r'''<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ClaimPromoteBench 正式外部盲審（易讀版）</title>
<style>
:root{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;color:#171717;background:#f5f5f5}
*{box-sizing:border-box} body{margin:0} .wrap{max-width:980px;margin:auto;padding:18px}
.top{position:sticky;top:0;z-index:10;background:rgba(255,255,255,.96);border-bottom:1px solid #ddd;padding:12px 18px}
.topin{max-width:980px;margin:auto;display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.card{background:white;border:1px solid #ddd;border-radius:14px;padding:18px;margin:14px 0;box-shadow:0 1px 2px rgba(0,0,0,.04)}
h1{font-size:22px;margin:0} h2{font-size:19px;margin:4px 0 12px} h3{font-size:16px;margin:14px 0 8px}
.note{background:#f0f7ff;border-left:4px solid #4b86c5;padding:12px;border-radius:8px}.warn{background:#fff8e8;border-left:4px solid #b27b00;padding:12px;border-radius:8px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:10px}.state{border:1px solid #ddd;border-radius:10px;padding:10px}.muted{color:#666;font-size:13px}
.claim{font-size:18px;line-height:1.55;padding:13px;background:#fafafa;border-radius:10px}.change{font-weight:700;padding:10px;background:#eef7ee;border-radius:10px}
.ev{border:1px solid #d8d8d8;border-radius:12px;padding:12px;margin:10px 0}.evtitle{font-weight:700;margin-bottom:8px}.rows{display:grid;grid-template-columns:minmax(150px,220px) 1fr;gap:6px 12px;align-items:start}.rows>div:nth-child(odd){color:#555}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;word-break:break-all}
.alias{display:inline-block;font-family:ui-monospace,SFMono-Regular,Consolas,monospace;background:#f0f0f0;border-radius:6px;padding:2px 7px;font-weight:700}.okbadge{display:inline-block;border:1px solid #bbb;border-radius:999px;padding:2px 8px;font-size:13px}
details{margin-top:10px} summary{cursor:pointer;color:#444}.raw{white-space:pre-wrap;word-break:break-word;background:#f7f7f7;padding:10px;border-radius:8px;max-height:360px;overflow:auto;font:12px ui-monospace,SFMono-Regular,Consolas,monospace}
.answer{display:grid;grid-template-columns:1fr 1fr 180px;gap:10px}.answer label{display:block;font-weight:650}.answer select,.answer textarea,#reviewer{width:100%;font:inherit;padding:9px;border:1px solid #bbb;border-radius:8px;background:white}.answer textarea{min-height:70px}.full{grid-column:1/-1}
.actions{display:flex;gap:8px;justify-content:space-between;flex-wrap:wrap;margin:14px 0}button{font:inherit;padding:10px 16px;border:1px solid #aaa;border-radius:9px;background:white;cursor:pointer}button.primary{background:#111;color:white;border-color:#111}button:disabled{opacity:.4;cursor:not-allowed}
.policy li{margin:5px 0}.reason-help{font-size:13px;color:#555;margin-top:4px}.footer label{display:block;margin:8px 0}.hidden{display:none!important}
@media(max-width:700px){.answer{grid-template-columns:1fr}.rows{grid-template-columns:1fr}.rows>div:nth-child(odd){font-weight:650;margin-top:5px}}
</style>
</head>
<body>
<div class="top"><div class="topin"><h1>ClaimPromoteBench 正式外部盲審</h1><b id="progress">0/20</b></div></div>
<div class="wrap">
<div class="card note"><b>你不是在判斷數學命題最後到底真不真。</b><br>你只需要依這份 policy 判斷：目前提供的 evidence，是否足以允許 requested transition。長 SHA256 已在本頁轉成題目內的「指紋 A / B / C」；相同原始值會顯示成相同指紋，完整原始資料仍可展開查看。</div>
<div class="card policy">
<details open><summary><b>先看 2 分鐘規則速查</b></summary>
<ul>
<li><b>ALLOW</b>：所有必要條件都滿足。</li>
<li><b>HOLD</b>：目前證據不足、身份/scope 不符、執行或驗證失敗、過期、provenance 不符等。</li>
<li><b>DEMOTE</b>：current state 已是較高狀態，但支撐它的既有 basis 已失效。</li>
<li><b>ESCALATE</b>：存在符合權威條件、仍未解決的 OPEN contradiction。</li>
</ul>
<div class="muted">共 20 題。建議每題先看「這次要升級什麼」，再看 evidence。完整 policy 已嵌在本頁，不需要讀程式碼。</div>
</details>
</div>
<div class="card"><label><b>Reviewer ID</b><input id="reviewer" placeholder="例如 reviewer-01"></label><div class="muted">請使用作者指定給你的 ID。作答只存在你自己的瀏覽器 localStorage，不會自動上傳。</div></div>
<div id="case"></div>
<div class="actions"><button id="prev">← 上一題</button><button id="next" class="primary">下一題 →</button></div>
<div class="card footer" id="finish">
<h2>完成後</h2>
<label><input type="checkbox" id="a1"> 我獨立完成判斷。</label>
<label><input type="checkbox" id="a2"> 我沒有查看 gold labels。</label>
<label><input type="checkbox" id="a3"> 我沒有查看 model outputs。</label>
<label><input type="checkbox" id="a4"> 我沒有和其他人協作決定答案。</label>
<label><input type="checkbox" id="a5"> 我同意 review 關閉並 unblind 後，匿名結果可用於研究報告。</label>
<button class="primary" onclick="exportReview()">匯出作答 JSON</button> <button onclick="clearSaved()">清除本機進度</button>
<p class="muted">把匯出的 JSON 原封不動傳回作者即可。</p>
</div>
</div>
<script>
const D=__DATA__;
const packet=D.packet, manifest=D.manifest, policy=D.policy;
const key="cpb-external-audit-v1-friendly";
let saved=JSON.parse(localStorage.getItem(key)||"{}");
let index=Number(localStorage.getItem(key+"-index")||0); if(index<0||index>=packet.length)index=0;
function esc(x){return String(x??"").replace(/[&<>\"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'\"':"&quot;"}[c]));}
function labelState(x){return D.stateZh[x]||x;}
function axisLabel(x){return D.axisZh[x]||x;}
function evidenceLabel(x){return D.evidenceZh[x]||x;}
function fingerprintAliases(p){
 const map=new Map(); let n=0; const letters="ABCDEFGHIJKLMNOPQRSTUVWXYZ";
 function add(v){if(typeof v!=="string")return; if(!(v.startsWith("sha256:")||v.startsWith("author-")||v.startsWith("claim-")||v.startsWith("reviewer-")||v.startsWith("ev-")))return;if(!map.has(v)){map.set(v,letters[n]||String(n+1));n++;}}
 function walk(v){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==="object")Object.values(v).forEach(walk);else add(v);}
 walk(p); return map;
}
function alias(map,v,kind="指紋"){if(typeof v!=="string")return esc(v);if(map.has(v))return `<span class="alias">${kind} ${map.get(v)}</span>`;return `<span class="mono">${esc(v)}</span>`;}
function fmtDomain(d){if(!d||!Array.isArray(d.variables))return "—";return d.variables.map(v=>`${esc(v.name)} ∈ ${v.lower_inclusive?"[":"("}${esc(v.lower)}, ${esc(v.upper)}${v.upper_inclusive?"]":")"}`).join("；");}
function stateBox(title,s){return `<div class="state"><b>${title}</b>${Object.entries(s||{}).map(([k,v])=>`<div><span class="muted">${esc(axisLabel(k))}</span><br>${esc(labelState(v))} <span class="mono muted">(${esc(v)})</span></div>`).join("")}</div>`;}
function changeSummary(p){const cur=p.current_state||{},tar=p.requested_transition?.target_state||{};const diff=[];for(const k of Object.keys(tar)){if(cur[k]!==tar[k])diff.push(`${axisLabel(k)}：${labelState(cur[k])} → ${labelState(tar[k])}`);}return diff.length?diff.join("；"):"沒有狀態變化";}
function evidenceCard(e,i,p,map,idIndex){
 const prov=e.provenance||{}, sc=e.scope||{}; const deps=(e.dependencies||[]).map(d=>idIndex.has(d)?`Evidence ${idIndex.get(d)+1}`:alias(map,d,"證據 ID")).join("、")||"無";
 let special="";
 if(e.type==="COMPUTATION")special=`<div>Protocol</div><div>${esc(sc.protocol_id||"—")} / ${esc(sc.protocol_version||"—")}</div><div>重複次數</div><div>${esc(sc.repetitions??"—")}</div><div>預先登記</div><div>${sc.preregistered===true?"是":sc.preregistered===false?"否":"—"}</div><div>數值精度</div><div>${esc(sc.precision_bits??"—")} bits</div><div>涵蓋範圍</div><div>${fmtDomain(sc.domain)}</div>`;
 if(e.type==="FORMAL_CERTIFICATE")special=`<div>Formal verifier</div><div>${esc(sc.verifier||"—")}</div><div>工具鏈指紋</div><div>${alias(map,sc.toolchain_lock_sha256,"工具鏈")}</div>`;
 if(e.type==="REVIEW")special=`<div>角色</div><div>${esc(prov.actor_role||"—")}</div><div>審查者身份</div><div>${alias(map,prov.actor_id,"身份")}</div><div>執行環境</div><div>${alias(map,prov.environment_sha256,"環境")}</div><div>Cold start</div><div>${prov.cold_start===true?"是":prov.cold_start===false?"否":"—"}</div>`;
 if(e.type==="CONTRADICTION")special=`<div>矛盾狀態</div><div>${esc(sc.contradiction_status||"—")}</div><div>角色</div><div>${esc(prov.actor_role||"—")}</div><div>提出者身份</div><div>${alias(map,prov.actor_id,"身份")}</div><div>執行環境</div><div>${alias(map,prov.environment_sha256,"環境")}</div><div>Cold start</div><div>${prov.cold_start===true?"是":prov.cold_start===false?"否":"—"}</div>`;
 return `<div class="ev"><div class="evtitle">Evidence ${i+1} — ${esc(evidenceLabel(e.type))} <span class="mono muted">(${esc(e.type)})</span></div><div class="rows"><div>Evidence ID</div><div>${alias(map,e.id,"證據 ID")}</div><div>被哪些 root 引用／依賴</div><div>${deps}</div><div>工具結束碼</div><div>${esc(e.tool_exit===null?"未完成 / null":e.tool_exit)}</div><div>驗證結果</div><div>${esc(e.verifier_result??"—")}</div><div>時間</div><div>${esc(e.timestamp||"—")}</div><div>對應 Claim ID</div><div>${alias(map,sc.claim_id,"Claim")}</div><div>對應命題指紋</div><div>${alias(map,sc.statement_sha256,"Statement")}</div>${special}</div><details><summary>其他技術資料</summary><div class="rows"><div>Artifact</div><div>${esc(e.artifact_path||"—")}</div><div>Artifact 指紋</div><div>${alias(map,e.artifact_hash,"Artifact")}</div><div>Actor role</div><div>${esc(prov.actor_role||"—")}</div><div>Actor identity</div><div>${alias(map,prov.actor_id,"身份")}</div><div>Environment</div><div>${alias(map,prov.environment_sha256,"環境")}</div></div></details></div>`;
}
function currentBasis(p,map,idIndex){const b=p.current_state_basis||{};if(!Object.keys(b).length)return "";return `<h3>既有較高狀態的 basis</h3>${Object.entries(b).map(([axis,r])=>`<div class="ev"><b>${esc(axisLabel(axis))}</b><div class="rows"><div>Basis evidence</div><div>${(r.evidence_ids||[]).map(id=>idIndex.has(id)?`Evidence ${idIndex.get(id)+1}`:alias(map,id,"證據 ID")).join("、")||"無"}</div><div>綁定 Artifact 指紋</div><div>${alias(map,r.bound_artifact_sha256,"Artifact")}</div></div></div>`).join("")}`;}
function answerBlock(id,s){const actions=[["ALLOW","證據足夠，允許升級"],["HOLD","目前不足，先不要升級"],["DEMOTE","既有較高狀態的 basis 失效"],["ESCALATE","存在有效且未解決的矛盾"]];const reasons=policy.reason_precedence||[];return `<div class="answer"><label>Action<select data-id="${id}" data-k="action"><option value="">--請選--</option>${actions.map(([v,z])=>`<option value="${v}" ${s.action===v?"selected":""}>${v} — ${z}</option>`).join("")}</select></label><label>主要 reason<select data-id="${id}" data-k="reason"><option value="">--請選--</option>${reasons.map(r=>`<option value="${esc(r)}" ${s.reason===r?"selected":""}>${esc(D.reasonZh[r]||r)} — ${esc(r)}</option>`).join("")}</select><div id="reasonhelp" class="reason-help"></div></label><label>Confidence 1–5<select data-id="${id}" data-k="confidence"><option value="">--請選--</option>${[1,2,3,4,5].map(x=>`<option ${String(s.confidence)===String(x)?"selected":""}>${x}</option>`).join("")}</select></label><label class="full">補充理由（可留空）<textarea data-id="${id}" data-k="rationale" placeholder="只有覺得案例或規則模糊時才需要寫">${esc(s.rationale||"")}</textarea></label></div>`;}
function render(){
 const row=packet[index],p=row.payload,s=saved[row.review_item_id]||{};const map=fingerprintAliases(p);const evidence=p.evidence||[];const idIndex=new Map(evidence.map((e,i)=>[e.id,i]));
 const roots=p.requested_transition?.basis_evidence_ids||[];
 const rootNames=roots.map(id=>idIndex.has(id)?`Evidence ${idIndex.get(id)+1}`:alias(map,id,"證據 ID")).join("、")||"無";
 const evalTime=policy.evaluation_time||manifest.evaluation_time; const maxAge=policy.evidence_validity?.max_age_days;
 document.getElementById("case").innerHTML=`<div class="card"><div class="muted">第 ${index+1} 題 / ${packet.length}</div><h2>研究 claim</h2><div class="claim">${esc(p.claim_text)}</div><details><summary>Claim 識別資訊（需要比較 identity 時再看）</summary><div class="rows"><div>作者身份</div><div>${alias(map,p.claim_context?.author_id,"身份")}</div><div>作者環境</div><div>${alias(map,p.claim_context?.author_environment_sha256,"環境")}</div><div>Claim ID</div><div>${alias(map,p.claim_context?.claim_id,"Claim")}</div><div>命題指紋</div><div>${alias(map,p.claim_context?.statement_sha256,"Statement")}</div></div></details><h3>狀態</h3><div class="grid">${stateBox("目前 current state",p.current_state)}${stateBox("要求 target state",p.requested_transition?.target_state)}</div><p class="change">這次要判斷的升級：${esc(changeSummary(p))}</p><div class="rows"><div>指定的根 evidence</div><div>${rootNames}</div><div>固定評估時間</div><div>${esc(evalTime)}</div><div>證據最大有效期</div><div>${esc(maxAge??"—")} 天</div></div>${currentBasis(p,map,idIndex)}<h3>提供的 evidence</h3>${evidence.map((e,i)=>evidenceCard(e,i,p,map,idIndex)).join("")}<details><summary>進階：完整原始 JSON</summary><pre class="raw">${esc(JSON.stringify(p,null,2))}</pre></details><h3>你的判斷</h3>${answerBlock(row.review_item_id,s)}</div>`;
 document.querySelectorAll("[data-id]").forEach(el=>el.addEventListener(el.tagName==="TEXTAREA"?"input":"change",save));
 const reason=document.querySelector('[data-k="reason"]'); if(reason){reason.addEventListener("change",showReasonHelp);showReasonHelp({target:reason});}
 document.getElementById("prev").disabled=index===0;document.getElementById("next").textContent=index===packet.length-1?"完成區 ↓":"下一題 →";
 document.getElementById("progress").textContent=`已完成 ${completedCount()}/${packet.length}｜目前第 ${index+1} 題`;
 localStorage.setItem(key+"-index",String(index));window.scrollTo({top:0,behavior:"smooth"});
}
function save(e){const id=e.target.dataset.id,k=e.target.dataset.k;saved[id]=saved[id]||{};saved[id][k]=e.target.value;localStorage.setItem(key,JSON.stringify(saved));document.getElementById("progress").textContent=`已完成 ${completedCount()}/${packet.length}｜目前第 ${index+1} 題`;}
function showReasonHelp(e){const r=e.target.value;document.getElementById("reasonhelp").textContent=r?(D.reasonZh[r]||r):"";}
function completedCount(){return packet.filter(r=>{const s=saved[r.review_item_id]||{};return s.action&&s.reason&&s.confidence;}).length;}
document.getElementById("prev").onclick=()=>{if(index>0){index--;render();}};
document.getElementById("next").onclick=()=>{if(index<packet.length-1){index++;render();}else document.getElementById("finish").scrollIntoView({behavior:"smooth"});};
function exportReview(){const reviewer=document.getElementById("reviewer").value.trim();if(!/^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$/.test(reviewer)){alert("請填作者指定的 reviewer ID，例如 reviewer-01");return;}const decisions=[];for(const row of packet){const s=saved[row.review_item_id]||{};if(!s.action||!s.reason||!s.confidence){alert("還有題目未完成 action / reason / confidence");return;}if(s.action==="ALLOW"&&s.reason!=="POLICY_SATISFIED"){alert("ALLOW 的 reason 必須選『所有必要條件皆符合』");return;}if(s.action!=="ALLOW"&&s.reason==="POLICY_SATISFIED"){alert("非 ALLOW 不可使用 POLICY_SATISFIED");return;}decisions.push({review_item_id:row.review_item_id,action:s.action,reason_codes:[s.reason],confidence:Number(s.confidence),rationale:s.rationale||""});}const checks=["a1","a2","a3","a4","a5"].map(id=>document.getElementById(id).checked);if(checks.some(x=>!x)){alert("請完成最後五個聲明");return;}const out={schema_version:"1.0.0",reviewer_id:reviewer,packet_id:manifest.packet_id,packet_sha256:manifest.packet_sha256,policy_sha256:manifest.policy_sha256,completed_at:new Date().toISOString(),attestation:{independent:true,no_gold_access:true,no_model_outputs:true,no_collaboration:true,public_release_after_unblinding:true},decisions};const blob=new Blob([JSON.stringify(out,null,2)+"\n"],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=reviewer+"-submission.json";a.click();URL.revokeObjectURL(a.href);}
function clearSaved(){if(confirm("確定清除這 20 題在本機的作答進度？")){localStorage.removeItem(key);saved={};render();}}
render();
</script>
</body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.package_dir, args.out)


if __name__ == "__main__":
    main()
