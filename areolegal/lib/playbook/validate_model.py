# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'playbook/validate_model.py: בדיקות תוכן כלליות על playbook-model.json ועל הגרעין, לכל סוג הסכם.\n\nהמאמת כללי: הוא בודק מנגנונים שחלים בכל פלייבוק, ואינו מכיל שיקול משפטי של סוג הסכם מסוים (נושאים, כיוון של\nסעיף, דין ושיפוט, סוג מקור של עסקה מסוימת). שיקול כזה שייך לפלייבוק של הלקוח, כנתון שהפלייבוק נושא. בדיקות\nהנוסח עצמן הן של מודול בדיקות הפערים המשותף (common/gap_checks.py).\n\nvalidate(model, core=None, index_entry=None) מחזיר רשימת ממצאים {code, severity: error|warning, rule_id,\ntrack, message}. error = חוסם מסירה. הקודים:\n- WALKAWAY_ALL, WALKAWAY_NOT_CRITICAL, WALKAWAY_TOO_MANY (אזהרה), WALKAWAY_NO_SOURCE (שובר עסקה בלי\n  walk_away_source: statute | client_answer | company_document).\n- HOLD_GREEN_ALL, HOLD_GREEN_LOW.\n- YELLOW_EQUALS_GREEN, FALLBACK_EQUALS_GREEN, YELLOW_WORSENS_MAIN_ROLE (מסלול שסומן protects_main_role=false).\n- ROLE_EFFECT_MISSING: חסרה שורת השפעה לאחד התפקידים שיש לחברה בהסכם (approval_sheet.company_roles).\n- WORDING_GAP: נוסח ירוק, צהוב או נסיגה שנכשל בבדיקות הפערים המשותפות. GAP_CHECKS_UNAVAILABLE: המודול חסר.\n- LABEL_DUAL_FIELD: presentation_label נשמר במקום כלשהו. LABEL_MISMATCH: בסיס התווית שנשמרה שונה מהתווית\n  שנגזרת (status.base_code), או שהמעמד אינו תואם אותה. LABEL_DRIFT: שכבות (מודל, גרעין, אינדקס, handoff) שומרות\n  תוויות שונות. LABEL_OLD_WORDING (אזהרה): התווית בניסוח הקודם. (status.label_findings)\n- APPROVER_FIELD: שדה מאשר או הסלמה (authority, approval_required, approval_source, required_approver ...).\n- MARKET_COUNT_MISMATCH: מספר בשורת השקיפות או ב-handoff שונה מ-market_research.counts.\n- UNVERIFIED_LABEL_FORMAT: "1 מקורות" או סוגריים ריקים בתווית "ממצא לא מאומת".\n- MARKET_SAMPLE_PURPOSE: כל משפחות המקורות (או רובן, אזהרה) ממטרת התקשרות שאינה מטרת הפלייבוק\n  (source_refs[].engagement_purpose מול market_research.question.engagement_purpose), בכל סוג הסכם.\n- MARKET_NO_LOCAL_SOURCE: אין מקור שוק מתחום השיפוט של הדין החל (scope_summary.governing_laws[], ובלעדיו מדינת\n  ההתאגדות של הישות החותמת), ואין jurisdiction_note.\n- MARKET_NO_HOME_COUNTRY (אזהרה): אין governing_laws[] ואין incorporation_country מזוהה. אין הנחה של IL: בדיקת\n  המקור המקומי אינה רצה.\n- SOURCE_CASE_LAW: כתובת של אתר בית משפט, מאגר פסיקה או מדור פסיקה (common/case_law.py) בכל מקור. SOURCE_NOT_APPROVED:\n  מקור משפטי או רגולטורי (regulatory_research, external_sources L/X, statutory_override) מחוץ לרשימת המקורות\n  המאושרים. SOURCE_LIST_UNAVAILABLE (אזהרה). (source_findings)\n- CASE_LAW_NO_CONNECTOR, CASE_LAW_TEXT: פסיקה בלי מחבר פסיקה סגור (case_law_access.connector הוא null);\n  CASE_LAW_NO_REF, CASE_LAW_IN_WORDING: עם מחבר (case_law_findings).\n- GOVERNING_LAWS_MISSING, OVERRIDE_NO_JURISDICTION (אזהרות): הדין החל של הסוג, ו-jurisdiction בכל חובה בדין ובכל\n  שכבת statute (jurisdiction_findings).\n- NO_SOURCE_NOTE (אזהרה, לעולם אינה חוסמת): נושא שבו מחקר רשת הותר (מחקר עומק שהלקוח בחר, או פלייבוק לפי הרשת\n  והשוק שהלקוח ביקש) ולא נמצא מקור מורשה, ואין בו ההערה הגלויה "AREO לא מצאה מקור מורשה לנקודה זו"\n  (no_source_findings). אין רצפות ותקרות של הדין בקוד: ממצא בדין בא רק מרשימת המקורות המאושרים.\n- SOURCE_NOT_SHOWN: עמדה (ירוק, צהוב או אדום) שנגזרה ממסמכי הלקוח, בלי הסכם וסעיף שעליהם נשענה\n  (position_source_findings, כלל מייסד 12).\n- COVERAGE_LEDGER, COVERAGE_LEDGER_AGREEMENT: ספר הכיסוי (coverage_ledger) אינו מסתכם: סעיפים = סעיפים עם מדיניות\n  + סעיפים שנרשמו במפורש כ"אין מדיניות שאפשר לחלץ" + סעיפים ייחודיים שממתינים להכרעה (כלל מייסד 14).\n- SUFFICIENCY_NOT_ASKED, SUFFICIENCY_STALE (אזהרה): ההסכמים אינם מספיקים להסקת קווי הנסיגה, והלקוח לא נשאל\n  (playbook/sufficiency.py, כלל מייסד 13).\n- RATIONALE_DUPLICATE, LEGAL_CORE_MISSING, LEGAL_CORE_REVIEW_ONLY, LEGAL_CORE_STATUTE: נימוק שהודבק לכמה כללים, ושלד\n  משפטי חסר או שאינו אלא "טעון בדיקה משפטית" (rationale_findings).\n- TRACK_WORDING_MISMATCH, COUNTERPARTY_UNREALISTIC, CONCERN_UNMAPPED (אזהרה): נוסח שאינו תואם את תיאורו, נסיגה שאינה\n  ריאלית מול גוף ציבורי, וחשש של הלקוח בלי כלל (fallback_findings).\n- LEGAL_FACT_SOURCE, LEGAL_FACT_STALE: עובדת דין ממקור רשמי אחד עם בדיקת עדכניות.\n- FORBIDDEN_LABEL, PRODUCED_WITH.\n- DEPT_*: המחלקות האחראיות ושיוך החיובים (departments_and_responsibilities.md), כשהשדות קיימים: DEPT_SHAPE (מבנה),\n  DEPT_TYPE (type שאינו אחד מ-17 סוגי החובה של מרשם ההתחייבויות), DEPT_TYPE_DUPLICATE (שני שיוכים לאותו סוג),\n  DEPT_UNKNOWN (מחלקה שאינה ב-responsible_departments, או מחלקה מוצעת בלי needs_verification), DEPT_NO_SOURCE\n  (שיוך או הצעה בלי הפניית מקור), DEPT_PROPOSED_NO_QUOTE (מחלקה מוצעת בלי ציטוט).\n- COVERAGE_*: כל יחידת סעיף בכל הסכם בקורפוס קיבלה נושא, קוד טכני, סימון "סעיף ייחודי" או סיבה מפורשת\n  לכך שלא מופתה (coverage_findings). אין נושא "ברירת מחדל", ונושא שקיבל חלק חריג מהיחידות מחייב נימוק.\n  כשנמסרים מלאי הסעיפים (clause-inventory.json) וקובץ החילוץ (corpus-extract.json), הספירה מחושבת מהם\n  ומושווית לבלוק שבמודל (coverage_from_inventory), וכל פסקה מהותית בכל הסכם חייבת להיות בתוך יחידה.\n'
import json,re
try:from playbook import status as S,market_counts as MC;from playbook.approval_sheet import track_wording,company_roles,role_effect,role_code;from common.terms import terms_re
except ImportError:import os;import sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from playbook import status as S;from playbook import market_counts as MC;from playbook.approval_sheet import track_wording,company_roles,role_effect,role_code;from common.terms import terms_re
try:from obligations.model import TYPES as OBLIGATION_TYPES
except ImportError:OBLIGATION_TYPES='payment','milestone','deliverable','insurance','guarantee','reporting','notice','renewal_notice','term_end','option','audit','consent_approval','data_return_deletion','confidentiality','compliance','price_adjustment','other'
TRACKS='green','yellow','red'
MAX_WALK_AWAY=5
WALK_SOURCES='statute','client_answer','company_document'
FORBIDDEN='אומת בשני מקורות','אומת במקור אחד בלבד'
APPROVER_KEYS='approval_required','approval_source','required_approver','required_by','escalation','approver','per_track'
_HEB=re.compile('[\u0590-\u05ff]')
COUNTRY_CODES={'ישראל':'IL','israel':'IL','ארצות הברית':'US','ארה"ב':'US','ארה״ב':'US','united states':'US','usa':'US','בריטניה':'GB','אנגליה':'GB','united kingdom':'GB','uk':'GB','england':'GB','גרמניה':'DE','germany':'DE','צרפת':'FR','france':'FR','הולנד':'NL','netherlands':'NL','אירלנד':'IE','ireland':'IE','קפריסין':'CY','cyprus':'CY','שווייץ':'CH','switzerland':'CH','סינגפור':'SG','singapore':'SG','קנדה':'CA','canada':'CA','אוסטרליה':'AU','australia':'AU','הודו':'IN','india':'IN','יפן':'JP','japan':'JP','איטליה':'IT','italy':'IT','ספרד':'ES','spain':'ES','לוקסמבורג':'LU','luxembourg':'LU','איחוד האמירויות':'AE','united arab emirates':'AE','uae':'AE'}
def country_code(raw):
	'ISO-3166 alpha-2 מהערך שנשמר; None כשהערך חסר או לא מזוהה.';A=re.sub('\\s+',' ',str(raw or'')).strip()
	if re.fullmatch('[A-Za-z]{2}',A):return A.upper()
	return COUNTRY_CODES.get(A)or COUNTRY_CODES.get(A.lower())
def _country_of(code):'המדינה של קוד תחום שיפוט: GB-EAW -> GB, US-NY -> US, "Israel" -> IL. None כשאינו מזוהה.';A=str(code or'').strip();return country_code(A)or country_code(re.split('[-_/ ]',A)[0])if A else None
def governing_countries(model):
	'המדינות של הדין החל על הסכמי הסוג (scope_summary.governing_laws[]), בלי כפילות.';A=(model.get('scope_summary')or{}).get('governing_laws')or[]
	if isinstance(A,str):A=[A]
	return list(dict.fromkeys(A for A in(_country_of(A.get('code')if isinstance(A,dict)else A)for A in A)if A))
def _f(out,code,severity,message,rule_id=None,track=None):out.append({'code':code,'severity':severity,'rule_id':rule_id,'track':track,'message':message})
def _imp(rule):return str(rule.get('importance')or'').lower()
def _core_val(rule,core_by_id,key):
	B=key;A=rule
	if A.get(B)is not None:return A[B]
	return(core_by_id.get(A['rule_id'])or{}).get(B)
def _wordings(t,track):
	'[(text, lang)] של כל נוסח במסלול: proposed_clause בכל שפה, ונוסח הנסיגה בצהוב.';B=[];A=t.get('proposed_clause')
	if isinstance(A,dict):
		for D in('he','en'):
			if(A.get(D)or'').strip():B.append((A[D],D))
	elif isinstance(A,str)and A.strip():B.append((A,'he'if _HEB.search(A)else'en'))
	if track=='yellow':
		C=track_wording('yellow',t)
		if C and all(C!=A for(A,B)in B):B.append((C,'he'if _HEB.search(C)else'en'))
	return B
def _iter_tracks(rule):
	'(segment_id, track, block) לכל מסלול בכלל ובכל וריאנט.'
	for A in TRACKS:yield(None,A,(rule.get('traffic_light')or{}).get(A)or{})
	for B in rule.get('segment_variants')or[]:
		for A in TRACKS:
			C=(B.get('traffic_light')or{}).get(A)
			if C:yield(B.get('segment_id'),A,C)
def _accept_text(model,lang):
	'כל נוסחי הירוק בשפה הזו, פסקה לכל כלל: "ההסכם" שהפלייבוק מציע, לבדיקות שתלויות בשאר ההסכם.';A=[]
	for B in model.get('rules')or[]:C=(B.get('traffic_light')or{}).get('green')or{};A+=[A for(A,B)in _wordings(C,'green')if B==lang]
	return'\n'.join(A)
def wording_findings(model):
	'בדיקות הפערים המשותפות (common.gap_checks) על כל נוסח ירוק, צהוב ונסיגה, בכל שפה. ממצא = error.\n    אין כאן רמז נושא ואין שיקול של סוג הסכם: המודול המשותף בודק מנגנונים כלליים בלבד.';C=model
	try:from common import gap_checks as I
	except ImportError:return[{'code':'GAP_CHECKS_UNAVAILABLE','severity':'error','rule_id':None,'track':None,'message':'common.gap_checks אינו זמין, ולכן אי אפשר לבדוק את הנוסחים לפני הגיליון.'}]
	D=[]
	try:from playbook import approval_sheet as J;G=[A for(B,A)in J.company_roles(C)if A and B!='company']
	except Exception:G=[]
	for E in C.get('rules')or[]:
		for(K,A,L)in _iter_tracks(E):
			if A not in('green','yellow'):continue
			for(H,F)in _wordings(L,A):
				M={'accept_text':_accept_text(C,F)+'\n'+H,'source':'playbook','rule_id':E['rule_id'],'track':A,'segment':K,'allow_statutory_cap':True,'company_terms':G}
				for B in I.check_wording(H,F,topic=None,context=M)or[]:_f(D,'WORDING_GAP','error','%s: %s'%(B.get('code'),B.get('message_he')or''),E['rule_id'],A);D[-1].update(gap_code=B.get('code'),span=B.get('span'),lang=F)
	return D
def _approver_paths(obj,path=''):
	D=path;A=obj
	if isinstance(A,dict):
		for(B,C)in A.items():
			E='%s.%s'%(D,B)if D else B
			if(B in APPROVER_KEYS or B=='authority')and C not in(None,'',[],{},False):yield E
			else:yield from _approver_paths(C,E)
	elif isinstance(A,list):
		for(F,C)in enumerate(A):yield from _approver_paths(C,'%s[%d]'%(D,F))
TECHNICAL_CODES='signature_block','party_identification','notice_addresses','counterparts_esignature','headings','interpretation_grammar','recitals_descriptive','neutral_definition','bank_details','delivery_points_list','admin_form_fields','statutory_admin_restatement'
FORBIDDEN_OMISSION='לא רלוונטי','נוסח אחיד','נוסח עקבי','אין מחלוקת','תפעולי','הסכם יחיד','תנאי מסחרי','אין ראיה לעמדת החברה','סטנדרטי','טכני בלבד','אין צורך','ברור מאליו','not relevant','standard','boilerplate'
DEFAULT_TOPIC_RE=re.compile('ברירת מחדל|שלא זוהה בה נושא|לא זוהה (?:בה |בו )?נושא|by default|default topic|fallback topic',re.I)
NEGATION_RE=re.compile('(?:^|[\\s(])(?:ללא|בלי|אין|no|not|without|never)\\s+(?:\\S+\\s+){0,3}$',re.I)
SUBSTANTIVE_CHARS=40
CONCENTRATION_MIN_UNITS=20
CONTINUATION_MAX=8
def _cov_num(cov,name,alias):'המספר בשם שבסכמה (units, topic_units...), או בשם החלופי (units_total, units_mapped...).';A=cov.get(name);return A if isinstance(A,int)and not isinstance(A,bool)else cov.get(alias)
def _unit_kind(u):
	'rule | technical | unique | unmapped | None (יחידה שלא קיבלה דבר).'
	if u.get('rule_id'):return'rule'
	if u.get('technical'):return'technical'
	if u.get('unique'):return'unique'
	if str(u.get('unmapped_reason')or'').strip():return'unmapped'
def default_topic_hit(text):
	'הביטוי של שיוך ברירת מחדל בטקסט, או None. ביטוי שקודמת לו שלילה באותו משפט אינו נספר.'
	for A in DEFAULT_TOPIC_RE.finditer(text or''):
		B=re.split('[.,;:!?\\n]',text[:A.start()])[-1]
		if not NEGATION_RE.search(B):return A.group(0)
def _corpus_source(model,s):
	'מקור שנכנס למלאי הסעיפים: נכלל, ואינו תבנית. כשהמאגר הוא נוסחים שהחברה מציגה (corpus_status:\n    company_forms, workflow.md שלב 2ח), הנוסחים הם הקורפוס גם כשנרשמו כתבנית: בהרצה חיה הם\n    נרשמו doc_role: template, כמו שההוראות אמרו אז, ושלד המלאי יצא ריק.\n    תבנית של צד שכנגד (paper: theirs: טופס סטנדרטי שהצד שכנגד מציג לחתימה, למשל חוזה של צד אחד, תנאים\n    כלליים של צד או נספח של הליך תחרותי) היא מסמך מהקורפוס בכל מעמד, ונכנסת למלאי:\n    נספחים של הליך תחרותי עלולים להירשם כתבנית במעמד unknown, ולא להיות ממופים כלל (corpus-pipeline.md, פרק 2).'
	if not isinstance(s,dict)or s.get('included')is False:return False
	return s.get('doc_role')!='template'or s.get('paper')=='theirs'or S.corpus_status(model)=='company_forms'
def _base(p):return re.split('[\\\\/]',str(p or''))[-1].strip().lower()
def _extract_docs(model,extract):
	'{source_id: מסמך החילוץ}, לפי שם הקובץ ב-source_log מול path בחילוץ, או doc_id.';B=model;C=(extract or{}).get('documents')or[];E={_base(A.get('path')):A for A in C};F={A.get('doc_id'):A for A in C if A.get('doc_id')};D={}
	for A in B.get('source_log')or[]:
		if not _corpus_source(B,A):continue
		G=F.get(A.get('doc_id'))or E.get(_base(A.get('file')));D[A.get('source_id')]=G
	return D
def _substantive(doc):return{A.get('i')for A in doc.get('paragraphs')or[]if A.get('kind')!='header_footer'and len(str(A.get('text')or'').strip())>=SUBSTANTIVE_CHARS}
def inventory_skeleton(model,extract):
	'שלד המלאי מקובץ החילוץ: יחידה לכל סעיף, בלי שיוך. הבונה ממלא בכל יחידה rule_id, technical, unique או\n    unmapped_reason, ושומר כ-clause-inventory.json.\n    יחידה מתחילה בפסקה שזוהה בה מספר סעיף, וכוללת עד 8 פסקאות שאחריה עד מספר הסעיף הבא; כל פסקה מהותית אחרת היא יחידה בפני עצמה.\n    כך כל פסקה מהותית נמצאת ביחידה אחת בדיוק, גם כשזיהוי מספרי הסעיפים בחילוץ חלקי (מסמך בלי מספור, או מספור\n    חלקי), ויחידה אינה בולעת פרק שלם שמספרו לא זוהה.';H=extract;G=model;E=[];I=_extract_docs(G,H)
	if not(G or{}).get('source_log'):I={'S%02d'%(A+1):B for(A,B)in enumerate((H or{}).get('documents')or[])}
	for(F,D)in I.items():
		if D is None:continue
		J=_substantive(D);A=None
		for C in D.get('paragraphs')or[]:
			B=C.get('i')
			if C.get('kind')=='header_footer':continue
			if str(C.get('clause')or'').strip():A={'source_ref':F,'file':D.get('path'),'p':B,'p_to':B,'clause':str(C['clause']).strip(),'text':str(C.get('text')or'')[:300]};E.append(A)
			elif A is not None and A['source_ref']==F and B-A['p']<=CONTINUATION_MAX:A['p_to']=B
			elif B in J:A=None;E.append({'source_ref':F,'file':D.get('path'),'p':B,'p_to':B,'clause':'','text':str(C.get('text')or'')[:300]})
		A=None
	return{'generated_from':'corpus-extract.json','unit_rule':inventory_skeleton.__doc__.split('\n')[2].strip(),'units':E}
def coverage_from_inventory(model,inventory,extract=None):
	'הבלוק coverage, מחושב מהמלאי (ומהחילוץ, כשנמסר). הבונה מעתיק אותו למודל כמו שהוא.\n\n    יחידה במלאי: {source_ref, p, p_to, clause, text} ואחד מאלה: rule_id | technical (קוד מהרשימה הסגורה) |\n    unique: true עם queue_id | unmapped_reason. p ו-p_to הם האינדקסים (i) של הפסקה הראשונה והאחרונה ביחידה.';P=extract;O=inventory;F=model;G=(O or{}).get('units')or[];H={A.get('rule_id')for A in F.get('rules')or[]if isinstance(A,dict)};I,D,J,Q={},{'rule':0,'technical':0,'unique':0,'unmapped':0},[],[];K,R,S,L={},[],[],{}
	for A in G:
		B=_unit_kind(A);M=str(A.get('source_ref')or'').split('#')[0];E='%s#p%s'%(M,A.get('p'));C=L.setdefault(M,{'source_id':M,'units':0,'mapped':0,'technical':0,'unique':0,'unmapped':0,'unassigned':0});C['units']+=1
		if B is None:J.append(E);C['unassigned']+=1;continue
		D[B]+=1;C['mapped'if B=='rule'else B]+=1
		if B=='rule':
			I[A['rule_id']]=I.get(A['rule_id'],0)+1
			if A['rule_id']not in H:Q.append(A['rule_id'])
		elif B=='technical':K.setdefault(A['technical'],{'code':A['technical'],'reason':A.get('reason')or'','refs':[]});K[A['technical']]['refs'].append(E)
		elif B=='unique':R.append({'ref':E,'quote':A.get('text')or'','queue_id':A.get('queue_id')or'','kind':A.get('kind')or''})
		else:S.append({'ref':E,'reason':A['unmapped_reason']})
	W=_extract_docs(F,P)if P else{}
	for(N,T)in W.items():
		C=L.setdefault(N,{'source_id':N,'units':0,'mapped':0,'technical':0,'unique':0,'unmapped':0,'unassigned':0})
		if T is None:C['extract_paragraphs']=None;continue
		U=_substantive(T);V=set()
		for A in G:
			if str(A.get('source_ref')or'').split('#')[0]==N and isinstance(A.get('p'),int):X=A.get('p_to')if isinstance(A.get('p_to'),int)else A['p'];V.update(range(A['p'],X+1))
		C['extract_paragraphs']=len(U);C['uncovered_paragraphs']=len(U-V)
	Y=sum(1 for A in F.get('rules')or[]if isinstance(A,dict)and A.get('topic_origin')=='corpus_derived');return{'inventory_ref':(O or{}).get('ref')or'','units':len(G),'topic_units':D['rule'],'technical_units':D['technical'],'unique_units':D['unique'],'unmapped_units':D['unmapped'],'unassigned_units':len(J),'topics':len(H),'topics_with_rule':len(H),'topics_new':Y,'by_rule':I,'by_agreement':sorted(L.values(),key=lambda r:str(r['source_id'])),'technical_items':list(K.values()),'unique_clauses':R,'unmapped':S,'_unassigned_refs':J[:20],'_unknown_rules':sorted(set(Q))}
def coverage_findings(model,inventory=None,extract=None):
	'ממצאי הכיסוי: הבלוק שבמודל, ומול המלאי והחילוץ כשנמסרו. כל ממצא כאן חוסם.';d=extract;U=inventory;M=model;P=[];A=M.get('coverage')
	if not isinstance(A,dict):_f(P,'COVERAGE_MISSING','error','אין במודל coverage: אין הוכחה שכל סעיף בכל הסכם קיבל נושא.');return P
	B=lambda code,msg,rid=None:_f(P,code,'error',msg,rid);Q=_cov_num(A,'units','units_total');J=_cov_num(A,'topic_units','units_mapped');K=_cov_num(A,'technical_units','units_technical');N=_cov_num(A,'unique_units','units_unique')or 0;I=_cov_num(A,'unmapped_units','units_unmapped');e={'units':Q,'topic_units':J,'technical_units':K,'unmapped_units':I}
	for(G,f)in e.items():
		if not isinstance(f,int)or isinstance(f,bool):B('COVERAGE_NUMBERS','coverage.%s חסר או אינו מספר שנספר בקוד.'%G)
	if not str(A.get('inventory_ref')or'').strip():B('COVERAGE_NUMBERS','coverage.inventory_ref חסר: איפה נשמר מלאי הסעיפים.')
	o=all(isinstance(A,int)and not isinstance(A,bool)for A in e.values())
	if o and J+K+N+I!=Q:B('COVERAGE_SUM','coverage אינו מסתכם: %d יחידות, ו-%d ממופות לנושא, %d טכניות, %d ייחודיות ו-%d לא ממופות.'%(Q,J,K,N,I))
	if isinstance(A.get('topics'),int)and A.get('topics_with_rule')!=A['topics']:B('COVERAGE_TOPICS','%s נושאים בלי כלל ב-rules[].'%(A['topics']-(A.get('topics_with_rule')or 0)))
	g=[A for A in M.get('rules')or[]if isinstance(A,dict)];h={A.get('rule_id')for A in g};i=sum(1 for A in g if A.get('topic_origin')=='corpus_derived')
	if isinstance(A.get('topics_new'),int)and A['topics_new']!=i:B('COVERAGE_TOPICS','coverage.topics_new=%d, ו-%d כללים מסומנים topic_origin: corpus_derived.'%(A['topics_new'],i))
	V=A.get('unmapped')if isinstance(A.get('unmapped'),list)else[]
	if isinstance(I,int)and I:
		if len(V)!=I:B('COVERAGE_UNMAPPED','%d יחידות לא ממופות, ו-%d מהן רשומות ב-coverage.unmapped[] עם סיבה. יחידה שלא מופתה מותרת רק עם סיבה מפורשת (למשל טקסט שלא נקרא).'%(I,len(V)))
	for(R,C)in enumerate(V):
		L=str((C or{}).get('reason')or'')
		if not L.strip()or any(A in L for A in FORBIDDEN_OMISSION):B('COVERAGE_UNMAPPED','coverage.unmapped[%d] (%s): "%s" אינה סיבה.'%(R,(C or{}).get('ref'),L[:40]))
	W=A.get('unique_clauses')if isinstance(A.get('unique_clauses'),list)else[]
	if N and len(W)!=N:B('COVERAGE_UNIQUE','unique_units=%d, ו-%d סעיפים ב-coverage.unique_clauses[].'%(N,len(W)))
	p={A.get('id')for A in M.get('validation_queue')or[]if isinstance(A,dict)};j={}
	for(R,C)in enumerate(W):
		C=C or{}
		if not str(C.get('quote')or'').strip()or not C.get('ref'):B('COVERAGE_UNIQUE','coverage.unique_clauses[%d]: סעיף ייחודי נרשם עם ref ועם ציטוט.'%R)
		if C.get('queue_id')not in p:B('COVERAGE_UNIQUE','coverage.unique_clauses[%d] (%s): אין לו פריט בתור ההכרעות (queue_id).'%(R,C.get('ref')))
		if C.get('kind'):j.setdefault(str(C['kind']).strip(),set()).add(str(C.get('ref')or'').split('#')[0])
	for(q,X)in j.items():
		if len(X)>=2:B('COVERAGE_UNIQUE','סוג הסעיף "%s" מופיע ב-%d הסכמים (%s): סוג שחוזר בשני הסכמים או יותר הוא נושא בפלייבוק, עם רמזור, ולא "סעיף ייחודי".'%(q,len(X),', '.join(sorted(X))))
	S=A.get('technical_items')
	if not isinstance(S,list):B('COVERAGE_TECHNICAL','coverage.technical_items[] חסר (מקור הפרק "סעיפים שלא קיבלו מדיניות").');S=[]
	Y=0
	for(G,H)in enumerate(S):
		H=H if isinstance(H,dict)else{}
		if H.get('code')not in TECHNICAL_CODES:B('COVERAGE_TECHNICAL','coverage.technical_items[%d]: הקוד %s אינו ברשימה הסגורה.'%(G,H.get('code')))
		L=str(H.get('reason')or'')
		if not L or any(A in L for A in FORBIDDEN_OMISSION):B('COVERAGE_TECHNICAL','coverage.technical_items[%d]: "%s" אינו נימוק.'%(G,L[:40]))
		if not isinstance(H.get('refs'),list)or not H.get('refs'):B('COVERAGE_TECHNICAL','coverage.technical_items[%d]: חסר refs[] (איזה סעיף).'%G)
		else:Y+=len(H['refs'])
	if isinstance(K,int)and S and Y!=K:B('COVERAGE_TECHNICAL','technical_items מכסים %d סעיפים, ו-technical_units הוא %d.'%(Y,K))
	r=' '.join(str(A or'')for A in(A.get('method'),(U or{}).get('method')));k=default_topic_hit(r)
	if A.get('default_rule_id')or k:B('COVERAGE_DEFAULT_TOPIC','המלאי שייך יחידות שלא זוהה להן נושא לנושא אחד ("%s"). כל יחידה ממופה לנושא משלה, לנושא חדש שנגזר מהקורפוס, ל"סעיף ייחודי" או לקוד טכני.'%(A.get('default_rule_id')or k))
	D=coverage_from_inventory(M,U,d)if U else None;T=A.get('by_rule')if isinstance(A.get('by_rule'),dict)else(D or{}).get('by_rule')
	if T is None:B('COVERAGE_BY_RULE','coverage.by_rule{} חסר, ולא נמסר מלאי: אי אפשר לבדוק אם נושא אחד קיבל חלק חריג מהיחידות.')
	else:
		for E in T:
			if E not in h:B('COVERAGE_BY_RULE','coverage.by_rule: הכלל %s אינו ב-rules[].'%E,E)
		O=sum(A for A in T.values()if isinstance(A,int))
		if isinstance(J,int)and O!=J:B('COVERAGE_BY_RULE','coverage.by_rule מסתכם ב-%d, ו-topic_units הוא %d.'%(O,J))
		Z=len(h)
		if O>=CONCENTRATION_MIN_UNITS and Z>=4:
			E,a=max(T.items(),key=lambda kv:kv[1]if isinstance(kv[1],int)else 0);l=max(.25,3./Z);m=A.get('concentration_note')if isinstance(A.get('concentration_note'),dict)else{}
			if a>O*l and not(m.get('rule_id')==E and str(m.get('reason')or'').strip()):B('COVERAGE_CONCENTRATION','הנושא %s קיבל %d מתוך %d היחידות הממופות (%d%%), מעל %d%% ב-%d נושאים. זה סימן לשיוך ברירת מחדל: מפו את היחידות לנושאים שלהן, או נמקו ב-coverage.concentration_note.'%(E,a,O,round(1e2*a/O),round(100*l),Z),E)
	b=A.get('by_agreement')if isinstance(A.get('by_agreement'),list)else(D or{}).get('by_agreement');s=[A.get('source_id')for A in M.get('source_log')or[]if _corpus_source(M,A)]
	if b is None:B('COVERAGE_BY_AGREEMENT','coverage.by_agreement[] חסר, ולא נמסר מלאי: אין פירוט לפי הסכם.');b=[]
	t={A.get('source_id'):A for A in b if isinstance(A,dict)}
	for n in s:
		F=t.get(n)
		if F is None or not F.get('units'):
			if not str((F or{}).get('note')or'').strip():B('COVERAGE_BY_AGREEMENT','ההסכם %s נכלל בקורפוס, ואין לו אף יחידה במלאי.'%n)
	if D:
		if D['unassigned_units']:B('COVERAGE_UNASSIGNED','%d יחידות במלאי בלי נושא, קוד טכני, סימון ייחודי או סיבה (למשל %s).'%(D['unassigned_units'],', '.join(D['_unassigned_refs'][:5])))
		for E in D['_unknown_rules']:B('COVERAGE_INVENTORY','המלאי מפנה לכלל %s שאינו ב-rules[].'%E,E)
		for(G,c)in(('units',Q),('topic_units',J),('technical_units',K),('unique_units',N),('unmapped_units',I)):
			if isinstance(c,int)and c!=D[G]:B('COVERAGE_INVENTORY','coverage.%s במודל הוא %d, ובמלאי %d.'%(G,c,D[G]))
		for F in D['by_agreement']:
			if F.get('extract_paragraphs')is None and d:B('COVERAGE_EXTRACT','ההסכם %s אינו בקובץ החילוץ, ולכן אי אפשר לבדוק שכל סעיף בו כוסה.'%F['source_id'])
			elif F.get('uncovered_paragraphs'):B('COVERAGE_PARAGRAPHS','בהסכם %s %d מתוך %d הפסקאות המהותיות אינן בתוך אף יחידה במלאי: זיהוי הסעיפים חלקי.'%(F['source_id'],F['uncovered_paragraphs'],F['extract_paragraphs']))
	return P
def _has_source(v):
	if isinstance(v,dict):return any(str(v.get(A)or'').strip()for A in('agreement','clause','citation_id'))
	return bool(str(v or'').strip())
def department_findings(model):
	'המחלקות האחראיות ושיוך החיובים: שדות רשות, ונבדקים רק כשהם קיימים (ps1-playbook-identity-scope.md).';I=model;A=[];P='responsible_departments','departments_proposed','obligation_assignments'
	if not any(A in I for A in P):return A
	F=I.get('responsible_departments');G=I.get('departments_proposed');H=I.get('obligation_assignments')
	for(Q,N)in(('responsible_departments',F),('departments_proposed',G),('obligation_assignments',H)):
		if N is not None and not isinstance(N,list):_f(A,'DEPT_SHAPE','error','%s: נדרשת רשימה.'%Q)
	F=F if isinstance(F,list)else[];G=G if isinstance(G,list)else[];H=H if isinstance(H,list)else[];O=set()
	for(B,J)in enumerate(F):
		if not isinstance(J,str)or not J.strip():_f(A,'DEPT_SHAPE','error','responsible_departments[%d]: נדרש שם מחלקה (מחרוזת).'%B)
		else:O.add(J.strip())
	K=set()
	for(B,C)in enumerate(G):
		if not isinstance(C,dict)or not str(C.get('name')or'').strip():_f(A,'DEPT_SHAPE','error','departments_proposed[%d]: נדרש {name, quote, source}.'%B);continue
		K.add(C['name'].strip())
		if not str(C.get('quote')or'').strip():_f(A,'DEPT_PROPOSED_NO_QUOTE','error','departments_proposed[%d] (%s): מחלקה מוצעת נשענת על ציטוט מההסכם שמייחס לה תפקיד.'%(B,C['name']))
		if not _has_source(C.get('source')):_f(A,'DEPT_NO_SOURCE','error','departments_proposed[%d] (%s): חסרה הפניית מקור (הסכם וסעיף).'%(B,C['name']))
	L={}
	for(B,C)in enumerate(H):
		if not isinstance(C,dict):_f(A,'DEPT_SHAPE','error','obligation_assignments[%d]: נדרש {type, department, source, needs_verification}.'%B);continue
		D=C.get('type')
		if D not in OBLIGATION_TYPES:_f(A,'DEPT_TYPE','error','obligation_assignments[%d]: type "%s" אינו אחד מ-17 סוגי החובה של מרשם ההתחייבויות (%s).'%(B,D,', '.join(OBLIGATION_TYPES)))
		elif D in L:_f(A,'DEPT_TYPE_DUPLICATE','error','obligation_assignments[%d]: הסוג "%s" כבר משויך (שורה %d). שורה אחת לכל סוג חיוב, כדי שהמרשם ימצא מחלקה אחת.'%(B,D,L[D]))
		else:L[D]=B
		E=str(C.get('department')or'').strip();M=C.get('needs_verification')
		if M is not None and not isinstance(M,bool):_f(A,'DEPT_SHAPE','error','obligation_assignments[%d].needs_verification: true או false.'%B)
		if not E:_f(A,'DEPT_SHAPE','error','obligation_assignments[%d]: חסרה מחלקה.'%B)
		elif E not in O:
			if E in K and M is True:0
			elif E in K:_f(A,'DEPT_UNKNOWN','error','obligation_assignments[%d]: המחלקה "%s" הוצעה ועוד לא נקבעה, ולכן השיוך מסומן needs_verification: true.'%(B,E))
			else:_f(A,'DEPT_UNKNOWN','error','obligation_assignments[%d]: המחלקה "%s" אינה ב-responsible_departments.'%(B,E))
		if not _has_source(C.get('source')):_f(A,'DEPT_NO_SOURCE','error','obligation_assignments[%d]: חסרה הפניית מקור (הסכם וסעיף).'%B)
	return A
URL_KEYS='url','final_url','source_url','link'
QUOTE_KEYS={'quote','quotes','excerpt','verbatim','source_quote','clause_text','text_quote','evidence','source_log','coverage','agreement_exceptions','observed_alternatives','search_log','case_law','case_law_access','holding_quote','citations','corpus','inventory','produced_with'}
def _approved_rules(path=None):
	'כללי הדומיינים המאושרים מ-risk.validate_register (מקורות-מאושרים.json, או רשימת הנפילה שבקוד), או None\n    כשהמודול אינו זמין. מקבל גם צורה שבה approved_domains מחזיר רשימה ולא זוג.'
	try:from risk.validate_register import approved_domains as B
	except ImportError:return
	try:A=B(path)if path else B()
	except TypeError:A=B()
	if isinstance(A,tuple)and len(A)==2 and isinstance(A[0],(tuple,list)):A=A[0]
	return A if isinstance(A,tuple)else tuple(A or())
def _domain_ok(url,rules):
	A=rules
	try:from risk.validate_register import domain_ok as C;return C(url,A)
	except ImportError:B=re.sub('^[a-z]+://','',url or'',flags=re.I).split('/')[0].split(':')[0].lower();return any(B==A.split('/')[0]or B.endswith('.'+A.split('/')[0])for A in A)
def _case_law_url(url):
	try:from common.case_law import case_law_url as A
	except ImportError:return
	return A(url)
def _urls(obj,path=''):
	'(נתיב, כתובת) לכל כתובת במבנה.';C=path;B=obj
	if isinstance(B,dict):
		for(D,A)in B.items():
			E='%s.%s'%(C,D)if C else D
			if D in URL_KEYS and isinstance(A,str)and re.match('(https?://|www\\.)',A.strip(),re.I):yield(E,A.strip())
			elif isinstance(A,(dict,list)):yield from _urls(A,E)
	elif isinstance(B,list):
		for(F,A)in enumerate(B):yield from _urls(A,'%s[%d]'%(C,F))
def source_findings(model,approved_sources=None):
	'SOURCE_CASE_LAW: כתובת של אתר בית משפט, מאגר פסיקה או מדור פסיקה בכל מקור (regulatory_research,\n    external_sources, market_research.source_refs, statutory_override). SOURCE_NOT_APPROVED: מקור משפטי או\n    רגולטורי (regulatory_research, external_sources עם ref של L או X, statutory_override) שאינו ברשימת המקורות\n    המאושרים, בדומיין ובנתיב. SOURCE_LIST_UNAVAILABLE (אזהרה): risk.validate_register אינו זמין.';D=model;A=[];B,F=[],[];B+=list(_urls(D.get('regulatory_research')or{},'regulatory_research'))
	for(K,E)in enumerate(D.get('external_sources')or[]):
		if not isinstance(E,dict):continue
		L=list(_urls(E,'external_sources[%d]'%K));(B if str(E.get('ref')or E.get('source_id')or'').startswith(('L','X'))else F).extend(L)
	F+=list(_urls((D.get('market_research')or{}).get('source_refs')or[],'market_research.source_refs'))
	for H in D.get('rules')or[]:B+=list(_urls(H.get('statutory_override')or[],'%s.statutory_override'%H.get('rule_id')))
	for(G,C)in B+F:
		I=_case_law_url(C)
		if I:_f(A,'SOURCE_CASE_LAW','error','%s: %s'%(G,I))
	if not B:return A
	J=_approved_rules(approved_sources)
	if not J:_f(A,'SOURCE_LIST_UNAVAILABLE','warning','רשימת המקורות המאושרים לא נטענה (--approved-sources או AREO_APPROVED_SOURCES): המקורות המשפטיים לא נבדקו מולה.');return A
	for(G,C)in B:
		if not _case_law_url(C)and not _domain_ok(C,J):_f(A,'SOURCE_NOT_APPROVED','error','%s: %s אינו ברשימת המקורות המאושרים (approved-regulatory-sources.md, מקורות-מאושרים.json). דין ורגולציה רק משם; אחרת "טעון בדיקה משפטית".'%(G,C))
	return A
def _texts(obj,path=''):
	'(נתיב, מחרוזת) לכל מחרוזת, בלי שדות של ציטוט מילולי מההסכמים (QUOTE_KEYS).';B=path;A=obj
	if isinstance(A,str):yield(B,A)
	elif isinstance(A,dict):
		for(C,D)in A.items():
			if C in QUOTE_KEYS:continue
			yield from _texts(D,'%s.%s'%(B,C)if B else C)
	elif isinstance(A,list):
		for(E,D)in enumerate(A):yield from _texts(D,'%s[%d]'%(B,E))
def case_law_connector(model):A=model.get('case_law_access');return(A.get('connector')if isinstance(A,dict)else None)or None
def case_law_findings(model,core=None):
	'פסיקה בתוצרי הבונה (playbook-qa.md, בדיקה 7).\n    בלי מחבר (case_law_access.connector הוא null): CASE_LAW_NO_CONNECTOR על case_law[] לא ריק או על שכבת\n    case_law ב-legal_basis_layers[]; CASE_LAW_TEXT על אזכור פסק דין (common.case_law) בנימוק, בעמדות, בנוסחים,\n    בשאלות ובכל טקסט יוצא של המודל או של הגרעין. עם מחבר: CASE_LAW_NO_REF על פסק דין בלי retrieval_ref, ו-\n    CASE_LAW_IN_WORDING על אזכור פסיקה בנוסח מוצע, בנוסח נסיגה או בגרעין.';D=model;A=[];E=case_law_connector(D)
	try:from common.case_law import case_law_hits as C
	except ImportError:C=None
	for B in D.get('rules')or[]:
		I=B.get('rule_id');F=[A for A in B.get('case_law')or[]if A];M=[A for A in B.get('legal_basis_layers')or[]if isinstance(A,dict)and(A.get('layer')=='case_law'or A.get('case_law_ref'))]
		if not E and(F or M):_f(A,'CASE_LAW_NO_CONNECTOR','error','פסיקה בכלל (%s) בלי מחבר פסיקה סגור (case_law_access.connector הוא null). פסיקה רק ממחבר שהלקוח חיבר; אחרת "טעון בדיקה משפטית".'%('case_law[]'if F else'legal_basis_layers: case_law'),I)
		if E:
			for J in F:
				if not(isinstance(J,dict)and J.get('retrieval_ref')):_f(A,'CASE_LAW_NO_REF','error','פסק דין בלי retrieval_ref: רק מה שהמחבר החזיר בהרצה הזו.',I)
	if C is None:return A
	if not E:
		for(N,O)in(('model',D),('core',core)):
			for(G,H)in _texts(O or{},N):
				K=C(H)
				if K:_f(A,'CASE_LAW_TEXT','error','%s: אזכור פסיקה בלי מחבר פסיקה סגור (%s). פסיקה לא נכתבת, לא נקראת בשם ולא מתוארת; הסעיף מסומן "טעון בדיקה משפטית".'%(G,'; '.join(K[:2])))
	else:
		for B in D.get('rules')or[]:
			for(R,L,P)in _iter_tracks(B):
				for(Q,S)in _wordings(P,L):
					if C(Q):_f(A,'CASE_LAW_IN_WORDING','error','אזכור פסיקה בנוסח: פסיקה אינה נכנסת לנוסח מוצע או לנוסח נסיגה.',B.get('rule_id'),L)
		for(G,H)in _texts(core or{},'core'):
			if C(H):_f(A,'CASE_LAW_IN_WORDING','error','%s: פסיקה אינה נכנסת לגרעין.'%G)
	return A
def jurisdiction_findings(model):
	'GOVERNING_LAWS_MISSING (אזהרה): אין scope_summary.governing_laws[]. OVERRIDE_NO_JURISDICTION (אזהרה): חובה\n    בדין או שכבת statute בלי jurisdiction, ולכן הרכיבים הקוראים אינם יכולים להחיל אותה רק בדין הנכון.';E=model;A=[]
	if not(E.get('scope_summary')or{}).get('governing_laws'):_f(A,'GOVERNING_LAWS_MISSING','warning','חסר scope_summary.governing_laws[] (קודים: IL, GB-EAW, US-NY, DE), מההסכמים של הסוג.')
	for B in E.get('rules')or[]:
		for D in B.get('statutory_override')or[]:
			if isinstance(D,dict)and not str(D.get('jurisdiction')or'').strip():_f(A,'OVERRIDE_NO_JURISDICTION','warning','חובה בדין (%s) בלי jurisdiction.'%(D.get('statute')or'?'),B.get('rule_id'))
		for C in B.get('legal_basis_layers')or[]:
			if isinstance(C,dict)and C.get('layer')=='statute'and not str(C.get('jurisdiction')or'').strip():_f(A,'OVERRIDE_NO_JURISDICTION','warning','שכבת statute (%s) בלי jurisdiction.'%(C.get('statute')or'?'),B.get('rule_id'))
	return A
UNIT_WORDS={'business_days':'ימי\\s+עבודה|ימי\\s+עסקים|business\\s+days?|working\\s+days?','days':'ימים|יום|days?','hours':'שעות|שעה|hours?','months':'החודשים|חודשים|חודשי|חודש|months?','years':'השנים|שנים|שנה|years?','percent':'%|אחוזים|אחוז|percent','times_per_year':'פעמים\\s+בשנה|פעם\\s+בשנה|times\\s+(?:a|per)\\s+year|per\\s+year|annually'}
_NUM_UNIT=re.compile('(?<![\\d.,])(\\d+(?:[.,]\\d+)?)\\s*(?:\\)\\s*)?(?:[-\\s]?(?:calendar\\s+)?)('+'|'.join('(?:%s)'%A for A in UNIT_WORDS.values())+')(?![\\w])',re.I)
LEGAL_CORE_FIELDS='governing_rule','decisive_distinction','consequence_for_company','interplay','verification'
LEGAL_CORE_VERIFY='statute_text','case_law_connector','legal_review_required','expert_assessment'
LEGAL_KINDS='משפטי','legal'
REVIEW_LABELS='טעון בדיקה משפטית','Needs legal review','Legal review required','טעון אימות','Needs verification'
RATIONALE_FIELDS='executive_policy_rationale','protected_interest_and_clause_purpose','legal_risk_and_legal_framework','contractual_risk_allocation_mechanism','company_role_and_policy_fit','business_operational_impact','green_boundary_rationale','yellow_boundary_rationale','red_boundary_rationale','tradeoff_statement'
TRACK_TEXT_FIELDS='company_effect','comments','notes'
NEAR_DUP_RATIO=.9
NEAR_DUP_MIN_CHARS=40
NEAR_DUP_ERROR_RULES=3
PUBLIC_KINDS='public_body','government_company','university'
PUBLIC_POWER_REMOVED=re.compile('(?:אינו|אינה|לא\\s+יהיה|לא\\s+תהיה)\\s+רשאי(?:ת)?\\s+(?:לסיים|לבטל|להביא\\s+את\\s+ההסכם\\s+לידי\\s+סיום)|אין\\s+(?:ל[א-ת]+\\s+)?זכות\\s+(?:סיום|ביטול)|(?:shall|will|may)\\s+(?:have\\s+)?no(?:t)?\\s+(?:right\\s+to\\s+)?terminat|may\\s+not\\s+terminate|no\\s+right\\s+(?:of|to)\\s+terminat|צד\\s+חלופי|substitute\\s+party|replacement\\s+party',re.I)
def _norm_text(s):s=re.sub('[\\d]+','0',str(s or'').casefold());return' '.join(re.findall('\\w+',s))
def _num_units(text):
	'{unit: {numbers}} מהטקסט: מספר וליד היחידה (14 days, 30 יום, twenty-four (24) hours).';A={}
	for B in _NUM_UNIT.finditer(str(text or'')):
		D=B.group(2);C=next((A for(A,B)in UNIT_WORDS.items()if re.fullmatch(B,D,re.I)),None)
		if C:A.setdefault(C,set()).add(float(B.group(1).replace(',','.')))
	return A
def home_countries(model):
	'המדינות של הדין החל על הסכמי הסוג (scope_summary.governing_laws[]); בלעדיהן, מדינת ההתאגדות של הישות החותמת.\n    רשימה ריקה כשאין אף אחד מהם: אין הנחה של מדינה.';B=model;C=governing_countries(B)
	if C:return C
	A=(B.get('scope_summary')or{}).get('contracting_entity');D=A if isinstance(A,list)else[A];return list(dict.fromkeys(A for A in(country_code(A.get('incorporation_country'))for A in D if isinstance(A,dict))if A))
NO_SOURCE_NOTE={'he':'AREO לא מצאה מקור מורשה לנקודה זו','en':'AREO did not find an approved source for this point'}
RESEARCH_RAN='Performed','Completed','Partial'
def no_source_text(lang='he'):return NO_SOURCE_NOTE['en'if str(lang or'').lower().startswith('en')else'he']
def research_permitted(model):
	'True כשמחקר רשת הותר ורץ בפלייבוק הזה: מחקר עומק שהלקוח בחר (regulatory_research), או פלייבוק שנבנה לפי הרשת\n    והשוק לבקשת הלקוח (market_research). בלי אחד מהם אין מחקר, ואין מה לומר על מקור שלא נמצא.';A=model
	if not isinstance(A,dict):return False
	for C in('regulatory_research','market_research'):
		B=A.get(C)
		if isinstance(B,dict)and B.get('status')in RESEARCH_RAN:return True
	return False
def _open_legal_point(rule):
	'נושא שיש בו שאלה בדין שנשארה פתוחה: נושא משפטי, או שכבה "טעון בדיקה משפטית", בלי מקור מורשה שנקרא.';A=rule
	if A.get('regulatory_status')=='ApplicableSourcesFound'or A.get('regulatory_sources'):return False
	B=[A for A in A.get('legal_basis_layers')or[]if isinstance(A,dict)]
	if any(A.get('layer')=='statute'for A in B):return False
	C=str(A.get('clause_kind')or'')in LEGAL_KINDS;return C or any(A.get('layer')=='legal_review_required'for A in B)or bool(A.get('legal_review_required'))
def no_source_notes(model):
	'[(rule_id, topic_name, has_note)] לכל נושא שמחקר הרשת הותר בו ולא נמצא לו מקור מורשה.';B=model
	if not research_permitted(B):return[]
	C=[]
	for A in B.get('rules')or[]:
		if isinstance(A,dict)and _open_legal_point(A):D=str(A.get('no_source_note')or'');C.append((A.get('rule_id'),A.get('topic_name')or'',any(A in D for A in NO_SOURCE_NOTE.values())))
	return C
def no_source_findings(model):
	'NO_SOURCE_NOTE (אזהרה, לעולם אינה חוסמת): נושא עם שאלה בדין שלא נמצא לה מקור מורשה, ובלי ההערה הגלויה.';A=model;B=[];C=(A or{}).get('output_language')or'he'
	for(D,E,F)in no_source_notes(A):
		if not F:_f(B,'NO_SOURCE_NOTE','warning','הנושא "%s": מחקר הרשת הותר ולא נמצא מקור מורשה. רשמו ב-no_source_note "%s" (ולא ממלאים את החסר מהזיכרון).'%(E,no_source_text(C)),D)
	return B
DOCUMENT_BASES={'green':('template','own_paper_repeated','documents_majority','company_request'),'yellow':('established','single','offered_unexecuted'),'red':('company_source','struck','rejected_comment','never_accepted','bid_condition')}
def _evidence_index(rule,model):
	'{מזהה: ראיה} לפי evidence_id בכלל (ובווריאנטים) ו-citation_id ב-citations[] של המודל.';C={}
	for A in list(rule.get('evidence')or[])+[B for A in rule.get('segment_variants')or[]if isinstance(A,dict)for B in A.get('evidence')or[]]:
		if isinstance(A,dict):
			for D in('evidence_id','citation_id'):
				if A.get(D):C.setdefault(str(A[D]),A)
	for B in model.get('citations')or[]:
		if isinstance(B,dict)and B.get('citation_id'):C.setdefault(str(B['citation_id']),B)
	return C
def position_sources(rule,model,t):
	'[{evidence_id, source_id, agreement, clause}] של עמדה אחת: ההסכם (source_log) והסעיף שעליהם basis_refs נשען.\n    ref שאינו נפתר לראיה מדולג (ממצא ב-position_source_findings). משמש גם את גרעין ההפעלה ואת התצוגות.';D=model;G=_evidence_index(rule,D);H={A.get('source_id'):A for A in D.get('source_log')or[]if isinstance(A,dict)};E=[]
	for F in t.get('basis_refs')or[]:
		A=G.get(str(F))
		if not A:continue
		B=str(A.get('source_ref')or'').split('#')[0];C=H.get(B)or{};E.append({'evidence_id':str(F),'source_id':B,'agreement':C.get('short_name')or C.get('title')or C.get('file')or B,'clause':str(A.get('clause_ref')or'').strip()})
	return E
def position_source_findings(model):
	'SOURCE_NOT_SHOWN: עמדה שנגזרה ממסמכי הלקוח (DOCUMENT_BASES) שאין לה basis_refs, או ש-ref אינו נפתר לראיה, או\n    שבראיה חסר ההסכם (source_ref) או הסעיף (clause_ref), או שההסכם אינו ב-source_log. כל מסלול, בכל כלל ובכל וריאנט.';G=model;C=[];J={A.get('source_id')for A in G.get('source_log')or[]if isinstance(A,dict)}
	for A in G.get('rules')or[]:
		if not isinstance(A,dict):continue
		M=_evidence_index(A,G)
		for(K,B,F)in _iter_tracks(A):
			if not F or F.get('basis')not in DOCUMENT_BASES.get(B,()):continue
			D='%s%s'%(B,' (%s)'%K if K else'');L=[A for A in F.get('basis_refs')or[]if str(A).strip()]
			if not L:_f(C,'SOURCE_NOT_SHOWN','error','עמדת %s נשענת על מסמכי הלקוח (%s) ואין לה basis_refs: איזה הסכם ואיזה סעיף?'%(D,F.get('basis')),A.get('rule_id'),B);continue
			for E in L:
				H=M.get(str(E))
				if H is None:_f(C,'SOURCE_NOT_SHOWN','error','עמדת %s: basis_refs "%s" אינו ראיה ברשימת הראיות של הכלל.'%(D,E),A.get('rule_id'),B);continue
				I=str(H.get('source_ref')or'').split('#')[0]
				if not I:_f(C,'SOURCE_NOT_SHOWN','error','עמדת %s: בראיה %s חסר ההסכם (source_ref).'%(D,E),A.get('rule_id'),B)
				elif J and I not in J:_f(C,'SOURCE_NOT_SHOWN','error','עמדת %s: ההסכם %s של הראיה %s אינו ב-source_log.'%(D,I,E),A.get('rule_id'),B)
				if not str(H.get('clause_ref')or'').strip():_f(C,'SOURCE_NOT_SHOWN','error','עמדת %s: בראיה %s חסר הסעיף (clause_ref).'%(D,E),A.get('rule_id'),B)
	return C
def coverage_ledger(model):
	'הספר, מספרים בלבד: clauses (כל הסעיפים בכל ההסכמים), with_policy (ממופים לנושא), no_extractable_policy\n    (טכניים ושלא מופו, כולם רשומים במפורש), unique_pending (ייחודיים, ממתינים להכרעה בתור), unassigned (בלי כלום),\n    listed_no_policy (כמה מהם נרשמו בפועל ברשימה המפורשת), agreements (מספר ההסכמים) ו-balanced.\n    None כשאין coverage.';A=(model or{}).get('coverage')
	if not isinstance(A,dict):return
	def B(n,a):B=_cov_num(A,n,a);return B if isinstance(B,int)and not isinstance(B,bool)else 0
	F,G=B('units','units_total'),B('topic_units','units_mapped');C,D=B('technical_units','units_technical'),B('unmapped_units','units_unmapped');H,E=B('unique_units','units_unique'),B('unassigned_units','units_unassigned');J=A.get('technical_items')if isinstance(A.get('technical_items'),list)else[];I=sum(len(A.get('refs')or[])for A in J if isinstance(A,dict))+len(A.get('unmapped')if isinstance(A.get('unmapped'),list)else[]);K=A.get('by_agreement')if isinstance(A.get('by_agreement'),list)else[];return{'clauses':F,'with_policy':G,'no_extractable_policy':C+D,'unique_pending':H,'unassigned':E,'listed_no_policy':I,'agreements':len(K),'balanced':F==G+C+D+H+E and E==0 and I==C+D}
def coverage_ledger_findings(model):
	'COVERAGE_LEDGER: הספר אינו מסתכם (סעיפים שונים מסכום החלקים, סעיף בלי שיוך, או סעיף "בלי מדיניות" שלא נרשם\n    במפורש), או שסכום הסעיפים לפי הסכם שונה מהסך. COVERAGE_LEDGER_AGREEMENT: שורת הסכם שאינה מסתכמת.';F=model;B=[];A=coverage_ledger(F)
	if A is None:return B
	G=A['with_policy']+A['no_extractable_policy']+A['unique_pending']+A['unassigned']
	if A['clauses']!=G:_f(B,'COVERAGE_LEDGER','error','ספר הכיסוי אינו מסתכם: %d סעיפים, ו-%d עם מדיניות + %d בלי מדיניות שאפשר לחלץ + %d ייחודיים + %d בלי שיוך.'%(A['clauses'],A['with_policy'],A['no_extractable_policy'],A['unique_pending'],A['unassigned']))
	elif A['unassigned']:_f(B,'COVERAGE_LEDGER','error','%d סעיפים בלי מדיניות ובלי רישום מפורש כ"אין מדיניות שאפשר לחלץ".'%A['unassigned'])
	if A['listed_no_policy']!=A['no_extractable_policy']:_f(B,'COVERAGE_LEDGER','error','%d סעיפים הוגדרו "אין מדיניות שאפשר לחלץ", ו-%d מהם רשומים במפורש (technical_items[].refs ו-unmapped[]). כל סעיף כזה נרשם בשמו.'%(A['no_extractable_policy'],A['listed_no_policy']))
	D=[A for A in(F.get('coverage')or{}).get('by_agreement')or[]if isinstance(A,dict)]
	if D and all(isinstance(A.get('units'),int)for A in D):
		if sum(A['units']for A in D)!=A['clauses']:_f(B,'COVERAGE_LEDGER','error','סכום הסעיפים לפי הסכם הוא %d, והסך הכול %d.'%(sum(A['units']for A in D),A['clauses']))
	for E in D:
		C=[E.get(A)for A in('mapped','technical','unique','unmapped','unassigned')]
		if all(isinstance(A,int)for A in C[:4])and isinstance(E.get('units'),int):
			if sum(A for A in C if isinstance(A,int))!=E['units']:_f(B,'COVERAGE_LEDGER_AGREEMENT','error','בהסכם %s: %d סעיפים, ו-%d ממופים + %d טכניים + %d ייחודיים + %d לא ממופים + %d בלי שיוך.'%(E.get('source_id'),E['units'],C[0],C[1],C[2],C[3],C[4]or 0))
	return B
def coverage_ledger_lines(model,lang='he'):
	'שורה ללקוח על הספר, בקול של מנהל מוצר: התוצאה קודם. [] כשאין coverage.';A=coverage_ledger(model)
	if not A:return[]
	if str(lang or'').lower().startswith('en'):
		B='We went through all %d clauses in %d agreements. %d have a policy.'%(A['clauses'],A['agreements'],A['with_policy'])
		if A['no_extractable_policy']:B+=' %d are listed one by one as having no policy to extract.'%A['no_extractable_policy']
		if A['unique_pending']:B+=' %d unique clauses wait for your decision.'%A['unique_pending']
	else:
		B='עברנו על כל %d הסעיפים ב-%d הסכמים. ל-%d מהם יש מדיניות.'%(A['clauses'],A['agreements'],A['with_policy'])
		if A['no_extractable_policy']:B+=' %d רשומים אחד אחד כסעיפים שאין להם מדיניות שאפשר לחלץ.'%A['no_extractable_policy']
		if A['unique_pending']:B+=' %d סעיפים ייחודיים ממתינים להכרעה שלכם.'%A['unique_pending']
	return[B]
def sufficiency_findings(model):
	'הבדיקה של playbook/sufficiency.py כממצאי מאמת: SUFFICIENCY_NOT_ASKED, SUFFICIENCY_STALE.'
	try:from playbook import sufficiency as B
	except ImportError:return[]
	A=[]
	for(C,D,E)in B.findings(model):_f(A,C,D,E)
	return A
def _dup_groups(items):
	'[(text, rule_id)] -> קבוצות של כללים שהטקסט שלהם כמעט זהה (יחס דמיון מעל NEAR_DUP_RATIO).';import difflib as F;C=[]
	for(E,A)in items:
		D=_norm_text(E)
		if len(D)<NEAR_DUP_MIN_CHARS:continue
		for B in C:
			if B['rule_ids'][-1]!=A and F.SequenceMatcher(None,B['norm'],D).ratio()>=NEAR_DUP_RATIO:
				if A not in B['rule_ids']:B['rule_ids'].append(A)
				break
		else:C.append({'norm':D,'text':str(E),'rule_ids':[A]})
	return[A for A in C if len(A['rule_ids'])>1]
def rationale_findings(model):
	'RATIONALE_DUPLICATE: אותו נימוק, או אותה שורת השפעה על החברה או הערת מסלול, כמעט מילה במילה (דמיון מעל 90%\n    אחרי נרמול מספרים ופיסוק) ב-3 כללים או יותר (error), או בשניים (warning). שדה כזה נכתב לכל כלל, או נמחק.\n    LEGAL_CORE_MISSING: כלל ש-clause_kind שלו משפטי בלי שלד משפטי מלא (legal_core: governing_rule,\n    decisive_distinction, consequence_for_company, interplay, verification). LEGAL_CORE_REVIEW_ONLY: governing_rule\n    שאינו אלא התווית "טעון בדיקה משפטית", בלי מה שמעורר את השאלה. LEGAL_CORE_STATUTE: verification: statute_text בלי\n    שכבת statute עם סעיף ב-legal_basis_layers[].';E=[];M=[A for A in model.get('rules')or[]if isinstance(A,dict)];F={}
	for A in M:
		C=A.get('rule_id');N=A.get('policy_rationale')if isinstance(A.get('policy_rationale'),dict)else{}
		for B in RATIONALE_FIELDS:
			if isinstance(N.get(B),str):F.setdefault('policy_rationale.'+B,[]).append((N[B],C))
		D=A.get('legal_core')if isinstance(A.get('legal_core'),dict)else{}
		for B in('decisive_distinction','consequence_for_company'):
			if isinstance(D.get(B),str):F.setdefault('legal_core.'+B,[]).append((D[B],C))
		for I in TRACKS:
			H=(A.get('traffic_light')or{}).get(I)or{}
			for B in TRACK_TEXT_FIELDS:
				if isinstance(H.get(B),str):F.setdefault('%s.%s'%(I,B),[]).append((H[B],C))
			for(J,G)in(H.get('role_effects')or{}).items()if isinstance(H.get('role_effects'),dict)else():
				if isinstance(G,str):F.setdefault('%s.role_effects.%s'%(I,J),[]).append((G,C))
		for(J,G)in(A.get('role_effects')or{}).items()if isinstance(A.get('role_effects'),dict)else():
			if isinstance(G,str):F.setdefault('role_effects.'+str(J),[]).append((G,C))
	for(Q,R)in F.items():
		for K in _dup_groups(R):O=len(K['rule_ids']);_f(E,'RATIONALE_DUPLICATE','error'if O>=NEAR_DUP_ERROR_RULES else'warning','%s כמעט זהה ב-%d כללים (%s): "%s". נימוק ושורת השפעה נכתבים לכל כלל לפי הנושא, או נמחקים.'%(Q,O,', '.join(str(A)for A in K['rule_ids'][:8]),K['text'][:80]))
	for A in M:
		C=A.get('rule_id')
		if str(A.get('clause_kind')or'').strip().lower()not in LEGAL_KINDS:continue
		D=A.get('legal_core')if isinstance(A.get('legal_core'),dict)else{};P=[A for A in LEGAL_CORE_FIELDS if not str(D.get(A)or'').strip()]
		if P:_f(E,'LEGAL_CORE_MISSING','error','כלל משפטי בלי שלד משפטי מלא: חסר %s (policy-rationale.md, "השלד המשפטי של כל נושא").'%', '.join(P),C);continue
		if D.get('verification')not in LEGAL_CORE_VERIFY:_f(E,'LEGAL_CORE_MISSING','error','legal_core.verification "%s" (%s).'%(D.get('verification'),' | '.join(LEGAL_CORE_VERIFY)),C)
		S=str(D.get('governing_rule')or'');L=S
		for T in REVIEW_LABELS:L=L.replace(T,'')
		if len(_norm_text(L))<15:_f(E,'LEGAL_CORE_REVIEW_ONLY','error','governing_rule הוא רק התווית: "טעון בדיקה משפטית" אינו מחליף ניתוח. כתוב את הכלל או המנגנון שקובע את התוצאה, ומה בהסכם מעורר את השאלה.',C)
		if D.get('verification')=='statute_text'and not any(isinstance(A,dict)and A.get('layer')=='statute'and A.get('section')for A in A.get('legal_basis_layers')or[]):_f(E,'LEGAL_CORE_STATUTE','error','verification: statute_text בלי שכבת statute עם סעיף ב-legal_basis_layers[].',C)
	return E
def fallback_findings(model):
	'TRACK_WORDING_MISMATCH: התיאור של המסלול (position) והנוסח שלו (proposed_clause, ובצהוב גם fallback_wording)\n    נוקבים במספר אחר באותה יחידה (התיאור 14 יום, הנוסח 30 יום), בכל כלל ובכל וריאנט.\n    COUNTERPARTY_UNREALISTIC: מול צד שכנגד שהוא גוף ציבורי, חברה ממשלתית או מוסד להשכלה גבוהה\n    (applicability.counterparty_kinds או counterparty_kind של הווריאנט), צהוב או נוסח נסיגה שמסיר סמכות שהגוף אינו יכול\n    לוותר עליה (סיום מטעמי ציבור או תקציב, החלפת הצד בלי הליך תחרותי): error; בירוק: warning.\n    CONCERN_UNMAPPED (אזהרה): חשש של הלקוח (scope_summary.client_concerns[]) בלי כלל קיים ב-mapped_rule_ids.';B=model;F=[];T=B.get('applicability')if isinstance(B.get('applicability'),dict)else{};M=set(T.get('counterparty_kinds')or[]);U={A.get('rule_id')for A in B.get('rules')or[]if isinstance(A,dict)};N={}
	for G in(B.get('segmentation_model')or{}).get('segments')or[]if isinstance(B.get('segmentation_model'),dict)else[]:
		if isinstance(G,dict)and G.get('segment_id'):H=G.get('counterparty_kind');N[G['segment_id']]=set(H if isinstance(H,list)else[H]if H else[])
	for J in B.get('rules')or[]:
		if not isinstance(J,dict):continue
		O=J.get('rule_id')
		for(D,A,C)in _iter_tracks(J):
			if not C:continue
			V=_num_units(C.get('position'))if A!='red'else{}
			for(W,X)in _wordings(C,A):
				K=_num_units(W)
				for(E,P)in V.items():
					if E in K and not P&K[E]:_f(F,'TRACK_WORDING_MISMATCH','error','במסלול %s%s התיאור נוקב ב-%s %s, והנוסח אינו נוקב בהם (בנוסח: %s %s). הנוסח ותיאורו אומרים אותו דבר.'%(A,', '+D if D else'','/'.join('%g'%A for A in sorted(P)),E,'/'.join('%g'%A for A in sorted(K[E])),E),O,A);break
			I=N.get(D,set())if D else M
			if D and not I:I=M
			if I&set(PUBLIC_KINDS):
				Q=[str(C.get('position')or'')]+[A for(A,B)in _wordings(C,A)]
				for R in C.get('fallback_steps')or[]:
					if isinstance(R,dict):Q.append(str(R.get('text')or''))
				S=next((PUBLIC_POWER_REMOVED.search(A)for A in Q if PUBLIC_POWER_REMOVED.search(A)),None)
				if S and A!='red':_f(F,'COUNTERPARTY_UNREALISTIC','error'if A=='yellow'else'warning','מול %s, המסלול %s מסיר סמכות שגוף כזה אינו יכול לוותר עליה ("%s"). הצהוב והנסיגה נבנים סביב המחיר של הסמכות (הודעה מוקדמת, פיצוי על השקעה שלא הוחזרה, תשלום על עבודה שבוצעה), ולא סביב ביטולה (clause-catalog.md, "Public body").'%(', '.join(sorted(I&set(PUBLIC_KINDS))),A,S.group(0)),O,A)
	for L in(B.get('scope_summary')or{}).get('client_concerns')or[]:
		if not isinstance(L,dict):continue
		if not any(A in U for A in L.get('mapped_rule_ids')or[]):_f(F,'CONCERN_UNMAPPED','warning','חשש של הלקוח ("%s") בלי כלל בפלייבוק: מפה אותו לכלל, או רשום אותו בשאלות הפתוחות.'%str(L.get('text')or'')[:60])
	return F
def validate(model,core=None,index_entry=None,check_wording=True,inventory=None,extract=None,approved_sources=None):
	c=index_entry;K=core;B=model;A=coverage_findings(B,inventory=inventory,extract=extract);A+=coverage_ledger_findings(B);A+=department_findings(B);A+=source_findings(B,approved_sources);A+=case_law_findings(B,K);A+=jurisdiction_findings(B);A+=no_source_findings(B);A+=position_source_findings(B);A+=sufficiency_findings(B);A+=rationale_findings(B);A+=fallback_findings(B);D=B.get('rules')or[];T={A.get('id')or A.get('rule_id'):A for A in(K or{}).get('clauses')or[]};N=[A for A in D if bool(_core_val(A,T,'walk_away'))]
	if D and len(N)==len(D):_f(A,'WALKAWAY_ALL','error','כל %d הכללים מסומנים שובר עסקה: אין מרחב ויתור. שובר עסקה רק לשובר עסקה אמיתי.'%len(D))
	for C in N:
		if _imp(C)!='critical':_f(A,'WALKAWAY_NOT_CRITICAL','error','שובר עסקה בכלל בחשיבות "%s".'%_imp(C),C['rule_id'])
		if _core_val(C,T,'walk_away_source')not in WALK_SOURCES:_f(A,'WALKAWAY_NO_SOURCE','error','שובר עסקה בלי walk_away_source (חובה בדין, מסמך של החברה, או תשובת הלקוח).',C['rule_id'])
	if len(N)>MAX_WALK_AWAY:_f(A,'WALKAWAY_TOO_MANY','warning','%d שוברי עסקה (המלצה: עד %d).'%(len(N),MAX_WALK_AWAY))
	d=[A for A in D if _core_val(A,T,'round1_posture')=='hold_green']
	if D and len(d)==len(D):_f(A,'HOLD_GREEN_ALL','error','כל הכללים hold_green בסבב הראשון: הנושא ונותן אינו יכול לבנות תגובה ממוקדת.')
	for C in d:
		if _imp(C)=='low':_f(A,'HOLD_GREEN_LOW','error','hold_green בכלל בחשיבות נמוכה: בסבב הראשון מציעים צהוב.',C['rule_id'])
	O=[A for(A,B)in company_roles(B)];t=role_code(B)=='mutual'or len(O)>1
	for C in D:
		e=C.get('traffic_light')or{};U,f=e.get('green')or{},e.get('yellow')or{}
		if U.get('position')and U['position'].strip()==(f.get('position')or'').strip():_f(A,'YELLOW_EQUALS_GREEN','error','הצהוב זהה לירוק: אין מרחב ויתור.',C['rule_id'])
		G=f.get('fallback_wording');G=G.get('text')if isinstance(G,dict)else G;F=U.get('proposed_clause');F=F.get('he')or F.get('en')if isinstance(F,dict)else F
		if G and F and G.strip()==F.strip():_f(A,'FALLBACK_EQUALS_GREEN','error','נוסח הנסיגה זהה לנוסח הירוק.',C['rule_id'])
		for(_,H,V)in _iter_tracks(C):
			if V.get('protects_main_role')is False:_f(A,'YELLOW_WORSENS_MAIN_ROLE','error','המסלול %s סומן כפוגע בתפקיד העיקרי של החברה.'%H,C['rule_id'],H)
			if t and V.get('position'):
				if len(O)<2:_f(A,'ROLE_EFFECT_MISSING','error','לחברה יותר מתפקיד אחד בהסכם, ונמצאה שורת השפעה לתפקיד אחד בלבד (%s) במסלול %s.'%(', '.join(O),H),C['rule_id'],H)
				for g in O:
					if not role_effect(V,g):_f(A,'ROLE_EFFECT_MISSING','error','חסרה שורת ההשפעה של התפקיד %s במסלול %s.'%(g,H),C['rule_id'],H)
	if check_wording:A+=wording_findings(B)
	h=[('model',B),('core',K),('index',c)]
	if isinstance(B.get('handoff'),dict):h.append(('handoff',B['handoff']))
	for(W,P)in h:
		if not P:continue
		for i in S.DUAL_FIELDS:
			if i in P:_f(A,'LABEL_DUAL_FIELD','error','%s.%s: שדה תווית כפול. התווית היחידה היא status_label, שנגזרת ב-status.derive_status.'%(W,i))
	for(j,u)in S.label_findings(B,K,c):_f(A,j,'warning'if j=='LABEL_OLD_WORDING'else'error',u)
	for(W,P)in(('model',B),('core',K)):
		for X in _approver_paths(P or{}):_f(A,'APPROVER_FIELD','error','%s.%s: שדה מאשר או הסלמה. אין שרשרת אישורים: ויתור מעבר לצהוב או חציית אדום מוצגים למשתמש כ"נדרשת הכרעתך". החתימה של היועץ המשפטי על הגיליון נשארת.'%(W,X))
	I=B.get('market_research')or{};Q=I.get('source_refs')or I.get('sources')or[];Y=(I.get('question')or{}).get('engagement_purpose')or(B.get('applicability')if isinstance(B.get('applicability'),dict)else{}).get('engagement_purpose')
	if Q and Y:
		E={}
		for J in Q:
			if not J.get('engagement_purpose'):continue
			k=J.get('template_family')or J.get('family')or J.get('source_id')or J.get('id');E[k]=E.get(k,True)and J['engagement_purpose']!=Y
		if E and all(E.values()):_f(A,'MARKET_SAMPLE_PURPOSE','error','כל משפחות המקורות ממטרת התקשרות אחרת ממטרת הפלייבוק (%s). נדרשת לפחות משפחה אחת ממטרה זהה.'%Y)
		elif E and sum(E.values())*2>len(E):_f(A,'MARKET_SAMPLE_PURPOSE','warning','רוב משפחות המקורות (%d מתוך %d) ממטרת התקשרות אחרת: לשקלל או להוציא.'%(sum(E.values()),len(E)))
	if Q:
		L=governing_countries(B);R=((B.get('scope_summary')or{}).get('contracting_entity')or{}).get('incorporation_country')
		if not L and country_code(R):L=[country_code(R)]
		if not L:_f(A,'MARKET_NO_HOME_COUNTRY','warning','אין scope_summary.governing_laws[] ואין contracting_entity.incorporation_country מזוהה (%s): נדרש קוד (IL, GB-EAW, US-NY, DE) כדי לבדוק מקור שוק מתחום השיפוט.'%('חסר'if not str(R or'').strip()else R))
		else:
			v=any(_country_of(A.get('jurisdiction'))in L for A in Q)
			if not v and not I.get('jurisdiction_note'):_f(A,'MARKET_NO_LOCAL_SOURCE','error','אין מקור שוק מ-%s, ואין jurisdiction_note שאומר זאת ("לא נמצא נוסח <הסוג> מ-<תחום השיפוט> שפורסם; העמדות התלויות בדין סומנו טעון בדיקה משפטית").'%', '.join(L))
	Z=MC.counts(B)
	if'counted'in Z:
		l=I.get('disclosure')or{};w=[('market_research.disclosure.fixed_sentence',l.get('fixed_sentence')),('market_research.disclosure.chat_message',l.get('chat_message')),('meta.evidence_disclaimer',(B.get('meta')or{}).get('evidence_disclaimer'))]
		for(x,y)in w:
			for X in MC.count_claims(y or'',B):_f(A,'MARKET_COUNT_MISMATCH','error','%s: %s'%(x,X))
		a=B.get('handoff')or{}
		if isinstance(a.get('counted_sources'),int)and a['counted_sources']!=Z['counted']:_f(A,'MARKET_COUNT_MISMATCH','error','handoff.counted_sources=%d, ובספירה counted=%d'%(a['counted_sources'],Z['counted']))
	for b in I.get('unverified_findings')or[]:
		m=' '.join(A for A in(b.get('label'),b.get('reason'))if A)
		if re.search('(?<!\\d)1 מקורות|\\(\\s*\\)',m):_f(A,'UNVERIFIED_LABEL_FORMAT','error','התווית "%s": "מקור אחד (W..)", בלי סוגריים ריקים.'%m,b.get('rule_id'))
	z=(B.get('regulatory_research')or{}).get('facts')or[];n=set()
	for M in z:
		o=M.get('fact_id')or M.get('id');p=M.get('official_source')or{}
		if not p.get('url')or not M.get('currency_check'):_f(A,'LEGAL_FACT_SOURCE','error','עובדת דין %s: נדרש מקור רשמי אחד עם קישור, ובדיקת עדכניות (הנוסח בתוקף ביום המחקר).'%o);continue
		q=M['currency_check'];A0=str(p.get('version_date')or'');A1=[A for A in q.get('amendments_after_version')or[]if str(A.get('in_force')or'')>A0]
		if A1 or q.get('result')=='outdated':n.add(o)
	for C in D:
		for r in C.get('statutory_override')or[]:
			if r.get('fact_id')in n:_f(A,'LEGAL_FACT_STALE','error','"חובה בדין" נשענת על נוסח שקודם לתיקון (%s). מסמנים "טעון בדיקה משפטית" עד שנקרא הנוסח בתוקף.'%r['fact_id'],C['rule_id'])
	A2=json.dumps(B,ensure_ascii=False)
	for s in FORBIDDEN:
		if terms_re([s]).search(A2):_f(A,'FORBIDDEN_LABEL','error','התווית "%s" אסורה. "לא אומת" עם מספר המקורות והסיבה, או מקור רשמי אחד עם בדיקת עדכניות לעובדת דין.'%s)
	A3=B.get('produced_with')or{}
	if not all(A3.get(A)for A in('skill_version','notes_version','refs_sha256')):_f(A,'PRODUCED_WITH','error','חסר produced_with {skill_version, notes_version, refs_sha256}.')
	return A
def errors(findings):return[A for A in findings if A['severity']=='error']
def codes(findings,severity=None):A=severity;return{B['code']for B in findings if A is None or B['severity']==A}
