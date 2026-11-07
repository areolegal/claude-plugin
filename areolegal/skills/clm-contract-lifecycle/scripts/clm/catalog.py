# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import copy,json,os
from clm import i18n
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CATEGORIES=['מועד','זכות שפוקעת','כסף','בטוחה','התחייבות מתמשכת','תנאי מתלה או מפסיק']
CONSEQUENCES={'right_lapses','auto_change','we_breach','opportunity','they_breach_monitor'}
def _read(*A):
	with open(os.path.join(ROOT,*A),encoding='utf-8')as B:return json.load(B)
def _en(section,lang):
	if i18n.norm(lang if lang is not None else i18n.lang())!='en':return
	A=os.path.join(ROOT,'catalog','en.json');return _read('catalog','en.json').get(section)or{}if os.path.exists(A)else{}
def load_events(lang=None):
	A,B=_read('catalog','events.json'),_en('events',lang)
	if B:
		for(C,D)in A.items():D.update({A:B for(A,B)in(B.get(C)or{}).items()if A in('label','action','if_nothing')and B})
	return A
def load_key_clauses(lang=None):
	A,B=_read('catalog','key_clauses.json'),_en('key_clauses',lang)
	if B:A={A:B.get(A)or C for(A,C)in A.items()}
	return A
def load_types(lang=None):
	F=os.path.join(ROOT,'catalog','types');G=_en('types',lang);D={}
	for E in sorted(os.listdir(F)):
		if E.endswith('.json'):
			A=_read('catalog','types',E);B=(G or{}).get(A['type_code'])or{}
			if B:
				A=copy.deepcopy(A);A['label']=B.get('label')or A['label']
				for C in A.get('type_fields',[]):C['label']=(B.get('type_fields')or{}).get(C['key'])or C['label']
			D[A['type_code']]=A
	return D
