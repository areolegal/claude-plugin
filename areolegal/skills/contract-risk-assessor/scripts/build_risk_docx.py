#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'גרסת ה-Word של דוח הסיכונים, רק לבקשת המשתמש, באותו מבנה ובאותו סדר בדיוק.'
import argparse,datetime as _dt,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from docx import Document
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt,RGBColor
from common import paths,rtl
import risk_states as RS
from risk.render_check import band_text_from_register
LENS_HE={'legal':'משפטי-חוזי','financial':'כספי','operational':'תפעולי','technology':'טכנולוגי וסייבר','regulatory':'רגולציה ופרטיות','reputational':'מוניטין','insurance':'ביטוח','force_majeure':'כוח עליון וגיאופוליטי'}
LEVEL_HE={'critical':'קריטי','high':'גבוה','medium':'בינוני','low':'נמוך'}
LEVEL_ORDER={'critical':0,'high':1,'medium':2,'low':3}
SIGN_HE={'yes':'אפשר לחתום כמו שהוא','with_fixes':'אפשר לחתום אחרי התיקונים','no':'לא מומלץ לחתום כמו שהוא'}
SIDE_HE={'as_obligor':'כמי שמתחייב','as_beneficiary':'כמי שהסעיף מגן עליו','both':'בשני התפקידים','as_discloser':'כמי שהסעיף מגן עליו','as_recipient':'כמי שמתחייב'}
STATUS_HE={'findings':'נמצאו ממצאים','none_found':'נבדק ולא נמצא','not_checked':'לא נבדק'}
LENS_EN={'legal':'Legal and contractual','financial':'Financial','operational':'Operational','technology':'Technology and cyber','regulatory':'Regulation and privacy','reputational':'Reputation','insurance':'Insurance','force_majeure':'Force majeure and geopolitical'}
LEVEL_EN={'critical':'Critical','high':'High','medium':'Medium','low':'Low'}
SIGN_EN={'yes':'Can be signed as is','with_fixes':'Can be signed after the fixes','no':'Should not be signed as is'}
SIDE_EN={'as_obligor':'As the bound party','as_beneficiary':'As the protected party','both':'In both roles','as_discloser':'As the protected party','as_recipient':'As the bound party'}
STATUS_EN={'findings':'Findings identified','none_found':'Checked, nothing found','not_checked':'Not checked'}
T={'he':{'lens':LENS_HE,'level':LEVEL_HE,'sign':SIGN_HE,'side':SIDE_HE,'status':STATUS_HE,'title':'Areo Workspace | סיכונים','glance':'התמונה במבט אחד','head':('הצד שכנגד','העסקה','הצד שלנו בהסכם','מה נסרק','מה לא נמסר','מה שביקשתם לבדוק, בלשונכם'),'bl':'השורה התחתונה','lenses':'העדשות','lens_head':('עדשה','מצב','סיכונים'),'counts':'סיכונים: %d   סתירות: %d   צירופים: %d','dates':'מועדים קריטיים','dates_head':('מתי','מה קורה','סעיף','מה אם חולף'),'no_entity':'עוד לא בדקנו את הצד השני במרשמים הרשמיים.','ch1':'1. הסיכונים','ch1_head':('מספר','עדשה','הסיכון בשורה אחת','סעיף','חומרה','כיוון טיפול'),'ch2':'2. סתירות בין ההסכם לנספחים','ch2_head':('נושא','למה מסוכן','מה גובר','התיקון'),'no_defects':'לא נמצאו סתירות.','ch3':'3. צירופים ושרשראות','breaking':'התיקון ששובר את הצירוף: %s','no_combos':'לא נמצאו צירופים.','ch4':'4. הסיכונים הקריטיים בפירוט','no_crit':'לא דורג סיכון קריטי.','ch5':'5. מה לא נבדק ומה חסר','assume':'הנחה לאישור: %s','web':'מה נבדק ברשת ומתי','web_doc':'מקורות רגולטוריים ממחקר הפלייבוק ומהמסמכים (לא נפתחו ברשת בהרצה הזו)','open':'פתיחה','dd':'הבדיקה אינה תחליף לבדיקת נאותות פיננסית מלאה.','app':'נספח: ציטוטים מילוליים','app_head':('מספר','מסמך וסעיף','הנוסח המילולי'),'file':'%s - דוח סיכונים - %s.docx','agreement':'הסכם','mutual':'הדדי','money':'התמונה הכספית','money_head':('החשיפה','סכום או טווח','המקור','סיכונים'),'to':' עד ','upto':'עד ','unl':'בלתי מוגבל','no_amt':'אין בהסכם או מהלקוח סכום','src':{'contract':'מתוך ההסכם','client':'לפי מסירת הלקוח'},'per':{'שנתי':'לשנה','כולל':'בסך הכול','annual':'לשנה','total':'בסך הכול'},'dv':'שווי העסקה','no_dv':'לא ידוע','term':', לתקופה של %s','ins':'ביטוח','req':'ההסכם מחייב','held':'הכיסוי שבידינו','no_req':'אין בהסכם סכום ביטוח','no_held':'אין בתיק מסמך מהמבטח; ראו פרק 5','old_ins':'ראו פרק 5','no_money':'אין בהסכם או מהלקוח סכום לאף חשיפה.','money_lg':'סכומים רק מההסכם או ממסירת הלקוח; טווח רק כשאין סכום מדויק. אין סכימה בין החשיפות, ואין יחס מחושב.','treated':'טופל'},'en':{'lens':LENS_EN,'level':LEVEL_EN,'sign':SIGN_EN,'side':SIDE_EN,'status':STATUS_EN,'title':'Areo Workspace | Risks','glance':'At a glance','head':('Counterparty','The deal','Our side','Reviewed','Not provided','What you asked us to look at, in your words'),'bl':'Bottom line','lenses':'The lenses','lens_head':('Lens','Status','Risks'),'counts':'Risks: %d   Conflicts: %d   Combinations: %d','dates':'Critical dates','dates_head':('When','What happens','Clause','If it passes'),'no_entity':"We haven't checked the other side in the official registers yet.",'ch1':'1. Risks','ch1_head':('#','Lens','The risk in one line','Clause','Severity','Treatment direction'),'ch2':'2. Agreement vs annexes','ch2_head':('Topic','Why it is dangerous','What prevails','The fix'),'no_defects':'No conflicts were found.','ch3':'3. Combinations and chains','breaking':'The one fix that breaks it: %s','no_combos':'No combinations were found.','ch4':'4. Critical risks in detail','no_crit':'No risk was rated critical.','ch5':'5. Not checked and missing','assume':'Assumption to confirm: %s','web':'What was checked online, and when','web_doc':'Regulatory sources from the playbook research and the documents (not opened online in this run)','open':'Open','dd':'This check is not a substitute for full financial due diligence.','app':'Appendix: verbatim quotes','app_head':('#','Document and clause','Verbatim text'),'file':'%s - Risk report - %s.docx','agreement':'Agreement','mutual':'mutual','money':'The money picture','money_head':('Exposure','Amount or range','Source','Risks'),'to':' to ','upto':'up to ','unl':'unlimited','no_amt':'No amount in the agreement or from the client','src':{'contract':'from the agreement','client':'as provided by the client'},'per':{'שנתי':'per year','כולל':'in total','annual':'per year','total':'in total'},'dv':'Deal value','no_dv':'Not known','term':', term: %s','ins':'Insurance','req':'The agreement requires','held':'Our cover','no_req':'No insurance amount in the agreement','no_held':'No insurer document in the file; see chapter 5','old_ins':'See chapter 5','no_money':'No amount in the agreement or from the client for any exposure.','money_lg':'Amounts only from the agreement or from the client; a range only without an exact amount. Not added up, and not a ratio.','treated':'Treated in the document'}}
def report_lang(reg,lang=None,profile=None):
	B=profile or{};A=B.get('deliverable_language')
	if str(A or'').strip().lower()=='both':A=B.get('display_language')
	return rtl.lang_of(lang,A,(reg.get('meta')or{}).get('display_language'))
def load(path):
	A=path
	if not os.path.exists(A):print('המרשם אינו קיים: %s'%A);raise SystemExit(2)
	with io.open(A,encoding='utf-8')as B:return json.load(B)
def h(doc,text,size=14):A=rtl.add_paragraph(doc,text,bold=True,size=size);return A
def para(doc,text,size=10.5,bold=False):return rtl.add_paragraph(doc,str(text or''),bold=bold,size=size)
def table(doc,head,rows):
	A=doc.add_table(rows=1,cols=len(head));A.style='Table Grid'
	for(B,E)in enumerate(head):
		C=A.rows[0].cells[B];C.text=E
		for F in C.paragraphs[0].runs:F.bold=True
	for G in rows:
		H=A.add_row().cells
		for(B,D)in enumerate(G):H[B].text=str(D if D is not None else'')
	rtl.set_table_rtl(A);return A
def hyperlink(paragraph,url,text):A=paragraph;I=A.part;J=I.relate_to(url,RT.HYPERLINK,is_external=True);B=OxmlElement('w:hyperlink');B.set(qn('r:id'),J);C=OxmlElement('w:r');D=OxmlElement('w:rPr');F=OxmlElement('w:color');F.set(qn('w:val'),'0563C1');D.append(F);G=OxmlElement('w:u');G.set(qn('w:val'),'single');D.append(G);C.append(D);E=OxmlElement('w:t');E.text=text;E.set(qn('xml:space'),'preserve');C.append(E);B.append(C);A._p.append(B);H=A.add_run(' (%s)'%url);H.font.size=Pt(8);rtl.set_run_ltr(H);return A
def band(doc,text):
	for B in doc.sections:
		for A in(B.header,B.footer):D=A.paragraphs[0]if A.paragraphs else A.add_paragraph();C=D.add_run(text);C.font.size=Pt(8);C.font.color.rgb=RGBColor(154,52,18)
def quotes_index(reg):
	A=reg;B,C={},[]
	def D(a):
		if not a or not a.get('quote'):return
		A=a.get('document'),a.get('clause'),a.get('quote')
		if A not in B:B[A]=len(C)+1;C.append(a)
		return B[A]
	for E in A.get('risks')or[]:E['_q']=[D(A)for A in E.get('anchors')or[]]
	for F in A.get('document_defects')or[]:F['_q']=[D(A)for A in F.get('locations')or[]]
	for G in A.get('dangerous_combinations')or[]:G['_q']=[D(A)for A in G.get('anchors')or[]]
	return C
def refs(nums):return' '.join('[%d]'%A for A in nums or[]if A)
CUR_WORDS={'he':{'ILS':'ש"ח','USD':'דולר','EUR':'אירו','GBP':'ליש"ט','CHF':'פרנק שווייצרי','JPY':'ין יפני','SGD':'דולר סינגפורי','AED':'דירהם','CAD':'דולר קנדי','AUD':'דולר אוסטרלי','HKD':'דולר הונג קונגי','CNY':'יואן','INR':'רופי הודי','SEK':'כתר שוודי','NOK':'כתר נורווגי','DKK':'כתר דני','PLN':'זלוטי','TRY':'לירה טורקית','BRL':'ריאל ברזילאי','NZD':'דולר ניו זילנדי'},'en':{'ILS':'NIS'}}
CUR_ALIASES={'₪':'ILS','NIS':'ILS','ש"ח':'ILS','ש״ח':'ILS','שקל':'ILS','שקלים':'ILS','$':'USD','US$':'USD','דולר':'USD','דולרים':'USD','€':'EUR','אירו':'EUR','יורו':'EUR','£':'GBP','ליש"ט':'GBP','ליש״ט':'GBP','לירה שטרלינג':'GBP','לירות שטרלינג':'GBP','פרנק':'CHF','פרנקים':'CHF','FR.':'CHF','¥':'JPY','ין':'JPY','S$':'SGD','A$':'AUD','C$':'CAD','HK$':'HKD','דירהם':'AED'}
TO_COMPLETE={'he':'[להשלים]','en':'[to complete]'}
def currency_label(cur,lang):
	C=lang;C='en'if C=='en'else'he';A=str(cur or'').strip()
	if not A:return TO_COMPLETE[C]
	B=CUR_ALIASES.get(A)or CUR_ALIASES.get(A.upper())or A.upper();return CUR_WORDS[C].get(B)or(B if len(B)==3 and B.isalpha()and B.isascii()else A)
MONTHS_EN='January','February','March','April','May','June','July','August','September','October','November','December'
def fmt_date(v,lang):
	A=re.match('^(\\d{4})-(\\d{2})-(\\d{2})',str(v or''))
	if not A:return v or''
	B,C,D=int(A.group(1)),int(A.group(2)),int(A.group(3));return'%d %s %d'%(D,MONTHS_EN[C-1],B)if lang=='en'else'%d.%d.%d'%(D,C,B)
def money(a,lang):
	if not a or a.get('value')is None:return''
	A=float(a['value']);B=format(int(A),',')if A==int(A)else format(A,',.2f');return B+' '+currency_label(a.get('currency'),lang)
def money_rows(reg,L,lang):
	I=reg;C=lang;X,Y=I.get('summary')or{},I.get('meta')or{};D=X.get('money_picture')
	def B(a):return L['src'][a['source']]+(', '+a['source_ref']if a.get('source_ref')else'')if a and a.get('source')in L['src']else''
	def E(a):return[a['calc']]if a and a.get('calc')and a['calc']!='כלשון הסעיף'else[]
	T={A.get('id'):A.get('risk_no')for A in I.get('risks')or[]};O=[]
	if D and D.get('exposures'):
		for F in D['exposures']:
			J,G=F.get('amount')or{},F.get('range')or{};H,K=G.get('low')or{},G.get('high')or{}
			if J.get('value')is not None:P,Q,M=money(J,C),B(J),E(J)
			elif H.get('value')is not None or K.get('value')is not None or G.get('high_unlimited'):R=L['unl']if G.get('high_unlimited')else money(K,C);P=money(H,C)+(L['to']+R if R else'')if H.get('value')is not None else L['unl']if G.get('high_unlimited')else L['upto']+R;Q,M='; '.join(A for A in(B(H),B(K))if A),E(H)+E(K)
			else:P,Q,M=L['no_amt'],F.get('reason')or'',[]
			O.append((F.get('what')or'',P+(' (%s)'%'; '.join(M)if M else''),Q,', '.join(str(A)for A in sorted(T.get(A)for A in F.get('risk_ids')or[]if T.get(A)))))
	else:
		Z=[A for A in I.get('risks')or[]if((A.get('exposure')or{}).get('amount')or{}).get('value')is not None]
		for S in sorted(Z,key=lambda r:-float(r['exposure']['amount']['value'])):N=S['exposure']['amount'];O.append((S.get('name')or'',money(N,C)+(' (%s)'%'; '.join(E(N))if E(N)else''),B(N),str(S.get('risk_no')or'')))
	A=Y.get('deal_value')or{};a=money({'value':A['amount'],'currency':A.get('currency')},C)+(' '+L['per'][A.get('basis')]if L['per'].get(A.get('basis'))else'')+(L['term']%A['term']if A.get('term')else'')+(' (%s)'%B(A)if B(A)else'')if A.get('amount')is not None else L['no_dv']
	if D:
		U=D.get('insurance')or{}
		def V(a,empty):a=a or{};return money(a,C)+(' (%s)'%B(a)if B(a)else'')if a.get('value')is not None else a.get('text')or empty
		W='%s: %s · %s: %s'%(L['req'],V(U.get('required'),L['no_req']),L['held'],V(U.get('held'),L['no_held']))
	else:W=L['old_ins']
	return O,'%s: %s'%(L['dv'],a),'%s: %s'%(L['ins'],W)
def critical_text(r):
	A=r.get('critical_detail')
	if isinstance(A,dict):return' '.join(A for A in(A.get('what_happens'),A.get('why_not_protected'))if A)
	return A or r.get('description')
def build(reg,out,lang='he'):
	H=lang;F=reg;RS.derive_levels(F);B=T['en'if H=='en'else'he'];E,G=F.get('meta')or{},F.get('summary')or{};X=quotes_index(F);J=sorted(F.get('risks')or[],key=lambda r:(LEVEL_ORDER.get(r.get('severity_level'),9),r.get('risk_no')or 0));L=str(E.get('position')or'');Y='הדדי'in L or'mutual'in L.lower()or E.get('mutual_primary_role');A=Document();band(A,band_text_from_register(F,H));h(A,B['title'],16);h(A,E.get('scope_label')or'',13);h(A,B['glance']);Z=(E.get('counterparty')or{}).get('name')if isinstance(E.get('counterparty'),dict)else E.get('counterparty');a=Z,G.get('deal_one_line'),E.get('position'),', '.join(E.get('annexes_reviewed')or[])if isinstance(E.get('annexes_reviewed'),list)else E.get('annexes_reviewed'),', '.join(E.get('annexes_missing')or[])if isinstance(E.get('annexes_missing'),list)else E.get('annexes_missing'),'"%s"'%E['user_focus']if E.get('user_focus')else None
	for(b,M)in zip(B['head'],a):
		if M:para(A,'%s: %s'%(b,M))
	h(A,B['bl'],12)
	for c in G.get('bottom_line')or[]:para(A,c)
	if G.get('sign_as_is'):para(A,B['sign'].get(G['sign_as_is'],G['sign_as_is']),bold=True)
	h(A,B['money'],12);N,d,e=money_rows(F,B,H)
	if N:table(A,B['money_head'],N)
	else:para(A,B['no_money'])
	para(A,d);para(A,e);para(A,B['money_lg'],size=9);h(A,B['lenses'],12);table(A,B['lens_head'],[(B['lens'].get(A.get('lens'),A.get('lens')),B['status'].get(A.get('status'),A.get('status')),len(A.get('risk_ids')or[]))for A in F.get('coverage')or[]]);para(A,B['counts']%(len(J),len(F.get('document_defects')or[]),len(F.get('dangerous_combinations')or[])),bold=True)
	if G.get('key_dates'):h(A,B['dates'],12);table(A,B['dates_head'],[(fmt_date(A.get('date'),H)or A.get('window'),A.get('what'),A.get('clause'),A.get('consequence'))for A in G['key_dates'][:5]])
	O=F.get('entity_research')or{};para(A,O.get('note')or(B['no_entity']if O.get('status')!='done'else''));h(A,B['ch1']);P=[]
	for C in J:
		K=C.get('name')or''
		if Y and C.get('side'):K='%s: %s'%(B['side'].get(C['side'],C['side']),K)
		f=(C.get('anchors')or[{}])[0];Q=f.get('clause')or''
		if len(set(C.get('concession_refs')or[]))>1:Q='; '.join(dict.fromkeys(A.get('clause')for A in C.get('anchors')or[]if A.get('clause')))
		P.append((C.get('risk_no'),B['lens'].get(C.get('primary_lens'),C.get('primary_lens')),K,'%s %s'%(Q,refs(C.get('_q'))),B['level'].get(C.get('severity_level'),'')+(' · '+B['treated']if(C.get('residual')or{}).get('treated')else'')+(' · '+RS.STATE_LABEL_EN.get(C.get('exposure_state'),'')if H=='en'and C.get('exposure_state')in('proposed','agreed')else' · '+RS.STATE_LABEL.get(C.get('exposure_state'),'')if C.get('exposure_state')in('proposed','agreed')else''),C.get('treatment_direction')))
	table(A,B['ch1_head'],P);h(A,B['ch2']);R=F.get('document_defects')or[]
	if R:table(A,B['ch2_head'],[(A.get('topic')or A.get('title'),'%s %s'%(A.get('risk_created')or'',refs(A.get('_q'))),A.get('prevails')or A.get('what_prevails')or'',A.get('fix')or A.get('proposed_fix')or'')for A in R])
	else:para(A,B['no_defects'])
	h(A,B['ch3']);S=F.get('dangerous_combinations')or[]
	for I in S:
		para(A,'%s %s'%(I.get('why_together')or'',refs(I.get('_q'))))
		if I.get('breaking_fix'):para(A,B['breaking']%I['breaking_fix'],size=10)
	if not S:para(A,B['no_combos'])
	h(A,B['ch4']);U=[A for A in J if A.get('severity_level')=='critical']
	for C in U:para(A,'%s. %s'%(C.get('risk_no'),C.get('name')),bold=True);para(A,critical_text(C))
	if not U:para(A,B['no_crit'])
	h(A,B['ch5'])
	for D in G.get('not_checked')or[]:para(A,'%s: %s (%s)'%(D.get('item'),D.get('why'),D.get('who'))if isinstance(D,dict)else D)
	for D in G.get('assumptions')or[]:para(A,B['assume']%(D.get('text')or D.get('assumption')or''if isinstance(D,dict)else D))
	V=(F.get('research')or{}).get('sources_checked')or[]
	if V:
		h(A,B['web']if(F.get('research')or{}).get('mode')=='approved_sources'else B['web_doc'],12)
		for(g,D)in enumerate(V,1):
			W=para(A,'%d. %s: %s. '%(g,D.get('source'),D.get('taken')or D.get('subject')or''),size=10)
			if D.get('url'):hyperlink(W,D['url'],B['open'])
			W.add_run(' %s'%fmt_date(D.get('date'),H))
		para(A,B['dd'],size=9)
	h(A,B['app']);table(A,B['app_head'],[(B,'%s, %s'%(A.get('document'),A.get('clause')),A.get('quote'))for(B,A)in enumerate(X,1)]);rtl.enforce(A,H,author=E.get('prepared_for_counsel')or'');A.save(out)
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8');B=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B.add_argument('--data',required=True,help='risk-register.json, בתיקיית העסקה');B.add_argument('--date',help='DD.MM.YYYY; בלעדיו: היום');B.add_argument('--lang',choices=('he','en'),help='שפת ה-Word; בלעדיו: deliverable_language בפרופיל, ואחריו meta.display_language שבמרשם');B.add_argument('--profile',help='פרופיל-לקוח.json: שפת התוצר (deliverable_language)');A=B.parse_args(argv);D=load(A.data);H=load(A.profile)if A.profile else{};E=report_lang(D,A.lang,H);F=T[E];I=A.date or _dt.date.today().strftime('%d.%m.%Y');J=re.sub('[\\\\/:*?"<>|]','',re.sub(',\\s*\\d{2}\\.\\d{2}\\.\\d{4}$','',(D.get('meta')or{}).get('scope_label')or F['agreement']));C=paths.unique_path(os.path.join(os.path.dirname(os.path.abspath(A.data)),F['file']%(J,I)));paths.check_write_path(C);build(D,C,E);G=rtl.audit(C,E,run_date=_dt.date.today());print('נבנה: %s'%C)
	for K in G:print('  בדיקת כיווניות: %s'%K)
	return 3 if G else 0
if __name__=='__main__':sys.exit(main())
