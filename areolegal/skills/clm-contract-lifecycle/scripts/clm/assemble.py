# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy,datetime as dt,hashlib,json,os,re
from clm import catalog,core,dates,doc_kind,grouping,i18n,money
from clm.i18n import t
from clm.validate import check_extraction
RENEWAL_CODES='term_end','nonrenewal_notice','option_extend'
NOT_TERM_END_ROLES='min_commitment_end','max_end'
CARRIED='events','commercials','guarantees','key_clauses'
REVIEW_GROUP={'role':('צד החברה בהסכם',"Company's side in the agreement"),'counterparty':('צד שכנגד','Other side'),'family':('סוג הסכם','Agreement type'),'non_agreement':('מסמך שאינו הסכם','Document that is not an agreement'),'outcome':('תוצאת מועד שחלף','Outcome of a passed date'),'verify_critical':('מועד קריטי לאימות מול המקור','Critical date to check against the source'),'duplicate':('כפילות','Duplicate'),'not_extracted':('קובץ שלא חולץ','File not read yet'),'bad_extract':('חילוץ פגום','Reading to redo'),'source_removed':('מקור שהוסר','Removed source'),'split':('קיבוץ לבדיקה','Grouping to check'),'merged':('קיבוץ לבדיקה','Grouping to check'),'renewal_verify':('תוצאת מועד שחלף','Outcome of a passed date'),'unreadable':('קובץ שלא נקרא','File we could not open'),'amendment_unconfirmed':('סוג מסמך לבדיקה','Document type to check'),'kind_conflict':('סוג מסמך לבדיקה','Document type to check'),'role_conflict':('סתירה לבדיקה','Conflict to review'),'removed_from_register':('הוצא מהמאגר','Removed from the register'),'missing_core':('שדה ליבה חסר','Missing core field'),'abandoned_evidence':('משא ומתן','Negotiation'),'unsupported':('קובץ שלא קראנו','File we did not read'),'signing_unverified':('חתימה ותחילה לבדיקה','Signing and start to check'),'home_law_unknown':('הדין המקומי','Home law'),'scanned':('מסמך סרוק','Scanned document')}
ROLE_SOURCE={'playbook':('מהפלייבוק','from the playbook'),'suggested':('השערה מהחילוץ','our reading of the agreement'),'none':('בלי מקור','no source'),'user':('אישור משתמש','confirmed by a user')}
OUT_OF_REGISTER={'template':('תבנית','a template'),'non_agreement':('מסמך שאינו הסכם','a document that is not an agreement')}
PLACEHOLDERS='[להשלים]','[to complete]'
OVERDUE_BUCKETS='ours','theirs','role','outcome','old','superseded'
def _sid(*A):return hashlib.sha1('|'.join(str(A)for A in A).encode('utf-8')).hexdigest()[:10]
def _int(v):
	try:return int(v or 0)
	except(TypeError,ValueError):return 0
DASHES={'–':'-','—':'-'}
def undash(x,key=None):
	if isinstance(x,str):
		if key=='quote':return x
		for(A,B)in DASHES.items():x=x.replace(A,B)
		return x
	if isinstance(x,dict):return{A:undash(B,A)for(A,B)in x.items()}
	if isinstance(x,list):return[undash(A,key)for A in x]
	return x
def load_extracts(extract_dir):
	E=extract_dir;F,C={},[]
	if not os.path.isdir(E):return F,C
	for B in sorted(os.listdir(E)):
		if not B.endswith('.json'):continue
		try:
			with open(os.path.join(E,B),encoding='utf-8-sig')as G:A=json.load(G)
		except(ValueError,UnicodeDecodeError,OSError)as H:C.append({'file':B,'problems':['הקובץ פגום ולא נקרא (%s)'%type(H).__name__]});continue
		A=undash(A);D=check_extraction(A)
		if not D and str(A['sha256'])!=B[:-len('.json')]:D=['sha256 שבתוך הקובץ אינו תואם את שם הקובץ %s. שם הקובץ חייב להיות <sha256>.json לפי scan.json'%B]
		if D:C.append({'file':A.get('file',B)if isinstance(A,dict)else B,'problems':D})
		else:F[A['sha256']]=A
	return F,C
def _role_label(row):
	for B in('company_role','company_role_code'):
		A=row.get(B)
		if isinstance(A,str)and A.strip():return A.strip()
	return''
def load_playbooks(path):
	B=path
	if not B or not os.path.exists(B):return[],None
	try:
		with open(B,encoding='utf-8-sig')as D:E=json.load(D)
	except(ValueError,UnicodeDecodeError,OSError)as L:return[],'אינדקס הפלייבוקים אינו קריא (%s). צד החברה לא נלקח ממנו'%type(L).__name__
	F=E.get('playbooks')if isinstance(E,dict)else None
	if not isinstance(F,list):return[],'באינדקס הפלייבוקים אין רשימת playbooks. צד החברה לא נלקח ממנו'
	G=os.path.dirname(os.path.abspath(B));H=[]
	for I in F:
		if not isinstance(I,dict):continue
		A=dict(I);J=A.get('core_path')
		if not(isinstance(A.get('company_role'),str)and A['company_role'].strip())and isinstance(J,str):
			for M in(os.path.dirname(G),G):
				K=os.path.join(M,*J.replace('\\','/').split('/'))
				if os.path.exists(K):
					try:
						with open(K,encoding='utf-8-sig')as D:C=json.load(D)
					except(ValueError,UnicodeDecodeError,OSError):break
					if isinstance(C,dict)and isinstance(C.get('company_role'),str)and C['company_role'].strip():A['company_role']=C['company_role'].strip()
					break
		if _role_label(A):H.append(A)
	return H,None
def _norm(s):return' '.join(str(s or'').split()).casefold()
def playbook_role(ext,tinfo,playbooks):
	G=playbooks;B=ext
	if not G:return None,''
	C=B.get('playbook_family_id')
	if C:
		D=[A for A in G if C in(A.get('family_id'),A.get('family_code'))]
		if not D:return None,t('הפלייבוק %s לא נמצא ברשימת הפלייבוקים','The playbook %s is not in your playbook list')%C
	else:
		J={_norm(B.get('type_label')),_norm((tinfo or{}).get('label'))}-{''};I=B.get('type_code');D=[]
		for A in G:
			K=[A.get('family_name')]+(A.get('family_aliases')if isinstance(A.get('family_aliases'),list)else[])
			if I and I in(A.get('type_code'),A.get('family_code'))or J&{_norm(A)for A in K if isinstance(A,str)}:D.append(A)
	E=sorted({_role_label(A)for A in D}-{''})
	if len(E)>1:return None,t('כמה פלייבוקים מתאימים, וכל אחד מגדיר צד אחר שלכם בהסכם: %s','Several playbooks match, each with a different side for you: %s')%', '.join(E)
	if not E:return None,''
	F,H=E[0],_norm((B.get('our_role')or{}).get('value'))
	if not C and H and H not in _norm(F)and _norm(F)not in H:return None,t('ההשערה מהחילוץ (%s) שונה מצד החברה בפלייבוק (%s)',"Our reading of the agreement (%s) differs from the company's side in the playbook (%s)")%(B['our_role']['value'],F)
	return F,''
POLICY_MATCH='match','differs','not_compared'
def policy_match(kc,pb):
	A=(kc.get('policy_match')or'').strip()if isinstance(kc.get('policy_match'),str)else''
	if not pb or A not in POLICY_MATCH:return'not_compared'
	return A
def _value_rank(src,si):
	A=src
	if si==0 or A['doc_kind']!='amendment':return''
	B=A['_ext']['dates'].get('signed')
	if not B or doc_kind.says_draft(grouping.basename(A['file'])):return
	return B
def _clause_code(x):
	if isinstance(x,dict):x=x.get('clause_code')
	return x if isinstance(x,str)else None
def _rv(kind,text,subject=None,**D):
	C=subject;A=kind;B={'kind':A,'group':t(*REVIEW_GROUP[A])if A in REVIEW_GROUP else A,'text':text};B.update(D)
	if C is not None:B['_s']=C
	return B
def _event_ids(items):
	A=items;G=[_sid(*A)for(A,B)in A];D,E=[None]*len(A),{}
	for(B,C)in enumerate(G):E.setdefault(C,[]).append(B)
	for(C,H)in E.items():
		for(F,B)in enumerate(sorted(H,key=lambda j:(str(A[j][1]or''),j))):D[B]='ev-'+(C if F==0 else _sid(*A[B][0]+['#%d'%F]))
	return D
def _review_ids(review):
	E={}
	for A in review:
		B=A.pop('_s',None)
		if B is None:B=''if A.get('agreementId')or A.get('eventId')else A['text']
		F=[A['kind'],A.get('agreementId')or'',A.get('eventId')or'',B];C='rv-'+_sid(*F);D=E.get(C,0);E[C]=D+1;A['id']=C if D==0 else'rv-'+_sid(*F+['#%d'%D])
def _signed_state(mine,start,today):
	C=today;B=start;A=mine;A=[A for A in A if not A.get('superseded_by')];A=[A for A in A if not(A['event_code']=='term_end'and A.get('term_role')in NOT_TERM_END_ROLES)];D=[A for A in A if A['event_code']in RENEWAL_CODES and A['state']=='upcoming'and A['date']and(dt.date.fromisoformat(A['date'])-C).days<=120]
	if any(A['event_code']=='term_end'and A['state']=='needs_action'for A in A):return'term_passed_unverified'
	if D:return'renewal_window'
	if any(A.get('renewed')for A in A):return'extended'
	if B and dt.date.fromisoformat(B)>C:return'signed_not_effective'
	return'in_force'
def _amendment_note(signed,end,original_end):
	C=original_end;B=signed;A=end
	if not C:return t('תיקון להסכם מיום %s קובע את סיום התקופה: %s; לאשר את התוצאה','An amendment dated %s sets the end of the term: %s; confirm the outcome')%(dates.fmt(dates.parse(B)),dates.fmt(dates.parse(A)))
	D=dates.parse(A)<dates.parse(C);E=t('מקצר','shortens')if D else t('מאריך','extends');return t('תיקון להסכם מיום %s %s את התקופה עד %s; לאשר את התוצאה','An amendment dated %s %s the term to %s; confirm the outcome')%(dates.fmt(dates.parse(B)),E,dates.fmt(dates.parse(A)))
def _mark_superseded(e,kid_id,note):
	e.update(superseded_by=kid_id,superseded_note=note,state_note=note)
	if e['state']=='upcoming':e.update(act_by=None,next_reminder=None)
def _amendment_end(head,kids,order):
	B,D=[],[]
	for A in kids:
		C=A['_ext']['dates']
		if A['doc_kind']!='amendment'or not C.get('end'):continue
		if C['end']==head['_ext']['dates'].get('end'):continue
		(D if not C.get('signed')or doc_kind.says_draft(grouping.basename(A['file']))else B).append(A)
	E=max(B,key=lambda z:(z['_ext']['dates']['signed'],order[z['id']]))if B else None;return E,D
def _supersede(head_events,kid,original_end):
	C=original_end;D=kid['_ext']['dates'];A=dates.parse(D['end']);E=dates.parse(C)if C else A-dt.timedelta(days=1);G=_amendment_note(D['signed'],D['end'],C);H=('needs_action','lapsed_pending','upcoming')+(('pending_trigger',)if A>E else())
	for B in head_events:
		if B['event_code']not in RENEWAL_CODES or B['state']not in H:continue
		F=dates.parse(B['date'])if B.get('date')else None
		if F and(A>E and F<A or A<E and F>A):_mark_superseded(B,kid['id'],G)
_norm_entity=core.norm_entity
def _signing_shown(a):
	B,A=a['dates'],a.get('signatories')or[];C=any(A.get('status')=='signed'or A.get('date')for A in A)
	if A and not C and all(A.get('status')=='blank'for A in A):return False
	return bool(B.get('signed'))or bool(B.get('start')and(C or not A))or any(A.get('date')for A in A)
def _entity(extracted,company):
	B=extracted;A=company
	if _norm_entity(B)==_norm_entity(A):return A
	return B or A
HOME_ALIASES={'ישראל','israel','israeli','הישראלי'},{'בריטניה','אנגליה','united kingdom','uk','england','english','england and wales','האנגלי'},{'ארצות הברית','united states','usa','u.s.','american','האמריקני'},{'גרמניה','germany','german','הגרמני'},{'צרפת','france','french','הצרפתי'},{'הולנד','netherlands','dutch','ההולנדי'},{'אירלנד','ireland','irish','האירי'},{'קפריסין','cyprus','cypriot','הקפריסאי'}
def _home_law(home_law,previous,source=None):
	B=home_law
	if B:return B,source or'given'
	A=(previous or{}).get('meta')or{}
	if A.get('home_law')and A.get('home_law_source'):return A['home_law'],A['home_law_source']
	return None,None
def _law_class(law,home_law):
	B=home_law;A=law;A=(A or'').strip()
	if not A or A.startswith(('לא נקבע','לא סוכם'))or A.lower().startswith(('not set','not agreed')):return'unset'
	if not B:return'unknown'
	C={B.lower()}if B else set()
	for D in HOME_ALIASES:
		if C&D:C|=D
	return'home'if any(B in A.lower()for B in C)else'foreign'
def _as_texts(v):
	if isinstance(v,str):v=[v]
	return[A.strip()for A in v if isinstance(A,str)and A.strip()]if isinstance(v,list)else[]
def _deadline_end(head_evs):A=[A for A in head_evs if A['event_code']=='term_end'and not A.get('relative')and A.get('term_role')in(None,'initial_end')and A.get('contract_date_original')and A.get('occurrence')!='passed'];return min(A,key=lambda e:e['contract_date_original'])if A else None
def _current_end(mine,end):
	B=[A for A in mine if A['event_code']in('term_end','auto_renewal')and A.get('renewed')and A.get('term_role')not in NOT_TERM_END_ROLES and A['state']=='upcoming'and not A.get('superseded_by')and A.get('occurrence')!='passed'and A.get('date')and(not end or A['date']>end)]
	if not B:return None,None
	A=min(B,key=lambda x:x['date']);C=A.get('renewal_months')or(A.get('recurrence')or{}).get('months');return A['date'],{'kind':'auto_renewal','note':t('מחושב: %s ועוד %s של %s לפי %s; לאמת שההסכם התחדש','Computed: %s plus %s of %s under %s; confirm that the agreement renewed')%(dates.fmt(dates.parse(A['contract_date_original'])),core.count(len(A['history']),'חידוש אחד','חידושים','renewal','renewals'),core.count(C,'חודש אחד','חודשים','month','months'),A['clause'])}
def _abandoned_items(a):return[_rv('abandoned_evidence',t('סימן לכך שהמשא ומתן הופסק ב"%s": %s. רק אדם מסמן משא ומתן כ"נזנח"','A sign that negotiations stopped on "%s": %s. Only a person can mark it "Abandoned"')%(a['title'],A['value']or A['label']),agreementId=a['id'],subject='%s|%s'%(A['file'],A['value']or A['label']))for A in a.get('facts')or[]if A.get('code')=='negotiation_stopped']
def _overdue_bucket(e,today):
	if e['state']=='upcoming'and e.get('act_by_passed'):return'role'if e.get('role_pending')else'theirs'if e.get('obligor')=='them'else'ours'
	if e['state']not in('needs_action','lapsed_pending'):return
	if e.get('superseded_by'):return'superseded'
	if e.get('date')and dates.parse(e['date'])<dt.date(today.year,1,1):return'old'
	if e.get('role_pending'):return'role'
	if e.get('obligor')=='them':return'theirs'
	return'ours'if e['state']=='needs_action'else'outcome'
def tidy_text(s):return re.sub('(?<!\\.)\\.\\.(?!\\.)','.',s)if isinstance(s,str)else s
NOTICE_CODES='nonrenewal_notice','option_extend'
ACT_BY_PREFIX=re.compile('^(?:מועד היעד לטיפול \\([\\d.]+\\) חלף\\. |The act-by date \\([\\d.]+\\) has passed\\. )+')
def _act_by_passed(events,today):
	B=events;D={}
	for A in B:D.setdefault(A['agreementId'],[]).append(A)
	C=today.isoformat()
	for A in B:
		if A['state']!='upcoming'or not A.get('act_by')or A['act_by']>=C or A.get('superseded_by')or A.get('occurrence')=='passed':continue
		E=[A for A in D[A['agreementId']]if not A.get('superseded_by')];I=A['event_code']in('term_end','auto_renewal')and any(B['event_code']in NOTICE_CODES and B.get('date')and B['date']<C and B['date']<=A['date']and(B['state']in('lapsed_pending','needs_action')or B.get('occurrence')=='passed')and(dates.parse(A['date'])-dates.parse(B['date'])).days<=366 for B in E)
		if I:
			F=sorted(B for B in E if B['event_code']in NOTICE_CODES and B['state']=='upcoming'and B.get('act_by')and B['act_by']>=C and B is not A and B.get('occurrence')!='passed'and B.get('date'));A['decision_closed']=True;G=t('המועד להודעה חלף, ולכן ההסכם יתחדש ב-%s לפי ההסכם.','The notice deadline has passed, so the agreement renews on %s under its terms.')%dates.fmt(dates.parse(A['date']))
			if F:H=min(F,key=lambda x:x['act_by']);G+=t(' ההחלטה הבאה: עד %s (%s).',' Next decision: by %s (%s).')%(dates.fmt(dates.parse(H['act_by'])),H['label'])
			A['action']=G
		else:A['act_by_passed']=True;J=ACT_BY_PREFIX.sub('',A.get('action')or'');A['action']=t('מועד היעד לטיפול (%s) חלף. ','The act-by date (%s) has passed. ')%dates.fmt(dates.parse(A['act_by']))+J
def _rederive(row,today,ev_cat,confirmed,cp):
	A=row;B={A:B for(A,B)in A.items()if A not in('renewed','occurrence','renewal_check')};B['date']=A.get('contract_date_original')
	if B.get('action')and B.get('action')==A.get('state_note'):B['action']=''
	C=dates.derive_all(B,today,ev_cat,role_confirmed=confirmed,cp=cp)
	for D in C[1:]:D['id']='ev-'+_sid(A['id'],'occurrence',D['date'])
	if A.get('superseded_by'):_mark_superseded(C[0],A['superseded_by'],A['superseded_note'])
	return C
def resolve_lang(lang=None,previous=None):
	if lang:return i18n.norm(lang)
	return i18n.norm(((previous or{}).get('meta')or{}).get('lang'))
def assemble(scan,extracts,company,today,previous=None,default_owner='me',bad_extracts=(),as_of=None,playbooks=(),home_law=None,company_aliases=(),lang=None,home_law_source=None):
	B=previous
	with i18n.using(resolve_lang(lang,B))as E:
		C,F=_home_law(home_law,B,home_law_source);A=_assemble(scan,extracts,company,today,B,default_owner,bad_extracts,as_of,playbooks,C,company_aliases);A['meta']['lang'],A['meta']['home_law_source']=E,F
		if not C and any(A.get('law_class')=='unknown'for A in A['agreements']):D=_rv('home_law_unknown',t('לא ידוע מהו הדין המקומי של החברה, ולכן הדין החל בהסכמים לא סווג כמקומי או זר. להשלים את מדינת ההתאגדות בהקמה',"We do not know the company's home law, so governing law is not classed as home or foreign. Add the country of incorporation in the setup"),subject='home_law');_review_ids([D]);A['review_queue'].append(D)
		return A
def _assemble(scan,extracts,company,today,previous,default_owner,bad_extracts,as_of,playbooks,home_law,company_aliases):
	AC=home_law;AB=playbooks;s=company;V=scan;H=today;AD,Ay=catalog.load_events(),catalog.load_types();AE=t(*PLACEHOLDERS);AZ=[s]+[A for A in company_aliases if A];E,R,Aa,AF=[],[],[],{}
	for D in V['files']:
		if D['status']=='removed':continue
		if D['status']=='duplicate':AF[D['path']]=_rv('duplicate',t('%s זהה ל-%s','%s is identical to %s')%(D['path'],D.get('duplicate_of')),subject=D['path']);E.append(AF[D['path']]);continue
		if D['status']=='unsupported':E.append(_rv('unsupported',t('לא קראנו את %s, כי אין לנו דרך לקרוא קובץ מהסוג הזה. אם יש בו הסכם, שמרו אותו בפורמט אחר והוסיפו אותו לתיקייה','We did not read %s, because we cannot open this kind of file. If it holds an agreement, save it in another format and add it to the folder')%D['path'],subject=D['path']));continue
		if D.get('scanned'):E.append(_rv('scanned',(t('%s הוא מסמך סרוק. זיהינו בו טקסט מהתמונה, וכדאי לבדוק את התאריכים והסכומים מול המקור','%s is a scanned document. We recognised its text from the image, so check the dates and amounts against the source')if D.get('ocr')=='done'else t('%s הוא מסמך סרוק, ואין במחשב כלי לזיהוי טקסט. הנתונים נקראים מתמונות העמודים, וכדאי לבדוק את התאריכים והסכומים מול המקור','%s is a scanned document, and this computer has no text recognition. The data is read from the page images, so check the dates and amounts against the source'))%D['path'],subject=D['path']))
		if D['status']=='unreadable':E.append(_rv('unreadable',t('לא ניתן היה לקרוא את הקובץ (נעול או לא זמין): %s. הנתונים מהחילוץ הקודם נשמרים. לסגור את הקובץ ולהריץ סריקה שוב','We could not open the file (locked or unavailable): %s. The data from the last reading is kept. Close the file and scan again')%D['path'],subject=D['path']))
		B=extracts.get(D['sha256'])if D.get('sha256')else None
		if not B:Aa.append(D['path']);continue
		R.append({'id':'doc-'+D['sha256'][:10],'file':D['path'],'sha256':D['sha256'],'doc_kind':B['doc_kind'],'date':B.get('version_date')or B['dates'].get('signed'),'signed_date':B['dates'].get('signed'),'start_date':B['dates'].get('start'),'counterparty':B['counterparty'].get('name')or'','title':B['title'],'relation':B.get('relation')or{'kind':None,'parent_hint':None},'version_by':B.get('version_by','unknown'),'_ext':B})
		if B['doc_kind']in OUT_OF_REGISTER and not D.get('attachments')and(doc_kind.says_signed(D['path'])or D.get('suggested_kind')=='signed'):E.append(_rv('kind_conflict',t('%s: שם הקובץ מעיד על הסכם חתום, והחילוץ סיווג אותו כ%s. לאשר את הסיווג','%s: the file name suggests a signed agreement, but our reading classed it as %s. Confirm the classification')%(grouping.basename(D['path']),t(*OUT_OF_REGISTER[B['doc_kind']])),subject=D['path']))
	Az={A.get('sha256'):A['path']for A in V['files']if A.get('sha256')}
	for S in bad_extracts:
		i=Az.get(str(S['file'])[:-len('.json')],S['file'])if str(S['file']).endswith('.json')else S['file']
		if i18n.en():A_='one of the files'if str(i).endswith('.json')else i;E.append(_rv('bad_extract','We could not use what we read from %s. It will be read again on the next update'%A_,subject=S['file'],detail=list(S['problems'][:5]),source=i))
		else:E.append(_rv('bad_extract','%s: %s'%(i,'; '.join(S['problems'][:3])),detail=list(S['problems'][:5]),source=i))
	j=grouping.group(R,s);E.extend(j['review']);u={A['id']:A for A in R};T=previous or{};v=T.get('agreements',[]);B0={A['number']:A for A in v};w={A['id']:A for A in T.get('documents',[])}
	def Ab(p):
		A={w[A]['file']for A in p.get('doc_ids',[])if A in w}
		if p.get('file'):A.add(p['file'])
		return A
	def B1(n):A=str(n).rsplit('-',1)[-1];return int(A)if A.isdigit()else 0
	AG=max([_int((T.get('meta')or{}).get('number_seq'))]+[B1(A['number'])for A in v]);B2={B['id']:A for(A,B)in enumerate(R)};Ac={A:[u[B]for(B,C)in sorted(j['children'].items())if C==A]for A in range(len(j['groups']))};AH=[set(B['doc_ids'])|{A['id']for A in Ac[A]}for(A,B)in enumerate(j['groups'])];x=[{u[A]['file']for A in A}for A in AH];k,AI,AJ={},{},[]
	for I in v:
		B3,B4=set(I.get('doc_ids',[])),Ab(I);AK=[A for A in range(len(AH))if AH[A]&B3 or x[A]&B4];y=[A for A in AK if A not in k]
		if not y:
			if AK:AJ.append((AK[0],I['number']))
			continue
		Ad=next((A for A in y if I.get('file')in x[A]),y[0]);k[Ad]=I['number']
		for M in y:
			if M!=Ad:AI.setdefault(M,I['number'])
	B5=set(k);N,L,AL,AM,z,AN,W=[],[],[],[],[],[],[];A0=set()
	def c(aid,clause,file,quote):
		A=quote
		if not A:return[]
		W.append({'n':len(W)+1,'agreementId':aid,'clause':clause,'file':file,'quote':A});return[len(W)]
	for(M,Ae)in enumerate(j['groups']):
		A1=[u[A]for A in Ae['doc_ids']];U=u[Ae['head_id']];B=U['_ext'];AO=Ac[M];O=k.get(M)
		if not O:AG+=1;O='CLM-%d-%04d'%(H.year,AG)
		F='ag-'+_sid(O);P=Ay.get(B.get('type_code'));J,l,m=B['our_role'],'',None;A2=(B0.get(O)or{}).get('our_role')or{}
		if A2.get('source')=='user'and A2.get('value')and J.get('source')!='user':
			if J.get('value')and _norm(J['value'])!=_norm(A2['value']):m=J
			J={'value':A2['value'],'source':'user'}
		elif J.get('source')!='user':
			if J.get('source')=='playbook'and J.get('value'):n=J['value']
			else:n,l=playbook_role(B,P,AB)
			if n:Af=core.side_conflict(n,B);J={'value':n,'source':'suggested'}if Af else{'value':n,'source':'playbook'};l=Af or l
		d=J.get('source')in('playbook','user');B6=playbook_role(B,P,AB)[0]if AB else None;AP=U['doc_kind']in grouping.CHILD
		if AP:X=bool(B['dates'].get('signed'))
		else:X=any(A['doc_kind']=='signed'for A in A1)
		A3=B['counterparty'].get('name')or AE;A={'id':F,'number':O,'title':B['title'],'type_code':B.get('type_code')if P else None,'family':P['label']if P else B.get('type_label')or t('לא סווג','Not classified'),'type_label':B.get('type_label')or'','counterparty':A3,'counterparty_id':B['counterparty'].get('company_number'),'contracting_entity':_entity(B.get('contracting_entity'),s),'our_role':{'value':J.get('value')or'','source':J.get('source')or'none','confirmed':d},'doc_ids':[A['id']for A in A1]+[A['id']for A in AO],'versions':len(A1),'file':U['file'],'original_location':U['file'],'signature':'signed_unverified'if X else'unknown'if AP else'not_signed','dates':{'signed':B['dates'].get('signed'),'start':B['dates'].get('start'),'end':B['dates'].get('end'),'actual_end':None},'governing_law':B.get('governing_law'),'law_class':_law_class(B.get('governing_law'),AC),'counterparty_notice_address':B['counterparty'].get('notice_address')or None,'legal_owner':default_owner if d else None,'business_owner':None,'coverage':B['coverage'],'type_fields':[{'label':A['label'],'value':(B.get('type_fields')or{}).get(A['key'])}for A in(P or{}).get('type_fields',[])]};e=[U]+AO;Ag=[(A,C)for(A,B)in enumerate(e)for C in range(len(B['_ext']['events']))];B7=dict(zip(Ag,_event_ids([([O,A['event_code'],A['label'],A['clause']]+([]if B==0 else[e[B]['id']]),A.get('date'))for(B,C)in Ag for A in[e[B]['_ext']['events'][C]]])));B8,Ah,o,Ai,Aj=[],[],[],[],set();B9=catalog.load_key_clauses()
		for(AQ,Y)in enumerate(e):
			f=Y['_ext'];Ai.extend({'text':A,'file':Y['file']}for A in _as_texts(f.get('notes')));Aj.update(A.get('clause_code')for A in f.get('key_clauses')or[]if isinstance(A,dict))
			for(BA,C)in enumerate(f['events']):
				AR={A:B for(A,B)in C.items()if A!='quote'};AR.update(agreementId=F,refs=c(F,C['clause'],Y['file'],C.get('quote')),verify=not C.get('quote'),id=B7[AQ,BA]);AS=dates.derive_all(AR,H,AD,role_confirmed=d,cp=A3)
				for Ak in AS[1:]:Ak['id']='ev-'+_sid(AR['id'],'occurrence',Ak['date'])
				L.extend(AS)
				if AQ==0:o.extend(AS)
			for G in f.get('commercials',[]):
				K={A:B for(A,B)in G.items()if A!='quote'};K.update(agreementId=F,refs=c(F,G['clause'],Y['file'],G.get('quote')));AL.append(K);B8.append(K);Al=_value_rank(Y,AQ)
				if Al is not None:Ah.append(dict(K,_rank=Al))
			for AT in f.get('guarantees',[]):K={A:B for(A,B)in AT.items()if A!='quote'};K.update(agreementId=F,refs=c(F,AT['clause'],Y['file'],AT.get('quote')));AM.append(K)
			for p in f.get('key_clauses',[]):K={A:B for(A,B)in p.items()if A!='quote'};K.update(agreementId=F,refs=c(F,p['clause'],Y['file'],p.get('quote')));K.update(core.key_clause_fields(p,AZ,B['counterparty'].get('name'),d,H));K['policy_match']=policy_match(p,B6);z.append(K)
		BB=[A for A in e if A['_ext'].get('key_clauses_checked')]or[U];BC={A for B in BB for A in map(_clause_code,B['_ext'].get('key_clauses_not_found')or[])if A in B9}-Aj;Z=money.annual(Ah,B.get('currency'),as_of=H.isoformat());a=Z['by_currency'];A4=None
		if a:
			A4=t('מחושב מהתמורה שבהסכם','Computed from the payments in the agreement')
			if Z['amended_on']:A4+=t('; לפי התיקון להסכם מיום %s','; per the amendment dated %s')%dates.fmt(dates.parse(Z['amended_on']))
			if Z['estimated']:A4+=t('; כולל אומדן','; includes an estimate')
		Am=money.currency_of({},B.get('currency'));A['value']={'annual_by_currency':a,'annual':next(iter(a.values()))if len(a)==1 else None,'currency':next(iter(a))if len(a)==1 else Am,'total':B.get('total_value'),'total_currency':Am,'basis':A4,'components':Z['components'],'not_counted':Z['not_counted'],'unknown_currency':Z['unknown_currency'],'in_portfolio':False};g,BD=_amendment_end(U,AO,B2)if X else(None,[])
		if g:A['dates'].update(original_end=A['dates']['end'],end=g['_ext']['dates']['end'],end_source=g['id']);_supersede(o,g,A['dates']['original_end'])
		A['notes'],A['key_clauses_not_found']=Ai,sorted(BC);A.update(core.agreement_fields(B,lambda cl,q:c(F,cl,U['file'],q),AZ,B['counterparty'].get('name'),d));A['facts']=core.facts([(A['file'],A['_ext'])for A in e],lambda cl,q,f:c(F,cl,f,q));A5=_deadline_end(o)if not A['dates']['end']else None;An,BE=(None,None)if A['dates']['end']or A5 else core.computed_end(B.get('term'),core.start_for(B.get('term'),B['dates']))
		if g:A['dates']['end_basis']={'kind':'amendment','note':t('לפי התיקון להסכם מיום %s','Per the amendment dated %s')%dates.fmt(dates.parse(g['_ext']['dates']['signed']))}
		elif A5:A['dates']['end']=A5['contract_date_original'];A['dates']['end_basis']={'kind':'deadline','note':t('לפי המועד: ','From the date: ')+A5['label']}
		elif An:A['dates']['end']=An;A['dates']['end_basis']={'kind':'computed','note':BE}
		else:A['dates']['end_basis']={'kind':'contract'if A['dates']['end']else None,'note':''}
		for h in BD:E.append(_rv('amendment_unconfirmed',t('%s: תיקון להסכם משנה את תאריך הסיום; לאשר שנחתם','%s: an amendment changes the end date; confirm it was signed')%grouping.basename(h['file']),agreementId=F,subject=h['file']))
		Ao=[A for A in L if A['agreementId']==F];b,A6=_current_end(Ao,A['dates']['end'])
		if b:A['dates']['current_end'],A['dates']['current_end_basis']=b,A6
		else:
			b,A6,Ap=core.current_end(A['dates']['end'],A['term'],A['renewal'],H,X)
			if Ap:E.append(_rv('renewal_verify','%s: %s'%(A['title'],Ap),agreementId=F))
			if A6:A['dates']['current_end'],A['dates']['current_end_basis']=b,A6
			else:A['dates']['current_end']=A['dates']['end']or None;A['dates']['current_end_basis']={'kind':'same_as_end'if A['dates']['end']else None,'note':''}
		BF,Aq,BG=core.max_end(B.get('term'),B.get('renewal'),A['dates']['end'],o);A['dates'].update(max_end=BF,max_end_basis={'kind':Aq,'note':BG}if Aq else None);A['dates']['survival_end'],A['dates']['survival_end_label']=core.survival_end(o)
		if X:A['handling_stage']=None;A['agreement_state']=core.term_passed(_signed_state(Ao,A['dates']['start'],H),A['dates'],A['dates']['current_end'],H);A['value']['in_portfolio']=A['agreement_state']in money.PORTFOLIO_STATES
		else:
			q=None
			for A7 in sorted(A1,key=lambda z:z['date']or'0000'):BH=A7['doc_kind']=='negotiation_version'and A7['version_by']=='them';q={'agreementId':F,'date':A7['date'],'stage':'comments_received'if BH else'drafting','source':{'type':'file','name':A7['file']},'evidence_rank':3};AN.append(q)
			A['agreement_state']=None;A['handling_stage']='comments'if q['stage']=='comments_received'and not AP else'drafting';A['waiting_on']='us';A['idle_days']=(H-dt.date.fromisoformat(q['date'])).days if q['date']else None
		A['field_status']={A:'extracted'if B else'missing'for(A,B)in{'our_role':A['our_role']['value'],'counterparty':A3!=AE,'type':bool(P),'end_date':A['dates']['end'],'start_date':A['dates']['start'],'value':a,'governing_law':A['governing_law'],'business_owner':None,'term_kind':A['term'],'signatories':A['signatories']}.items()};Ar=A['dates']['end_basis']['kind']
		if Ar in('contract','amendment'):A['field_status']['end_date']='extracted'
		elif Ar in('deadline','computed'):A['field_status']['end_date']='derived'
		elif(A['term']or{}).get('kind')in core.NOT_RELEVANT_TERMS:A['field_status']['end_date']='not_relevant'
		elif not A['term']and not A['dates']['current_end']and(P or{}).get('end_date_expected')is False:A['field_status']['end_date']='not_expected'
		else:A['field_status']['end_date']='missing'
		if A['signature']=='signed_unverified':
			AU=[A for(A,B)in((t('תאריך חתימה','Signing date'),not A['dates']['signed']),(t('תאריך סיום','End date'),A['field_status']['end_date']=='missing'),(t('סוג תקופה','Term type'),not A['term']),(t('חותמים','Signatories'),not A['signatories']))if B];AU+=core.missing_party_sides(A['signatories'])
			if AU:E.append(_rv('missing_core',t('שדה ליבה חסר ב"%s": %s. להשלים מהמקור, או לאשר "נבדק ולא נמצא"','Missing core field in "%s": %s. Fill it in from the source, or confirm "Checked, not found"')%(A['title'],', '.join(AU)),agreementId=F))
		if not X:E.extend(_abandoned_items(A))
		if X and not _signing_shown(A):A.update(signature='unknown',agreement_state='status_unverified');A['value']['in_portfolio']=False;E.append(_rv('signing_unverified',t('לא מצאנו ב"%s" תאריך חתימה, תאריך תחילה או חותם שחתם, ולכן הוא לא מוצג כבתוקף. לאשר שנחתם ומתי נכנס לתוקף','We found no signing date, start date or signed signatory in "%s", so it is not shown as in force. Confirm it was signed and when it took effect')%A['title'],agreementId=F))
		N.append(A)
		if B.get('key_clauses_checked'):A0.add(F)
		if M in AI and M not in B5:E.append(_rv('split',t('ההסכם %s פוצל. מספר חדש: %s','Agreement %s was split. New number: %s')%(AI[M],O),agreementId=F))
		for(BI,AV)in AJ:
			if BI==M:E.append(_rv('merged',t('ההסכמים %s ו-%s זוהו כעסקה אחת ואוחדו. נשמר המספר %s, והמספר %s אינו בשימוש עוד. לאשר את האיחוד','Agreements %s and %s were found to be one deal and merged. Number %s is kept, and %s is no longer used. Confirm the merge')%(O,AV,O,AV),agreementId=F,subject=AV))
		if m:E.append(_rv('role_conflict',t('סתירה לבדיקה: צד החברה ב"%s" אושר כ"%s", והגרסה החדשה מציינת "%s" (%s). הערך שאושר נשמר עד להכרעה','Conflict to review: the company\'s side in "%s" was confirmed as "%s", and the new version says "%s" (%s). The confirmed value stays until you decide')%(A['title'],J['value'],m['value'],t(*ROLE_SOURCE[m.get('source')])if m.get('source')in ROLE_SOURCE else''),agreementId=F))
		if not d:E.append(_rv('role',t('לאשר את צד החברה ב"%s"%s','Confirm the company\'s side in "%s"%s')%(A['title'],' (%s)'%l if l else''),agreementId=F))
		if A3==AE:E.append(_rv('counterparty',t('להשלים את הצד שכנגד ב"%s"','Fill in the other side in "%s"')%A['title'],agreementId=F))
		if not P:E.append(_rv('family',t('סוג הסכם שאינו בקטלוג ("%s"): לאשר או להציע הגדרה מקומית','Agreement type not in the catalogue ("%s"): confirm it or suggest a local definition')%A['family'],agreementId=F))
	BJ={A['path']for A in V['files']if A['status']!='removed'};BK={A['path']for A in V['files']if A['status']=='removed'};BL,BM=set(k.values()),{A for(B,A)in AJ};BN={A['id']for A in R};BO=set((T.get('registers')or{}).get('key_clauses_unchecked')or[]);As,At,AW=set(),[],{};BP=set().union(*x)if x else set();Au={A['file']:A['doc_kind']for A in R if A['doc_kind']in OUT_OF_REGISTER and A['file']not in BP}
	def Av(p,flag):
		A=copy.deepcopy(p);A.pop('source_removed',None);A.pop('extraction_pending',None);A[flag]=True;N.append(A);D={}
		for O in sorted((A for A in T.get('footnotes',[])if A.get('agreementId')==p['id']),key=lambda x:x['n']):W.append(dict(copy.deepcopy(O),n=len(W)+1));D[O['n']]=len(W)
		for(I,P)in zip(CARRIED,(L,AL,AM,z)):
			for G in T.get(I,[]):
				if G.get('agreementId')!=p['id']or G.get('occurrence')=='passed':continue
				F=copy.deepcopy(G);F['refs']=[D[A]for A in G.get('refs')or[]if A in D]
				if I=='events':P.extend(_rederive(F,H,AD,bool((A.get('our_role')or{}).get('confirmed')),A.get('counterparty')or None))
				else:
					if I=='key_clauses':F['active']=core._active(F,H)
					P.append(F)
		def Q(x):
			if isinstance(x,dict)and'refs'in x:x['refs']=[D[A]for A in x.get('refs')or[]if A in D]
		for C in('term','renewal','exit','jurisdiction','payment_terms'):Q(A.get(C))
		for C in('signatories','facts'):
			for V in A.get(C)or[]:Q(V)
		if A.get('agreement_state')and A['agreement_state']!='status_unverified':A['agreement_state']=_signed_state([B for B in L if B['agreementId']==A['id']],(A.get('dates')or{}).get('start'),H)
		B=A.setdefault('dates',{});B.setdefault('end_basis',{'kind':'amendment'if B.get('end_source')else'contract'if B.get('end')else None,'note':''});J,K=_current_end([B for B in L if B['agreementId']==A['id']],B.get('end'));M=None
		if not J:J,K,M=core.current_end(B.get('end'),A.get('term'),A.get('renewal'),H,A.get('signature')=='signed_unverified')
		if M:E.append(_rv('renewal_verify','%s: %s'%(A['title'],M),agreementId=A['id']))
		if K:B['current_end'],B['current_end_basis']=J,K
		else:B['current_end']=B.get('end')or None;B['current_end_basis']={'kind':'same_as_end'if B.get('end')else None,'note':''}
		for C in('term','renewal','exit','jurisdiction','payment_terms'):A.setdefault(C,None)
		for C in('signatories','facts'):A.setdefault(C,[])
		for C in('max_end','max_end_basis','survival_end','survival_end_label'):B.setdefault(C,None)
		R=[B for B in L if B['agreementId']==A['id']];B['survival_end'],B['survival_end_label']=core.survival_end(R)
		if(B.get('max_end_basis')or{}).get('kind')!='extracted':X,S,Y=core.max_end(None,A.get('renewal'),B.get('end'),R);B['max_end'],B['max_end_basis']=X,{'kind':S,'note':Y}if S else None
		U=A.setdefault('field_status',{});U.setdefault('term_kind','missing');U.setdefault('signatories','missing')
		if A.get('agreement_state'):A['agreement_state']=core.term_passed(A['agreement_state'],B,B['current_end'],H)
		if A.get('signature')!='signed_unverified':E.extend(_abandoned_items(A))
		A['law_class']=_law_class(A.get('governing_law'),AC);A['value']=money.normalize(A.get('value'),A.get('signature')=='signed_unverified'and A.get('agreement_state')in money.PORTFOLIO_STATES);AN.extend(copy.deepcopy(A)for A in T.get('timeline',[])if A.get('agreementId')==p['id']);At.extend(copy.deepcopy(w[A])for A in p.get('doc_ids',[])if A in w and A not in BN)
		if T.get('registers')is not None and p['id']not in BO:A0.add(p['id'])
		return A
	for I in v:
		if I['number']in BL or I['number']in BM:continue
		A8=Ab(I)
		if not A8:continue
		r=A8&BJ
		if r and all(A in Au for A in r):BQ=t(' ו',' and ').join(sorted({t(*OUT_OF_REGISTER[Au[A]])for A in r}));E.append(_rv('removed_from_register',t('הוצא מהמאגר: ההסכם %s ("%s") סווג כ%s. המספר אינו בשימוש עוד. לאשר את הסיווג','Removed from the register: agreement %s ("%s") was classed as %s. The number is no longer used. Confirm the classification')%(I['number'],I['title'],BQ),subject=I['number']));continue
		if r:
			G=Av(I,'extraction_pending')
			for Q in r:AW[Q]=G
		elif A8<=BK or I.get('source_removed'):G=Av(I,'source_removed');As|=A8;E.append(_rv('source_removed',t('המקור של "%s" הוסר מהתיקייה. ההסכם נשמר ומסומן','The source of "%s" was removed from the folder. The agreement is kept and marked')%G['title'],agreementId=G['id']))
	for(Q,Aw)in AF.items():
		G=AW.get(Q)
		if G:Aw['text']+=t('. ההסכם %s מוצג לפי החילוץ הקודם','. Agreement %s is shown as last read')%G['number'];Aw['agreementId']=G['id']
	for Q in Aa:
		G=AW.get(Q)
		if G:E.append(_rv('not_extracted',t('הקובץ טרם חולץ מחדש: %s. ההסכם %s מוצג לפי החילוץ הקודם','The file has not been read again yet: %s. Agreement %s is shown as last read')%(Q,G['number']),agreementId=G['id'],subject=Q))
		else:E.append(_rv('not_extracted',t('הקובץ טרם חולץ: %s','The file has not been read yet: %s')%Q,subject=Q))
	for D in V['files']:
		if D['status']=='removed'and D['path']not in As:E.append(_rv('source_removed',t('הקובץ הוסר מהתיקייה: %s','The file was removed from the folder: %s')%D['path'],subject=D['path']))
	BR={A['path']for A in V['files']if A.get('attachments')}
	for A9 in R:
		if A9['doc_kind']=='non_agreement'and A9['file']not in BR:E.append(_rv('non_agreement',t('זוהה כמסמך שאינו הסכם: %s. לאשר הוצאה מהמאגר','Identified as a document that is not an agreement: %s. Confirm removing it from the register')%grouping.basename(A9['file']),subject=A9['file']))
	AX={A['id']:A['title']for A in N};_act_by_passed(L,H)
	for C in L:
		C['overdue_bucket']=_overdue_bucket(C,H)
		for h in('action','state_note','superseded_note'):
			if C.get(h):C[h]=tidy_text(C[h])
	for C in L:
		if C.get('renewal_check'):E.append(_rv('renewal_verify',t('לאמת שההסכם התחדש: %s, %s (המועד %s חלף)','Confirm that the agreement renewed: %s, %s (the date %s has passed)')%(AX[C['agreementId']],C['label'],dates.fmt(dates.parse(C['date']))),agreementId=C['agreementId'],eventId=C['id']))
		elif C['state']=='lapsed_pending':E.append(_rv('outcome','%s: %s%s'%(C['label'],AX[C['agreementId']],'. '+C['superseded_note']if C.get('superseded_note')else''),agreementId=C['agreementId'],eventId=C['id']))
	for C in L:
		if C['critical']and C['state']in('upcoming','needs_action')and C.get('occurrence')!='passed'and not(C.get('superseded_by')and C['state']=='upcoming'):E.append(_rv('verify_critical','%s: %s'%(C['label'],AX[C['agreementId']]),agreementId=C['agreementId'],eventId=C['id']))
	_review_ids(E);AY={}
	for A in N:
		if A['counterparty']in PLACEHOLDERS:continue
		G=AY.setdefault(A['counterparty'],{'name':A['counterparty'],'agreements':[],'annual_by_currency':{}});G['agreements'].append(A['id'])
		if A['value']['in_portfolio']:
			for(b,BS)in A['value']['annual_by_currency'].items():G['annual_by_currency'][b]=G['annual_by_currency'].get(b,0)+BS
	for G in AY.values():G['annual_by_currency']=money.tidy(G['annual_by_currency'])
	Ax={'term_passed':[A['id']for A in N if A['agreement_state']=='term_passed_unverified'],'not_signed':[A['id']for A in N if A['signature']=='not_signed'],'poa':None,'regulatory':None,'key_clauses_unchecked':sorted(A['id']for A in N if A['id']not in A0)};Ax.update(core.registers(N,z,A0,H));AA=H.isoformat();return{'meta':{'company':s,'generated_at':AA,'last_updated':AA,'as_of':as_of or AA+'T07:00','source_run':AA,'home_law':AC,'schema_version':'2.0','files_scanned':sum(1 for A in V['files']if A['status']not in('removed','duplicate')),'number_seq':AG},'documents':[{A:B for(A,B)in A.items()if not A.startswith('_')}for A in R]+At,'agreements':N,'events':L,'commercials':AL,'guarantees':AM,'key_clauses':z,'footnotes':W,'timeline':AN,'counterparties':sorted(AY.values(),key=lambda c:c['name']),'registers':Ax,'review_queue':E,'catalog':AD,'key_clause_labels':catalog.load_key_clauses()}
