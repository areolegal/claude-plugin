#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'יציאה לרשת של מעריך הסיכונים: בקשה אחת למקור רשמי, דרך שכבת הרשת האחת.'
import argparse,io,json,os,re,sys,tempfile
from urllib.parse import unquote,unquote_plus,urlsplit
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common import net
from common.case_law import case_law_url
from risk.entity_store import EntityStore
from risk.validate_register import APPROVED_SOURCES_ENV,ENTITY_PURPOSE,approved_domains,domain_ok,media_problem,media_rule
MAX_PER_QUESTION=10
def run_dir_for(deal):import hashlib as B;C=B.sha256(os.path.abspath(deal).encode('utf-8')).hexdigest()[:16];A=os.path.join(tempfile.gettempdir(),'areo-net',C);os.makedirs(A,exist_ok=True);return A
def count_question(run_dir,question):
	B=question;import datetime as E;D=os.path.join(run_dir,'questions-%s.json'%E.date.today().isoformat())
	try:
		with io.open(D,encoding='utf-8')as C:A=json.load(C)
	except(OSError,ValueError):A={}
	A[B]=A.get(B,0)+1
	with io.open(D,'w',encoding='utf-8')as C:json.dump(A,C)
	return A[B]
REGISTRY='ישויות.json'
def registry_for(profile_path,registry_path=None):
	B=profile_path;A=registry_path
	if A:return A if os.path.isfile(A)else None
	if not B:return
	C=os.path.dirname(os.path.abspath(B))
	for D in(os.path.join(C,REGISTRY),os.path.join(os.path.dirname(os.path.dirname(C)),REGISTRY)):
		if os.path.isfile(D):return D
def names_from(profile_path,registry_path=None):
	B=profile_path;C=[]
	if B:
		with io.open(B,encoding='utf-8')as D:F=json.load(D)
		C+=[F.get('organization_name'),F.get('organization_name_en')]
	G=registry_for(B,registry_path)
	if G:
		try:
			with io.open(G,encoding='utf-8')as D:H=(json.load(D)or{}).get('entities')or[]
		except(OSError,ValueError):H=[]
		C+=[A.get('name')for A in H if isinstance(A,dict)]
	E=[]
	for A in C:
		A=str(A or'').strip()
		if len(A)>=2 and A.casefold()not in{A.casefold()for A in E}:E.append(A)
	return E
def out(res,code):print(json.dumps(res,ensure_ascii=False,indent=1));return code
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8');B=argparse.ArgumentParser(description=__doc__.split('\n')[0]);B.add_argument('--deal',required=True,help='תיקיית העסקה: העותק נשמר ב-sources/');B.add_argument('--source-id',required=True,help='מזהה המקור במרשם, למשל SRC-01');B.add_argument('--url',required=True,help='הכתובת המדויקת של הדף במקור הרשמי');B.add_argument('--purpose',required=True,help='entity: בדיקת רקע על הצד שכנגד, המטרה היחידה שבה המעריך יוצא לרשת. כל ערך אחר מסורב, אלא עם --kind entity (ואז זו השאלה, בלי פרטי הלקוח)');B.add_argument('--question',required=True,help='מזהה השאלה ב-research.question: עד עשר בקשות לשאלה');B.add_argument('--excerpt',help='הקטע המילולי: בדף גדול נשמר רק חלון סביבו');B.add_argument('--profile',help='פרופיל-לקוח.json: שמות החברה, שאסור שיופיעו בשאילתה');B.add_argument('--entities',help='ישויות.json: שמות כל הישויות, שאסור שיופיעו בשאילתה (בלעדיו: ליד הפרופיל, או בשורש Areo-נתונים מעל תיקיית הישות)');B.add_argument('--counterparty',help='השם הפומבי של הצד שכנגד: בבדיקת רקע הוא השאילתה עצמה');B.add_argument('--kind',choices=('regulatory','entity'),default='regulatory',help='entity: כמו --purpose entity. regulatory: מסורב (אין אימות רגולטורי ברשת)');B.add_argument('--registration-no',help='בחקר ישות: מספר הרישום של הצד שכנגד, כפי שהוא בהסכם');B.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: %s, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json; אין רשימת נפילה בקוד)'%APPROVED_SOURCES_ENV);A=B.parse_args(argv)
	if not os.path.isdir(A.deal):print('תיקיית העסקה אינה קיימת: %s'%A.deal);return 2
	if A.approved_sources and not os.path.isfile(A.approved_sources):print('קובץ המקורות המאושרים אינו קיים: %s'%A.approved_sources);return 2
	Q=A.kind==ENTITY_PURPOSE or A.purpose.strip().lower()==ENTITY_PURPOSE
	if not Q:return out({'status':None,'blocked':False,'stored':None,'source_class':None,'reason':'refused: מעריך הסיכונים יוצא לרשת רק לבדיקת רקע על הצד שכנגד, לבקשת הלקוח (--purpose entity). דרישה רגולטורית שלא אומתה במסמכים או בפלייבוק מסומנת "טעון בדיקה משפטית", בלי יציאה לרשת'},3)
	E=case_law_url(A.url)
	if E:return out({'status':None,'blocked':False,'stored':None,'source_class':None,'reason':'refused: %s. הליכים משפטיים נגד הצד שכנגד הם משימה לעורך הדין, "טעון בדיקה משפטית"'%E},3)
	G,R=approved_domains(A.approved_sources,ENTITY_PURPOSE)
	if not R:return out({'status':None,'blocked':False,'stored':None,'source_class':None,'reason':'refused: קובץ המקורות המאושרים (מקורות-מאושרים.json) לא נקרא. אין רשימת נפילה: העותק נארז בתוסף (lib/מקורות-מאושרים.json); נתיב אחר עובר ב---approved-sources'},3)
	if any(net.rule_matches(A.url,B)for B in getattr(G,'refuse',())):return out({'status':None,'blocked':False,'stored':None,'source_class':None,'reason':'refused: מדור פסיקה ברשימה (case_law_only). פסיקה רק ממחבר פסיקה סגור (כלל 1.1)'},3)
	C='official'if domain_ok(A.url,G)else None
	if not C:
		E=media_problem(A.url,A.approved_sources,ENTITY_PURPOSE)
		if E:return out({'status':None,'blocked':False,'stored':None,'source_class':None,'reason':'refused: לא מקור רשמי ברשימה, ולא כלי תקשורת (%s): %s'%(urlsplit(A.url).hostname,E)},3)
		C='media'
	H=names_from(A.profile,A.entities);L=unquote(urlsplit(A.url).path)
	for I in H:
		if I and I.casefold()in L.casefold():return out({'status':None,'blocked':False,'stored':None,'reason':'refused: פרט של הלקוח או של העסקה בכתובת (%s)'%I},3)
	for J in re.findall('(?<!\\d)\\d{9}(?!\\d)',L):
		if net._id_check_digit(J)and J!=(A.registration_no or''):return out({'status':None,'blocked':False,'stored':None,'reason':'refused: מספר חברה או זהות בכתובת (%s)'%J},3)
	D=unquote_plus(urlsplit(A.url).query or'')+' '+A.purpose
	if C=='media':D=re.sub('\\d{5,}',lambda m:m.group(0)if net._id_check_digit(m.group(0))else' ',D)
	if not(A.counterparty or A.registration_no):print('בבדיקת רקע נדרשים --counterparty או --registration-no: השאילתה בנויה רק מהם');return 2
	for M in(A.counterparty,A.registration_no):
		if M:D=D.replace(M,' ')
	N=next((A for A in H if A.casefold()in D.casefold()),'')or net.client_detail_in_query(D,H)
	if N:return out({'status':None,'blocked':False,'stored':None,'reason':'refused: פרט של הלקוח או של העסקה בשאילתה (%s). השאילתה נבנית מהשאלה בלבד'%N},3)
	O=run_dir_for(A.deal);S=count_question(O,A.question)
	if S>MAX_PER_QUESTION:return out({'status':None,'blocked':False,'stored':None,'reason':'refused: %d בקשות לשאלה %s. עוצרים, ומה שלא נמצא נכתב בפרק 5'%(MAX_PER_QUESTION,A.question)},3)
	if C=='media':P=net.registrable_domain((urlsplit(A.url).hostname or'').lower()),
	else:P=G
	T='entity: בדיקת רקע על הצד שכנגד'if A.purpose.strip().lower()==ENTITY_PURPOSE else A.purpose;K=net.fetch(A.url,T,allowed_domains=P,store=EntityStore(A.deal),source_id=A.source_id,excerpt=A.excerpt,run_dir=O);F={A:B for(A,B)in K.items()if A not in('content','text')};F['question']=A.question;F['source_class']=C
	if C=='media':F['label']=media_rule(A.approved_sources)['label']
	U=bool(K.get('stored'))and not K.get('blocked');return out(F,0 if U else 3)
if __name__=='__main__':sys.exit(main())
