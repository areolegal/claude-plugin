#!/usr/bin/env python3
"""Render canonical playbook JSON into a self-contained editable HTML workbench."""
import json
import sys
from pathlib import Path


def main(inp, out):
    data = json.loads(Path(inp).read_text(encoding="utf-8"))
    lang = data.get("output_language", "en")
    he = lang == "he"
    labels = {
        "he": {
            "title": "מדיניות חוזית",
            "workspaceSubtitle": "מרכז ניהול, התאמה ואישור של מדיניות החברה",
            "workspaceEyebrow": "מרכז מדיניות חוזית",
            "overview": "תמונת מצב",
            "segments": "סגמנטים",
            "matrix": "מטריצת מדיניות",
            "topics": "סעיפי מדיניות",
            "decisions": "החלטות לאישור",
            "family": "סוג החוזים",
            "role": "פוזיציית החברה",
            "documents": "מקורות שנבדקו",
            "status": "מצב המדיניות",
            "segStatus": "מצב הסגמנטציה",
            "search": "חיפוש סעיף, נושא או סיכון...",
            "allSegments": "כל הסגמנטים",
            "policyRationale": "מדוע נבחרה מדיניות זו",
            "purpose": "מטרת הסעיף והאינטרס המוגן",
            "legal": "החשיפה המשפטית והמסגרת הנורמטיבית",
            "allocation": "מנגנון חוזי והקצאת סיכון",
            "roleFit": "התאמת המדיניות לפוזיציית החברה",
            "applicability": "מתי המדיניות מתאימה",
            "business": "השלכה עסקית ותפעולית",
            "evidence": "ראיות מתוך מאגר החברה",
            "market": "מקובלות שוק / בסיס ההערכה",
            "greenWhy": "מדוע ירוק",
            "yellowWhy": "מדוע צהוב",
            "redWhy": "מדוע אדום",
            "tradeoff": "האיזון וה-trade-off",
            "related": "קשרים לסעיפים אחרים",
            "uncertainty": "אי-ודאות ומגבלות",
            "green": "ירוק — מאושר",
            "yellow": "צהוב — מסכימים בכפוף להערות",
            "red": "אדום — לא מאושר",
            "criteria": "קריטריונים",
            "clause": "נוסח סעיף מוצע",
            "comments": "הערות נדרשות",
            "prior": "הסכמים קודמים שבהם התקבל נוסח משפטי זה",
            "segmentWhy": "מדוע המדיניות שונה בסגמנט זה",
            "accept": "אשר",
            "edit": "סמן כערוך",
            "reject": "דחה",
            "defer": "השאר פתוח",
            "na": "לא רלוונטי",
            "acceptRationale": "אשר את הנימוק",
            "approver": "שם המאשר/ת",
            "save": "שמור בדפדפן",
            "export": "ייצא JSON מעודכן",
            "exportDecisions": "ייצא יומן החלטות",
            "finalize": "אשר את המדיניות",
            "draftWarning": "המדיניות נמצאת בטיוטה. ניתן לערוך, להשוות בין סגמנטים ולאשר כל נושא לפני הפיכתה למדיניות מאושרת.",
            "noSegments": "לא זוהתה סגמנטציה פעילה.",
            "unresolved": "החלטות שטרם אושרו",
            "rationaleStatus": "סטטוס הנימוק",
            "policyStatus": "סטטוס המדיניות",
            "confidence": "רמת ביטחון ראייתית",
        },
        "en": {
            "title": "Contract Policy",
            "workspaceSubtitle": "Review, tailor, and approve organizational contract policy",
            "workspaceEyebrow": "Contract policy center",
            "overview": "Dashboard",
            "segments": "Segments",
            "matrix": "Policy Matrix",
            "topics": "Policy Clauses",
            "decisions": "Approval Decisions",
            "family": "Contract types",
            "role": "Company role",
            "documents": "Sources reviewed",
            "status": "Policy status",
            "segStatus": "Segmentation status",
            "search": "Search clause, topic, or risk...",
            "allSegments": "All segments",
            "policyRationale": "Why this policy was selected",
            "purpose": "Clause purpose and protected interest",
            "legal": "Legal risk and legal framework",
            "allocation": "Contractual risk-allocation mechanism",
            "roleFit": "Fit with the company's role",
            "applicability": "When this policy applies",
            "business": "Business and operational impact",
            "evidence": "Internal corpus evidence",
            "market": "Market practice / assessment basis",
            "greenWhy": "Why Green",
            "yellowWhy": "Why Yellow",
            "redWhy": "Why Red",
            "tradeoff": "Management trade-off",
            "related": "Related-clause effects",
            "uncertainty": "Uncertainty and limitations",
            "green": "Green — Approved",
            "yellow": "Yellow — Agree with comments",
            "red": "Red — Not approved",
            "criteria": "Match criteria",
            "clause": "Proposed clause",
            "comments": "Required comments",
            "prior": "Previous agreements where this legal wording was accepted",
            "segmentWhy": "Why the policy differs for this segment",
            "accept": "Accept",
            "edit": "Mark edited",
            "reject": "Reject",
            "defer": "Defer",
            "na": "Not applicable",
            "acceptRationale": "Accept rationale",
            "approver": "Approver name",
            "save": "Save in browser",
            "export": "Export updated JSON",
            "exportDecisions": "Export decision log",
            "finalize": "Approve policy",
            "draftWarning": "This policy is in draft. Review, tailor, compare segments, and approve each topic before finalization.",
            "noSegments": "No active segmentation detected.",
            "unresolved": "Decisions awaiting approval",
            "rationaleStatus": "Rationale status",
            "policyStatus": "Policy status",
            "confidence": "Evidence confidence",
        },
    }["he" if he else "en"]
    direction = "rtl" if he else "ltr"
    align = "right" if he else "left"
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    labels_json = json.dumps(labels, ensure_ascii=False).replace("</", "<\\/")

    template = r'''<!doctype html>
<html lang="__LANG__" dir="__DIR__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#f3f5f9;--surface:#ffffff;--surface-2:#f8fafc;--text:#18212f;--muted:#697586;--border:#e4e8ef;--accent:#315efb;--accent-soft:#edf2ff;--nav:#111827;--nav2:#182235;--green:#effaf3;--greenb:#16834b;--yellow:#fff9e8;--yellowb:#ad7417;--red:#fff1f1;--redb:#bf3f45;--shadow:0 10px 28px rgba(20,32,54,.07);--shadow2:0 18px 60px rgba(20,32,54,.10);--radius:18px}
*{box-sizing:border-box}html{background:var(--bg)}body{margin:0;font-family:Inter,ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,"Noto Sans Hebrew",sans-serif;background:var(--bg);color:var(--text);line-height:1.55}.app-shell{min-height:100vh;display:grid;grid-template-columns:248px minmax(0,1fr)}[dir="rtl"] .app-shell{grid-template-columns:minmax(0,1fr) 248px}.sidebar{grid-column:1;grid-row:1;position:sticky;top:0;height:100vh;background:linear-gradient(180deg,var(--nav),var(--nav2));color:#fff;padding:20px 14px;display:flex;flex-direction:column;gap:22px;z-index:20}[dir="rtl"] .sidebar{grid-column:2}.main{grid-column:2;grid-row:1;min-width:0}[dir="rtl"] .main{grid-column:1}.brand{display:flex;align-items:center;gap:11px;padding:6px 8px 18px;border-bottom:1px solid rgba(255,255,255,.10)}.brand-mark{width:38px;height:38px;border-radius:12px;background:linear-gradient(135deg,#6f8cff,#315efb);display:grid;place-items:center;font-weight:900;box-shadow:0 8px 20px rgba(49,94,251,.35)}.brand-copy strong{display:block;font-size:15px}.brand-copy span{display:block;font-size:11px;opacity:.68;margin-top:2px}.tabs{display:flex;flex-direction:column;gap:6px}.tabs button{width:100%;border:0;background:transparent;color:#cbd5e1;padding:11px 12px;border-radius:11px;cursor:pointer;text-align:inherit;font:inherit;font-weight:650;transition:.18s}.tabs button:hover{background:rgba(255,255,255,.07);color:#fff}.tabs button.active{background:rgba(255,255,255,.12);color:#fff;box-shadow:inset 0 0 0 1px rgba(255,255,255,.08)}.sidebar-foot{margin-top:auto;padding:12px 10px;border-radius:12px;background:rgba(255,255,255,.06);font-size:12px;color:#cbd5e1}.app-header{background:rgba(255,255,255,.88);backdrop-filter:blur(14px);border-bottom:1px solid rgba(228,232,239,.9);padding:25px 32px 20px;position:sticky;top:0;z-index:15}.hero-row{display:flex;align-items:flex-start;justify-content:space-between;gap:24px}.eyebrow{font-size:12px;font-weight:800;letter-spacing:.04em;color:var(--accent);margin-bottom:4px}.app-header h1{margin:0;font-size:30px;letter-spacing:-.025em}.sub{color:var(--muted);font-size:14px;margin-top:5px}.scope-chips{display:flex;gap:7px;flex-wrap:wrap;margin-top:13px}.scope-chip{background:var(--surface-2);border:1px solid var(--border);border-radius:999px;padding:5px 9px;font-size:12px;color:#445064}.scope-chip strong{color:var(--text)}.topbar{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.topbar input,.topbar button{min-height:40px;padding:9px 12px;border-radius:11px;border:1px solid var(--border);background:#fff;color:var(--text);font:inherit}.topbar input{min-width:170px}.topbar button{cursor:pointer;font-weight:700;box-shadow:0 2px 5px rgba(20,32,54,.04)}.topbar button:hover{border-color:#c9d2e1;transform:translateY(-1px)}.wrap{max-width:1540px;margin:0 auto;padding:24px 32px 92px}.tab{display:none}.tab.active{display:block}.notice{background:linear-gradient(90deg,#fffaf0,#fff);border:1px solid #f6d78c;padding:13px 15px;border-radius:14px;margin-bottom:18px;color:#6e5415}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:14px}.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:18px;box-shadow:var(--shadow);margin-bottom:16px}.card:hover{box-shadow:var(--shadow2)}.metric{font-size:30px;font-weight:850;letter-spacing:-.03em}.muted{color:var(--muted)}.badge,.pill{display:inline-flex;align-items:center;padding:4px 9px;border-radius:999px;background:#f0f3f7;font-size:12px;margin:2px}.status-Confirmed{background:#eaf8ef}.status-Inferred{background:#fff7dd}.status-Unclear{background:#fdecec}.topic{scroll-margin-top:130px}.topic h2{margin:0;font-size:22px}.section{border-top:1px solid var(--border);padding-top:15px;margin-top:15px}.section h3{margin:0 0 9px;font-size:15px}.editable{white-space:pre-wrap;border:1px solid transparent;border-radius:10px;padding:9px;transition:.15s}.editable:hover{background:var(--surface-2)}.editable:focus{outline:none;border-color:#9db2ff;background:#f8faff;box-shadow:0 0 0 3px rgba(49,94,251,.10)}.traffic{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.color{border-radius:15px;padding:15px;border:1px solid}.green{background:var(--green);border-color:#bfe6ce}.yellow{background:var(--yellow);border-color:#f0d891}.red{background:var(--red);border-color:#efc2c5}.color h4{margin:0 0 8px;font-size:15px}.clause{width:100%;min-height:138px;border:1px solid rgba(20,32,54,.14);border-radius:11px;padding:10px;background:rgba(255,255,255,.84);font:inherit;direction:inherit;resize:vertical}.clause:focus{outline:none;border-color:#9db2ff;box-shadow:0 0 0 3px rgba(49,94,251,.10)}.decision{display:flex;gap:7px;flex-wrap:wrap;margin-top:14px}.decision button{border:1px solid var(--border);background:#fff;border-radius:10px;padding:8px 11px;cursor:pointer;font-weight:650}.decision button:hover{border-color:#bdc8d8}.decision button.selected{background:var(--accent);border-color:var(--accent);color:#fff}.segments{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}.segment-card{border-top:4px solid var(--accent)}table{width:100%;border-collapse:separate;border-spacing:0;background:#fff;border:1px solid var(--border);border-radius:14px;overflow:hidden}th,td{border-bottom:1px solid var(--border);border-inline-end:1px solid var(--border);padding:11px;vertical-align:top}tr:last-child td{border-bottom:0}th:last-child,td:last-child{border-inline-end:0}th{background:#f7f9fc;position:sticky;top:119px;text-align:inherit;font-size:12px;color:#526074}.mini{font-size:12px;margin:3px 0;padding:5px 7px;border-radius:7px}.filters{display:flex;gap:9px;flex-wrap:wrap;margin-bottom:15px;padding:10px;background:#fff;border:1px solid var(--border);border-radius:14px;box-shadow:var(--shadow)}.filters input,.filters select{padding:10px 12px;border:1px solid var(--border);border-radius:10px;background:#fff;font:inherit;min-width:220px}.segment-variant{border:1px solid #cbd8ff;background:#f7f9ff;border-radius:14px;padding:15px;margin:14px 0}.prior{font-size:13px}.prior li{margin-bottom:5px}.footer-actions{position:fixed;bottom:18px;inset-inline-end:24px;background:rgba(17,24,39,.94);backdrop-filter:blur(12px);padding:9px;border-radius:14px;display:flex;align-items:center;gap:9px;box-shadow:0 18px 50px rgba(17,24,39,.24);z-index:30}.footer-actions button{padding:10px 14px;border-radius:10px;border:0;background:#fff;cursor:pointer;font-weight:800}.footer-actions .primary{background:var(--accent);color:#fff}.footer-actions .muted{color:#d1d5db}.decision-row{border-bottom:1px solid var(--border);padding:10px 0}.hidden{display:none}
@media(max-width:1050px){.app-shell,[dir="rtl"] .app-shell{display:block}.sidebar,[dir="rtl"] .sidebar{position:relative;height:auto;padding:12px}.brand{padding-bottom:12px}.tabs{flex-direction:row;overflow:auto}.tabs button{width:auto;white-space:nowrap}.sidebar-foot{display:none}.main,[dir="rtl"] .main{display:block}.app-header{position:sticky;top:0}.hero-row{flex-direction:column}.topbar{justify-content:flex-start}.wrap{padding:18px 16px 95px}.traffic{grid-template-columns:1fr}.footer-actions{inset-inline:14px;justify-content:center}.app-header{padding:18px 16px}th{top:104px}}
</style>
</head>
<body>
<div class="app-shell">
  <aside class="sidebar">
    <div class="brand"><div class="brand-mark">§</div><div class="brand-copy"><strong id="brandTitle"></strong><span id="brandSubtitle"></span></div></div>
    <nav class="tabs" id="tabs"></nav>
    <div class="sidebar-foot" id="sidebarStatus"></div>
  </aside>
  <main class="main">
    <header class="app-header">
      <div class="hero-row">
        <div>
          <div class="eyebrow" id="workspaceEyebrow"></div>
          <h1 id="pageTitle"></h1>
          <div class="sub" id="workspaceSubtitle"></div>
          <div class="scope-chips" id="headerScope"></div>
        </div>
        <div class="topbar">
          <input id="approver" placeholder="">
          <button onclick="saveState()" id="saveBtn"></button>
          <button onclick="downloadUpdated()" id="exportBtn"></button>
          <button onclick="downloadDecisions()" id="exportDecisionsBtn"></button>
        </div>
      </div>
    </header>
    <div class="wrap">
      <div class="notice" id="draftNotice"></div>
      <section id="overview" class="tab active"></section>
      <section id="segments" class="tab"></section>
      <section id="matrix" class="tab"></section>
      <section id="topics" class="tab"></section>
      <section id="decisions" class="tab"></section>
    </div>
  </main>
</div>
<div class="footer-actions"><button class="primary" onclick="finalizePlaybook()" id="finalizeBtn"></button><span id="saveStatus" class="muted"></span></div>
<script id="playbook-data" type="application/json">__PLAYBOOK_JSON__</script>
<script id="labels-data" type="application/json">__LABELS_JSON__</script>
<script>
const L=JSON.parse(document.getElementById('labels-data').textContent);
const original=JSON.parse(document.getElementById('playbook-data').textContent);
let model=JSON.parse(JSON.stringify(original));
const stateKey=`contract-playbook:${model.playbook_id||'unknown'}:${model.version||'draft'}`;
let saved={decisions:{},segmentDecisions:{},notes:{}};
try{saved=Object.assign(saved,JSON.parse(localStorage.getItem(stateKey)||'{}'));}catch(e){}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const arr=v=>Array.isArray(v)?v:[];
const isHe=document.documentElement.lang==='he';const statusMap=isHe?{Confirmed:'מאושר',Inferred:'מוסק',Unclear:'טעון הכרעה',Candidate:'סגמנטציה מוצעת',NotDetected:'לא זוהתה סגמנטציה',Draft:'טיוטה',Approved:'מאושר',High:'גבוהה',Medium:'בינונית',Low:'נמוכה'}:{Confirmed:'Confirmed',Inferred:'Inferred',Unclear:'Unclear',Candidate:'Candidate segmentation',NotDetected:'No segmentation detected',Draft:'Draft',Approved:'Approved',High:'High',Medium:'Medium',Low:'Low'};const trStatus=s=>statusMap[s]||s;
function getFamily(){return arr(model.scope_summary?.contract_families)[0]||{};}
function contractTypes(){return arr(model.scope_summary?.contract_families).map(f=>f.contract_family_name).filter(Boolean).join(' · ');}
function companyRoles(){return [...new Set(arr(model.scope_summary?.contract_families).map(f=>f.company_role).filter(Boolean))].join(' · ');}
function setTab(id){document.querySelectorAll('.tab').forEach(x=>x.classList.toggle('active',x.id===id));document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('active',x.dataset.tab===id));}
function decisionKey(ruleId,segmentId='base'){return `${ruleId}::${segmentId}`;}
function decisionControls(key){const d=saved.decisions[key]||'';const opts=[['accepted',L.accept],['edited',L.edit],['rejected',L.reject],['deferred',L.defer],['na',L.na]];return `<div class="decision">${opts.map(([v,t])=>`<button class="${d===v?'selected':''}" onclick="setDecision('${esc(key)}','${v}')">${esc(t)}</button>`).join('')}</div>`;}
function setDecision(key,val){saved.decisions[key]=val;saveState(false);renderDecisions();renderTopics();}
function setSegmentDecision(id,val){saved.segmentDecisions[id]=val;saveState(false);renderSegments();renderDecisions();}
function markRationaleConfirmed(ruleId,segmentId=''){const rule=model.rules.find(r=>r.rule_id===ruleId);if(!rule)return;if(segmentId){const v=arr(rule.segment_variants).find(x=>x.segment_id===segmentId);if(v?.segmentation_rationale)v.segmentation_rationale.rationale_status='Confirmed';}else if(rule.policy_rationale){rule.policy_rationale.rationale_status='Confirmed';}saveState(false);renderTopics();}
function updateRationale(ruleId,field,text,segmentId=''){const rule=model.rules.find(r=>r.rule_id===ruleId);if(!rule)return;if(segmentId){const v=arr(rule.segment_variants).find(x=>x.segment_id===segmentId);if(v?.segmentation_rationale){v.segmentation_rationale[field]=text;v.segmentation_rationale.rationale_status='Draft';}}else{rule.policy_rationale[field]=text;rule.policy_rationale.rationale_status='Draft';}saved.decisions[decisionKey(ruleId,segmentId||'base')]='edited';saveState(false);}
function updateClause(ruleId,color,text,segmentId=''){const rule=model.rules.find(r=>r.rule_id===ruleId);if(!rule)return;let tl=rule.traffic_light;if(segmentId){const v=arr(rule.segment_variants).find(x=>x.segment_id===segmentId);tl=v?.traffic_light;}if(tl?.[color])tl[color].proposed_clause=text;saved.decisions[decisionKey(ruleId,segmentId||'base')]='edited';saveState(false);}
function saveState(show=true){localStorage.setItem(stateKey,JSON.stringify({...saved,model}));if(show)document.getElementById('saveStatus').textContent=new Date().toLocaleTimeString()+ ' ✓';}
(function restore(){try{const x=JSON.parse(localStorage.getItem(stateKey)||'{}');if(x.model)model=x.model;}catch(e){}})();
function download(name,obj){const blob=new Blob([JSON.stringify(obj,null,2)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
function downloadUpdated(){download(`${model.playbook_id||'playbook'}-${model.version||'draft'}-updated.json`,model);}
function downloadDecisions(){download(`${model.playbook_id||'playbook'}-decisions.json`,{playbook_id:model.playbook_id,version:model.version,decisions:saved.decisions,segment_decisions:saved.segmentDecisions,exported_at:new Date().toISOString()});}
function listHTML(items){return `<ul>${arr(items).map(x=>`<li>${esc(typeof x==='string'?x:(x.label||x.criteria||JSON.stringify(x)))}</li>`).join('')}</ul>`;}
function editable(ruleId,field,text,segmentId=''){return `<div class="editable" contenteditable="true" onblur="updateRationale('${esc(ruleId)}','${esc(field)}',this.innerText,'${esc(segmentId)}')">${esc(text)}</div>`;}
function rationaleHTML(rule,r=null,segmentId=''){const x=r||rule.policy_rationale||{};const pairs=segmentId?[
 [L.policyRationale,'executive_segment_rationale'],[L.segmentWhy,'segment_characteristic_and_risk_change'],[L.legal,'legal_basis'],[L.business,'business_basis'],[L.evidence,'internal_evidence_basis'],[L.market,'market_practice_assessment'],[L.greenWhy,'green_boundary_rationale'],[L.yellowWhy,'yellow_boundary_rationale'],[L.redWhy,'red_boundary_rationale'],[L.tradeoff,'tradeoff'],[L.related,'related_clause_effect'],[L.uncertainty,'uncertainties_and_limitations']
]:[
 [L.policyRationale,'executive_policy_rationale'],[L.purpose,'protected_interest_and_clause_purpose'],[L.legal,'legal_risk_and_legal_framework'],[L.allocation,'contractual_risk_allocation_mechanism'],[L.roleFit,'company_role_and_policy_fit'],[L.business,'business_operational_impact'],[L.evidence,'internal_evidence_rationale'],[L.market,'market_practice_assessment'],[L.greenWhy,'green_boundary_rationale'],[L.yellowWhy,'yellow_boundary_rationale'],[L.redWhy,'red_boundary_rationale'],[L.tradeoff,'tradeoff_statement'],[L.related,'related_clause_rationale'],[L.uncertainty,'uncertainties_and_limitations']
];
 let html=`<div class="section"><h3>${esc(L.policyRationale)}</h3><span class="pill">${esc(L.rationaleStatus)}: ${esc(trStatus(x.rationale_status||'Draft'))}</span>`;
 for(const [label,field] of pairs){if(x[field]!==undefined)html+=`<div class="section"><h3>${esc(label)}</h3>${editable(rule.rule_id,field,x[field],segmentId)}</div>`;}
 if(arr(x.applicability_scenarios).length)html+=`<div class="section"><h3>${esc(L.applicability)}</h3>${listHTML(x.applicability_scenarios)}</div>`;
 html+=`<button onclick="markRationaleConfirmed('${esc(rule.rule_id)}','${esc(segmentId)}')">${esc(L.acceptRationale)}</button></div>`;return html;
}
function colorHTML(rule,tl,color,segmentId=''){const b=tl?.[color]||{};const title={green:L.green,yellow:L.yellow,red:L.red}[color];return `<div class="color ${color}"><h4>${esc(title)}</h4><div><b>${esc(b.position||'')}</b></div><div class="section"><h3>${esc(L.criteria)}</h3>${listHTML(b.match_criteria)}</div>${color==='yellow'?`<div class="section"><h3>${esc(L.comments)}</h3>${listHTML(b.comments)}</div>`:''}<div class="section"><h3>${esc(L.clause)}</h3><textarea class="clause" oninput="updateClause('${esc(rule.rule_id)}','${color}',this.value,'${esc(segmentId)}')">${esc(b.proposed_clause||'')}</textarea></div>${priorHTML(b.previous_agreements_where_language_accepted)}</div>`;}
function priorHTML(items){if(!arr(items).length)return '';return `<div class="section prior"><h3>${esc(L.prior)}</h3><ul>${items.map(x=>`<li>${esc(x.agreement_label||x.agreement_id)} — ${esc(x.date||'')} — ${esc(x.similarity||'')} — ${esc(x.clause_ref||'')}</li>`).join('')}</ul></div>`;}
function trafficHTML(rule,tl,segmentId=''){return `<div class="traffic">${['green','yellow','red'].map(c=>colorHTML(rule,tl,c,segmentId)).join('')}</div>`;}
function renderOverview(){const segs=arr(model.segmentation_model?.segments);document.getElementById('overview').innerHTML=`<div class="grid"><div class="card"><div class="muted">${esc(L.family)}</div><div class="metric" style="font-size:20px">${esc(contractTypes()||'—')}</div></div><div class="card"><div class="muted">${esc(L.role)}</div><div class="metric" style="font-size:20px">${esc(companyRoles()||'—')}</div></div><div class="card"><div class="muted">${esc(L.documents)}</div><div class="metric">${esc(model.scope_summary?.total_document_count||0)}</div></div><div class="card"><div class="muted">${esc(L.status)}</div><div class="metric" style="font-size:20px">${esc(trStatus(model.playbook_status))}</div></div><div class="card"><div class="muted">${esc(L.segStatus)}</div><div class="metric" style="font-size:20px">${esc(trStatus(model.segmentation_model?.status))}</div><div>${segs.map(s=>`<span class="badge">${esc(s.label)}</span>`).join('')}</div></div></div>${model.scope_summary?.scope_limitations?.length?`<div class="card"><h3>${esc(L.uncertainty)}</h3>${listHTML(model.scope_summary.scope_limitations)}</div>`:''}`;}
function renderSegments(){const segs=arr(model.segmentation_model?.segments);if(!segs.length){document.getElementById('segments').innerHTML=`<div class="card">${esc(L.noSegments)}</div>`;return;}document.getElementById('segments').innerHTML=`<div class="segments">${segs.map(s=>`<div class="card segment-card"><h3>${esc(s.label)}</h3><div>${esc(s.description||'')}</div><div class="section"><b>${esc(L.criteria)}:</b>${listHTML(s.criteria)}</div><div><span class="pill">${esc(L.policyStatus)}: ${esc(trStatus(s.policy_status))}</span> <span class="pill">${esc(L.confidence)}: ${esc(trStatus(s.confidence||''))}</span></div><div class="decision">${[['accepted',L.accept],['edited',L.edit],['rejected',L.reject],['deferred',L.defer]].map(([v,t])=>`<button class="${saved.segmentDecisions[s.segment_id]===v?'selected':''}" onclick="setSegmentDecision('${esc(s.segment_id)}','${v}')">${esc(t)}</button>`).join('')}</div></div>`).join('')}</div>`;}
function cellSummary(tl){if(!tl)return '—';return ['green','yellow','red'].map(c=>`<div class="mini ${c}"><b>${c==='green'?L.green:c==='yellow'?L.yellow:L.red}</b><br>${esc((tl[c]?.position||'').slice(0,120))}</div>`).join('');}
function renderMatrix(){const segs=arr(model.segmentation_model?.segments);let h=`<div class="card" style="overflow:auto"><table><thead><tr><th>${esc(L.topics)}</th><th>${esc(L.allSegments)}</th>${segs.map(s=>`<th>${esc(s.label)}</th>`).join('')}</tr></thead><tbody>`;for(const r of arr(model.rules)){h+=`<tr><td><a href="#" onclick="openTopic('${esc(r.rule_id)}');return false">${esc(r.topic_name)}</a></td><td>${cellSummary(r.traffic_light)}</td>`;for(const s of segs){const v=arr(r.segment_variants).find(x=>x.segment_id===s.segment_id);h+=`<td>${v?cellSummary(v.traffic_light):'<span class="muted">—</span>'}</td>`;}h+='</tr>';}h+='</tbody></table></div>';document.getElementById('matrix').innerHTML=h;}
function openTopic(id){setTab('topics');setTimeout(()=>document.getElementById(`topic-${CSS.escape(id)}`)?.scrollIntoView({behavior:'smooth'}),20);}
function renderTopics(){let h=`<div class="filters"><input id="topicSearch" placeholder="${esc(L.search)}" oninput="renderTopicsFiltered()"><select id="segmentFilter" onchange="renderTopicsFiltered()"><option value="">${esc(L.allSegments)}</option>${arr(model.segmentation_model?.segments).map(s=>`<option value="${esc(s.segment_id)}">${esc(s.label)}</option>`).join('')}</select></div><div id="topicList"></div>`;document.getElementById('topics').innerHTML=h;renderTopicsFiltered();}
function renderTopicsFiltered(){const search=(document.getElementById('topicSearch')?.value||'').toLowerCase();const seg=document.getElementById('segmentFilter')?.value||'';let h='';for(const r of arr(model.rules)){if(search&&!String(r.topic_name).toLowerCase().includes(search))continue;const variants=arr(r.segment_variants);if(seg&&!variants.some(v=>v.segment_id===seg))continue;h+=`<article class="card topic" id="topic-${esc(r.rule_id)}"><h2>${esc(r.topic_name)}</h2><div><span class="badge status-${esc(r.policy_status)}">${esc(L.policyStatus)}: ${esc(trStatus(r.policy_status))}</span> <span class="badge">${esc(L.confidence)}: ${esc(trStatus(r.confidence))}</span></div><div class="section"><h3>${esc(L.policyRationale)}</h3>${rationaleHTML(r)}</div><div class="section">${trafficHTML(r,r.traffic_light)}</div>${decisionControls(decisionKey(r.rule_id))}`;
 for(const v of variants){if(seg&&v.segment_id!==seg)continue;const s=arr(model.segmentation_model?.segments).find(x=>x.segment_id===v.segment_id)||{};h+=`<div class="segment-variant"><h3>${esc(s.label||v.segment_id)}</h3>${rationaleHTML(r,v.segmentation_rationale,v.segment_id)}${trafficHTML(r,v.traffic_light,v.segment_id)}${decisionControls(decisionKey(r.rule_id,v.segment_id))}</div>`;}
 h+='</article>';}document.getElementById('topicList').innerHTML=h;}
function renderDecisions(){const rows=[];for(const r of arr(model.rules)){const base=decisionKey(r.rule_id);rows.push({name:r.topic_name,key:base,d:saved.decisions[base]||'deferred'});for(const v of arr(r.segment_variants)){const s=arr(model.segmentation_model?.segments).find(x=>x.segment_id===v.segment_id);const k=decisionKey(r.rule_id,v.segment_id);rows.push({name:`${r.topic_name} — ${s?.label||v.segment_id}`,key:k,d:saved.decisions[k]||'deferred'});}}document.getElementById('decisions').innerHTML=`<div class="card"><h2>${esc(L.unresolved)}</h2>${rows.map(x=>`<div class="decision-row"><b>${esc(x.name)}</b> — ${esc(x.d)}</div>`).join('')}</div>`;}
function finalizePlaybook(){const approver=document.getElementById('approver').value.trim();const missing=[];for(const r of arr(model.rules)){const k=decisionKey(r.rule_id);if(!['accepted','edited','na'].includes(saved.decisions[k]))missing.push(r.topic_name);if(saved.decisions[k]!=='na'&&r.policy_rationale?.rationale_status!=='Confirmed')missing.push(`${r.topic_name}: ${L.rationaleStatus}`);for(const v of arr(r.segment_variants)){const vk=decisionKey(r.rule_id,v.segment_id);if(!['accepted','edited','na'].includes(saved.decisions[vk]))missing.push(`${r.topic_name}/${v.segment_id}`);if(saved.decisions[vk]!=='na'&&v.segmentation_rationale?.rationale_status!=='Confirmed')missing.push(`${r.topic_name}/${v.segment_id}: ${L.rationaleStatus}`);}}if(arr(model.segmentation_model?.segments).length){for(const s of model.segmentation_model.segments){if(!['accepted','edited','rejected'].includes(saved.segmentDecisions[s.segment_id]||''))missing.push(s.label);}}if(!approver)missing.push(L.approver);if(missing.length){alert(`${L.unresolved}:\n- `+missing.join('\n- '));return;}model.playbook_status='Approved';model.approved_by=approver;model.approved_at=new Date().toISOString();for(const r of model.rules){if(saved.decisions[decisionKey(r.rule_id)]!=='na')r.policy_status='Confirmed';for(const v of arr(r.segment_variants)){if(saved.decisions[decisionKey(r.rule_id,v.segment_id)]!=='na')v.policy_status='Confirmed';}}for(const s of arr(model.segmentation_model?.segments)){if(['accepted','edited'].includes(saved.segmentDecisions[s.segment_id]))s.policy_status='Confirmed';}if(arr(model.segmentation_model?.segments).every(s=>s.policy_status==='Confirmed'))model.segmentation_model.status='Confirmed';saveState();downloadUpdated();renderAll();alert(L.finalize);}
function renderAll(){document.getElementById('pageTitle').textContent=L.title;document.getElementById('brandTitle').textContent=L.title;document.getElementById('brandSubtitle').textContent=L.workspaceSubtitle;document.getElementById('workspaceSubtitle').textContent=L.workspaceSubtitle;document.getElementById('workspaceEyebrow').textContent=L.workspaceEyebrow;document.getElementById('headerScope').innerHTML=[[L.family,contractTypes()],[L.role,companyRoles()],[L.documents,model.scope_summary?.total_document_count||0],[L.status,trStatus(model.playbook_status)]].filter(x=>x[1]!==undefined&&x[1]!==null&&x[1]!=='').map(([k,v])=>`<span class="scope-chip"><strong>${esc(k)}:</strong> ${esc(v)}</span>`).join('');document.getElementById('sidebarStatus').innerHTML=`<div>${esc(L.status)}: <strong>${esc(trStatus(model.playbook_status))}</strong></div><div style="margin-top:5px">${esc(L.segStatus)}: <strong>${esc(trStatus(model.segmentation_model?.status))}</strong></div>`;document.getElementById('approver').placeholder=L.approver;document.getElementById('saveBtn').textContent=L.save;document.getElementById('exportBtn').textContent=L.export;document.getElementById('exportDecisionsBtn').textContent=L.exportDecisions;document.getElementById('finalizeBtn').textContent=L.finalize;document.getElementById('draftNotice').textContent=L.draftWarning;const tabs=[['overview','◫',L.overview],['segments','◉',L.segments],['matrix','⌘',L.matrix],['topics','≡',L.topics],['decisions','✓',L.decisions]];document.getElementById('tabs').innerHTML=tabs.map(([id,icon,t],i)=>`<button data-tab="${id}" class="${i===0?'active':''}" onclick="setTab('${id}')"><span style="display:inline-block;min-width:22px;opacity:.82">${icon}</span>${esc(t)}</button>`).join('');renderOverview();renderSegments();renderMatrix();renderTopics();renderDecisions();}
renderAll();
</script>
</body>
</html>'''
    html = (template.replace("__LANG__", "he" if he else "en")
                    .replace("__DIR__", direction)
                    .replace("__TITLE__", labels["title"])
                    .replace("__PLAYBOOK_JSON__", data_json)
                    .replace("__LABELS_JSON__", labels_json))
    Path(out).write_text(html, encoding="utf-8")
    print(f"WROTE {out}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: render_playbook_html.py PLAYBOOK.json OUTPUT.html")
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
