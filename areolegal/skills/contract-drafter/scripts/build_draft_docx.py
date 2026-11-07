#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib
from client_text_gate import HEB_CH,client_text_problems,english_parties
ensure_lib()
try:from common.voice_check import check_text as _voice_check
except Exception:_voice_check=None
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm,Pt,RGBColor
INK='16191F'
INK_SOFT='5B6472'
LINE='C9CFD6'
NAVY='12314F'
GAP_BG='FFF2A8'
FONT_HE='David'
FONT_LATIN='Calibri'
FONT=FONT_HE
RTL=True
TXT={'he':{'draft':'טיוטה','stamp':'טיוטה · הופק בתאריך %s','fill':'[להשלים]','defined':' (להלן: "%s")','part1':'מצד אחד;','part2':'מצד שני;','whereas':'הואיל ו','now':'לפיכך הוסכם, הותנה והוצהר בין הצדדים כדלקמן:','definitions':'הגדרות','case_law':' [להשלמה]','annex':'נספח','defs_lead':'בהסכם זה יהיו למונחים הבאים הפירושים שלצידם:','defs_lead_recitals':'בהסכם זה, לרבות במבוא לו, יהיו למונחים הבאים הפירושים שלצידם:','witness':'ולראיה באו הצדדים על החתום:','by':'על ידי: ','not_found':'[לא אותר]','mand':'סעיף שהחוק מחייב: %s','sources':'המקורות שהטיוטה נשענת עליהם','internal':'פנימי. לא נשלח לצד השני.','law':'הדין החל','law_head':['דרג','מקור','סעיפים','סטטוס'],'verified':'אומת','unverified':'טעון אימות','ags':'הסכמים מייצגים שאושרו','ags_head':['הסכם','מפרסם','כיוון'],'page':' · עמוד ','cover':'דף ליווי: ','cover_stamp':'טיוטה · הופק בתאריך %s','trace':'מטריצת עקיבות','trace_head':['סעיף','נושא','מקור','סעיף חובה','עמדת פתיחה'],'own':'ניסוח עצמאי','yes':'כן','no':'לא','removed':'סעיפי חובה שהוסרו לבקשתכם','removed_line':'%s: %s. החשיפה: %s','gaps':'פערים ומגבלות','no_research':'לא בוצע מחקר רגולטורי: נבחר איסוף הסכמים בלבד. הטיוטה אינה נשענת על מיפוי של הדין החל.','research_limits':'המחקר מוגבל למאגר המקורות המאושרים של Areo (רק האתרים והנתיבים שרשומים בו לכל מדינה). הנחיות שלא פורסמו במקורות האלה, או שלא ניתן היה לשלוף אותן, אינן בו.','unverified_line':'טעון אימות: ','case_law_list':'AREO לא מצאה מקור מורשה לנקודה זו. הצעד הבא: להעלות הסכם דומה כמקור, או להשאיר את הנקודה כפי שהיא. סעיפים ','run_risk':'להריץ על הטיוטה הערכת סיכונים לפני שהיא יוצאת?','cover_stamp_plain':'טיוטה · הופק בתאריך %s','src_playbook':'פלייבוק','src_third_party':'פלייבוק ונוסחים של צד שלישי','tp_notice':'הנייר אינו של החברה. המבנה וסדר הסעיפים נלקחו מנוסחים של צד שלישי שעומד באותו צד בהסכם, והעמדה בכל סעיף נלקחה מהפלייבוק. הנוסח נכתב מחדש ואינו מועתק מהנוסחים.','matrix':'מטריצת המקורות','matrix_head':['סעיף','נושא','פלייבוק','נוסחים','עובדות העסקה'],'no_pb':'אין עמדה בפלייבוק','sources_used':'המקורות','pb_line':'פלייבוק: %s','doc_line':'%s. %s','facts':'עובדות העסקה','to_fill':'מה נותר להשלים','loc_meta':'פרטי המסמך והצדדים','loc_recitals':'מבוא','loc_def':'הגדרת "%s"','loc_clause':'סעיף %s','loc_sign':'בלוק החתימות','legal_review':'נקודות בלי מקור מורשה','conditional':'סעיפים מותנים','conditional_line':'סעיף %s: הסעיף נכלל כי %s לא נשלל; אשרו או מחקו.','pb_gaps':'נושאים שאין עליהם עדיין עמדה בפלייבוק','pb_gap_line':'%s (%s)','pb_gaps_answer':'התשובה לשאלת ההשלמה: %s','decisions':'מה הוחלט בטיוטה','notes':'הערות','choices':'מה נבחר ולמה','pb_pending':'טיוטת מדיניות','from_pb':'כן','choice_default':'ברירת המחדל, הנוסח השכיח בהסכמים שלכם','to_fill_count':'%s: %d פרטים פתוחים','concern':'החשש העיקרי שלכם בעסקה','concern_answer':'כלשונכם: %s','concern_clauses':'המענה בטיוטה: סעיפים %s','options':'מוצע כאפשרות, לא נכלל','option_line':'%s: %s','key_dates':'המועדים שיהיו חשובים בהמשך','key_date_clause':' (סעיף %s)','ld_review':'פיצוי מוסכם (סעיף %s): AREO לא מצאה מקור מורשה לנקודה זו (אכיפות הפיצוי המוסכם לפי %s). הצעד הבא: לחבר מקור מהרשימה המאושרת, או להשאיר את הסעיף כפי שהוא.','law_unset':'הדין החל, שטרם נקבע','lead':'הטיוטה מוכנה.','lead_clear':'אין בה פרטים פתוחים.','lead_open':'נשארו %d פרטים להשלים, כ-%d דקות.','next_fill':'הצעד הבא: להשלים את הפרטים המסומנים ברקע צהוב.','next_review':'הצעד הבא: להחליט על סעיפים %s: להעלות מקור, או להשאיר אותם כפי שהם.','next_send':'הצעד הבא: לשלוח לצד השני, או להריץ קודם בדיקת סיכונים.','notice_title':'מאיפה באה הטיוטה','internal_note':'פנימי. לא נשלח לצד השני.'},'en':{'draft':'Draft','stamp':'Draft · Produced on %s','fill':'[to complete]','defined':' (the "%s")','part1':'of the first part;','part2':'of the second part;','whereas':'WHEREAS ','now':'NOW, THEREFORE, the parties agree as follows:','definitions':'Definitions','case_law':' [to be completed]','annex':'Annex','defs_lead':'In this Agreement, the following terms have the meanings set out below:','defs_lead_recitals':'In this Agreement, including the recitals, the following terms have the meanings set out below:','witness':'IN WITNESS WHEREOF, the parties have signed:','by':'By: ','not_found':'[not found]','mand':'Clause required by law: %s','sources':'Sources the draft relies on','internal':'Internal. Not sent to the other side.','law':'Applicable law','law_head':['Rank','Source','Sections','Status'],'verified':'Verified','unverified':'Needs verification','ags':'Approved representative agreements','ags_head':['Agreement','Publisher','Orientation'],'page':' · Page ','cover':'Cover note: ','cover_stamp':'Draft · Produced on %s','trace':'Traceability matrix','trace_head':['Clause','Topic','Source','Mandatory','Opening position'],'own':'Independent drafting','yes':'Yes','no':'No','removed':'Mandatory clauses removed at your request','removed_line':'%s: %s. Exposure: %s','gaps':'Gaps and limits','no_research':'No regulatory research was done: only collecting agreements was chosen. The draft does not rest on a mapping of the applicable law.','research_limits':'The research is limited to the approved-sources repository (only the sites and paths listed for each country). Guidance not published in these sources, or not retrievable, is not in it.','unverified_line':'Needs verification: ','case_law_list':'AREO did not find an approved source for this point. Next step: upload a similar agreement as a source, or keep the point as it is. Clauses ','run_risk':'Run a risk assessment on the draft before it goes out?','cover_stamp_plain':'Draft · Produced on %s','src_playbook':'playbook','src_third_party':'playbook and third-party forms','tp_notice':"This is not the company's paper. The structure and the order of the clauses come from third-party forms in the same position, and the position in each clause comes from the playbook. The wording was written anew and is not copied from the forms.",'matrix':'Source matrix','matrix_head':['Clause','Topic','Playbook','Forms','Deal facts'],'no_pb':'No playbook position','sources_used':'Sources','pb_line':'Playbook: %s','doc_line':'%s. %s','facts':'Deal facts','to_fill':'What is still open','loc_meta':'Document details and parties','loc_recitals':'Recitals','loc_def':'Definition of "%s"','loc_clause':'Clause %s','loc_sign':'Signature block','legal_review':'Points without an approved source','conditional':'Conditional clauses: for your confirmation','conditional_line':'Clause %s: included because %s was not ruled out; confirm or delete.','pb_gaps':'Topics with no settled playbook position yet','pb_gap_line':'%s (%s)','pb_gaps_answer':'Answer to the completion question: %s','decisions':'Decisions','notes':'Notes','choices':'What was chosen and why','pb_pending':'Draft policy','from_pb':'Yes','choice_default':'the default, the most common wording in your agreements','to_fill_count':'%s: %d open details','concern':'Your main concern in this deal','concern_answer':'In your words: %s','concern_clauses':'Where the draft answers it: clauses %s','options':'Offered as an option, not included','option_line':'%s: %s','key_dates':'Dates that will matter later','key_date_clause':' (clause %s)','ld_review':'Liquidated damages (clause %s): AREO did not find an approved source for this point (enforceability under %s). Next step: connect a source from the approved list, or keep the clause as it is.','law_unset':'the governing law, not yet set','lead':'Your draft is ready.','lead_clear':'Nothing is left open.','lead_open':'%d details are left to complete, about %d minutes.','next_fill':'Next step: complete the details marked in yellow.','next_review':'Next step: decide on clauses %s: upload a source, or keep them as they are.','next_send':'Next step: send it to the other side, or run a risk check first.','notice_title':'Where this draft came from','internal_note':'Internal. Not sent to the other side.'}}
NORM_RANKS_EN={1:'Primary legislation',2:'Secondary legislation',3:'Binding regulator instruction',4:'Regulator guidance',5:'Staff position or FAQ',6:'Source in process'}
SCOPES_EN={'agreements':'collecting representative agreements','research':'layered regulatory research','both':'collecting agreements and regulatory research'}
ORIENT_EN={'לטובת הפוזיציה':'Favours our position','מאוזן':'Balanced','נגד הפוזיציה':'Against our position'}
ORIENT_HE={'לטובת הפוזיציה':'לטובת הצד שלכם','מאוזן':'מאוזן','נגד הפוזיציה':'נגד הצד שלכם'}
def tr(key):return TXT['he'if RTL else'en'][key]
def is_en(lang):A=str(lang or'').strip().lower();return A[:2]=='en'or A in('english','אנגלית')
def profile_lang(prof):
	A=prof;A=A or{};B=str(A.get('deliverable_language')or'').strip().lower()
	if B=='both':B=str(A.get('display_language')or'').strip().lower()
	return B or None
PPR_ORDER=['pStyle','keepNext','keepLines','pageBreakBefore','numPr','pBdr','shd','tabs','bidi','spacing','ind','contextualSpacing','jc','outlineLvl','rPr']
GAP_RX=re.compile('(\\[(?:להשלים|to complete)[^\\[\\]]*\\]|\\[[^\\[\\]]{0,80}\\])',re.I)
def _el(tag,**B):
	A=OxmlElement(tag)
	for(C,D)in B.items():A.set(qn('w:'+C),D)
	return A
def _local(tag):return tag.split('}')[-1]
TBLPR_ORDER=['tblStyle','tblpPr','tblOverlap','bidiVisual','tblStyleRowBandSize','tblStyleColBandSize','tblW','jc','tblCellSpacing','tblInd','tblBorders','shd','tblLayout','tblCellMar','tblLook','tblCaption','tblDescription','tblPrChange']
SECTPR_ORDER=['footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange']
def put_ordered(parent,el,order):
	C=order;B=parent;A=el;D=_local(A.tag);E=B.find(qn('w:'+D))
	if E is not None:B.remove(E)
	H=C.index(D)if D in C else 99
	for F in B:
		G=_local(F.tag)
		if(C.index(G)if G in C else 99)>H:F.addprevious(A);return A
	B.append(A);return A
def ppr_put(p,el):
	A=el;B=p._p.get_or_add_pPr();C=_local(A.tag);D=B.find(qn('w:'+C))
	if D is not None:B.remove(D)
	G=PPR_ORDER.index(C)if C in PPR_ORDER else 99
	for E in B:
		F=_local(E.tag)
		if(PPR_ORDER.index(F)if F in PPR_ORDER else 99)>G:E.addprevious(A);return A
	B.append(A);return A
def dir_p(p):
	if RTL:ppr_put(p,_el('w:bidi'))
def mixed_direction(doc):
	E=[doc.element.body]
	for F in doc.sections:
		for G in(F.header,F.footer):
			if not G.is_linked_to_previous:E.append(G._element)
	H=0
	for O in E:
		for B in O.iter(qn('w:p')):
			I=''.join(A.text or''for A in B.iter(qn('w:t')));J=len(HEB_RX.findall(I))
			if not J:continue
			if J>=len(re.findall('[A-Za-z]',I)):
				A=B.find(qn('w:pPr'))
				if A is None:A=B.makeelement(qn('w:pPr'),{});B.insert(0,A)
				K=A.find(qn('w:bidi'))
				if K is not None:A.remove(K)
				P=PPR_ORDER.index('bidi')
				for L in A:
					M=_local(L.tag)
					if(PPR_ORDER.index(M)if M in PPR_ORDER else 99)>P:L.addprevious(_el('w:bidi'));break
				else:A.append(_el('w:bidi'))
				for N in A.findall(qn('w:jc')):
					if N.get(qn('w:val'))in('left','right'):A.remove(N)
				H+=1
			for C in B.iter(qn('w:r')):
				Q=''.join(A.text or''for A in C.iter(qn('w:t')))
				if HEB_RX.search(Q):
					D=C.find(qn('w:rPr'))
					if D is None:D=C.makeelement(qn('w:rPr'),{});C.insert(0,D)
					put_ordered(D,_el('w:rtl'),RPR_ORDER)
	return H
RPR_ORDER=['rStyle','rFonts','b','bCs','i','iCs','caps','smallCaps','strike','dstrike','outline','shadow','emboss','imprint','noProof','snapToGrid','vanish','webHidden','color','spacing','w','kern','position','sz','szCs','highlight','u','effect','bdr','shd','fitText','vertAlign','rtl','cs','em','lang','eastAsianLayout']
HEB_RX=re.compile('[\u0590-\u05ff]')
def latin_font():return FONT_HE if RTL else FONT_LATIN
def set_fonts(rpr,text='',size=None,bold=False,italic=False):
	B=rpr;A=_el('w:rFonts');A.set(qn('w:ascii'),latin_font());A.set(qn('w:hAnsi'),latin_font());A.set(qn('w:cs'),FONT_HE)
	if RTL or HEB_RX.search(text or''):A.set(qn('w:hint'),'cs')
	put_ordered(B,A,RPR_ORDER)
	if bold:put_ordered(B,_el('w:bCs'),RPR_ORDER)
	if italic:put_ordered(B,_el('w:iCs'),RPR_ORDER)
	if size:put_ordered(B,_el('w:szCs',val=str(int(round(size*2)))),RPR_ORDER)
def run(p,text,size=11,bold=False,color=INK,italic=False,fill=None,underline=False):
	C=italic;A=p.add_run(text);A.font.size=Pt(size);A.bold=bold;A.italic=C;A.underline=underline;A.font.color.rgb=RGBColor.from_string(color);B=A._r.get_or_add_rPr();set_fonts(B,text,size,bold,C)
	if fill:put_ordered(B,_el('w:shd',val='clear',color='auto',fill=fill),RPR_ORDER)
	if RTL:put_ordered(B,_el('w:rtl'),RPR_ORDER)
	return A
GAPS=[]
LINK='0B5CAD'
def link(p,url,text=None,size=10,bold=False):
	B=url;from docx.opc.constants import RELATIONSHIP_TYPE as F;B=(B or'').strip()
	if not B:return
	G=p.part.relate_to(B,F.HYPERLINK,is_external=True);C=_el('w:hyperlink');C.set(qn('r:id'),G);D=_el('w:r');A=_el('w:rPr')
	if bold:A.append(_el('w:b'))
	A.append(_el('w:color',val=LINK));A.append(_el('w:sz',val=str(int(size*2))));A.append(_el('w:u',val='single'));set_fonts(A,text or B,size,bold)
	if RTL:put_ordered(A,_el('w:rtl'),RPR_ORDER)
	D.append(A);E=_el('w:t');E.text=text or B;E.set('{http://www.w3.org/XML/1998/namespace}space','preserve');D.append(E);C.append(D);p._p.append(C);return C
def cell_link(cell,url,text=None,size=9.5):
	B=url;A=cell.paragraphs[0]
	for C in list(A._p.findall(qn('w:r'))):A._p.remove(C)
	dir_p(A);A.paragraph_format.space_before=Pt(3);A.paragraph_format.space_after=Pt(3)
	if B:link(A,B,text or B,size)
	else:run(A,text or tr('not_found'),size,False,INK_SOFT)
def rich(p,text,size=11,bold=False,color=INK):
	for A in GAP_RX.split(s(text)):
		if not A:continue
		if GAP_RX.fullmatch(A):GAPS.append(A);run(p,A,size,True,INK,fill=GAP_BG)
		else:run(p,A,size,bold,color)
	return p
def para(doc,text='',size=11,bold=False,color=INK,before=0,after=5,line=1.2,container=None,align=None,indent=.0,italic=False):
	D=align;C=indent;B=(container or doc).add_paragraph();dir_p(B);A=B.paragraph_format;A.space_before=Pt(before);A.space_after=Pt(after);A.line_spacing=line;A.alignment=D if D is not None else WD_ALIGN_PARAGRAPH.JUSTIFY
	if C:A.left_indent=Cm(C)if not RTL else None;A.right_indent=Cm(C)if RTL else None
	if text:run(B,text,size,bold,color,italic)
	return B
def table_borders(tbl,color=LINE,visible=True):
	A=tbl._tbl.tblPr;B=_el('w:tblBorders')
	for C in('top','left','bottom','right','insideH','insideV'):B.append(_el('w:'+C,val='single'if visible else'none',sz='4',space='0',color=color))
	put_ordered(A,B,TBLPR_ORDER)
	if RTL:put_ordered(A,_el('w:bidiVisual'),TBLPR_ORDER)
def cell_text(cell,text,bold=False,size=10.5,color=INK,align=None):
	C=align;B=color;A=cell.paragraphs[0]
	for D in list(A._p.findall(qn('w:r'))):A._p.remove(D)
	dir_p(A);A.paragraph_format.space_before=Pt(3);A.paragraph_format.space_after=Pt(3)
	if C is not None:A.alignment=C
	E=str(text).split('\n')if text else['']
	for(F,G)in enumerate(E):
		if F:run(A,'',size,bold,B)._r.append(_el('w:br'))
		rich(A,G,size,bold,B)
MONTHS_EN='January','February','March','April','May','June','July','August','September','October','November','December'
DMY_RX=re.compile('(?<![\\d.])(\\d{1,2})[./](\\d{1,2})[./](\\d{4})(?![\\d.]?\\d)')
ISO_RX=re.compile('(?<![\\d-])(\\d{4})-(\\d{2})-(\\d{2})(?![\\d-])')
def local_dates(t,en=None):
	A=en;A=not RTL if A is None else A
	def B(d,m,y):
		d,m=int(d),int(m)
		if not(1<=d<=31 and 1<=m<=12):return
		return'%d %s %s'%(d,MONTHS_EN[m-1],y)if A else'%d.%d.%s'%(d,m,y)
	t=ISO_RX.sub(lambda x:B(x.group(3),x.group(2),x.group(1))or x.group(0),t)
	if A:t=DMY_RX.sub(lambda x:B(x.group(1),x.group(2),x.group(3))or x.group(0),t)
	return t
def s(v,limit=None):B=limit;A=' '.join(str(v).split())if v not in(None,'')else'';A=A.replace('—',', ').replace('–','-').replace(' ,',',');A=local_dates(A);return A[:B]if B else A
def produced_on(meta):
	from research_sources import display_date as B;A=s(meta.get('generated_at'))[:10]
	if not(len(A)==10 and A[4]=='-'):A=datetime.date.today().isoformat()
	return B(A,'he'if RTL else'en')
def txt(node,*B):
	for A in B:
		if node.get(A):return s(node[A])
	return''
def base(doc):
	global FONT;FONT=latin_font();C=doc.styles['Normal'];C.font.size=Pt(11);B=C.element.get_or_add_rPr();set_fonts(B,'',11);put_ordered(B,_el('w:lang',val='en-US',bidi='he-IL'),RPR_ORDER)
	if RTL:put_ordered(B,_el('w:rtl'),RPR_ORDER)
	for A in doc.sections:
		A.left_margin=A.right_margin=Cm(2.4);A.top_margin=Cm(2.2);A.bottom_margin=Cm(2.)
		if RTL:put_ordered(A._sectPr,_el('w:bidi'),SECTPR_ORDER);put_ordered(A._sectPr,_el('w:rtlGutter'),SECTPR_ORDER)
def title_block(doc,m):
	B=doc;G=txt(m,'title','doc_type')or tr('draft');A=para(B,before=0,after=4,align=WD_ALIGN_PARAGRAPH.CENTER);run(A,G,19,True,NAVY);C=' · '.join([A for A in(txt(m,'doc_type')if txt(m,'title')else'',txt(m,'place_date'))if A])
	if C:A=para(B,before=0,after=2,align=WD_ALIGN_PARAGRAPH.CENTER);run(A,C,10.5,False,INK_SOFT)
	D=tr('stamp')%produced_on(m);E=txt(m,'classification')
	if E:D+=' · '+E
	A=para(B,before=0,after=14,align=WD_ALIGN_PARAGRAPH.CENTER);run(A,D,9.5,False,INK_SOFT);F=para(B,before=0,after=14);I=F._p.get_or_add_pPr();H=ppr_put(F,_el('w:pBdr'));H.append(_el('w:top',val='single',sz='8',space='6',color=LINE))
def parties(doc,m):
	B=doc;C=m.get('parties')or[]
	if not C:return
	for(H,A)in enumerate(C):
		D=para(B,before=2,after=2);I=txt(A,'name')or tr('fill');E=I
		for F in(txt(A,'reg'),txt(A,'address')):
			if F:E+=', '+F
		rich(D,E,11,False);G=txt(A,'defined_as')or txt(A,'role')
		if G:run(D,tr('defined')%G,11,True)
		if H<len(C)-1:para(B,tr('part1'),10,False,INK_SOFT,after=6,align=WD_ALIGN_PARAGRAPH.LEFT)
	para(B,tr('part2'),10,False,INK_SOFT,after=12,align=WD_ALIGN_PARAGRAPH.LEFT)
def recitals(doc,rs):
	if not rs:return
	for C in rs:
		A=s(C);B=para(doc,before=0,after=5,indent=.6)
		if RTL and not A.startswith('הואיל'):run(B,tr('whereas'),11,True)
		elif not RTL and not A.upper().startswith('WHEREAS'):run(B,tr('whereas'),11,True)
		rich(B,A,11)
	para(doc,tr('now'),11,True,INK,before=8,after=12)
def definitions(doc,defs,has_recitals=False):
	A=doc
	if not defs:return
	h1(A,tr('definitions'));para(A,tr('defs_lead_recitals')if has_recitals else tr('defs_lead'),11,False,INK,before=0,after=4)
	for C in defs:B=para(A,before=2,after=4,indent=.6);run(B,'"%s" '%txt(C,'term'),11,True);run(B,'- ',11,False,INK_SOFT);rich(B,txt(C,'text','definition'),11)
def h1(doc,text,num=''):
	A=para(doc,before=16,after=6,align=WD_ALIGN_PARAGRAPH.JUSTIFY)
	if num:run(A,'%s. '%num,13,True,NAVY)
	run(A,s(text),13,True,NAVY);return A
def num_label(num):A=s(num).rstrip('.');return A+'.'if A and A[-1].isalnum()else A
def needs_review(c):return bool(c.get('needs_legal_review')or c.get('needs_case_law'))
def clause(doc,c,depth=0):
	F=depth;C=doc;D=num_label(c.get('number'));E=txt(c,'heading','title');A=txt(c,'text','body')
	if needs_review(c)and A:A+=tr('case_law')
	if F==0:
		if E:
			h1(C,E,D.rstrip('.'))
			if A:rich(para(C,before=0,after=5,indent=.6),A,11)
		else:
			B=para(C,before=8,after=5)
			if D:run(B,'%s '%D,11,True)
			rich(B,A,11)
	else:
		B=para(C,before=0,after=4,indent=.6+.6*F)
		if D:run(B,'%s '%D,11,True)
		if E:run(B,s(E)+'. ',11,True)
		rich(B,A,11)
	for G in c.get('children')or c.get('subclauses')or[]:clause(C,G,F+1)
def page_break(doc):A=para(doc,before=0,after=0);run(A,'')._r.append(_el('w:br',type='page'));return A
def annexes(doc,ans):
	B=doc
	if not ans:return
	for A in ans:
		page_break(B);D=txt(A,'label')or tr('annex');C=txt(A,'title');E=para(B,before=0,after=10,align=WD_ALIGN_PARAGRAPH.CENTER);run(E,D+(' - '+C if C else''),15,True,NAVY)
		if A.get('text'):rich(para(B,before=0,after=5),txt(A,'text'),11)
		for F in A.get('clauses')or[]:clause(B,F)
def signatures(doc,sig,m):
	A=(sig or{}).get('blocks')or[]
	if not A:A=[{'name':txt(A,'defined_as','name')}for A in m.get('parties')or[]]
	if not A:return
	para(doc,s((sig or{}).get('note'))or tr('witness'),11,True,INK,before=22,after=14);C=doc.add_table(rows=2,cols=len(A));C.alignment=WD_TABLE_ALIGNMENT.CENTER;table_borders(C,LINE,visible=False)
	for(E,B)in enumerate(A):
		cell_text(C.rows[0].cells[E],'_______________________',False,11,INK_SOFT,WD_ALIGN_PARAGRAPH.CENTER);D=[txt(B,'name')]
		if txt(B,'by'):D.append(tr('by')+txt(B,'by'))
		if txt(B,'title'):D.append(txt(B,'title'))
		cell_text(C.rows[1].cells[E],'\n'.join([A for A in D if A]),False,10,INK,WD_ALIGN_PARAGRAPH.CENTER)
def clause_sources(c):
	A=c.get('source')
	if isinstance(A,(list,tuple)):B=A
	else:B=[A for A in re.split('[,;]',str(A or''))]
	return[A.strip()for A in B if str(A).strip()]
def walk_clauses(cs,out=None):
	A=out;A=[]if A is None else A
	for B in cs or[]:A.append(B);walk_clauses(B.get('children')or B.get('subclauses'),A)
	return A
def all_clauses(d):
	A=walk_clauses(d.get('clauses'))
	for B in d.get('annexes')or[]:walk_clauses(B.get('clauses'),A)
	return A
def source_link(sid,research):
	from research_sources import approved_agreements as F,normalise as G;B=G(research or{});D,K,C=sid.partition('-')
	if D=='REG':
		for(H,A)in enumerate(B.get('law')or[]):
			if str(A.get('row',H+1))==C:return'%s (%s)'%(s(A.get('instrument')),s(A.get('sections'))),A.get('url')
	elif D=='AGR':
		for A in F(B):
			if str(A.get('no'))==C:return s(A.get('title')),A.get('url')
	elif D=='MAND':
		I={str(A.get('row',B+1)):A for(B,A)in enumerate(B.get('law')or[])}
		for E in B.get('mandatory_clauses')or[]:
			if E.get('clause_id')==C:J=I.get(str(E.get('source_row')),{});return tr('mand')%(s(E.get('title'))or C),J.get('url')
	return sid,None
def sources_section(doc,d,research):
	E=research;A=doc
	if not E:return
	from research_sources import NORM_RANKS as H,approved_agreements as I,normalise as J,scope_has as F;B=J(E);C=B.get('law')or[]if F(B,'research')else[];D=I(B)if F(B,'agreements')else[]
	if not(C or D):return
	h1(A,tr('sources'))
	def G(header,rows,link_col):
		E=header;B=A.add_table(rows=1+len(rows),cols=len(E));B.alignment=WD_TABLE_ALIGNMENT.CENTER;table_borders(B)
		for(C,G)in enumerate(E):cell_text(B.rows[0].cells[C],G,True,9.5,NAVY)
		for(F,H)in enumerate(rows):
			for(C,D)in enumerate(H):
				if C==link_col:cell_link(B.rows[F+1].cells[C],D[1],D[0])
				else:cell_text(B.rows[F+1].cells[C],D,False,9.5)
		para(A,after=6)
	if C:h1(A,tr('law'));K=H if RTL else NORM_RANKS_EN;G(tr('law_head'),[[K.get(A.get('rank'),''),(s(A.get('instrument')),A.get('url')),s(A.get('sections')),tr('verified')if A.get('verified')else tr('unverified')]for A in C],1)
	if D:h1(A,tr('ags'));G(tr('ags_head'),[[(s(A.get('title')),A.get('url')),s(A.get('publisher')),ORIENT_HE.get(A.get('orientation'),s(A.get('orientation')))if RTL else ORIENT_EN.get(A.get('orientation'),s(A.get('orientation')))]for A in D],0)
def footer(doc,m):
	B=[txt(m,'doc_type')or tr('draft')]
	if txt(m,'classification'):B.append(txt(m,'classification'))
	B.append(produced_on(m))
	for C in doc.sections:A=C.footer.paragraphs[0];dir_p(A);A.alignment=WD_ALIGN_PARAGRAPH.CENTER;run(A,' · '.join(B)+tr('page'),8.5,False,INK_SOFT);A._p.append(_el('w:fldSimple',instr='PAGE'))
class DraftRefused(Exception):0
class State4Refused(DraftRefused):0
class PublicFormRefused(DraftRefused):0
def public_form_gate(d,prof):
	from check_draft_integrity import public_party as C;A=d.get('meta')or{}
	if C(prof,A.get('counterparty_public_body'),A.get('company_role_code')):return
	B=[A for A in all_clauses(d)if A.get('public_form')and not A.get('user_requested')]
	if B:raise PublicFormRefused(['סעיף %s (%s) מקורו בטופס של גוף ציבורי, ואף אחד מהצדדים אינו גוף ציבורי (הפרופיל, meta.counterparty_public_body). הוציאו אותו מ-clauses והעבירו ל-cover.options, או סמנו user_requested אם המשתמש ביקש אותו.'%(num_label(A.get('number')).rstrip('.')or'?',txt(A,'heading')or txt(A,'text')[:40])for A in B])
def concern_refs(d):
	A=(d.get('cover')or{}).get('main_concern')
	if not A:return'',[]
	if not isinstance(A,dict):return s(A),[]
	B=A.get('clauses')or[];B=B if isinstance(B,(list,tuple))else re.split('[,;]\\s*',str(B));return s(A.get('answer')),[num_label(A).rstrip('.')for A in B if str(A).strip()]
def concern_gate(d):
	C,A=concern_refs(d)
	if not C:return
	if not A:raise DraftRefused(['החשש העיקרי שמסר הלקוח (cover.main_concern) לא תורגם לאף סעיף. נסחו לפחות סעיף מותאם אחד, ורשמו את מספרו ב-cover.main_concern.clauses.'])
	D={num_label(A.get('number')).rstrip('.')for A in all_clauses(d)if A.get('number')};B=[A for A in A if A not in D]
	if B:raise DraftRefused(['cover.main_concern מפנה לסעיפים שאינם בטיוטה: %s.'%', '.join(B)])
THIRD_PARTY='third_party_paper'
RESEARCH_IDS=re.compile('^(?:REG|MAND|AGR)-')
def state4_gate(d,research,approved_sources=None,inc_country=None):
	A=research;from research_sources import approved_mandatory as H,check,normalise as I,scope_has as J;B=d.get('meta')or{};K=s(B.get('source_mode'))==THIRD_PARTY;L=any(RESEARCH_IDS.match(B)for A in all_clauses(d)for B in clause_sources(A))
	if not(B.get('notice')and not K or d.get('sources')or A or L):return
	M=B.get('outside_basis')or{};F=[A for A in('no_playbook','no_client_agreements','client_asked')if M.get(A)is not True]
	if F:raise State4Refused(['ניסוח מבחוץ מותר רק כשללקוח אין פלייבוק ואין הסכמי טיוטה והוא ביקש זאת במפורש. חסר ב-meta.outside_basis: %s.'%', '.join(F)])
	if not A:raise State4Refused(['מקור REG-, MAND-, AGR- או sources דורש את קובץ המחקר (--research), שנאסף מהרשימה המאושרת בלבד.'])
	C,N,N=check(A,stage='draft',approved_sources=approved_sources,inc_country=inc_country);D=I(A)
	if J(D,'research'):
		G=set()
		for O in all_clauses(d):G.update(clause_sources(O))
		for E in H(D):
			if'MAND-%s'%E.get('clause_id')not in G:C.append('סעיף חובה %s (%s) לא שובץ באף סעיף בטיוטה. משבצים אותו, או מסירים אותו עם סיבה.'%(E.get('clause_id'),E.get('title')or''))
	if C:raise State4Refused(C)
	return D
def build(d,prof,out,research=None,cover=None,lang=None,approved_sources=None):
	F=lang;E=prof;C=cover;B=out;global RTL;D=d.get('meta')or{};L=state4_gate(d,research,approved_sources,(E or{}).get('incorporation_country'));public_form_gate(d,E);concern_gate(d);F=s(F)or s(D.get('language'))or s(profile_lang(E))or'he';RTL=not is_en(F);d,H=english_parties(d,E,RTL,s)
	if H:raise DraftRefused(H)
	del GAPS[:];A=Document();base(A);title_block(A,D);parties(A,D);recitals(A,d.get('recitals'));definitions(A,d.get('definitions'),bool(d.get('recitals')))
	for M in d.get('clauses')or[]:clause(A,M)
	annexes(A,d.get('annexes'));signatures(A,d.get('signatures'),D);footer(A,D)
	if not RTL:mixed_direction(A)
	A.save(B);from build_template_registry import docx_text as I;from check_draft_integrity import count_placeholders as N;J=N(I(B,limit=400000)[0])
	if C:write_cover(C,d,L,J)
	K=client_text_problems((B,C),RTL,I,_voice_check)
	if K:
		for G in(B,C):
			if G and os.path.exists(G):os.remove(G)
		raise DraftRefused(K)
	return{'out':B,'rtl':RTL,'clauses':len(d.get('clauses')or[]),'definitions':len(d.get('definitions')or[]),'annexes':len(d.get('annexes')or[]),'placeholders':J,'cover':C or''}
def open_items(d):
	E=[]
	def A(where,*B):
		A=[A for B in B for A in GAP_RX.findall(s(B))if A.strip()not in(TXT['he']['case_law'].strip(),TXT['en']['case_law'].strip())]
		if A:E.append((where,A))
	B=d.get('meta')or{};A(tr('loc_meta'),B.get('title'),B.get('place_date'),*[txt(A,B)for A in B.get('parties')or[]for B in('name','reg','address')]);A(tr('loc_recitals'),*(d.get('recitals')or[]))
	for F in d.get('definitions')or[]:A(tr('loc_def')%txt(F,'term'),txt(F,'text','definition'))
	for C in d.get('annexes')or[]:
		if C.get('text'):A(txt(C,'label')or tr('annex'),txt(C,'text'))
	for D in all_clauses(d):A(tr('loc_clause')%num_label(D.get('number')).rstrip('.'),txt(D,'heading','title'),txt(D,'text','body'))
	G=(d.get('signatures')or{}).get('blocks')or[];A(tr('loc_sign'),*[txt(A,B)for A in G for B in('name','by','title')]);return E
def key_date_lines(cv,lang=None):
	E=TXT[('en'if is_en(lang)else'he')if lang else'he'if RTL else'en'];C=[]
	for A in(cv or{}).get('key_dates')or[]:
		if isinstance(A,dict):
			F,G,D=s(A.get('what')),s(A.get('when')),s(A.get('clause'));B=': '.join(A for A in(F,G)if A)
			if B and D:B+=E['key_date_clause']%D
		else:B=s(A)
		if B:C.append(B)
	return C
def write_cover(path,d,r=None,gaps=None):
	E=gaps;D=d.get('meta')or{};B=d.get('cover')or{};P=s(D.get('source_mode'))==THIRD_PARTY;A=Document();base(A);run(para(A,after=2),tr('cover')+s(B.get('title')or txt(D,'title','doc_type')or tr('draft')),16,True,NAVY)
	if r is not None:from research_sources import normalise as Q;r=Q(r);L=tr('cover_stamp')%produced_on(D)
	else:L=tr('cover_stamp_plain')%produced_on(D)
	run(para(A,after=6),L,9.5,False,INK_SOFT);F=[A for A in all_clauses(d)if needs_review(A)];M=[A for A in all_clauses(d)if A.get('condition')];H=tr('lead');I=(E or 0)+len(F)+len(M)
	if I:
		H+=' '+tr('lead_open')%(I,5*max(1,-(-I//5)))
		if E:J=tr('next_fill')
		else:J=tr('next_review')%', '.join(num_label(A.get('number')).rstrip('.')for A in F+M)
	else:H+=' '+tr('lead_clear');J=tr('next_send')
	run(para(A,after=2),H,12,True,INK);run(para(A,after=10),J,11,False,NAVY);G=txt(D,'notice')
	if P and not G:G=tr('tp_notice')
	if G:h1(A,tr('notice_title'));N=para(A,before=0,after=10);ppr_put(N,_el('w:shd',val='clear',color='auto',fill='F5F7F9'));run(N,G,10,False,NAVY)
	def R():
		if r is not None:trace_matrix(A,d,r);sources_section(A,d,r)
		else:source_matrix(A,d,B)
	def C(title,lines,size=10.5):
		B=lines
		if not B:return
		h1(A,title)
		for C in B:rich(para(A,after=2,indent=.5),C,size)
	O,S=concern_refs(d)
	if O:C(tr('concern'),[tr('concern_answer')%O,tr('concern_clauses')%', '.join(S)])
	C(tr('choices'),choice_lines(B));C(tr('key_dates'),key_date_lines(B));C(tr('to_fill_count')%(tr('to_fill'),E)if E else tr('to_fill'),['%s: %s'%(A,', '.join(B))for(A,B)in open_items(d)])
	if F:C(tr('legal_review'),[tr('case_law_list')+', '.join(num_label(A.get('number')).rstrip('.')for A in F)])
	C(tr('conditional'),[tr('conditional_line')%(num_label(A.get('number')).rstrip('.'),s(A.get('condition')))for A in all_clauses(d)if A.get('condition')]);K=[tr('pb_gap_line')%(s(A.get('topic')),s(A.get('reason')))if isinstance(A,dict)else s(A)for A in B.get('playbook_gaps')or[]]
	if K and B.get('playbook_gaps_answer'):K.append(tr('pb_gaps_answer')%s(B.get('playbook_gaps_answer')))
	C(tr('pb_gaps'),K);C(tr('options'),[tr('option_line')%(s(A.get('title')),s(A.get('reason')))if isinstance(A,dict)else s(A)for A in B.get('options')or[]]);C(tr('decisions'),[s(A)for A in B.get('decisions')or[]]);C(tr('notes'),[s(A)for A in B.get('notes')or[]]+ld_notes(d));R()
	if r is not None:research_gaps(A,d,r)
	para(A,tr('run_risk'),10.5,True,INK,before=14)
	if not RTL:mixed_direction(A)
	A.save(path)
def choice_lines(cv,lang=None):
	E=TXT[('en'if is_en(lang)else'he')if lang else'he'if RTL else'en'];B=[]
	for A in(cv or{}).get('choices')or[]:
		if isinstance(A,dict):D=s(A.get('why'))or(E['choice_default']if A.get('default')else'');C=': '.join(A for A in(s(A.get('question')),s(A.get('answer')))if A);B.append(C+(('. 'if C and not C.endswith('.')else' ')+D if D else''))
		elif s(A):B.append(s(A))
	return[A for A in B if A]
def ld_notes(d):
	from check_draft_integrity import LD_RX;import governing_law as C;A=[num_label(A.get('number')).rstrip('.')for A in all_clauses(d)if A.get('number')and LD_RX.search(txt(A,'text','body'))]
	if not A:return[]
	B=(d.get('meta')or{}).get('governing_law');return[tr('ld_review')%(', '.join(A),C.name(B,'he'if RTL else'en')if B else tr('law_unset'))]
def source_matrix(doc,d,cv):
	C=cv;A=doc;h1(A,tr('matrix'));K=[]
	def L(cs,inherited):
		for A in cs or[]:
			B=clause_sources(A)or inherited
			if A.get('number'):K.append((A,B))
			L(A.get('children')or A.get('subclauses'),B)
	L(d.get('clauses'),[])
	for S in d.get('annexes')or[]:L(S.get('clauses'),[])
	H=A.add_table(rows=1+len(K),cols=5);H.alignment=WD_TABLE_ALIGNMENT.CENTER;table_borders(H)
	for(T,U)in enumerate(tr('matrix_head')):cell_text(H.rows[0].cells[T],U,True,9.5,NAVY)
	for(V,(D,P))in enumerate(K):M=lambda pre:', '.join(A[len(pre):]for A in P if A.upper().startswith(pre));E=H.rows[V+1].cells;cell_text(E[0],num_label(D.get('number')).rstrip('.'),False,9.5);cell_text(E[1],txt(D,'heading')or txt(D,'text')[:40],False,9.5);Q=[A for A in M('PB-').split(', ')if A];W=C.get('playbook_topics')or{};X=', '.join(dict.fromkeys(lang_safe(s(W.get(A)),'')or tr('from_pb')for A in Q));cell_text(E[2],X or tr('no_pb'),False,9.5,INK if Q else INK_SOFT);I=s(D.get('source_clause'))if D.get('source_clause')else'';N=', '.join(doc_title(C,A)for A in M('DOC-').split(', ')if A);cell_text(E[3],N+(' (%s)'%I if N and I else I)if N or I else'',False,9.5);Y=M('DEAL-')or(tr('yes')if any(A.upper()=='DEAL'for A in P)else'');cell_text(E[4],Y,False,9.5)
	para(A,after=6);F=[];G=C.get('playbook')or{}
	if G:F.append(tr('pb_line')%', '.join(A for A in(lang_safe(s(G.get('name')),''),pb_status(G.get('status')))if A)if isinstance(G,dict)else tr('pb_line')%s(G))
	for(J,B)in enumerate(C.get('documents')or[]):
		if isinstance(B,dict):F.append(tr('doc_line')%(s(B.get('no')or J+1),', '.join(lang_safe(s(B.get(A)),'')for A in('title','publisher','year')if lang_safe(s(B.get(A)),''))or'Form %s'%(B.get('no')or J+1)))
		else:F.append(tr('doc_line')%(J+1,lang_safe(s(B),'Form %s'%(J+1))))
	if F:
		h1(A,tr('sources_used'))
		for O in F:rich(para(A,after=2,indent=.5),O,10.5)
	R=[s(A)for A in C.get('facts')or[]]
	if R:
		h1(A,tr('facts'))
		for O in R:rich(para(A,after=2,indent=.5),O,10.5)
def lang_safe(text,fallback):return fallback if not RTL and HEB_CH.search(text or'')else text
def doc_title(cv,no):
	for(C,A)in enumerate(cv.get('documents')or[]):
		D=str(A.get('no')or C+1)if isinstance(A,dict)else str(C+1)
		if D==str(no):B=lang_safe(s(A.get('title')if isinstance(A,dict)else A),'Form %s'%no);return B if len(B)<=40 else B[:40].rsplit(' ',1)[0]+'...'
	return s(no)
def pb_status(v):A=s(v);return tr('pb_pending')if re.search('מוצע|טעון אישור|טיוטת מדיניות|מחכה לאישור|proposed|pending|draft|awaiting',A,re.I)else A
def write_cover4(path,d,r):write_cover(path,d,r)
def trace_matrix(doc,d,r):
	F=doc;h1(F,tr('trace'));G=[A for A in all_clauses(d)if A.get('number')];D=F.add_table(rows=1+len(G),cols=5);D.alignment=WD_TABLE_ALIGNMENT.CENTER;table_borders(D)
	for(I,J)in enumerate(tr('trace_head')):cell_text(D.rows[0].cells[I],J,True,9.5,NAVY)
	for(K,B)in enumerate(G):
		E=clause_sources(B);A=D.rows[K+1].cells;cell_text(A[0],s(B.get('number')),False,9.5);cell_text(A[1],txt(B,'heading')or txt(B,'text')[:40],False,9.5)
		if E:C,H=source_link(E[0],r);C=C if C!=E[0]else tr('own');cell_link(A[2],H,C)if H else cell_text(A[2],C,False,9.5)
		else:cell_text(A[2],tr('own'),False,9.5,INK_SOFT)
		cell_text(A[3],tr('yes')if any(A.startswith('MAND-')for A in E)else tr('no'),False,9.5);cell_text(A[4],tr('yes')if B.get('opening_position')else'',False,9.5)
	para(F,after=6)
def research_gaps(doc,d,r):
	B=doc;from research_sources import scope_has as F;G=r.get('approvals')or{};C=G.get('removed_clauses')or[]
	if C:
		h1(B,tr('removed'))
		for A in C:
			if isinstance(A,dict):D=tr('removed_line')%(A.get('clause_id',''),A.get('reason',''),A.get('exposure',tr('fill')))
			else:D=str(A)
			rich(para(B,after=3,indent=.5),D,10.5)
	h1(B,tr('gaps'))
	if not F(r,'research'):para(B,tr('no_research'),10.5,True,INK,after=3)
	else:
		para(B,tr('research_limits'),10.5,False,INK,after=3)
		for A in[A for A in r.get('law')or[]if not A.get('verified')]:E=para(B,after=3,indent=.5);run(E,tr('unverified_line'),10.5,True);link(E,A.get('url'),s(A.get('instrument')),10.5)
def main():
	B=argparse.ArgumentParser();B.add_argument('--draft',required=True);B.add_argument('--profile');B.add_argument('--out',required=True);B.add_argument('--research',help='מצב 4: קובץ המחקר שאושר. בלעדיו טיוטת מצב 4 אינה נבנית');B.add_argument('--cover',help='דף ליווי, בכל מצב: במצב 4 עם מטריצת עקיבות מול המחקר, ובלי מחקר עם מטריצת המקורות (פלייבוק, נוסחים, עובדות העסקה)');B.add_argument('--lang',choices=('he','en'),help='שפת הטיוטה; בלעדיו: meta.language, ואחריו deliverable_language בפרופיל');B.add_argument('--approved-sources',help='מצב 4: מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json). בלי רשימה תקפה, טיוטה ממחקר רגולטורי נעצרת בקוד 2');B.add_argument('--force',action='store_true',help='לדרוס טיוטה או דף ליווי קיימים (הרצה חוזרת אחרי תיקון)');A=B.parse_args();from build_template_registry import guard_out as F;G=[A.draft,A.profile,A.research,A.approved_sources];F(A.out,G,A.force)
	if A.cover:F(A.cover,G+[A.out],A.force)
	H=json.load(io.open(A.draft,encoding='utf-8'));D={}
	if A.profile:
		try:D=json.load(io.open(A.profile,encoding='utf-8'))
		except(OSError,ValueError):D={}
	I=json.load(io.open(A.research,encoding='utf-8'))if A.research else None;from research_sources import ApprovedSourcesMissing as J
	try:C=build(H,D,A.out,I,A.cover,A.lang,A.approved_sources)
	except J as E:print('הטיוטה לא נבנתה. סירוב: %s'%E);sys.exit(2)
	except DraftRefused as E:
		print('הטיוטה לא נבנתה:')
		for K in E.args[0]:print('  חוסם: '+K)
		sys.exit(1)
	print('הטיוטה נבנתה: %s'%C['out']);print('סעיפים ראשיים: %d · הגדרות: %d · נספחים: %d · כיווניות: %s'%(C['clauses'],C['definitions'],C['annexes'],'RTL'if C['rtl']else'LTR'))
	if C['placeholders']:print('פרטים להשלים שסומנו בצהוב: %d. הם של הלקוח, רשומים בדף הליווי ובהודעת המסירה, ואינם עוצרים את המסירה.'%C['placeholders'])
	if C['cover']:print('דף הליווי נבנה: %s'%C['cover'])
	import governing_law as L
	if not L.code((H.get('meta')or{}).get('governing_law')):print('אזהרה: meta.governing_law חסר או לא מוכר. הדין החל נשאל לפני הניסוח (SKILL.md), ואינו מונח. Warning: meta.governing_law is missing or unknown. Ask for the governing law; never assume it.')
if __name__=='__main__':main()
