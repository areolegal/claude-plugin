# -*- coding: utf-8 -*-
"""playbook/validate_model.py: בדיקות תוכן כלליות על playbook-model.json ועל הגרעין, לכל סוג הסכם.

המאמת כללי (החלטה 22, כלל נוקשה 2.26): הוא בודק מנגנונים שחלים בכל פלייבוק, ואינו מכיל שיקול משפטי של
סוג הסכם מסוים (נושאים, כיוון של סעיף, דין ושיפוט, סוג מקור של עסקה מסוימת). שיקול כזה שייך לפלייבוק של
הלקוח, כנתון שהפלייבוק נושא.

הבעיה (סבב 3, הערות 5.5):
- נוסח ירוק שהיועצת חתמה עליו נפסל אחר כך בבדיקות שהנושא ונותן מריץ על כל נוסח שהוא מכניס. עכשיו כל נוסח
  ירוק, צהוב ונסיגה עובר את אותן בדיקות (common.gap_checks.check_wording), לפני שהגיליון מופק (שינוי 80).
- שתי תוויות באותה רשומה (presentation_label ו-status_label), ושדות מאשר והסלמה במודל, בניגוד להחלטה
  המחייבת שאין שרשרת אישורים (שינויים 79, 76).
- "10 הסכמים מ-10 גופים" כשנספרו 6 (שינוי 82).
- שורת ההשפעה הייתה קשורה לשני תפקידים קבועים; עכשיו לכל תפקיד שיש לחברה בהסכם (שינוי 84).

validate(model, core=None, index_entry=None) מחזיר רשימת ממצאים {code, severity: error|warning, rule_id,
track, message}. error = חוסם מסירה. הקודים:
- WALKAWAY_ALL, WALKAWAY_NOT_CRITICAL, WALKAWAY_TOO_MANY (אזהרה), WALKAWAY_NO_SOURCE (שובר עסקה בלי
  walk_away_source: statute | client_answer | company_document).
- HOLD_GREEN_ALL, HOLD_GREEN_LOW.
- YELLOW_EQUALS_GREEN, FALLBACK_EQUALS_GREEN, YELLOW_WORSENS_MAIN_ROLE (מסלול שסומן protects_main_role=false).
- ROLE_EFFECT_MISSING: חסרה שורת השפעה לאחד התפקידים שיש לחברה בהסכם (approval_sheet.company_roles).
- WORDING_GAP: נוסח ירוק, צהוב או נסיגה שנכשל בבדיקות הפערים המשותפות. GAP_CHECKS_UNAVAILABLE: המודול חסר.
- LABEL_DUAL_FIELD: presentation_label נשמר במקום כלשהו. LABEL_MISMATCH: status_label של פלייבוק שלא אושר
  שונה מהתווית הבסיסית שנגזרת.
- APPROVER_FIELD: שדה מאשר או הסלמה (authority, approval_required, approval_source, required_approver ...).
- MARKET_COUNT_MISMATCH: מספר בשורת השקיפות או ב-handoff שונה מ-market_research.counts.
- UNVERIFIED_LABEL_FORMAT: "1 מקורות" או סוגריים ריקים בתווית "ממצא לא מאומת".
- MARKET_SAMPLE_PURPOSE: כל משפחות המקורות (או רובן, אזהרה) ממטרת התקשרות שאינה מטרת הפלייבוק
  (source_refs[].engagement_purpose מול market_research.question.engagement_purpose), בכל סוג הסכם.
- MARKET_NO_LOCAL_SOURCE: אין מקור מתחום השיפוט של החברה, ואין jurisdiction_note.
- LEGAL_FACT_SOURCE, LEGAL_FACT_STALE: עובדת דין ממקור רשמי אחד עם בדיקת עדכניות (החלטה 3, ללא שינוי).
- FORBIDDEN_LABEL, PRODUCED_WITH.
"""
import json
import re

try:
    from playbook import status as S
    from playbook import market_counts as MC
    from playbook.approval_sheet import track_wording, company_roles, role_effect, role_code
    from common.terms import terms_re
except ImportError:  # pragma: no cover
    import os
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from playbook import status as S
    from playbook import market_counts as MC
    from playbook.approval_sheet import track_wording, company_roles, role_effect, role_code
    from common.terms import terms_re

TRACKS = ('green', 'yellow', 'red')
MAX_WALK_AWAY = 5
WALK_SOURCES = ('statute', 'client_answer', 'company_document')
FORBIDDEN = ('אומת בשני מקורות', 'אומת במקור אחד בלבד')
APPROVER_KEYS = ('approval_required', 'approval_source', 'required_approver', 'required_by', 'escalation',
                 'approver', 'per_track')
_HEB = re.compile('[֐-׿]')


def _f(out, code, severity, message, rule_id=None, track=None):
    out.append({'code': code, 'severity': severity, 'rule_id': rule_id, 'track': track, 'message': message})


def _imp(rule):
    return str(rule.get('importance') or '').lower()


def _core_val(rule, core_by_id, key):
    if rule.get(key) is not None:
        return rule[key]
    return (core_by_id.get(rule['rule_id']) or {}).get(key)


def _wordings(t, track):
    """[(text, lang)] של כל נוסח במסלול: proposed_clause בכל שפה, ונוסח הנסיגה בצהוב."""
    out = []
    pc = t.get('proposed_clause')
    if isinstance(pc, dict):
        for lang in ('he', 'en'):
            if (pc.get(lang) or '').strip():
                out.append((pc[lang], lang))
    elif isinstance(pc, str) and pc.strip():
        out.append((pc, 'he' if _HEB.search(pc) else 'en'))
    if track == 'yellow':
        fw = track_wording('yellow', t)
        if fw and all(fw != x for x, _ in out):
            out.append((fw, 'he' if _HEB.search(fw) else 'en'))
    return out


def _iter_tracks(rule):
    """(segment_id, track, block) לכל מסלול בכלל ובכל וריאנט."""
    for track in TRACKS:
        yield None, track, (rule.get('traffic_light') or {}).get(track) or {}
    for var in rule.get('segment_variants') or []:
        for track in TRACKS:
            t = (var.get('traffic_light') or {}).get(track)
            if t:
                yield var.get('segment_id'), track, t


def _accept_text(model, lang):
    """כל נוסחי הירוק בשפה הזו, פסקה לכל כלל: "ההסכם" שהפלייבוק מציע, לבדיקות שתלויות בשאר ההסכם."""
    out = []
    for rule in model.get('rules') or []:
        t = (rule.get('traffic_light') or {}).get('green') or {}
        out += [text for text, lg in _wordings(t, 'green') if lg == lang]
    return '\n'.join(out)


def wording_findings(model):
    """בדיקות הפערים המשותפות (common.gap_checks) על כל נוסח ירוק, צהוב ונסיגה, בכל שפה. ממצא = error.
    אין כאן רמז נושא ואין שיקול של סוג הסכם: המודול המשותף בודק מנגנונים כלליים בלבד."""
    try:
        from common import gap_checks
    except ImportError:
        return [{'code': 'GAP_CHECKS_UNAVAILABLE', 'severity': 'error', 'rule_id': None, 'track': None,
                 'message': 'common.gap_checks אינו זמין, ולכן אי אפשר לבדוק את הנוסחים לפני הגיליון.'}]
    out = []
    for rule in model.get('rules') or []:
        for seg, track, t in _iter_tracks(rule):
            if track not in ('green', 'yellow'):
                continue
            for text, lang in _wordings(t, track):
                ctx = {'accept_text': _accept_text(model, lang) + '\n' + text, 'source': 'playbook',
                       'rule_id': rule['rule_id'], 'track': track, 'segment': seg}
                for hit in gap_checks.check_wording(text, lang, topic=None, context=ctx) or []:
                    _f(out, 'WORDING_GAP', 'error', '%s: %s' % (hit.get('code'), hit.get('message_he') or ''),
                       rule['rule_id'], track)
                    out[-1].update(gap_code=hit.get('code'), span=hit.get('span'), lang=lang)
    return out


def _approver_paths(obj, path=''):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = '%s.%s' % (path, k) if path else k
            if (k in APPROVER_KEYS or k == 'authority') and v not in (None, '', [], {}, False):
                yield p
            else:
                yield from _approver_paths(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _approver_paths(v, '%s[%d]' % (path, i))


def validate(model, core=None, index_entry=None, check_wording=True):
    out = []
    rules = model.get('rules') or []
    core_by_id = {c.get('id') or c.get('rule_id'): c for c in (core or {}).get('clauses') or []}

    # --- שוברי עסקה ו-hold_green: לפי החשיבות, בכל סוג הסכם ---
    walks = [r for r in rules if bool(_core_val(r, core_by_id, 'walk_away'))]
    if rules and len(walks) == len(rules):
        _f(out, 'WALKAWAY_ALL', 'error', 'כל %d הכללים מסומנים שובר עסקה: אין מרחב ויתור. '
           'שובר עסקה רק לשובר עסקה אמיתי.' % len(rules))
    for r in walks:
        if _imp(r) != 'critical':
            _f(out, 'WALKAWAY_NOT_CRITICAL', 'error', 'שובר עסקה בכלל בחשיבות "%s".' % _imp(r), r['rule_id'])
        if _core_val(r, core_by_id, 'walk_away_source') not in WALK_SOURCES:
            _f(out, 'WALKAWAY_NO_SOURCE', 'error', 'שובר עסקה בלי walk_away_source (חובה בדין, מסמך של החברה, או '
               'תשובת הלקוח).', r['rule_id'])
    if len(walks) > MAX_WALK_AWAY:
        _f(out, 'WALKAWAY_TOO_MANY', 'warning', '%d שוברי עסקה (המלצה: עד %d).' % (len(walks), MAX_WALK_AWAY))
    holds = [r for r in rules if _core_val(r, core_by_id, 'round1_posture') == 'hold_green']
    if rules and len(holds) == len(rules):
        _f(out, 'HOLD_GREEN_ALL', 'error', 'כל הכללים hold_green בסבב הראשון: הנושא ונותן אינו יכול לבנות '
           'תגובה ממוקדת.')
    for r in holds:
        if _imp(r) == 'low':
            _f(out, 'HOLD_GREEN_LOW', 'error', 'hold_green בכלל בחשיבות נמוכה: בסבב הראשון מציעים צהוב.',
               r['rule_id'])

    # --- מרחב אמיתי, ושורת השפעה לכל תפקיד של החברה ---
    roles = [r for r, _ in company_roles(model)]
    multi = role_code(model) == 'mutual' or len(roles) > 1
    for r in rules:
        tl = r.get('traffic_light') or {}
        g, y = tl.get('green') or {}, tl.get('yellow') or {}
        if g.get('position') and g['position'].strip() == (y.get('position') or '').strip():
            _f(out, 'YELLOW_EQUALS_GREEN', 'error', 'הצהוב זהה לירוק: אין מרחב ויתור.', r['rule_id'])
        fw = y.get('fallback_wording')
        fw = fw.get('text') if isinstance(fw, dict) else fw
        gw = g.get('proposed_clause')
        gw = (gw.get('he') or gw.get('en')) if isinstance(gw, dict) else gw
        if fw and gw and fw.strip() == gw.strip():
            _f(out, 'FALLBACK_EQUALS_GREEN', 'error', 'נוסח הנסיגה זהה לנוסח הירוק.', r['rule_id'])
        for _, track, t in _iter_tracks(r):
            if t.get('protects_main_role') is False:
                _f(out, 'YELLOW_WORSENS_MAIN_ROLE', 'error', 'המסלול %s סומן כפוגע בתפקיד העיקרי של החברה.'
                   % track, r['rule_id'], track)
            if multi and t.get('position'):
                if len(roles) < 2:
                    _f(out, 'ROLE_EFFECT_MISSING', 'error', 'לחברה יותר מתפקיד אחד בהסכם, ונמצאה שורת השפעה לתפקיד '
                       'אחד בלבד (%s) במסלול %s.' % (', '.join(roles), track), r['rule_id'], track)
                for role in roles:
                    if not role_effect(t, role):
                        _f(out, 'ROLE_EFFECT_MISSING', 'error', 'חסרה שורת ההשפעה של התפקיד %s במסלול %s.'
                           % (role, track), r['rule_id'], track)

    # --- נוסחים: בדיקות הפערים המשותפות ---
    if check_wording:
        out += wording_findings(model)

    # --- תווית אחת ---
    want = S.base_label(model)
    holders = [('model', model), ('core', core), ('index', index_entry)]
    if isinstance(model.get('handoff'), dict):
        holders.append(('handoff', model['handoff']))
    for name, holder in holders:
        if not holder:
            continue
        for f in S.DUAL_FIELDS:
            if f in holder:
                _f(out, 'LABEL_DUAL_FIELD', 'error', '%s.%s: שדה תווית כפול. התווית היחידה היא status_label, '
                   'שנגזרת ב-status.derive_status.' % (name, f))
        lbl = holder.get(S.LABEL_FIELD)
        if lbl and holder.get('playbook_status', 'Draft') == 'Draft' and lbl != want:
            _f(out, 'LABEL_MISMATCH', 'error', '%s.status_label="%s", ולפי corpus_origin=%s וה-basis של '
               'המסלולים: "%s".' % (name, lbl, model.get('corpus_origin'), want))

    # --- אין שרשרת אישורים ---
    for name, holder in (('model', model), ('core', core)):
        for p in _approver_paths(holder or {}):
            _f(out, 'APPROVER_FIELD', 'error', '%s.%s: שדה מאשר או הסלמה. אין שרשרת אישורים: ויתור מעבר לצהוב '
               'או חציית אדום מוצגים למשתמש כ"נדרשת הכרעתך". החתימה של היועץ המשפטי על הגיליון נשארת.' % (name, p))

    # --- מדגם השוק: מטרת ההתקשרות ותחום השיפוט, לכל משפחה ---
    mr = model.get('market_research') or {}
    srcs = mr.get('source_refs') or mr.get('sources') or []
    want_purpose = (mr.get('question') or {}).get('engagement_purpose') or \
        (model.get('applicability') or {}).get('engagement_purpose')
    if srcs and want_purpose:
        fam_other = {}
        for s in srcs:
            if not s.get('engagement_purpose'):
                continue
            fam = s.get('template_family') or s.get('family') or s.get('source_id') or s.get('id')
            fam_other[fam] = fam_other.get(fam, True) and s['engagement_purpose'] != want_purpose
        if fam_other and all(fam_other.values()):
            _f(out, 'MARKET_SAMPLE_PURPOSE', 'error', 'כל משפחות המקורות ממטרת התקשרות אחרת ממטרת הפלייבוק (%s). '
               'נדרשת לפחות משפחה אחת ממטרה זהה.' % want_purpose)
        elif fam_other and sum(fam_other.values()) * 2 > len(fam_other):
            _f(out, 'MARKET_SAMPLE_PURPOSE', 'warning', 'רוב משפחות המקורות (%d מתוך %d) ממטרת התקשרות אחרת: '
               'לשקלל או להוציא.' % (sum(fam_other.values()), len(fam_other)))
    if srcs:
        home = ((model.get('scope_summary') or {}).get('contracting_entity') or {}).get('incorporation_country') or 'IL'
        local = any((s.get('jurisdiction') or '').upper().startswith(home) for s in srcs)
        if not local and not mr.get('jurisdiction_note'):
            _f(out, 'MARKET_NO_LOCAL_SOURCE', 'error', 'אין מקור שוק מ-%s, ואין jurisdiction_note שאומר זאת.' % home)

    # --- אותם מספרים בכל משטח ---
    c = MC.counts(model)
    if 'counted' in c:
        disc = mr.get('disclosure') or {}
        texts = [('market_research.disclosure.fixed_sentence', disc.get('fixed_sentence')),
                 ('market_research.disclosure.chat_message', disc.get('chat_message')),
                 ('meta.evidence_disclaimer', (model.get('meta') or {}).get('evidence_disclaimer'))]
        for where, txt in texts:
            for p in MC.count_claims(txt or '', model):
                _f(out, 'MARKET_COUNT_MISMATCH', 'error', '%s: %s' % (where, p))
        ho = model.get('handoff') or {}
        if isinstance(ho.get('counted_sources'), int) and ho['counted_sources'] != c['counted']:
            _f(out, 'MARKET_COUNT_MISMATCH', 'error', 'handoff.counted_sources=%d, ובספירה counted=%d'
               % (ho['counted_sources'], c['counted']))

    # --- תווית "ממצא לא מאומת" בתבנית אחת ---
    for u in mr.get('unverified_findings') or []:
        lbl = ' '.join(x for x in (u.get('label'), u.get('reason')) if x)
        if re.search(r'(?<!\d)1 מקורות|\(\s*\)', lbl):
            _f(out, 'UNVERIFIED_LABEL_FORMAT', 'error', 'התווית "%s": "מקור אחד (W..)", בלי סוגריים ריקים.' % lbl,
               u.get('rule_id'))

    # --- עובדות דין: מקור רשמי אחד ובדיקת עדכניות ---
    facts = (model.get('regulatory_research') or {}).get('facts') or []
    stale = set()
    for fact in facts:
        fid = fact.get('fact_id') or fact.get('id')
        src = fact.get('official_source') or {}
        if not src.get('url') or not fact.get('currency_check'):
            _f(out, 'LEGAL_FACT_SOURCE', 'error', 'עובדת דין %s: נדרש מקור רשמי אחד עם קישור, ובדיקת עדכניות '
               '(הנוסח בתוקף ביום המחקר).' % fid)
            continue
        cc = fact['currency_check']
        version = str(src.get('version_date') or '')
        later = [a for a in cc.get('amendments_after_version') or [] if str(a.get('in_force') or '') > version]
        if later or cc.get('result') == 'outdated':
            stale.add(fid)
    for r in rules:
        for so in r.get('statutory_override') or []:
            if so.get('fact_id') in stale:
                _f(out, 'LEGAL_FACT_STALE', 'error', '"חובה בדין" נשענת על נוסח שקודם לתיקון (%s). מסמנים '
                   '"טעון בדיקה משפטית" עד שנקרא הנוסח בתוקף.' % so['fact_id'], r['rule_id'])

    # --- תוויות אסורות וגרסה ---
    blob = json.dumps(model, ensure_ascii=False)
    for w in FORBIDDEN:
        if terms_re([w]).search(blob):   # 1.2.0: מילה שלמה (common/terms.py)
            _f(out, 'FORBIDDEN_LABEL', 'error', 'התווית "%s" אסורה. "לא אומת" עם מספר המקורות והסיבה, או מקור '
               'רשמי אחד עם בדיקת עדכניות לעובדת דין.' % w)
    pw = model.get('produced_with') or {}
    if not all(pw.get(k) for k in ('skill_version', 'notes_version', 'refs_sha256')):
        _f(out, 'PRODUCED_WITH', 'error', 'חסר produced_with {skill_version, notes_version, refs_sha256}.')
    return out


def errors(findings):
    return [f for f in findings if f['severity'] == 'error']


def codes(findings, severity=None):
    return {f['code'] for f in findings if severity is None or f['severity'] == severity}
