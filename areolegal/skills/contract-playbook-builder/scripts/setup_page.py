#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""עמוד ההקמה (skills/contract-setup-diagnostician/assets/setup-page.html) בשלב הפלייבוק: שני תפקידים.

1. init: בונה את העמוד במצב אישור מהפלייבוק עצמו. העמדות שמוצגות הן רק אלה שעוד לא אושרו, לפי אותו חישוב
   מעמד שכל המערכת קוראת (playbook/status.py), ולכל נושא שטעון בדיקה משפטית מוצג מה צריך לבדוק.

       python3 -B setup_page.py init --model playbook-model.json --records "Areo-נתונים/אישורים" \\
           --page "AREO_RT/skills/contract-setup-diagnostician/assets/setup-page.html" \\
           --out "<קובץ זמני>.html" [--approver-name "<שם מלא>" --approver-role "<תפקיד>"] [--workspace-url URL]

2. apply: קולט את ההודעה שהעמוד שלח (kind: areo_playbook_decisions) דרך תור האישור הרשמי בצ'אט
   (ingest_approval.py --queue / --answer), ולא במסלול נפרד: אותן רשומות, אותו מעמד, ואותה נעילה אחת לבדיקה
   משפטית. נושא שאושר: "לאשר", ובנושא טעון בדיקה משפטית "נבדק ולאשר". נושא שביקשו לשנות, שלא אושר, או
   שעורך דין יעבור עליו אחר כך: "לדלג", והוא נשאר פתוח בסביבת העבודה. השינויים וההערות מודפסים לסוכן.

       python3 -B setup_page.py apply --decisions <decisions.json> --model playbook-model.json \\
           --core playbook-core.json --index Areo-נתונים/playbooks/index.json --records "Areo-נתונים/אישורים"

decisions.json הוא השדה answers מההודעה, כמו שהוא: {family, approver: {name, role}, date, decisions: [...]}.
"""
import io
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import areo_lib  # noqa: F401,E402  מוסיף את areolegal/lib לנתיב הייבוא

from playbook import ingest_approval as IA  # noqa: E402
from playbook import status as S  # noqa: E402

MARKER = "/*__AREO_INIT__*/null"
HERE = os.path.dirname(os.path.abspath(__file__))
CLI = os.path.join(HERE, "ingest_approval.py")
MAX_ROUNDS = 20


def _load(p):
    with io.open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _track(rule, t):
    return (rule.get("traffic_light") or {}).get(t) or {}


def _position(x):
    return str(x.get("position") or "").strip()


def _cells(model, model_path, records):
    cells = S.record_cells_for(model, model_path)
    if not cells and records:
        _, rec = IA.current_record(records)
        if rec:
            cells = IA.record_cells(rec)
    return cells or {}


def family_name(model):
    """שם סוג ההסכם כפי שהלקוח קורא לו, והצד של החברה: "הסכמי שירותים (מקבלת השירותים)"."""
    fams = (model.get("scope_summary") or {}).get("contract_families") or [{}]
    f = next((x for x in fams if x.get("contract_family_id") == model.get("family_id")), fams[0]) or {}
    name = model.get("family_label") or f.get("contract_family_name") or ""
    role = f.get("company_role") or ""
    return "%s (%s)" % (name, role) if name and role else name


def build_init(model, model_path, records=None, approver=None, workspace_url=None):
    """{mode: approve, family, positions[], legal{}, approver, workspace_url}. רק נושאים שיש בהם תא שלא אושר."""
    cells = _cells(model, model_path, records)
    st = S.derive_status(model, cells)
    approved = set(st["approved_keys"])
    positions, legal = [], {}
    for rule in model.get("rules") or []:
        rid = rule["rule_id"]
        keys = [S.cell_key(rid, t) for t in S.TRACKS if _position(_track(rule, t))]
        if not keys or all(k in approved for k in keys):
            continue
        g = _track(rule, "green")
        concerns = [x for x in (rule.get("legal_review_required") or []) if isinstance(x, dict)]
        positions.append({
            "id": rid, "t": rule.get("topic_name") or "", "imp": rule.get("importance") or "",
            "g": _position(g), "y": _position(_track(rule, "yellow")), "r": _position(_track(rule, "red")),
            "areo": g.get("basis") == "areo_proposal", "n": len(g.get("evidence") or []),
            "legal": bool(concerns),
        })
        if concerns:
            legal[rid] = str(concerns[0].get("concern") or "").strip()
    out = {"mode": "approve", "family": family_name(model), "positions": positions, "legal": legal}
    if approver and IA._is_person_name(approver.get("name") or ""):
        out["approver"] = {"name": approver["name"], "role": approver.get("role") or ""}
    if workspace_url:
        out["workspace_url"] = workspace_url
    return out


def write_page(page, init, out):
    with io.open(page, encoding="utf-8") as fh:
        html = fh.read()
    if MARKER not in html:
        raise SystemExit("בעמוד אין את הסימון %s" % MARKER)
    # JSON בתוך <script>: "</" נשבר כדי שטקסט בעמדה לא יסגור את התגית
    data = json.dumps(init, ensure_ascii=False).replace("</", "<\\/")
    with io.open(out, "w", encoding="utf-8") as fh:
        fh.write(html.replace(MARKER, data, 1))


def _run(args):
    r = subprocess.run([sys.executable, "-B", CLI] + args, capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def reply_for(batch, by_rule):
    """התשובה לתור, מהכרעות העמוד. None כשהמנה אינה מהסוג שהעמוד מכריע בו (החלטות הנהלה, שאלות)."""
    items = batch.get("items") or []
    if batch.get("stage") == "batch":
        out = [it["n"] for it in items if (by_rule.get(it["rule_id"]) or {}).get("decision") not in
               ("approved", "approved_after_legal_review")]
        if len(out) == len(items):
            return "לדלג על המנה"
        return "לאשר הכול" + (" חוץ מ-" + ", ".join(map(str, out)) if out else "")
    if batch.get("stage") == "topics":
        lines = []
        for it in items:
            d = (by_rule.get(it["rule_id"]) or {}).get("decision")
            if d in ("approved", "approved_after_legal_review"):
                legal = any(c.get("legal") for c in it.get("cells") or [])
                lines.append("%d %s" % (it["n"], "נבדק ולאשר" if legal else "לאשר"))
            elif d == "legal_review_later":
                lines.append("%d לעורך דין" % it["n"])   # נשמר כ"מחכה לעורך דין", לא כדילוג סתם
            else:
                lines.append("%d לדלג" % it["n"])
        return "\n".join(lines)
    return None


def apply(dec, model_path, core, index, records, word=None, workspace=None, local_copy_dir=None):
    """עובר על התור בשני שלבים בלבד, המנה הראשונה ואז הנושאים (--stage), כדי שהחלטות הנהלה ושאלות פתוחות שלפניהם
    בתור לא יעצרו את קליטת העמוד. הן נשארות בתור ומדווחות ב-others."""
    approver = dec.get("approver") or {}
    by_rule = {d.get("rule_id"): d for d in dec.get("decisions") or [] if d.get("rule_id")}
    log, failed = [], False
    for stage in ("batch", "topics"):
        for _ in range(MAX_ROUNDS):
            code, out = _run(["--queue", "--stage", stage, "--model", model_path, "--records", records])
            if code != 0:
                log.append(out.strip())
                failed = True
                break
            batch = IA.open_batch(IA.load_queue(records, _load(model_path)))
            if not batch or batch.get("stage") != stage:
                break
            reply = reply_for(batch, by_rule)
            if reply is None:
                break
            args = ["--answer", reply, "--approver", approver.get("name") or "", "--role", approver.get("role") or "",
                    "--model", model_path, "--records", records]
            for flag, val in (("--core", core), ("--index", index), ("--word", word), ("--workspace", workspace),
                              ("--local-copy-dir", local_copy_dir)):
                if val:
                    args += [flag, val]
            code, out = _run(args)
            log.append(out.strip())
            if code != 0:
                failed = True
                break
        if failed:
            break
    pending = [d for d in by_rule.values() if d.get("decision") not in ("approved", "approved_after_legal_review")]
    return {"log": log, "pending": pending, "failed": failed, "others": _others(model_path, records)}


def _others(model_path, records):
    """מה שנשאר בתור ושהעמוד אינו מכריע בו: {decisions: N, questions: N}."""
    model = _load(model_path)
    try:
        qs = IA.queue_state(model, _cells(model, model_path, records), "he", False, (), ())
    except Exception:  # noqa: BLE001  הדיווח הוא תוספת; כשל בו אינו מבטל קליטה שכבר נעשתה
        return {}
    return {k: len(qs.get(k) or []) for k in ("decisions", "questions") if qs.get(k)}


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--model", required=True)
    i.add_argument("--records")
    i.add_argument("--page", required=True)
    i.add_argument("--out", required=True)
    i.add_argument("--approver-name")
    i.add_argument("--approver-role")
    i.add_argument("--workspace-url")
    a = sub.add_parser("apply")
    a.add_argument("--decisions", required=True)
    a.add_argument("--model", required=True)
    a.add_argument("--core")
    a.add_argument("--index")
    a.add_argument("--records", required=True)
    a.add_argument("--word")
    a.add_argument("--workspace")
    a.add_argument("--local-copy-dir", help="כמו ב-ingest_approval.py: תיקיית הבסיס של העותק המקומי")
    args = ap.parse_args()
    if args.cmd == "init":
        model = _load(args.model)
        appr = {"name": args.approver_name, "role": args.approver_role} if args.approver_name else None
        init = build_init(model, args.model, args.records, appr, args.workspace_url)
        write_page(args.page, init, args.out)
        print(json.dumps({"positions": len(init["positions"]), "legal": sorted(init["legal"])}, ensure_ascii=False))
        return 0
    dec = _load(args.decisions)
    res = apply(dec, args.model, args.core, args.index, args.records, args.word, args.workspace, args.local_copy_dir)
    for ln in res["log"]:
        print(ln)
    oth = res["others"]
    if oth:
        print("\nנשארו בתור החלטות שהעמוד אינו מכריע בהן: %s. ממשיכים בהן ב\"אישור פלייבוק\" בשיחה." % ", ".join(
            "%d %s" % (n, {"decisions": "החלטות הנהלה", "questions": "שאלות פתוחות"}[k]) for k, n in oth.items()))
    if res["pending"]:
        print("\nנשארו פתוחים (לא אושרו בעמוד):")
        for d in res["pending"]:
            print("- %s: %s%s" % (d.get("rule_id"), d.get("decision"), (" · " + d["note"]) if d.get("note") else ""))
    return 3 if res["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
