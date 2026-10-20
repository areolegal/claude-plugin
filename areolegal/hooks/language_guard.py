#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שומר השפה: הודעה אחרונה באנגלית בשיחה עברית של Areo נכתבת מחדש בעברית.

בהרצה חיה (20.10.2026) כל הודעת הסיכום של הנושא ונותן ללקוח יצאה באנגלית, גם כשהכלל היה
בראש כל SKILL.md וגם בהוראות שרת ה-MCP. ה-hook הזה רץ כש-Claude מסיים תור (Stop):

* רק בשיחה שהופעל בה רכיב של Areo (בתמליל מופיע areolegal), ושהמשתמש כתב בה בעברית.
* כשרוב האותיות בהודעה האחרונה לטיניות (בלי קוד, כתובות ושמות קבצים), התור אינו מסתיים:
  Claude מקבל הוראה לכתוב את אותה הודעה בעברית, בלי לשנות את התוכן.
* פעם אחת בלבד לכל תור (stop_hook_active), כדי שלא תהיה לולאה.

תקלה בבדיקה עצמה אינה עוצרת את התור.
"""
import json
import re
import sys

HEB = re.compile(r"[֐-׿]")
LAT = re.compile(r"[A-Za-z]")
NOISE = re.compile(r"```.*?```|`[^`]*`|https?://\S+|\[[^\]]*\]\([^)]*\)|\S+\.(?:docx|html|json|md|py|pdf)\b", re.S)


def letters(text):
    t = NOISE.sub(" ", text or "")
    return len(HEB.findall(t)), len(LAT.findall(t))


def messages(path):
    users, last = [], ""
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            msg = d.get("message") if isinstance(d.get("message"), dict) else {}
            content = msg.get("content")
            if d.get("type") == "user":
                if isinstance(content, str):
                    users.append(content)
                elif isinstance(content, list):
                    users += [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
            elif d.get("type") == "assistant" and isinstance(content, list):
                texts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
                if any(t.strip() for t in texts):
                    last = "\n".join(texts)
    return users, last


def main():
    try:
        event = json.load(sys.stdin)
        if event.get("stop_hook_active"):
            return 0
        path = event.get("transcript_path") or ""
        with open(path, encoding="utf-8") as fh:
            if "areolegal" not in fh.read():
                return 0
        users, last = messages(path)
        uh, ul = letters(" ".join(users))
        if uh <= ul:                       # המשתמש אינו כותב בעברית
            return 0
        h, l = letters(last)
        if l < 80 or l <= 2 * h:           # הודעה קצרה, או שרובה עברית
            return 0
    except Exception:  # noqa: BLE001  תקלה בבדיקה אינה עוצרת את התור
        return 0
    print(json.dumps({"decision": "block", "reason": (
        "ההודעה האחרונה ללקוח נכתבה באנגלית, והשיחה בעברית. כתוב את אותה הודעה מחדש בעברית מלאה, "
        "בלי לשנות את התוכן, את המספרים ואת שמות הקבצים, ובלי להוסיף הסבר על השינוי. "
        "The last message to the client is in English; rewrite the same message in Hebrew.")},
        ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
