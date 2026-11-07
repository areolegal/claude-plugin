# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,glob,json,os,subprocess,sys
HERE=os.path.dirname(os.path.abspath(__file__))
NEG=os.path.normpath(os.path.join(HERE,'..','..','contract-negotiation-orchestrator','scripts'))
ASSETS=os.path.normpath(os.path.join(HERE,'..','assets'))
DEFAULT_DASHBOARD_TEMPLATE=os.path.join(ASSETS,'dashboard_template.html')
DEFAULT_WIZARD_TEMPLATE=os.path.join(ASSETS,'wizard_template.html')
def run(name,args,report):B=[sys.executable,'-B']+args;A=subprocess.run(B,capture_output=True,text=True,encoding='utf-8',errors='replace');C=(A.stdout or'')+(A.stderr or'');D='\n'.join(C.strip().splitlines()[-6:]);report.append({'step':name,'ok':A.returncode==0,'exit':A.returncode,'tail':D});return A.returncode==0
def main(argv=None):
	D=argparse.ArgumentParser(description='שלב הסיום של בונה הפלייבוק בקריאה אחת')
	for I in('model','core','data','profile','lang','extract','workspace','out-dir','index','inventory'):D.add_argument('--'+I,required=True)
	D.add_argument('--dashboard-template',default=DEFAULT_DASHBOARD_TEMPLATE);D.add_argument('--wizard-template',default=DEFAULT_WIZARD_TEMPLATE);D.add_argument('--approved-sources',default=None);D.add_argument('--payload',default='payload.json');D.add_argument('--current',default=None);D.add_argument('--artifact',default=None);A=D.parse_args(argv);F=[A for A in(A.model,A.profile,A.extract,A.dashboard_template,A.wizard_template)if not os.path.isfile(A)]
	if F:print(json.dumps({'ok':False,'stopped_at':'inputs','missing':F},ensure_ascii=False,indent=1));return 2
	C=lambda n:os.path.join(HERE,n);B=[];run('core',[C('build_playbook_core.py'),'--model',A.model],B);run('register',[C('register_playbook.py'),'--data',A.data,'--model',A.model,'--core',A.core],B);J=[C('build_workspace_payload.py'),A.model,'--data',A.data,A.payload,'--profile',A.profile,'--lang',A.lang,'--extract',A.extract]+(['--current',A.current]if A.current else[]);run('payload',J,B)
	if not run('enforce',[C('enforce_playbook_checks.py'),A.model,'--extract',A.extract],B):print(json.dumps({'ok':False,'stopped_at':'enforce','steps':B},ensure_ascii=False,indent=1));return 2
	run('validate_data',[C('validate_data.py'),'--data',A.payload],B);K=[C('build_dashboard.py'),A.dashboard_template,A.payload,A.workspace,'--wizard',A.wizard_template,'--lang',A.lang,'--profile',A.profile]+(['--artifact',A.artifact]if A.artifact else[]);run('workspace',K,B);run('word',[C('build_playbook_docx.py'),'--model',A.model,'--profile',A.profile,'--out-dir',A.out_dir],B);G=sorted(glob.glob(os.path.join(A.out_dir,'*.docx')),key=os.path.getmtime);E=G[-1]if G else'';run('validate_model',[C('validate_playbook_model.py'),A.model,'--core',A.core,'--index',A.index,'--word',E,'--workspace',A.workspace,'--inventory',A.inventory,'--extract',A.extract]+(['--approved-sources',A.approved_sources]if A.approved_sources else[]),B)
	if os.path.isfile(os.path.join(NEG,'check_playbook_contract.py')):run('contract',[os.path.join(NEG,'check_playbook_contract.py'),A.model,'--core',A.core],B)
	run('deliverables',[C('check_deliverables.py'),'--word',E,'--workspace',A.workspace],B);H=all(A['ok']for A in B);print(json.dumps({'ok':H,'word':E,'workspace':A.workspace,'steps':B},ensure_ascii=False,indent=1));return 0 if H else 2
if __name__=='__main__':sys.exit(main())
