# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import datetime as _dt,hashlib,io,json,os,re,shutil,zipfile
from lxml import etree
try:from playbook.approval_sheet import fingerprint,norm_text,decision_slots,AREO_AUTHOR,HE,EN;from playbook import approval_sheet as A;from playbook import status as S;from common import paths as P
except ImportError:import sys;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from playbook.approval_sheet import fingerprint,norm_text,decision_slots,AREO_AUTHOR,HE,EN;from playbook import approval_sheet as A;from playbook import status as S;from common import paths as P
W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
W14='http://schemas.microsoft.com/office/word/2010/wordml'
W15='http://schemas.microsoft.com/office/word/2012/wordml'
DC='http://purl.org/dc/elements/1.1/'
TRACKS='green','yellow','red'
MAX_UNZIPPED=62914560
ROLE_WORDS='היועץ','היועצת','המשפטי','המשפטית','מנכ"ל','מנכ״ל','סמנכ"ל','הלשכה','המחלקה','general counsel','legal counsel','ceo'
EVIDENCE_KINDS='user_upload','chat_attachment'
_ATTACHMENT_ID=re.compile('^[A-Za-z0-9_\\-:.]{6,128}$')
_DATE=re.compile('\\d{1,2}[./-]\\d{1,2}[./-]\\d{2,4}|\\d{4}-\\d{2}-\\d{2}')
class IngestRefused(ValueError):0
def q(tag,ns=W):return'{%s}%s'%(ns,tag)
def long_path(path):return P.long_path(path)
def _para_text(p):return''.join(A.text or''for A in p.iter(q('t')))
def sha256_file(path):
	with open(long_path(path),'rb')as A:return hashlib.sha256(A.read()).hexdigest()
class SignedDoc:
	PARSER=etree.XMLParser(resolve_entities=False,no_network=True,huge_tree=False)
	def __init__(A,path):
		with zipfile.ZipFile(long_path(path))as B:
			if sum(A.file_size for A in B.infolist())>MAX_UNZIPPED:raise ValueError('הקובץ גדול מדי לקליטה')
			C=set(B.namelist());A.parts={A:B.read(A)for A in('word/document.xml','word/comments.xml','word/commentsExtended.xml','docProps/core.xml')if A in C}
		A.doc=A._xml('word/document.xml')
		if A.doc is None:raise ValueError('זה אינו קובץ Word תקין')
		A.comments=A._xml('word/comments.xml');A.cext=A._xml('word/commentsExtended.xml');A.core=A._xml('docProps/core.xml')
	def _xml(A,name):B=A.parts.get(name);return etree.fromstring(B,A.PARSER)if B else None
	def token(A):
		if A.core is not None:
			B=A.core.find(q('identifier',DC))
			if B is not None and B.text:return B.text.strip()
		C=re.search('ISS-\\d{4}\\|[^|\\s]+\\|[0-9a-f]{12}',''.join(A.doc.itertext()));return C.group(0)if C else None
	def checkboxes(G,root=None):
		B={}
		for C in(root if root is not None else G.doc).iter(q('sdt')):
			A=C.find(q('sdtPr'));D=A.find(q('tag'))if A is not None else None;E=A.find(q('checkbox',W14))if A is not None else None
			if D is None or E is None:continue
			F=E.find(q('checked',W14));H=''.join(A.text or''for A in C.iter(q('t')));B[D.get(q('val'))]=bool(F is not None and F.get(q('val',W14))in('1','true')or'☒'in H)
		return B
	def open_areo_comment_ids(A):
		D={}
		if A.cext is not None:
			for E in A.cext.iter(q('commentEx',W15)):D[E.get(q('paraId',W15))]=E.get(q('done',W15))in('1','true')
		B=set()
		if A.comments is None:return B
		for C in A.comments.iter(q('comment')):
			if(C.get(q('author'))or'')!=AREO_AUTHOR:continue
			F=[A.get(q('paraId',W14))for A in C.iter(q('p'))]
			if not any(D.get(A)for A in F if A):B.add(C.get(q('id')))
		return B
	def tables(A):return list(A.doc.iter(q('tbl')))
def _rows_by_code(sd,manifest):
	B={}
	for E in sd.tables():
		for F in E.iter(q('tr')):
			A=F.findall(q('tc'))
			if len(A)!=4:continue
			C=list(A[0].iter(q('p')));D=norm_text(_para_text(C[0]))if C else''
			if D in manifest['rows']:B[D]=A
	return B
def _cell_parts(tc):
	D,C,E,F,G=None,None,[],None,None;B=HE,EN;L=[norm_text(A[B])for A in B for B in('wording','cure')];M={norm_text(A['no_wording'])for A in B};N=[norm_text(A['legal_line'])for A in B];O=[norm_text(A['legal_date'])for A in B];P=tuple(norm_text(A[B])for A in B for B in('flags','assume'))
	for Q in tc.iter(q('p')):
		A=norm_text(_para_text(Q))
		if not A:continue
		H=next((B for B in L if A.startswith(B)),None);I=next((B for B in N if A.startswith(B)),None);J=next((B for B in O if A.startswith(B)),None)
		if H:
			C=A[len(H):].strip()
			if C in M:C=''
		elif A.startswith(('כשהחברה','מה זה מטיל','When the company','What this imposes')):E.append(A.split(':',1)[1].strip()if':'in A else A)
		elif I:F=A[len(I):].strip(' _.')or None
		elif J:K=_DATE.search(A[len(J):]);G=K.group(0)if K else None
		elif A.startswith(P)or'☐'in A or'☒'in A:continue
		elif D is None:D=A
	return D,C,E,F,G
def _is_person_name(name):
	A=norm_text(name)
	if len(A.split())<2:return False
	B=A.lower();return not any(A.lower()in B for A in ROLE_WORDS)
def _signers(sd,boxes):
	E={norm_text(C):B for A in(HE,EN)for(B,C)in A['track_label'].items()};D={}
	for F in sd.tables():
		for G in F.iter(q('tr')):
			A=G.findall(q('tc'))
			if len(A)!=5:continue
			B=E.get(norm_text(''.join(_para_text(A)for A in A[0].iter(q('p')))))
			if not B:continue
			C=[norm_text(' '.join(_para_text(A)for A in A.iter(q('p'))))for A in A[2:5]];D[B]={'checked':bool(boxes.get('chk:sign:%s'%B)),'name':C[0],'role':C[1],'date':C[2]}
	return D
def _row_has_comment(tcs,ids):
	for A in tcs:
		for B in A.iter(q('commentRangeStart'),q('commentReference')):
			if B.get(q('id'))in ids:return True
	return False
def _row_choices(manifest,row_meta,boxes):
	G=boxes;A=row_meta;H,B={},[]
	for C in A.get('questions')or[]:
		D=(manifest.get('questions')or{}).get(C)or{};E=[A for A in D.get('options')or[]if G.get(A['tag'])]
		if not E:B.append('לא נבחרה אפשרות בשאלה %s'%C)
		elif len(E)>1:B.append('נבחרה יותר מאפשרות אחת בשאלה %s'%C)
		else:F=E[0];H[C]={'row':D.get('row'),'index':F['index'],'text':F['text'],'tag':F['tag'],'question':D.get('question')or''}
	if not A.get('questions')and A.get('choices')and not any(G.get(A)for A in A['choices']):B.append('לא נבחרה אפשרות')
	return H,B
def evidence_status(received_via,upload_ref,signed_sha,issued_sha=None):
	E=issued_sha;D=signed_sha;C=received_via;B=upload_ref;A=[]
	if C not in EVIDENCE_KINDS:A.append('אין ראיה שהקובץ הגיע מהמשתמש (received_via: %s). הרשומה מסומנת simulated, ושער המדיניות לא יתיר "מדיניות" על סמכה.'%(C or'חסר'));return True,A
	if not B:A.append('חסרה הפניה לאירוע ההעלאה (upload_ref). הרשומה מסומנת simulated.');return True,A
	if os.path.exists(long_path(B)):
		if sha256_file(B)!=D:A.append('הקובץ שב-upload_ref אינו הקובץ שנקלט. הרשומה מסומנת simulated.');return True,A
	elif not _ATTACHMENT_ID.match(str(B)):A.append('upload_ref אינו נתיב קיים ואינו מזהה צרופה. הרשומה מסומנת simulated.');return True,A
	if E and E==D:A.append('הקובץ זהה בייט לבייט לגיליון שהופק: אין בו חתימה. הרשומה מסומנת simulated.');return True,A
	return False,A
def ingest(signed_path,manifest,received_via=None,upload_ref=None,today=None):
	Z=upload_ref;Y=received_via;X=signed_path;I=today;D=manifest;I=I or _dt.date.today().isoformat();F=SignedDoc(X)
	if F.token()!=D['token']:raise ValueError('המסמך שייך להפקה אחרת, ולא לגיליון הזה')
	N=F.checkboxes()
	if not N.get('chk:final'):return{'cells':{},'record':None,'warnings':['לא סומן "זו הגרסה הסופית לחתימה"']}
	J=[];h=_signers(F,N);G={}
	for(E,K)in h.items():
		if not K['checked']:continue
		if not _is_person_name(K['name']):J.append('עמודת %s: "%s" אינו שם מלא של אדם. העמודה לא נקלטה.'%(E,K['name']));continue
		G[E]=K
	O=sha256_file(X);P,i=evidence_status(Y,Z,O,D.get('issued_sha256'));J+=i;j=F.open_areo_comment_ids();a=_rows_by_code(F,D);b,c={},{}
	for(L,d)in D['rows'].items():
		H=a.get(L);C=[]
		if H is not None and _row_has_comment(H,j):C.append('הערת Areo פתוחה בשורה %s (%s)'%(L,', '.join(A for A in d.get('questions')or[]if A)or'בחירה נדרשת'))
		k,l=_row_choices(D,d,N);C+=['%s בשורה %s'%(A,L)for A in l];b.update(k)
		if C:c[L]=C
	Q={}
	for(e,A)in D['cells'].items():
		E=e.split('|')[2];B={'status':'not_signed','policy_claim':False,'reason':None,'approved_text':None,'simulated':P,'legal_review_required':A['legal_review'],'legal_review_done_by':None,'legal_review_done_at':None,'approved_at':None,'issued_fp':A['fp'],'assumptions_confirmed':[]};Q[e]=B
		if E not in G:B['reason']='העמודה לא נחתמה';continue
		H=a.get(A['row'])
		if H is None:B.update(status='open',reason='השורה %s לא נמצאה בקובץ'%A['row']);continue
		C=list(c.get(A['row'])or[]);m=F.checkboxes(H[A['col']]);n={A['tag']:A['text']for A in A.get('assumption_texts')or[]}
		for R in A.get('assumptions')or[]:
			if m.get(R):B['assumptions_confirmed'].append({'tag':R,'text':n.get(R,''),'confirmed_by':G[E]['name'],'at':I})
			else:C.append('הנחה שלא אושרה בתא')
		if C:B.update(status='pending_choice',reason='; '.join(C));continue
		M,S,T,U,V=_cell_parts(H[A['col']])
		if not M:B.update(status='open',reason='תוכן התא נמחק: לא מאשרים את המסלול, או דורשים נוסח אחר?');continue
		W=' '.join([M,S or'']+T);f=decision_slots(W)+[A for A in A.get('decision_slots')or[]if A in W and A not in decision_slots(W)]
		if f:B.update(status='pending_choice',reason='נשאר ערך שלא נקבע: %s. יש לכתוב את הערך במקום הסוגריים (דף "החלטות הנהלה"), ולחתום שוב'%', '.join(f));continue
		g=fingerprint([M,S or'']+T);o='approved'if g==A['fp']else'approved_modified';B.update(approved_text={'position':M,'wording':S,'effects':T},approved_fp=g,approved_at=I,signer=G[E]['name'],role=G[E]['role'])
		if A['legal_review']and not(U and V):B.update(status='pending_legal_review',legal_review_done_by=U,legal_review_done_at=V,reason='טעון בדיקה משפטית: לא נרשמו שם הבודק ותאריך הבדיקה ("נבדק בידי:", "תאריך הבדיקה:")');continue
		B.update(status=o,legal_review_done_by=U,legal_review_done_at=V,policy_claim=not P)
	p={'kind':'signature','token':D['token'],'signed_sha256':O,'signed_copy':O[:12]+'.docx','received_at':I,'evidence':{'received_via':Y,'upload_ref':Z},'simulated':P,'signers':G,'choices':b,'warnings':J,'counts':{A:sum(1 for B in Q.values()if B['status']==A)for A in('approved','approved_modified','pending_choice','pending_legal_review','open','not_signed')}};return{'cells':Q,'record':p,'warnings':J}
def _existing_records(records_dir):
	D=records_dir;A=[];B=long_path(D)
	if not os.path.isdir(B):return A
	for C in sorted(os.listdir(B)):
		if re.match('APR-\\d{4}\\.json$',C):
			with io.open(os.path.join(B,C),encoding='utf-8')as E:A.append((os.path.join(D,C),json.load(E)))
	return A
def save_record(records_dir,signed_path,result,supersedes=None,reason=None):
	O=result;N=signed_path;F=reason;E=records_dir;B=supersedes;A=O['record'];H=_existing_records(E);D=[(C,B)for(C,B)in H if B.get('signed_sha256')==A['signed_sha256']and not B.get('superseded_by')];I=[A for(B,A)in D if S.is_legacy_record(A)]
	if I and not S.is_legacy_record(A)and not B and len(I)==len(D):B,F=I[-1].get('record_id'),F or'העלאה חוזרת אחרי רשומה ישנה בלי ראיה'
	for(J,C)in D:
		if C.get('evidence')==A.get('evidence')and C.get('simulated')==A.get('simulated'):return J
	if D and not(B and F):raise IngestRefused('הקובץ החתום הזה כבר נקלט (%s) עם ראיה אחרת. קליטה חוזרת רק עם supersedes ונימוק.'%', '.join(B.get('record_id')or os.path.basename(A)for(A,B)in D))
	Q=os.path.join(E,A['signed_copy']);P.check_write_path(Q);os.makedirs(E,exist_ok=True);T,G=os.path.abspath(N),os.path.abspath(Q)
	if os.path.normcase(T)!=os.path.normcase(G):
		if not(os.path.exists(G)and sha256_file(G)==A['signed_sha256']):shutil.copyfile(long_path(N),G)
	R=1+len(H);K=os.path.join(E,'APR-%04d.json'%R);P.check_write_path(K);L=dict(A,record_id='APR-%04d'%R,cells=O['cells'])
	if B:
		L.update(supersedes=B,supersede_reason=F)
		for(J,C)in H:
			if C.get('record_id')==B:
				C['superseded_by']=L['record_id']
				with io.open(J,'w',encoding='utf-8')as M:json.dump(C,M,ensure_ascii=False,indent=1)
	with io.open(K,'w',encoding='utf-8')as M:json.dump(L,M,ensure_ascii=False,indent=1)
	return K
def current_record(records_dir):A=[(B,A)for(B,A)in _existing_records(records_dir)if not A.get('superseded_by')];return A[-1]if A else(None,None)
def record_cells(record):return S.effective_cells(record)
def migrate_legacy_record(path):
	B=path
	with io.open(long_path(B),encoding='utf-8')as C:A=json.load(C)
	if not S.is_legacy_record(A)or A.get('reupload_notice'):return False,None
	A['legacy']=True;A['simulated']=True;A['cells']=S.effective_cells(A);A['reupload_notice']=S.REUPLOAD_NOTICE;A.setdefault('evidence',{'received_via':A.get('received_via'),'upload_ref':A.get('upload_ref')});P.check_write_path(B);D=B+'.tmp'
	with io.open(D,'w',encoding='utf-8')as C:json.dump(A,C,ensure_ascii=False,indent=1)
	os.replace(D,B);return True,S.REUPLOAD_NOTICE
def merge_prior(result,prior_cells):
	A=result;B=0
	for(D,E)in(A.get('cells')or{}).items():
		C=(prior_cells or{}).get(D)
		if E.get('status')=='not_signed'and C and S.cell_counts(C)and C.get('approved_fp')==E.get('issued_fp'):A['cells'][D]=dict(C,carried_forward=True);B+=1
	if B and A.get('record'):A['record']['counts']=_counts(A['cells']);A['record']['carried_forward']=B
	return B
CHAT_VIA='chat_reply'
BATCH_MAX=8
STRONG_CORPUS='signed','company_forms'
MIN_STRONG_DOCS=2
STAGES='batch','decisions','questions','topics'
QUEUE_FILE='approval-queue-%s.json'
TEXT_KINDS='text_edited','text_added','text_deleted','our_change_rejected'
APPROVED_STATUSES='approved','approved_modified'
_TRACK_WORDS={'green':('ירוק','green','נדרוש'),'yellow':('צהוב','yellow','נסכים'),'red':('אדום','red')}
_APPROVE='לאשר','מאשרת','מאשר','מאושר','אישור','approve','approved','accept','accepted'
_NEGATE='לא לאשר','לא מאשר','אל תאשר','לא אישור','not approve',"don't approve",'do not approve','reject','not accept',"don't accept",'do not accept'
_REVIEWED='נבדק','נבדקה','reviewed'
_SKIP='לדלג','דלג','skip'
_LAWYER_LATER='לעורך דין','לבדיקת עורך דין','for a lawyer','lawyer later'
REASON_LAWYER_LATER='מחכה לבדיקה של עורך דין, לבקשת המאשר'
_ALL='הכול','הכל','כל המנה','all'
_EXCEPT='חוץ מ','למעט','except'
_CHANGE=re.compile('^(?:לשנות|שינוי|change)\\s*([^:]{0,20}):\\s*(.+)$',re.S|re.I)
_NUM=re.compile('^\\s*(\\d{1,2})\\s*[.):\\-]?\\s+(.+)$',re.S)
_SPLIT=re.compile('\\s*[,;]\\s*(?=\\d{1,2}\\s*[.):\\-]?\\s+\\S)')
Q={'he':{'head':'אישור המדיניות','batch':'עמדות ירוקות שנשענות על המסמכים שלכם, כל אחת לפחות בשני מסמכים ({n} עמדות). ההמלצה: לאשר את כולן במנה אחת. הנוסח של כל עמדה הוא הנוסח שחוזר במסמכים שלכם, והוא מופיע במלואו בפלייבוק.','batch_line':'{n}. {topic} (סעיף {num}) · {pos} · {docs} מסמכים','reply_batch':'לתשובה: "לאשר הכול", "לאשר הכול חוץ מ-3, 7" (מה שהוצא עובר לבדיקה אחת אחת), או "לדלג על המנה".','decisions':'מספרים שההנהלה צריכה לקבוע ({n}). אלה ערכים עסקיים, ולא נוסח משפטי, ולכל אחד מוצע מי מחליט. הערך נכתב בנוסח במקום הסוגריים, ואת העמדה עצמה מאשרים אחר כך עם שאר העמדות.','proposal':'   מה המדיניות מציעה: {p}','owner':'   מי מחליט, לפי ההצעה: {o}','decision_head':'{n}. {q} (סעיף {num})','reply_decisions':'לתשובה, שורה לכל ערך: "1 לשנות: <הערך>", "2 לאשר" (כשאין ערך לקבוע), או "3 לדלג".','questions':'שאלות פתוחות שחוסמות את אישור הנושא שלהן ({n}).','option':'   {k}) {o}','rec':'   ההמלצה של Areo: {r}','reply_questions':'לתשובה, שורה לכל שאלה: "1 אפשרות 2", או "1 לדלג".','topics':'נושאים לבדיקה אחת אחת ({n} נושאים, {m} עמדות).','topic_head':'{n}. {topic} (סעיף {num}) · חשיבות: {imp}','tracks':{'green':'מקובל עלינו (ירוק)','yellow':'אפשר להתגמש (צהוב)','red':'לא מסכימים (אדום)'},'track':'   {label}: {pos}','wording':'   הנוסח שיוחל, מילה במילה: {w}','cure':'   הנוסח שנשיב, מילה במילה: {w}','flags':'   לתשומת לבכם: {f}','legal':'   כדאי שעורך דין יעבור על זה','assume':'   הנחה (אישור העמדה מאשר גם אותה): {a}','reply_topics':'לתשובה, שורה לכל נושא: "1 לאשר", "2 לשנות צהוב: <הנוסח>", "3 לדלג", ובנושא שעורך דין צריך לעבור עליו, אחרי שעבר: "4 נבדק ולאשר". אפשר גם "לאשר הכול".','updates':'עדכונים למדיניות מהעסקאות ({n}): מה שעורך הדין שינה ביד לפני המשלוח, ומה שהוחלט מעבר למדיניות. עדכון שמאשרים נכנס למדיניות כעמדה מאושרת.','update_head':'{n}. {topic} (סעיף {num}) · {label}','event':'   {deal}, {clause}: {what}','current':'   היום במדיניות: {w}','proposed':'   מוצע: {w}','no_proposed':'   אין נוסח מוצע מילה במילה: לעדכון כתבו "לשנות: <הנוסח>".','reply_updates':'לתשובה, שורה לכל עדכון: "1 לאשר", "2 לשנות: <הנוסח>", או "3 לדלג".','waiting':'{n} עמדות מחכות למספר שההנהלה תקבע במקום הסוגריים.','info_q':'שאלה פתוחה שנסגרת רק בעדכון המדיניות, ועד אז אי אפשר לאשר את המדיניות כולה: {q}','more':'אחרי המנה הזו ממתינים עוד {n} פריטים.','empty':'אין עמדות שממתינות לאישור.','ignored':'לא הוצעו: {a} שינויים שאינם נוגעים בכלל של הפלייבוק, {b} שינויים בהערות לצד השני.','rec_company':'לאשר: העמדה חוזרת ב-{k} מסמכים שלכם.','rec_areo':'לאשר רק אם הנוסח משקף את מה שאתם מוכנים לתת: זו המלצה של Areo, ולא נוסח מהמסמכים שלכם.','rec_market':'לאשר אם הנקודה בשוק מתאימה לכם: העמדה נגזרה ממקורות שוק ציבוריים.','rec_weak':'לבדוק לפני אישור: יש מעט דוגמאות מההסכמים שלכם ({why}).','rec_statute':'לאשר אחרי שמוודאים שהדרישה בדין חלה עליכם.','rec_legal':'לאשר אחרי שעורך דין עבר על זה, בתשובה "נבדק ולאשר".','weak_docs':'פחות משני מסמכים','weak_unverified':'מקור שעוד לא אימתנו','weak_assume':'נשענת על הנחה','weak_corpus':'המסמכים אינם הסכמים חתומים של החברה','rec_update':'חזר ב-{k} עסקאות, ולכן מועמד לעדכון. כדאי לכתוב נוסח כללי, בלי פרטי העסקה ("לשנות").','rec_update_skip':'עסקה אחת היא נקודת מידע אחת, ולא מדיניות: מומלץ לדלג, ולחזור לזה אם יחזור בעסקה נוספת.','rec_adapt':'התאמה של הנוסח לעסקה הזו (דין, מטבע, כינויים), ולא שינוי מדיניות: מומלץ לדלג.','ev_text_edited':'שונה ביד לפני המשלוח. הופק: {b}. נשלח: {a}','ev_text_added':'נוסף ביד לפני המשלוח: {a}','ev_text_deleted':'נמחק ביד לפני המשלוח: {b}','ev_our_change_rejected':'השינוי שלנו בוטל ביד לפני המשלוח. הופק: {b}. נשלח: {a}','ev_accepted_red':'התקבל נוסח שהפלייבוק מסווג כאדום: {a}','ev_decided_outside':'הכרעה מפורשת בנושא שהפלייבוק לא הכריע בו: {a}','ev_red_line_exception':'חריגה מקו אדום שאושרה בעסקה: {a}','ev_adaptation':'התאמה של נוסח הפלייבוק לעסקה: {a}'},'en':{'head':'Policy approval','batch':'Green positions that rest on your own documents, each in at least two documents ({n} positions). Recommendation: approve them all in one batch. The wording of each position is the wording that recurs in your documents, and it appears in full in the playbook.','batch_line':'{n}. {topic} (clause {num}) · {pos} · {docs} documents','reply_batch':'To answer: "approve all", "approve all except 3, 7" (what is excluded moves to one-by-one review), or "skip the batch".','decisions':'Numbers for management to set ({n}). These are business values, not legal wording, and each has a proposed owner. The value goes into the wording in place of the brackets, and you approve the position itself later with the other positions.','proposal':'   What the policy proposes: {p}','owner':'   Who decides, as proposed: {o}','decision_head':'{n}. {q} (clause {num})','reply_decisions':'To answer, one line per value: "1 change: <the value>", "2 approve" (when there is no value to set), or "3 skip".','questions':'Open questions that block approval of their topic ({n}).','option':'   {k}) {o}','rec':'   Areo recommendation: {r}','reply_questions':'To answer, one line per question: "1 option 2", or "1 skip".','topics':'Topics for one-by-one review ({n} topics, {m} positions).','topic_head':'{n}. {topic} (clause {num}) · Importance: {imp}','tracks':{'green':'We accept (green)','yellow':'We can flex (yellow)','red':"We don't agree (red)"},'track':'   {label}: {pos}','wording':'   Wording to apply, verbatim: {w}','cure':'   Wording we answer with, verbatim: {w}','flags':'   Note: {f}','legal':'   A lawyer should review this','assume':'   Assumption (approving the position confirms it): {a}','reply_topics':'To answer, one line per topic: "1 approve", "2 change yellow: <the wording>", "3 skip", and for a topic a lawyer needs to review, once they have: "4 reviewed and approve". "approve all" also works.','updates':'Policy updates from deals ({n}): what the lawyer changed by hand before sending, and what was decided beyond the policy. An update you approve enters the policy as an approved position.','update_head':'{n}. {topic} (clause {num}) · {label}','event':'   {deal}, {clause}: {what}','current':'   In the policy today: {w}','proposed':'   Proposed: {w}','no_proposed':'   No verbatim wording proposed: to update, write "change: <the wording>".','reply_updates':'To answer, one line per update: "1 approve", "2 change: <the wording>", or "3 skip".','waiting':'{n} positions are waiting for management to set the number in brackets.','info_q':'An open question that closes only in a policy update, and until then the whole policy cannot be approved: {q}','more':'{n} more items are waiting after this batch.','empty':'No positions are waiting for approval.','ignored':'Not proposed: {a} changes that touch no playbook rule, {b} changes to comments to the other side.','rec_company':'Approve: the position recurs in {k} of your documents.','rec_areo':'Approve only if the wording reflects what you are prepared to give: this is an Areo recommendation, not wording from your documents.','rec_market':'Approve if the market point suits you: the position was derived from public market sources.','rec_weak':'Check before approving: there are few examples from your agreements ({why}).','rec_statute':'Approve after confirming the legal requirement applies to you.','rec_legal':'Approve once a lawyer has reviewed it, by answering "reviewed and approve".','weak_docs':'fewer than two documents','weak_unverified':'a source we have not verified yet','weak_assume':'rests on an assumption','weak_corpus':"the documents are not the company's signed agreements",'rec_update':'Recurred in {k} deals, so it is a candidate for an update. Write general wording, without the deal details ("change").','rec_update_skip':'One deal is one data point, not a policy: skipping is recommended, and coming back to it if it recurs in another deal.','rec_adapt':'An adaptation of the wording to this deal (law, currency, defined terms), not a policy change: skipping is recommended.','ev_text_edited':'Edited by hand before sending. Produced: {b}. Sent: {a}','ev_text_added':'Added by hand before sending: {a}','ev_text_deleted':'Deleted by hand before sending: {b}','ev_our_change_rejected':'Our change was undone by hand before sending. Produced: {b}. Sent: {a}','ev_accepted_red':'Wording the playbook classifies as red was accepted: {a}','ev_decided_outside':'An explicit decision on a topic the playbook did not decide: {a}','ev_red_line_exception':'A red-line exception approved in the deal: {a}','ev_adaptation':'An adaptation of the playbook wording to the deal: {a}'}}
class ReplyError(ValueError):0
def _ql(lang):return'en'if str(lang or'').lower().startswith('en')else'he'
def _counts(cells):return{A:sum(1 for B in cells.values()if B.get('status')==A)for A in('approved','approved_modified','pending_choice','pending_legal_review','open','not_signed','skipped')}
def _rules(model):return{A['rule_id']:A for A in model.get('rules')or[]if A.get('rule_id')}
def _views(model,lang):
	C=lang;B=model;G=A.role_lines(B,C);H=A.unverified_index(B);I=A.management_decisions(B,C);D={}
	for E in B.get('rules')or[]:
		for F in S.TRACKS:D[S.cell_key(E['rule_id'],F)]=A.cell_view(B,E,F,C,H,G,I)
	return D
def _cell_done(cell,view):return bool(S.cell_counts(cell)and cell.get('approved_fp')in(None,view['fp']))
def _unverified(view):return any(A.startswith(('ממצא לא מאומת','Unverified finding'))for A in view['flags'])
def _weak_reasons(model,rule,track,view,lang):
	B=Q[_ql(lang)];C=(rule.get('traffic_light')or{}).get(track)or{};A=[]
	if len(C.get('evidence')or[])<MIN_STRONG_DOCS:A.append(B['weak_docs'])
	if _unverified(view):A.append(B['weak_unverified'])
	if view['assumptions']:A.append(B['weak_assume'])
	if S.corpus_status(model)not in STRONG_CORPUS:A.append(B['weak_corpus'])
	return A
def is_strong(model,rule,track,view,blocked_rules=()):C=track;A=view;D=(rule.get('traffic_light')or{}).get(C)or{};B=D.get('basis');return bool(C=='green'and B and B not in S.NON_COMPANY_BASES and B!='statute'and S.corpus_status(model)in STRONG_CORPUS and len(D.get('evidence')or[])>=MIN_STRONG_DOCS and not(A['legal']or A['slots']or A['assumptions']or _unverified(A))and rule['rule_id']not in blocked_rules)
def _recommendation(model,rule,track,view,lang):
	D=track;B=view;A=Q[_ql(lang)];E=(rule.get('traffic_light')or{}).get(D)or{};C=E.get('basis')
	if B['legal']:return'legal',A['rec_legal']
	F=_weak_reasons(model,rule,D,B,lang)
	if C=='areo_proposal':return'review',A['rec_areo']
	if C=='statute':return'review',A['rec_statute']
	if C=='market_standard'and not _unverified(B):return'review',A['rec_market']
	if F:return'review',A['rec_weak'].format(why=', '.join(F))
	return'approve',A['rec_company'].format(k=len(E.get('evidence')or[]))
def _decision_done(model,d,rules):
	if any(A.get('field')=='management_decision'and A.get('rule_id')==d.get('rule_id')for A in model.get('change_log')or[]):return True
	if d.get('slots'):A=json.dumps((rules.get(d.get('rule_id'))or{}).get('traffic_light')or{},ensure_ascii=False);return not any(B in A for B in d['slots'])
	return False
def queue_state(model,cells,lang='he',revisit=False,demoted=(),skipped=()):
	H=revisit;D=lang;C=model;D=_ql(D);E=_rules(C);F=_views(C,D);G=S.open_decisive(C);Q={A.get('rule_id')for A in G if A.get('rule_id')and A.get('rule_id')!='GLOBAL'};I,J=[],0
	for(B,K)in F.items():
		L=(cells or{}).get(B)or{}
		if _cell_done(L,K):continue
		if L.get('status')=='skipped'and not H:continue
		if K['slots']:J+=1;continue
		I.append(B)
	M,N=[],{}
	for B in I:
		O,Z,R=B.split('|')
		if B not in demoted and is_strong(C,E[O],R,F[B],Q):M.append(B)
		else:N.setdefault(O,[]).append(B)
	P=set()if H else set(skipped or());T=[A for A in A.management_decisions(C,D)if not _decision_done(C,A,E)and'decision:%s'%A.get('rule_id')not in P];U=[A for A in G if A.get('options')and'question:%s'%(A.get('id')or A.get('queue_id'))not in P];V=[A for A in G if not A.get('options')];W={'critical':0,'high':1,'medium':2,'low':3};X={B:A for(A,B)in enumerate(E)};Y=sorted(N.items(),key=lambda kv:(W.get(str(E[kv[0]].get('importance')or'').lower(),4),X[kv[0]]));return{'batch':M,'decisions':T,'questions':U,'topics':Y,'info':V,'waiting':J,'views':F}
def _cell_item(model,key,view,lang):B=model;A=view;D,H,C=key.split('|');E=_rules(B)[D];F,G=_recommendation(B,E,C,A,lang);return{'key':key,'track':C,'fp':A['fp'],'position':A['position'],'wording':A['wording'],'effects':A['effects'],'flags':A['flags'],'legal':A['legal'],'assumptions':A['assumptions'],'rec_code':F,'recommendation':G}
def make_batch(model,cells,lang='he',stage=None,revisit=False,demoted=(),skipped=()):
	L=stage;I=model;A=queue_state(I,cells,lang,revisit,demoted,skipped);J=_rules(I)
	for E in[L]if L else STAGES:
		B,G=[],0
		if E=='batch'and A['batch']:
			for(F,H)in enumerate(A['batch'],1):C=H.split('|')[0];O=(J[C].get('traffic_light')or{}).get('green')or{};B.append({'n':F,'kind':'cell','rule_id':C,'topic':J[C].get('topic_name')or'','key':H,'track':'green','fp':A['views'][H]['fp'],'position':A['views'][H]['position'],'docs':len(O.get('evidence')or[])})
		elif E=='decisions'and A['decisions']:
			for(F,P)in enumerate(A['decisions'][:BATCH_MAX],1):B.append(dict(P,n=F,kind='decision'))
			G=max(0,len(A['decisions'])-BATCH_MAX)
		elif E=='questions'and A['questions']:
			for(F,D)in enumerate(A['questions'][:BATCH_MAX],1):B.append({'n':F,'kind':'question','qid':D.get('id')or D.get('queue_id'),'rule_id':D.get('rule_id'),'question':D.get('question')or'','options':list(D.get('options')or[]),'recommendation':D.get('recommendation')or''})
			G=max(0,len(A['questions'])-BATCH_MAX)
		elif E=='topics'and A['topics']:
			M=0
			for(C,K)in A['topics']:
				if B and M+len(K)>BATCH_MAX:break
				N=J[C];Q=[_cell_item(I,B,A['views'][B],lang)for B in K];B.append({'n':len(B)+1,'kind':'topic','rule_id':C,'topic':N.get('topic_name')or'','importance':N.get('importance')or'','cells':Q});M+=len(K)
			G=len(A['topics'])-len(B)
		if B:return{'stage':E,'items':B,'waiting':A['waiting'],'more':G,'info':[A.get('question')or''for A in A['info']]}
def _event_key(tid,source,ev):A=ev;B='|'.join(str(A)for A in(tid,source,A.get('clause_id'),A.get('kind'),A.get('round'),A.get('before'),A.get('after')));return hashlib.sha256(B.encode('utf-8')).hexdigest()[:12]
def deal_events(state,model):
	E=state;R=E.get('meta')or{};L=R.get('transaction_id')or'';I=_rules(model);J={A.get('clause_id'):A for A in E.get('clauses')or[]if isinstance(A,dict)};M,F=[],{'no_rule':0,'comment':0}
	def G(source,kind,rid,track,cl_id,before,after,proposed,rnd=None,date=None):B=source;A={'source':B,'kind':kind,'rule_id':rid,'track':track,'clause_id':cl_id,'round':rnd,'date':date,'before':before or'','after':after or'','proposed':(proposed or'').strip()or None,'transaction_id':L};A['key']=_event_key(L,B,A);M.append(A)
	for B in E.get('lawyer_overrides')or[]:
		if not isinstance(B,dict):continue
		C=[A for A in B.get('rule_ids')or[]if A in I]
		if not C:F['no_rule']+=1;continue
		if B.get('kind')not in TEXT_KINDS:F['comment']+=1;continue
		N=(J.get(B.get('clause_id'))or{}).get('track_match');G('lawyer_override',B['kind'],C[0],N if N in('green','yellow')else'green',B.get('clause_id'),B.get('produced_text')or B.get('before'),B.get('sent_text')or B.get('after'),B.get('sent_text')if B['kind']!='our_change_rejected'else None,B.get('round'),B.get('date'))
	O=set()
	for D in E.get('exception_log')or[]:
		if not isinstance(D,dict):continue
		A=J.get(D.get('clause_id'))or{};C=[A for A in D.get('rule_ids')or A.get('rule_ids')or[]if A in I]
		if not C:F['no_rule']+=1;continue
		P='adaptation'if D.get('type')=='adaptation'else'red_line_exception';G('exception_log',P,C[0],'yellow',D.get('clause_id'),A.get('playbook_default'),D.get('what')or D.get('inserted')or'',A.get('agreed_text')if P!='adaptation'else None,None,D.get('date'));O.add(D.get('clause_id'))
	for(K,A)in J.items():
		C=[A for A in A.get('rule_ids')or[]if A in I]
		if not C or K in O:continue
		Q=A.get('user_decision')or{};H=A.get('agreed_text')or A.get('current_text')or''
		if A.get('op')=='accept'and A.get('track_match')=='red':G('clause','accepted_red',C[0],'yellow',K,A.get('playbook_default'),H,H,A.get('accepted_in_round')or A.get('decided_in_round'))
		elif Q.get('answer_kind')=='explicit'and A.get('track_match')not in('green','yellow','red'):G('clause','decided_outside',C[0],'yellow',K,A.get('playbook_default'),H,H,A.get('decided_in_round'),str(Q.get('recorded_at')or'')[:10]or None)
	return M,F
def deal_updates(states,model,lang='he'):
	J=lang;E=model;J=_ql(J);K=Q[J];V=E.get('family_id');X={A.get('key')for A in E.get('deal_feedback')or[]};M={}
	for N in E.get('deal_feedback')or[]:M.setdefault((N.get('rule_id'),N.get('track')),set()).add(N.get('transaction_id'))
	W,L,C={},[],{'no_rule':0,'comment':0}
	for O in states:
		P=((O.get('meta')or{}).get('position')or{}).get('playbook_family');Y=(O.get('meta')or{}).get('transaction_id')or''
		if P and V and P!=V:L.append('%s: %s'%(Y,P));continue
		F,Z=deal_events(O,E)
		for D in C:C[D]+=Z[D]
		for B in F:
			M.setdefault((B['rule_id'],B['track']),set()).add(B['transaction_id'])
			if B['key']not in X:W.setdefault((B['rule_id'],B['track']),[]).append(B)
	R=_rules(E);a={B:A for(A,B)in enumerate(R)};G=[]
	for((H,I),F)in sorted(W.items(),key=lambda kv:(a[kv[0][0]],S.TRACKS.index(kv[0][1]))):
		b=(R[H].get('traffic_light')or{}).get(I)or{};D=len({A for A in M.get((H,I),())if A})
		if all(A['kind']=='adaptation'for A in F):T,U='skip',K['rec_adapt']
		elif D>=2:T,U='update',K['rec_update'].format(k=D)
		else:T,U='skip',K['rec_update_skip']
		c=next((A['proposed']for A in reversed(F)if A.get('proposed')),None);G.append({'n':len(G)+1,'kind':'update','rule_id':H,'track':I,'topic':R[H].get('topic_name')or'','events':F,'proposed':c,'current':A.track_wording(I,b,J),'deals':D,'rec_code':T,'recommendation':U,'key':S.cell_key(H,I)})
	if C['no_rule']or C['comment']:L.append(K['ignored'].format(a=C['no_rule'],b=C['comment']))
	if not G:return None,L
	return{'stage':'updates','items':G[:BATCH_MAX],'waiting':0,'info':[],'more':max(0,len(G)-BATCH_MAX)},L
def queue_path(records_dir,model):return os.path.join(records_dir,QUEUE_FILE%(model.get('family_id')or'family'))
def load_queue(records_dir,model):
	A=model;B=queue_path(records_dir,A)
	if os.path.exists(long_path(B)):
		with io.open(long_path(B),encoding='utf-8')as C:return json.load(C)
	return{'family_id':A.get('family_id'),'batches':[],'demoted':[]}
def save_queue(records_dir,model,data):
	B=records_dir;A=queue_path(B,model);P.check_write_path(A);os.makedirs(B,exist_ok=True)
	with io.open(A,'w',encoding='utf-8')as C:json.dump(data,C,ensure_ascii=False,indent=1)
	return A
def open_batch(queue):A=[A for A in queue.get('batches')or[]if A.get('status')=='open'];return A[-1]if A else None
def issue_batch(queue,batch,lang,today=None):
	B=queue;A=batch
	for C in B.get('batches')or[]:
		if C.get('status')=='open':C['status']='replaced'
	D='Q-%04d'%(1+len(B.get('batches')or[]));A=dict(A,batch_id=D,lang=_ql(lang),status='open',issued_at=today or _dt.date.today().isoformat());B.setdefault('batches',[]).append(A);return A
_PLAIN_FLAGS={'he':(('הצעת Areo','המלצה של Areo'),('ממצא לא מאומת','מקור שעוד לא אימתנו')),'en':(('Areo proposal','Areo recommendation'),('Unverified finding','A source we have not verified yet'))}
def _plain_flag(flag,lang):
	A=flag
	for(B,C)in _PLAIN_FLAGS[_ql(lang)]:A=A.replace(B,C)
	return A
def _short(s,n=220):s=norm_text(s);return s if len(s)<=n else s[:n-1].rstrip()+'…'
def render_batch(batch,model=None,lang='he'):
	K=model;H=lang;G=batch;H=_ql(H);B,M=Q[H],A.SHEETS[H];P=A.role_lines(K,H)if K else[];I=G['stage'];F=G['items'];D=[B['head']];L=lambda it:it.get('num')or(A.display_num(K,it.get('rule_id'))if K else'')or'-'
	if I=='batch':
		D.append(B['batch'].format(n=len(F)))
		for C in F:D.append(B['batch_line'].format(n=C['n'],num=L(C),topic=C['topic'],pos=C['position'],docs=C['docs']))
		D.append(B['reply_batch'])
	elif I=='decisions':
		D.append(B['decisions'].format(n=len(F)))
		for C in F:
			D.append(B['decision_head'].format(n=C['n'],q=C['question'],num=L(C)))
			if C.get('proposal'):D.append(B['proposal'].format(p=' / '.join(C['proposal'].split('\n'))))
			D.append(B['owner'].format(o=C.get('owner')or''))
		D.append(B['reply_decisions'])
	elif I=='questions':
		D.append(B['questions'].format(n=len(F)))
		for C in F:
			D.append('%d. %s'%(C['n'],C['question']))
			for(R,S)in enumerate(C['options'],1):D.append(B['option'].format(k=R,o=S))
			if C.get('recommendation'):D.append(B['rec'].format(r=C['recommendation']))
		D.append(B['reply_questions'])
	elif I=='topics':
		D.append(B['topics'].format(n=len(F),m=sum(len(A['cells'])for A in F)))
		for C in F:
			T=M['importance'].get(str(C.get('importance')or'').lower(),C.get('importance')or'');D.append(B['topic_head'].format(n=C['n'],num=L(C),topic=C['topic'],imp=T));N=[]
			for E in C['cells']:
				D.append(B['track'].format(label=B['tracks'][E['track']],pos=E['position']));D.append(B['cure'if E['track']=='red'else'wording'].format(w=E['wording']or M['no_wording']))
				for(O,U)in P:
					if(E.get('effects')or{}).get(O):D.append('   '+U+E['effects'][O])
				if E.get('flags'):D.append(B['flags'].format(f=' · '.join(_plain_flag(A,H)for A in E['flags'])))
				if E.get('legal'):D.append(B['legal'])
				for V in E.get('assumptions')or[]:D.append(B['assume'].format(a=V))
				if E['recommendation']not in N:N.append(E['recommendation'])
			D.append(B['rec'].format(r=' '.join(N)))
		D.append(B['reply_topics'])
	elif I=='updates':
		D.append(B['updates'].format(n=len(F)))
		for C in F:
			D.append(B['update_head'].format(n=C['n'],num=L(C),topic=C['topic'],label=B['tracks'][C['track']]))
			for J in C['events']:W=B['ev_'+J['kind']].format(b=_short(J.get('before')),a=_short(J.get('after')));D.append(B['event'].format(deal=J.get('transaction_id')or'',clause=J.get('clause_id')or'',what=W))
			D.append(B['current'].format(w=C.get('current')or M['no_wording']));D.append(B['proposed'].format(w=C['proposed'])if C.get('proposed')else B['no_proposed']);D.append(B['rec'].format(r=C['recommendation']))
		D.append(B['reply_updates'])
	if G.get('more'):D.append(B['more'].format(n=G['more']))
	if G.get('waiting'):D.append(B['waiting'].format(n=G['waiting']))
	for X in G.get('info')or[]:D.append(B['info_q'].format(q=X))
	return'\n'.join(D)
def _track_of(s):s=(s or'').lower();A=[A for(A,B)in _TRACK_WORDS.items()if any(A in s for A in B)];return A[0]if len(A)==1 else None
def _has(s,words):A=s.lower();return any(B in A for B in words)
def _classify(cmd,item,lang='he'):
	B=item;A=cmd;A=A.strip().strip('"״\'').strip();E=_CHANGE.match(A)
	if E:
		D=E.group(2).strip().strip('"״').strip()
		if not D:raise ReplyError('"לשנות" בלי נוסח בפריט %d'%B['n'])
		if B.get('kind')=='decision'and'='not in D:
			for G in B.get('context')or():value_for_slot(D,G,lang)
		return{'action':'change','track':_track_of(E.group(1)),'text':D}
	if B['kind']=='question':
		F=re.match('^(?:אפשרות|option)?\\s*(\\d{1,2})$',A,re.I)
		if F:
			C=int(F.group(1))
			if not 1<=C<=len(B['options']):raise ReplyError('אין אפשרות %d בשאלה %d'%(C,B['n']))
			return{'action':'choose','option':C}
		for(C,H)in enumerate(B['options'],1):
			if norm_text(A)==norm_text(H):return{'action':'choose','option':C}
	if _has(A,_NEGATE):raise ReplyError('תשובה שלילית בפריט %d: כדי לא לאשר, "לשנות: <הנוסח>" או "לדלג"'%B['n'])
	if _has(A,_LAWYER_LATER):return{'action':'skip','lawyer_later':True}
	if _has(A,_SKIP):return{'action':'skip'}
	if _has(A,_APPROVE):return{'action':'approve','reviewed':_has(A,_REVIEWED),'track':_track_of(A)}
	raise ReplyError('לא הבנתי את התשובה לפריט %d: "%s"'%(B['n'],_short(A,60)))
def parse_reply(reply,batch):
	H=batch;B={A['n']:A for A in H['items']};F=[A.strip()for A in(reply or'').splitlines()if A.strip()]
	if not F:raise ReplyError('תשובה ריקה')
	if len(F)==1 and not _NUM.match(F[0]):
		A=norm_text(F[0]);N=_has(A,_ALL)or'המנה'in A or'batch'in A.lower()
		if N and not _CHANGE.match(A):
			if _has(A,_NEGATE):raise ReplyError('תשובה שלילית לכל המנה: "לדלג על המנה", או תשובה לכל פריט')
			if _has(A,_SKIP):return{A:{'action':'skip'}for A in B}
			if _has(A,_APPROVE):
				I=set()
				for O in _EXCEPT:
					L=A.lower().find(O)
					if L>=0:I={int(A)for A in re.findall('\\d{1,2}',A[L:])}
				M=sorted(I-set(B))
				if M:raise ReplyError('אין במנה פריט %s'%', '.join(map(str,M)))
				P=_has(A,_REVIEWED);return{A:{'action':'except'}if A in I else{'action':'approve','reviewed':P,'track':None}for A in B}
		if len(B)==1:return{1:_classify(A,B[1],H.get('lang')or'he')}
		raise ReplyError('לא ברור לאיזה פריט התשובה מתייחסת. כתבו את מספר הפריט בתחילת השורה, או "לאשר הכול"')
	J={}
	for Q in F:
		K,G=[],None
		for C in _SPLIT.split(Q):
			if G is not None:G+=', '+C;continue
			D=_NUM.match(C)
			if D and _CHANGE.match(D.group(2).strip()):G=C
			else:K.append(C)
		if G is not None:K.append(G)
		for C in K:
			D=_NUM.match(C)
			if not D:raise ReplyError('שורה בלי מספר פריט: "%s"'%_short(C,60))
			E=int(D.group(1))
			if E not in B:raise ReplyError('אין במנה פריט %d'%E)
			if E in J:raise ReplyError('שתי תשובות לפריט %d'%E)
			J[E]=_classify(D.group(2),B[E],H.get('lang')or'he')
	return J
def set_track_wording(t,track,text,lang='he'):
	B=text
	if track=='yellow':
		C=t.get('fallback_wording')
		if isinstance(C,dict)and C.get('text'):D=C['text'];C['text']=B;return'fallback_wording.text',D
		if isinstance(C,str)and C.strip():t['fallback_wording']=B;return'fallback_wording',C
	E=t.get('proposed_clause')
	if isinstance(E,dict):D=A.track_wording('green',{'proposed_clause':E},lang);F='he'if re.search('[\u0590-\u05ff]',B)else'en';t['proposed_clause']={'he':B if F=='he'else'','en':B if F=='en'else'','source_language':F};return'proposed_clause',D
	if not E and t.get('preferred_wording'):D=t['preferred_wording'];t['preferred_wording']=B;return'preferred_wording',D
	t['proposed_clause']=B;return'proposed_clause',E or''
def _fill_slots(text,mapping,units=None):
	B=text
	for(C,G)in mapping.items():
		H=(units or{}).get(C);I=_VALUE.match(G or'')if H else None
		if not I or C not in B:B=B.replace(C,G);continue
		D,E=[],0
		while True:
			F=B.find(C,E)
			if F<0:D.append(B[E:]);break
			D.append(B[E:F]);J=B[F+len(C):];D.append(I.group(1)if J[:1].isspace()and A.unit_of(J[:24])==H else G);E=F+len(C)
		B=''.join(D)
	return B
def _replace_slots(obj,mapping,units=None):
	E=units;D=mapping;A=obj;C=0
	if isinstance(A,dict):F=list(A.items())
	elif isinstance(A,list):F=list(enumerate(A))
	else:return 0
	for(H,B)in F:
		if isinstance(B,str):
			G=_fill_slots(B,D,E)
			if G!=B:A[H]=G;C+=1
		else:C+=_replace_slots(B,D,E)
	return C
_SLOT_TEXT_FIELDS='position','proposed_clause','fallback_wording','fallback_steps','preferred_wording','company_effect','role_effects'
_VALUE=re.compile('^\\s*([-+]?\\d+(?:[.,]\\d+)?)\\s*(.*)$',re.S)
_UNIT_CONFLICT={'he':'הערך "{v}" ביחידה אחרת מהמשפט: "{s}". היחידה בו היא {u}. כתבו את המספר ב{u}, או שנו את הנוסח ("לשנות ירוק: <הנוסח>")','en':'The value "{v}" uses a different unit from the sentence: "{s}". Its unit is {u}. Write the number in {u}, or change the wording ("change green: <the wording>")'}
def value_for_slot(value,ctx,lang='he'):
	D=value;B=ctx;C=(B or{}).get('unit');F=_VALUE.match(D or'')
	if not C or not F:return D
	E,G=F.group(1),F.group(2).strip();H=A.unit_of(G)if G else None
	if H and H!=C:raise ReplyError(_UNIT_CONFLICT[_ql(lang)].format(v=D,s=B.get('sentence')or B.get('slot'),u=A.UNIT_NAMES[C][_ql(lang)]))
	if G and not H:return D
	if B.get('unit_where')=='after':return E
	if C=='percent':return E+'%'
	if C=='multiple':return E
	I=B.get('sentence')or B.get('slot')or'';return'%s %s'%(E,A.UNIT_NAMES[C]['he'if re.search('[\u0590-\u05ff]',I)else'en'])
def apply_decision_value(rule,slots,value,context=None,lang='he'):
	F=value;E=slots;E=list(dict.fromkeys(E or[]));F=(F or'').strip()
	if'='in F:
		C={}
		for I in re.split('\\s*;\\s*',F):
			if'='not in I:continue
			D,J=(A.strip()for A in I.split('=',1));D=D if D.startswith('[')else'[%s]'%D
			if D not in E or not J:raise ReplyError('אין בהחלטה סוגריים %s'%D)
			C[D]=J
	elif len(E)==1 or not re.search('[^\\W\\d_]',F):C={A:F for A in E}
	else:raise ReplyError('בהחלטה כמה ערכים (%s): כתבו "לשנות: [x]=ערך; [y]=ערך"'%', '.join(E))
	K={A.get('slot'):A for A in context or()if isinstance(A,dict)};C={A:value_for_slot(B,K.get(A),lang)for(A,B)in C.items()};L={A:(K.get(A)or{}).get('unit')for A in C};G=[]
	for(M,A)in(rule.get('traffic_light')or{}).items():
		if not isinstance(A,dict):continue
		for B in _SLOT_TEXT_FIELDS+tuple(A for A in A if A.startswith('as_')and A.endswith('_effect')):
			if B not in A:continue
			N=json.loads(json.dumps(A[B],ensure_ascii=False))
			if isinstance(A[B],str):
				H=_fill_slots(A[B],C,L)
				if H!=A[B]:A[B]=H;G.append((M,B,N,H))
			elif _replace_slots(A[B],C,L):G.append((M,B,N,A[B]))
	return G
def _bump(version):
	A=version
	try:B,C=str(A or'1.0').split('.')[:2];return'%d.%d'%(int(B),int(C)+1)
	except ValueError:return str(A or'1.0')+'.1'
def _approved_cell(view,roles,name,role,today,reviewed,modified,answer):
	D=reviewed;C=today;B=name;A=view;F=[A['effects'][B]for(B,C)in roles];E={'status':'approved_modified'if modified else'approved','policy_claim':True,'reason':None,'approved_text':{'position':A['position'],'wording':A['wording'],'effects':F},'approved_fp':A['fp'],'issued_fp':A['fp'],'approved_at':C,'signer':B,'role':role,'simulated':False,'legal_review_required':A['legal'],'legal_review_done_by':B if A['legal']and D else None,'legal_review_done_at':C if A['legal']and D else None,'assumptions_confirmed':[{'tag':'chat','text':A,'confirmed_by':B,'at':C}for A in A['assumptions']],'via':'chat','answer':answer}
	if A['slots']:E.update(status='pending_choice',policy_claim=False,reason='נשאר ערך שלא נקבע: %s (החלטות הנהלה)'%', '.join(A['slots']))
	elif A['legal']and not D:E.update(status='pending_legal_review',policy_claim=False,reason='טעון בדיקה משפטית: התשובה לא אמרה "נבדק"')
	return E
def apply_answers(model,batch,answers,approver,role=None,reply='',today=None,prior_cells=None,lang='he'):
	k=reply;T=role;L=approver;K=lang;J=batch;H=today;G=model;H=H or _dt.date.today().isoformat()
	if not _is_person_name(L or''):raise ReplyError('"%s" אינו שם מלא של אדם. כל תשובה נרשמת בשם המאשר'%(L or''))
	K=_ql(K);X=_rules(G);v=A.role_lines(G,K);l=_views(G,K);M={A:dict(B)for(A,B)in(prior_cells or{}).items()};f,g,m,n,o,Y,O=set(),[],{},[],[],[],[];p=str(G.get('version')or'1.0');q=_bump(p);I={'approved':0,'changed':0,'skipped':0,'pending':0,'decided':0,'chosen':0}
	def Z(rid,track,field,prev,new,reason,trigger,refs=()):O.append({'change_id':'CH-%s-%d'%(J.get('batch_id')or'Q',len(O)+1),'date':H,'version_from':p,'version_to':q,'rule_id':rid,'segment_id':None,'track':track,'field':field,'previous':prev,'new':new,'evidence_refs':list(refs),'reason':reason,'trigger':trigger,'decided_by':L,'decided_role':T,'via':J.get('batch_id')})
	def r(item_fp,key):
		if l[key]['fp']!=item_fp:g.append('%s: הנוסח השתנה מאז שהמנה הוצגה, ולכן התשובה לא נקלטה. הנושא יוצג שוב.'%key);return True
		return False
	def a(key,reviewed,modified,ans):
		C=reviewed;A=key;D=_views(G,K)[A];M[A]=_approved_cell(D,v,L,T,H,C,modified,ans);f.add(A)
		if M[A]['status']in APPROVED_STATUSES:
			I['approved']+=1
			if D['legal']and C:
				F,J,E=A.split('|')
				for B in X[F].get('legal_review_required')or[]:
					if isinstance(B,dict)and(B.get('track')==E or E in(B.get('tracks')or[])):B.update(checked_by=L,checked_at=H)
		else:I['pending']+=1
	def s(key,ans,lawyer_later=False):
		B=lawyer_later;A=key
		if not S.cell_counts(M.get(A)or{}):
			M[A]={'status':'skipped','policy_claim':False,'simulated':False,'skipped_by':L,'skipped_at':H,'via':'chat','answer':ans,'reason':REASON_LAWYER_LATER if B else'דולג בתור האישור'}
			if B:M[A]['lawyer_later']=True
			f.add(A)
		Y.append(A);I['skipped']+=1
	for(F,B)in sorted(((A['n'],A)for A in J['items']),key=lambda x:x[0]):
		C=answers.get(F)
		if not C or C['action']=='except':continue
		D=C['action'];b=C.get('text')or D
		if B['kind']=='cell':
			if r(B['fp'],B['key']):continue
			if D=='approve':a(B['key'],False,False,b)
			elif D=='skip':s(B['key'],b)
			else:raise ReplyError('במנת הירוקים: "לאשר הכול", "חוץ מ" או "לדלג". שינוי נוסח נעשה בבדיקה אחת אחת')
		elif B['kind']=='topic':
			c=[A['key']for A in B['cells']]
			if any(r(A['fp'],A['key'])for A in B['cells']):continue
			if D=='skip':
				for Q in c:s(Q,b,C.get('lawyer_later'))
				continue
			if D=='approve':
				t=[A for A in c if not C.get('track')or A.endswith('|'+C['track'])]
				if not t:raise ReplyError('בפריט %d אין מסלול %s'%(F,C['track']))
				for Q in t:a(Q,C.get('reviewed'),False,b)
				continue
			if D!='change':raise ReplyError('תשובה שאינה מתאימה לנושא בפריט %d'%F)
			E=C.get('track')or(B['cells'][0]['track']if len(c)==1 else None);P=S.cell_key(B['rule_id'],E)if E else None
			if P not in c:raise ReplyError('בפריט %d כמה מסלולים: כתבו "לשנות ירוק:", "לשנות צהוב:" או "לשנות אדום:"'%F)
			d=X[B['rule_id']]['traffic_light'][E];h,U=set_track_wording(d,E,C['text'],K);Z(B['rule_id'],E,h,U,C['text'],'שינוי נוסח בתור האישור','client_request');a(P,True,True,C['text']);I['changed']+=1
		elif B['kind']=='decision':
			V=X.get(B.get('rule_id'))
			if D=='skip':Y.append('decision:%s'%B.get('rule_id'));I['skipped']+=1;continue
			if D=='approve':
				if B.get('slots'):raise ReplyError('בהחלטה %d יש ערך לקבוע (%s): "לשנות: <הערך>"'%(F,', '.join(B['slots'])))
				N=None
			elif D=='change':N=C['text']
			else:raise ReplyError('תשובה שאינה מתאימה להחלטה %d'%F)
			if V is None:raise ReplyError('ההחלטה %d אינה שייכת לכלל בפלייבוק'%F)
			if N is not None and not B.get('slots'):
				for R in B.get('context')or():
					if isinstance(R,dict):value_for_slot(N,R,K)
			if N is not None and B.get('slots'):
				for(E,w,U,x)in apply_decision_value(V,B['slots'],N,B.get('context'),K):Z(V['rule_id'],E,w,U,x,'החלטת הנהלה: %s'%B['question'],'client_request')
			Z(V['rule_id'],None,'management_decision',B.get('proposal')or'',N if N is not None else'אושר כפי שהוצע',B['question'],'client_request');O[-1].update(question=B['question'],owner=B.get('owner'));n.append({'rule_id':V['rule_id'],'question':B['question'],'value':N,'owner':B.get('owner'),'decided_by':L,'role':T,'at':H});I['decided']+=1
		elif B['kind']=='question':
			if D=='skip':Y.append('question:%s'%B['qid']);I['skipped']+=1;continue
			if D!='choose':raise ReplyError('בשאלה %d בוחרים אפשרות: "%d אפשרות 1"'%(F,F))
			Q=C['option'];m[B['qid']]={'row':B.get('rule_id'),'index':Q-1,'text':B['options'][Q-1],'tag':'chat:%s'%J.get('batch_id'),'question':B['question']};I['chosen']+=1
		elif B['kind']=='update':
			W,E=B['rule_id'],C.get('track')or B['track'];y=['%s:%s'%(A.get('transaction_id'),A.get('clause_id'))for A in B['events']];i='skipped'
			if D=='approve'and not B.get('proposed'):raise ReplyError('בעדכון %d אין נוסח מוצע מילה במילה: "%d לשנות: <הנוסח>"'%(F,F))
			if D in('approve','change'):j=B['proposed']if D=='approve'else C['text'];d=X[W]['traffic_light'][E];h,U=set_track_wording(d,E,j,K);d.setdefault('deal_refs',[]).extend({'transaction_id':A.get('transaction_id'),'clause_id':A.get('clause_id'),'kind':A.get('kind'),'round':A.get('round')}for A in B['events']);Z(W,E,h,U,j,'עדכון פלייבוק מעסקה: %s'%', '.join(sorted({A['kind']for A in B['events']})),'negotiation_beyond_playbook',y);a(S.cell_key(W,E),True,True,j);i='approved'if D=='approve'else'changed';I['changed']+=1
			elif D=='skip':I['skipped']+=1
			else:raise ReplyError('תשובה שאינה מתאימה לעדכון %d'%F)
			z=G.setdefault('deal_feedback',[])
			for e in B['events']:z.append({'key':e['key'],'transaction_id':e.get('transaction_id'),'clause_id':e.get('clause_id'),'kind':e.get('kind'),'rule_id':W,'track':E,'decision':i,'by':L,'role':T,'at':H,'via':J.get('batch_id')})
			o.append({'rule_id':W,'track':E,'decision':i,'events':[A['key']for A in B['events']]})
	A0=_views(G,K)
	for(P,A1)in A0.items():
		R=M.get(P)
		if P not in f and R and S.cell_counts(R)and l[P]['fp']!=A1['fp']:M[P]=dict(R,status='open',policy_claim=False,reason='הנוסח השתנה אחרי האישור (%s). יש לאשר מחדש'%J.get('batch_id'))
	if O:G.setdefault('change_log',[]).extend(O);G['version']=q;G['last_updated']=H
	u=hashlib.sha256((k or'').encode('utf-8')).hexdigest();A2={'kind':'chat','batch_id':J.get('batch_id'),'stage':J.get('stage'),'token':'CHAT|%s|%s'%(G.get('family_id')or'',J.get('batch_id')),'signed_sha256':None,'reply_verbatim':k,'reply_sha256':u,'received_at':H,'evidence':{'received_via':CHAT_VIA,'upload_ref':'chat:%s:%s'%(J.get('batch_id'),u[:12])},'simulated':False,'signers':{'chat':{'name':L,'role':T,'date':H}},'choices':m,'decisions':n,'updates':o,'skipped':Y,'warnings':g,'counts':_counts(M)};return{'cells':M,'record':A2,'warnings':g,'summary':I,'changes':O,'wording_changed':any(A['field']!='management_decision'for A in O)}
def save_chat_record(records_dir,result,supersedes=None):
	D=records_dir;B=supersedes;A=result;H=_existing_records(D);I=1+len(H);E=os.path.join(D,'APR-%04d.json'%I);P.check_write_path(E);os.makedirs(D,exist_ok=True);F=dict(A['record'],record_id='APR-%04d'%I,cells=A['cells'])
	if B:
		F.update(supersedes=B,supersede_reason='קובץ ההערות מאשף ההערות; התאים הקודמים נמזגו'if A['record'].get('kind')=='wizard'else'מנה %s בתור האישור; התאים הקודמים נמזגו'%A['record'].get('batch_id'));A['record']['supersedes']=B
		for(J,C)in H:
			if C.get('record_id')==B and not C.get('superseded_by'):
				C['superseded_by']=F['record_id']
				with io.open(J,'w',encoding='utf-8')as G:json.dump(C,G,ensure_ascii=False,indent=1)
	with io.open(E,'w',encoding='utf-8')as G:json.dump(F,G,ensure_ascii=False,indent=1)
	return E
_SUMMARY={'he':'נקלט: {a} אושרו, {c} שונו ואושרו, {s} דולגו, {d} מספרים נקבעו, {q} שאלות נענו. {p} עמדות מחכות לעורך דין או לערך בסוגריים.','en':'Recorded: {a} approved, {c} changed and approved, {s} skipped, {d} numbers set, {q} questions answered. {p} positions are waiting for a lawyer or for a value in brackets.'}
def summary_line(sm,lang='he'):A=sm;return _SUMMARY[_ql(lang)].format(a=A['approved']-A['changed'],c=A['changed'],s=A['skipped'],d=A['decided'],q=A['chosen'],p=A['pending'])
WIZARD_VIA='wizard_file'
def wizard_approvals(model,approvals,by_rule,source,source_sha=None,at_rule=None,today=None,prior_cells=None,lang='he'):
	P=approvals;L=model;G=lang;F=source;E=today;E=E or _dt.date.today().isoformat();G=_ql(G);R=A.role_lines(L,G);T=_views(L,G);H={A:dict(B)for(A,B)in(prior_cells or{}).items()};Q,I=[],[];C={'approved':0,'already':0,'pending_value':0,'pending_legal':0,'not_person':0};D={'pending_value':[],'pending_legal':[],'not_person':[]}
	for B in sorted(P):
		J=norm_text((by_rule or{}).get(B)or'')
		if not _is_person_name(J):C['not_person']+=1;D['not_person'].append(B);continue
		if J not in I:I.append(J)
		U=str((at_rule or{}).get(B)or E)[:10]
		for V in P[B]:
			M=S.cell_key(B,V);N=T.get(M)
			if N is None:continue
			if _cell_done(H.get(M)or{},N):C['already']+=1;continue
			K=_approved_cell(N,R,J,None,U,False,False,'wizard:%s'%F);K['via']='wizard';H[M]=K
			if K['status']in APPROVED_STATUSES:C['approved']+=1
			elif K['status']=='pending_choice':
				C['pending_value']+=1
				if B not in D['pending_value']:D['pending_value'].append(B)
			else:
				C['pending_legal']+=1
				if B not in D['pending_legal']:D['pending_legal'].append(B)
	O=source_sha or hashlib.sha256(str(F).encode('utf-8')).hexdigest();W={'kind':'wizard','token':'WIZARD|%s|%s'%(L.get('family_id')or'',O[:12]),'signed_sha256':None,'source_file':F,'source_sha256':O,'received_at':E,'evidence':{'received_via':WIZARD_VIA,'upload_ref':'wizard:%s:%s'%(F,O[:12])},'simulated':False,'signers':{'wizard':{'name':', '.join(I),'role':None,'date':E}}if I else{},'choices':{},'decisions':[],'updates':[],'skipped':[],'warnings':Q,'counts':_counts(H)};return{'cells':H,'record':W,'warnings':Q,'summary':C,'rules':D,'changes':[],'wording_changed':False}
