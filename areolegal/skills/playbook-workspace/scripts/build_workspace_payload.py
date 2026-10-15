#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ממיר את playbook-model.json לנתוני הדף של סביבת העבודה.

נתוני הדף נבנים בסקריפט בלבד (`dashboard_spec.md`, "מאיפה נבנים נתוני הדף").
אין לכתוב אותם ביד, ואין לנחש שדה שאין לו מקור במודל: שדה חסר נשאר ריק,
והתבנית מסתירה את מה שנשען עליו. כל ההמרות כאן הן העברה או צמצום של מה
שכתוב במודל, ואין כאן חישוב מדיניות.

  python3 build_workspace_payload.py playbook-model.json payload.json

ואחר כך:
  python3 validate_data.py --data payload.json
  python3 build_dashboard.py <תבנית> payload.json dashboard.html
"""
import argparse
import io
import json
import re
import sys

LIGHTS = ("green", "yellow", "red")
# המסלול שבו נבנה הפלייבוק, לפס הבסיס
ORIGIN_TO_PATH = {"own": "own", "own_plus_market": "own_plus_market",
                  "market_built": "market_built"}
STATUS = {"Draft": "Draft", "Approved": "Approved", "Superseded": "Superseded"}
# התווית שמסמנת עמדה שאינה מההסכמים של החברה
AREO_LABEL = "הצעת Areo (לא מבוסס על מסמכי הלקוח)"


def warn(msg):
    sys.stderr.write("אזהרה: %s\n" % msg)


def ls_key(text):
    """מפתח לשמירת סימונים בדפדפן: אותיות לטיניות, ספרות וקו תחתון בלבד."""
    k = re.sub(r"[^A-Za-z0-9_]+", "_", str(text or "")).strip("_")
    return k or "playbook"


def first_line(text, limit=160):
    s = re.sub(r"\s+", " ", str(text or "")).strip()
    return s[:limit]


def pick(d, *names):
    """הערך הראשון שקיים מבין השמות. המודל התפתח, ושמות ישנים עוד בשימוש."""
    for n in names:
        if isinstance(d, dict) and d.get(n) not in (None, "", [], {}):
            return d[n]
    return None


def build_meta(m):
    scope = m.get("scope_summary") or {}
    basis = scope.get("corpus_basis") or {}
    fams = scope.get("contract_families") or []
    fam = fams[0] if fams else {}
    family = pick(fam, "contract_family_name", "label") or ""
    role = pick(fam, "company_role") or ""
    company = pick(m.get("company") or {}, "name") or pick(m, "company_name") or ""
    pid = pick(m, "playbook_id", "family_id") or "playbook"
    meta = {
        "id": pid,
        "slug": ls_key(pick(m, "family_id", "playbook_id")),
        "ls_key": ls_key(pid),
        "company": company,
        "title": (family + (" · " + role if role else "")) or "פלייבוק חוזי",
        "version": str(pick(m, "version") or "1.0"),
        "created": pick(m, "generated_at") or "",
        "updated": pick(m, "last_updated", "generated_at") or "",
        "status": STATUS.get(pick(m, "status") or "Draft", "Draft"),
    }
    # פס הבסיס: המספר נספר בקוד בבונה, וכאן הוא רק מועבר
    units = basis.get("agreement_units")
    origin = scope.get("corpus_origin")
    if isinstance(units, int) and origin in ORIGIN_TO_PATH:
        meta["build_path"] = {"n": units, "path": ORIGIN_TO_PATH[origin]}
    else:
        warn("אין corpus_basis.agreement_units או corpus_origin במודל, "
             "ולכן פס הבסיס לא יוצג")
    # המעמד והתווית נגזרים במודל, והדף רק מציג אותם מילה במילה. הדף אינו
    # מחשב תווית, ואינו ממציא אותה כשהמודל לא כתב אותה
    gate = m.get("policy_gate") or {}
    for key in ("status_label", "label_now"):
        v = pick(m, key) or pick(gate, key)
        if v:
            meta[key] = v
    for key in ("approved_count", "positions_count"):
        v = gate.get(key)
        if isinstance(v, int):
            meta[key] = v
    mr = m.get("market_research") or {}
    date = pick(mr, "research_date", "date", "performed_at")
    if date:
        meta["market_research_date"] = date
    # התפקידים הם נתון של הפלייבוק, ולא רשימה קבועה של הסקיל
    roles = [x for x in (scope.get("company_roles") or []) if isinstance(x, dict)]
    if roles:
        meta["company_roles"] = [{"role": pick(x, "role") or "",
                                  "label": pick(x, "label") or ""} for x in roles]
    main = pick(scope, "main_role")
    if main:
        meta["main_role"] = main
    short = []
    if isinstance(units, int):
        short.append("%d הסכמים" % units)
    if basis.get("files"):
        short.append("מתוך %d קבצים" % basis["files"])
    if short:
        meta["evidence_short"] = ", ".join(short) + "."
    return meta


def scope_block(m):
    sc = m.get("scope_summary") or {}
    out = {"contract_families": sc.get("contract_families") or []}
    for a, b in (("limitations", "limitations"), ("date_range", "date_range"),
                 ("locations", "source_locations")):
        v = pick(sc, b)
        if v is not None:
            out[a] = v
    return out


def build_sources(m):
    """מפתח המקור ← מה שהתבנית מציגה עליו. `paper` מגיע מהמודל ולא מהשם."""
    out, friendly = {}, {}
    for row in m.get("source_log") or []:
        sid = pick(row, "source_id")
        if not sid:
            continue
        name = pick(row, "title", "file") or sid
        src = {"label": name, "name": name, "kind": "internal"}
        src["title"] = name
        for a, b in (("paper", "paper"), ("doc_role", "doc_role"),
                     ("date", "signed_at"), ("counterparty", "counterparty"),
                     ("url", "url"), ("channel", "channel"),
                     ("acceptance_mode", "acceptance_mode"),
                     ("role", "company_role_in_source"), ("status", "status"),
                     ("path", "path"), ("loc", "folder")):
            v = pick(row, b)
            if v is not None:
                src[a] = v
        if row.get("doc_role") == "template":
            src["kind"] = "internal"
        out[sid] = src
        friendly[sid] = pick(row, "short_name") or first_line(name, 60)
    # מקורות השוק הם חיצוניים, ונשמרים בנפרד כדי שלא ייספרו באחוז ההסכמים
    for row in ((m.get("market_research") or {}).get("sources") or []) + (m.get("market") or []):
        sid = pick(row, "source_id", "id")
        if sid and sid not in out:
            out[sid] = {"label": pick(row, "title") or sid,
                        "name": pick(row, "title") or sid, "kind": "external",
                        "url": pick(row, "url") or "", "date": pick(row, "checked_at", "date") or ""}
    return out, friendly


def build_market(m):
    rows = []
    for row in ((m.get("market_research") or {}).get("sources") or []) + (m.get("market") or []):
        sid = pick(row, "source_id", "id")
        if not sid:
            continue
        out = {"id": sid, "title": pick(row, "title") or sid,
               "body": pick(row, "issuer", "body") or "",
               "url": pick(row, "url") or "",
               "date": pick(row, "doc_date", "checked_at", "date") or ""}
        for a, b in (("retrieved_at", "retrieved_at"), ("drafter_role", "drafter_role"),
                     ("drafted_by", "drafted_by")):
            v = pick(row, b)
            if v:
                out[a] = v
        sup = row.get("supports") or row.get("topics")
        if isinstance(sup, list) and sup:
            out["supports"] = sup
        rows.append(out)
    return rows


def light(obj, rule_id, color):
    """עמדה אחת בשלוש העמדות. `label` נקבע לפי `basis` ולא לפי מספר הציטוטים."""
    if not isinstance(obj, dict):
        return None
    out = {}
    pos = pick(obj, "position", "pos", "text")
    if pos:
        out["pos"] = pos
    # הקריטריונים הם מערך שהתבנית חותכת, ולכן הם תמיד מערך
    crit = obj.get("match_criteria") or obj.get("crit") or []
    out["crit"] = [str(c) for c in crit] if isinstance(crit, list) else [str(crit)]
    out["evidence"] = obj.get("evidence") or []
    for a, b in (("basis", "basis"), ("basis_note", "basis_note"),
                 ("why", "meaning"), ("notes", "notes"), ("comments", "comments"),
                 ("source_label", "source_label")):
        v = pick(obj, b)
        if v is not None:
            out[a] = v
    pc = obj.get("proposed_clause")
    if isinstance(pc, dict):
        out["clause"] = pick(pc, "he", "en") or ""
    elif isinstance(pc, str) and pc:
        out["clause"] = pc
    refs = obj.get("basis_refs")
    if isinstance(refs, list) and refs:
        out["basis_refs"] = refs
    if obj.get("basis") in ("areo_proposal", "market_standard"):
        out["label"] = pick(obj, "label") or AREO_LABEL
        ids = obj.get("market_source_ids")
        if isinstance(ids, list) and ids:
            out["market_source_ids"] = ids
            if obj.get("basis") == "market_standard" and len(ids) < 3:
                warn("%s %s: market_standard עם %d מקורות, נדרשים שלושה"
                     % (rule_id, color, len(ids)))
        elif obj.get("basis") == "market_standard":
            warn("%s %s: market_standard בלי market_source_ids" % (rule_id, color))
    # מה המסלול מטיל על החברה, שורה לכל תפקיד שיש לה בהסכם. `role_effects`
    # הוא הנוסח הכללי; שמות as_*_effect נשמרים לפלייבוק הדדי שנכתב לפניו
    eff = obj.get("role_effects")
    if isinstance(eff, dict):
        eff = {k: v for k, v in eff.items() if v}
        if eff:
            out["role_effects"] = eff
    for a in ("as_discloser_effect", "as_recipient_effect", "company_effect"):
        v = obj.get(a)
        if v:
            out[a] = v
    if color == "yellow":
        fw = obj.get("fallback_wording")
        if isinstance(fw, dict) and fw.get("text"):
            out["fallback_wording"] = {"text": fw["text"], "source": fw.get("source") or ""}
    return out or None


def build_rules(m, cites):
    """כלל ← סעיף בדף. הציטוטים נאספים לרשימה אחת שהדף סופר לפיה."""
    rules, seen = [], set()
    for r in m.get("rules") or []:
        rid = pick(r, "rule_id", "id")
        if not rid:
            warn("כלל בלי rule_id נדלג")
            continue
        if rid in seen:
            warn("rule_id כפול: %s" % rid)
        seen.add(rid)
        rat = r.get("policy_rationale") or {}
        row = {"id": rid, "topic": pick(r, "topic_name", "topic") or rid,
               "issue": pick(r, "clause_issue") or ""}
        for a, b in (("num", "clause_number"), ("kind", "clause_kind"),
                     ("they", "counterparty_objective"), ("pb", "playbook_id"),
                     ("conf", "confidence"), ("why", "why_address_topic"),
                     ("reg", "regulatory_status"), ("policy", "policy_status")):
            v = pick(r, b)
            if v is not None:
                row[a] = v
        if rat:
            row["rat"] = rat
        tl = {}
        src_tl = r.get("traffic_light") or r.get("tl") or {}
        for c in LIGHTS:
            one = light(src_tl.get(c), rid, c)
            if one:
                tl[c] = one
        if tl:
            row["tl"] = tl
        pc = r.get("proposed_clause") or {}
        if pc:
            row["clause"] = pick(pc, "he", "en") or ""
            row["clause_en"] = pc.get("en") or ""
            row["clause_lang"] = pc.get("source_language") or ""
        norms = []
        for n in r.get("legal_basis_layers") or []:
            if n.get("statute"):
                norms.append({"law": n.get("statute") or "", "ref": n.get("section") or "",
                              "meaning": first_line(pick(n, "meaning", "effect") or "", 220)})
        if norms:
            row["norms"] = norms
        impacts = []
        for i in r.get("related_clauses") or r.get("impacts") or []:
            impacts.append({"related_rule_id": pick(i, "related_rule_id", "rule_id", "ref") or "",
                            "impact": pick(i, "impact", "relation", "effect") or "",
                            "action": pick(i, "action") or ""})
        if impacts:
            row["impacts"] = impacts
        presence = r.get("presence_rule") or r.get("presence")
        if isinstance(presence, dict) and presence:
            row["presence"] = {"requirement": pick(presence, "requirement") or "",
                               "missing_clause_color": pick(presence, "missing_clause_color") or ""}
        elif isinstance(presence, str) and presence:
            row["presence"] = {"requirement": presence, "missing_clause_color": ""}
        else:
            warn("%s: אין presence_rule. הסינון לפי נחיצות הסעיף לא יראה אותו" % rid)
        trig = r.get("activation_conditions")
        if isinstance(trig, list) and trig:
            row["trig"] = {"he": [str(x) for x in trig], "en": []}
        # התמונה הראייתית בכרטיס: שורה למקור, ולא שורה לציטוט
        ev_rows, by_src = [], {}
        for e in r.get("evidence") or []:
            sid = pick(e, "source_ref", "source_id")
            if not sid or sid in by_src:
                continue
            by_src[sid] = True
            ev_rows.append({"source_id": sid, "weight": pick(e, "weight") or "",
                            "note": pick(e, "note", "tag") or ""})
        if ev_rows:
            row["ev"] = ev_rows
        ec = r.get("evidence_count") or {}
        if ec:
            row["ec"] = ec
        fb = r.get("fallback_origin") or {}
        if fb.get("label_he"):
            row["fallback_origin"] = {"label_he": fb["label_he"],
                                      "baseline": fb.get("baseline") or ""}
        # ראיות: כל אחת נכנסת לרשימת הציטוטים עם המסלול שהיא תומכת בו
        for ev in r.get("evidence") or []:
            cid = pick(ev, "evidence_id", "id") or ("c%d" % (len(cites) + 1))
            track = pick(ev, "track")
            if not track:
                warn("%s: ראיה %s בלי track, לא תיספר באחוז" % (rid, cid))
            cite = {"id": cid, "rules": [rid], "src": pick(ev, "source_ref", "source_id") or "",
                    "text": pick(ev, "quote", "text") or "",
                    "ref": pick(ev, "clause_ref", "ref") or "",
                    "tag": pick(ev, "tag") or "",
                    "side": pick(ev, "side") or "pro"}
            if track:
                cite["track"] = track
            for a, b in (("weight", "weight"), ("segment_id", "segment_id")):
                v = pick(ev, b)
                if v:
                    cite[a] = v
            cites.append(cite)
        rules.append(row)
    return rules


def build_segments(m, rules_by_id):
    """הסגמנטים לדף, והווריאנט נתלה על הכלל שהוא משנה: התבנית קוראת
    `r.variants[].seg` ולא מחפשת בתוך הסגמנט."""
    out = []
    for s in (m.get("segmentation_model") or {}).get("segments") or []:
        sid = pick(s, "segment_id", "id")
        if not sid:
            continue
        out.append({"segment_id": sid, "label": pick(s, "segment_name", "label", "name") or sid,
                    "criteria": pick(s, "criteria", "criterion") or "",
                    "status": pick(s, "status") or ""})
        for v in s.get("variants") or []:
            rid = pick(v, "rule_id")
            row = rules_by_id.get(rid)
            if not row:
                warn("ווריאנט בסגמנט %s מפנה לכלל %s שאינו בפלייבוק" % (sid, rid))
                continue
            vr = {"seg": sid, "mode": pick(v, "negotiation_mode") or ""}
            tl = {}
            for c in LIGHTS:
                one = light((v.get("traffic_light") or {}).get(c), sid, c)
                if one:
                    tl[c] = one
            if tl:
                vr["tl"] = tl
            rat = v.get("segment_rationale") or v.get("policy_rationale")
            if rat:
                vr["rat"] = rat
            row.setdefault("variants", []).append(vr)
    return out


def build_queue(m):
    out = []
    for q in m.get("validation_queue") or []:
        out.append({"item_id": pick(q, "id", "item_id") or "",
                    "issue": pick(q, "topic", "issue") or "",
                    "question": pick(q, "question") or "",
                    "impact": pick(q, "why", "impact") or "",
                    "scope": pick(q, "scope") or "", "rule_id": pick(q, "rule_id") or "",
                    "segment_id": pick(q, "segment_id") or "",
                    "severity": pick(q, "severity") or "",
                    "rec": pick(q, "recommendation") or ""})
    return out


def build_findings(m):
    out = []
    for f in (m.get("company_findings") or []) + (m.get("template_findings") or []):
        out.append({"title": pick(f, "title", "finding") or "",
                    "body": pick(f, "detail", "body") or "",
                    "severity": (pick(f, "severity") or "").lower() or "medium",
                    "refs": f.get("clause_refs") or f.get("refs") or []})
    return out


def build_playbooks(m):
    """התצוגה הרוחבית. רק מה שהמודל יודע על פלייבוקים אחרים של החברה."""
    out = []
    for b in m.get("company_playbooks") or m.get("playbooks") or []:
        bid = pick(b, "playbook_id", "id")
        if not bid:
            continue
        out.append({"id": bid, "family": pick(b, "family", "contract_family_name") or "",
                    "role": pick(b, "role", "company_role") or "",
                    "rules": b.get("rules") or 0, "segments": b.get("segments") or 0,
                    "scanned": b.get("scanned") or b.get("agreement_units") or 0,
                    "updated": pick(b, "updated", "last_updated") or "",
                    "current": bool(b.get("current"))})
    return out


def convert(m):
    cites = []
    sources, friendly = build_sources(m)
    rules = build_rules(m, cites)
    by_id = {r["id"]: r for r in rules}
    payload = {
        "meta": build_meta(m),
        "scope": scope_block(m),
        "sources": sources,
        "friendly": friendly,
        "rules": rules,
        "cites": cites,
        "segments": build_segments(m, by_id),
        "precedents": m.get("previous_agreements_where_language_accepted") or [],
        "templateFindings": build_findings(m),
        "queue": build_queue(m),
    }
    for key, value in (("reg", m.get("regulatory_research")),
                       ("commercial", m.get("commercial")),
                       ("coverage", m.get("coverage")),
                       ("market", build_market(m)),
                       ("playbooks", build_playbooks(m)),
                       ("external_sources", m.get("external_sources")),
                       ("external_sources_table", m.get("external_sources_table")),
                       ("assumptions", m.get("assumptions")),
                       ("cross", m.get("cross_family_links"))):
        if value:
            payload[key] = value
    return payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("out")
    ap.add_argument("--meta", help="שדות הצגה שאינם במודל, למשל הודעת הדגמה או docAccess")
    a = ap.parse_args()
    m = json.load(io.open(a.model, encoding="utf-8"))
    payload = convert(m)
    if a.meta:
        extra = json.loads(io.open(a.meta, encoding="utf-8").read())
        # תוספות הצגה בלבד. הן אינן יוצרות עמדה, ראיה או מספר
        for k, v in (extra.get("meta") or extra).items():
            payload["meta"][k] = v
    io.open(a.out, "w", encoding="utf-8").write(
        json.dumps(payload, ensure_ascii=False, indent=2))
    print("נכתב %s: %d סעיפים, %d ציטוטים, %d מקורות, %d סגמנטים"
          % (a.out, len(payload["rules"]), len(payload["cites"]),
             len(payload["sources"]), len(payload["segments"])))
    bp = payload["meta"].get("build_path")
    if bp:
        print("פס הבסיס: %d הסכמים, מסלול %s" % (bp["n"], bp["path"]))
    print("הבא: python3 validate_data.py --data %s" % a.out)


if __name__ == "__main__":
    main()
