"""קיבוץ מסמכים לעסקה אחת, ושיוך תיקונים, נספחים והזמנות להסכם המסגרת.

מפתח הקיבוץ: צד שכנגד מנורמל, נושא מנורמל מתוך שם הקובץ, ותיקייה. כשיש ספק
אין מקבצים בשקט: שני הסכמים חתומים באותו נושא נשארים נפרדים ועוברים לבדיקה,
ומסמך משנה שלא נמצא לו הסכם מסגרת יחיד נקלט כהסכם עצמאי ומסומן יתום.
"""
import re

from clm.i18n import t as tr

VERSIONABLE = {"signed", "draft", "negotiation_version"}
CHILD = {"amendment", "schedule", "order"}
CO_SUFFIX = re.compile(r"(בע\"?מ|בעמ|\bltd\b\.?|\blimited\b|\binc\b\.?|\bllc\b|\bgmbh\b)", re.I)
NOISE = re.compile(r"\b(redline|edits|tgrnedits|tracked|final|clean|v\d+)\b", re.I)
HEB_NOISE = re.compile(r"(עקוב אחר שינויים|טיוטה נגדית|טיוטה|נוסח סופי|נקי|מלא\d*|רגיש)")


def basename(path):
    return re.sub(r"\.(docx|pdf|doc|txt|md|eml)$", "", path.split("/")[-1], flags=re.I)


def folder(path):
    return path.rsplit("/", 1)[0] if "/" in path else ""


def norm_cp(name):
    n = (name or "").replace("״", '"').replace("׳", "'")
    n = CO_SUFFIX.sub(" ", n)
    n = re.sub(r"[^\w\s]", " ", n)
    return re.sub(r"\s+", " ", n).strip().lower()


def topic_key(path):
    n = basename(path)
    n = re.sub(r"\(.*?\)|\[.*?\]", " ", n)
    n = re.sub(r"\d{1,2}[.\-]\d{1,2}[.\-]\d{2,4}", " ", n)
    n = n.replace("_", " ")
    n = re.split(r"\s+-\s+|,\s*", n)[0]
    n = NOISE.sub(" ", n)
    n = HEB_NOISE.sub(" ", n)
    return re.sub(r"\s+", " ", n).strip().lower()


def _key(d):
    return norm_cp(d["counterparty"]), topic_key(d["file"]), folder(d["file"])


def _by_date(d):
    return d["date"] or "0000"


def _hint(d):
    return re.sub(r"\s+", " ", (d.get("relation") or {}).get("parent_hint") or "").strip().lower()


HINT_FILLER = {"הסכם", "ההסכם", "חוזה", "מיום", "בין", "לבין", "ובין", "מתאריך", "תאריך", "תיקון", "התיקון", "נספח",
               "בע", "בעמ", "agreement", "contract", "nda", "cda", "amendment", "addendum", "to", "the", "of", "and",
               "dated", "between", "no", "number", "first", "second", "third"}
NAME_STOP = {"חברת", "קבוצת", "the", "company"}
DATE_IN_HINT = re.compile(r"(?<![\d.])(\d{1,2})[./](\d{1,2})[./](\d{4})(?![\d])")
PREFIXES = "ולהבמש"


def _date_tuple(iso):
    m = re.match(r"(\d{4})-(\d{1,2})-(\d{1,2})$", iso or "")
    return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else None


def _parent_dates(parent):
    """תאריך החתימה ותאריך התחילה של ההורה."""
    signed = parent.get("signed_date") or (parent.get("date") if parent.get("doc_kind") == "signed" else None)
    return {t for t in (_date_tuple(signed), _date_tuple(parent.get("start_date"))) if t}


def _variants(t):
    return {t, t[1:]} if len(t) > 2 and t[0] in PREFIXES else {t}


def _words(text):
    """מילים (רצפי אותיות וספרות) באותיות קטנות; גרשיים עבריים כמו מירכאות, ולכן "בע״מ" ו-'בע"מ' זהים."""
    return re.findall(r"\w+", (text or "").replace("״", '"').replace("׳", "'").lower())


def _filler(t):
    return bool(_variants(t) & HINT_FILLER)


def _phrase_at(phrase, words, i):
    """הצירוף מופיע במילים החל ממקום i; כל מילה בהינט רשאית לשאת אות שימוש אחת (ו/ה/ב/ל/מ/ש) בראשה."""
    return i + len(phrase) <= len(words) and all(w in _variants(words[i + j]) for j, w in enumerate(phrase))


def _has_phrase(phrase, words):
    return bool(phrase) and any(_phrase_at(phrase, words, i) for i in range(len(words)))


def _name_phrases(name):
    """[השם המלא, המילה הראשונה המובחנת] כרשימות מילים. השם המלא: בלי סיומת חברה (בע"מ, Ltd).
    המילה הראשונה המובחנת: המילה הראשונה בשם שאינה מילת קישור ואינה ב-NAME_STOP ("חברת", "the" וכו'),
    למשל "מדיקס", "דאטה-הר". שאר המילים בשם אינן רעש."""
    words = [_words(norm_cp(w)) for w in (name or "").split()]
    first = next((ph for ph in words if ph and not all(_filler(t) or t in NAME_STOP for t in ph)), [])
    return [ph for ph in (_words(norm_cp(name)), first) if ph]


def _name_noise(*names):
    """צירופי השמות כזוגות (סוג, מילים): "full" לשם המלא, "first" למילה הראשונה המובחנת."""
    return [(kind, ph) for nm in names for kind, ph in zip(("full", "first"), _name_phrases(nm))]


def _strip(words, names):
    """מסיר מהמילים כל מופע של צירוף שם (השמות המלאים קודם). מחזיר (המילים שנשארו, סוגי ההסרות)."""
    rest, kinds = list(words), []
    for kind, ph in sorted(names, key=lambda x: x[0] != "full"):
        i = 0
        while i < len(rest):
            if _phrase_at(ph, rest, i):
                del rest[i:i + len(ph)]
                kinds.append(kind)
            else:
                i += 1
    return rest, kinds


def _content_of(words):
    return [t for t in words if len(t) >= 2 and not t.isdigit() and not _filler(t)]


def _topic_content(tk, names=()):
    """אסימוני התוכן של נושא ההורה: מילות topic_key בלי צירופי השמות (כלל 1) ובלי מילות קישור ושמות עצם
    כלליים ("הסכם", "חוזה", "agreement"; כלל 2)."""
    return _content_of(_strip(_words(tk), names)[0])


def _hint_info(child, company, hint=None):
    """מחושב פעם אחת לכל מסמך משנה: תאריכי ההינט, צירופי השמות, ההינט בלי השמות ואסימוני התוכן שלו.
    תאריכי ההינט: כל התאריכים בו פרט לתאריך החתימה של התיקון עצמו (תיקון שנחתם באותו יום כמו המסגרת
    מאבד את התאריך הזה, ולכן הינט של תאריך בלבד מסמן יתום, הכישלון הבטוח).
    צירופי השמות: לחברה ולצד שכנגד, השם המלא והמילה הראשונה המובחנת (_name_phrases); כל מילה בהינט
    רשאית לשאת אות שימוש אחת. אסימוני תוכן: מילים באורך 2 ומעלה שאינן ספרות ואינן מילות קישור."""
    hint = _hint(child) if hint is None else hint
    own = _date_tuple(child.get("signed_date"))
    names = _name_noise(company, child.get("counterparty"))
    rest, kinds = _strip(_words(DATE_IN_HINT.sub(" ", hint)), names)
    return {"dates": {(int(d), int(m), int(y)) for d, m, y in DATE_IN_HINT.findall(hint)} - {own},
            "names": names, "rest": rest, "stripped": kinds, "content": _content_of(rest)}


def _rank(parent, info):
    """-1 סתירה, 0 אין התאמה, 1 התאמת תאריך בלבד, 2 התאמת נושא. info: _hint_info של מסמך המשנה.

    כלל אחד: יתום הוא הכישלון הבטוח, שיוך שגוי הוא המסוכן. בספק מסמן יתום.
    תאריכי ההורה: חתימה ותחילה. נושא ההורה: מילות topic_key בלי צירופי השמות; אסימוני התוכן שלו:
    בלי מילות קישור ושמות עצם כלליים. כל ההשוואות נעשות מול ההינט בלי השמות, לא מול ההינט הגולמי.
    1. סתירה: יש תאריכים בהינט ואף אחד אינו תאריך של ההורה. חל על כל סוגי ההתאמה.
       תאריך נוסף שאינו של ההורה (תיקון קודם) אינו סותר כשתאריך של ההורה מופיע.
    2. התאמת נושא:
       - בנושא אין אסימון תוכן (רק שם הצד שכנגד, "הסכם", "חוזה"): אין התאמת נושא.
       - אסימון תוכן אחד: הנושא מופיע בהינט כצירוף מילים, ובהינט אין אסימון תוכן אחר.
       - שניים ומעלה: הנושא מופיע כצירוף, או 80% מאסימוני התוכן שלו ומעלה באסימוני התוכן של ההינט.
       בצירוף, כל מילה בהינט רשאית לשאת אות שימוש אחת (ו/ה/ב/ל/מ/ש).
    3. התאמת תאריך בלבד: תאריך של ההורה בהינט, ולהינט לא נשאר אף אסימון תוכן, ולא רק משום שהוסרה ממנו
       מילה ראשונה יחידה של שם (כמו "הסכם אירוח" מול צד שכנגד "אירוח ענן"). שם מלא, או שני השמות, מספיקים."""
    match_dates = info["dates"] & _parent_dates(parent)
    if info["dates"] and not match_dates:
        return -1
    have = set().union(*[_variants(t) for t in info["content"]])
    # נושא ההורה: מנושא שם הקובץ, מכותרת ההסכם ומשם הקובץ המלא. שם קובץ כמו "Datadog - Master Subscription
    # Agreement" מצטמצם בנושא לשם הספק, והכותרת שומרת את "Master Subscription"
    for source in (topic_key(parent["file"]), parent.get("title") or "", basename(parent["file"])):
        topic = _strip(_words(source), info["names"])[0]
        want = _content_of(topic)
        phrase = _has_phrase(topic, info["rest"])
        if len(want) == 1 and phrase and all(want[0] in _variants(t) for t in info["content"]):
            return 2
        if len(want) >= 2 and (phrase or sum(1 for t in want if t in have) >= 0.8 * len(want)):
            return 2
    if match_dates and not info["content"] and info["stripped"] != ["first"]:
        return 1
    return 0


def _coverage(parent, info):
    """שובר שוויון בין כמה הורים בהתאמת נושא: החלק הגדול ביותר מאסימוני הנושא של ההורה שמופיע בהפניה, ואחריו
    מספר אסימוני ההפניה שההורה מכסה. "מבנה משטרה" מכסה את ההפניה במלואה, "מבנה בפסגות" רק ב-80%."""
    have = set().union(*[_variants(t) for t in info["content"]])
    best = (0.0, 0)
    for source in (topic_key(parent["file"]), parent.get("title") or "", basename(parent["file"])):
        want = _content_of(_strip(_words(source), info["names"])[0])
        if not want:
            continue
        mine = set().union(*[_variants(t) for t in want])
        back = sum(1 for t in info["content"] if _variants(t) & mine)
        best = max(best, (sum(1 for t in want if t in have) / len(want), back))
    return best


def _best_strong(idxs, frameworks, by_id, info):
    """מבין מועמדים בהתאמת נושא: היחיד, או זה שהכיסוי שלו גבוה בבירור מכל האחרים. אחרת None (בספק, יתום)."""
    if len(idxs) == 1:
        return idxs[0]
    cov = sorted(((_coverage(by_id[frameworks[i]["head_id"]], info), i) for i in idxs), reverse=True)
    return cov[0][1] if cov and cov[0][0] > cov[1][0] else None


def _template_matches(t, buckets):
    tk, fo, tcp = topic_key(t["file"]), folder(t["file"]), norm_cp(t["counterparty"])
    return [k for k, members in buckets.items()
            if k[1] == tk and k[2] == fo and (not tcp or tcp == k[0])
            and any(m["doc_kind"] == "negotiation_version" for m in members)]


def _parent_for(child, frameworks, by_id, company=""):
    """הורה יחיד: מסגרת של אותו צד שכנגד. בלי הינט: רק כשיש מסגרת אחת. עם הינט: הדירוג הטוב ביותר
    (התאמת נושא עדיפה על התאמת תאריך בלבד), ורק כשיש מועמד יחיד בדירוג הזה."""
    cp = norm_cp(child["counterparty"])
    hint = _hint(child)
    head_cp = [norm_cp(by_id[gr["head_id"]]["counterparty"]) for gr in frameworks]
    cands = [i for i, c in enumerate(head_cp) if cp and c == cp]
    # צד שכנגד שלא נקרא (בתיקון או במסגרת): מועמד רק בהתאמת נושא מלאה (דירוג 2), ורק כשהוא יחיד
    loose = [i for i, c in enumerate(head_cp) if i not in cands and (not cp or not c)]
    if not hint and len(cands) == 1:
        return cands[0]
    if not hint:
        # כמה מסגרות, או צד שכנגד שלא נקרא, ובלי הפניה: הכותרת של מסמך המשנה משמשת כהפניה
        hint = re.sub(r"\s+", " ", child.get("title") or "").strip().lower()
        if not hint:
            return None
    info = _hint_info(child, company) if hint == _hint(child) else _hint_info(child, company, hint)
    ranks = {i: _rank(by_id[frameworks[i]["head_id"]], info) for i in cands}
    best = max(ranks.values(), default=0)
    winners = [i for i, r in ranks.items() if r == best]
    if best > 0 and len(winners) == 1:
        return winners[0]
    if best == 2:
        return _best_strong(winners, frameworks, by_id, info)
    if best <= 0 and loose:
        strong = [i for i in loose if _rank(by_id[frameworks[i]["head_id"]], info) == 2]
        return _best_strong(strong, frameworks, by_id, info) if strong else None
    return None


def group(docs, company=""):
    review, groups, buckets = [], [], {}
    by_id = {d["id"]: d for d in docs}
    for d in docs:
        if d["doc_kind"] in VERSIONABLE:
            buckets.setdefault(_key(d), []).append(d)
    for t in docs:
        if t["doc_kind"] != "template":
            continue
        matches = _template_matches(t, buckets)
        if len(matches) == 1:
            t["base_version"] = True
            buckets[matches[0]].insert(0, t)
        elif len(matches) > 1:
            review.append({"kind": "ambiguous_template", "group": tr("קיבוץ לבדיקה", "Grouping to check"),
                           "text": tr("תבנית בסיס %s תואמת כמה עסקאות. לא צורפה",
                                      "The base template %s matches several deals, so it was not attached") % basename(t["file"])})
    for k, members in buckets.items():
        signed = [m for m in members if m["doc_kind"] == "signed"]
        if len(signed) > 1:
            for s in signed:
                groups.append({"doc_ids": [s["id"]], "head_id": s["id"]})
            review.append({"kind": "ambiguous_group", "group": tr("קיבוץ לבדיקה", "Grouping to check"),
                           "text": tr("%d הסכמים חתומים באותו נושא מול אותו צד (%s). לא קובצו",
                                      "%d signed agreements on the same subject with the same party (%s). "
                                      "They were kept apart") % (len(signed), k[1])})
            rest = sorted([m for m in members if m["doc_kind"] != "signed"], key=_by_date)
            if rest:
                groups.append({"doc_ids": [m["id"] for m in rest], "head_id": rest[-1]["id"]})
            continue
        base = [m for m in members if m.get("base_version")]
        others = sorted([m for m in members if not m.get("base_version")], key=_by_date)
        ordered = base + others
        head = signed[0] if signed else ordered[-1]
        groups.append({"doc_ids": [m["id"] for m in ordered], "head_id": head["id"]})
    frameworks = list(groups)
    children = {}
    # נספחים והזמנות קודם, ואחריהם תיקונים: תיקון לנספח שאין לו מסגרת בתיקייה (למשל תיקון לנספח של מכרז)
    # משויך לנספח עצמו
    kids = sorted((d for d in docs if d["doc_kind"] in CHILD), key=lambda d: d["doc_kind"] == "amendment")
    for d in kids:
        parent = _parent_for(d, frameworks, by_id, company)
        if parent is None and d["doc_kind"] == "amendment" and len(groups) > len(frameworks):
            extra = list(range(len(frameworks), len(groups)))
            sub = _parent_for(d, [groups[gi] for gi in extra], by_id, company)
            parent = extra[sub] if sub is not None else None
        if parent is not None:
            children[d["id"]] = parent
        else:
            groups.append({"doc_ids": [d["id"]], "head_id": d["id"]})
            review.append({"kind": "orphan", "group": tr("מסמך יתום", "Unlinked document"),
                           "text": tr("לא נמצא הסכם מסגרת יחיד עבור %s. נקלט כהסכם עצמאי עד לשיוך",
                                      "No single framework agreement was found for %s. It was added as a separate "
                                      "agreement until it is linked") % basename(d["file"])})
    return {"groups": groups, "children": children, "review": review}
