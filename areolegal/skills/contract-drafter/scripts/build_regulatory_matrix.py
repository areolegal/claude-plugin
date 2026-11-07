#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,sys
from openpyxl import Workbook
from openpyxl.styles import Alignment,Border,Font,PatternFill,Side
from openpyxl.utils import get_column_letter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from research_sources import NORM_RANKS,NOT_FOUND,RANK_STATUS,check,display_date,normalise,scope_has,ApprovedSourcesMissing
from build_template_registry import guard_out
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
FONT='Arial'
HEAD_FILL=PatternFill('solid',fgColor='12314F')
STATUS_FILL={'מחייב':'E8EDF2','מנחה':'F4F4F4','בהליך':'FFF4E0'}
THIN=Side(style='thin',color='C9CFD6')
BORDER=Border(left=THIN,right=THIN,top=THIN,bottom=THIN)
WRAP=Alignment(horizontal='right',vertical='top',wrap_text=True,readingOrder=2)
WRAP_LTR=Alignment(horizontal='left',vertical='top',wrap_text=True,readingOrder=1)
LAW_SHEET='מטריצה רגולטורית'
MAND_SHEET='סעיפי חובה'
AGR_SHEET='הסכמים מייצגים'
TXT={'he':{'sheets':(LAW_SHEET,MAND_SHEET,AGR_SHEET),'law_head':['מס"ד','דרג','סוג המקור','שם המקור','גוף מפרסם','מעמד','תאריך פרסום מקורי','תאריך פרסום או תיקון אחרון','סעיפים רלוונטיים','תמצית הסעיפים','המשמעות להסכם','אופן ההתייחסות בהסכם','סוג השפעה','סעיף חובה','קישור','סטטוס אימות'],'mand_head':['מזהה','שם הסעיף','הדרישה','שורת מקור','סעיף בחיקוק','הצד החייב','נוסח מוצע בתמצית','סטטוס'],'ags_head':["מס'",'כותרת','מפרסם','סוג האתר','דין חל','כיוון','נימוק לכיוון','נושאים','מה ההסכם תורם','סעיפי חובה חסרים','תאריך פרסום','שימוש','קישור'],'yes':'כן','no':'לא','verified':'אומת','unverified':'טעון אימות','included':'כלול','removed':'הוסר לבקשת הלקוח','row':'שורה %s'},'en':{'sheets':('Regulatory matrix','Mandatory clauses','Representative agreements'),'law_head':['No.','Rank','Source type','Source','Publisher','Standing','Original publication date','Last publication or amendment','Relevant sections','Summary of sections','Meaning for the agreement','Treatment in the agreement','Type of effect','Mandatory clause','Link','Verification status'],'mand_head':['ID','Clause name','Requirement','Source row','Section in the law','Bound party','Proposed wording in brief','Status'],'ags_head':['No.','Title','Publisher','Site type','Governing law','Orientation','Orientation reason','Topics','What the agreement contributes','Missing mandatory clauses','Publication date','Use','Link'],'yes':'Yes','no':'No','verified':'Verified','unverified':'Needs verification','included':'Included','removed':'Removed by the client','row':'Row %s'}}
STATUS_EN={'מחייב':'Binding','מנחה':'Guidance','בהליך':'In process'}
SOURCE_TYPE_EN={'אתר משפטי':'Legal website','משרד עורכי דין':'Law firm','רגולטור':'Regulator','גוף ציבורי':'Public body','הליך תחרותי ציבורי':'Public competitive procedure','דיווח פומבי':'Public filing','אחר':'Other'}
RANKS_EN={1:'Primary legislation',2:'Secondary legislation',3:'Binding regulator instruction',4:'Regulator guidance',5:'Staff position or FAQ',6:'Source in process'}
B_ORIENT_HE={'לטובת הפוזיציה':'לטובת הצד שלכם','מאוזן':'מאוזן','נגד הפוזיציה':'נגד הצד שלכם'}
ORIENT_EN={'לטובת הפוזיציה':'Favours our position','מאוזן':'Balanced','נגד הפוזיציה':'Against our position'}
FLAGS_EN={'מותר כלשונו, בציון המקור':'Verbatim use allowed, with attribution','מבנה, נושאים ועמדות בלבד':'Structure, topics and positions only','נכתב לטובת המדינה כלקוח':'Written in favour of the state as customer','לעיון בלבד':'For reference only','חסר נימוק לכיוון':'Orientation reason missing'}
LTR=False
def ddate(v):A=display_date(v,'en'if LTR else'he');return'[not found]'if LTR and A==NOT_FOUND else A
def sheet(wb,title,header,widths):
	A=wb.create_sheet(title);A.sheet_view.rightToLeft=not LTR;A.append(header)
	for(C,D)in enumerate(widths,1):B=A.cell(row=1,column=C);B.font=Font(name=FONT,bold=True,color='FFFFFF',size=10);B.fill=HEAD_FILL;B.alignment=Alignment(horizontal='left'if LTR else'right',vertical='center',wrap_text=True,readingOrder=1 if LTR else 2);B.border=BORDER;A.column_dimensions[get_column_letter(C)].width=D
	A.freeze_panes='A2';return A
def put(ws,row,values,fill=None):
	for(B,C)in enumerate(values,1):
		A=ws.cell(row=row,column=B,value=C);A.font=Font(name=FONT,size=10);A.alignment=WRAP_LTR if LTR else WRAP;A.border=BORDER
		if fill:A.fill=PatternFill('solid',fgColor=fill)
def hyperlink(cell,target,text=None):B=target;A=cell;A.value=text if text is not None else B;A.hyperlink=B;A.font=Font(name=FONT,size=10,color='0B5CAD',underline='single')
def finish(ws,ncols,nrows):
	A=nrows
	if A:ws.auto_filter.ref='A1:%s%d'%(get_column_letter(ncols),A+1)
def main():
	K=argparse.ArgumentParser();K.add_argument('--research',required=True);K.add_argument('--out',required=True);K.add_argument('--lang',choices=('he','en'),help='שפת הקובץ; בלעדיו: deliverable_language בפרופיל, ואחרת עברית');K.add_argument('--profile',help='פרופיל-לקוח.json: שפת התוצר (deliverable_language)');K.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json). נתיב שנמסר ואינו קיים: מחקר רגולטורי נעצר בקוד 2');K.add_argument('--force',action='store_true',help='לדרוס קובץ פלט קיים');D=K.parse_args();guard_out(D.out,[D.research,D.profile,D.approved_sources],D.force);global LTR;N=json.load(io.open(D.profile,encoding='utf-8'))if D.profile else{};O=str(N.get('deliverable_language')or'').strip().lower()
	if O=='both':O=str(N.get('display_language')or'').strip().lower()
	Q=str(D.lang or O or'he').strip().lower();LTR=Q[:2]=='en'or Q in('english','אנגלית');E=TXT['en'if LTR else'he'];R,V,W=E['sheets'];H=normalise(json.load(io.open(D.research,encoding='utf-8')))
	try:S,X,Y=check(H,stage='brief',approved_sources=D.approved_sources,inc_country=N.get('incorporation_country'))
	except ApprovedSourcesMissing as Z:print('סירוב: %s'%Z);sys.exit(2)
	if S:
		print('קובץ ה-Excel לא נבנה:')
		for a in S:print('  חוסם: '+a)
		sys.exit(1)
	L=Workbook();L.remove(L.active);T={}
	if scope_has(H,'research'):
		J=E['law_head'];C=sheet(L,R,J,[6,6,16,32,20,9,12,14,16,36,36,40,12,9,34,14])
		for(I,A)in enumerate(H.get('law')or[]):F=I+2;P=A.get('rank');M=A.get('status')or RANK_STATUS.get(P,'');T[A.get('row',I+1)]=F;put(C,F,[A.get('row',I+1),P,A.get('source_kind')or(RANKS_EN if LTR else NORM_RANKS).get(P,''),A.get('instrument',''),A.get('publisher',''),STATUS_EN.get(M,M)if LTR else M,ddate(A.get('published_original')),ddate(A.get('published_last')),A.get('sections',''),A.get('sections_summary',''),A.get('meaning',''),A.get('contract_treatment',''),A.get('effect',''),E['yes']if A.get('mandatory')else E['no'],A.get('url',''),E['verified']if A.get('verified')else E['unverified']],STATUS_FILL.get(M));hyperlink(C.cell(row=F,column=4),A['url'],A.get('instrument',''));hyperlink(C.cell(row=F,column=15),A['url'])
		finish(C,len(J),len(H.get('law')or[]));J=E['mand_head'];C=sheet(L,V,J,[8,24,40,10,14,14,44,16])
		for(I,G)in enumerate(H.get('mandatory_clauses')or[]):
			F=I+2;put(C,F,[G.get('clause_id',''),G.get('title',''),G.get('requirement',''),G.get('source_row',''),G.get('source_section',''),G.get('bound_party',''),G.get('proposed_text',''),E['removed']if G.get('status')=='הוסר'else E['included']]);U=T.get(G.get('source_row'))
			if U:hyperlink(C.cell(row=F,column=4),"#'%s'!D%d"%(R,U),E['row']%G.get('source_row'))
		finish(C,len(J),len(H.get('mandatory_clauses')or[]))
	if scope_has(H,'agreements'):
		J=E['ags_head'];C=sheet(L,W,J,[6,30,20,14,12,14,36,30,34,16,12,22,34])
		for(I,B)in enumerate(H.get('agreements')or[]):F=I+2;put(C,F,[B.get('no',I+1),B.get('title',''),B.get('publisher',''),SOURCE_TYPE_EN.get(B.get('source_type'),B.get('source_type',''))if LTR else B.get('source_type',''),B.get('governing_law',''),ORIENT_EN.get(B.get('orientation'),B.get('orientation',''))if LTR else B_ORIENT_HE.get(B.get('orientation'),B.get('orientation','')),B.get('orientation_reason',''),', '.join(B.get('topics')or[]),B.get('contributes',''),', '.join(B.get('missing_mandatory')or[]),ddate(B.get('published')),', '.join(FLAGS_EN.get(A,A)if LTR else A for A in X['agreements'][I]),B.get('url','')]);hyperlink(C.cell(row=F,column=2),B['url'],B.get('title',''));hyperlink(C.cell(row=F,column=13),B['url'])
		finish(C,len(J),len(H.get('agreements')or[]))
	L.save(D.out);print('קובץ ה-Excel: %s'%D.out);print('גיליונות: %s'%' · '.join(L.sheetnames))
	for b in Y:print('  '+b)
if __name__=='__main__':main()
