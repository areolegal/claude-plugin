# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as _dt,json,os,re
from lxml import etree
from common import docx_tracked as dt
from common import gap_checks
from common import ids
from common import paths
from common.case_law import case_law_mentions
from common.terms import terms_re
from orchestrator import pre_send
from orchestrator import state_builder as SB
from orchestrator.question_batch import ROUND_MATRIX,REPLACES_SENT,_sentences as qb_sentences
W=dt.W
LONG_DASH=re.compile('[–—]')
def case_law_in_text(text):return case_law_mentions(text or'')
FORBIDDEN_TERMS='פלייבוק','playbook','קו אדום','red line','fallback','עמדת נסיגה','נסיגה','רזרבה','פלייבוק מוצע','מחקר שוק','industry standard','ירוק','צהוב','נדרשת הכרעתך','לאישורך','לא מוסכם','כלל קבוע','בכל ההתקשרויות שלנו'
FORBIDDEN_TERM_RE=terms_re(FORBIDDEN_TERMS,regex_terms=('market (practice|standard)',))
FORBIDDEN_CODES=re.compile('\\b(R|V|Q|SEG|DS|LG|PB|OS|EMP)-?\\d+\\b|\\b[AR][123]\\b|\\bN1\\b|https?://|APR-|קטגוריה\\s*\\d',re.I)
class _Either:
	def __init__(A,*B):A.rxs=B
	def search(B,text):A=[A for A in(A.search(text)for A in B.rxs)if A];return min(A,key=lambda m:m.start())if A else None
FORBIDDEN_ALWAYS=_Either(FORBIDDEN_TERM_RE,FORBIDDEN_CODES)
FORBIDDEN_UNLESS_CLAIM=terms_re(('מדיניות','policy'))
INSURANCE_CONTEXT=re.compile('insur|\\bpremiums?\\b|underwrit|policyholder',re.I)
INSURANCE_POLICY=re.compile('\\b(insurance|insurer\\W?s?|liability|indemnity|cyber|E&O|D&O)\\s+polic(y|ies)\\b|\\bpolic(y|ies)\\s+(of|for)\\s+insurance\\b',re.I)
def policy_claim_term(text):
	A=text
	for B in FORBIDDEN_UNLESS_CLAIM.finditer(A or''):
		if B.group(0).lower().startswith('polic'):
			C=max(A.rfind('.',0,B.start()),A.rfind(';',0,B.start()))+1;D=min([A for A in(A.find('.',B.end()),A.find(';',B.end()))if A>=0]or[len(A)])
			if INSURANCE_POLICY.search(A[C:D])or INSURANCE_CONTEXT.search(A[C:D]):continue
		return B
PRACTICE_OPENING={'he':re.compile('^\\s*(אנחנו נוהגים|אנו נוהגים|כמקובל|בהתאם לנוהג|כנהוג)'),'en':re.compile('^\\s*(As is customary|In line with (our|market) practice|As standard|We (normally|usually|always) )',re.I)}
ENTITY_NAME_EN_PLACEHOLDER='[Company registered English name]'
OUR_PH=re.compile('\\[להשלים\\]|\\[to complete\\]|\\[to be completed\\]|\\[●\\]|\\[\\s*\\d[\\d,.\\s]*\\]|\\[[^\\]\\n]{1,40}\\]')
UNDERSCORES=re.compile('_{3,}')
THEIR_PH=re.compile('_{3,}|\\[[^\\]\\n]{0,40}\\]')
COMPANY_NO={'he':re.compile('(ח\\.?\\s?פ\\.?|ע\\.?\\s?מ\\.?|מספר (?:חברה|תאגיד))\\s*:?\\s*\\[?\\s*(?P<num>\\d[\\d\\s\\-]{5,12}\\d)\\s*\\]?'),'en':re.compile('(company (?:number|no\\.?)|registration (?:number|no\\.?)|reg\\. no\\.)\\s*:?\\s*\\[?\\s*(?P<num>\\d[\\d\\s\\-]{5,12}\\d)\\s*\\]?',re.I)}
SENT_END=re.compile('[.?!](\\s|$)')
_REF_NUM='\\d{1,3}(?:\\.\\d{1,3})*[א-ת]?(?:\\s?\\([a-zA-Z0-9א-ת]{1,4}\\))*'
CLAUSE_REF=re.compile("(?:(?<![א-ת])[ובלמהש]{0,2}(?:סעיפים|סעיף|ס\\'|תת-סעיף|נספחים|נספח|פרקים|פרק|תקנה|פסקה)|\\b(?:[Cc]lauses?|[Ss]ections?|[Pp]aragraphs?|[Pp]aras?\\.?|[Aa]nnex(?:es)?|[Ss]chedules?|[Aa]ppendi(?:x|ces)|[Aa]rticles?|[Ee]xhibits?))\\s*"+_REF_NUM+'(?:\\s*(?:,|ו-?|and|or|או|to|עד|-)\\s*'+_REF_NUM+')*')
OWN_NOT_POSSESSIVE="(?<!\\bits )(?<!\\btheir )(?<!\\bour )(?<!\\byour )(?<!\\bhis )(?<!\\bher )(?<!\\bmy )(?<!'s )(?<!’s )(?<!\\bone's )\\bowns?\\b"
NOT_COMPETITOR_HE='(?<!אינו )(?<!אינה )(?<!אינם )(?<!אין )(?<!ולא )(?<! לא )'
NOT_COMPETITOR_EN='(?<!not a )(?<!not an )(?<!nor a )(?<!\\bno )(?<!non-)'
_NOT_EXCL='לא','אחראי','אחראית','האחראי','האחראית','דעתו','דעתה','דעתם','דעתנו','הדעת','שיפוט','השיפוט','בעלים','הבעלים','סעד','הסעד','תרופה','התרופה','רכושו','רכושה','רכוש'
EXCLUSIVE_HE='בלעדיות|'+''.join('(?<!%s )(?<!%s ה)'%(A,A)for A in _NOT_EXCL)+'(?<![א-ת])ה?בלעדי(?:ת|ים|ות)?(?![א-ת])'
EXCLUSIVE_EN='\\bexclusivity\\b|(?<!non-)\\bexclusive\\b(?!\\s+(?:and\\s+\\w+\\s+)?(?:jurisdiction|remed(?:y|ies)|property|owner(?:ship)?|venue|forum|courts?))'
FUNCTIONS={'מחיר ותמורה':('תמורה|מחיר|דמי (רישיון|שימוש|תחזוקה|ניהול)|תעריף|הוצאות','תמור|מחיר|דמי|תעריפ|תעריף|הוצא|עלות|תשלום|ישול|תשלמו','\\bfees?\\b|\\bprice|\\brent\\b|\\bcharges?\\b|consideration|expenses','fee|price|rent|charge|consideration|expens|cost',True),'מועד התשלום':('(ישולם|ישולמו|תשולם|משולמת|ישלם|לשלם)[^.\\n]{0,60}\\d+\\s*(יום|ימים|ימי עסקים)|שוטף\\s*(\\+|פלוס)|(תשלום|ישולם|ישולמו|תשולם|ישלם|לשלם|בתנאי)[:\\s]{1,3}שוטף(?![\\u05d0-\\u05ea])','\\d+\\s*(יום|ימים)|ימי עסקים|ימים|שוטף','(payable|paid|pay)[^.\\n]{0,60}\\d+\\s*(calendar |business )?days|net\\s*\\d+','\\d+\\s*(calendar |business )?days|\\bdays\\b|\\bnet\\b',True),'ריבית והצמדה':('ריבית|פיגורים|הצמדה','ריבית|פיגור|הצמד','interest|late (payment )?(fee|charge)|indexation','interest|late|index',True),'קיזוז ועיכבון':('לקזז|קיזוז|עיכבון|לעכב','קיז|לקזז|עיכבון|לעכב|עיכוב','set[- ]?off|withhold|\\blien\\b','set[- ]?off|withhold|lien',True),'מס':('מע"מ|מס ערך מוסף|ניכוי מס','מע"מ|מס','\\bVAT\\b|\\btax','VAT|tax',True),'הגבלת אחריות':('תקרה|מוגבלת לסכום|לא תעלה על|נזק עקיף|תוצאתי|לא יישא באחריות','תקר|הגבל|מוגבל|לא תעלה|עקיף|תוצאתי|אחריות|פטור','liabilit[^.\\n]{0,60}(limited|exceed|cap)|indirect|consequential|not be liable','cap|limit|liab|indirect|consequential',True),'שיפוי וערבות':('ישפה|שיפוי|ערבות|ערובה|דרישה ראשונה|בטוחה|פיקדון','שיפוי|ישפה|לשפות|ערבות|ערובה|דרישה|בטוחה|פיקדון','indemnif|guarantee|security deposit|first demand|letter of credit','indemn|guarant|deposit|demand|security',True),'ביטוח':('ביטוח|פוליסה','ביטוח|פוליס','insurance|policy of insurance','insur',True),'קניין רוחני':('קניין רוחני|זכויות יוצרים|בעלות|מרגע היווצרם|ימחה','קניין|זכויות|בעלות|שייכ|המח|שלו|שלכם','intellectual property|ownership|'+OWN_NOT_POSSESSIVE+'|assigns? all','intellectual|own|assign',True),'היקף הרישיון':('להעברה|רישיונות משנה|רישיון משנה|בלתי חוזר|לצמיתות|כלל-עולמי','להעביר|העבר|רישיונות משנה|רישיון משנה|בלתי חוזר|לצמיתות|כלל-עולמי','transferable|sublicens|irrevocable|perpetual|worldwide','transfer|sublicens|irrevocab|perpetual|worldwide',True),'סודיות':('ישמור בסוד|חובת (ה)?סודיות|ישמור על סודיות|לא יגלה','סוד','in confidence|confidentiality obligations|shall not disclose|keep[^.\\n]{0,30}confidential','confiden',False),'מידע אישי ואבטחת מידע':('מידע אישי|פרטיות|אבטחת (ה)?מידע|מחוץ ל(מדינה|ישראל)|לחו"ל','מידע אישי|פרטיות|אבטח|עיבוד|מחוץ ל|חו"ל|העבר','personal data|privacy|data processing|security incident|de-identif|outside the country','personal|privacy|data|security|de-identif|transfer|abroad|outside',False),'מחיקה והחזרה':('ימחק|ישמיד|מחיקת|השמדת|יחזיר','מחק|מחיק|השמד|יושמד|יוחזר|החזר','\\bdelete|\\bdestroy|\\breturn (or|all)','delet|destroy|return',True),'הגבלת תחרות ובלעדיות':(NOT_COMPETITOR_HE+'מתחרה|תחרות|'+EXCLUSIVE_HE,'מתחר|תחרות|בלעדי|ניגוד עניינים','\\bcompet(e|es|ing|ition)\\b|'+NOT_COMPETITOR_EN+'\\bcompetitors?\\b|'+EXCLUSIVE_EN,'compet|exclusiv|conflict',True),'איסור שידול':('ישדל|שידול','שידול|ישדל|לגייס','solicit','solicit',True),'הסבה וקבלני משנה':('להסב|הסבה|להמחות|המחאה|קבלני? משנה','הסב|המח|קבלנ','\\bassign|subcontract','assign|subcontract',True),'סיום ותקופה':('רשאי לסיים|לבטל את ההסכם|בתוקפו|הארכ|חידוש|הודעה מוקדמת','סיום|לסיים|לבטל|ביטול|תקופ|הארכ|חידוש|הודעה','terminat|renew|term of this|notice period|prior notice','terminat|renew|term|notice',True),'דין ושיפוט':('יחול (ה)?דין|סמכות (ה)?שיפוט|בוררות|סעד (זמני|דחוף)|צו מניעה','דין|שיפוט|בורר|סעד|בית משפט|בתי המשפט','governed by|jurisdiction|venue|arbitrat|injunctive|interim relief','law|jurisdiction|venue|court|arbitrat|relief',True),'שפה גוברת':('הנוסח (העברי|האנגלי)','נוסח|שפה|גובר','prevail|translation','prevail|translat',False),'טיב ורמת שירות':('אחריות ל(טיב|תקינות)|רמת (ה)?שירות|פיצוי מוסכם|קנס|כמות שהוא|במיומנות','טיב|תקינות|רמת|פיצוי|קנס|כמות שהוא|מיומנות|מקצועיות','warrant|"as is"|service level|liquidated damages|penalt','warrant|as is|service level|liquidated|penalt',True),'שימוש במידע וכלים':('בינה מלאכותית|לאימון','בינה מלאכותית|אימון|כלי','artificial intelligence|\\bAI\\b|\\btrain','artificial|(?-i:\\bAI\\b)|\\btrain|\\btool',True),'ביקורת ופיקוח':('ישתף פעולה|זכות ביקורת|לערוך ביקורת|לבקר את','מבקר|ביקורת|רשו|פיקוח|שיתוף פעולה|תשתפו','right to (audit|inspect)|shall cooperate|audit rights','audit|inspect|regulat|cooperat',True)}
CONCEPTS_HE={B:(A[0],A[1],A[4])for(B,A)in FUNCTIONS.items()}
CONCEPTS_EN={B:(A[2],A[3],A[4])for(B,A)in FUNCTIONS.items()}
CONCEPTS=CONCEPTS_HE
NUMERIC_FUNCTIONS='מועד התשלום',
REASON={'he':re.compile('(?<![\\u05d0-\\u05ea])ו?(כדי|כי|שכן|לכן|בשל|בגלל|נועד\\w*|לפיכך|עקב|לאור|לנוכח|נוכח|בהינתן|שהרי|היות|לצורך|במטרה|מחמת|מטעמי)(?![\\u05d0-\\u05ea])|מאחר ש|מאחר ו|משום ש|מפני ש|הואיל ו|על כן|כך ש|כדי ש|מכיוון ש|מכיוון ו|על מנת|משום כך|בשל כך|מטעם זה|בשים לב ל|בהתחשב ב'),'en':re.compile('\\b(because|so that|since|in order to|to ensure|to avoid|so as to|given that|otherwise|therefore|hence|thus|as a result|for this reason|due to|owing to|in light of|in view of|which means|this means)\\b|\\bas (the|this|it|we|you|our|your|these|those|a|an|they|its|their|there|each|both)\\b|\\bgiven (the|its|their|our|this|these|those|how)\\b|(?:[,;]\\s*|^\\s*)so\\b(?!\\s+(?:far|long as|much|many)\\b)|(?<!\\bdo )(?<!\\bif )(?<!\\bor )(?<!\\bdone )(?<!\\bdoing )\\bso (the|that|it|we|you|they|each|both|any|its|their|our|your|neither|no|this|these|those|a|an)\\b',re.I)}
REASON_LEAD={'he':re.compile('^\\s*(זאת\\s+)?(כדי|כי|מאחר|משום|מפני|הואיל|שכן|לכן|הסיבה|היות|מכיוון|לאור|נוכח|לנוכח|בהינתן|לפיכך|על מנת)'),'en':re.compile('^\\s*(This is |That is |This )?(because|so that|since|in order|to ensure|the reason|given|as a result|for this reason|therefore|hence|this means|otherwise)',re.I)}
RIGHT_WORDS={'he':'רשאי|זכאי|תהיה זכות','en':'\\bmay\\b|entitled|right to'}
DELETION_CLAIM={'he':re.compile('^\\s*(מחקנו|הסרנו)'),'en':re.compile('^\\s*We (have )?(deleted|removed)',re.I)}
KNOWN_CLAIM={'he':re.compile('ידוע(ה|ים|ות)? מראש|סכום קבוע מראש'),'en':re.compile('known in advance|fixed in advance|known up front|a fixed amount',re.I)}
CAP_RX={'he':('אחריות','מוגבלת|תקרה|לא תעלה|לא יעלה','(ה)?(תמורה|מחיר|דמי \\S+) (ה)?(כוללת|כולל|מוסכמת|מוסכם)','\\d[\\d,]*\\s*(ש"ח|₪|שקלים|אלף|דולר|אירו)|(הנקוב|הנקובה|הקבוע|הקבועה)[^.\\n]{0,15}בסעיף'),'en':('liabilit','limited to|shall not exceed|capped at','(total|agreed|aggregate) (fees|consideration|contract value|price|rent|charges)','(\\$|USD|NIS|ILS|EUR|€|£)\\s?\\d|\\d[\\d,]*\\s*(USD|NIS|ILS|EUR)|(set out|stated|specified) in (Section|Clause)')}
INTERNAL_AUTHORS=tuple(A for A in(dt.INTERNAL_AUTHOR,getattr(dt,'INTERNAL_AUTHOR_EN',None),'Internal, delete before sending')if A)
def _f(code,message,where=None):return{'code':code,'message':message,'where':where}
def _sentences(text):return[A.strip()for A in re.split('(?<=[.?!;])\\s+',text)if A.strip()]
def _parse_local(s):return _dt.datetime.strptime(s,dt.DATE_FMT_LOCAL if not s.endswith('Z')else dt.DATE_FMT)
def concepts_for(lang):return CONCEPTS_EN if lang=='en'else CONCEPTS_HE
def check_entity_name_en(profile,lang,mode,accept_text=''):
	B=profile
	if lang!='en'or not B.get('organization_name')or B.get('organization_name_en'):return[],[]
	A=ENTITY_NAME_EN_PLACEHOLDER in(accept_text or'');D='העותק למשלוח אינו מופק עד שהשם נמסר ונשמר בפרופיל אצל סוכן ההקמה, וקובץ העבודה מופק מחדש מאותן הכרעות'if A else'הנוסח שלנו אינו משתמש בשם, ולכן העותק למשלוח מופק; כדאי לשמור את השם בפרופיל לסבב הבא';C=_f('ENTITY_NAME_EN_MISSING','הסכם באנגלית, ובפרופיל אין שם רשום באנגלית לחברה (organization_name_en)%s. %s. השם העברי אינו מתועתק ואינו מתורגם'%('; בנוסח יש מציין מקום %s'%ENTITY_NAME_EN_PLACEHOLDER if A else'',D));return([C],[])if mode=='send'and A else([],[C])
INTERNAL_MARK=re.compile('sources annex|נספח (?:ה)?מקורות|remove before sending|delete before sending|למחיקה לפני (?:ה)?משלוח|(?<![א-ת])לא למשלוח|not for sending|internal only|for internal use|לשימוש פנימי בלבד|טיוטת עבודה פנימית|internal work(?:ing)? draft|^\\s*(?:internal|פנימי)\\s*[.:]?\\s*$|:\\s*internal\\s*\\.',re.I|re.M)
PLAYBOOK_MENTION=re.compile('(?<![א-ת])[ובלמהש]{0,2}פלייבוק|\\bplaybooks?\\b|מדיניות(?: ה)?(?:חוזית|פנימית)|\\bour (?:internal |contracting )?polic(?:y|ies)\\b|\\binternal polic(?:y|ies)\\b',re.I)
def check_internal_leak(parts,root,comments,mode,ext_ids=()):
	E=parts;A=mode;F,G=[],[];B=[('גוף',A,dt.para_text(B))for(A,B)in enumerate(dt.body_paragraphs(root))]
	if A=='send':
		for C in E:
			if re.match('word/(header|footer)\\d*\\.xml$',C):
				try:J=etree.fromstring(E[C])
				except etree.XMLSyntaxError:continue
				B.append(('כותרת',C,''.join(A.text or''for A in J.iter(W+'t'))))
	for D in comments:
		if A=='send'or D['id']in set(ext_ids):B.append(('בועה',D['id'],D['text']))
	for(K,L,H)in B:
		I=INTERNAL_MARK.search(H or'')or PLAYBOOK_MENTION.search(H or'')
		if I:(F if A=='send'else G).append(_f('INTERNAL_LEAK','תוכן פנימי ב%s שהצד השני רואה: "%s"'%(K,I.group(0).strip()[:60]),L))
	return F,G
def _internal_texts(core):
	D=[]
	for A in(core or{}).get('clauses')or():
		if not isinstance(A,dict):continue
		C=[A.get('red_line'),A.get('concession_note'),A.get('sensitivity_note'),A.get('interpretation_guidance')]
		for F in('green','yellow','red'):
			E=A.get(F)or{}
			if isinstance(E,dict):C.append(E.get('position'))
		C+=[A.get('context')for A in A.get('exceptions')or()if isinstance(A,dict)];G={' '.join(str(A.get(B)or'').split())for B in('preferred_wording','fallback_wording','floor_wording')}
		for B in C:
			B=' '.join(str(B or'').split())
			if len(B)>=40 and B not in G:D.append((A.get('id'),B))
	return D
def check_playbook_text_leak(parts,root,comments,core,mode,ext_ids=()):
	A,B=[],[];C=_internal_texts(core)
	if not C:return A,B
	D=[dt.para_text(A)for A in dt.body_paragraphs(root)];D+=[A['text']for A in comments if mode=='send'or A['id']in set(ext_ids)];G=' '.join(' '.join(str(A or'').split())for A in D)
	for(E,F)in C:
		if F in G:(A if mode=='send'else B).append(_f('INTERNAL_LEAK','טקסט פנימי מהפלייבוק בעותק שהצד השני רואה (%s): "%s"'%(E,F[:60]),E))
	return A,B
def check_ladder_steps(state,mode):
	E,F=[],[];G={}
	for A in(state or{}).get('decisions')or():
		if not isinstance(A,dict)or not isinstance(A.get('ladder_step'),int):continue
		B=tuple(A.get('rule_ids')or())or(A.get('clause_id'),);G.setdefault(B,[]).append((int(A.get('round')or 0),A['ladder_step']))
	for(B,H)in G.items():
		H.sort();C=None
		for(I,D)in H:
			if I<=1 and D>1:(E if mode=='send'else F).append(_f('LADDER_SKIP','בסבב הראשון הוחלה מדרגה %d ב-%s: בסבב הראשון לכל היותר המדרגה הראשונה'%(D,'/'.join(str(A)for A in B)),B[0]))
			if C is not None and D-C>1:(E if mode=='send'else F).append(_f('LADDER_SKIP','ב-%s ירדנו מהמדרגה %d ל-%d בסבב %d: מדרגה אחת בכל סבב'%('/'.join(str(A)for A in B),C,D,I),B[0]))
			C=D if C is None else max(C,D)
	return E,F
def check_lawyer_name_en(profile,lang,mode):
	A=profile;C=A.get('lawyer_name')or''
	if lang!='en'or A.get('lawyer_name_en')or not re.search('[\u0590-\u05ff]',C):return[],[]
	B=_f('LAWYER_NAME_EN_MISSING','הסכם באנגלית, ובפרופיל אין שם באנגלית לעורך הדין (lawyer_name_en): הבועות חתומות בשם העברי. העותק למשלוח אינו מופק עד שהשם נשמר אצל סוכן ההקמה');return([B],[])if mode=='send'else([],[B])
def author_for(profile,lang):
	A=profile
	if lang=='en'and A.get('lawyer_name_en'):return A['lawyer_name_en']
	return A['lawyer_name']
def initials_for(profile,lang='he'):
	A=profile
	if A.get('lawyer_initials'):return A['lawyer_initials']
	B=[A for A in author_for(A,lang).replace('"',' ').split()if A and A[0].isalpha()];return''.join(A[0]for A in B[:3]).upper()or'X'
def check_package(parts,root,profile,received_comment_ids,window,work_path=None,author=None,received_authors=()):
	M=work_path;L=profile;F=root;D=parts;C=author;A,N=[],{};C=C or L['lawyer_name'];R=etree.fromstring(D['word/settings.xml'])
	if R.find(W+'trackRevisions')is None:A.append(_f('PKG_TRACK_REVISIONS','w:trackRevisions חסר ב-settings.xml'))
	if R.find(W+'trackChanges')is not None:A.append(_f('PKG_TRACK_CHANGES_INVALID','w:trackChanges אינו רכיב בסכמה'))
	for(H,b)in D.items():
		if not H.endswith('.xml')or not H.startswith('word/'):continue
		try:S=etree.fromstring(b)
		except etree.XMLSyntaxError as I:A.append(_f('PKG_XML','XML פגום: %s'%I,H));continue
		c=(S.get(dt.MC_IGNORABLE)or'').split();T=[A for A in c if A not in S.nsmap]
		if T:A.append(_f('PKG_NAMESPACE_UNDECLARED','קידומות ב-mc:Ignorable שאינן מוצהרות: %s'%T,H))
	U=[A for A in F.iter(W+'ins',W+'del')];J=[A for A in U if A.get(W+'author')==C];V={A.get(W+'author')for A in U}-{C}-set(received_authors or())
	if V:A.append(_f('PKG_AUTHOR','סימוני מעקב במחבר אחר: %s'%sorted(A for A in V if A)))
	X,d=window;O=None
	for I in J:
		E,G=I.get(W+'date'),I.get(dt.DATE_UTC_ATTR)
		if not E or not re.fullmatch('\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\d',E):A.append(_f('PKG_DATE_FORMAT','w:date בתבנית לא נכונה (שעה מקומית בלי Z): %r'%E));break
		if not G or not re.fullmatch('\\d{4}-\\d\\d-\\d\\dT\\d\\d:\\d\\d:\\d\\dZ',G):A.append(_f('PKG_DATE_UTC','w16du:dateUtc חסר או לא תקין: %r'%G));break
		Y=_parse_local(E)
		if not X<=Y<=d:A.append(_f('PKG_DATE_RANGE','תאריך שאינו של ההרצה: %s'%E));break
		P=Y-_parse_local(G)
		if O is None:O=P
		e=_dt.datetime.now().astimezone().utcoffset()
		if abs((P-e).total_seconds())>60 or P!=O:A.append(_f('PKG_DATE_UTC','הפרש בין w:date ל-dateUtc אינו הפרש השעון המקומי: %s / %s'%(E,G)));break
	N['revisions']=len(J);N['distinct_dates']=len({A.get(W+'date')for A in J});f=etree.fromstring(D[dt.COMMENTS_PART])if dt.COMMENTS_PART in D else None;g=dt.areo_paragraphs(F,dt._areo_comment_ids(f));Z=F.getroottree();i={Z.getpath(A)for A in g}
	def h(h):A=next(h.iterancestors(W+'p'),None);return A is not None and Z.getpath(A)in i and h.get(W+'val')==dt.AREO_HIGHLIGHT
	a=[B for A in J if local_tag(A)=='ins'for B in A.iter(W+'highlight')if not h(B)]
	if a:A.append(_f('PKG_HIGHLIGHT','צבע בטקסט שהוכנס: %d'%len(a)))
	K=D.get('docProps/core.xml',b'').decode('utf-8');j=D.get('docProps/app.xml',b'').decode('utf-8')
	if'python-docx'in K+j:A.append(_f('PKG_METADATA','"python-docx" במאפייני הקובץ'))
	if dt.esc(C)not in K and C not in K:A.append(_f('PKG_METADATA','המחבר במאפייני הקובץ אינו עורך הדין מהפרופיל'))
	for Q in re.finditer('<dcterms:(created|modified)[^>]*>([^<]+)<',K):
		try:
			k=_dt.datetime.strptime(Q.group(2)[:19],'%Y-%m-%dT%H:%M:%S')
			if k<X-_dt.timedelta(days=1):A.append(_f('PKG_METADATA','תאריך %s במאפיינים קודם להרצה: %s'%(Q.group(1),Q.group(2))))
		except ValueError:pass
	if dt.audit_schema_order(F):A.append(_f('PKG_SCHEMA_ORDER','סדר סכמה שגוי ב-%d מכלים'%dt.audit_schema_order(F)))
	if M and len(os.path.abspath(M))>paths.PATH_LIMIT:A.append(_f('PKG_PATH_LENGTH','נתיב של %d תווים (הגבול %d)'%(len(os.path.abspath(M)),paths.PATH_LIMIT)))
	l=dt.read_comments(D)
	for B in l:
		if B['id']in received_comment_ids:continue
		if B['author']!=C and B['author']not in INTERNAL_AUTHORS:A.append(_f('BUB_UNKNOWN_AUTHOR','בועה במחבר לא מוכר: %s'%B['author'],B['id']))
		if B['author']==C and L.get('lawyer_initials')and B['initials']!=L['lawyer_initials']:A.append(_f('BUB_INITIALS','ראשי תיבות שאינם מהפרופיל: %s'%B['initials'],B['id']))
	return A,N
def local_tag(e):return dt.local(e.tag)
def check_bubbles(ext,accept_text,state,reject_text='',lang='he'):
	D=state;A=[];N=accept_text+'\n'+reject_text;O=bool((D or{}).get('policy_claim_allowed'));H=list((D or{}).get('deal_context',{}).get('facts',[]))if D else[];H+=list(((D or{}).get('meta')or{}).get('deal_context',{}).get('facts',[]))if D else[];P=[str(A.get('fact'))for A in H if A.get('disclosure')in('drafting_only','internal_only')];G={}
	for C in ext:
		B=C['text'];E=FORBIDDEN_ALWAYS.search(B)
		if E:A.append(_f('BUB_FORBIDDEN','מונח פנימי בבועה: "%s"'%E.group(0),C['id']))
		E=None if O else policy_claim_term(B)
		if E:A.append(_f('BUB_FORBIDDEN','"%s" בבועה בלי טענת מדיניות מאושרת'%E.group(0),C['id']))
		I=case_law_in_text(B)
		if I:A.append(_f('BUB_CASE_LAW','הפניה לפסיקה בבועה: %s'%'; '.join(I[:3]),C['id']))
		if LONG_DASH.search(B):A.append(_f('BUB_LONG_DASH','מקף ארוך בבועה',C['id']))
		if len(SENT_END.findall(B+' '))>5:A.append(_f('BUB_SENTENCES','יותר מחמישה משפטים',C['id']))
		if PRACTICE_OPENING[lang].search(B)or PRACTICE_OPENING['he'].search(B):A.append(_f('BUB_PRACTICE_OPENING','בועה שנפתחת במשפט נוהג',C['id']))
		for J in re.findall('\\d[\\d,]*',CLAUSE_REF.sub(' ',B)):
			if J.strip(',')not in N:A.append(_f('BUB_NUMBER_NOT_IN_BODY','המספר %s אינו בנוסח'%J,C['id']))
		for K in P:
			if K and K in B:A.append(_f('BUB_DISCLOSURE','עובדה שסווגה לנוסח בלבד או פנימית מופיעה בבועה',C['id']))
		F=B.split();L=' '.join(F[:3]if F[:1]and F[0].lower()in('we','אנו','אנחנו')else F[:2]);G[L]=G.get(L,0)+1
	Q=max(2,len(ext)//3);M={B:A for(B,A)in G.items()if A>Q}
	if M:A.append(_f('BUB_REPEATED_OPENER','פתיח זהה ביותר משליש מהבועות: %s'%M))
	return A
def _para_accept(p):return''.join(dt._node_text(A)for(A,B)in dt._text_nodes(p)if dt.local(A.tag)!='delText'and'del'not in B)
def _tied_reason(sents,idx,lang):
	B=idx;A=sents
	if REASON[lang].search(A[B]):return True
	return B+1<len(A)and bool(REASON_LEAD[lang].search(A[B+1]))
def _changed_sentences(p,author):
	C=[]
	for A in p.iter(W+'ins'):
		if A.getparent()is not None and dt.local(A.getparent().tag)=='rPr'or A.get(W+'author')!=author:continue
		B=''.join(A.text or''for A in A.iter(W+'t')).strip()
		if len(B)>=2:C.append(B);C.extend(A.strip()for A in _sentences(B)if len(A.strip())>=2 and A.strip()!=B)
	D=_para_accept(p);return'\n'.join(A for A in _sentences(D)if any(B in A for B in C))
def changed_paragraphs(root,author):
	B=author;E=[]
	for(F,A)in enumerate(dt.body_paragraphs(root)):
		C,D=dt.revision_text(A,'ins',B),dt.revision_text(A,'del',B)
		if C.strip()or D.strip():
			if _is_heading(A):C,D='',''
			E.append((F,A,C,D,_changed_sentences(A,B)))
	return E
def _is_heading(p):A=_para_accept(p).strip();return dt._mark(p)=='ins'and 0<len(A)<60 and not re.search('[.;:]',A)
def _strip_removed(dele,texts):
	A=dele
	for C in texts or():
		for B in(C,C.strip()):
			if B and B in A:A=A.replace(B,' ');break
	return A
def check_coverage(root,ext_by_para,author,lang='he',removed=None):
	C=[];E=concepts_for(lang)
	for(A,H,I,B,J)in changed_paragraphs(root,author):
		B=_strip_removed(B,(removed or{}).get(A));F=' '.join(ext_by_para.get(A,[]));D=[C for(C,(A,D,E))in E.items()if re.search(A,I)or re.search(A,B)or C in NUMERIC_FUNCTIONS and re.search(A,J)]
		if not F:K=', '.join(D)if D else'שינוי טכני (%s)'%(_para_accept(H)or B)[:40];C.append(_f('COV_CHANGE_WITHOUT_BUBBLE','שינוי בלי בועה חיצונית: %s'%K,A));continue
		G=[A for A in D if not re.search(E[A][1],F,re.I if lang=='en'else 0)]
		if G:C.append(_f('COV_UNCOVERED_CHANGE','הבועה אינה מתארת: %s'%', '.join(G),A))
	return C
def check_bubble_why(root,ext_by_para,author,accept_text,lang='he',context=None,removed=None):
	A=lang;D=[];H=concepts_for(A);B=re.I if A=='en'else 0
	for(C,I,O,J,P)in changed_paragraphs(root,author):
		K=ext_by_para.get(C,[])
		if not K:continue
		F=[B for A in K for B in _sentences(A)];L=_strip_removed(J,(removed or{}).get(C));M=[B for(B,(A,D,C))in H.items()if C and(re.search(A,O)or re.search(A,L)or B in NUMERIC_FUNCTIONS and re.search(A,P))]
		if dt._mark(I)in('del','both')and re.search(RIGHT_WORDS[A],L,B):M.append('__deleted_right__')
		for E in M:
			Q='מחקנו|הסרנו|נמחק|deleted|removed|struck'if E=='__deleted_right__'else H[E][1];N=[A for(A,C)in enumerate(F)if re.search(Q,C,B)]
			if not N:continue
			if not any(_tied_reason(F,B,A)for B in N):R='זכות שלהם שנמחקה'if E=='__deleted_right__'else E;D.append(_f('BUB_WHY_MISSING','אין משפט נימוק ל: %s'%R,C))
		S=_para_accept(I);T,U,V,W=CAP_RX[A]
		for G in F:
			if KNOWN_CLAIM[A].search(G)and re.search('תקר|cap|limit',G,B):
				X=[A for(A,C,C)in gap_checks.sentences(S)if re.search(T,A,B)and re.search(U,A,B)]
				if any(re.search(V,A,B)and not re.search(W,A,B)for A in X):D.append(_f('BUB_CLAIM_FALSE','הבועה אומרת שבסיס התקרה ידוע מראש, והנוסח קובע רק תקרה ולא סכום',C))
			if DELETION_CLAIM[A].search(G)and not J.strip():D.append(_f('BUB_CLAIM_FALSE','הבועה אומרת שמחקנו, ובפסקה לא נמחק דבר',C))
	return D
HEB_RUN=re.compile('[\u0590-\u05ff](?:[\u0590-\u05ff"\'׳״\\-. ]*[\u0590-\u05ff])?')
def check_language(root,ext,author,lang,received_text):
	B=[]
	if lang!='en':return B
	E=(received_text or'').translate(dt.QUOTE_FOLD)
	def C(text):return[A.group(0)for A in HEB_RUN.finditer(text or'')if A.group(0).translate(dt.QUOTE_FOLD)not in E]
	for(F,G)in enumerate(dt.body_paragraphs(root)):
		A=C(dt.revision_text(G,'ins',author))
		if A:B.append(_f('LANG_HEBREW_IN_EN','אותיות עבריות בנוסח שהכנסנו להסכם באנגלית: "%s". בהסכם באנגלית הישות נכתבת בשם הרשום באנגלית (organization_name_en בפרופיל)'%A[0][:40],F))
	for D in ext:
		A=C(D['text'])
		if A:B.append(_f('LANG_HEBREW_IN_EN','אותיות עבריות בבועה בהסכם באנגלית: "%s"'%A[0][:40],D['id']))
	return B
BUBBLE_FAIL_FACTOR=1.5
BUBBLE_WORDS={B:(A['max_words'],int(A['max_words']*BUBBLE_FAIL_FACTOR))for(B,A)in ROUND_MATRIX.items()}
BUBBLE_SENTENCES={B:(A['max_sentences'],int(A['max_sentences']*BUBBLE_FAIL_FACTOR))for(B,A)in ROUND_MATRIX.items()}
PASSIVE={'en':re.compile('\\b(?:is|are|was|were|has been|have been)\\s+(?:now\\s+)?(?:replaced|deleted|removed|amended|added|inserted|changed|limited|extended|reduced|qualified|completed|incorporated)\\b|\\bthe (?:revised |amended )?(?:clause|section|provision|paragraph|item|schedule|agreement) now (?:provides|states|covers|requires|says|includes)\\b|\\bunder the revised (?:clause|section)\\b|\\bnow replaces?\\b',re.I),'he':re.compile('(?<![א-ת])(?:הוחלפ(?:ה|ו)?|הוחלף|נמחק(?:ה|ו)?|תוקנ(?:ה|ו)|תוקן|הוסף|הוספה|הושלמ(?:ה|ו)|הושלם)(?![א-ת])|הסעיף (?:קובע|כולל|מחייב) כעת')}
ACTIVE={'en':re.compile('\\b[Ww]e\\b'),'he':re.compile('(?<![א-ת])ו?(?:שינינו|הוספנו|מחקנו|השארנו|החלפנו|ביקשנו|צמצמנו|הרחבנו|קיבלנו|תיקנו|השלמנו|הסרנו|אנו|אנחנו|נבקש|נשמח|נציע)(?![א-ת])')}
def _round_of(state,decisions=None):
	B=decisions;A=(B or{}).get('round')if isinstance(B,dict)else None;A=A or((state or{}).get('meta')or{}).get('round_number')
	try:return int(A)if A is not None else None
	except(TypeError,ValueError):return
def round_stage(state,decisions=None):
	A=state or{};B=A.get('meta')or{};C=_round_of(A,decisions)
	if C:return SB.stage_for_round(C)
	D=B.get('round_stage')or B.get('stage')or A.get('stage');return D if D in BUBBLE_WORDS else'opening'
def check_bubble_style(ext,lang,stage):
	A=stage;G,F=[],[];A=A if A in BUBBLE_WORDS else'opening';H,I=BUBBLE_WORDS[A];J,K=BUBBLE_SENTENCES[A]
	for C in ext:
		B=C['text']or'';L=re.sub(REPLACES_SENT,' ',B,flags=re.I).strip()or B;D,E=len(L.split()),qb_sentences(L)
		if D>I or E>K:G.append(_f('BUB_LENGTH','בועה של %d מילים ו-%d משפטים (הגבול בשלב %s: %d מילים, %d משפטים). לקצר: מה שינינו, למה, ומה נשאר'%(D,E,A,I,K),C['id']))
		elif D>H or E>J:F.append(_f('BUB_LENGTH','בועה של %d מילים ו-%d משפטים (התקרה בשלב %s: %d מילים, %d משפטים)'%(D,E,A,H,J),C['id']))
		M='en'if len(re.findall('[A-Za-z]',B))>len(re.findall('[א-ת]',B))else'he';N=PASSIVE[M].search(B)
		if N and not ACTIVE[M].search(B):F.append(_f('BUB_PASSIVE_VOICE','בועה בגוף שלישי סביל ("%s"). קול פעיל: "We have replaced..." / "החלפנו..."'%N.group(0),C['id']))
	return G,F
GONE_CLAIM={'en':[re.compile('(?:^|[.;]\\s*)(?P<x>[^.;]{3,140}?)\\s+(?:is|are)\\s+no longer\\s+(?:required|needed|necessary|applicable|a condition)',re.I),re.compile('\\bno longer requires?\\s+(?P<x>[^.;,]{3,100})',re.I),re.compile('\\b(?:removed|deleted|struck out|struck)\\s+(?:the (?:words?|phrase|reference to|requirement (?:for|of|that))\\s+)?(?P<x>"[^"]{3,100}"|“[^”]{3,100}”)',re.I),re.compile('(?P<x>"[^"]{3,100}"|“[^”]{3,100}”)\\s+(?:has|have) been (?:removed|deleted)',re.I)],'he':[re.compile('(?P<x>[^.;]{3,100}?)\\s+(?:אינה|אינו|אינם|אינן)\\s+נדרש(?:ת|ים|ות)?\\s+עוד'),re.compile('(?:מחקנו|הסרנו)\\s+את\\s+(?:הדרישה ל|המילים\\s+)?(?P<x>"[^"]{3,100}"|״[^״]{3,100}״|[^.;,]{3,60})')]}
APPROVAL={'en':re.compile("(?i:consent|approval|authori[sz]ation|agreement)\\s+of\\s+(?:the\\s+)?(?P<p>[A-Z][\\w-]+(?: [A-Z][\\w-]+)?)|(?P<q>[A-Z][\\w-]+)\\'s\\s+(?i:prior\\s+)?(?i:written\\s+)?(?i:consent|approval)"),'he':re.compile('(?:הסכמת|אישור|הסכמתה של|אישורו של)\\s+(?:ה)?(?P<p>[א-ת]{2,})')}
LIST_LABEL=re.compile('^\\s*(\\(?[ivx]{1,4}\\)|\\(?[a-z]{1,2}\\)|\\(?\\d{1,2}\\)|\\(?[א-י]\\))\\s',re.I)
def _approval_rx(party,lang):
	A=re.escape(party)
	if lang=='he':return re.compile('(?:הסכמת|אישור|לפי שיקול דעת|כפי שי?קבע|כפי שתקבע|להנחת דעת)\\s+(?:של\\s+)?ה?'+A)
	return re.compile('(?:consent|approval|authori[sz]ation)\\s+of\\s+(?:the\\s+)?'+A+'|'+A+"\\'s\\s+(?:prior\\s+)?(?:written\\s+)?(?:consent|approval)|(?:as\\s+)?determined\\s+by\\s+(?:the\\s+)?"+A+'|(?:sole\\s+)?discretion\\s+of\\s+(?:the\\s+)?'+A+'|approved\\s+by\\s+(?:the\\s+)?'+A+'|to\\s+the\\s+satisfaction\\s+of\\s+(?:the\\s+)?'+A,re.I)
def _scope(acc,first,last):
	B=acc;A=last;D=list(range(first,A+1))
	if B[A].rstrip().endswith(':'):
		E=set()
		for F in range(A+1,min(len(B),A+16)):
			C=LIST_LABEL.match(B[F])
			if not C or C.group(1).strip('()').lower()in E:break
			E.add(C.group(1).strip('()').lower());D.append(F)
	return D
def check_bubble_text_match(root,ext,spans,lang):
	G=spans;H=[];D=[_para_accept(A)for A in dt.body_paragraphs(root)];I=lambda s:_norm_ws(s).translate(dt.QUOTE_FOLD).lower()
	for B in ext:
		if B['id']not in G:continue
		J,K=G[B['id']];N=I(' '.join(D[A]for A in _scope(D,J,K)));O=' '.join(D[A]for A in _scope(D,J,K));E='en'if len(re.findall('[A-Za-z]',B['text']))>len(re.findall('[א-ת]',B['text']))else'he'
		for P in GONE_CLAIM[E]:
			C=None
			for Q in P.finditer(B['text']):
				A=Q.group('x').strip().strip('"“”״');A=re.sub('^(?:the requirement (?:for|of|that)|the reference to|הדרישה ל)\\s*','',A,flags=re.I)
				if len(A)>=3 and I(A)in N:C='הביטוי "%s" נשאר בנוסח'%A[:60]
				else:
					F=APPROVAL[E].search(A);L=F and(F.group('p')or F.groupdict().get('q'))
					if L:
						M=_approval_rx(L.strip(),E).search(O)
						if M:C='הבועה אומרת ש-"%s" כבר אינו נדרש, ובנוסח נשאר "%s"'%(A[:50],M.group(0))
				if C:break
			if C:H.append(_f('BUB_TEXT_MISMATCH','הבועה מתארת תוצאה שהנוסח אינו נותן: %s. לתקן את הנוסח או את הבועה'%C,B['id']));break
	return H
MODIFYING_OPS='replace','replace_span','delete_paragraph','insert_paragraph'
REOPEN_KINDS='reopen','reopened','reopen_instruction','withdraw','withdraw_concession'
REOPEN_WHAT='פתיחה מחדש בהוראת עורך הדין'
LAST_OFFERED='last_fallback','fallback_2','reserve','last'
NO_TEXT=re.compile('^\\s*(?:אין|none|n/?a)\\b',re.I)
def _is_reopen(h):return bool(h.get('reopen')or any(h.get(A)in REOPEN_KINDS for A in('kind','type','action'))or str(h.get('what')or'').startswith(REOPEN_WHAT))
def _instructed(cl,d,st,cid,since=None):
	B=since;B=B or 0
	for C in(cl or{}).get('reopen_log')or():
		if isinstance(C,dict)and C.get('recorded_at')and int(C.get('round')or 0)>=B:return True
	if(cl or{}).get('reopen_instruction')or(d or{}).get('reopen_instruction'):return True
	for D in(cl or{}).get('concession_history')or():
		if isinstance(D,dict)and _is_reopen(D)and int(D.get('round')or 0)>=B:return True
	for A in(st or{}).get('user_decisions')or():
		if cid not in(A.get('applies_to')or())or A.get('answer_kind')!='explicit':continue
		if str(A.get('id')or'').startswith('reopen-%s-'%cid)or A.get('reopen')or A.get('kind')in REOPEN_KINDS or A.get('situation')in REOPEN_KINDS:return True
	return False
def _agreed(st,cl):
	if not isinstance(cl.get('closed_in_round'),int)or cl.get('closed_basis')not in SB.CLOSED_BASES:return False
	return not SB.premature_closed(st,cl)
def _delivered_concessions(st,clauses,rnd):
	C={}
	def D(cid,r):
		A=cid
		if A and isinstance(r,int)and r<rnd:C[A]=min(C.get(A,r),r)
	for B in st.get('deliberate_concessions')or():
		if isinstance(B,dict)and B.get('clause_ref')and not B.get('reopened_in_round'):D(B['clause_ref'],B.get('delivered_in_round'))
	for(G,E)in clauses.items():
		F=E.get('accepted_in_round')
		if isinstance(F,int)and SB.delivered(st,F)and not _agreed(st,E):D(G,F)
		for A in E.get('concession_history')or():
			if isinstance(A,dict)and A.get('who')=='us'and not _is_reopen(A)and isinstance(A.get('round'),int)and SB.delivered(st,A['round']):D(G,A['round'])
	return C
def _sent_norm(s):return re.sub('\\s+',' ',(s or'').translate(dt.QUOTE_FOLD)).strip().lower()
def check_round_rules(state,decisions,rroot,root,authors,spans,our_ids,prev_bubbles=(),mode='work'):
	R=authors;Q=rroot;J=decisions;K,L=[],[];C=state or{};g=C.get('meta')or{};G=J.get('decisions',[])if isinstance(J,dict)else J or[];D=_round_of(C,J)or 1;H={A.get('clause_id'):A for A in C.get('clauses')or()if isinstance(A,dict)};S=_delivered_concessions(C,H,D);M={A for A in R or()if A};T=dt.body_paragraphs(Q)if Q is not None else[]
	def h(d,cl,cid):
		A=d.get('para')
		if any(isinstance(B,dict)and int(B.get('round')or 0)==D and(B.get('clause_id')==cid or isinstance(A,int)and B.get('received_para')==A)for B in C.get('silent_changes')or()):return True
		if(cl.get('reopened_by_counterparty')or{}).get('round')==D or any(isinstance(A,dict)and A.get('by')=='them'and A.get('round')==D for A in cl.get('rejections')or()):return True
		return isinstance(A,int)and 0<=A<len(T)and any(A.get(W+'author')not in M for A in T[A].iter(W+'ins',W+'del'))
	F=(g.get('deal_context')or{}).get('stance');F=(F.get('value')if isinstance(F,dict)else F)or'playbook';i={A.get('id'):A for A in G}
	def j(d):
		if not(d.get('conforming')and d.get('conforms_to')):return False
		D=d['conforms_to'];A=i.get(D)
		if A is not None and A is not d:return A.get('op')in MODIFYING_OPS+('comment_only',)
		B=H.get(D);return bool(B)and B.get('status')not in('CLOSED',)and not _agreed(C,B)
	for A in G:
		E=A.get('clause_id')or A.get('id');B=H.get(E)or{};b=A.get('op')in MODIFYING_OPS and not h(A,B,E)and not j(A);U=B.get('closed_in_round')
		if b and _agreed(C,B)and U<=D and not _instructed(B,A,C,E,U):K.append(_f('ROUND_REOPEN_CLOSED','ההכרעה משנה נוסח בסעיף שהוסכם בסבב %d, בלי הוראה רשומה לפתוח אותו מחדש. פתיחה מחדש רק בהוראת עורך הדין: negotiation_state.py reopen --clause %s --instruction "<ההוראה>" --reason "<הסיבה>" (reopen_log, עם התאריך)'%(U,E),A.get('id')))
		elif b and E in S and not _instructed(B,A,C,E,S[E]):K.append(_f('ROUND_CONCESSION_WITHDRAWN','ההכרעה משנה נוסח בסעיף שוויתרנו עליו, והוויתור נמסר לצד השני בסבב %d: ויתור שנמסר אינו נלקח בחזרה בלי הוראה רשומה של עורך הדין (negotiation_state.py reopen)'%S[E],A.get('id')))
		if D==1 and F in('playbook','stricter'):
			N=[]
			for V in(A,B):
				N=[A for A in[V.get('fallback_1'),V.get('fallback_2')]+list(V.get('reserve')or())if isinstance(A,str)and A.strip()and not NO_TEXT.match(A)]
				if N:break
			X=N[-1]if N else None;k=_sent_norm(' '.join(str(A.get(B)or'')for B in('new','new_text','text')));l=A.get('offered_now')or B.get('offered_now')
			if A.get('at_last_fallback')or l in LAST_OFFERED or X and len(X)>=20 and _sent_norm(X)in k:L.append(_f('ROUND_LAST_FALLBACK_EARLY','נוסח הנסיגה האחרון מוצע כבר בסבב 1, בגישת %s: לא נשאר מרווח לסבבים הבאים'%F,A.get('id')))
	Y=list(prev_bubbles or())
	for B in H.values():
		for m in('external_comment_history','previous_external_comments'):Y+=[A if isinstance(A,str)else(A or{}).get('text','')for A in B.get(m)or()]
	c={_sent_norm(A)for B in Y for A in _sentences(B or'')if len(A.split())>=8}
	if D>1:
		from orchestrator.question_batch import rejected_argument_findings as n
		for A in G:
			for Z in n(A,previous=Y):L.append(_f('BUB_REPEATS_REJECTED_ARGUMENT'if Z['code']=='ROUND_REPEATS_REJECTED_ARGUMENT'else Z['code'],Z['message'],A.get('id')))
	if c and D>1:
		for A in G:
			o=A.get('external_comment')or'';d=[A for A in _sentences(o)if len(A.split())>=8 and _sent_norm(A)in c]
			if d:B=H.get(A.get('clause_id')or A.get('id'))or{};p=' (ההצעה נדחתה בסבב הקודם)'if any(A in SB.THEIR_REJECTION for A in B.get('last_round_changes')or())else'';L.append(_f('BUB_REPEATS_REJECTED','הבועה חוזרת מילה במילה על נימוק מסבב קודם%s: "%s". נימוק שנדחה אינו חוזר בלי חידוש: עונים לנימוק שלהם, או מוסיפים נימוק חדש'%(p,d[0][:80]),A.get('id')))
	if Q is not None:
		e=_received_groups(root,R[0])if R else[];q={id(B):A for(A,B)in enumerate(dt.body_paragraphs(root))};r={D for(A,(B,C))in spans.items()if A in our_ids for D in range(B,C+1)};s={A.get('para'):A for A in G if isinstance(A.get('para'),int)}
		for(O,t)in enumerate(T):
			I=[]
			for P in t.iter(W+'del'):
				if P.get(W+'author')in M or P.getparent().tag==W+'rPr':continue
				if any(A.tag==W+'ins'and A.get(W+'author')in M for A in P.iterancestors()):I.append(''.join(A.text or''for A in P.iter(W+'delText')))
			I=[A for A in I if A.strip()]
			if not I or O>=len(e):continue
			a=e[O];u=_para_accept(a);v=''.join(B.text or''for A in a.iter(W+'del')if A.get(W+'author')not in M for B in A.iter(W+'delText'));f=[A for A in I if A in u and A not in v]
			if not f:continue
			A=s.get(O)or{}
			if q.get(id(a))in r or A.get('external_comment'):continue
			K.append(_f('ROUND_RESTORE_NO_BUBBLE','החזרנו נוסח שלנו שהצד שכנגד מחק ("%s") בלי בועה: דחייה ב-Word אינה משאירה סימון, ולכן הבועה אומרת מה מחקו, מה החזרנו ולמה'%f[0].strip()[:60],O))
	return K,L
def check_contradictions(ext,accept_text,lang='he'):
	A=accept_text;B=[];C='\n'.join(A['text']for A in ext)
	if re.search('(טעות|שגיאה)[^.\\n]{0,20}תרגום|תרגום (שגוי|לקוי|מכונה)|תורגם בטעות',C)and re.search('הנוסח העברי[^.\\n]{0,80}(המחייב|גובר)',A+'\n'+C):B.append(_f('CON_CONTRADICTION','בועה טוענת לתרגום שגוי, ובאותו סבב הנוסח העברי נקבע מחייב או גובר'))
	if re.search('mistranslat|translation error|incorrectly translated',C,re.I)and re.search('prevails over any[^.\\n]{0,60}translation',A,re.I):B.append(_f('CON_CONTRADICTION','בועה טוענת לתרגום שגוי, והנוסח החתום גובר על כל תרגום'))
	if re.search('מוגן ב(תנאי התשלום|הסכם)',C)and re.search('(שלילת|ישלול)[^.\\n]{0,10}עיכבון|לא יעכב[^.\\n]{0,80}מחלוקת',A)and not re.search('רשאי להשהות|זכות (ה)?השהי',A):B.append(_f('CON_CONTRADICTION','בועה נשענת על הגנת תשלום שהתגובה עצמה הסירה'))
	if re.search('protected by the payment terms',C,re.I)and re.search('shall not (withhold|suspend)',A,re.I)and not re.search('may suspend|right to suspend',A,re.I):B.append(_f('CON_CONTRADICTION','בועה נשענת על הגנת תשלום שהתגובה עצמה הסירה'))
	return B
def check_reasoning_warnings(ext):
	B=[]
	for A in ext:
		if re.search('הדין (מטיל|קובע)[^.\\n]{0,20}ממילא|חלה ממילא',A['text'])or re.search('(law|statute) (already )?(requires|imposes)[^.]{0,40}(anyway|in any event)|applies anyway',A['text'],re.I):B.append(_f('BUB_LAW_ANYWAY','נימוק "חובה שהדין מטיל ממילא" מזמין את התשובה שאין צורך בסעיף',A['id']))
	return B
def check_placeholders(root,ext,author,state,mode):
	F,A=[],{'ours':[],'theirs':[],'signing_blanks':[]};I=any((A or{}).get('status')=='signing_blank'for A in((state or{}).get('entity_details')or{}).values());J=tuple(ids.SIGNING_BLANKS.values())
	for(C,G)in enumerate(dt.body_paragraphs(root)):
		K=dt.revision_text(G,'ins',author);D=K
		for E in J:
			while E in D:
				if I:A['signing_blanks'].append({'para':C,'text':E})
				else:A['ours'].append({'para':C,'text':E,'why':'אין תשובה "נשלים לפני החתימה"'})
				D=D.replace(E,'',1)
		for B in OUR_PH.finditer(D):A['ours'].append({'para':C,'text':B.group(0)})
		for B in UNDERSCORES.finditer(D):A['ours'].append({'para':C,'text':B.group(0)})
		L=''.join(A.text or''for A in G.iter(W+'t')if not any(dt.local(A.tag)=='ins'for A in A.iterancestors()))
		for B in THEIR_PH.finditer(L):A['theirs'].append({'para':C,'text':B.group(0)})
	for H in ext:
		for B in OUR_PH.finditer(H['text']):A['ours'].append({'comment':H['id'],'text':B.group(0)})
	if mode=='send'and A['ours']:F.append(_f('PH_OURS','מציין מקום שלנו בעותק למשלוח: %s'%[A['text']for A in A['ours']]))
	return F,A
def _digits(s):return re.sub('\\D','',s or'')
def _our_names(profile):A=profile;return[str(A).strip().lower()for A in(A.get('organization_name'),A.get('organization_name_en'))if A and len(str(A).strip())>2]
def check_identifiers(root,author,profile,lang='he',received_text=''):
	G=profile;H,F=[],[];C=ids.israeli_registry(G);I=G.get('organization_id')or G.get('registration_number');D=ids.validate_company_number(I,israeli=C is not False)if I else None;J=_our_names(G);K=dt.body_paragraphs(root);L=[''.join(A.text or''for A in A.iter(W+'t'))for A in K];M=_digits(received_text);N=COMPANY_NO[lang]
	for(B,O)in enumerate(K):
		S=dt.revision_text(O,'ins',author);P=L[B].lower();T=L[B-1].lower()if B else'';U=bool(re.match('\\s*\\(?\\s*(?:ח\\.?\\s?פ|ע\\.?\\s?מ|מספר|company|registration|reg\\.)',P,re.I));V=any(A in P for A in J)or U and any(A in T for A in J)
		for A in N.finditer(S):
			Q=_digits(A.group('num'));X=V or bool(I)and Q==_digits(I)
			if not X:
				if M and Q not in M:F.append(_f('ID_NUMBER_NOT_IN_SOURCE','מספר רישום שהוכנס לנוסח, שאינו של החברה שלנו, אינו במסמך שהתקבל: %s'%A.group('num'),B))
				continue
			E=ids.validate_company_number(A.group('num'),israeli=C is not False);R=bool(D)and E['number']==D['number']
			if not E['valid']:
				(H if C else F).append(_f('ID_COMPANY_NUMBER','מספר תאגיד שנכשל בבדיקה (%s) הוכנס לנוסח: %s'%(E['reason'],A.group('num')),B))
				if C is None and D and not R:H.append(_f('ID_COMPANY_NUMBER','מספר תאגיד שונה מהפרופיל: %s'%A.group('num'),B))
			elif D and(D['valid']or C is not True)and not R:H.append(_f('ID_COMPANY_NUMBER','מספר תאגיד שונה מהפרופיל: %s'%A.group('num'),B))
			elif not D and C is False:F.append(_f('ID_COMPANY_NUMBER','אין מספר רישום בפרופיל להשוואה: %s'%A.group('num'),B))
		Y=''.join(dt._node_text(A)for(A,B)in dt._text_nodes(O)if'ins'not in B and'del'not in B and dt.local(A.tag)!='delText')
		for A in N.finditer(Y):
			E=ids.validate_company_number(A.group('num'))
			if not E['valid']and E['reason']not in('wrong_length','not_digits'):F.append(_f('ID_THEIR_NUMBER','מספר תאגיד בנוסח שלהם נכשל בבדיקה: %s'%A.group('num'),B))
	return H,F
def touched_paragraphs(root,author):
	A=[]
	for B in dt.body_paragraphs(root):
		if dt.revision_text(B,'ins',author).strip():A.append(_para_accept(B))
	return A
NUM_PREFIX=re.compile('^\\s*(\\d+(\\.\\d+)*\\.?|\\(?[\\dא-תa-z]{1,2}\\))\\s+',re.I)
def _norm_ws(s):return re.sub('\\s+',' ',s or'').strip()
def _norm_cmp(s):return _norm_ws(s).translate(dt.QUOTE_FOLD)
def playbook_verbatim_texts(state):
	B=[]
	for A in(state or{}).get('clauses',[]):
		C=[A.get('element')for A in A.get('basis_elements')or[]if A.get('source')=='PolicyDerived']
		if A.get('decision_basis')=='PolicyDerived'and not A.get('deviation_from_approved')and not A.get('safe_wording'):C+=[A.get(B)for B in('playbook_default','fallback_1','fallback_2')]+list(A.get('reserve')or[])
		B+=[_norm_ws(A)for A in C if isinstance(A,str)and A.strip()]
	return B
def _cap_from_playbook(t,lang,verbatim):A=verbatim;C=gap_checks.P.get(lang)or gap_checks.P[gap_checks.detect_lang(t)];D=re.I if lang=='en'else 0;B=[NUM_PREFIX.sub('',A)for A in _sentences(t)if re.search(C['pay_latest'],A,D)];return bool(A and B)and all(any(_norm_ws(B)in A for A in A)for B in B)
def check_self_created_gaps(root,author,accept_text,lang='he',context=None,state=None):
	H=accept_text;F=lang;G,D=[],set();B=dict(context or{});B['accept_text']=H;B.pop('allow_statutory_cap',None);J=playbook_verbatim_texts(state);I=touched_paragraphs(root,author)
	for E in I:
		K=dict(B,allow_statutory_cap=True)if _cap_from_playbook(E,F,J)else B
		for A in gap_checks.check_wording(E,F,context=K):
			C=A['code'],A['message_he'],E[:60]
			if C not in D:D.add(C);G.append(_f(A['code'],A['message_he'],E[:60]))
	for A in gap_checks.check_document(H,I,F,B):
		C=A['code'],A['message_he'],None
		if C not in D:D.add(C);G.append(_f(A['code'],A['message_he']))
	return G
def waived_gap_codes(state):
	A=set()
	for B in(state or{}).get('deliberate_concessions',[]):
		if(B.get('user_decision')or{}).get('answer_kind')=='explicit':A.update(B.get('gap_codes',[]))
	return A
def check_state(state,mode):
	A=state;C,F=[],[]
	for G in(A or{}).get('clauses',[]):
		H=G.get('clause_id');B=G.get('safe_wording')or{}
		if B:
			I=B.get('not_worse_than_position'),B.get('not_worse_than_default');D=B.get('statute_ref')or{}
			if True in I and not(D.get('source_id')and D.get('url')and D.get('verified_in')=='playbook'):C.append(_f('SAFE_WORDING_SELF_CERTIFIED','נוסח בטוח סומן "אינו מרע" בלי מקור מאומת בפלייבוק',H))
	if A and'meta'in A:
		from orchestrator.state_builder import validate_state as J
		for E in J(A):(C if mode=='send'else F).append(_f(E['code'],E['message'],E['where']))
	return C,F
CHANGE_OPS='replace','replace_span','insert_paragraph','delete_paragraph'
def check_legal_review(state,decisions,core,mode):
	B=decisions;F,C=[],[];D=state or{};G=B.get('decisions',[])if isinstance(B,dict)else B or[];A=[]
	for E in[A.get('clause_id')for A in D.get('clauses')or()if A.get('legal_review_required')]+[A.get('id')for A in G if isinstance(A,dict)and A.get('legal_review_required')]:
		if E and E not in A:A.append(E)
	if A:H=D.get('numbering_map')or{};C.append(_f('NO_APPROVED_SOURCE','AREO לא מצאה מקור מורשה לנקודה זו: %s. הצעד הבא: להוסיף לתיקיית ההסכמים של החברה הסכם שמסדיר אותה, או לאשר עמדה בפלייבוק. אינו מעכב את המשלוח'%', '.join(H.get(A)or A for A in A),','.join(A)))
	if not D.get('clauses'):(F if mode=='send'else C).append(_f('STATE_NO_CLAUSES','קובץ המצב חסר או בלי סעיפים. השער במצב משלוח צריך את קובץ המצב של הסבב: הריצו קודם negotiation_state.py write עם קובץ ההכרעות, ואחריו את השער עם --deal (או --state)'))
	return F,C
def _our_ins_mark(p,author):A=p.find(W+'pPr/'+W+'rPr');B=A.find(W+'ins')if A is not None else None;return B is not None and B.get(W+'author')==author
def _our_del_mark(p,author):
	A=p.find(W+'pPr/'+W+'rPr');B=A.find(W+'del')if A is not None else None
	if B is None or B.get(W+'author')!=author:return False
	for C in p.iter(W+'t'):
		if(C.text or'').strip()and not any(dt.local(A.tag)=='del'for A in C.iterancestors()):return False
	return True
def _received_groups(root,author):
	C=author;B,A=[],[]
	for D in dt.body_paragraphs(root):
		A.append(D)
		if _our_ins_mark(D,C):continue
		B.append(A);A=[]
	if A:B.append(A)
	def E(q):return any(('ins',C)not in dt._revision_of(A,q)for(A,B)in dt._text_nodes(q))
	return[next((A for A in reversed(A)if E(A)),A[-1])for A in B]
def check_decisions_applied(root,received_texts,decisions,author,our_comment_ids=(),received_paras=None,prior=(),received_rej=None):
	T=prior;P=received_rej;O=received_paras;N=decisions;M=root;J=author;F=received_texts;Q=[];Z=N.get('decisions',[])if isinstance(N,dict)else N or[];K=_received_groups(M,J)
	if len(K)!=len(F):return[_f('DEC_NOT_APPLIED','קובץ העבודה אינו מתמפה לטיוטה שהתקבלה (%d פסקאות מול %d): אי אפשר לאמת שההכרעות סומנו'%(len(K),len(F)))]
	a=dt.comment_paragraph_spans(M);U=dt.body_paragraphs(M);b={id(B):A for(A,B)in enumerate(U)}
	def R(p,kind):return bool(dt.revision_text(p,kind,J))or kind=='del'and any(A.get(W+'author')==J for A in p.iter(W+'del'))
	for A in Z:
		D,L,B=A.get('op'),A.get('id','?'),A.get('para')
		if D in(None,'accept'):continue
		C,E=True,''
		if D in('replace_span','replace','delete_paragraph','comment_only'):
			if not isinstance(B,int)or not 0<=B<len(K):Q.append(_f('DEC_NOT_APPLIED','%s: אין פסקה %s בטיוטה'%(L,B),L));continue
			G=K[B];H=_norm_cmp(_para_accept(G))
		if D=='replace_span':
			S,I=_norm_cmp(A.get('old')),_norm_cmp(A.get('new'));c=R(G,'ins')or R(G,'del');V=F[B]
			if P is not None and B<len(P)and dt.their_changes_mode(A)=='reject':V=P[B]
			C=c and(not I or I in H)and(S in I or H.count(S)<_norm_cmp(V).count(S))
			if not C and O is not None and T and B<len(O):
				try:C=bool(dt.prior_edit_exists(O[B],A.get('old'),dt.match_quotes(A.get('new')or'',dt.quote_style(F)),T))and(not I or I in H)
				except dt.UnsupportedEdit:C=False
			E='הטווח "%s" לא סומן'%(A.get('old')or'')[:40]
		elif D=='replace':C=H==_norm_cmp(A.get('new_text'));E='נוסח היעד לא סומן'
		elif D=='delete_paragraph':C=not H and(R(G,'del')or not _norm_cmp(F[B]));E='הפסקה לא נמחקה'
		elif D=='insert_paragraph':X=_norm_cmp(A.get('text'))[-60:];C=bool(X)and any(X in _norm_cmp(_para_accept(A))for A in U if dt._mark(A)=='ins'or('ins',J)in[C for(B,D)in dt._text_nodes(A)for C in dt._revision_of(B,A)]);E='הפסקה החדשה לא נוספה'
		elif D=='comment_only'and A.get('external_comment'):Y=b.get(id(G));C=Y is not None and any(B<=Y<=C for(A,(B,C))in a.items()if A in our_comment_ids);E='הבועה לא נוספה'
		if not C:Q.append(_f('DEC_NOT_APPLIED','%s (%s): %s. ההכרעה לא סומנה בקובץ, ולכן אינה מוכנה למשלוח'%(L,D,E),L))
	return Q
def hidden_text(p):
	B=''
	for C in p.iter(W+'r'):
		A=C.find(W+'rPr');D=[]if A is None else[A.find(W+'vanish'),A.find(W+'webHidden')]
		if any(A is not None and A.get(W+'val')not in('0','false','off')for A in D):B+=''.join(A.text or''for A in C.iter(W+'t',W+'delText'))
	return B
def check_hidden_removals(rroot,decisions):
	D=decisions;I=D.get('decisions',[])if isinstance(D,dict)else D or[];E=dt.body_paragraphs(rroot);H,F={},[]
	for A in I:
		if A.get('kind')!='hidden_text_removal':continue
		B,G=A.get('para'),A.get('op')
		if not isinstance(B,int)or not 0<=B<len(E)or not(G=='replace_span'and not(A.get('new')or'').strip()or G=='delete_paragraph'):F.append(_f('COV_HIDDEN_KIND_INVALID','%s: kind: hidden_text_removal רק על מחיקה של טקסט מוסתר (replace_span עם new ריק, או delete_paragraph)'%A.get('id'),A.get('id')));continue
		C=A.get('old')if G=='replace_span'else dt.para_text(E[B])
		if not _norm_ws(C)or _norm_ws(C)not in _norm_ws(hidden_text(E[B])):F.append(_f('COV_HIDDEN_KIND_INVALID','%s: הטווח "%s" אינו טקסט מוסתר בטיוטה שהתקבלה, ולכן הבועה צריכה לתאר אותו כמו כל שינוי'%(A.get('id'),(C or'')[:50]),A.get('id')));continue
		H.setdefault(B,[]).append(C)
	return H,F
def check_silent_changes(state,decisions,not_applied,mode):
	J=not_applied;B=decisions;G=state or{}
	if not G.get('silent_changes'):return[],[]
	H=_round_of(G,B);I={'meta':{'round_number':H},'silent_changes':[dict(A)for A in G['silent_changes']if isinstance(A,dict)]};K={}
	if B is not None:SB.link_silent_decisions(I,B);K={A.get('id'):A for A in(B.get('decisions',[])if isinstance(B,dict)else B)}
	E=[]
	for A in SB.unresolved_silent_changes(I,H):E.append(_f('SILENT_CHANGE_UNDECIDED','שינוי שלא סומן בסעיף %s (%s) בלי הכרעה מסומנת: החזרה בעקוב אחר שינויים, או קבלה עם בועה, בהכרעה שנושאת silent_change: %s. נדרשת הכרעתך (מצב 9)'%(A.get('clause')or'?',A.get('id'),A.get('id')),A.get('id')))
	for A in I['silent_changes']:
		C=A.get('decision_ref')
		if int(A.get('round')or 0)!=(H or 0)or A.get('decision')not in SB.SILENT_DECISIONS or not C:continue
		F=K.get(C);D=None
		if B is None:D='קובץ ההכרעות לא נמסר לשער, ולכן לא נבדק שההכרעה %s סומנה'%C
		elif F is None:D='ההכרעה %s אינה בקובץ ההכרעות של הסבב'%C
		elif J is None or C in J:D='ההכרעה %s לא סומנה בקובץ בפועל (DEC_NOT_APPLIED)'%C
		elif isinstance(F.get('para'),int)and isinstance(A.get('received_para'),int)and F['para']!=A['received_para']:D='ההכרעה %s מסומנת בפסקה %s, והשינוי השקט בפסקה %s'%(C,F['para'],A['received_para'])
		if D:E.append(_f('SILENT_CHANGE_UNDECIDED','שינוי שלא סומן בסעיף %s (%s): %s'%(A.get('clause')or'?',A.get('id'),D),A.get('id')))
	return(E,[])if mode=='send'else([],E)
def check_structure(root,author):
	B=[]
	for(G,E)in enumerate(dt.body_paragraphs(root)):
		if dt._mark(E)=='ins':
			if not _para_accept(E).strip():B.append(_f('STRUCT_EMPTY_PARAGRAPH','פסקה ריקה שהוספנו',G))
	H=re.compile('^\\s*(\\d+[\\u05d0-\\u05ea]?)[.)]\\u200f?\\s')
	for F in('accept','reject_del_only'):
		C=set()
		for D in dt.paragraph_views(root,F):
			A=H.match(D)
			if A:
				if A.group(1)in C:B.append(_f('STRUCT_DUP_NUMBER','מספר מוקלד כפול בפרק (%s): %s'%(F,A.group(1))));break
				C.add(A.group(1))
			elif D.strip()and len(D.strip())<60:C=set()
	return B
def sent_prior_keys(state,deal_dir):
	B=deal_dir;C=(state or{}).get('meta')or{};A=[A for A in C.get('sent_documents')or()if isinstance(A,dict)]
	if not(B and A):return set()
	def D(rec):A=rec.get('file_name')or rec.get('path')or'';return A if os.path.isabs(A)else os.path.join(B,A)
	E=max(int(A.get('round')or 0)for A in A);F=[D(A)for A in C.get('received_documents')or()if isinstance(A,dict)and int(A.get('round')or 0)<=E];return dt.sent_revision_keys([D(A)for A in A],F)
def run_gate(path,received,mode,profile,state=None,expected_accept=None,window=None,work_path=None,lang=None,register=None,context=None,decisions=None,core=None,deal_dir=None):
	j=expected_accept;a=window;N=decisions;M=profile;J=state;G=lang;F=mode;assert F in('work','send');K=dt.read_package(path);C=etree.fromstring(K['word/document.xml']);b=dt.read_package(received);L=etree.fromstring(b['word/document.xml']);O=[dt.para_text(A)for A in dt.body_paragraphs(L)];G=G or gap_checks.detect_lang('\n'.join(O));c={A['id']for A in dt.read_comments(b)};k=_dt.datetime.now();a=a or(k-_dt.timedelta(days=2),k+_dt.timedelta(minutes=5));E=author_for(M,G);A,H=[],[];U=[E]+[A for A in[M.get('lawyer_name'),M.get('lawyer_name_en')]+list(M.get('lawyer_aliases')or[])if A and A!=E];d=dt.prior_revisions(L,U);z={dt.revision_key(A)for A in L.iter(W+'ins',W+'del')};d|=sent_prior_keys(J,deal_dir)&z;l=dt.set_aside_prior(C,d);A0={A.get(W+'author')for A in L.iter(W+'ins',W+'del')}|l;B,m=check_package(K,C,M,c,a,work_path or path,E,received_authors=A0);A+=B;V=dt.reject_ours_view(C,E);e=[dt.received_reject_text(A,set(U))for A in dt.body_paragraphs(L)]
	if len(V)==len(O):n=all(A==B or A==C for(A,B,C)in zip(V,O,e))
	else:n=V==O
	if not n:A.append(_f('RT_REJECT','"דחה הכול" אינו מחזיר את הטיוטה שהתקבלה'))
	o=dt.paragraph_views(C,'accept')
	if j is not None and o!=j:A.append(_f('RT_ACCEPT','"קבל הכול" אינו נותן את נוסחי היעד'))
	for(P,A1)in enumerate(dt.body_paragraphs(C)):
		p=dt.duplicated_insertions(A1,lambda e:e is not None and e.get(W+'author')==E)
		if p:A.append(_f('RT_DUPLICATE','נוסח כפול בפסקה אחרי "קבל הכול": "%s..." מופיע יותר מפעם אחת, ואחת ההופעות בהוספה שלנו. ההוספה הישנה והחדשה עומדות זו לצד זו'%p[0][:60],P))
	Q='\n'.join(o);X=[A for A in dt.read_comments(K)if A['id']not in c];I=[A for A in X if A['author']==E];f=[A for A in X if A['author']in INTERNAL_AUTHORS];R=dt.comment_paragraph_spans(C);q=dt.body_paragraphs(C);A2={A['id']for A in I}
	for(r,(S,Y))in list(R.items()):
		if r not in A2 or S is None:continue
		P=Y
		while P+1<len(q)and _our_del_mark(q[P+1],E):P+=1
		if P!=Y:R[r]=S,P
	g={}
	for s in I:
		S,Y=R.get(s['id'],(None,None))
		for A3 in range(S,Y+1)if S is not None else(None,):g.setdefault(A3,[]).append(s['text'])
	h=dict(context or{});h.setdefault('waived',sorted(waived_gap_codes(J)));A+=check_bubbles(I,Q,J,'\n'.join(V),G);A+=check_language(C,I,E,G,'\n'.join(O+e));B,D=check_bubble_style(I,G,round_stage(J,N));A+=B;H+=D;H+=check_bubble_text_match(C,I,R,G);A4=[A['text']for A in dt.read_comments(b)if A['author']in U];B,D=check_round_rules(J,N,L,C,U+sorted(l),R,{A['id']for A in I},A4,F);A+=B;H+=D;T,B=check_hidden_removals(L,N)if N is not None else({},[]);A+=B;A5={id(B):A for(A,B)in enumerate(dt.body_paragraphs(C))};t=_received_groups(C,E);u={A:A5[id(B)]for(A,B)in enumerate(t)}if len(t)==len(O)else{};T={u.get(A,A):B for(A,B)in T.items()};v=check_coverage(C,g,E,G,T);A6={u.get(A,A)for(A,B)in enumerate(dt.body_paragraphs(L))if hidden_text(B).strip()}
	for Z in v:
		if Z['code']=='COV_UNCOVERED_CHANGE'and Z['where']in A6 and Z['where']not in T:Z['message']+='. בפסקה יש טקסט מוסתר בטיוטה שהתקבלה: כשהמחיקה היא של הטקסט המוסתר, עם הבועה הניטרלית, ההכרעה נושאת kind: hidden_text_removal'
	A+=v;A+=check_bubble_why(C,g,E,Q,G,h,T);A+=check_contradictions(I,Q,G);H+=check_reasoning_warnings(I);B,i=check_placeholders(C,I,E,J,F);A+=B;B,D=check_identifiers(C,E,M,G,'\n'.join(O));A+=B;H+=D;A+=check_self_created_gaps(C,E,Q,G,h,state=J);B,D=check_state(J,F);A+=B;H+=D;B,D=check_legal_review(J,N,core,F);A+=B;H+=D;B,D=check_entity_name_en(M,G,F,Q+'\n'+'\n'.join(A['text']for A in I));A+=B;H+=D;B,D=check_lawyer_name_en(M,G,F);A+=B;H+=D;B,D=check_internal_leak(K,C,X,F,[A['id']for A in I]);A+=B;H+=D;B,D=check_playbook_text_leak(K,C,X,core,F,[A['id']for A in I]);A+=B;H+=D;B,D=check_ladder_steps(J,F);A+=B;H+=D;A+=check_structure(C,E);w=set()
	if N is not None:B=check_decisions_applied(C,O,N,E,{A['id']for A in I},received_paras=dt.body_paragraphs(L),prior=d,received_rej=e);A+=B;w=None if any(A['where']is None for A in B)else{A['where']for A in B}
	elif F=='send':A.append(_f('DEC_FILE_MISSING','השער רץ בלי קובץ ההכרעות (--decisions), ולכן אינו יכול לוודא שכל הכרעה סומנה בקובץ'))
	else:H.append(_f('DEC_FILE_MISSING','בלי קובץ ההכרעות לא נבדק שכל הכרעה סומנה בקובץ'))
	B,D=check_silent_changes(J,N,w,F);A+=B;H+=D;A7=''.join(K[A].decode('utf-8','ignore')for A in K if A.startswith('word/header'));A8=any(A['author']in INTERNAL_AUTHORS and not A['text'].strip().startswith(dt.AREO_LABEL_PREFIXES)for A in dt.read_comments(K)if A['id']not in c);A9=dt.INTERNAL_HEADER_TEXT,getattr(dt,'INTERNAL_HEADER_TEXT_EN',dt.INTERNAL_HEADER_TEXT);x=any(A in A7 for A in A9)
	if F=='work'and A8 and not x:A.append(_f('INT_HEADER_MISSING','חסרה הכותרת הפנימית בקובץ העבודה'))
	if F=='send':
		if x:A.append(_f('INT_IN_SEND','הכותרת הפנימית נשארה בעותק למשלוח'))
		if f:A.append(_f('INT_IN_SEND','בועה פנימית בעותק למשלוח: %d'%len(f)))
		AA=' '.join(dt.para_text(A)for A in dt.body_paragraphs(C))+' '+' '.join(A['text']for A in dt.read_comments(K))
		if any(A in AA for A in dt.AREO_LABEL_PREFIXES):A.append(_f('AREO_IN_SEND','התווית של סעיף AREO נשארה בעותק למשלוח'))
		y=[B for A in C.iter(W+'ins',W+'del')if A.get(W+'author')==E for B in A.iter(W+'highlight')if B.get(W+'val')==dt.AREO_HIGHLIGHT]
		if y:A.append(_f('AREO_IN_SEND','מירקור צהוב בנוסח שלנו בעותק למשלוח: %d'%len(y)))
	m.update(lang=G,external_comments=len(I),internal_comments=len(f),placeholders=i,signing_checklist=[dict(item='signing_blank',**A)for A in i['signing_blanks']]+[dict(item='their_placeholder',**A)for A in i['theirs']]);return{'mode':F,'passed':not A,'failures':A,'warnings':H,'info':m}
RUNS_DIR='runs'
def run_report_path(deal_dir,round_no,name):
	A=deal_dir
	try:B=int(round_no)
	except(TypeError,ValueError):return
	if not A or B<1:return
	return os.path.join(A,RUNS_DIR,'round-%d'%B,name)
def write_run_report(path,data):
	A=path;D=os.path.dirname(A);os.makedirs(D,exist_ok=True)
	if os.path.exists(A):
		B=os.path.join(D,'history');os.makedirs(B,exist_ok=True);E,F=os.path.splitext(os.path.basename(A));G=_dt.datetime.fromtimestamp(os.path.getmtime(A)).strftime('%Y%m%dT%H%M%S');C=os.path.join(B,'%s.%s%s'%(E,G,F));H=2
		while os.path.exists(C):C=os.path.join(B,'%s.%s-%d%s'%(E,G,H,F));H+=1
		os.replace(A,C)
	with open(A,'w',encoding='utf-8')as I:json.dump(data,I,ensure_ascii=False,indent=2,default=str)
	return A
def build_send_copy(work_path,received,send_path,profile,state=None,expected_accept=None,window=None,lang=None,deal_dir=None,register=None,context=None,decisions=None,core=None):
	F=decisions;D=deal_dir;C=state;A=send_path
	if F is None and D and(C or{}).get('decisions_file'):
		G=os.path.join(D,C['decisions_file'])
		if os.path.exists(G):
			with open(G,encoding='utf-8')as H:F=json.load(H)
	E=A[:-5]+'.tmp.docx'if A.endswith('.docx')else A+'.tmp';paths.check_write_path(E);dt.strip_internal(work_path,E);B=run_gate(E,received,'send',profile,C,expected_accept,window,work_path=A,lang=lang,register=register,context=context,decisions=F,core=core,deal_dir=D)
	if B['passed']:
		os.replace(E,A);B['send_copy']=A
		if C is not None:B['send_copy_record']=pre_send.record_send_copy(C,A,D)
	else:os.remove(E);B['send_copy']=None;B['retracted']=pre_send.retract_send_copy(A,C,B['info'].get('lang','he'),deal_dir=D)
	return B
