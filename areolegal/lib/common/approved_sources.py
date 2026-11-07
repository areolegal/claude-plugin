# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,json,os,sys
from urllib.parse import urlsplit
if __name__=='__main__':
	_lib=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	if _lib not in sys.path:sys.path.insert(0,_lib)
from common.case_law import case_law_url
from common.net import url_allowed
from risk import validate_register as VR
REFUSED='case_law_only','pending','not_approved','not_on_list','no_list'
def _host(url):
	try:A=(urlsplit(url or'').hostname or'').lower().rstrip('.')
	except ValueError:return''
	return A[4:]if A.startswith('www.')else A
def _host_in(host,dom):A=dom;A=VR._norm_dom(A).partition('/')[0];return bool(A)and(host==A or host.endswith('.'+A))
def _entry(src,jur,kind):
	B={'kind':kind,'jurisdiction':jur.get('jurisdiction_en')or jur.get('jurisdiction_he')or''}
	for A in('body','domain','status','include_subdomains','allowed_paths','include_hosts','restriction_kind','note_en','title','url','topic_he'):
		if src.get(A)not in(None,'',[]):B[A]=src[A]
	return B
def lookup(url,path=None,purpose=None):
	O=purpose;B=url;C=_host(B);A={'url':B,'host':C};H,S=VR._load_sources_file(path)
	if not H:A.update(status='no_list',reason='רשימת המקורות המאושרים (מקורות-מאושרים.json) לא נמצאה או לא נקראה. אף מקור אינו מאושר בלעדיה.');return A
	if not C:A.update(status='not_on_list',reason='אין כתובת תקינה');return A
	J=case_law_url(B);Q=VR.approved_domains(path,O)[0];K=tuple(getattr(Q,'refuse',()))
	if J or url_allowed(B,K)and not url_allowed(B,tuple(A for A in K if not A.startswith('!'))):0
	if J or any(url_allowed(B,(A.lstrip('!'),))for A in K):A.update(status='case_law_only',reason=J or'מסומן ברשימה כמדור פסיקה (case_law_only): פסיקה רק ממחבר פסיקה סגור של הלקוח (כלל 1.1)');return A
	P=[('source',H.get('jurisdictions')or[])]
	if O==VR.ENTITY_PURPOSE:P.append(('entity_check',(H.get('entity_check')or{}).get('jurisdictions')or[]))
	I=None
	for(L,R)in P:
		for E in R:
			for D in E.get('sources')or[]:
				if not isinstance(D,dict):continue
				F=VR._src_rules(D)
				if F and url_allowed(B,VR._rules_obj(F,())):A.update(status='approved',entry=_entry(D,E,L));return A
				if I is None and D.get('status')!='approved'and _host_in(C,D.get('domain')):I=_entry(D,E,L)
			if L=='source':
				for M in E.get('pages')or[]:
					F=VR._page_rule(M)if isinstance(M,dict)else None
					if F and url_allowed(B,(F,)):A.update(status='approved',entry=_entry(M,E,'page'));return A
	if I:A.update(status='pending',entry=I,reason='הגוף ברשימה אך טרם אומת ואושר: אסור עד אישור');return A
	for G in H.get('not_approved_for_legal_conclusions')or[]:
		N=G.get('url')if isinstance(G,dict)else G
		if _host(N)and(_host(N)==C or C.endswith('.'+_host(N))):A.update(status='not_approved',entry={'kind':'not_approved','title':G.get('title')if isinstance(G,dict)else''},reason='ברשימת המקורות שאינם מאושרים למסקנה משפטית');return A
	A.update(status='not_on_list',reason='אינו ברשימת המקורות המאושרים, בדומיין, בתת-דומיין או בנתיב: %s'%C);return A
def main(argv=None):
	sys.dont_write_bytecode=True
	try:sys.stdout.reconfigure(encoding='utf-8')
	except(AttributeError,ValueError):pass
	A=argparse.ArgumentParser(description='בדיקת כתובת אחת מול רשימת המקורות המאושרים, מהדיסק');A.add_argument('--url',required=True);A.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json)');A.add_argument('--purpose',choices=('entity',),help='entity: בדיקת רקע על הצד שכנגד (מעריך הסיכונים בלבד)');B=A.parse_args(argv);C=lookup(B.url,B.approved_sources,B.purpose);print(json.dumps(C,ensure_ascii=False,indent=1));return 0 if C['status']=='approved'else 2 if C['status']=='no_list'else 1
if __name__=='__main__':sys.exit(main())
