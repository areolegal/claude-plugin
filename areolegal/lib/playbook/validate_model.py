# -*- coding: utf-8 -*-
"""playbook/validate_model.py: בדיקות תוכן כלליות על playbook-model.json ועל הגרעין, לכל סוג הסכם.

המאמת כללי: הוא בודק מנגנונים שחלים בכל פלייבוק, ואינו מכיל שיקול משפטי של סוג הסכם מסוים (נושאים, כיוון של
סעיף, דין ושיפוט, סוג מקור של עסקה מסוימת). שיקול כזה שייך לפלייבוק של הלקוח, כנתון שהפלייבוק נושא. בדיקות
הנוסח עצמן הן של מודול בדיקות הפערים המשותף (common/gap_checks.py).

validate(model, core=None, index_entry=None) מחזיר רשימת ממצאים {code, severity: error|warning, rule_id,
track, message}. error = חוסם מסירה. הקודים:
- WALKAWAY_ALL, WALKAWAY_NOT_CRITICAL, WALKAWAY_TOO_MANY (אזהרה), WALKAWAY_NO_SOURCE (שובר עסקה בלי
  walk_away_source: statute | client_answer | company_document).
- HOLD_GREEN_ALL, HOLD_GREEN_LOW.
- YELLOW_EQUALS_GREEN, FALLBACK_EQUALS_GREEN, YELLOW_WORSENS_MAIN_ROLE (מסלול שסומן protects_main_role=false).
- ROLE_EFFECT_MISSING: חסרה שורת השפעה לאחד התפקידים שיש לחברה בהסכם (approval_sheet.company_roles).
- WORDING_GAP: נוסח ירוק, צהוב או נסיגה שנכשל בבדיקות הפערים המשותפות. GAP_CHECKS_UNAVAILABLE: המודול חסר.
- LABEL_DUAL_FIELD: presentation_label נשמר במקום כלשהו. LABEL_MISMATCH: בסיס התווית שנשמרה שונה מהתווית
  שנגזרת (status.base_code), או שהמעמד אינו תואם אותה. LABEL_DRIFT: שכבות (מודל, גרעין, אינדקס, handoff) שומרות
  תוויות שונות. LABEL_OLD_WORDING (אזהרה): התווית בניסוח הקודם. (status.label_findings)
- APPROVER_FIELD: שדה מאשר או הסלמה (authority, approval_required, approval_source, required_approver ...).
- MARKET_COUNT_MISMATCH: מספר בשורת השקיפות או ב-handoff שונה מ-market_research.counts.
- UNVERIFIED_LABEL_FORMAT: "1 מקורות" או סוגריים ריקים בתווית "ממצא לא מאומת".
- MARKET_SAMPLE_PURPOSE: כל משפחות המקורות (או רובן, אזהרה) ממטרת התקשרות שאינה מטרת הפלייבוק
  (source_refs[].engagement_purpose מול market_research.question.engagement_purpose), בכל סוג הסכם.
- MARKET_NO_LOCAL_SOURCE: אין מקור שוק מתחום השיפוט של הדין החל (scope_summary.governing_laws[], ובלעדיו מדינת
  ההתאגדות של הישות החותמת), ואין jurisdiction_note.
- MARKET_NO_HOME_COUNTRY (אזהרה): אין governing_laws[] ואין incorporation_country מזוהה. אין הנחה של IL: בדיקת
  המקור המקומי אינה רצה.
- SOURCE_CASE_LAW: כתובת של אתר בית משפט, מאגר פסיקה או מדור פסיקה (common/case_law.py) בכל מקור. SOURCE_NOT_APPROVED:
  מקור משפטי או רגולטורי (regulatory_research, external_sources L/X, statutory_override) מחוץ לרשימת המקורות
  המאושרים. SOURCE_LIST_UNAVAILABLE (אזהרה). (source_findings)
- CASE_LAW_NO_CONNECTOR, CASE_LAW_TEXT: פסיקה בלי מחבר פסיקה סגור (case_law_access.connector הוא null);
  CASE_LAW_NO_REF, CASE_LAW_IN_WORDING: עם מחבר (case_law_findings).
- GOVERNING_LAWS_MISSING, OVERRIDE_NO_JURISDICTION (אזהרות): הדין החל של הסוג, ו-jurisdiction בכל חובה בדין ובכל
  שכבת statute (jurisdiction_findings).
- NO_SOURCE_NOTE (אזהרה, לעולם אינה חוסמת): נושא שבו מחקר רשת הותר (מחקר עומק שהלקוח בחר, או פלייבוק לפי הרשת
  והשוק שהלקוח ביקש) ולא נמצא מקור מורשה, ואין בו ההערה הגלויה "AREO לא מצאה מקור מורשה לנקודה זו"
  (no_source_findings). אין רצפות ותקרות של הדין בקוד: ממצא בדין בא רק מרשימת המקורות המאושרים.
- SOURCE_NOT_SHOWN: עמדה (ירוק, צהוב או אדום) שנגזרה ממסמכי הלקוח, בלי הסכם וסעיף שעליהם נשענה
  (position_source_findings, כלל מייסד 12).
- COVERAGE_LEDGER, COVERAGE_LEDGER_AGREEMENT: ספר הכיסוי (coverage_ledger) אינו מסתכם: סעיפים = סעיפים עם מדיניות
  + סעיפים שנרשמו במפורש כ"אין מדיניות שאפשר לחלץ" + סעיפים ייחודיים שממתינים להכרעה (כלל מייסד 14).
- SUFFICIENCY_NOT_ASKED, SUFFICIENCY_STALE (אזהרה): ההסכמים אינם מספיקים להסקת קווי הנסיגה, והלקוח לא נשאל
  (playbook/sufficiency.py, כלל מייסד 13).
- RATIONALE_DUPLICATE, LEGAL_CORE_MISSING, LEGAL_CORE_REVIEW_ONLY, LEGAL_CORE_STATUTE: נימוק שהודבק לכמה כללים, ושלד
  משפטי חסר או שאינו אלא "טעון בדיקה משפטית" (rationale_findings).
- TRACK_WORDING_MISMATCH, COUNTERPARTY_UNREALISTIC, CONCERN_UNMAPPED (אזהרה): נוסח שאינו תואם את תיאורו, נסיגה שאינה
  ריאלית מול גוף ציבורי, וחשש של הלקוח בלי כלל (fallback_findings).
- LEGAL_FACT_SOURCE, LEGAL_FACT_STALE: עובדת דין ממקור רשמי אחד עם בדיקת עדכניות.
- FORBIDDEN_LABEL, PRODUCED_WITH.
- DEPT_*: המחלקות האחראיות ושיוך החיובים (departments_and_responsibilities.md), כשהשדות קיימים: DEPT_SHAPE (מבנה),
  DEPT_TYPE (type שאינו אחד מ-17 סוגי החובה של מרשם ההתחייבויות), DEPT_TYPE_DUPLICATE (שני שיוכים לאותו סוג),
  DEPT_UNKNOWN (מחלקה שאינה ב-responsible_departments, או מחלקה מוצעת בלי needs_verification), DEPT_NO_SOURCE
  (שיוך או הצעה בלי הפניית מקור), DEPT_PROPOSED_NO_QUOTE (מחלקה מוצעת בלי ציטוט).
- COVERAGE_*: כל יחידת סעיף בכל הסכם בקורפוס קיבלה נושא, קוד טכני, סימון "סעיף ייחודי" או סיבה מפורשת
  לכך שלא מופתה (coverage_findings). אין נושא "ברירת מחדל", ונושא שקיבל חלק חריג מהיחידות מחייב נימוק.
  כשנמסרים מלאי הסעיפים (clause-inventory.json) וקובץ החילוץ (corpus-extract.json), הספירה מחושבת מהם
  ומושווית לבלוק שבמודל (coverage_from_inventory), וכל פסקה מהותית בכל הסכם חייבת להיות בתוך יחידה.
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

try:
    from obligations.model import TYPES as OBLIGATION_TYPES
except ImportError:  # pragma: no cover
    OBLIGATION_TYPES = ('payment', 'milestone', 'deliverable', 'insurance', 'guarantee', 'reporting', 'notice',
                        'renewal_notice', 'term_end', 'option', 'audit', 'consent_approval', 'data_return_deletion',
                        'confidentiality', 'compliance', 'price_adjustment', 'other')

TRACKS = ('green', 'yellow', 'red')
MAX_WALK_AWAY = 5
WALK_SOURCES = ('statute', 'client_answer', 'company_document')
FORBIDDEN = ('אומת בשני מקורות', 'אומת במקור אחד בלבד')
APPROVER_KEYS = ('approval_required', 'approval_source', 'required_approver', 'required_by', 'escalation',
                 'approver', 'per_track')
_HEB = re.compile('[֐-׿]')
# שם מדינה נפוץ לקוד ISO-3166 alpha-2 (כמו COUNTRY_CODES בהקמה); קוד בן שתי אותיות עובר כמו שהוא, באותיות גדולות
COUNTRY_CODES = {
    'ישראל': 'IL', 'israel': 'IL', 'ארצות הברית': 'US', 'ארה"ב': 'US', 'ארה״ב': 'US', 'united states': 'US',
    'usa': 'US', 'בריטניה': 'GB', 'אנגליה': 'GB', 'united kingdom': 'GB', 'uk': 'GB', 'england': 'GB',
    'גרמניה': 'DE', 'germany': 'DE', 'צרפת': 'FR', 'france': 'FR', 'הולנד': 'NL', 'netherlands': 'NL',
    'אירלנד': 'IE', 'ireland': 'IE', 'קפריסין': 'CY', 'cyprus': 'CY', 'שווייץ': 'CH', 'switzerland': 'CH',
    'סינגפור': 'SG', 'singapore': 'SG', 'קנדה': 'CA', 'canada': 'CA', 'אוסטרליה': 'AU', 'australia': 'AU',
    'הודו': 'IN', 'india': 'IN', 'יפן': 'JP', 'japan': 'JP', 'איטליה': 'IT', 'italy': 'IT', 'ספרד': 'ES',
    'spain': 'ES', 'לוקסמבורג': 'LU', 'luxembourg': 'LU', 'איחוד האמירויות': 'AE', 'united arab emirates': 'AE',
    'uae': 'AE',
}


def country_code(raw):
    """ISO-3166 alpha-2 מהערך שנשמר; None כשהערך חסר או לא מזוהה."""
    v = re.sub(r'\s+', ' ', str(raw or '')).strip()
    if re.fullmatch(r'[A-Za-z]{2}', v):
        return v.upper()
    return COUNTRY_CODES.get(v) or COUNTRY_CODES.get(v.lower())


def _country_of(code):
    """המדינה של קוד תחום שיפוט: GB-EAW -> GB, US-NY -> US, "Israel" -> IL. None כשאינו מזוהה."""
    v = str(code or '').strip()
    return country_code(v) or country_code(re.split(r'[-_/ ]', v)[0]) if v else None


def governing_countries(model):
    """המדינות של הדין החל על הסכמי הסוג (scope_summary.governing_laws[]), בלי כפילות."""
    laws = (model.get('scope_summary') or {}).get('governing_laws') or []
    if isinstance(laws, str):
        laws = [laws]
    return list(dict.fromkeys(c for c in (_country_of(x.get('code') if isinstance(x, dict) else x)
                                          for x in laws) if c))


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
                # הסייג "או המועד המרבי שבדין, לפי המוקדם" מותר בנוסח של פלייבוק (evidence-policy.md)
                ctx = {'accept_text': _accept_text(model, lang) + '\n' + text, 'source': 'playbook',
                       'rule_id': rule['rule_id'], 'track': track, 'segment': seg, 'allow_statutory_cap': True}
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


# --- כיסוי הסעיפים (playbook-schema.md, coverage; clause-catalog.md) ---
# הרשימה הסגורה של הקודים הטכניים, מילה במילה מ-clause-catalog.md. אין קוד "אחר": סעיף שאינו אחד מאלה הוא נושא
TECHNICAL_CODES = ('signature_block', 'party_identification', 'notice_addresses', 'counterparts_esignature',
                   'headings', 'interpretation_grammar', 'recitals_descriptive', 'neutral_definition',
                   'bank_details', 'delivery_points_list', 'admin_form_fields', 'statutory_admin_restatement')
# נימוקים שאינם נימוק להשמטה: נוסח שחוזר בכל ההסכמים הוא הראיה החזקה ביותר לירוק
FORBIDDEN_OMISSION = ('לא רלוונטי', 'נוסח אחיד', 'נוסח עקבי', 'אין מחלוקת', 'תפעולי', 'הסכם יחיד', 'תנאי מסחרי',
                      'אין ראיה לעמדת החברה', 'סטנדרטי', 'טכני בלבד', 'אין צורך', 'ברור מאליו', 'not relevant',
                      'standard', 'boilerplate')
# שיוך "כל מה שלא זוהה" לנושא אחד. בהרצה חיה 274 יחידות שויכו כך לנושא הראשון
DEFAULT_TOPIC_RE = re.compile('ברירת מחדל|שלא זוהה בה נושא|לא זוהה (?:בה |בו )?נושא|by default|default topic|'
                              'fallback topic', re.I)
# שלילה לפני הביטוי, באותו משפט ועד שלוש מילים לפניו: "ללא נושא ברירת מחדל" אומר שאין שיוך כזה. בהרצה חיה
# המשפט הזה נפסל כ-COVERAGE_DEFAULT_TOPIC
NEGATION_RE = re.compile(r'(?:^|[\s(])(?:ללא|בלי|אין|no|not|without|never)\s+(?:\S+\s+){0,3}$', re.I)
SUBSTANTIVE_CHARS = 40      # פסקה מהותית בקובץ החילוץ: 40 תווים ומעלה, שאינה כותרת עליונה או תחתונה
CONCENTRATION_MIN_UNITS = 20
CONTINUATION_MAX = 8        # כמה פסקאות בלי מספר נכללות בסעיף שמספרו זוהה, לפני שכל פסקה נעשית יחידה


def _cov_num(cov, name, alias):
    """המספר בשם שבסכמה (units, topic_units...), או בשם החלופי (units_total, units_mapped...)."""
    v = cov.get(name)
    return v if isinstance(v, int) and not isinstance(v, bool) else cov.get(alias)


def _unit_kind(u):
    """rule | technical | unique | unmapped | None (יחידה שלא קיבלה דבר)."""
    if u.get('rule_id'):
        return 'rule'
    if u.get('technical'):
        return 'technical'
    if u.get('unique'):
        return 'unique'
    if str(u.get('unmapped_reason') or '').strip():
        return 'unmapped'
    return None


def default_topic_hit(text):
    """הביטוי של שיוך ברירת מחדל בטקסט, או None. ביטוי שקודמת לו שלילה באותו משפט אינו נספר."""
    for m in DEFAULT_TOPIC_RE.finditer(text or ''):
        before = re.split(r'[.,;:!?\n]', text[:m.start()])[-1]
        if not NEGATION_RE.search(before):
            return m.group(0)
    return None


def _corpus_source(model, s):
    """מקור שנכנס למלאי הסעיפים: נכלל, ואינו תבנית. כשהמאגר הוא נוסחים שהחברה מציגה (corpus_status:
    company_forms, workflow.md שלב 2ח), הנוסחים הם הקורפוס גם כשנרשמו כתבנית: בהרצה חיה הם
    נרשמו doc_role: template, כמו שההוראות אמרו אז, ושלד המלאי יצא ריק.
    תבנית של צד שכנגד (paper: theirs: טופס סטנדרטי שהצד שכנגד מציג לחתימה, למשל חוזה של צד אחד, תנאים
    כלליים של צד או נספח של הליך תחרותי) היא מסמך מהקורפוס בכל מעמד, ונכנסת למלאי:
    נספחים של הליך תחרותי עלולים להירשם כתבנית במעמד unknown, ולא להיות ממופים כלל (corpus-pipeline.md, פרק 2)."""
    if not isinstance(s, dict) or s.get('included') is False:
        return False
    return (s.get('doc_role') != 'template' or s.get('paper') == 'theirs'
            or S.corpus_status(model) == 'company_forms')


def _base(p):
    return re.split(r'[\\/]', str(p or ''))[-1].strip().lower()


def _extract_docs(model, extract):
    """{source_id: מסמך החילוץ}, לפי שם הקובץ ב-source_log מול path בחילוץ, או doc_id."""
    docs = (extract or {}).get('documents') or []
    by_name = {_base(d.get('path')): d for d in docs}
    by_id = {d.get('doc_id'): d for d in docs if d.get('doc_id')}
    out = {}
    for s in model.get('source_log') or []:
        if not _corpus_source(model, s):
            continue
        d = by_id.get(s.get('doc_id')) or by_name.get(_base(s.get('file')))
        out[s.get('source_id')] = d
    return out


def _substantive(doc):
    return {p.get('i') for p in doc.get('paragraphs') or []
            if p.get('kind') != 'header_footer' and len(str(p.get('text') or '').strip()) >= SUBSTANTIVE_CHARS}


def inventory_skeleton(model, extract):
    """שלד המלאי מקובץ החילוץ: יחידה לכל סעיף, בלי שיוך. הבונה ממלא בכל יחידה rule_id, technical, unique או
    unmapped_reason, ושומר כ-clause-inventory.json.
    יחידה מתחילה בפסקה שזוהה בה מספר סעיף, וכוללת עד 8 פסקאות שאחריה עד מספר הסעיף הבא; כל פסקה מהותית אחרת היא יחידה בפני עצמה.
    כך כל פסקה מהותית נמצאת ביחידה אחת בדיוק, גם כשזיהוי מספרי הסעיפים בחילוץ חלקי (מסמך בלי מספור, או מספור
    חלקי), ויחידה אינה בולעת פרק שלם שמספרו לא זוהה."""
    units = []
    docs = _extract_docs(model, extract)
    if not (model or {}).get('source_log'):
        # השלד נבנה לפני המודל (wf1, שלב 4א): בלי source_log, כל מסמך בחילוץ, והמזהים S01, S02... לפי סדר
        # המסמכים בחילוץ. source_log נבנה אחר כך באותם מזהים, לפי השדה file שבכל יחידה
        docs = {'S%02d' % (n + 1): d for n, d in enumerate((extract or {}).get('documents') or [])}
    for sid, doc in docs.items():
        if doc is None:
            continue
        subst = _substantive(doc)
        cur = None
        for par in doc.get('paragraphs') or []:
            i = par.get('i')
            if par.get('kind') == 'header_footer':
                continue
            if str(par.get('clause') or '').strip():
                cur = {'source_ref': sid, 'file': doc.get('path'), 'p': i, 'p_to': i,
                       'clause': str(par['clause']).strip(), 'text': str(par.get('text') or '')[:300]}
                units.append(cur)
            elif cur is not None and cur['source_ref'] == sid and i - cur['p'] <= CONTINUATION_MAX:
                cur['p_to'] = i
            elif i in subst:
                cur = None
                units.append({'source_ref': sid, 'file': doc.get('path'), 'p': i, 'p_to': i, 'clause': '',
                              'text': str(par.get('text') or '')[:300]})
        cur = None
    return {'generated_from': 'corpus-extract.json', 'unit_rule': inventory_skeleton.__doc__.split('\n')[2].strip(),
            'units': units}


def coverage_from_inventory(model, inventory, extract=None):
    """הבלוק coverage, מחושב מהמלאי (ומהחילוץ, כשנמסר). הבונה מעתיק אותו למודל כמו שהוא.

    יחידה במלאי: {source_ref, p, p_to, clause, text} ואחד מאלה: rule_id | technical (קוד מהרשימה הסגורה) |
    unique: true עם queue_id | unmapped_reason. p ו-p_to הם האינדקסים (i) של הפסקה הראשונה והאחרונה ביחידה."""
    units = (inventory or {}).get('units') or []
    rule_ids = {r.get('rule_id') for r in model.get('rules') or [] if isinstance(r, dict)}
    by_rule, cnt, unassigned, unknown = {}, {'rule': 0, 'technical': 0, 'unique': 0, 'unmapped': 0}, [], []
    tech, uniq, unm, per_src = {}, [], [], {}
    for u in units:
        k = _unit_kind(u)
        src = str(u.get('source_ref') or '').split('#')[0]
        ref = '%s#p%s' % (src, u.get('p'))
        row = per_src.setdefault(src, {'source_id': src, 'units': 0, 'mapped': 0, 'technical': 0, 'unique': 0,
                                       'unmapped': 0, 'unassigned': 0})
        row['units'] += 1
        if k is None:
            unassigned.append(ref)
            row['unassigned'] += 1
            continue
        cnt[k] += 1
        row['mapped' if k == 'rule' else k] += 1
        if k == 'rule':
            by_rule[u['rule_id']] = by_rule.get(u['rule_id'], 0) + 1
            if u['rule_id'] not in rule_ids:
                unknown.append(u['rule_id'])
        elif k == 'technical':
            tech.setdefault(u['technical'], {'code': u['technical'], 'reason': u.get('reason') or '', 'refs': []})
            tech[u['technical']]['refs'].append(ref)
        elif k == 'unique':
            uniq.append({'ref': ref, 'quote': u.get('text') or '', 'queue_id': u.get('queue_id') or '',
                         'kind': u.get('kind') or ''})
        else:
            unm.append({'ref': ref, 'reason': u['unmapped_reason']})
    docs = _extract_docs(model, extract) if extract else {}
    for sid, doc in docs.items():
        row = per_src.setdefault(sid, {'source_id': sid, 'units': 0, 'mapped': 0, 'technical': 0, 'unique': 0,
                                       'unmapped': 0, 'unassigned': 0})
        if doc is None:
            row['extract_paragraphs'] = None
            continue
        subst = _substantive(doc)
        covered = set()
        for u in units:
            if str(u.get('source_ref') or '').split('#')[0] == sid and isinstance(u.get('p'), int):
                end = u.get('p_to') if isinstance(u.get('p_to'), int) else u['p']
                covered.update(range(u['p'], end + 1))
        row['extract_paragraphs'] = len(subst)
        row['uncovered_paragraphs'] = len(subst - covered)
    topics_new = sum(1 for r in model.get('rules') or [] if isinstance(r, dict)
                     and r.get('topic_origin') == 'corpus_derived')
    return {'inventory_ref': (inventory or {}).get('ref') or '', 'units': len(units),
            'topic_units': cnt['rule'], 'technical_units': cnt['technical'], 'unique_units': cnt['unique'],
            'unmapped_units': cnt['unmapped'], 'unassigned_units': len(unassigned),
            'topics': len(rule_ids), 'topics_with_rule': len(rule_ids), 'topics_new': topics_new,
            'by_rule': by_rule, 'by_agreement': sorted(per_src.values(), key=lambda r: str(r['source_id'])),
            'technical_items': list(tech.values()), 'unique_clauses': uniq, 'unmapped': unm,
            '_unassigned_refs': unassigned[:20], '_unknown_rules': sorted(set(unknown))}


def coverage_findings(model, inventory=None, extract=None):
    """ממצאי הכיסוי: הבלוק שבמודל, ומול המלאי והחילוץ כשנמסרו. כל ממצא כאן חוסם."""
    out = []
    cov = model.get('coverage')
    if not isinstance(cov, dict):
        _f(out, 'COVERAGE_MISSING', 'error', 'אין במודל coverage: אין הוכחה שכל סעיף בכל הסכם קיבל נושא.')
        return out
    E = lambda code, msg, rid=None: _f(out, code, 'error', msg, rid)  # noqa: E731
    total = _cov_num(cov, 'units', 'units_total')
    mapped = _cov_num(cov, 'topic_units', 'units_mapped')
    tech_n = _cov_num(cov, 'technical_units', 'units_technical')
    uniq_n = _cov_num(cov, 'unique_units', 'units_unique') or 0
    unm_n = _cov_num(cov, 'unmapped_units', 'units_unmapped')
    nums = {'units': total, 'topic_units': mapped, 'technical_units': tech_n, 'unmapped_units': unm_n}
    for k, v in nums.items():
        if not isinstance(v, int) or isinstance(v, bool):
            E('COVERAGE_NUMBERS', 'coverage.%s חסר או אינו מספר שנספר בקוד.' % k)
    if not str(cov.get('inventory_ref') or '').strip():
        E('COVERAGE_NUMBERS', 'coverage.inventory_ref חסר: איפה נשמר מלאי הסעיפים.')
    ok = all(isinstance(v, int) and not isinstance(v, bool) for v in nums.values())
    if ok and mapped + tech_n + uniq_n + unm_n != total:
        E('COVERAGE_SUM', 'coverage אינו מסתכם: %d יחידות, ו-%d ממופות לנושא, %d טכניות, %d ייחודיות ו-%d לא ממופות.'
          % (total, mapped, tech_n, uniq_n, unm_n))
    if isinstance(cov.get('topics'), int) and cov.get('topics_with_rule') != cov['topics']:
        E('COVERAGE_TOPICS', '%s נושאים בלי כלל ב-rules[].' % (cov['topics'] - (cov.get('topics_with_rule') or 0)))
    rules = [r for r in model.get('rules') or [] if isinstance(r, dict)]
    rids = {r.get('rule_id') for r in rules}
    new_n = sum(1 for r in rules if r.get('topic_origin') == 'corpus_derived')
    if isinstance(cov.get('topics_new'), int) and cov['topics_new'] != new_n:
        E('COVERAGE_TOPICS', 'coverage.topics_new=%d, ו-%d כללים מסומנים topic_origin: corpus_derived.'
          % (cov['topics_new'], new_n))
    # יחידה שלא מופתה: רק עם סיבה מפורשת, אחת לכל יחידה
    unm = cov.get('unmapped') if isinstance(cov.get('unmapped'), list) else []
    if isinstance(unm_n, int) and unm_n:
        if len(unm) != unm_n:
            E('COVERAGE_UNMAPPED', '%d יחידות לא ממופות, ו-%d מהן רשומות ב-coverage.unmapped[] עם סיבה. יחידה '
              'שלא מופתה מותרת רק עם סיבה מפורשת (למשל טקסט שלא נקרא).' % (unm_n, len(unm)))
    for i, x in enumerate(unm):
        reason = str((x or {}).get('reason') or '')
        if not reason.strip() or any(b in reason for b in FORBIDDEN_OMISSION):
            E('COVERAGE_UNMAPPED', 'coverage.unmapped[%d] (%s): "%s" אינה סיבה.' % (i, (x or {}).get('ref'), reason[:40]))
    # סעיף ייחודי: ציטוט, ופריט בתור ההכרעות
    uq = cov.get('unique_clauses') if isinstance(cov.get('unique_clauses'), list) else []
    if uniq_n and len(uq) != uniq_n:
        E('COVERAGE_UNIQUE', 'unique_units=%d, ו-%d סעיפים ב-coverage.unique_clauses[].' % (uniq_n, len(uq)))
    qids = {q.get('id') for q in model.get('validation_queue') or [] if isinstance(q, dict)}
    kinds = {}
    for i, x in enumerate(uq):
        x = x or {}
        if not str(x.get('quote') or '').strip() or not x.get('ref'):
            E('COVERAGE_UNIQUE', 'coverage.unique_clauses[%d]: סעיף ייחודי נרשם עם ref ועם ציטוט.' % i)
        if x.get('queue_id') not in qids:
            E('COVERAGE_UNIQUE', 'coverage.unique_clauses[%d] (%s): אין לו פריט בתור ההכרעות (queue_id).'
              % (i, x.get('ref')))
        if x.get('kind'):
            kinds.setdefault(str(x['kind']).strip(), set()).add(str(x.get('ref') or '').split('#')[0])
    for kind, srcs in kinds.items():
        if len(srcs) >= 2:
            E('COVERAGE_UNIQUE', 'סוג הסעיף "%s" מופיע ב-%d הסכמים (%s): סוג שחוזר בשני הסכמים או יותר הוא נושא '
              'בפלייבוק, עם רמזור, ולא "סעיף ייחודי".' % (kind, len(srcs), ', '.join(sorted(srcs))))
    # קודים טכניים: רק מהרשימה הסגורה, עם נימוק והפניה
    items = cov.get('technical_items')
    if not isinstance(items, list):
        E('COVERAGE_TECHNICAL', 'coverage.technical_items[] חסר (מקור הפרק "סעיפים שלא קיבלו מדיניות").')
        items = []
    refs_total = 0
    for k, it in enumerate(items):
        it = it if isinstance(it, dict) else {}
        if it.get('code') not in TECHNICAL_CODES:
            E('COVERAGE_TECHNICAL', 'coverage.technical_items[%d]: הקוד %s אינו ברשימה הסגורה.' % (k, it.get('code')))
        reason = str(it.get('reason') or '')
        if not reason or any(b in reason for b in FORBIDDEN_OMISSION):
            E('COVERAGE_TECHNICAL', 'coverage.technical_items[%d]: "%s" אינו נימוק.' % (k, reason[:40]))
        if not isinstance(it.get('refs'), list) or not it.get('refs'):
            E('COVERAGE_TECHNICAL', 'coverage.technical_items[%d]: חסר refs[] (איזה סעיף).' % k)
        else:
            refs_total += len(it['refs'])
    if isinstance(tech_n, int) and items and refs_total != tech_n:
        E('COVERAGE_TECHNICAL', 'technical_items מכסים %d סעיפים, ו-technical_units הוא %d.' % (refs_total, tech_n))
    # אין נושא "ברירת מחדל"
    method = ' '.join(str(x or '') for x in (cov.get('method'), (inventory or {}).get('method')))
    hit = default_topic_hit(method)
    if cov.get('default_rule_id') or hit:
        E('COVERAGE_DEFAULT_TOPIC', 'המלאי שייך יחידות שלא זוהה להן נושא לנושא אחד ("%s"). כל יחידה ממופה לנושא '
          'משלה, לנושא חדש שנגזר מהקורפוס, ל"סעיף ייחודי" או לקוד טכני.' % (cov.get('default_rule_id') or hit))
    # החלוקה לפי נושא ולפי הסכם: מהבלוק, או מהמלאי כשנמסר
    calc = coverage_from_inventory(model, inventory, extract) if inventory else None
    by_rule = cov.get('by_rule') if isinstance(cov.get('by_rule'), dict) else (calc or {}).get('by_rule')
    if by_rule is None:
        E('COVERAGE_BY_RULE', 'coverage.by_rule{} חסר, ולא נמסר מלאי: אי אפשר לבדוק אם נושא אחד קיבל חלק חריג '
          'מהיחידות.')
    else:
        for rid in by_rule:
            if rid not in rids:
                E('COVERAGE_BY_RULE', 'coverage.by_rule: הכלל %s אינו ב-rules[].' % rid, rid)
        s = sum(v for v in by_rule.values() if isinstance(v, int))
        if isinstance(mapped, int) and s != mapped:
            E('COVERAGE_BY_RULE', 'coverage.by_rule מסתכם ב-%d, ו-topic_units הוא %d.' % (s, mapped))
        n_topics = len(rids)
        if s >= CONCENTRATION_MIN_UNITS and n_topics >= 4:
            rid, top = max(by_rule.items(), key=lambda kv: kv[1] if isinstance(kv[1], int) else 0)
            limit = max(0.25, 3.0 / n_topics)
            note = cov.get('concentration_note') if isinstance(cov.get('concentration_note'), dict) else {}
            if top > s * limit and not (note.get('rule_id') == rid and str(note.get('reason') or '').strip()):
                E('COVERAGE_CONCENTRATION', 'הנושא %s קיבל %d מתוך %d היחידות הממופות (%d%%), מעל %d%% ב-%d נושאים. '
                  'זה סימן לשיוך ברירת מחדל: מפו את היחידות לנושאים שלהן, או נמקו ב-coverage.concentration_note.'
                  % (rid, top, s, round(100.0 * top / s), round(100 * limit), n_topics), rid)
    rows = cov.get('by_agreement') if isinstance(cov.get('by_agreement'), list) else (calc or {}).get('by_agreement')
    included = [s.get('source_id') for s in model.get('source_log') or [] if _corpus_source(model, s)]
    if rows is None:
        E('COVERAGE_BY_AGREEMENT', 'coverage.by_agreement[] חסר, ולא נמסר מלאי: אין פירוט לפי הסכם.')
        rows = []
    seen = {r.get('source_id'): r for r in rows if isinstance(r, dict)}
    for sid in included:
        r = seen.get(sid)
        if r is None or not r.get('units'):
            if not str((r or {}).get('note') or '').strip():
                E('COVERAGE_BY_AGREEMENT', 'ההסכם %s נכלל בקורפוס, ואין לו אף יחידה במלאי.' % sid)
    # מול המלאי והחילוץ: הבלוק במודל הוא הספירה, וכל פסקה מהותית בתוך יחידה
    if calc:
        if calc['unassigned_units']:
            E('COVERAGE_UNASSIGNED', '%d יחידות במלאי בלי נושא, קוד טכני, סימון ייחודי או סיבה (למשל %s).'
              % (calc['unassigned_units'], ', '.join(calc['_unassigned_refs'][:5])))
        for rid in calc['_unknown_rules']:
            E('COVERAGE_INVENTORY', 'המלאי מפנה לכלל %s שאינו ב-rules[].' % rid, rid)
        for k, old in (('units', total), ('topic_units', mapped), ('technical_units', tech_n),
                       ('unique_units', uniq_n), ('unmapped_units', unm_n)):
            if isinstance(old, int) and old != calc[k]:
                E('COVERAGE_INVENTORY', 'coverage.%s במודל הוא %d, ובמלאי %d.' % (k, old, calc[k]))
        for r in calc['by_agreement']:
            if r.get('extract_paragraphs') is None and extract:
                E('COVERAGE_EXTRACT', 'ההסכם %s אינו בקובץ החילוץ, ולכן אי אפשר לבדוק שכל סעיף בו כוסה.'
                  % r['source_id'])
            elif r.get('uncovered_paragraphs'):
                E('COVERAGE_PARAGRAPHS', 'בהסכם %s %d מתוך %d הפסקאות המהותיות אינן בתוך אף יחידה במלאי: זיהוי '
                  'הסעיפים חלקי.' % (r['source_id'], r['uncovered_paragraphs'], r['extract_paragraphs']))
    return out


def _has_source(v):
    if isinstance(v, dict):
        return any(str(v.get(k) or '').strip() for k in ('agreement', 'clause', 'citation_id'))
    return bool(str(v or '').strip())


def department_findings(model):
    """המחלקות האחראיות ושיוך החיובים: שדות רשות, ונבדקים רק כשהם קיימים (ps1-playbook-identity-scope.md)."""
    out = []
    keys = ('responsible_departments', 'departments_proposed', 'obligation_assignments')
    if not any(k in model for k in keys):
        return out
    resp = model.get('responsible_departments')
    prop = model.get('departments_proposed')
    asg = model.get('obligation_assignments')
    for k, v in (('responsible_departments', resp), ('departments_proposed', prop), ('obligation_assignments', asg)):
        if v is not None and not isinstance(v, list):
            _f(out, 'DEPT_SHAPE', 'error', '%s: נדרשת רשימה.' % k)
    resp = resp if isinstance(resp, list) else []
    prop = prop if isinstance(prop, list) else []
    asg = asg if isinstance(asg, list) else []
    names = set()
    for i, n in enumerate(resp):
        if not isinstance(n, str) or not n.strip():
            _f(out, 'DEPT_SHAPE', 'error', 'responsible_departments[%d]: נדרש שם מחלקה (מחרוזת).' % i)
        else:
            names.add(n.strip())
    proposed = set()
    for i, x in enumerate(prop):
        if not isinstance(x, dict) or not str(x.get('name') or '').strip():
            _f(out, 'DEPT_SHAPE', 'error', 'departments_proposed[%d]: נדרש {name, quote, source}.' % i)
            continue
        proposed.add(x['name'].strip())
        if not str(x.get('quote') or '').strip():
            _f(out, 'DEPT_PROPOSED_NO_QUOTE', 'error', 'departments_proposed[%d] (%s): מחלקה מוצעת נשענת על ציטוט '
               'מההסכם שמייחס לה תפקיד.' % (i, x['name']))
        if not _has_source(x.get('source')):
            _f(out, 'DEPT_NO_SOURCE', 'error', 'departments_proposed[%d] (%s): חסרה הפניית מקור (הסכם וסעיף).'
               % (i, x['name']))
    seen = {}
    for i, x in enumerate(asg):
        if not isinstance(x, dict):
            _f(out, 'DEPT_SHAPE', 'error', 'obligation_assignments[%d]: נדרש {type, department, source, '
               'needs_verification}.' % i)
            continue
        typ = x.get('type')
        if typ not in OBLIGATION_TYPES:
            _f(out, 'DEPT_TYPE', 'error', 'obligation_assignments[%d]: type "%s" אינו אחד מ-17 סוגי החובה של מרשם '
               'ההתחייבויות (%s).' % (i, typ, ', '.join(OBLIGATION_TYPES)))
        elif typ in seen:
            _f(out, 'DEPT_TYPE_DUPLICATE', 'error', 'obligation_assignments[%d]: הסוג "%s" כבר משויך (שורה %d). '
               'שורה אחת לכל סוג חיוב, כדי שהמרשם ימצא מחלקה אחת.' % (i, typ, seen[typ]))
        else:
            seen[typ] = i
        dept = str(x.get('department') or '').strip()
        nv = x.get('needs_verification')
        if nv is not None and not isinstance(nv, bool):
            _f(out, 'DEPT_SHAPE', 'error', 'obligation_assignments[%d].needs_verification: true או false.' % i)
        if not dept:
            _f(out, 'DEPT_SHAPE', 'error', 'obligation_assignments[%d]: חסרה מחלקה.' % i)
        elif dept not in names:
            if dept in proposed and nv is True:
                pass
            elif dept in proposed:
                _f(out, 'DEPT_UNKNOWN', 'error', 'obligation_assignments[%d]: המחלקה "%s" הוצעה ועוד לא נקבעה, '
                   'ולכן השיוך מסומן needs_verification: true.' % (i, dept))
            else:
                _f(out, 'DEPT_UNKNOWN', 'error', 'obligation_assignments[%d]: המחלקה "%s" אינה ב-'
                   'responsible_departments.' % (i, dept))
        if not _has_source(x.get('source')):
            _f(out, 'DEPT_NO_SOURCE', 'error', 'obligation_assignments[%d]: חסרה הפניית מקור (הסכם וסעיף).' % i)
    return out


# ---- מקורות: פסיקה רק ממחבר סגור, ודין רק מהרשימה המאושרת (הכללים המשותפים 1.1, 2.2) ----
URL_KEYS = ('url', 'final_url', 'source_url', 'link')
# שדות שהם ציטוט מילולי מהסכמי הלקוח: הסכם יכול לצטט פסק דין, וזה אינו פסיקה שהבונה הביא
QUOTE_KEYS = {'quote', 'quotes', 'excerpt', 'verbatim', 'source_quote', 'clause_text', 'text_quote', 'evidence',
              'source_log', 'coverage', 'agreement_exceptions', 'observed_alternatives', 'search_log', 'case_law',
              'case_law_access', 'holding_quote', 'citations', 'corpus', 'inventory', 'produced_with'}


def _approved_rules(path=None):
    """כללי הדומיינים המאושרים מ-risk.validate_register (מקורות-מאושרים.json, או רשימת הנפילה שבקוד), או None
    כשהמודול אינו זמין. מקבל גם צורה שבה approved_domains מחזיר רשימה ולא זוג."""
    try:
        from risk.validate_register import approved_domains
    except ImportError:
        return None
    try:
        got = approved_domains(path) if path else approved_domains()
    except TypeError:
        got = approved_domains()
    if isinstance(got, tuple) and len(got) == 2 and isinstance(got[0], (tuple, list)):
        got = got[0]   # (כללים, הנתיב שנקרא)
    return got if isinstance(got, tuple) else tuple(got or ())   # Rules נשמר כמו שהוא, עם כללי הדחייה (refuse)


def _domain_ok(url, rules):
    try:
        from risk.validate_register import domain_ok
        return domain_ok(url, rules)
    except ImportError:
        host = re.sub(r'^[a-z]+://', '', url or '', flags=re.I).split('/')[0].split(':')[0].lower()
        return any(host == r.split('/')[0] or host.endswith('.' + r.split('/')[0]) for r in rules)


def _case_law_url(url):
    try:
        from common.case_law import case_law_url
    except ImportError:
        return None
    return case_law_url(url)


def _urls(obj, path=''):
    """(נתיב, כתובת) לכל כתובת במבנה."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = '%s.%s' % (path, k) if path else k
            if k in URL_KEYS and isinstance(v, str) and re.match(r'(https?://|www\.)', v.strip(), re.I):
                yield p, v.strip()
            elif isinstance(v, (dict, list)):
                yield from _urls(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _urls(v, '%s[%d]' % (path, i))


def source_findings(model, approved_sources=None):
    """SOURCE_CASE_LAW: כתובת של אתר בית משפט, מאגר פסיקה או מדור פסיקה בכל מקור (regulatory_research,
    external_sources, market_research.source_refs, statutory_override). SOURCE_NOT_APPROVED: מקור משפטי או
    רגולטורי (regulatory_research, external_sources עם ref של L או X, statutory_override) שאינו ברשימת המקורות
    המאושרים, בדומיין ובנתיב. SOURCE_LIST_UNAVAILABLE (אזהרה): risk.validate_register אינו זמין."""
    out = []
    legal, market = [], []
    legal += list(_urls(model.get('regulatory_research') or {}, 'regulatory_research'))
    for i, s in enumerate(model.get('external_sources') or []):
        if not isinstance(s, dict):
            continue
        hits = list(_urls(s, 'external_sources[%d]' % i))
        (legal if str(s.get('ref') or s.get('source_id') or '').startswith(('L', 'X')) else market).extend(hits)
    market += list(_urls((model.get('market_research') or {}).get('source_refs') or [], 'market_research.source_refs'))
    for r in model.get('rules') or []:
        legal += list(_urls(r.get('statutory_override') or [], '%s.statutory_override' % r.get('rule_id')))
    for where, url in legal + market:
        why = _case_law_url(url)
        if why:
            _f(out, 'SOURCE_CASE_LAW', 'error', '%s: %s' % (where, why))
    if not legal:
        return out
    rules = _approved_rules(approved_sources)
    if not rules:
        # בלי קובץ המקורות המאושרים אין רשימה לבדוק מולה (אין רשימת נפילה): אזהרה, ו-b5-outputs.md מעביר תמיד
        # --approved-sources
        _f(out, 'SOURCE_LIST_UNAVAILABLE', 'warning', 'רשימת המקורות המאושרים לא נטענה (--approved-sources או '
           'AREO_APPROVED_SOURCES): המקורות המשפטיים לא נבדקו מולה.')
        return out
    for where, url in legal:
        if not _case_law_url(url) and not _domain_ok(url, rules):
            _f(out, 'SOURCE_NOT_APPROVED', 'error', '%s: %s אינו ברשימת המקורות המאושרים (approved-regulatory-sources.md,'
               ' מקורות-מאושרים.json). דין ורגולציה רק משם; אחרת "טעון בדיקה משפטית".' % (where, url))
    return out


def _texts(obj, path=''):
    """(נתיב, מחרוזת) לכל מחרוזת, בלי שדות של ציטוט מילולי מההסכמים (QUOTE_KEYS)."""
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k in QUOTE_KEYS:
                continue
            yield from _texts(v, '%s.%s' % (path, k) if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _texts(v, '%s[%d]' % (path, i))


def case_law_connector(model):
    cla = model.get('case_law_access')
    return (cla.get('connector') if isinstance(cla, dict) else None) or None


def case_law_findings(model, core=None):
    """פסיקה בתוצרי הבונה (playbook-qa.md, בדיקה 7).
    בלי מחבר (case_law_access.connector הוא null): CASE_LAW_NO_CONNECTOR על case_law[] לא ריק או על שכבת
    case_law ב-legal_basis_layers[]; CASE_LAW_TEXT על אזכור פסק דין (common.case_law) בנימוק, בעמדות, בנוסחים,
    בשאלות ובכל טקסט יוצא של המודל או של הגרעין. עם מחבר: CASE_LAW_NO_REF על פסק דין בלי retrieval_ref, ו-
    CASE_LAW_IN_WORDING על אזכור פסיקה בנוסח מוצע, בנוסח נסיגה או בגרעין."""
    out = []
    conn = case_law_connector(model)
    try:
        from common.case_law import case_law_hits
    except ImportError:
        case_law_hits = None
    for r in model.get('rules') or []:
        rid = r.get('rule_id')
        cl = [c for c in r.get('case_law') or [] if c]
        layers = [x for x in r.get('legal_basis_layers') or [] if isinstance(x, dict) and
                  (x.get('layer') == 'case_law' or x.get('case_law_ref'))]
        if not conn and (cl or layers):
            _f(out, 'CASE_LAW_NO_CONNECTOR', 'error', 'פסיקה בכלל (%s) בלי מחבר פסיקה סגור (case_law_access.connector '
               'הוא null). פסיקה רק ממחבר שהלקוח חיבר; אחרת "טעון בדיקה משפטית".'
               % ('case_law[]' if cl else 'legal_basis_layers: case_law'), rid)
        if conn:
            for c in cl:
                if not (isinstance(c, dict) and c.get('retrieval_ref')):
                    _f(out, 'CASE_LAW_NO_REF', 'error', 'פסק דין בלי retrieval_ref: רק מה שהמחבר החזיר בהרצה הזו.', rid)
    if case_law_hits is None:
        return out
    if not conn:
        for name, holder in (('model', model), ('core', core)):
            for where, txt in _texts(holder or {}, name):
                hits = case_law_hits(txt)
                if hits:
                    _f(out, 'CASE_LAW_TEXT', 'error', '%s: אזכור פסיקה בלי מחבר פסיקה סגור (%s). פסיקה לא נכתבת, '
                       'לא נקראת בשם ולא מתוארת; הסעיף מסומן "טעון בדיקה משפטית".' % (where, '; '.join(hits[:2])))
    else:
        for r in model.get('rules') or []:
            for _, track, t in _iter_tracks(r):
                for text, _lang in _wordings(t, track):
                    if case_law_hits(text):
                        _f(out, 'CASE_LAW_IN_WORDING', 'error', 'אזכור פסיקה בנוסח: פסיקה אינה נכנסת לנוסח מוצע או '
                           'לנוסח נסיגה.', r.get('rule_id'), track)
        for where, txt in _texts(core or {}, 'core'):
            if case_law_hits(txt):
                _f(out, 'CASE_LAW_IN_WORDING', 'error', '%s: פסיקה אינה נכנסת לגרעין.' % where)
    return out


def jurisdiction_findings(model):
    """GOVERNING_LAWS_MISSING (אזהרה): אין scope_summary.governing_laws[]. OVERRIDE_NO_JURISDICTION (אזהרה): חובה
    בדין או שכבת statute בלי jurisdiction, ולכן הרכיבים הקוראים אינם יכולים להחיל אותה רק בדין הנכון."""
    out = []
    if not (model.get('scope_summary') or {}).get('governing_laws'):
        _f(out, 'GOVERNING_LAWS_MISSING', 'warning', 'חסר scope_summary.governing_laws[] (קודים: IL, GB-EAW, US-NY, '
           'DE), מההסכמים של הסוג.')
    for r in model.get('rules') or []:
        for so in r.get('statutory_override') or []:
            if isinstance(so, dict) and not str(so.get('jurisdiction') or '').strip():
                _f(out, 'OVERRIDE_NO_JURISDICTION', 'warning', 'חובה בדין (%s) בלי jurisdiction.'
                   % (so.get('statute') or '?'), r.get('rule_id'))
        for x in r.get('legal_basis_layers') or []:
            if isinstance(x, dict) and x.get('layer') == 'statute' and not str(x.get('jurisdiction') or '').strip():
                _f(out, 'OVERRIDE_NO_JURISDICTION', 'warning', 'שכבת statute (%s) בלי jurisdiction.'
                   % (x.get('statute') or '?'), r.get('rule_id'))
    return out


# ---- ניתוח משפטי ונימוק: נימוק שאינו תבנית, שלד משפטי, נסיגה שתואמת את התיאור ----
# יחידות שמזוהות בטקסט ליד מספר, בעברית ובאנגלית (בדיקת נוסח שאינו תואם את תיאורו)
UNIT_WORDS = {
    'business_days': r'ימי\s+עבודה|ימי\s+עסקים|business\s+days?|working\s+days?',
    'days': r'ימים|יום|days?',
    'hours': r'שעות|שעה|hours?',
    'months': r'החודשים|חודשים|חודשי|חודש|months?',
    'years': r'השנים|שנים|שנה|years?',
    'percent': r'%|אחוזים|אחוז|percent',
    'times_per_year': r'פעמים\s+בשנה|פעם\s+בשנה|times\s+(?:a|per)\s+year|per\s+year|annually',
}
_NUM_UNIT = re.compile(r'(?<![\d.,])(\d+(?:[.,]\d+)?)\s*(?:\)\s*)?(?:[-\s]?(?:calendar\s+)?)(' +
                       '|'.join('(?:%s)' % v for v in UNIT_WORDS.values()) + r')(?![\w])', re.I)
LEGAL_CORE_FIELDS = ('governing_rule', 'decisive_distinction', 'consequence_for_company', 'interplay', 'verification')
LEGAL_CORE_VERIFY = ('statute_text', 'case_law_connector', 'legal_review_required', 'expert_assessment')
LEGAL_KINDS = ('משפטי', 'legal')
REVIEW_LABELS = ('טעון בדיקה משפטית', 'Needs legal review', 'Legal review required', 'טעון אימות',
                 'Needs verification')
# שדות הנימוק שנכתבים לכל כלל, ואסור שיחזרו כמעט מילה במילה בין כללים (תבנית שהודבקה)
RATIONALE_FIELDS = ('executive_policy_rationale', 'protected_interest_and_clause_purpose',
                    'legal_risk_and_legal_framework', 'contractual_risk_allocation_mechanism',
                    'company_role_and_policy_fit', 'business_operational_impact', 'green_boundary_rationale',
                    'yellow_boundary_rationale', 'red_boundary_rationale', 'tradeoff_statement')
TRACK_TEXT_FIELDS = ('company_effect', 'comments', 'notes')
NEAR_DUP_RATIO = 0.9
NEAR_DUP_MIN_CHARS = 40
NEAR_DUP_ERROR_RULES = 3
PUBLIC_KINDS = ('public_body', 'government_company', 'university')
# הסרה של סמכות שגוף ציבורי אינו יכול לוותר עליה: סיום מטעמי ציבור או תקציב, והחלפת הצד בלי הליך תחרותי
PUBLIC_POWER_REMOVED = re.compile(
    r'(?:אינו|אינה|לא\s+יהיה|לא\s+תהיה)\s+רשאי(?:ת)?\s+(?:לסיים|לבטל|להביא\s+את\s+ההסכם\s+לידי\s+סיום)|'
    r'אין\s+(?:ל[א-ת]+\s+)?זכות\s+(?:סיום|ביטול)|'
    r'(?:shall|will|may)\s+(?:have\s+)?no(?:t)?\s+(?:right\s+to\s+)?terminat|may\s+not\s+terminate|'
    r'no\s+right\s+(?:of|to)\s+terminat|'
    r'צד\s+חלופי|substitute\s+party|replacement\s+party',
    re.I)


def _norm_text(s):
    s = re.sub(r'[\d]+', '0', str(s or '').casefold())
    return ' '.join(re.findall(r'\w+', s))


def _num_units(text):
    """{unit: {numbers}} מהטקסט: מספר וליד היחידה (14 days, 30 יום, twenty-four (24) hours)."""
    out = {}
    for m in _NUM_UNIT.finditer(str(text or '')):
        word = m.group(2)
        unit = next((k for k, rx in UNIT_WORDS.items() if re.fullmatch(rx, word, re.I)), None)
        if unit:
            out.setdefault(unit, set()).add(float(m.group(1).replace(',', '.')))
    return out


def home_countries(model):
    """המדינות של הדין החל על הסכמי הסוג (scope_summary.governing_laws[]); בלעדיהן, מדינת ההתאגדות של הישות החותמת.
    רשימה ריקה כשאין אף אחד מהם: אין הנחה של מדינה."""
    homes = governing_countries(model)
    if homes:
        return homes
    ent = (model.get('scope_summary') or {}).get('contracting_entity')
    ents = ent if isinstance(ent, list) else [ent]
    return list(dict.fromkeys(c for c in (country_code(e.get('incorporation_country')) for e in ents
                                          if isinstance(e, dict)) if c))


# ---- מקור מורשה: כשמחקר הרשת הותר ולא נמצא מקור, ההערה גלויה והפלייבוק לא נחסם (כללים מייסדים 3 ו-5) ----
NO_SOURCE_NOTE = {'he': 'AREO לא מצאה מקור מורשה לנקודה זו',
                  'en': 'AREO did not find an approved source for this point'}
RESEARCH_RAN = ('Performed', 'Completed', 'Partial')


def no_source_text(lang='he'):
    return NO_SOURCE_NOTE['en' if str(lang or '').lower().startswith('en') else 'he']


def research_permitted(model):
    """True כשמחקר רשת הותר ורץ בפלייבוק הזה: מחקר עומק שהלקוח בחר (regulatory_research), או פלייבוק שנבנה לפי הרשת
    והשוק לבקשת הלקוח (market_research). בלי אחד מהם אין מחקר, ואין מה לומר על מקור שלא נמצא."""
    if not isinstance(model, dict):
        return False
    for key in ('regulatory_research', 'market_research'):
        blk = model.get(key)
        if isinstance(blk, dict) and blk.get('status') in RESEARCH_RAN:
            return True
    return False


def _open_legal_point(rule):
    """נושא שיש בו שאלה בדין שנשארה פתוחה: נושא משפטי, או שכבה "טעון בדיקה משפטית", בלי מקור מורשה שנקרא."""
    if rule.get('regulatory_status') == 'ApplicableSourcesFound' or rule.get('regulatory_sources'):
        return False
    layers = [x for x in rule.get('legal_basis_layers') or [] if isinstance(x, dict)]
    if any(x.get('layer') == 'statute' for x in layers):
        return False
    legal_kind = str(rule.get('clause_kind') or '') in LEGAL_KINDS
    return legal_kind or any(x.get('layer') == 'legal_review_required' for x in layers) or \
        bool(rule.get('legal_review_required'))


def no_source_notes(model):
    """[(rule_id, topic_name, has_note)] לכל נושא שמחקר הרשת הותר בו ולא נמצא לו מקור מורשה."""
    if not research_permitted(model):
        return []
    out = []
    for r in model.get('rules') or []:
        if isinstance(r, dict) and _open_legal_point(r):
            note = str(r.get('no_source_note') or '')
            out.append((r.get('rule_id'), r.get('topic_name') or '', any(t in note for t in NO_SOURCE_NOTE.values())))
    return out


def no_source_findings(model):
    """NO_SOURCE_NOTE (אזהרה, לעולם אינה חוסמת): נושא עם שאלה בדין שלא נמצא לה מקור מורשה, ובלי ההערה הגלויה."""
    out = []
    lang = (model or {}).get('output_language') or 'he'
    for rid, name, has in no_source_notes(model):
        if not has:
            _f(out, 'NO_SOURCE_NOTE', 'warning', 'הנושא "%s": מחקר הרשת הותר ולא נמצא מקור מורשה. רשמו ב-no_source_note '
               '"%s" (ולא ממלאים את החסר מהזיכרון).' % (name, no_source_text(lang)), rid)
    return out


# ---- המקור מוצג: כל עמדה שנגזרה ממסמכי הלקוח מציגה את ההסכם והסעיף שעליהם נשענה (כלל מייסד 12) ----
# מסלולים שנשענים על מסמכי הלקוח, לפי basis (ps3-rule-and-evidence.md). client_answer, market_standard ו-areo_proposal
# אינם מסמך בתיקייה של הלקוח, ולכן אינם כאן
DOCUMENT_BASES = {
    'green': ('template', 'own_paper_repeated', 'documents_majority', 'company_request'),
    'yellow': ('established', 'single', 'offered_unexecuted'),
    'red': ('company_source', 'struck', 'rejected_comment', 'never_accepted', 'bid_condition'),
}


def _evidence_index(rule, model):
    """{מזהה: ראיה} לפי evidence_id בכלל (ובווריאנטים) ו-citation_id ב-citations[] של המודל."""
    idx = {}
    for e in list(rule.get('evidence') or []) + [x for v in rule.get('segment_variants') or []
                                               if isinstance(v, dict) for x in v.get('evidence') or []]:
        if isinstance(e, dict):
            for k in ('evidence_id', 'citation_id'):
                if e.get(k):
                    idx.setdefault(str(e[k]), e)
    for c in model.get('citations') or []:
        if isinstance(c, dict) and c.get('citation_id'):
            idx.setdefault(str(c['citation_id']), c)
    return idx


def position_sources(rule, model, t):
    """[{evidence_id, source_id, agreement, clause}] של עמדה אחת: ההסכם (source_log) והסעיף שעליהם basis_refs נשען.
    ref שאינו נפתר לראיה מדולג (ממצא ב-position_source_findings). משמש גם את גרעין ההפעלה ואת התצוגות."""
    idx = _evidence_index(rule, model)
    logs = {s.get('source_id'): s for s in model.get('source_log') or [] if isinstance(s, dict)}
    out = []
    for ref in t.get('basis_refs') or []:
        e = idx.get(str(ref))
        if not e:
            continue
        sid = str(e.get('source_ref') or '').split('#')[0]
        s = logs.get(sid) or {}
        out.append({'evidence_id': str(ref), 'source_id': sid,
                    'agreement': s.get('short_name') or s.get('title') or s.get('file') or sid,
                    'clause': str(e.get('clause_ref') or '').strip()})
    return out


def position_source_findings(model):
    """SOURCE_NOT_SHOWN: עמדה שנגזרה ממסמכי הלקוח (DOCUMENT_BASES) שאין לה basis_refs, או ש-ref אינו נפתר לראיה, או
    שבראיה חסר ההסכם (source_ref) או הסעיף (clause_ref), או שההסכם אינו ב-source_log. כל מסלול, בכל כלל ובכל וריאנט."""
    out = []
    logs = {s.get('source_id') for s in model.get('source_log') or [] if isinstance(s, dict)}
    for r in model.get('rules') or []:
        if not isinstance(r, dict):
            continue
        idx = _evidence_index(r, model)
        for seg, track, t in _iter_tracks(r):
            if not t or t.get('basis') not in DOCUMENT_BASES.get(track, ()):
                continue
            where = '%s%s' % (track, ' (%s)' % seg if seg else '')
            refs = [x for x in t.get('basis_refs') or [] if str(x).strip()]
            if not refs:
                _f(out, 'SOURCE_NOT_SHOWN', 'error', 'עמדת %s נשענת על מסמכי הלקוח (%s) ואין לה basis_refs: איזה '
                   'הסכם ואיזה סעיף?' % (where, t.get('basis')), r.get('rule_id'), track)
                continue
            for ref in refs:
                e = idx.get(str(ref))
                if e is None:
                    _f(out, 'SOURCE_NOT_SHOWN', 'error', 'עמדת %s: basis_refs "%s" אינו ראיה ברשימת הראיות של הכלל.'
                       % (where, ref), r.get('rule_id'), track)
                    continue
                sid = str(e.get('source_ref') or '').split('#')[0]
                if not sid:
                    _f(out, 'SOURCE_NOT_SHOWN', 'error', 'עמדת %s: בראיה %s חסר ההסכם (source_ref).' % (where, ref),
                       r.get('rule_id'), track)
                elif logs and sid not in logs:
                    _f(out, 'SOURCE_NOT_SHOWN', 'error', 'עמדת %s: ההסכם %s של הראיה %s אינו ב-source_log.'
                       % (where, sid, ref), r.get('rule_id'), track)
                if not str(e.get('clause_ref') or '').strip():
                    _f(out, 'SOURCE_NOT_SHOWN', 'error', 'עמדת %s: בראיה %s חסר הסעיף (clause_ref).' % (where, ref),
                       r.get('rule_id'), track)
    return out


# ---- ספר הכיסוי: סעיפים = סעיפים עם מדיניות + "אין מדיניות שאפשר לחלץ" + ייחודיים שממתינים (כלל מייסד 14) ----
def coverage_ledger(model):
    """הספר, מספרים בלבד: clauses (כל הסעיפים בכל ההסכמים), with_policy (ממופים לנושא), no_extractable_policy
    (טכניים ושלא מופו, כולם רשומים במפורש), unique_pending (ייחודיים, ממתינים להכרעה בתור), unassigned (בלי כלום),
    listed_no_policy (כמה מהם נרשמו בפועל ברשימה המפורשת), agreements (מספר ההסכמים) ו-balanced.
    None כשאין coverage."""
    cov = (model or {}).get('coverage')
    if not isinstance(cov, dict):
        return None

    def num(n, a):
        v = _cov_num(cov, n, a)
        return v if isinstance(v, int) and not isinstance(v, bool) else 0

    total, mapped = num('units', 'units_total'), num('topic_units', 'units_mapped')
    tech, unm = num('technical_units', 'units_technical'), num('unmapped_units', 'units_unmapped')
    uniq, unassigned = num('unique_units', 'units_unique'), num('unassigned_units', 'units_unassigned')
    items = cov.get('technical_items') if isinstance(cov.get('technical_items'), list) else []
    listed = sum(len(i.get('refs') or []) for i in items if isinstance(i, dict)) + \
        len(cov.get('unmapped') if isinstance(cov.get('unmapped'), list) else [])
    rows = cov.get('by_agreement') if isinstance(cov.get('by_agreement'), list) else []
    return {'clauses': total, 'with_policy': mapped, 'no_extractable_policy': tech + unm, 'unique_pending': uniq,
            'unassigned': unassigned, 'listed_no_policy': listed, 'agreements': len(rows),
            'balanced': total == mapped + tech + unm + uniq + unassigned and unassigned == 0
            and listed == tech + unm}


def coverage_ledger_findings(model):
    """COVERAGE_LEDGER: הספר אינו מסתכם (סעיפים שונים מסכום החלקים, סעיף בלי שיוך, או סעיף "בלי מדיניות" שלא נרשם
    במפורש), או שסכום הסעיפים לפי הסכם שונה מהסך. COVERAGE_LEDGER_AGREEMENT: שורת הסכם שאינה מסתכמת."""
    out = []
    led = coverage_ledger(model)
    if led is None:
        return out          # coverage_findings כבר אומר COVERAGE_MISSING
    parts_sum = led['with_policy'] + led['no_extractable_policy'] + led['unique_pending'] + led['unassigned']
    if led['clauses'] != parts_sum:
        _f(out, 'COVERAGE_LEDGER', 'error', 'ספר הכיסוי אינו מסתכם: %d סעיפים, ו-%d עם מדיניות + %d בלי מדיניות שאפשר '
           'לחלץ + %d ייחודיים + %d בלי שיוך.' % (led['clauses'], led['with_policy'], led['no_extractable_policy'],
                                                    led['unique_pending'], led['unassigned']))
    elif led['unassigned']:
        _f(out, 'COVERAGE_LEDGER', 'error', '%d סעיפים בלי מדיניות ובלי רישום מפורש כ"אין מדיניות שאפשר לחלץ".'
           % led['unassigned'])
    if led['listed_no_policy'] != led['no_extractable_policy']:
        _f(out, 'COVERAGE_LEDGER', 'error', '%d סעיפים הוגדרו "אין מדיניות שאפשר לחלץ", ו-%d מהם רשומים במפורש '
           '(technical_items[].refs ו-unmapped[]). כל סעיף כזה נרשם בשמו.' % (led['no_extractable_policy'],
                                                                              led['listed_no_policy']))
    rows = [r for r in (model.get('coverage') or {}).get('by_agreement') or [] if isinstance(r, dict)]
    if rows and all(isinstance(r.get('units'), int) for r in rows):
        if sum(r['units'] for r in rows) != led['clauses']:
            _f(out, 'COVERAGE_LEDGER', 'error', 'סכום הסעיפים לפי הסכם הוא %d, והסך הכול %d.'
               % (sum(r['units'] for r in rows), led['clauses']))
    for r in rows:
        parts = [r.get(k) for k in ('mapped', 'technical', 'unique', 'unmapped', 'unassigned')]
        if all(isinstance(x, int) for x in parts[:4]) and isinstance(r.get('units'), int):
            if sum(x for x in parts if isinstance(x, int)) != r['units']:
                _f(out, 'COVERAGE_LEDGER_AGREEMENT', 'error', 'בהסכם %s: %d סעיפים, ו-%d ממופים + %d טכניים + %d '
                   'ייחודיים + %d לא ממופים + %d בלי שיוך.' % (r.get('source_id'), r['units'], parts[0], parts[1],
                                                             parts[2], parts[3], parts[4] or 0))
    return out


def coverage_ledger_lines(model, lang='he'):
    """שורה ללקוח על הספר, בקול של מנהל מוצר: התוצאה קודם. [] כשאין coverage."""
    led = coverage_ledger(model)
    if not led:
        return []
    if str(lang or '').lower().startswith('en'):
        line = 'We went through all %d clauses in %d agreements. %d have a policy.' % (
            led['clauses'], led['agreements'], led['with_policy'])
        if led['no_extractable_policy']:
            line += ' %d are listed one by one as having no policy to extract.' % led['no_extractable_policy']
        if led['unique_pending']:
            line += ' %d unique clauses wait for your decision.' % led['unique_pending']
    else:
        line = 'עברנו על כל %d הסעיפים ב-%d הסכמים. ל-%d מהם יש מדיניות.' % (
            led['clauses'], led['agreements'], led['with_policy'])
        if led['no_extractable_policy']:
            line += ' %d רשומים אחד אחד כסעיפים שאין להם מדיניות שאפשר לחלץ.' % led['no_extractable_policy']
        if led['unique_pending']:
            line += ' %d סעיפים ייחודיים ממתינים להכרעה שלכם.' % led['unique_pending']
    return [line]


def sufficiency_findings(model):
    """הבדיקה של playbook/sufficiency.py כממצאי מאמת: SUFFICIENCY_NOT_ASKED, SUFFICIENCY_STALE."""
    try:
        from playbook import sufficiency as SU
    except ImportError:  # pragma: no cover
        return []
    out = []
    for code, sev, msg in SU.findings(model):
        _f(out, code, sev, msg)
    return out

def _dup_groups(items):
    """[(text, rule_id)] -> קבוצות של כללים שהטקסט שלהם כמעט זהה (יחס דמיון מעל NEAR_DUP_RATIO)."""
    import difflib
    groups = []
    for text, rid in items:
        n = _norm_text(text)
        if len(n) < NEAR_DUP_MIN_CHARS:
            continue
        for g in groups:
            if g['rule_ids'][-1] != rid and difflib.SequenceMatcher(None, g['norm'], n).ratio() >= NEAR_DUP_RATIO:
                if rid not in g['rule_ids']:
                    g['rule_ids'].append(rid)
                break
        else:
            groups.append({'norm': n, 'text': str(text), 'rule_ids': [rid]})
    return [g for g in groups if len(g['rule_ids']) > 1]


def rationale_findings(model):
    """RATIONALE_DUPLICATE: אותו נימוק, או אותה שורת השפעה על החברה או הערת מסלול, כמעט מילה במילה (דמיון מעל 90%
    אחרי נרמול מספרים ופיסוק) ב-3 כללים או יותר (error), או בשניים (warning). שדה כזה נכתב לכל כלל, או נמחק.
    LEGAL_CORE_MISSING: כלל ש-clause_kind שלו משפטי בלי שלד משפטי מלא (legal_core: governing_rule,
    decisive_distinction, consequence_for_company, interplay, verification). LEGAL_CORE_REVIEW_ONLY: governing_rule
    שאינו אלא התווית "טעון בדיקה משפטית", בלי מה שמעורר את השאלה. LEGAL_CORE_STATUTE: verification: statute_text בלי
    שכבת statute עם סעיף ב-legal_basis_layers[]."""
    out = []
    rules = [r for r in model.get('rules') or [] if isinstance(r, dict)]
    fields = {}
    for r in rules:
        rid = r.get('rule_id')
        pr = r.get('policy_rationale') if isinstance(r.get('policy_rationale'), dict) else {}
        for k in RATIONALE_FIELDS:
            if isinstance(pr.get(k), str):
                fields.setdefault('policy_rationale.' + k, []).append((pr[k], rid))
        lc = r.get('legal_core') if isinstance(r.get('legal_core'), dict) else {}
        for k in ('decisive_distinction', 'consequence_for_company'):
            if isinstance(lc.get(k), str):
                fields.setdefault('legal_core.' + k, []).append((lc[k], rid))
        for track in TRACKS:
            t = (r.get('traffic_light') or {}).get(track) or {}
            for k in TRACK_TEXT_FIELDS:
                if isinstance(t.get(k), str):
                    fields.setdefault('%s.%s' % (track, k), []).append((t[k], rid))
            for role, txt in (t.get('role_effects') or {}).items() if isinstance(t.get('role_effects'), dict) else ():
                if isinstance(txt, str):
                    fields.setdefault('%s.role_effects.%s' % (track, role), []).append((txt, rid))
        for role, txt in (r.get('role_effects') or {}).items() if isinstance(r.get('role_effects'), dict) else ():
            if isinstance(txt, str):
                fields.setdefault('role_effects.' + str(role), []).append((txt, rid))
    for field, items in fields.items():
        for g in _dup_groups(items):
            n = len(g['rule_ids'])
            _f(out, 'RATIONALE_DUPLICATE', 'error' if n >= NEAR_DUP_ERROR_RULES else 'warning',
               '%s כמעט זהה ב-%d כללים (%s): "%s". נימוק ושורת השפעה נכתבים לכל כלל לפי הנושא, או נמחקים.'
               % (field, n, ', '.join(str(x) for x in g['rule_ids'][:8]), g['text'][:80]))
    for r in rules:
        rid = r.get('rule_id')
        if str(r.get('clause_kind') or '').strip().lower() not in LEGAL_KINDS:
            continue
        lc = r.get('legal_core') if isinstance(r.get('legal_core'), dict) else {}
        missing = [k for k in LEGAL_CORE_FIELDS if not str(lc.get(k) or '').strip()]
        if missing:
            _f(out, 'LEGAL_CORE_MISSING', 'error', 'כלל משפטי בלי שלד משפטי מלא: חסר %s (policy-rationale.md, '
               '"השלד המשפטי של כל נושא").' % ', '.join(missing), rid)
            continue
        if lc.get('verification') not in LEGAL_CORE_VERIFY:
            _f(out, 'LEGAL_CORE_MISSING', 'error', 'legal_core.verification "%s" (%s).'
               % (lc.get('verification'), ' | '.join(LEGAL_CORE_VERIFY)), rid)
        gr = str(lc.get('governing_rule') or '')
        rest = gr
        for lbl in REVIEW_LABELS:
            rest = rest.replace(lbl, '')
        if len(_norm_text(rest)) < 15:
            _f(out, 'LEGAL_CORE_REVIEW_ONLY', 'error', 'governing_rule הוא רק התווית: "טעון בדיקה משפטית" אינו מחליף '
               'ניתוח. כתוב את הכלל או המנגנון שקובע את התוצאה, ומה בהסכם מעורר את השאלה.', rid)
        if lc.get('verification') == 'statute_text' and not any(
                isinstance(x, dict) and x.get('layer') == 'statute' and x.get('section')
                for x in r.get('legal_basis_layers') or []):
            _f(out, 'LEGAL_CORE_STATUTE', 'error', 'verification: statute_text בלי שכבת statute עם סעיף ב-'
               'legal_basis_layers[].', rid)
    return out


def fallback_findings(model):
    """TRACK_WORDING_MISMATCH: התיאור של המסלול (position) והנוסח שלו (proposed_clause, ובצהוב גם fallback_wording)
    נוקבים במספר אחר באותה יחידה (התיאור 14 יום, הנוסח 30 יום), בכל כלל ובכל וריאנט.
    COUNTERPARTY_UNREALISTIC: מול צד שכנגד שהוא גוף ציבורי, חברה ממשלתית או מוסד להשכלה גבוהה
    (applicability.counterparty_kinds או counterparty_kind של הווריאנט), צהוב או נוסח נסיגה שמסיר סמכות שהגוף אינו יכול
    לוותר עליה (סיום מטעמי ציבור או תקציב, החלפת הצד בלי הליך תחרותי): error; בירוק: warning.
    CONCERN_UNMAPPED (אזהרה): חשש של הלקוח (scope_summary.client_concerns[]) בלי כלל קיים ב-mapped_rule_ids."""
    out = []
    app = model.get('applicability') if isinstance(model.get('applicability'), dict) else {}
    base_kinds = set(app.get('counterparty_kinds') or [])
    ids = {r.get('rule_id') for r in model.get('rules') or [] if isinstance(r, dict)}
    variants_kind = {}
    for s in (model.get('segmentation_model') or {}).get('segments') or [] if isinstance(
            model.get('segmentation_model'), dict) else []:
        if isinstance(s, dict) and s.get('segment_id'):
            k = s.get('counterparty_kind')
            variants_kind[s['segment_id']] = set(k if isinstance(k, list) else [k] if k else [])
    for r in model.get('rules') or []:
        if not isinstance(r, dict):
            continue
        rid = r.get('rule_id')
        for seg, track, t in _iter_tracks(r):
            if not t:
                continue
            # באדום התיאור הוא מה שהצד שכנגד דורש, והנוסח הוא התחליף שלנו: אין ביניהם התאמה לבדוק
            desc = _num_units(t.get('position')) if track != 'red' else {}
            for w, _lang in _wordings(t, track):
                wu = _num_units(w)
                for unit, nums in desc.items():
                    if unit in wu and not (nums & wu[unit]):
                        _f(out, 'TRACK_WORDING_MISMATCH', 'error', 'במסלול %s%s התיאור נוקב ב-%s %s, והנוסח אינו נוקב '
                           'בהם (בנוסח: %s %s). הנוסח ותיאורו אומרים אותו דבר.' % (
                               track, ', ' + seg if seg else '', '/'.join('%g' % x for x in sorted(nums)), unit,
                               '/'.join('%g' % x for x in sorted(wu[unit])), unit), rid, track)
                        break
            kinds = variants_kind.get(seg, set()) if seg else base_kinds
            if seg and not kinds:
                kinds = base_kinds
            if kinds & set(PUBLIC_KINDS):
                texts = [str(t.get('position') or '')] + [w for w, _ in _wordings(t, track)]
                for st in t.get('fallback_steps') or []:
                    if isinstance(st, dict):
                        texts.append(str(st.get('text') or ''))
                m = next((PUBLIC_POWER_REMOVED.search(x) for x in texts if PUBLIC_POWER_REMOVED.search(x)), None)
                if m and track != 'red':
                    _f(out, 'COUNTERPARTY_UNREALISTIC', 'error' if track == 'yellow' else 'warning',
                       'מול %s, המסלול %s מסיר סמכות שגוף כזה אינו יכול לוותר עליה ("%s"). הצהוב והנסיגה נבנים סביב '
                       'המחיר של הסמכות (הודעה מוקדמת, פיצוי על השקעה שלא הוחזרה, תשלום על עבודה שבוצעה), ולא '
                       'סביב ביטולה (clause-catalog.md, "Public body").'
                       % (', '.join(sorted(kinds & set(PUBLIC_KINDS))), track, m.group(0)), rid, track)
    for c in (model.get('scope_summary') or {}).get('client_concerns') or []:
        if not isinstance(c, dict):
            continue
        if not any(x in ids for x in c.get('mapped_rule_ids') or []):
            _f(out, 'CONCERN_UNMAPPED', 'warning', 'חשש של הלקוח ("%s") בלי כלל בפלייבוק: מפה אותו לכלל, או רשום אותו '
               'בשאלות הפתוחות.' % str(c.get('text') or '')[:60])
    return out


def validate(model, core=None, index_entry=None, check_wording=True, inventory=None, extract=None,
             approved_sources=None):
    out = coverage_findings(model, inventory=inventory, extract=extract)
    out += coverage_ledger_findings(model)
    out += department_findings(model)
    out += source_findings(model, approved_sources)
    out += case_law_findings(model, core)
    out += jurisdiction_findings(model)
    out += no_source_findings(model)
    out += position_source_findings(model)
    out += sufficiency_findings(model)
    out += rationale_findings(model)
    out += fallback_findings(model)
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

    # --- תווית אחת, מגזירה אחת (status.base_code), זהה בכל השכבות ---
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
    for code, msg in S.label_findings(model, core, index_entry):
        _f(out, code, 'warning' if code == 'LABEL_OLD_WORDING' else 'error', msg)

    # --- אין שרשרת אישורים ---
    for name, holder in (('model', model), ('core', core)):
        for p in _approver_paths(holder or {}):
            _f(out, 'APPROVER_FIELD', 'error', '%s.%s: שדה מאשר או הסלמה. אין שרשרת אישורים: ויתור מעבר לצהוב '
               'או חציית אדום מוצגים למשתמש כ"נדרשת הכרעתך". החתימה של היועץ המשפטי על הגיליון נשארת.' % (name, p))

    # --- מדגם השוק: מטרת ההתקשרות ותחום השיפוט, לכל משפחה ---
    mr = model.get('market_research') or {}
    srcs = mr.get('source_refs') or mr.get('sources') or []
    want_purpose = (mr.get('question') or {}).get('engagement_purpose') or \
        (model.get('applicability') if isinstance(model.get('applicability'), dict) else {}).get('engagement_purpose')
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
        # תחום השיפוט של המדגם: הדין החל על הסכמי הסוג (scope_summary.governing_laws[]), ורק כשאין, מדינת
        # ההתאגדות של הישות החותמת. אין הנחה של IL
        homes = governing_countries(model)
        raw_home = ((model.get('scope_summary') or {}).get('contracting_entity') or {}).get('incorporation_country')
        if not homes and country_code(raw_home):
            homes = [country_code(raw_home)]
        if not homes:
            _f(out, 'MARKET_NO_HOME_COUNTRY', 'warning', 'אין scope_summary.governing_laws[] ואין '
               'contracting_entity.incorporation_country מזוהה (%s): נדרש קוד (IL, GB-EAW, US-NY, DE) כדי לבדוק '
               'מקור שוק מתחום השיפוט.' % ('חסר' if not str(raw_home or '').strip() else raw_home))
        else:
            local = any(_country_of(s.get('jurisdiction')) in homes for s in srcs)
            if not local and not mr.get('jurisdiction_note'):
                _f(out, 'MARKET_NO_LOCAL_SOURCE', 'error', 'אין מקור שוק מ-%s, ואין jurisdiction_note שאומר זאת '
                   '("לא נמצא נוסח <הסוג> מ-<תחום השיפוט> שפורסם; העמדות התלויות בדין סומנו טעון בדיקה משפטית").'
                   % ', '.join(homes))

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
