# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import io,json,os,re
from docx import Document
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls,qn
try:from common import rtl;from playbook import status as S;from playbook import market_counts as MC
except ImportError:import sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common import rtl;from playbook import status as S;from playbook import market_counts as MC
STATUS_TAG='areo:status_label'
SUMMARY_TAG='areo:status_summary'
CELL_TAG='areo:cell_status:'
SUMMARY_PREFIX='מעמד העמדות: '
CELL_PREFIX='מעמד העמדה: '
PREFIXES={'he':{'summary':SUMMARY_PREFIX,'cell':CELL_PREFIX},'en':{'summary':'Status of positions: ','cell':'Position status: '}}
SUMMARY_PREFIXES=tuple(PREFIXES[A]['summary'].strip()for A in('he','en'))
CELL_PREFIXES=tuple(PREFIXES[A]['cell'].strip()for A in('he','en'))
_PARTIAL_RE=re.compile('^(%s); \\d+ (?:מתוך|of) \\d+ (?:עמדות מאושרות|positions approved)'%'|'.join(re.escape(A)for A in S.BASE_LABELS))
_DATA_MARKERS=re.compile('const\\s+D\\s*=\\s*'),re.compile('/\\*__DATA__\\*/')
CELL_TEXT={'approved':'מאושרת, {date}','approved_modified':'מאושרת בשינוי שהיועץ המשפטי הכניס, {date}','pending_choice':'ממתינה לבחירה בגיליון ({reason})','pending_legal_review':'ממתינה לבדיקה משפטית ("נבדק בידי" ותאריך)','open':'פתוחה ({reason})','not_signed':'לא מאושרת: העמודה לא נחתמה'}
CELL_TEXT_EN={'approved':'approved, {date}','approved_modified':'approved with a change made by legal counsel, {date}','pending_choice':'awaiting a choice in the sheet ({reason})','pending_legal_review':'awaiting legal review ("Reviewed by" and date)','open':'open ({reason})','not_signed':'not approved: the column was not signed'}
CELL_WORDS={'he':{'none':'מחכה לאישור שלכם','simulated':'לא מאושרת (החתימה נקלטה בסימולציה)','blocked':'ממתינה להכרעה בשאלה מכריעה פתוחה','not_approved':'לא מאושרת (%s)','missing':'חסרה דוגמה מההסכמים, או שעורך דין עוד לא עבר עליה','summary_all':'%s. כל %d העמדות מאושרות.','summary_part':'%s. %d מתוך %d עמדות מאושרות.'},'en':{'none':'awaiting your approval','simulated':'not approved (the signature was ingested in a simulation)','blocked':'awaiting a decision on an open decisive question','not_approved':'not approved (%s)','missing':"no example from your agreements, or a lawyer hasn't reviewed it yet",'summary_all':'%s. All %d positions are approved.','summary_part':'%s. %d of %d positions approved.'}}
REASON_EN=[(re.compile('^העמודה לא נחתמה$'),'the column was not signed'),(re.compile('^השורה (\\S+) לא נמצאה בקובץ$'),'row \\1 was not found in the file'),(re.compile('^תוכן התא נמחק'),'the cell content was deleted: reject the track, or require other wording?'),(re.compile('^טעון בדיקה משפטית'),'legal review required: reviewer name and review date were not recorded'),(re.compile('^הנחה שלא אושרה בתא'),'an assumption in the cell was not confirmed'),(re.compile('^הערת Areo פתוחה בשורה (\\S+)'),'an open Areo comment in row \\1'),(re.compile('^לא נבחרה אפשרות בשאלה (\\S+)'),'no option was chosen in question \\1'),(re.compile('^נבחרה יותר מאפשרות אחת בשאלה (\\S+)'),'more than one option was chosen in question \\1'),(re.compile('^לא נבחרה אפשרות'),'no option was chosen')]
_HEB=re.compile('[\u0590-\u05ff]')
def reason_text(reason,lang='he'):
	B=reason
	if lang!='en'or not B or not _HEB.search(B):return B or''
	D=[]
	for A in[A.strip()for A in B.split(';')if A.strip()]:
		for(E,C)in REASON_EN:
			if E.search(A):A=E.sub(C,A)if'\\'in C else C;break
		D.append(A if not _HEB.search(A)else CELL_WORDS['en']['missing'])
	return'; '.join(D)
def surface_lang(st=None,lang=None):return S.norm_lang(lang)or(st or{}).get('lang')or'he'
class RerenderError(RuntimeError):0
def _d(iso,lang='he'):
	try:return S.fmt_date(iso,lang)
	except(ValueError,TypeError):return str(iso or'')
def cell_status_text(cell,st=None,key=None,lang=None):
	B=cell;A=lang;A=surface_lang(st,A);D,C=PREFIXES[A]['cell'],CELL_WORDS[A]
	if not B:return D+C['none']
	if B.get('simulated'):return D+C['simulated']
	E=B.get('status');F=reason_text(B.get('reason'),A)
	if E in S.APPROVED and st is not None and key is not None and key not in st['approved_keys']:
		if S.cell_counts(B):return D+C['blocked']
		return D+C['not_approved']%(F or C['missing'])
	G=(CELL_TEXT_EN if A=='en'else CELL_TEXT).get(E,C['none']);return D+G.format(date=_d(B.get('approved_at'),A),reason=F)
def summary_text(st,lang=None):
	B=lang;A=st;B=surface_lang(A,B);A=S.in_lang(A,B);C=CELL_WORDS[B]
	if A['playbook_status']==S.STATUS_APPROVED:return PREFIXES[B]['summary']+C['summary_all']%(A['label'],A['positions_count'])
	return PREFIXES[B]['summary']+C['summary_part']%(A['label'],A['approved_count'],A['positions_count'])
def status_texts(model,st,cells):A=cells;A=A or{};return{'label':st['label'],'summary':summary_text(st),'cells':{B:cell_status_text(A.get(B),st,B)for B in S.iter_cell_keys(model)}}
def add_status_control(paragraph,tag,text,size=None,lang='he'):
	B=size;A=paragraph;E='<w:sz w:val="%d"/><w:szCs w:val="%d"/>'%(B*2,B*2)if B else''
	if lang=='en':C,D='<w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/>',''
	else:C,D='<w:rFonts w:ascii="David" w:hAnsi="David" w:cs="David"/>','<w:rtl/>'
	F='<w:sdt %s><w:sdtPr><w:tag w:val="%s"/></w:sdtPr><w:sdtContent><w:r><w:rPr>%s%s%s</w:rPr><w:t xml:space="preserve">%s</w:t></w:r></w:sdtContent></w:sdt>'%(nsdecls('w'),tag,C,E,D,_xml_escape(text));A._p.append(parse_xml(F))
	if lang=='en':set_paragraph_ltr(A)
	else:rtl.set_paragraph_rtl(A)
	return A
def _ltr_el(el):
	for B in('w:bidi','w:rtl','w:bidiVisual','w:rtlGutter'):
		for A in el.iter(qn(B)):A.getparent().remove(A)
def set_paragraph_ltr(paragraph):A=paragraph;_ltr_el(A._p);return A
def is_ltr_doc(doc):
	A=(doc.core_properties.language or'').lower()
	if A:return A.startswith('en')
	B=doc.element.body.find(qn('w:sectPr'));return B is not None and B.find(qn('w:bidi'))is None
def doc_lang(doc):return'en'if is_ltr_doc(doc)else'he'
def enforce_ltr_document(doc,author='',title=None,language='en-US'):
	A=doc;B=[A.element.body]
	for C in A.sections:
		for E in(C.header,C.footer):B.append(E._element)
	try:B.append(A.part._comments_part.element)
	except Exception:pass
	for D in B:_ltr_el(D);keep_hebrew_rtl(D)
	_ltr_el(A.styles.element);rtl.clean_metadata(A,author=author,title=title);A.core_properties.language=language;return A
_HEB_RE=re.compile('[\u0590-\u05ff]')
def hebrew_dominant(text):A=len(_HEB_RE.findall(text));return A>0 and A>=len(re.findall('[A-Za-z]',text))
def keep_hebrew_rtl(root):
	B=0
	for A in root.iter(qn('w:p')):
		C=_p_text(A)
		if not _HEB_RE.search(C):continue
		B+=1
		if hebrew_dominant(C):rtl._ppr_rtl(A)
		for D in A.iter(qn('w:r')):
			if _HEB_RE.search(''.join(A.text or''for A in D.iter(qn('w:t')))):rtl._rpr_rtl(D)
	return B
def _xml_escape(s):return(s or'').replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')
def _p_text(p_el):return''.join(A.text or''for A in p_el.iter(qn('w:t')))
def _set_runs_text(container_el,text):
	A=list(container_el.iter(qn('w:t')))
	if not A:return False
	A[0].text=text;A[0].set('{http://www.w3.org/XML/1998/namespace}space','preserve')
	for B in A[1:]:B.text=''
	return True
def _roots(doc):
	D=[doc.element.body]
	for A in doc.sections:
		for B in(A.header,A.footer,A.first_page_header,A.even_page_header):
			try:
				if not B.is_linked_to_previous or B is A.header:D.append(B._element)
			except Exception:pass
	E,F=set(),[]
	for C in D:
		if id(C)not in E:E.add(id(C));F.append(C)
	return F
def _is_label(text):A=text.strip();return A in S.BASE_LABELS or A.startswith(S.APPROVED_PREFIXES)or bool(_PARTIAL_RE.match(A))
FILE_WORDS={'he':{S.STATUS_DRAFT:'פלייבוק מוצע',S.STATUS_PARTIAL:'פלייבוק מאושר בחלקו',S.STATUS_APPROVED:'מדיניות מאושרת'},'en':{S.STATUS_DRAFT:'Proposed playbook',S.STATUS_PARTIAL:'Partially approved playbook',S.STATUS_APPROVED:'Approved policy'}}
def surface_filename(path,st):
	D,A=os.path.split(path)
	for B in FILE_WORDS.values():
		E=B[st['playbook_status']]
		for C in B.values():
			if C in A:return os.path.join(D,A.replace(C,E))
	return path
def restamp_docx(src,model,st,cells,dst=None):
	Q=model;G=src;B=Document(G);M=doc_lang(B);st=S.in_lang(st,M);C=status_texts(Q,st,cells);D={'label':0,'summary':0,'cells':0};N=set()
	for E in _roots(B):
		for R in E.iter(qn('w:sdt')):
			T=R.find(qn('w:sdtPr')+'/'+qn('w:tag'));H=T.get(qn('w:val'))if T is not None else'';I=R.find(qn('w:sdtContent'))
			if I is None:continue
			if H==STATUS_TAG:_set_runs_text(I,C['label']);D['label']+=1
			elif H==SUMMARY_TAG:_set_runs_text(I,C['summary']);D['summary']+=1
			elif H.startswith(CELL_TAG)and H[len(CELL_TAG):]in C['cells']:_set_runs_text(I,C['cells'][H[len(CELL_TAG):]]);D['cells']+=1
			else:continue
			N.add(I)
	J=[];U=[A for A in S.BASE_LABELS]
	for E in _roots(B):
		for A in E.iter(qn('w:p')):
			if any(A in N for A in A.iterancestors())or any(A in N for A in A.iter(qn('w:sdtContent'))):continue
			V=_p_text(A);K=V.strip()
			if not K:continue
			if _is_label(K):_set_runs_text(A,C['label']);D['label']+=1
			elif K.startswith(SUMMARY_PREFIXES):_set_runs_text(A,C['summary']);D['summary']+=1
			elif K.startswith(CELL_PREFIXES):J.append(A)
			else:
				for F in A.iter(qn('w:t')):
					for L in U:
						if F.text and L in F.text and L!=C['label']and not C['label'].startswith(L):F.text=F.text.replace(L,C['label']);D['label']+=1
	if J:
		O=list(S.iter_cell_keys(Q))
		if len(J)!=len(O):raise RerenderError('במסמך %d שורות "מעמד העמדה" ובפלייבוק %d תאים: יש לבנות את ה-Word מחדש מהמודל'%(len(J),len(O)))
		for(A,W)in zip(J,O):_set_runs_text(A,C['cells'][W]);D['cells']+=1
	if M=='en':
		for E in _roots(B):_ltr_el(E)
	else:
		for E in _roots(B):
			for A in E.iter(qn('w:p')):
				for F in A.iter(qn('w:r')):rtl._rpr_rtl(F)
	rtl.clean_metadata(B,author=B.core_properties.author or'',title=B.core_properties.title);B.core_properties.language='en-US'if M=='en'else'he-IL';P=dst or surface_filename(G,st);B.save(P)
	if os.path.abspath(P)!=os.path.abspath(G)and dst is None and os.path.exists(G):os.remove(G)
	return P,D
def read_docx_status(path):
	C=Document(path);B={'header':[],'labels':[],'summary':[],'cells':{},'cell_lines':[],'text':'','lang':doc_lang(C)};D=[]
	for(I,E)in enumerate(_roots(C)):
		for F in E.iter(qn('w:sdt')):
			G=F.find(qn('w:sdtPr')+'/'+qn('w:tag'));H=G.get(qn('w:val'))if G is not None else'';J=''.join(A.text or''for A in F.iter(qn('w:t'))).strip()
			if H.startswith(CELL_TAG):B['cells'][H[len(CELL_TAG):]]=J
		for K in E.iter(qn('w:p')):
			A=_p_text(K).strip()
			if not A:continue
			D.append(A)
			if _is_label(A):
				B['labels'].append(A)
				if I>0:B['header'].append(A)
			elif A.startswith(SUMMARY_PREFIXES):B['summary'].append(A)
			elif A.startswith(CELL_PREFIXES):B['cell_lines'].append(A)
	B['text']='\n'.join(D);return B
def _find_payload(html):
	B=html
	for D in _DATA_MARKERS:
		C=D.search(B)
		if not C:continue
		A=C.end()
		if B[A:A+4]=='null':continue
		E,F=json.JSONDecoder().raw_decode(B,A);return E,A,F
	raise RerenderError('לא נמצאו נתוני הדף (const D = {...} או /*__DATA__*/) ב-Workspace')
def restamp_workspace(src,st,dst=None):
	A=st
	with io.open(src,encoding='utf-8')as E:C=E.read()
	G,K,L=_find_payload(C);B=G.setdefault('meta',{});A=S.in_lang(A,B.get('lang'))
	for M in S.DUAL_FIELDS:B.pop(M,None)
	H=B.get('status');B.update({'status_label':A['label'],'label_now':A['label'],'status':A['label'],'playbook_status':A['playbook_status'],'approved_count':A['approved_count'],'positions_count':A['positions_count']})
	if'labels'in B:B['labels']={B:S.label_for(A,B)for B in('he','en')}
	for I in('evidence_disclaimer',):
		D=B.get(I)
		if isinstance(D,str):
			for F in[A for A in S.BASE_LABELS+((H,)if H else())if A]:
				if F in D and F!=A['label']:D=D.replace(F,A['label'])
			B[I]=D
	N=json.dumps(G,ensure_ascii=False).replace('</','<\\/');C=C[:K]+N+C[L:];J=dst or src
	with io.open(J,'w',encoding='utf-8',newline='')as E:E.write(C)
	return J
def read_workspace_status(path):
	with io.open(path,encoding='utf-8')as A:B=A.read()
	C,D,D=_find_payload(B);return C
def check_surfaces(st,word_path=None,workspace_path=None,model=None):
	G=workspace_path;F=word_path;E=model;A=st;B=[];H=A
	if F:
		C=read_docx_status(F);A=S.in_lang(H,C['lang']);N=[B for B in S.BASE_LABELS if not A['label'].startswith(B)]
		if not C['header']:B.append('Word: אין תווית בכותרת העליונה')
		for I in C['header']:
			if I!=A['label']:B.append('Word: הכותרת העליונה "%s", המחושב: "%s"'%(I,A['label']))
		for J in C['labels']:
			if J!=A['label']:B.append('Word: תווית "%s" בגוף המסמך, המחושב: "%s"'%(J,A['label']))
		for K in C['summary']:
			if K!=summary_text(A):B.append('Word: "%s" אינו המעמד המחושב'%K[:80])
		for L in N:
			if L in C['text']:B.append('Word: נשארה התווית הישנה "%s"'%L)
		if A['playbook_status']!=S.STATUS_DRAFT and('נקלט בסימולציה'in C['text']or'ingested in a simulation'in C['text'])and not any('סימולציה'in A or'simulation'in A for A in C['cells'].values()):B.append('Word: נשאר משפט על קליטה בסימולציה')
		if E is not None:B+=['Word: '+A for A in MC.count_claims(C['text'],E)]
	if G:
		O=read_workspace_status(G);D=O.get('meta')or{};A=S.in_lang(H,D.get('lang'))
		for M in S.DUAL_FIELDS:
			if M in D:B.append('Workspace: meta.%s: שדה תווית כפול'%M)
		if D.get('label_now')!=A['label']:B.append('Workspace: label_now="%s", המחושב: "%s"'%(D.get('label_now'),A['label']))
		if D.get('approved_count')!=A['approved_count']:B.append('Workspace: approved_count=%s, המחושב: %d'%(D.get('approved_count'),A['approved_count']))
		if E is not None:B+=['Workspace: '+A for A in MC.count_claims(D.get('evidence_disclaimer')or'',E)]
	return B
