#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,os,sys
HERE=os.path.dirname(os.path.abspath(__file__))
SCRIPTS=os.path.join(os.path.dirname(HERE),'skills','contract-playbook-builder','scripts')
def block(msg):sys.stderr.write(msg+'\n');return 2
def main():
	try:C=json.load(sys.stdin)
	except ValueError:return 0
	D=C.get('tool_name')
	if D not in('WebSearch','WebFetch'):return 0
	sys.dont_write_bytecode=True;sys.path.insert(0,SCRIPTS)
	try:import market_research as B;A=B.load_session()
	except Exception:return 0
	if not A:return 0
	if D=='WebFetch':return block('Areo: מושב מחקר פתוח. קריאה של מסמך במחקר עוברת רק ב-market_research.py fetch (זהות גלויה, קצב, אתרים לפי סוג המקור, יומן). בסוף המחקר: market_research.py stop.')
	F=(C.get('tool_input')or{}).get('query')or''
	try:G=B.load(A['corpus'],'החילוץ')if A.get('corpus')else None;H=B.load(A['profile'],'הפרופיל')if A.get('profile')else None;I='legal'if A.get('statutes')else'market';E=B.check_query(F,I,A['family_dir'],G,H,A.get('statutes')or(),via='hook')
	except BaseException as J:return block('Areo: בדיקת השאילתה נכשלה (%s), ולכן החיפוש לא נשלח.'%type(J).__name__)
	if E:return block('Areo: השאילתה נעצרה ולא נשלחה: %s. חפש בשאילתה כללית: סוג ההסכם, נושא הסעיף, הצד, תחום השיפוט והענף בלבד.'%E)
	return 0
if __name__=='__main__':sys.exit(main())
