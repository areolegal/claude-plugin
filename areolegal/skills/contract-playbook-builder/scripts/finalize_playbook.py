# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,glob,json,os,subprocess,sys,tempfile
HERE=os.path.dirname(os.path.abspath(__file__))
NEG=os.path.normpath(os.path.join(HERE,'..','..','contract-negotiation-orchestrator','scripts'))
ASSETS=os.path.normpath(os.path.join(HERE,'..','assets'))
DEFAULT_DASHBOARD_TEMPLATE=os.path.join(ASSETS,'dashboard_template.html')
DEFAULT_WIZARD_TEMPLATE=os.path.join(ASSETS,'wizard_template.html')
def run(name,args,report):B=[sys.executable,'-B']+args;A=subprocess.run(B,capture_output=True,text=True,encoding='utf-8',errors='replace');C=(A.stdout or'')+(A.stderr or'');D='\n'.join(C.strip().splitlines()[-6:]);report.append({'step':name,'ok':A.returncode==0,'exit':A.returncode,'tail':D});return A.returncode==0
def write_log(a,rep,ok):
	try:
		with open(a.model,encoding='utf-8')as B:A=json.load(B)
	except(OSError,ValueError):A={}
	C={}
	try:sys.path.insert(0,HERE);import ladder_checks as D;C=D.load_thresholds(a.model)
	except Exception:pass
	E={'at':__import__('datetime').datetime.now().isoformat(timespec='seconds'),'ok':ok,'steps':[{'step':A.get('step'),'ok':A.get('ok'),'exit':A.get('exit')}for A in rep],'corpus_count':A.get('corpus_count'),'paper_counts':(A.get('scope_summary')or{}).get('paper_counts'),'evidence_class':A.get('evidence_class'),'rules':len(A.get('rules')or[]),'findings':{B:len(A.get(B)or[])for B in('ladder_findings','reliability_findings','evidence_warnings')},'backtest':{B:(A.get('backtest')or{}).get(B)for B in('status','red_rate','reason')},'thresholds':C}
	try:
		with open(os.path.join(os.path.dirname(os.path.abspath(a.model)),'build-log.json'),'w',encoding='utf-8')as B:json.dump(E,B,ensure_ascii=False,indent=1)
	except OSError:pass
def main(argv=None):
	A=argparse.ArgumentParser(description='שלב הסיום של בונה הפלייבוק בקריאה אחת')
	for E in('model','core','data','profile','lang','extract','workspace','out-dir','index','inventory'):A.add_argument('--'+E,required=True)
	A.add_argument('--dashboard-template',default=DEFAULT_DASHBOARD_TEMPLATE);A.add_argument('--wizard-template',default=DEFAULT_WIZARD_TEMPLATE);A.add_argument('--approved-sources',default=None);A.add_argument('--payload',default=None,help='ברירת מחדל: קובץ זמני מחוץ לתיקיית הלקוח, שנמחק בסוף');A.add_argument('--current',default=None);A.add_argument('--artifact',default=None);A.add_argument('--word',action='store_true',help='גם קובץ Word, רק כשהלקוח ביקש קובץ בשיחה');B=A.parse_args(argv);C=[A for A in(B.model,B.profile,B.extract,B.dashboard_template,B.wizard_template)if not os.path.isfile(A)]
	if C:print(json.dumps({'ok':False,'stopped_at':'inputs','missing':C},ensure_ascii=False,indent=1));return 2
	F=lambda n:os.path.join(HERE,n);D=not B.payload
	if D:G,B.payload=tempfile.mkstemp(prefix='areo-payload-',suffix='.json');os.close(G)
	try:return _steps(B,F)
	finally:
		if D:
			try:os.remove(B.payload)
			except OSError:pass
def _skip(name,why,report):report.append({'step':name,'ok':False,'exit':None,'tail':'לא נבנה: %s'%why})
def _steps(a,S):
	A=[];run('evidence',[S('evidence_class.py'),'--model',a.model],A);run('ladder',[S('ladder_checks.py'),'--model',a.model],A);run('reliability',[S('reliability_checks.py'),'--model',a.model,'--extract',a.extract],A);run('related',[S('related_links.py'),'--model',a.model,'--extract',a.extract],A);run('core',[S('build_playbook_core.py'),'--model',a.model],A);run('register',[S('register_playbook.py'),'--data',a.data,'--model',a.model,'--core',a.core],A);F=[S('build_workspace_payload.py'),a.model,'--data',a.data,a.payload,'--profile',a.profile,'--lang',a.lang,'--extract',a.extract]+(['--current',a.current]if a.current else[]);run('payload',F,A)
	if not run('enforce',[S('enforce_playbook_checks.py'),a.model,'--extract',a.extract],A):print(json.dumps({'ok':False,'stopped_at':'enforce','steps':A},ensure_ascii=False,indent=1));return 2
	run('validate_data',[S('validate_data.py'),'--data',a.payload],A);C=[A['step']for A in A if not A['ok']];G=[S('build_dashboard.py'),a.dashboard_template,a.payload,a.workspace,'--wizard',a.wizard_template,'--lang',a.lang,'--profile',a.profile]+(['--artifact',a.artifact]if a.artifact else[])
	if C:_skip('workspace','בדיקה שלפניה נכשלה (%s)'%', '.join(C),A)
	else:run('workspace',G,A)
	B=''
	if a.word and C:_skip('word','בדיקה שלפניו נכשלה (%s)'%', '.join(C),A)
	elif a.word:
		run('word',[S('build_playbook_docx.py'),'--model',a.model,'--profile',a.profile,'--out-dir',a.out_dir],A);E=sorted(glob.glob(os.path.join(a.out_dir,'*.docx')),key=os.path.getmtime);B=E[-1]if E else''
		if B and not run('word_verify',[S('verify_playbook_docx.py'),'--docx',B,'--model',a.model,'--profile',a.profile]+(['--lang',a.lang]if a.lang in('he','en')else[])+(['--artifact',a.workspace]if os.path.isfile(a.workspace)else[]),A):B=''
	run('validate_model',[S('validate_playbook_model.py'),a.model,'--core',a.core,'--index',a.index]+(['--word',B]if B else[])+['--workspace',a.workspace,'--inventory',a.inventory,'--extract',a.extract]+(['--approved-sources',a.approved_sources]if a.approved_sources else[]),A)
	if os.path.isfile(os.path.join(NEG,'check_playbook_contract.py')):run('contract',[os.path.join(NEG,'check_playbook_contract.py'),a.model,'--core',a.core],A)
	if C:_skip('deliverables','סביבת העבודה לא נבנתה',A)
	else:run('deliverables',[S('check_deliverables.py'),'--workspace',a.workspace]+(['--word',B]if B else[]),A)
	D=all(A['ok']for A in A);write_log(a,A,D);print(json.dumps({'ok':D,'word':B,'workspace':a.workspace,'steps':A},ensure_ascii=False,indent=1));return 0 if D else 2
if __name__=='__main__':sys.exit(main())
