#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'בדיקת risk-register.json (ודוח חקר הישות) לפני בניית הדוח.'
import io,json,os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from common.cli import OutputRefused,guard_out,parser
from common.paths import long_path
from risk import entity_store as ES
from risk import extract_corpus as EC
from risk import validate_register as VR
import risk_states as RS
def load(path,what):
	A=path
	if not A:return
	if not os.path.exists(long_path(A)):print('%s אינו קיים: %s'%(what,A));raise SystemExit(2)
	try:
		with io.open(long_path(A),encoding='utf-8')as B:return json.load(B)
	except ValueError as C:print('%s אינו JSON תקין (%s)'%(what,C));raise SystemExit(2)
def corpus_for_check(corpus):
	A=corpus
	if A is None or isinstance(A,list):return A
	E=A.get('root')or'';C=[]
	for B in A.get('documents')or():
		D=os.path.join(E,B.get('path')or'')
		if B.get('format')in('docx','pdf')and os.path.exists(long_path(D)):C.append(EC.extract(D))
		else:print('אזהרה: %s לא נקרא לבדיקת הציטוטים (%s)'%(B.get('path'),B.get('format')))
	return C
def main(argv=None):
	sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8');B=parser(__doc__.split('\n')[0],out_required=False,out_help='רשימת השגיאות (JSON); לא קובץ קלט');B.add_argument('--data',required=True,help='risk-register.json');B.add_argument('--corpus',help='הפלט של extract_corpus.py: לבדיקת הציטוטים מההסכם');B.add_argument('--deal',help='תיקיית העסקה: העותקים הגולמיים של המקורות');B.add_argument('--state',help='negotiation_state.json של העסקה');B.add_argument('--profile',help='פרופיל-לקוח.json');B.add_argument('--playbook-status',help='מעמד הפלייבוק, משער המדיניות');B.add_argument('--entity',help='entity-report.json, כשנעשתה בדיקת רקע לבקשת הלקוח');B.add_argument('--purpose',choices=(VR.ENTITY_PURPOSE,),help='entity: בדיקת רקע על הצד שכנגד, המטרה היחידה שמתירה את מקורות בדיקת הרקע ואת התקשורת (דוח בדיקת הרקע נבדק כך גם בלעדיו)');B.add_argument('--amendments',help='JSON: רשימת התיקונים הידועים בחוקים שהמרשם נשען עליהם');B.add_argument('--approved-sources',help='מקורות-מאושרים.json (ברירת מחדל: משתנה הסביבה %s, ואחריו העותק שבתוסף, lib/מקורות-מאושרים.json)'%VR.APPROVED_SOURCES_ENV);B.add_argument('--case-law-connector',help='שם מחבר הפסיקה הסגור שהלקוח חיבר בהפעלה הזו (כלל 1.1). בלעדיו, אזכור פסק דין בטקסט המוצג הוא שגיאה');A=B.parse_args(argv);G=load(A.data,'המרשם');D=A.state
	if D and not os.path.exists(long_path(D))and(G.get('meta')or{}).get('scope')!='deal':print('אזהרה: אין קובץ מצב (%s); המרשם אינו של עסקה, והבדיקה רצה בלי קובץ מצב'%D);D=None
	try:C,E=VR.validate(G,corpus_for_check(load(A.corpus,'החילוץ')),A.deal,load(D,'קובץ המצב'),load(A.profile,'הפרופיל'),load(A.playbook_status,'מעמד הפלייבוק'),load(A.amendments,'רשימת התיקונים'),A.approved_sources,A.case_law_connector)
	except(AttributeError,TypeError,KeyError)as F:print('שגיאה: המרשם אינו במבנה של הסכמה 3.6, והבדיקה נעצרה (%s: %s)'%(type(F).__name__,F));print('הדוח אינו נבנה. תקן את המרשם והרץ שוב.');return 3
	H,I=RS.check(G);C+=H;E+=I
	if A.entity:C+=['entity '+A for A in VR.validate_entity_report(load(A.entity,'דוח חקר הישות'),A.approved_sources,A.purpose or VR.ENTITY_PURPOSE,A.case_law_connector)]
	if A.deal and os.path.isdir(os.path.join(A.deal,ES.SOURCES_DIR)):C+=['sources '+str(A)for A in ES.audit_deal_dir(A.deal)]
	for J in E:print('אזהרה: %s'%J)
	for K in C:print('שגיאה: %s'%K)
	print('שגיאות: %d, אזהרות: %d'%(len(C),len(E)))
	if C:print('הדוח אינו נבנה. תקן את המרשם והרץ שוב.')
	if A.out:
		L=[A for A in(A.data,A.corpus,D,A.profile,A.playbook_status,A.entity,A.amendments,A.approved_sources)if A]
		try:M=guard_out(A.out,inputs=L)
		except OutputRefused as F:print('סירוב: %s'%F);return 1
		with io.open(M,'w',encoding='utf-8')as N:json.dump({'errors':C,'warnings':E},N,ensure_ascii=False,indent=1)
	return 3 if C else 0
if __name__=='__main__':sys.exit(main())
