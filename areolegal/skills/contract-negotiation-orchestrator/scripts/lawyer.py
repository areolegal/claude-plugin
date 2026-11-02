# -*- coding: utf-8 -*-
"""שם עורך הדין שחותם על הבועות, מהמקום שבו הפרופיל באמת שומר אותו.

רכיב ההקמה כותב את השם ב-`branding.lawyer_name` (`storage-and-identity.md`,
"שם החותם על המסמכים היוצאים"). קוד הייחוס קורא `lawyer_name` בשורש הפרופיל
(`orchestrator/qa_gate.author_for`). בלי היישור הזה, על פרופיל אמיתי השער
נופל ב-KeyError, וכלי הסימון אינו מוצא את מי שחותם.

השדות מועתקים לשורש רק כשאינם שם כבר, כך שפרופיל שכבר כתוב בשורש אינו משתנה.
כשאין פרופיל בכלל (שינוי 45, "פלייבוק מוצע" בלי הקמה), השם נלקח מ-
`profile_gap.signer_name`.

פרופיל שנבנה לפני שההקמה פיצלה את החותם (באג 9, הרצה S1b, 28.10.2026) שומר
ב-`lawyer_name` את כל התשובה, למשל "עו"ד מיכל לוי, יועצת משפטית (Michal Levi,
General Counsel)". השם מפוצל כאן כמו ב-build_profile.split_signer: השם בלי תואר
ובלי תפקיד, והשם שבסוגריים ל-`lawyer_name_en`. הנוסח המקורי נשמר ב-
`lawyer_aliases`, כדי שסימונים קודמים בשמו עדיין יזוהו כשלנו.
"""
import re

FIELDS = ("lawyer_name", "lawyer_name_en", "lawyer_initials", "lawyer_aliases", "lawyer_role", "lawyer_role_en")
COUNSEL_TITLE_RE = re.compile(r'^\s*(?:עו(?:"|״|\x27\x27|”)ד|עוה(?:"|״)ד|עורך הדין|עורכת הדין|Adv\.?|Advocate)\s+',
                              re.I)
HEB = re.compile("[֐-׿]")


def split_signer(raw):
    """(שם, תפקיד, שם באנגלית, תפקיד באנגלית), כמו build_profile.split_signer."""
    raw = (raw or "").strip()
    name_en = role_en = None
    m = re.search(r"\(([^()]*)\)\s*$", raw)
    if m and re.search(r"[A-Za-z]", m.group(1)):
        en = [x.strip() for x in m.group(1).split(",", 1)]
        name_en = COUNSEL_TITLE_RE.sub("", en[0]).strip() or None
        role_en = en[1] if len(en) > 1 and en[1] else None
        raw = raw[:m.start()].strip()
    parts = [x.strip() for x in raw.split(",", 1)]
    name = COUNSEL_TITLE_RE.sub("", parts[0]).strip() or None
    return name, (parts[1] if len(parts) > 1 and parts[1] else None), name_en, role_en


def lawyer_view(profile):
    p = dict(profile or {})
    branding = p.get("branding") or {}
    for k in FIELDS:
        if not p.get(k) and branding.get(k):
            p[k] = branding[k]
    gap = p.get("profile_gap") or {}
    if not p.get("lawyer_name") and gap.get("signer_name"):
        p["lawyer_name"] = gap["signer_name"]
    raw = p.get("lawyer_name")
    if raw:
        name, role, name_en, role_en = split_signer(raw)
        if name and name != raw:
            p["lawyer_name"] = name
            p["lawyer_aliases"] = list(p.get("lawyer_aliases") or []) + [raw]
            for k, v in (("lawyer_role", role), ("lawyer_name_en", name_en), ("lawyer_role_en", role_en)):
                if v and not p.get(k):
                    p[k] = v
        if not p.get("lawyer_name_en") and not HEB.search(p["lawyer_name"]):
            p["lawyer_name_en"] = p["lawyer_name"]   # שם בלי אותיות עבריות משמש גם בנייר באנגלית
    return p


def needs_english_name(profile, lang):
    """בהסכם באנגלית הבועות נחתמות בשם האנגלי. אין שם כזה: שואלים שאלה אחת, ולא חותמים בשם העברי."""
    return lang == "en" and bool(profile.get("lawyer_name")) and not profile.get("lawyer_name_en")
