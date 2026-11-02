# -*- coding: utf-8 -*-
"""voice_scrub.py: מזהים פנימיים (R19, S07, S02#p12) אינם מגיעים ללקוח, בשום משטח שהבונה כותב לו.

הכלל (areo-voice.md): בלי קודים. המזהים נשארים במודל ובקבצי הנתונים, כי בהם הקוד מצמיד עמדה למקור. כל משטח שהלקוח
קורא (כותרות ה-Word, גיליון האישור, נתוני סביבת העבודה) מעביר את הטקסט כאן לפני הכתיבה: מזהה של נושא מוחלף בשם
הנושא, מזהה של מקור בשם המסמך, ומזהה שאין לו מקבילה בנוסח כללי ("נושא אחר בפלייבוק"). נוסח שהמודל כתב ושהקוד
אינו מזהה כמזהה אינו משתנה. כללי לכל סוג הסכם ולשתי השפות.

    import voice_scrub
    sc = voice_scrub.Scrubber(model, lang="he")
    sc.text("ראו גם (R21) ו-S02#p12")  ->  'ראו גם ("ביקורת...") ו-<שם המסמך>'
"""
import os
import re

RULE_RE = re.compile(r"(?<![\w/\.#])R(\d{1,3})(?![\w-])")
SRC_RE = re.compile(r"(?<![\w/\.#])S(\d{2,3})(?:#[A-Za-z]{0,2}\d+)?(?![\w-])")
CITE_RE = re.compile(r"(?<![\w/\.#])C\d{4}(?![\w-])")
GENERIC = {"he": ("נושא אחר בפלייבוק", "אחד המסמכים"), "en": ("another topic in the playbook", "one of the documents")}


def _short_name(f):
    stem = os.path.splitext(os.path.basename(str(f or "").replace(chr(92), "/")))[0]
    return re.sub(r"^\s*\d+\s*[-.)]*\s*", "", stem).strip() or stem


class Scrubber:
    def __init__(self, model, lang="he"):
        self.lang = "en" if str(lang or "").lower().startswith("en") else "he"
        model = model if isinstance(model, dict) else {}
        self.rules = {}
        for r in model.get("rules") or []:
            if isinstance(r, dict) and r.get("rule_id"):
                name = r.get("topic_name") or r.get("topic") or r.get("clause_issue") or ""
                self.rules[str(r["rule_id"])] = str(name).strip()
        self.sources = {}
        for r in model.get("source_log") or []:
            if isinstance(r, dict) and r.get("source_id"):
                self.sources[str(r["source_id"])] = _short_name(r.get("file"))

    def _rule(self, m):
        name = self.rules.get("R" + m.group(1)) or self.rules.get("R%02d" % int(m.group(1)))
        return '"%s"' % name if name else GENERIC[self.lang][0]

    def _src(self, m):
        name = self.sources.get("S" + m.group(1)) or self.sources.get("S%02d" % int(m.group(1)))
        return name or GENERIC[self.lang][1]

    def text(self, value):
        """הטקסט בלי מזהים פנימיים. מחרוזת בלבד; כל ערך אחר חוזר כמות שהוא."""
        if not isinstance(value, str) or not value:
            return value
        t = RULE_RE.sub(self._rule, value)
        t = SRC_RE.sub(self._src, t)
        t = CITE_RE.sub("", t)
        t = re.sub(r"\(\s*[,;]?\s*\)", "", t)
        return re.sub(r"[ \t]{2,}", " ", t).strip() if t != value else value

    def deep(self, obj, skip_keys=()):
        """אותו ניקוי על כל המחרוזות בעץ (dict, list), פרט למפתחות שנשארים מזהים (skip_keys)."""
        if isinstance(obj, dict):
            return {k: (v if k in skip_keys else self.deep(v, skip_keys)) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.deep(x, skip_keys) for x in obj]
        return self.text(obj) if isinstance(obj, str) else obj
