# -*- coding: utf-8 -*-
"""common/approved_sources.py: בדיקת כתובת אחת מול רשימת המקורות המאושרים, מהדיסק, בלי לטעון את הרשימה להקשר.

הרשימה (מקורות-מאושרים.json) ארוכה, ונארזת בתוסף (lib/מקורות-מאושרים.json; אין הורדה מהשרת בזמן ריצה). המודל
אינו קורא אותה: הוא מבקש מהקוד את הרשומה של כתובת אחת. בלי --approved-sources ובלי AREO_APPROVED_SOURCES נקרא
העותק שבתוסף (risk.validate_register.sources_path). lookup מחזיר רק את הרשומה המתאימה, או שאין כזאת:

  status: approved            הכתובת מותרת; entry היא הרשומה היחידה שהתאימה (גוף, דומיין, נתיבים מותרים, דין)
          case_law_only       מדור פסיקה או אתר בית משפט: נדחה בכל מטרה (כלל 1.1), גם כשהדומיין מאושר
          pending             הגוף ברשימה אבל טרם אומת (pending_verification): אסור
          not_approved        מופיע ברשימת "לא מאושר למסקנה משפטית" (תקשורת ודומיהם): אסור
          not_on_list         אינו ברשימה כלל: אסור
          no_list             קובץ הרשימה לא נמצא או לא נקרא: אף מקור אינו מאושר

הכללים זהים ל-risk.validate_register.approved_domains ו-domain_ok (אותן פונקציות), ולכן מה שהסירוב הקיים
חוסם, הבדיקה הזאת מחזירה כלא-מאושר, ולהפך.

CLI:  python3 -B approved_sources.py --url <כתובת> [--approved-sources <מקורות-מאושרים.json>] [--purpose entity]
      קוד יציאה 0 כשמאושר, 1 כשאינו מאושר, 2 כשאין רשימה.
"""
import argparse
import json
import os
import sys
from urllib.parse import urlsplit

if __name__ == "__main__":             # הרצה ישירה (python -I): AREO_RT/lib לנתיב הייבוא, כמו areo_lib.py בסקריפטים
    _lib = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if _lib not in sys.path:
        sys.path.insert(0, _lib)

from common.case_law import case_law_url  # noqa: E402
from common.net import url_allowed
from risk import validate_register as VR

REFUSED = ("case_law_only", "pending", "not_approved", "not_on_list", "no_list")


def _host(url):
    try:
        h = (urlsplit(url or "").hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return h[4:] if h.startswith("www.") else h


def _host_in(host, dom):
    dom = VR._norm_dom(dom).partition("/")[0]
    return bool(dom) and (host == dom or host.endswith("." + dom))


def _entry(src, jur, kind):
    """הרשומה המוחזרת: רק מה שצריך כדי לדעת מה מותר, בלי שאר הרשימה."""
    out = {"kind": kind, "jurisdiction": jur.get("jurisdiction_en") or jur.get("jurisdiction_he") or ""}
    for k in ("body", "domain", "status", "include_subdomains", "allowed_paths", "include_hosts",
              "restriction_kind", "note_en", "title", "url", "topic_he"):
        if src.get(k) not in (None, "", []):
            out[k] = src[k]
    return out


def lookup(url, path=None, purpose=None):
    """dict עם status (ראה למעלה), host, ו-entry (רק כשיש רשומה מתאימה). לעולם אינו מחזיר את הרשימה."""
    host = _host(url)
    res = {"url": url, "host": host}
    data, used = VR._load_sources_file(path)
    if not data:
        res.update(status="no_list", reason="רשימת המקורות המאושרים (מקורות-מאושרים.json) לא נמצאה או לא נקראה. "
                                            "אף מקור אינו מאושר בלעדיה.")
        return res
    if not host:
        res.update(status="not_on_list", reason="אין כתובת תקינה")
        return res
    why = case_law_url(url)
    rules = VR.approved_domains(path, purpose)[0]
    refuse = tuple(getattr(rules, "refuse", ()))
    if why or url_allowed(url, refuse) and not url_allowed(url, tuple(r for r in refuse if not r.startswith("!"))):
        pass
    if why or any(url_allowed(url, (r.lstrip("!"),)) for r in refuse):
        res.update(status="case_law_only", reason=why or "מסומן ברשימה כמדור פסיקה (case_law_only): פסיקה רק ממחבר "
                                                          "פסיקה סגור של הלקוח (כלל 1.1)")
        return res
    blocks = [("source", data.get("jurisdictions") or [])]
    if purpose == VR.ENTITY_PURPOSE:
        blocks.append(("entity_check", (data.get("entity_check") or {}).get("jurisdictions") or []))
    pending = None
    for kind, jurs in blocks:
        for jur in jurs:
            for src in jur.get("sources") or []:
                if not isinstance(src, dict):
                    continue
                r = VR._src_rules(src)
                if r and url_allowed(url, VR._rules_obj(r, ())):
                    res.update(status="approved", entry=_entry(src, jur, kind))
                    return res
                if pending is None and src.get("status") != "approved" and _host_in(host, src.get("domain")):
                    pending = _entry(src, jur, kind)
            if kind == "source":
                for pg in jur.get("pages") or []:
                    r = VR._page_rule(pg) if isinstance(pg, dict) else None
                    if r and url_allowed(url, (r,)):
                        res.update(status="approved", entry=_entry(pg, jur, "page"))
                        return res
    if pending:
        res.update(status="pending", entry=pending, reason="הגוף ברשימה אך טרם אומת ואושר: אסור עד אישור")
        return res
    for na in data.get("not_approved_for_legal_conclusions") or []:
        u = na.get("url") if isinstance(na, dict) else na
        if _host(u) and (_host(u) == host or host.endswith("." + _host(u))):
            res.update(status="not_approved", entry={"kind": "not_approved", "title": (na.get("title") if isinstance(na, dict) else "")},
                       reason="ברשימת המקורות שאינם מאושרים למסקנה משפטית")
            return res
    res.update(status="not_on_list", reason="אינו ברשימת המקורות המאושרים, בדומיין, בתת-דומיין או בנתיב: %s" % host)
    return res


def main(argv=None):
    sys.dont_write_bytecode = True
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="בדיקת כתובת אחת מול רשימת המקורות המאושרים, מהדיסק")
    ap.add_argument("--url", required=True)
    ap.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק "
                                               "שבתוסף, lib/מקורות-מאושרים.json)")
    ap.add_argument("--purpose", choices=("entity",), help="entity: בדיקת רקע על הצד שכנגד (מעריך הסיכונים בלבד)")
    a = ap.parse_args(argv)
    res = lookup(a.url, a.approved_sources, a.purpose)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["status"] == "approved" else (2 if res["status"] == "no_list" else 1)


if __name__ == "__main__":
    sys.exit(main())
