#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'עמוד ההקמה (skills/contract-setup-diagnostician/assets/setup-page.html) בשלב הפלייבוק: שני תפקידים.\n\n1. init: בונה את העמוד במצב אישור מהפלייבוק עצמו. העמדות שמוצגות הן רק אלה שעוד לא אושרו, לפי אותו חישוב\n   מעמד שכל המערכת קוראת (playbook/status.py), ולכל נושא שטעון בדיקה משפטית מוצג מה צריך לבדוק.\n\n       python3 -B setup_page.py init --model playbook-model.json --records "Areo-נתונים/אישורים" \\\n           --page "AREO_RT/skills/contract-setup-diagnostician/assets/setup-page.html" \\\n           --out "<קובץ זמני>.html" [--approver-name "<שם מלא>" --approver-role "<תפקיד>"] [--workspace-url URL]\n\n2. apply: קולט את ההודעה שהעמוד שלח (kind: areo_playbook_decisions) דרך תור האישור הרשמי בצ\'אט\n   (ingest_approval.py --queue / --answer), ולא במסלול נפרד: אותן רשומות, אותו מעמד, ואותה נעילה אחת לבדיקה\n   משפטית. נושא שאושר: "לאשר", ובנושא טעון בדיקה משפטית "נבדק ולאשר". נושא שביקשו לשנות, שלא אושר, או\n   שעורך דין יעבור עליו אחר כך: "לדלג", והוא נשאר פתוח בסביבת העבודה. השינויים וההערות מודפסים לסוכן.\n\n       python3 -B setup_page.py apply --decisions <decisions.json> --model playbook-model.json \\\n           --core playbook-core.json --index Areo-נתונים/playbooks/index.json --records "Areo-נתונים/אישורים"\n\ndecisions.json הוא השדה answers מההודעה, כמו שהוא: {family, approver: {name, role}, date, decisions: [...]}.\n'
import io,json,os,subprocess,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from playbook import ingest_approval as IA,status as S
MARKER='/*__AREO_INIT__*/null'
HERE=os.path.dirname(os.path.abspath(__file__))
CLI=os.path.join(HERE,'ingest_approval.py')
MAX_ROUNDS=20
def _load(p):
	with io.open(p,encoding='utf-8')as A:return json.load(A)
def _track(rule,t):return(rule.get('traffic_light')or{}).get(t)or{}
def _position(x):return str(x.get('position')or'').strip()
def _cells(model,model_path,records):
	B=records;A=S.record_cells_for(model,model_path)
	if not A and B:
		D,C=IA.current_record(B)
		if C:A=IA.record_cells(C)
	return A or{}
def family_name(model):A=model;C=(A.get('scope_summary')or{}).get('contract_families')or[{}];D=next((B for B in C if B.get('contract_family_id')==A.get('family_id')),C[0])or{};B=A.get('family_label')or D.get('contract_family_name')or'';E=D.get('company_role')or'';return'%s (%s)'%(B,E)if B and E else B
def build_init(model,model_path,records=None,approver=None,workspace_url=None):
	H=workspace_url;C=approver;B=model;L=_cells(B,model_path,records);M=S.derive_status(B,L);N=set(M['approved_keys']);I,J=[],{}
	for A in B.get('rules')or[]:
		D=A['rule_id'];K=[S.cell_key(D,B)for B in S.TRACKS if _position(_track(A,B))]
		if not K or all(A in N for A in K):continue
		E=_track(A,'green');F=[A for A in A.get('legal_review_required')or[]if isinstance(A,dict)];I.append({'id':D,'t':A.get('topic_name')or'','imp':A.get('importance')or'','g':_position(E),'y':_position(_track(A,'yellow')),'r':_position(_track(A,'red')),'areo':E.get('basis')=='areo_proposal','n':len(E.get('evidence')or[]),'legal':bool(F)})
		if F:J[D]=str(F[0].get('concern')or'').strip()
	G={'mode':'approve','family':family_name(B),'positions':I,'legal':J}
	if C and IA._is_person_name(C.get('name')or''):G['approver']={'name':C['name'],'role':C.get('role')or''}
	if H:G['workspace_url']=H
	return G
def write_page(page,init,out):
	with io.open(page,encoding='utf-8')as A:B=A.read()
	if MARKER not in B:raise SystemExit('בעמוד אין את הסימון %s'%MARKER)
	C=json.dumps(init,ensure_ascii=False).replace('</','<\\/')
	with io.open(out,'w',encoding='utf-8')as A:A.write(B.replace(MARKER,C,1))
def _run(args):A=subprocess.run([sys.executable,'-B',CLI]+args,capture_output=True,text=True);return A.returncode,(A.stdout or'')+(A.stderr or'')
def reply_for(batch,by_rule):
	F=by_rule;C=batch;D=C.get('items')or[]
	if C.get('stage')=='batch':
		E=[A['n']for A in D if(F.get(A['rule_id'])or{}).get('decision')not in('approved','approved_after_legal_review')]
		if len(E)==len(D):return'לדלג על המנה'
		return'לאשר הכול'+(' חוץ מ-'+', '.join(map(str,E))if E else'')
	if C.get('stage')=='topics':
		B=[]
		for A in D:
			G=(F.get(A['rule_id'])or{}).get('decision')
			if G in('approved','approved_after_legal_review'):H=any(A.get('legal')for A in A.get('cells')or[]);B.append('%d %s'%(A['n'],'נבדק ולאשר'if H else'לאשר'))
			elif G=='legal_review_later':B.append('%d לעורך דין'%A['n'])
			else:B.append('%d לדלג'%A['n'])
		return'\n'.join(B)
def apply(dec,model_path,core,index,records,word=None,workspace=None,local_copy_dir=None):
	B=records;A=model_path;H=dec.get('approver')or{};I={A.get('rule_id'):A for A in dec.get('decisions')or[]if A.get('rule_id')};D,C=[],False
	for J in('batch','topics'):
		for P in range(MAX_ROUNDS):
			E,F=_run(['--queue','--stage',J,'--model',A,'--records',B])
			if E!=0:D.append(F.strip());C=True;break
			G=IA.open_batch(IA.load_queue(B,_load(A)))
			if not G or G.get('stage')!=J:break
			K=reply_for(G,I)
			if K is None:break
			L=['--answer',K,'--approver',H.get('name')or'','--role',H.get('role')or'','--model',A,'--records',B]
			for(N,M)in(('--core',core),('--index',index),('--word',word),('--workspace',workspace),('--local-copy-dir',local_copy_dir)):
				if M:L+=[N,M]
			E,F=_run(L);D.append(F.strip())
			if E!=0:C=True;break
		if C:break
	O=[A for A in I.values()if A.get('decision')not in('approved','approved_after_legal_review')];return{'log':D,'pending':O,'failed':C,'others':_others(A,B)}
def _others(model_path,records):
	A=model_path;B=_load(A)
	try:C=IA.queue_state(B,_cells(B,A,records),'he',False,(),())
	except Exception:return{}
	return{A:len(C.get(A)or[])for A in('decisions','questions')if C.get(A)}
def main():
	import argparse as G;H=G.ArgumentParser(description=__doc__,formatter_class=G.RawDescriptionHelpFormatter);I=H.add_subparsers(dest='cmd',required=True);C=I.add_parser('init');C.add_argument('--model',required=True);C.add_argument('--records');C.add_argument('--page',required=True);C.add_argument('--out',required=True);C.add_argument('--approver-name');C.add_argument('--approver-role');C.add_argument('--workspace-url');B=I.add_parser('apply');B.add_argument('--decisions',required=True);B.add_argument('--model',required=True);B.add_argument('--core');B.add_argument('--index');B.add_argument('--records',required=True);B.add_argument('--word');B.add_argument('--workspace');B.add_argument('--local-copy-dir',help='כמו ב-ingest_approval.py: תיקיית הבסיס של העותק המקומי');A=H.parse_args()
	if A.cmd=='init':K=_load(A.model);L={'name':A.approver_name,'role':A.approver_role}if A.approver_name else None;F=build_init(K,A.model,A.records,L,A.workspace_url);write_page(A.page,F,A.out);print(json.dumps({'positions':len(F['positions']),'legal':sorted(F['legal'])},ensure_ascii=False));return 0
	M=_load(A.decisions);D=apply(M,A.model,A.core,A.index,A.records,A.word,A.workspace,A.local_copy_dir)
	for N in D['log']:print(N)
	J=D['others']
	if J:print('\nנשארו בתור החלטות שהעמוד אינו מכריע בהן: %s. ממשיכים בהן ב"אישור פלייבוק" בשיחה.'%', '.join('%d %s'%(B,{'decisions':'החלטות הנהלה','questions':'שאלות פתוחות'}[A])for(A,B)in J.items()))
	if D['pending']:
		print('\nנשארו פתוחים (לא אושרו בעמוד):')
		for E in D['pending']:print('- %s: %s%s'%(E.get('rule_id'),E.get('decision'),' · '+E['note']if E.get('note')else''))
	return 3 if D['failed']else 0
if __name__=='__main__':sys.exit(main())
