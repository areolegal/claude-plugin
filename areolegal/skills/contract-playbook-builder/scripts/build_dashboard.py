# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'מזריק נתוני פלייבוק לתבנית הדשבורד הקנונית. אין לבנות דשבורד מאפס.\n\nשימוש בסיסי, קובץ HTML מקומי:\n  python3 build_dashboard.py assets/dashboard_template.html payload.json dashboard.html\n  python3 build_dashboard.py payload.json dashboard.html      (בלי תבנית: העותק שבתוסף, assets/dashboard_template.html)\n\nהתבנית נארזה בתוסף ואינה מורדת מהשרת בזמן ריצה. בלי נתיב תבנית (שני ארגומנטים בלבד) נלקחת\nassets/dashboard_template.html של הרכיב, ואשף ההערות שלידה (assets/wizard_template.html). נתיב מפורש גובר.\n\nשימוש מלא, שני התוצרים באותה הרצה:\n  python3 build_dashboard.py assets/dashboard_template.html payload.json out.html --artifact artifact.html\n\n--artifact  מפיק תוכן לפרסום כעמוד משותף: ללא תגיות doctype/html/head/body,\n            publishTarget=artifact, וללא מסלולי הורדת קבצים. ספריית הגרפים\n            מוטמעת בקובץ עצמו בשני התוצרים, כי טעינה מרשת חיצונית חסומה בעמוד משותף.\n\n--wizard <wizard_template.html>\n            בונה גם את אשף ההערות, אשף אחד לכל פלייבוק שבדף, לצד הדף המקומי:\n            <שם הדף>.wizard.<מזהה>.html. בדף מופיע הכפתור "להערות ולהצעות\n            נוסח", והוא פותח את האשף של סוג ההסכם שנבחר בבורר. האשף נבנה\n            מאותם נתונים בדיוק, כי "מחולל אחד, שתי תצוגות" (wizard_spec.md),\n            ומוטמע בו רק מה שהוא מציג (wizard_data), כדי שייפתח מהר.\n            בעמוד משותף מפרסמים את קובצי האשף כקבצים נלווים באותם שמות.\n\nה-payload חייב לכלול: meta (כולל slug ו-ls_key), rules, cites, sources, segments,\nfriendly/shortx (מיפוי שמות ידידותיים למקורות), precedents, templateFindings, queue, cross.\nmeta יכול לכלול גם: sharing (personal|shared|both), publishTarget, docAccess {mode, baseUrl}.\n\n--profile <פרופיל-לקוח.json>\n            צבעי המותג של הלקוח (branding.theme), כשהלקוח אישר מיתוג והצבעים נגזרו: נכנסים ל-meta.branding.theme\n            בדף ובאשף, וכך גם הלוגו שבנתונים (meta.branding.logo) עובר לאשף.\n\n-h, --help  מדפיס את ההוראות האלה ויוצא בקוד 0.\n\n--lang he|en  שפת הדף (meta.lang). בלעדיו: deliverable_language מ---profile (ו-display_language כשהיא\n            "both"), ובלעדיהם מה שבנתונים (build_workspace_payload.py כותב אותו מ-deliverable_language),\n            וברירת המחדל עברית. כך דף של לקוח באנגלית לעולם אינו נבנה בעברית. השפה קובעת את dir ו-lang של\n            הדף ואת כל הטקסט הקבוע בתבנית ובאשף; הנתונים עצמם אינם מתורגמים.\n'
import io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
DEFAULT_TEMPLATE=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','dashboard_template.html'))
from common.cli import OutputRefused,guard_out
from common.branding import apply_theme
from common import capabilities as CAP
from playbook import approval_sheet as A
from playbook import status as S
def load(p):return io.open(p,encoding='utf-8').read()
_QMARK={'—':'\ue014','–':'\ue013'}
def _protect_quotes(v,key=''):
	A=key
	if isinstance(v,dict):return{B:_protect_quotes(C,B if not(A=='cites'and B=='text')else'quote')for(B,C)in v.items()}
	if isinstance(v,list):return[_protect_quotes(B,A)for B in v]
	if isinstance(v,str)and A=='quote':
		for(B,C)in _QMARK.items():v=v.replace(B,C)
	return v
def _dump(data):A=json.dumps(_protect_quotes(data),ensure_ascii=False);A=A.replace('—',', ').replace('–','-');return A.replace('\ue014','\\u2014').replace('\ue013','\\u2013')
def inject(tpl,data,chartjs):A=tpl;B=_dump(data);B=B.replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029');assert A.count('/*__DATA__*/null')==1,'injection point missing';assert A.count('/*__CHARTJS__*/')==1,'chart library placeholder missing';C=A.replace('/*__DATA__*/null',B).replace('/*__CHARTJS__*/',chartjs);assert'—'not in C and'–'not in C,'em/en dash leaked';return C
def page_lang(data):A=data.get('meta')or{};B=str(A.get('lang')or A.get('deliverable_language')or'he').strip().lower();return'en'if B.startswith('en')else'he'
def to_artifact(html,lang='he'):
	A=html;B=re.search('<title>.*?</title>',A,re.S);C=re.search('<body[^>]*>(.*)</body>',A,re.S)
	if not(B and C):sys.exit('שגיאה: מבנה התבנית אינו כצפוי, לא ניתן להפיק עמוד משותף')
	D=re.findall('<style>.*?</style>|<script>.*?</script>',A[:A.index('<body')],re.S);return B.group(0)+'\n'+'\n'.join(D)+'\n<script>document.documentElement.setAttribute("dir","%s");document.documentElement.setAttribute("lang","%s");</script>\n'%('ltr'if lang=='en'else'rtl',lang)+C.group(1).strip()+'\n'
def wizard_name(out_path,book_id):A=os.path.splitext(os.path.basename(out_path))[0];B=re.sub('[^A-Za-z0-9_]+','_',str(book_id or'playbook')).strip('_')or'playbook';return'%s.wizard.%s.html'%(A,B)
_TRACKS='green','yellow','red'
def _wiz_hash(text):return A.wiz_hash(text)
def _first_sent(t,n=220):t=str(t or'');A=t.find('. ');return t[:A+1]if 0<A<n else t[:n]
def disp_num(r,idx):
	if r.get('num'):return str(r['num'])
	A=re.sub('^0','',str(r.get('id')or'').replace('R-','',1));return A if re.fullmatch('[0-9][0-9.]*',A)else str(idx+1)
SHELL_TITLES={'page':{'he':'מדיניות חוזית','en':'Contract policy'},'wizard':{'he':'אשף ההערות','en':'Comments wizard'}}
def localize_shell(html,lang,kind='page'):B=lang;A=html;C='ltr'if B=='en'else'rtl';A=re.sub('<html\\b[^>]*>','<html lang="%s" dir="%s">'%(B,C),A,count=1);return re.sub('<title>.*?</title>','<title>%s</title>'%SHELL_TITLES[kind][B],A,count=1,flags=re.S)
def wizard_data(book,bid,dashboard_href):
	B=book;J=B.get('meta')or{};H={A:J[A]for A in('id','slug','title','company','lang','deliverable_language','version','created','updated','type_short','approved_count','positions_count')if A in J};H['dashboard_href']=dashboard_href;H['segments_count']=len(B.get('segments')or[]);I=B.get('pb')
	if not I:N=((B.get('scope')or{}).get('contract_families')or[{}])[0]or{};I={'id':bid,'family':J.get('type_short')or N.get('contract_family_name')or'','role':N.get('company_role')or''}
	O,P=[],set();V=B.get('rules')or[]
	for(W,A)in enumerate(V):
		K,Q=A.get('rat')or{},A.get('persp')or{};X=K.get('protected_interest_and_clause_purpose')or K.get('legal_risk_and_legal_framework')or Q.get('legal_analysis')or'';Y=K.get('business_operational_impact')or Q.get('business_analysis')or'';F={}
		for C in _TRACKS:
			D=(A.get('tl')or{}).get(C)or{};F[C]={'pos':D.get('pos')or'','clause':D.get('clause')or'','h':_wiz_hash(D.get('clause')or'')}
			if D.get('clause_lang'):F[C]['lang']=D['clause_lang']
			if D.get('slots'):F[C]['slots']=list(D['slots'])
			for L in('label','basis_note','company_effect'):
				if D.get(L):F[C][L]=D[L]
			if D.get('legal_review_open'):F[C]['legal_review_open']=True
		G={'id':A.get('id'),'tl':F,'interest':{'legal':_first_sent(X),'comm':_first_sent(Y)},'norms':[{'law':A.get('law')or'','ref':A.get('ref')or'','meaning':A.get('meaning')or''}for A in A.get('norms')or[]if isinstance(A,dict)]}
		for C in('topic','issue','kind','why','they'):
			if A.get(C):G[C]=A[C]
		G['num']=disp_num(A,W)
		if A.get('walk_away')is True:G['walk_away']=True
		if A.get('client_concern')is True:G['client_concern']=True
		O.append(G);P.add(A.get('id'))
	R,M=[],set()
	for E in B.get('cites')or[]:
		if str(E.get('track')or'')not in _TRACKS:continue
		S=[A for A in E.get('rules')or[]if A in P]
		if not S:continue
		R.append({'id':E.get('id'),'rules':S,'src':E.get('src'),'text':E.get('text')or'','ref':E.get('ref')or'','track':E.get('track')});M.add(E.get('src'))
	T=B.get('sources')or{};Z={A:{A:B[A]for A in('label','title','short','paper','kind','status','role','date','loc')if(B or{}).get(A)}for(A,B)in T.items()if A in M};H['int_total']=sum(1 for A in T.values()if(A or{}).get('kind')=='internal'and(not A.get('pb')or A.get('pb')==I.get('id')));U={'meta':H,'pb':I,'rules':O,'cites':R,'sources':Z,'queue':[{'rule_id':A.get('rule_id'),'question':A.get('question')or'','issue':A.get('issue')or''}for A in B.get('queue')or[]]}
	if B.get('shortx'):U['shortx']={A:B for(A,B)in B['shortx'].items()if A in M}
	return U
def inject_wizard(tpl,data):A=_dump(data);A=A.replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029');assert tpl.count('/*__DATA__*/null')==1,'injection point missing in the wizard';return tpl.replace('/*__DATA__*/null',A)
def build_wizards(wiz_tpl,data,out_path):
	G=out_path;A=data;D=A.get('books')or None
	if D:J=list(D.items())
	else:B=(A.get('meta')or{}).get('id')or'playbook';J=[(B,A)]
	M=os.path.dirname(os.path.abspath(G));E={}
	for(B,F)in J:
		C=wizard_data(F,B,os.path.basename(G));C['meta'].setdefault('lang',page_lang(A));K=(F.get('meta')or{}).get('branding')or(A.get('meta')or{}).get('branding')
		if K:C['meta']['branding']=K
		H=wizard_name(G,B);L=localize_shell(inject_wizard(wiz_tpl,C),C['meta']['lang']if C['meta'].get('lang')in('he','en')else page_lang(A),'wizard');io.open(os.path.join(M,H),'w',encoding='utf-8').write(L);F.setdefault('meta',{})['wizard_href']=H;F['meta']['wizard_doc']=L;E[B]=H
	if D:
		I=next((A['id']for A in A.get('playbooks')or[]if A.get('current')),None)
		if I in E:A['meta']['wizard_href']=E[I];A['meta']['wizard_doc']=D[I]['meta'].get('wizard_doc')
	return E
def main():
	A=sys.argv[1:]
	if'-h'in A or'--help'in A:print(__doc__);sys.exit(0)
	E=None;F=None
	if'--artifact'in A:B=A.index('--artifact');E=A[B+1];del A[B:B+2]
	if'--wizard'in A:B=A.index('--wizard');F=A[B+1];del A[B:B+2]
	J=None
	if'--profile'in A:B=A.index('--profile');J=A[B+1];del A[B:B+2]
	D=None
	if'--lang'in A:
		B=A.index('--lang');D=A[B+1];del A[B:B+2]
		if D=='both':D=None
		elif D not in('he','en'):sys.exit('--lang: he או en')
	if len(A)==2:A=[DEFAULT_TEMPLATE]+A
	if len(A)<3:sys.exit(__doc__)
	K,P,G=A[0],A[1],A[2]
	if not F:
		Q=os.path.join(os.path.dirname(os.path.abspath(K)),'wizard_template.html')
		if os.path.isfile(Q):F=Q
	try:
		R=[K,P,F]
		if G:guard_out(G,inputs=R)
		if E:guard_out(E,inputs=R+[G])
	except OutputRefused as b:print('refused: %s'%b,file=sys.stderr);sys.exit(2)
	T=load(K);C=json.load(io.open(P,encoding='utf-8'));H=os.path.join(os.path.dirname(os.path.abspath(K)),'chart.umd.js')
	if not os.path.exists(H):H=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','assets','chart.umd.js');H=os.path.normpath(H)
	if not os.path.exists(H):sys.exit('שגיאה: chart.umd.js חסר בתיקיית assets. הספרייה מוטמעת ואינה נטענת מהרשת.')
	U=load(H);N=C.setdefault('meta',{})
	if not D and J:V=json.load(io.open(J,encoding='utf-8'));D=S.norm_lang(V.get('deliverable_language'))or S.norm_lang(V.get('display_language'))
	if D:
		N['lang']=D
		for c in(C.get('books')or{}).values():c.setdefault('meta',{})['lang']=D
		for L in[N]+[A.get('meta')or{}for A in(C.get('books')or{}).values()]:
			M=(L.get('labels')or{}).get(D)
			if M:L['label_now']=L['status_label']=M
			W=(L.get('company_by_lang')or{}).get(D)
			if W:L['company']=W
		for X in C.get('playbooks')or[]:
			d=(C.get('books')or{}).get(X.get('id'))or{};M=((d.get('meta')or{}).get('labels')or{}).get(D)
			if M:X['status_label']=M
	Y=apply_theme(C,json.load(io.open(J,encoding='utf-8')))if J else None;e=build_wizards(load(F),C,G)if F else{}
	def Z(d,where):
		A=where;d['meta']['publishTarget']=A
		for B in(d.get('books')or{}).values():B.setdefault('meta',{})['publishTarget']=A
		return d
	if G:I=Z(json.loads(json.dumps(C)),'local');io.open(G,'w',encoding='utf-8').write(localize_shell(inject(T,I,U),page_lang(I)))
	if E:
		a=CAP.missing('workspace',[A for A in(K,F)if A])
		if a:print('העמוד המשותף לא נבנה: התבנית קוראת ל-%s, ואין להן הצהרה (common/capabilities.py)'%', '.join(a),file=sys.stderr);sys.exit(3)
		I=Z(json.loads(json.dumps(C)),'artifact');io.open(E,'w',encoding='utf-8').write(to_artifact(localize_shell(inject(T,I,U),page_lang(I)),page_lang(I)))
	f=(N.get('docAccess')or{}).get('mode','local');O=C.get('sources')or{};g=sum(1 for A in O if(O[A]or{}).get('url'));print('נבנה %s%s. מצב גישה: %s. מקורות עם קישור: %d מתוך %d. שפת הדף: %s'%(G,' ו-'+E if E else'',f,g,len(O),page_lang(C)))
	if Y:print(Y)
	if C.get('books'):print('פלייבוקים בדף: %d'%len(C['books']))
	for(h,i)in e.items():print('אשף: %s  (%s)'%(i,h))
	if F and E:print('בעמוד המשותף: פרסם את קובצי האשף כקבצים נלווים, באותם שמות')
	if E:print('בפרסום הראשון של העמוד המשותף העבר capabilities בדיוק כך: %s'%json.dumps(CAP.CAPABILITIES['workspace'],ensure_ascii=False))
	print('בדיקה: node --check על מקטע הסקריפט, ואז node scripts/qa_dashboard.js')
if __name__=='__main__':main()
