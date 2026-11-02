"""טעינת הקטלוג: סוגי מועדים, סוגי הסכמים וסעיפי מפתח.

הקטלוג הוא נתונים ולא קוד. סוג הסכם חדש נוסף כקובץ ב-catalog/types,
ואין לשנות לשם כך שום שורת קוד.

שפה: catalog/en.json מחזיק את התאומים באנגלית (תווית, פעולה והשלכת אי-פעולה של מועד; תווית סעיף מפתח; תווית
סוג ותוויות השדות הייעודיים). בשפה en הם מחליפים את הערכים העבריים, באותם מפתחות. ערך שאין לו תאום נשאר בעברית.
בלי lang, השפה היא שפת ההרכבה הנוכחית (i18n), ומחוץ להרכבה עברית.
"""
import copy
import json
import os

from clm import i18n

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES = ["מועד", "זכות שפוקעת", "כסף", "בטוחה", "התחייבות מתמשכת", "תנאי מתלה או מפסיק"]
CONSEQUENCES = {"right_lapses", "auto_change", "we_breach", "opportunity", "they_breach_monitor"}


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return json.load(f)


def _en(section, lang):
    """התאומים באנגלית של חלק בקטלוג, או None בעברית."""
    if i18n.norm(lang if lang is not None else i18n.lang()) != "en":
        return None
    path = os.path.join(ROOT, "catalog", "en.json")
    return (_read("catalog", "en.json").get(section) or {}) if os.path.exists(path) else {}


def load_events(lang=None):
    ev, en = _read("catalog", "events.json"), _en("events", lang)
    if en:
        for code, row in ev.items():
            row.update({k: v for k, v in (en.get(code) or {}).items() if k in ("label", "action", "if_nothing") and v})
    return ev


def load_key_clauses(lang=None):
    kc, en = _read("catalog", "key_clauses.json"), _en("key_clauses", lang)
    if en:
        kc = {code: en.get(code) or label for code, label in kc.items()}
    return kc


def load_types(lang=None):
    folder = os.path.join(ROOT, "catalog", "types")
    en = _en("types", lang)
    out = {}
    for name in sorted(os.listdir(folder)):
        if name.endswith(".json"):
            t = _read("catalog", "types", name)
            tw = (en or {}).get(t["type_code"]) or {}
            if tw:
                t = copy.deepcopy(t)
                t["label"] = tw.get("label") or t["label"]
                for f in t.get("type_fields", []):
                    f["label"] = (tw.get("type_fields") or {}).get(f["key"]) or f["label"]
            out[t["type_code"]] = t
    return out
