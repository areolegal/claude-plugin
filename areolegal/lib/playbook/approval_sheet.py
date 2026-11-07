# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import hashlib,os,re,unicodedata,uuid
from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_BREAK
from docx.oxml import OxmlElement,parse_xml
from docx.oxml.ns import nsdecls,qn
from docx.shared import Cm,Pt
try:from common import rtl;from playbook import status as S
except ImportError:import sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common import rtl;from playbook import status as S
TRACKS='green','yellow','red'
AREO_AUTHOR='Areo'
W14='http://schemas.microsoft.com/office/word/2010/wordml'
MIN_MARKET_SOURCES=3
POINT_NAMES='ours','middle','theirs'
HE={'title':'עמדות משא ומתן לאישור','file':'עמדות-לאישור','cols':['נושא','נדרוש (ירוק)','נסכים (צהוב)','אדום: לא מקבלים כמות שהוא, ומשיבים בנוסח ריפוי'],'importance':{'critical':'קריטית','high':'גבוהה','medium':'בינונית','low':'נמוכה'},'wording':'הנוסח שיוחל, מילה במילה: ','cure':'הנוסח שנשיב כשהצד השני מציע זאת (נוסח ריפוי), מילה במילה: ','no_wording':'אין נוסח להחלה: העמדה מוחלת כתנאי בלבד.','flags':'סימונים: ','areo':'הצעת Areo','legal':'טעון בדיקה משפטית','legal_line':'טעון בדיקה משפטית. נבדק בידי: ','legal_date':'תאריך הבדיקה: ','unverified':'ממצא לא מאומת, {count}{ids}: {reason}','topic_unverified':'ממצא לא מאומת בנושא, שאינו נקודה של אף מסלול: ','market':'הצעת Areo מ-{n} מקורות שוק ({ids})','statute':'חובה בדין ({ids})','company':'מבוסס הסכמי החברה ({n})','company_drafts':'מבוסס מסמכי החברה, רובם טיוטות ({n})','company_forms':'מבוסס נוסחים שהחברה מציגה ({n})','company_other':'מבוסס מסמכים שאינם הסכמים חתומים ({n})','walk_away':'שובר עסקה: לא נחתום','assume':'הנחה שיש לאשר (סמנו אם נכונה): ','choice_head':'בחירה נדרשת: ','recommendation':'המלצת Areo: ','comment_tail':'בחרו אפשרות אחת בתא הנושא. אחר כך פתרו או מחקו הערה זו. בלי בחירה, השורה לא תיקלט.','sign_head':'חתימה לפי עמודה','sign_cols':['עמודה','מאשר','שם מלא','תפקיד','תאריך'],'track_label':{'red':'אדום: מה לא מקבלים כמות שהוא','yellow':'נסכים (צהוב)','green':'נדרוש (ירוק)'},'final':'זו הגרסה הסופית לחתימה.','token':'מזהה הפקה (אין לשנות): {token}','importance_label':'חשיבות: ','single_role':'מה זה מטיל על החברה: ','role_line':'כשהחברה {label}: ','no_reason':'הסיבה לא נרשמה','few_sources':'פחות משלושה מקורות לנקודה','count':('מקורות','מקור אחד','לא נמצאו מקורות'),'rules_count':('כללים','כלל אחד','אין'),'open_market':'%d עמדות נגזרו ממקורות שוק ציבוריים, שלושה מקורות לפחות לכל עמדה','open_unverified':'%d עמדות נשענות על פחות משלושה מקורות שוק, ומסומנות "ממצא לא מאומת"','open_areo':'%d עמדות נוסחו בידי Areo בלי נקודת שוק','open_company':'%d עמדות נגזרו מהסכמי החברה','open_company_drafts':'%d עמדות נגזרו ממסמכי החברה, שרובם טיוטות','open_company_forms':'%d עמדות נגזרו מנוסחים שהחברה מציגה לצד שכנגד','open_company_other':'%d עמדות נגזרו מנוסחים שאינם הסכמים חתומים של החברה','open_statute':'%d עמדות הן חובה בדין','open_walks':'שוברי עסקה: %s (%s); בשאר %d הכללים האדום הוא מה שלא מקבלים כמות שהוא, ומשיבים עליו בנוסח הריפוי','open_no_walks':'אין שובר עסקה; בכל הכללים האדום הוא מה שלא מקבלים כמות שהוא, ומשיבים עליו בנוסח הריפוי','open_head':'אני מאמץ/ת את העמדות שבמסמך כמדיניות החברה. ','mgmt_title':'החלטות הנהלה','mgmt_intro':'אלה החלטות עסקיות במספרים, ולא נוסח משפטי. לכל החלטה מוצע בעל החלטה. כתבו את הערך שנקבע, והעבירו אותו לנוסח בגיליון במקום הסוגריים. תא שנשארו בו סוגריים של ערך שלא נקבע אינו נקלט כמאושר. שאר הגיליון הוא לחתימת היועץ המשפטי.','mgmt_cols':['#','ההחלטה','מה הפלייבוק מציע','הערך שנקבע','בעל החלטה מוצע','שם, תפקיד ותאריך'],'mgmt_set':'{topic}: {slots}','mgmt_in_sentence':'מה הערך במקום {slot} במשפט "{sentence}"? {tail}','mgmt_slot_only':'מה הערך במקום {slot}? {tail}','mgmt_unit':'היחידה: {unit}. כתבו מספר בלבד.','mgmt_no_unit':'כתבו את הערך עם היחידה, למשל "72 שעות" או "30 ימים".','mgmt_confirm':'{topic}: לאשר את המספרים בעמדה','mgmt_confirm_in':'{topic}: האם {num} במשפט "{sentence}" מקובל? {tail}','mgmt_confirm_tail':'היחידה: {unit}. אשרו, או כתבו מספר אחר.','clause_ref':'סעיף {num} במדיניות','mgmt_green':'מקובל עלינו: ','mgmt_yellow':'אפשר להתגמש: ','owners':{'finance':'כספים','infosec':'אבטחת מידע','technology':'טכנולוגיה','management':'הנהלה'},'owner_unverified':' (כדאי לוודא)','legal_head':'עמדות לחתימת היועץ המשפטי'}
EN={'title':'Negotiation positions for approval','file':'Positions-for-approval','cols':['Topic','We require (green)','We accept (yellow)','Red: not accepted as is, answered with cure wording'],'importance':{'critical':'Critical','high':'High','medium':'Medium','low':'Low'},'wording':'Wording to apply, verbatim: ','cure':'Wording we answer with when the other side proposes this (cure wording), verbatim: ','no_wording':'No wording to apply: the position applies as a condition only.','flags':'Flags: ','areo':'Areo proposal','legal':'Needs legal review','legal_line':'Needs legal review. Reviewed by: ','legal_date':'Review date: ','unverified':'Unverified finding, {count}{ids}: {reason}','topic_unverified':'Unverified finding on the topic, not the point of any track: ','market':'Areo proposal from {n} market sources ({ids})','statute':'Required by law ({ids})','company':"Based on the company's agreements ({n})",'company_drafts':"Based on the company's documents, most of them drafts ({n})",'company_forms':'Based on forms the company presents ({n})','company_other':'Based on documents that are not signed agreements ({n})','walk_away':'Deal breaker: we will not sign','assume':'Assumption to confirm (tick if correct): ','choice_head':'Choice required: ','recommendation':'Areo recommendation: ','comment_tail':'Choose one option in the topic cell. Then resolve or delete this comment. Without a choice, the row will not be ingested.','sign_head':'Signature by column','sign_cols':['Column','Approve','Full name','Role','Date'],'track_label':{'red':'Red: what is not accepted as is','yellow':'We accept (yellow)','green':'We require (green)'},'final':'This is the final version for signature.','token':'Issue ID (do not change): {token}','importance_label':'Importance: ','single_role':'What this imposes on the company: ','role_line':'When the company is the {label}: ','no_reason':'reason not recorded','few_sources':'fewer than three sources for the point','count':('sources','one source','no sources found'),'rules_count':('rules','one rule','none'),'open_market':'%d positions were derived from public market sources, at least three sources per position','open_unverified':'%d positions rest on fewer than three market sources, and are marked "Unverified finding"','open_areo':'%d positions were drafted by Areo without a market point','open_company':"%d positions were derived from the company's agreements",'open_company_drafts':"%d positions were derived from the company's documents, most of them drafts",'open_company_forms':'%d positions were derived from forms the company presents to its counterparties','open_company_other':'%d positions were derived from forms that are not signed agreements of the company','open_statute':'%d positions are required by law','open_walks':'Deal breakers: %s (%s); in the other %d rules, red is what is not accepted as is, and is answered with the cure wording','open_no_walks':'No deal breaker; in all rules, red is what is not accepted as is, and is answered with the cure wording','open_head':'I adopt the positions in this document as company policy. ','mgmt_title':'Management decisions','mgmt_intro':'These are business decisions in numbers, not legal wording. Each decision has a proposed decision owner. Write the value decided, and carry it into the wording in the sheet in place of the brackets. A cell that still has brackets for a value not decided is not ingested as approved. The rest of the sheet is for the legal counsel to sign.','mgmt_cols':['#','Decision','What the playbook proposes','Value decided','Proposed decision owner','Name, role and date'],'mgmt_set':'{topic}: {slots}','mgmt_in_sentence':'What value goes in place of {slot} in the sentence "{sentence}"? {tail}','mgmt_slot_only':'What value goes in place of {slot}? {tail}','mgmt_unit':'Unit: {unit}. Write the number only.','mgmt_no_unit':'Write the value with its unit, for example "72 hours" or "30 days".','mgmt_confirm':'{topic}: confirm the numbers in the position','mgmt_confirm_in':'{topic}: is {num} in the sentence "{sentence}" acceptable? {tail}','mgmt_confirm_tail':'Unit: {unit}. Confirm, or write another number.','clause_ref':'Clause {num} of the policy','mgmt_green':'We accept: ','mgmt_yellow':'We can flex to: ','owners':{'finance':'Finance','infosec':'Information security','technology':'Technology','management':'Management'},'owner_unverified':' (to confirm)','legal_head':'Positions for the legal counsel to sign'}
SHEETS={'he':HE,'en':EN}
SINGLE_ROLE_LABEL=HE['single_role']
ROLE_LINE=HE['role_line']
def sheet_lang(lang):return'en'if str(lang or'').strip().lower().startswith('en')else'he'
_EFFECT_FIELD=re.compile('^as_(\\w+)_effect$')
def company_roles(model):
	A=model;C=A.get('scope_summary')or{};D=C.get('company_roles')or[]
	if D:return[(A['role'],A.get('label')or A['role'])for A in D]
	if role_code(A)=='mutual':
		B=[]
		for G in A.get('rules')or[]:
			for E in(G.get('traffic_light')or{}).values():
				for F in list((E or{}).get('role_effects')or{})+[A.group(1)for A in map(_EFFECT_FIELD.match,(E or{}).keys())if A]:
					if F not in B:B.append(F)
		H=C.get('role_labels')or{};return[(A,H.get(A)or A)for A in B]or[('company',None)]
	return[('company',None)]
def role_effect(t,role,single=False):
	A=role;B=(t.get('role_effects')or{}).get(A)or t.get('as_%s_effect'%A)
	if not B and(A=='company'or single):B=t.get('company_effect')or next((t[A]for A in sorted(t)if _EFFECT_FIELD.match(A)and t[A]),'')
	return(B or'').strip()
def role_lines(model,lang='he'):
	B=SHEETS[sheet_lang(lang)];A=company_roles(model)
	if len(A)==1:return[(A[0][0],B['single_role'])]
	return[(A,B['role_line'].format(label=C))for(A,C)in A]
_LATIN=re.compile('[A-Za-z][A-Za-z0-9/&.\\-"\\\'(),;:]*(?:[ ][A-Za-z0-9/&.\\-"\\\'(),;:]+)*')
class SheetError(ValueError):0
def norm_text(s):s=unicodedata.normalize('NFKC',s or'');s=re.sub('[\u200e\u200f\u202a-\u202e\u2066-\u2069]','',s);return re.sub('\\s+',' ',s).strip()
def fingerprint(parts):return hashlib.sha256('\n'.join(norm_text(A)for A in parts).encode('utf-8')).hexdigest()
def cell_key(rule_id,track,segment=None):return'%s|%s|%s'%(rule_id,segment or'-',track)
def role_code(model):A=model;B=(A.get('scope_summary')or{}).get('contract_families')or[{}];return B[0].get('company_role_code')or A.get('company_role_code')or'mutual'
def track_wording(track,t,lang='he'):
	if track=='yellow':
		B=t.get('fallback_wording')
		if isinstance(B,dict)and B.get('text'):return B['text']
		if isinstance(B,str)and B.strip():return B
	A=t.get('proposed_clause')
	if isinstance(A,dict):return A.get(lang)or A.get(A.get('source_language')or'')or A.get('en')or A.get('he')or''
	return A or t.get('preferred_wording')or''
def clause_text(pc,lang='he'):
	B=pc;A=lang;A='en'if str(A or'').strip().lower().startswith('en')else'he'
	if isinstance(B,dict):
		for C in(A,'he'if A=='en'else'en'):
			if str(B.get(C)or'').strip():return B[C],C
		return'',A
	return B if isinstance(B,str)else'',A
def wiz_hash(text):
	A=0;B=str(text or'').encode('utf-16-le')
	for C in range(0,len(B),2):A=A*31+(B[C]|B[C+1]<<8)&4294967295
	return'h%x'%A
def legal_review_tracks(rule):
	A=rule.get('legal_review_required')
	if A is True:return set(TRACKS)
	if isinstance(A,list):return{A.get('track')for A in A if isinstance(A,dict)and A.get('track')}|{B for A in A if isinstance(A,dict)for B in A.get('tracks')or()}|{A for A in A if isinstance(A,str)}
	return set(rule.get('legal_review_tracks')or[])
def count_he(n,noun='מקורות',one='מקור אחד',none='לא נמצאו מקורות'):
	n=int(n or 0)
	if n==0:return none
	if n==1:return one
	return'%d %s'%(n,noun)
def unverified_label(n,ids,reason,lang='he'):
	B=ids;A=reason;C=SHEETS[sheet_lang(lang)];B=[A for A in B or[]if A];A=(A or C['no_reason']).strip()
	if C is HE:A=re.sub('(?<!\\d)1 מקורות','מקור אחד',A)
	return C['unverified'].format(count=count_he(n,*C['count']),ids=' (%s)'%', '.join(B)if B else'',reason=A)
def market_ids(t):return list(t.get('market_source_ids')or t.get('source_ids')or[A for B in t.get('evidence')or[]for A in[B.get('source_id')]if A])
def _point_levels(model):
	C={}
	for A in(model.get('market_research')or{}).get('ranges')or[]:
		D=A.get('topic')or A.get('rule_id');E={}
		for F in POINT_NAMES:
			B=A.get(F)
			if isinstance(B,dict)and'level'in B:E[F]=B['level']
		if D:C[D]=E
	return C
def unverified_index(model):
	C=model;I=_point_levels(C);J={A['rule_id']:A for A in C.get('rules')or[]};D,E={},{}
	for A in(C.get('market_research')or{}).get('unverified_findings')or[]:
		B=A.get('rule_id')or A.get('topic_id')
		if not B:continue
		if A.get('track'):D.setdefault((B,A['track']),[]).append(A);continue
		F=False;K=J.get(B)or{}
		for G in TRACKS:
			L=(K.get('traffic_light')or{}).get(G)or{};H=L.get('range_point')
			if H and'level'in A and I.get(B,{}).get(H)==A['level']:D.setdefault((B,G),[]).append(A);F=True
		if not F:E.setdefault(B,[]).append(A)
	return D,E
def _finding_label(u,lang='he'):
	B=u.get('source_ids')or[];A=u.get('sources_found',len(B))
	if isinstance(A,(list,tuple)):B,A=B or list(A),len(A)
	if u.get('label')and not A and not B and('לא נבדק'in u['label']or'not checked'in u['label'].lower()):return u.get('reason')or u['label']
	return unverified_label(A,B,u.get('reason'),lang)
def evidence_flag(track,t,lang='he',corpus_status='signed'):
	A=SHEETS[sheet_lang(lang)];C=t.get('basis')
	if C=='areo_proposal':return A['areo']
	if C=='market_standard':
		B=market_ids(t)
		if len(B)>=MIN_MARKET_SOURCES:return A['market'].format(n=len(B),ids=', '.join(B))
		return unverified_label(len(B),B,t.get('verification_reason')or A['few_sources'],lang)
	if C=='statute':return A['statute'].format(ids=', '.join(t.get('legal_source_ids')or t.get('source_ids')or[]))
	if C:D='company'+S.CORPUS_SUFFIX.get(corpus_status,'');return A[D].format(n=len(t.get('evidence')or[]))
def flags_for(rule,track,t,index=None,lang='he',corpus_status='signed'):
	D=track;B=lang;A=[];E=evidence_flag(D,t,B,corpus_status)
	if E:A.append(E)
	H=t.get('basis')=='market_standard'and len(market_ids(t))>=MIN_MARKET_SOURCES;I=(index or({},{}))[0]
	if not H:
		for J in I.get((rule['rule_id'],D))or[]:A.append(_finding_label(J,B))
		if t.get('verification')=='not_verified':A.append(unverified_label(t.get('sources_found',0),t.get('source_ids')or[],t.get('verification_reason'),B))
	F,G=set(),[]
	for C in A:
		if C not in F:F.add(C);G.append(C)
	return G
def _checkbox(paragraph,tag,lang='he'):A='<w:sdt %s xmlns:w14="%s"><w:sdtPr><w:tag w:val="%s"/><w14:checkbox><w14:checked w14:val="0"/><w14:checkedState w14:val="2612" w14:font="MS Gothic"/><w14:uncheckedState w14:val="2610" w14:font="MS Gothic"/></w14:checkbox></w:sdtPr><w:sdtContent><w:r><w:rPr>%s</w:rPr><w:t>☐</w:t></w:r></w:sdtContent></w:sdt>'%(nsdecls('w'),W14,tag,''if lang=='en'else'<w:rtl/>');paragraph._p.append(parse_xml(A))
def script_runs(text):
	B=text;C,A=[],0
	for D in _LATIN.finditer(B):
		if D.start()>A:C.append((B[A:D.start()],False))
		C.append((D.group(),True));A=D.end()
	if A<len(B):C.append((B[A:],False))
	return[A for A in C if A[0]]
def add_mixed_runs(paragraph,text,bold=False,size=9,lang='he'):
	C=size;B=paragraph
	if lang=='en':A=B.add_run(text);A.bold=bold;A.font.size=Pt(C);return B
	for(D,E)in script_runs(text):
		A=B.add_run(D);A.bold=bold
		if E:A.font.size=Pt(C);rtl.set_run_ltr(A)
		else:rtl.set_run_rtl(A,size=C)
	rtl.set_paragraph_rtl(B);return B
def _cell_lines(cell,lines,lang='he'):
	A=cell;B=not A.paragraphs[0].runs;C=[]
	for(E,F)in lines:D=A.paragraphs[0]if B else A.add_paragraph();B=False;add_mixed_runs(D,E,bold=F,size=9,lang=lang);C.append(D)
	return C
def _hide_paragraph(p):
	for C in p.runs:C.font.hidden=True
	B=p._p.get_or_add_pPr();A=B.find(qn('w:rPr'))
	if A is None:A=OxmlElement('w:rPr');B.append(A)
	if A.find(qn('w:vanish'))is None:A.append(OxmlElement('w:vanish'))
def _check_hebrew_only(text,lang='he'):
	A='market_built','own_plus_market','areo_proposal','market_standard'
	if lang!='en':A+='critical','Inferred'
	for B in A:
		if B in text:raise SheetError('תווית באנגלית בגיליון: %s'%B)
def basis_counts(model):
	A={'market':0,'areo':0,'company':0,'statute':0,'unverified':0}
	for D in model.get('rules')or[]:
		for E in TRACKS:
			C=(D.get('traffic_light')or{}).get(E)or{};B=C.get('basis')
			if B=='market_standard':A['market'if len(market_ids(C))>=MIN_MARKET_SOURCES else'unverified']+=1
			elif B=='areo_proposal':A['areo']+=1
			elif B=='statute':A['statute']+=1
			else:A['company']+=1
	return A
def opening_text(model,counts,lang='he'):
	F=counts;E=model;A=SHEETS[sheet_lang(lang)];G='open_company'+S.CORPUS_SUFFIX.get(S.corpus_status(E),'');B=[]
	for C in('market','unverified','areo','company','statute'):
		if F.get(C):B.append(A[G if C=='company'else'open_'+C]%F[C])
	D=[A['rule_id']for A in E.get('rules')or[]if A.get('walk_away')is True];H=len(E.get('rules')or[])
	if D:B.append(A['open_walks']%(count_he(len(D),*A['rules_count']),', '.join(D),H-len(D)))
	else:B.append(A['open_no_walks'])
	return A['open_head']+'; '.join(B)+'.'
SLOT_WORDS='מספר','מכפיל','שיעור','אחוז','ימים','שעות','חודשים','שנים','number','multiple','multiplier','percentage','percent','days','hours','months','years','x','n'
_COUNT_WORDS='מספר','number'
_UNITS='שעות','ימים','ימי','חודשים','שנים','פעמים','hours','days','months','years','times'
_SLOT=re.compile('\\[([^\\[\\]]{0,40})\\]')
_SLOT_FILLER=re.compile('^[\\s_.\\-•●*#xX?]*$')
MAX_DECISIONS=8
DECISION_TOPICS=('cap','finance',('תקרה','תקרת','הגבלת אחריות','הגבלת החבות'),('cap','liabilit'),('LIAB','CAP'),()),('insurance','finance',('ביטוח',),('insur',),('INS','INSUR'),('insurance',)),('indemnity','finance',('שיפוי',),('indemn',),('INDEM','IND'),()),('guarantee','finance',('ערבות','ערבויות','בטוחה','בטוחות','פיקדון','שעבוד'),('guarantee','deposit','collateral','bond'),('GUAR','DEPOSIT','COLL'),('guarantee',)),('payment','finance',('תשלום','תמורה','מחיר','תעריף','ריבית','דמי ','עמלה','שכר טרחה','שכר עבודה'),('payment',' fee','price','interest',' rent','commission'),('PAY','FEES','PRICE'),('payment',)),('price_adjustment','finance',('הצמדה','עדכון מחיר','עדכון תעריף'),('indexation','price adjustment'),('INDEX',),('price_adjustment',)),('audit','management',('ביקורת',),('audit','inspection'),('AUDIT',),('audit',)),('notice','management',('הודעה','דיווח'),('notice','notif','report'),('NOTIF','NOTICE','REPORT'),('notice','reporting')),('consent','management',('הסכמה מראש','אישור מראש','קבלני משנה','המחאה'),('consent','subcontract','assignment'),('CONSENT','ASSIGN'),('consent_approval',)),('deliverable','management',('זמינות','רמת שירות','רמות שירות','תמיכה','אבני דרך','אבן דרך','מסירה','לוח זמנים'),('availability','service level','support','milestone','delivery'),('SLA','SUPPORT','MILESTONE'),('deliverable','milestone')),('return','management',('מחיקה','מחיקת','השבת','החזרת'),('deletion','return of'),('DEL','RETURN'),('data_return_deletion',)),('confidentiality','management',('סודיות',),('confidential',),('CONF',),('confidentiality',)),('termination','management',('סיום','תקופת','ביטול','חידוש','שרידות','אופציה'),('terminat','renewal','surviv','option'),('TERM','EXIT','RENEW'),('term_end','renewal_notice','option')),('compliance','management',('ציות','רגולצי','רישיון','היתר'),('complian','regulat','licen','permit'),('COMPL','REG'),('compliance',))
_IMPORTANCE_RANK={'critical':0,'high':1,'medium':2,'low':3}
def decision_slots(text):
	C=[]
	for D in _SLOT.finditer(text or''):
		B=D.group(1).strip();A=(B.split()or[''])[0].strip(':,.').lower()
		if A.startswith('ה')and A[1:]in SLOT_WORDS:A=A[1:]
		E=B.lower().split(None,1)[1]if len(B.split())>1 else''
		if A in _COUNT_WORDS and E and not any(A in E for A in _UNITS):continue
		if(_SLOT_FILLER.match(B)or A in SLOT_WORDS)and D.group(0)not in C:C.append(D.group(0))
	return C
def _decision_topic(rule):
	A=' '+' '.join(str(rule.get(A)or'')for A in('topic_name','clause_issue','topic_name_en')).lower();B=set(re.split('[_\\-\\s]+',str(rule.get('rule_id')or'').upper()))
	for(C,D,E,F,G,H)in DECISION_TOPICS:
		if B&set(G)or any(B in A for B in E)or any(B in A for B in F):return C,D,H
def _decision_owner(model,rule,topic,T):
	E=model;C=topic;A=C[1]if C else'management'
	if rule.get('decision_owner'):return A,rule['decision_owner']
	for F in C[2]if C else():
		for B in E.get('obligation_assignments')or():
			if isinstance(B,dict)and B.get('type')==F and str(B.get('department')or'').strip():G=str(B['department']).strip();return None,G+(T['owner_unverified']if B.get('needs_verification')else'')
	H=T['owners'][A].lower()
	for D in E.get('responsible_departments')or():
		if isinstance(D,str)and H in D.lower():return A,D.strip()
	return A,T['owners'][A]
def _short(s,n=160):s=norm_text(s);return s if len(s)<=n else s[:n-1].rstrip()+'…'
UNIT_NAMES={'hours':{'he':'שעות','en':'hours'},'business_days':{'he':'ימי עבודה','en':'business days'},'days':{'he':'ימים','en':'days'},'weeks':{'he':'שבועות','en':'weeks'},'months':{'he':'חודשים','en':'months'},'years':{'he':'שנים','en':'years'},'percent':{'he':'אחוזים','en':'percent'},'times':{'he':'פעמים','en':'times'},'multiple':{'he':'מכפלה (פי כמה)','en':'a multiple (times)'}}
_UNIT_FORMS=('business_days',('ימי עבודה','ימי עסקים','business days','working days')),('hours',('שעות','שעה','השעות','hours','hour')),('days',('ימים','יום','ימי','הימים','days','day','calendar days')),('weeks',('שבועות','שבוע','weeks','week')),('months',('חודשים','חודש','החודשים','months','month')),('years',('שנים','שנה','השנים','years','year')),('percent',('אחוזים','אחוז','%','percent','per cent','percentage')),('times',('פעמים','פעם','times')),('multiple',('מכפיל','המכפיל','multiple','multiplier'))
_SENT_SPLIT=re.compile('(?<=[.;!?])\\s+')
def unit_of(text,loose=False):
	A=norm_text(text).lower().strip(' .,:;()')
	if not A:return
	for(B,C)in _UNIT_FORMS:
		for D in C:
			if A==D or A.startswith(D+' ')or D=='%'and A.startswith('%'):return B
	E=A.split()
	if loose and len(E)<=4:
		for(B,C)in _UNIT_FORMS:
			if any(A in E for A in C if A!='פעם'):return B
def slot_context(texts,slot):
	A=slot
	for B in texts:
		B=norm_text(B)
		if A not in B:continue
		C=next((B for B in _SENT_SPLIT.split(B)if A in B),B)
		if len(C)>320:F=C.index(A);G,H=max(0,F-150),min(len(C),F+len(A)+150);C=('…'if G else'')+C[G:H].strip()+('…'if H<len(C)else'')
		E=A.strip('[]').split();J=' '.join(E[1:])if len(E)>1 else' '.join(E);D,I=unit_of(J,loose=True),'inside'
		if not D:K=B[B.index(A)+len(A):];D,I=unit_of(K[:24]),'after'
		return{'slot':A,'sentence':C,'unit':D,'unit_where':I if D else None}
	return{'slot':A,'sentence':'','unit':None,'unit_where':None}
def _decision_texts(rule,lang):A=lang;B=rule.get('traffic_light')or{};C=[(B.get(A)or{}).get('position')or''for A in TRACKS];D=[track_wording(C,B.get(C)or{},A)for C in TRACKS];E=[track_wording(C,B.get(C)or{},'he'if A=='en'else'en')for C in TRACKS];return D+C+E if A=='en'else C+D+E
_NUM_UNIT=re.compile('(?<![\\w.])(\\d+(?:[.,]\\d+)?)\\s*(%|[^\\W\\d_]+(?:\\s+[^\\W\\d_]+)?)?')
def number_context(texts):
	for A in texts:
		A=norm_text(A)
		for B in _NUM_UNIT.finditer(A):
			C=next((A for A in _SENT_SPLIT.split(A)if B.group(0)in A),A)
			if len(C)>320:D=max(0,A.index(B.group(0)));C=('…'if D>150 else'')+A[max(0,D-150):D+170].strip()+'…'
			E=unit_of(B.group(2)or'')or(unit_of((B.group(2)or'').split()[0])if B.group(2)else None)
			if not E:continue
			return{'slot':B.group(1),'sentence':C,'unit':E,'unit_where':'after'if E else None}
def decision_question(topic,contexts,lang):
	A=SHEETS[sheet_lang(lang)];C=[]
	for B in contexts:
		D=(UNIT_NAMES.get(B.get('unit'))or{}).get(sheet_lang(lang));E=A['mgmt_unit'].format(unit=D)if D else A['mgmt_no_unit']
		if B.get('sentence'):C.append(A['mgmt_in_sentence'].format(slot=B['slot'],sentence=B['sentence'],tail=E))
		else:C.append(A['mgmt_slot_only'].format(slot=B['slot'],tail=E))
	return A['mgmt_set'].format(topic=topic,slots='; '.join(C))
def management_decisions(model,lang='he'):
	H=model;D=lang;G=SHEETS[sheet_lang(D)];N=H.get('management_decisions')or[];K=[]
	if N:
		V={A.get('rule_id'):A for A in H.get('rules')or[]}
		for A in N[:MAX_DECISIONS]:
			O=A.get('owner_code')or'';C=list(A.get('slots')or[]);B=V.get(A.get('rule_id'))or{};E=[slot_context(_decision_texts(B,sheet_lang(D)),A)for A in C];F=A.get('question')or''
			if E and not any(A['sentence']and A['sentence']in F for A in E):F=decision_question(B.get('topic_name')or F or A.get('rule_id')or'',E,D)
			K.append({'rule_id':A.get('rule_id'),'question':F,'proposal':A.get('proposal')or'','slots':C,'context':E,'owner_code':O or None,'owner':A.get('owner')or A.get('decision_owner')or G['owners'].get(O,'')})
	else:
		P=[]
		for(W,B)in enumerate(H.get('rules')or[]):
			Q=B.get('traffic_light')or{};C,R=[],False
			for I in TRACKS:
				L=Q.get(I)or{}
				for S in decision_slots((L.get('position')or'')+' '+track_wording(I,L,D)):
					if S not in C:C.append(S)
				if I!='red'and re.search('\\d',L.get('position')or''):R=True
			if not C and not R:continue
			X=_decision_topic(B);Y,Z=_decision_owner(H,B,X,G);M=B.get('topic_name')or B.get('rule_id')or'';E=[slot_context(_decision_texts(B,sheet_lang(D)),A)for A in C];J=None if C else number_context([B for(A,B)in zip(TRACKS*3,_decision_texts(B,sheet_lang(D)))if A!='red'])
			if J:a=(UNIT_NAMES.get(J['unit'])or{}).get(sheet_lang(D));b=G['mgmt_confirm_tail'].format(unit=a);F=G['mgmt_confirm_in'].format(topic=M,num=J['slot'],sentence=J['sentence'],tail=b);E=[J]
			else:F=decision_question(M,E,D)if C else G['mgmt_confirm'].format(topic=M)
			T=[]
			for(I,c)in(('green','mgmt_green'),('yellow','mgmt_yellow')):
				U=((Q.get(I)or{}).get('position')or'').strip()
				if U:T.append(G[c]+_short(U))
			d=0 if C else 1,_IMPORTANCE_RANK.get(str(B.get('importance')or'').lower(),4),W;P.append((d,{'rule_id':B.get('rule_id'),'question':F,'proposal':'\n'.join(T),'slots':C,'context':E,'owner_code':Y,'owner':Z}))
		K=[A for(B,A)in sorted(P,key=lambda x:x[0])[:MAX_DECISIONS]]
	for(e,A)in enumerate(K,1):A['n']=e;A['num']=display_num(H,A.get('rule_id'))
	return K
def display_num(model,rule_id):
	for(B,A)in enumerate(model.get('rules')or[]):
		if A.get('rule_id')==rule_id:return str(A.get('clause_number')or B+1)
	return''
def _decisions_page(doc,decisions,lang):
	C=doc;A=lang;B=SHEETS[A];E=A=='en'
	if E:_plain_para(C,B['mgmt_title'],bold=True,size=13)
	else:rtl.add_paragraph(C,B['mgmt_title'],bold=True,size=13)
	add_mixed_runs(C.add_paragraph(),B['mgmt_intro'],size=10,lang=A);F=C.add_table(rows=1,cols=len(B['mgmt_cols']));F.style='Table Grid'
	for(I,J)in enumerate(B['mgmt_cols']):_cell_lines(F.rows[0].cells[I],[(J,True)],A)
	for D in decisions:G=F.add_row().cells;_cell_lines(G[0],[(str(D['n']),True)],A);_cell_lines(G[1],[(D['question'],True)]+([(B['clause_ref'].format(num=D['num']),False)]if D.get('num')else[]),A);_cell_lines(G[2],[(A,False)for A in(D.get('proposal')or'-').split('\n')],A);_cell_lines(G[4],[(D.get('owner')or'',False)],A)
	if not E:rtl.set_table_rtl(F)
	H=C.add_paragraph();H.add_run().add_break(WD_BREAK.PAGE)
	if not E:rtl.set_paragraph_rtl(H)
	if E:_plain_para(C,B['legal_head'],bold=True,size=13)
	else:rtl.add_paragraph(C,B['legal_head'],bold=True,size=13)
def cell_view(model,rule,track,lang='he',index=None,roles=None,decisions=None):
	J=decisions;I=index;F=track;E=rule;D=model;B=roles;A=lang;A=sheet_lang(A);B=B if B is not None else role_lines(D,A);C=(E.get('traffic_light')or{}).get(F)or{};K=(C.get('position')or'').strip();L=(track_wording(F,C,A)or'').strip();M={A:role_effect(C,A,single=len(B)==1)for(A,D)in B};G=[K,L]+[M[A]for(A,B)in B];H=decision_slots(' '.join(G))
	for N in J if J is not None else management_decisions(D,A):
		if N.get('rule_id')==E.get('rule_id'):H+=[A for A in N.get('slots')or[]if A in' '.join(G)and A not in H]
	return{'position':K,'wording':L,'effects':M,'flags':flags_for(E,F,C,I if I is not None else unverified_index(D),A,S.corpus_status(D)),'legal':F in legal_review_tracks(E),'assumptions':list(C.get('assumptions')or[]),'slots':H,'fp':fingerprint(G)}
def _wording_gate(model):
	from playbook import validate_model as B;A=B.wording_findings(model)
	if A:C=['%s %s: %s'%(A['rule_id'],A.get('track')or'',A['message'])for A in A[:20]];raise SheetError('נוסח שנכשל בבדיקות הפערים (מודול בדיקות הפערים, common/gap_checks.py). הגיליון אינו מופק עד שהנוסח יתוקן:\n'+'\n'.join(C))
def _plain_para(doc,text,bold=False,size=11):A=doc.add_paragraph();B=A.add_run(text);B.bold=bold;B.font.size=Pt(size);return A
def build_sheet(model,out_dir,company='',lang='he',token_uid=None,check_wording=True):
	p=out_dir;R=company;F=model;A=lang;A=sheet_lang(A);B=SHEETS[A];I=A=='en'
	if check_wording:_wording_gate(F)
	T=role_lines(F,A);q=unverified_index(F);d=F.get('family_id')or'family';r=token_uid or uuid.uuid4().hex[:12];e='ISS-0001|%s|%s'%(d,r);C=Document();M=C.sections[0];M.orientation=WD_ORIENT.LANDSCAPE;M.page_width,M.page_height=M.page_height,M.page_width
	for A5 in('left_margin','right_margin','top_margin','bottom_margin'):setattr(M,A5,Cm(1.5))
	if I:_plain_para(C,B['title'],bold=True,size=16)
	else:rtl.add_paragraph(C,B['title'],bold=True,size=16)
	if R:add_mixed_runs(C.add_paragraph(),R,size=10,lang=A)
	s=basis_counts(F);U=management_decisions(F,A);P={'token':e,'uid':r,'family_id':d,'lang':A,'rows':{},'cells':{},'counts':s,'questions':{},'decisions':U}
	if U:_decisions_page(C,U,A)
	J=C.add_paragraph();_checkbox(J,'chk:open:Q-00',A);add_mixed_runs(J,' '+opening_text(F,s,A),size=10,lang=A);V=C.add_table(rows=1,cols=4);V.style='Table Grid'
	for(K,f)in enumerate(B['cols']):_cell_lines(V.rows[0].cells[K],[(f,True)],A)
	t={}
	for D in F.get('validation_queue')or[]:
		if D.get('rule_id')and not D.get('answered')and(D.get('status')or'open')=='open':t.setdefault(D['rule_id'],[]).append(D)
	for L in F.get('rules')or[]:
		G=L['rule_id'];W=G;H=V.add_row().cells;A6=B['importance'].get(str(L.get('importance')or'').lower(),'');X=[(W,True),(L.get('topic_name')or'',True),(B['importance_label']+A6,False)]
		if L.get('walk_away')is True:X.append((B['walk_away'],True))
		for A7 in q[1].get(G)or[]:X.append((B['topic_unverified']+_finding_label(A7,A),False))
		for(g,_)in X:_check_hebrew_only(g,A)
		_hide_paragraph(_cell_lines(H[0],X,A)[0]);Y={'rule_id':G,'segment':None,'choices':[],'comment':False,'questions':[]}
		for D in t.get(G,[]):
			h=D.get('id')or D.get('queue_id')or'Q';u=[(B['choice_head']+(D.get('question')or''),True)]
			if D.get('recommendation'):u.append((B['recommendation']+D['recommendation'],False))
			A8=_cell_lines(H[0],u,A)[0];v=[]
			for(Z,w)in enumerate(D.get('options')or[]):x=H[0].add_paragraph();N='chk:choice:%s:%s:%d'%(G,h,Z);_checkbox(x,N,A);add_mixed_runs(x,' '+w,size=9,lang=A);Y['choices'].append(N);v.append({'tag':N,'index':Z,'text':w})
			y=C.add_comment(A8.runs[0],text=B['choice_head']+(D.get('question')or''),author=AREO_AUTHOR,initials='AR');y.add_paragraph(B['comment_tail'])
			if not I:
				for A9 in y.paragraphs:rtl.set_paragraph_rtl(A9)
			Y['comment']=True;Y['questions'].append(h);P['questions'][h]={'row':W,'question':D.get('question')or'','options':v,'severity':D.get('severity')}
		P['rows'][W]=Y
		for(K,E)in enumerate(TRACKS):
			Q=(L.get('traffic_light')or{}).get(E)or{};i=(Q.get('position')or'').strip();a=(track_wording(E,Q,A)or'').strip()
			if E in('green','yellow')and not a:raise SheetError('%s %s: אין נוסח להחלה. הגיליון מציג את הנוסח שיוחל, ולא תקציר.'%(G,E))
			b={}
			for(j,AF)in T:
				z=role_effect(Q,j,single=len(T)==1)
				if not z:raise SheetError('%s %s: חסרה שורת ההשפעה של התפקיד %s. כל תא מציג מה העמדה מטילה על החברה בכל תפקיד שיש לה בהסכם.'%(G,E,j))
				b[j]=z
			k=flags_for(L,E,Q,q,A,S.corpus_status(F));AA=B['cure']if E=='red'else B['wording'];O=[(i,True),(AA+(a or B['no_wording']),False)];O+=[(B+b[A],False)for(A,B)in T]
			if k:O.append((B['flags']+' · '.join(k),False))
			A0=E in legal_review_tracks(L)
			if A0:O.append((B['legal_line'],True));O.append((B['legal_date'],True))
			for(g,_)in O:_check_hebrew_only(g,A)
			_cell_lines(H[1+K],O,A);l=[]
			for(Z,A1)in enumerate(Q.get('assumptions')or[]):A2=H[1+K].add_paragraph();N='chk:assume:%s:%s:%d'%(G,E,Z);_checkbox(A2,N,A);add_mixed_runs(A2,' '+B['assume']+A1,size=9,lang=A);l.append({'tag':N,'text':A1})
			m=[i,a]+[b[A]for(A,B)in T];n=decision_slots(' '.join(m))
			for A3 in U:
				if A3.get('rule_id')==G:n+=[A for A in A3.get('slots')or[]if A in' '.join(m)and A not in n]
			P['cells'][cell_key(G,E)]={'row':W,'col':1+K,'fp':fingerprint(m),'position':i,'wording':a,'effects':b,'flags':k,'legal_review':A0,'assumptions':[A['tag']for A in l],'assumption_texts':l,'decision_slots':n}
	if not I:rtl.set_table_rtl(V)
	if I:_plain_para(C,B['sign_head'],bold=True,size=11)
	else:rtl.add_paragraph(C,B['sign_head'],bold=True,size=11)
	c=C.add_table(rows=1,cols=5);c.style='Table Grid'
	for(K,f)in enumerate(B['sign_cols']):_cell_lines(c.rows[0].cells[K],[(f,True)],A)
	for E in('red','yellow','green'):H=c.add_row().cells;_cell_lines(H[0],[(B['track_label'][E],True)],A);_checkbox(H[1].paragraphs[0],'chk:sign:%s'%E,A)
	if not I:rtl.set_table_rtl(c)
	J=C.add_paragraph();_checkbox(J,'chk:final',A)
	if I:J.add_run(' '+B['final']).font.size=Pt(11)
	else:rtl.set_run_rtl(J.add_run(' '+B['final']),size=11);rtl.set_paragraph_rtl(J)
	add_mixed_runs(C.add_paragraph(),B['token'].format(token=e),size=7,lang=A);A4=C.settings.element
	if A4.find(qn('w:trackRevisions'))is None:A4.insert(0,OxmlElement('w:trackRevisions'))
	if I:from playbook import surfaces_render as AB;AB.enforce_ltr_document(C,author=R,title=B['title'])
	else:rtl.enforce_document(C,author=R,title=B['title']);C.core_properties.language='he-IL'
	C.core_properties.identifier=e;AC=re.sub('[\\\\/:*?"<>|]+','-',F.get('family_label')or d)[:40];AD='%s-%s-v1.docx'%(B['file'],AC);os.makedirs(p,exist_ok=True);o=os.path.join(p,AD);C.save(o)
	with open(o,'rb')as AE:P['issued_sha256']=hashlib.sha256(AE.read()).hexdigest()
	return o,P
