# -*- coding: utf-8 -*-
"""שם עורך הדין שחותם על הבועות, מהמקום שבו הפרופיל באמת שומר אותו.

רכיב ההקמה כותב את השם ב-`branding.lawyer_name` (`storage-and-identity.md`,
"שם החותם על המסמכים היוצאים"). קוד הייחוס קורא `lawyer_name` בשורש הפרופיל
(`orchestrator/qa_gate.author_for`). בלי היישור הזה, על פרופיל אמיתי השער
נופל ב-KeyError, וכלי הסימון אינו מוצא את מי שחותם.

השדות מועתקים לשורש רק כשאינם שם כבר, כך שפרופיל שכבר כתוב בשורש אינו משתנה.
כשאין פרופיל בכלל (שינוי 45, "פלייבוק מוצע" בלי הקמה), השם נלקח מ-
`profile_gap.signer_name`.
"""
FIELDS = ("lawyer_name", "lawyer_name_en", "lawyer_initials", "lawyer_aliases", "lawyer_role")


def lawyer_view(profile):
    p = dict(profile or {})
    branding = p.get("branding") or {}
    for k in FIELDS:
        if not p.get(k) and branding.get(k):
            p[k] = branding[k]
    gap = p.get("profile_gap") or {}
    if not p.get("lawyer_name") and gap.get("signer_name"):
        p["lawyer_name"] = gap["signer_name"]
    return p
