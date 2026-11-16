#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime,io,json,os,sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import build_draft_docx as B
from research_sources import MANDATORY_ALLOWED_RANKS,NORM_RANKS,RECOMMENDED_RANKS,SCOPES,ApprovedSourcesMissing,check,conditional_mandatory,market_status,normalise,scope_has
import drivers_lib as DL
from build_template_registry import guard_out
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
HEAD_BG='E8EDF2'
TXT={'he':{'title':'סיכום המחקר לפני הניסוח: ','agreement':'הסכם','stamp':'טיוטה · הופק בתאריך %s · הפוזיציה: %s · היקף: %s','intro':'לא נמצאו בתיקייה טיוטות, הסכמים או פלייבוק מסוג זה, וביקשתם לנסח מבחוץ. הטיוטה נבנית ממקורות מהרשימה המאושרת בלבד, והיא תאמר זאת בבירור. להלן מה שנמצא.','law':'1. הדין החל: תמצית דרגים 1 עד 3','matrix':'הטבלה המלאה, כולל הנחיות, עמדות סגל ומקורות בהליך, בקובץ: %s','law_head':['דרג','מקור','סעיפים','המשמעות להסכם','סטטוס'],'verified':'אומת','unverified':'טעון אימות','mand':'2. סעיפי חובה','mand_head':['מזהה','סעיף','הדרישה','מקור','הצד החייב','חל כאשר'],'always':'תמיד','conditions':'שאלות על העסקה, מתנאי התחולה של המקורות (הסעיף נכלל רק בתשובה חיובית)','rec':'סעיפים מומלצים, מהנחיות ועמדות סגל','qa':"שאלה א': להשאיר את %d סעיפי החובה שנגזרו מהמחקר הרגולטורי, או להסיר חלק מהם? להשאיר את כולם · להסיר סעיפים",'ags':'%d. הסכמים מייצגים','ags_head':["מס'",'הסכם','מפרסם','כיוון ונימוק','סעיפי חובה חסרים','שימוש'],'qb':"שאלה ב': להשתמש ב-%d ההסכמים כבסיס, או להסיר חלק מהם? להשתמש בכולם · להסיר הסכמים",'gaps':'פערים ומקורות טעוני אימות','unv_line':'טעון אימות, ואינו בסיס לסעיף חובה: ','approve':'שאלה אחת לפני הניסוח'},'en':{'title':'Research summary before drafting: ','agreement':'Agreement','stamp':'Draft · Produced on %s · Position: %s · Scope: %s','intro':'No drafts, agreements or playbook of this type were found in the folder, and you asked to draft from outside sources. The draft is built only from sources on the approved list, and it will say so plainly. Below is what was found.','law':'1. Applicable law: summary of ranks 1 to 3','matrix':'The full table, including guidance, staff positions and sources in process, is in: %s','law_head':['Rank','Source','Sections','Meaning for the agreement','Status'],'verified':'Verified','unverified':'Needs verification','mand':'2. Mandatory clauses','mand_head':['ID','Clause','Requirement','Source','Bound party','Applies when'],'always':'Always','conditions':'Questions about the deal, from the conditions under which the sources apply (the clause is included only on a yes)','rec':'Recommended clauses, from guidance and staff positions','qa':'Question A: keep the %d mandatory clauses derived from the regulatory research, or remove some? Keep all · Remove clauses','ags':'%d. Representative agreements','ags_head':['No.','Agreement','Publisher','Orientation and reason','Missing mandatory clauses','Use'],'qb':'Question B: use the %d agreements as the basis, or remove some of them? Use all · Remove agreements','gaps':'Gaps and sources that need verification','unv_line':'Needs verification, and is not a basis for a mandatory clause: ','approve':'One question before drafting'}}
EN_TEXT=('מותר כלשונו, בציון המקור','Verbatim use allowed, with attribution'),('מבנה, נושאים ועמדות בלבד','Structure, topics and positions only'),('נכתב לטובת המדינה כלקוח','Written in favour of the state as customer'),('לעיון בלבד','For reference only'),('חסר נימוק לכיוון','Orientation reason missing'),('סעיפי חובה לא מוכרים: ','Unknown mandatory clauses: '),('שכבות שנבדקו: ','Layers checked: '),('המחקר מוגבל למאגר המקורות המאושרים','The research is limited to approved sources. A point with no approved source is marked: AREO did not find an approved source for this point.'),('נבחר איסוף הסכמים בלבד','Only collecting agreements was chosen, so the law sources in the file are not part of the output.'),('נמצאו ','Fewer relevant agreements were found than the target: '),('דין זר',"Law other than the agreement's governing law"),('תחום שיפוט לא צוין','Jurisdiction not stated'),('מקור לא מסווג: ','Unclassified source: make sure it is not a law firm website or a commercial repository')
def en_text(t):
	for(A,B)in EN_TEXT:
		if t.startswith(A):
			C=t[len(A):]
			if A in('המחקר מוגבל למאגר המקורות המאושרים','נבחר איסוף הסכמים בלבד','דין זר','תחום שיפוט לא צוין','מקור לא מסווג: '):return B
			if A=='נמצאו ':return B+C.split(' ',1)[0]
			return B+C
	return t
def grid(doc,header,rows,link_cols=()):
	D=header;A=doc.add_table(rows=1+len(rows),cols=len(D));A.alignment=WD_TABLE_ALIGNMENT.CENTER;B.table_borders(A)
	for(C,H)in enumerate(D):E=A.rows[0].cells[C];B.cell_text(E,H,True,9.5,B.NAVY);E._tc.get_or_add_tcPr().append(B._el('w:shd',val='clear',color='auto',fill=HEAD_BG))
	for(I,J)in enumerate(rows):
		for(C,F)in enumerate(J):
			G=A.rows[I+1].cells[C]
			if C in link_cols:K,L=F;B.cell_link(G,L,K)
			else:B.cell_text(G,F,False,9.5)
	B.para(doc,after=6);return A
def main():
	F=argparse.ArgumentParser();F.add_argument('--research',required=True);F.add_argument('--out',required=True);F.add_argument('--matrix',help='שם קובץ ה-Excel, להפניה במסמך');F.add_argument('--lang',choices=('he','en'),help='שפת המסמך; בלעדיו: deliverable_language בפרופיל, ואחרת עברית');F.add_argument('--profile',help='פרופיל-לקוח.json: שפת התוצר (deliverable_language)');F.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json). נתיב שנמסר ואינו קיים: מחקר רגולטורי נעצר בקוד 2');F.add_argument('--force',action='store_true',help='לדרוס קובץ פלט קיים');E=F.parse_args();guard_out(E.out,[E.research,E.profile,E.matrix,E.approved_sources],E.force);A=normalise(json.load(io.open(E.research,encoding='utf-8')));L=json.load(io.open(E.profile,encoding='utf-8'))if E.profile else{}
	try:M,X,N=check(A,stage='brief',approved_sources=E.approved_sources,inc_country=L.get('incorporation_country'))
	except ApprovedSourcesMissing as Y:print('סירוב: %s'%Y);sys.exit(2)
	if M:
		print('המחקר אינו מוכן:')
		for Z in M:print('  חוסם: '+Z)
		sys.exit(1)
	B.RTL=not B.is_en(E.lang or B.profile_lang(L)or'he');D=TXT['he'if B.RTL else'en'];O=NORM_RANKS if B.RTL else B.NORM_RANKS_EN;a=(SCOPES if B.RTL else B.SCOPES_EN)[A['scope']];del B.GAPS[:];C=Document();B.base(C);b=datetime.date.today().isoformat();B.run(B.para(C,after=2),D['title']+B.s(A.get('agreement_type')or D['agreement']),17,True,B.NAVY);B.run(B.para(C,after=4),D['stamp']%(B.produced_on({'generated_at':b}),B.s(A.get('company_role')),a),9.5,False,B.INK_SOFT);B.para(C,D['intro'],10.5,False,B.INK,after=10);I=[]
	if scope_has(A,'research'):
		J=A.get('law')or[];c=[A for A in J if A.get('rank')in MANDATORY_ALLOWED_RANKS];B.h1(C,D['law'])
		if E.matrix:B.para(C,D['matrix']%os.path.basename(str(E.matrix).replace('\\','/')),10,False,B.INK_SOFT,after=6)
		grid(C,D['law_head'],[[O.get(A.get('rank'),''),(B.s(A.get('instrument')),A.get('url')),B.s(A.get('sections')),B.s(A.get('meaning')),D['verified']if A.get('verified')else D['unverified']]for A in c],link_cols=(1,));P=A.get('mandatory_clauses')or[];d=conditional_mandatory(A);B.h1(C,D['mand']);Q={A.get('row',B+1):A for(B,A)in enumerate(J)};grid(C,D['mand_head'],[[B.s(A.get('clause_id')),B.s(A.get('title')),B.s(A.get('requirement')),('%s, %s'%(B.s(Q.get(A.get('source_row'),{}).get('instrument')),B.s(A.get('source_section'))),Q.get(A.get('source_row'),{}).get('url')),B.s(A.get('bound_party')),'; '.join(d.get(A.get('clause_id'))or[])or D['always']]for A in P],link_cols=(3,));R=DL.research_drivers(A,'he'if B.RTL else'en')[0]
		if R:
			B.h1(C,D['conditions'])
			for e in R:B.para(C,e['question'],10.5,False,B.INK,after=3,indent=.5)
		S=[A for A in J if A.get('rank')in RECOMMENDED_RANKS]
		if S:
			B.h1(C,D['rec'])
			for G in S:H=B.para(C,after=3,indent=.5);B.rich(H,'%s: %s '%(O[G['rank']],B.s(G.get('contract_treatment'))),10.5);B.link(H,G.get('url'),B.s(G.get('instrument')),10)
		I.append(D['qa']%len(P))
	if scope_has(A,'agreements'):
		T=A.get('agreements')or[];B.h1(C,D['ags']%(3 if scope_has(A,'research')else 1));grid(C,D['ags_head'],[[str(A.get('no',C+1)),(B.s(A.get('title')),A.get('url')),B.s(A.get('publisher')),'%s: %s'%(B.ORIENT_HE.get(A.get('orientation'),B.s(A.get('orientation')))if B.RTL else B.ORIENT_EN.get(A.get('orientation'),B.s(A.get('orientation'))),B.s(A.get('orientation_reason'))),', '.join(A.get('missing_mandatory')or[])or'-',', '.join(A if B.RTL else en_text(A)for A in X['agreements'][C])]for(C,A)in enumerate(T)],link_cols=(1,));I.append(D['qb']%len(T));K=market_status(A,'he'if B.RTL else'en')
		if not K['market_based']:I.append('%s %s'%(K['line'],' · '.join(K['options'])))
	U=[A for A in N];V=[A for A in A.get('law')or[]if not A.get('verified')]if scope_has(A,'research')else[]
	if U or V:
		B.h1(C,D['gaps'])
		for W in U:B.rich(B.para(C,after=3,indent=.5),W if B.RTL else en_text(W),10.5)
		for G in V:H=B.para(C,after=3,indent=.5);B.run(H,D['unv_line'],10.5,True);B.link(H,G.get('url'),B.s(G.get('instrument')),10.5)
	B.h1(C,D['approve'])
	for f in I:B.para(C,f,11,True,B.INK,before=4,after=4)
	if not B.RTL:B.mixed_direction(C)
	C.save(E.out);print('סיכום המחקר: %s'%E.out);print('היקף: %s · מקורות דין: %d · סעיפי חובה: %d · הסכמים: %d'%(SCOPES[A['scope']],len(A.get('law')or[])if scope_has(A,'research')else 0,len(A.get('mandatory_clauses')or[])if scope_has(A,'research')else 0,len(A.get('agreements')or[])if scope_has(A,'agreements')else 0))
	for g in N:print('  '+g)
if __name__=='__main__':main()
