# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,json,re,sys
from pathlib import Path
LIB=Path(__file__).resolve().parents[1]
if str(LIB)not in sys.path:sys.path.insert(0,str(LIB))
from app import build_app as B
from app import clm_view,nego_view,policy_view
PAGES=('apps/policy.html','var P=',policy_view.MARKER,policy_view.TEMPLATE),('apps/nego.html','const DATA=',nego_view.MARKER,nego_view.TEMPLATE),('apps/clm.html','const D=areoData(',clm_view.MARKER,clm_view.TEMPLATE)
SHELL_PREFIX='const SHELL='
class Unreadable(Exception):0
def _parts(v):
	try:return tuple(int(A)for A in str(v).split('.'))
	except ValueError:return()
def extract(html,prefix):
	A=prefix;C=html.find(A)
	if C<0:raise Unreadable('לא נמצא %s'%A)
	B=html[C+len(A):];B=B.replace('<\\!--','<!--')
	try:D,F=json.JSONDecoder().raw_decode(B)
	except ValueError as E:raise Unreadable('%s: %s'%(A,E))
	return D
def _title(html):A=re.search('<title>([^<]*)</title>',html or'');return A.group(1).strip()if A else B.DEFAULT_TITLE
def check(old_dir):
	E=Path(old_dir)/'index.html'
	if not E.is_file():raise Unreadable('אין index.html')
	A=extract(E.read_text(encoding='utf-8'),SHELL_PREFIX)
	if not isinstance(A,dict):raise Unreadable('SHELL אינו אובייקט')
	C,D=str(A.get('built_with')or''),B.plugin_version();F=bool(D)and(not C or _parts(C)<_parts(D));return F,C,D,A
def refresh(old_dir,out_dir):
	E=out_dir;D=old_dir;D,E=Path(D),Path(E);V,M,I,F=check(D)
	if not V:return{'stale':False,'built_with':M,'current':I}
	G=E/'apps';G.mkdir(parents=True,exist_ok=True);A,N={},[]
	for(H,W,O,P)in PAGES:
		Q=D/H
		if not Q.is_file():
			if H=='apps/clm.html':continue
			raise Unreadable('חסר %s'%H)
		X=extract(Q.read_text(encoding='utf-8'),W);C=Path(P).read_text(encoding='utf-8')
		if C.count(O)!=1:raise Unreadable('בתבנית %s אין את הסמן פעם אחת'%P)
		R=E/H;R.write_text(C.replace(O,policy_view.to_js(X)),encoding='utf-8');A[H]=str(R)
	J=B.CLM in(F.get('products')or())and'apps/clm.html'in A
	if not J:A.pop('apps/clm.html',None);N.append('apps/clm.html')
	S=str(F.get('company')or'');B.render_playbook(S,G/'playbook.html');A['apps/playbook.html']=str(G/'playbook.html');B.render_playbook(S,G/'setup.html',mode='setup',has_clm=J);A['apps/setup.html']=str(G/'setup.html');F=dict(F,built_with=I,start='');T=_title((D/'index.html').read_text(encoding='utf-8'));K=E/'index.html';C=B.inject(B.TEMPLATE.read_text(encoding='utf-8'),F);C=C.replace('<title>%s</title>'%B.DEFAULT_TITLE,'<title>%s</title>'%B.page_title(T),1);B._write(K,C);L={'index.html':K.stat().st_size};L.update({A:Path(B).stat().st_size for(A,B)in A.items()});Y=sum(L.values());Z={'index':str(K),'title':B.page_title(T),'files':A,'capabilities':B.capabilities(J),'remove':N,'sizes':L,'total_bytes':Y};U=B.publish_spec(Z);U.update(stale=True,built_with=M or None,current=I);return U
def main(argv=None):
	B=argparse.ArgumentParser(description='מערכת שמורה בגרסה קודמת: המסכים של הגרסה הנוכחית, עם הנתונים שלה');B.add_argument('--old',required=True,help='תיקייה עם הקבצים של המערכת השמורה (index.html ו-apps/)');B.add_argument('--out',required=True,help='תיקיית הפלט');A=B.parse_args(argv);sys.dont_write_bytecode=True
	for C in(sys.stdout,sys.stderr):
		try:C.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
	if not Path(A.old).is_dir():sys.stderr.write('התיקייה אינה קיימת: %s\n'%A.old);return 2
	try:D=refresh(A.old,A.out)
	except Unreadable as E:print(json.dumps({'stale':None,'error':str(E)},ensure_ascii=False));return 3
	print(json.dumps(D,ensure_ascii=False));return 0
if __name__=='__main__':sys.exit(main())
