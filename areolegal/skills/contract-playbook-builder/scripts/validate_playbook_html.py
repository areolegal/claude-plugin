#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
from __future__ import annotations
import argparse,io,json,re,sys
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
MUST_BE_REPLACED=['/*__DATA__*/null','/*__CHARTJS__*/','__ENTITY__','__FAMILIES__']
VIEWS=['vOverview','vRules','vSegPolicy','vCompare','vCommercial','vFindings','vAdditions','vPrecedents','vDecisions','vSources','vExport']
INTERACTIONS=['save','tune','globalSearch','openRule','wizLink','localStorage','basisText','covPanel','imposedLayers']
STRUCTURE=['id="nav"','id="wrap"','id="rlist"','id="drawer"','id="pbbar"','normalizeRules','boot']
FORBIDDEN=[('function decide(','כפתור הכרעה: הדף אינו מאשר מדיניות'),('approveAll','כפתור אישור כל הפלייבוק'),('אישור כל הפלייבוק','טקסט אישור כל הפלייבוק'),('נכנס למדיניות','טקסט שאומר שעמדה נכנסה למדיניות'),('function agentPack','חבילת סוכן'),('function officeBlob','ייצוא למסמכי Office'),('function decisionsPack','יומן החלטות כ-JSON'),('ההחלטה שלך','פס הכרעה בסעיף'),('טרם הוכרע','תווית מצב הכרעה'),('נערך ידנית','תווית עריכה של מדיניות'),('id="editChip"','מצב עריכה בדף: הערות והצעות נכתבות באשף'),('class="noteta"','תיבת הערה בסעיף: הערות נכתבות באשף'),('onclick="dlComments()"','כפתור הורדת ההערות: קובץ שאף רכיב אינו קולט'),('confirm(','חלון confirm של הדפדפן: אינו מוצג בעמוד משותף')]
APPROVAL_WORDS=re.compile('>\\s*(?:מאשר|מאשרת|לא מאשר|אושר|אושרו|מאושר)\\s*<|>[^<]{0,40}(?:אישור כל הפלייבוק|נכנס למדיניות|אושר עם שינוי)')
REQUIRED_HE=[('הצעה, לא מדיניות','התווית שמבדילה הצעה ממדיניות'),('נימוקים מלאים','מונה הנימוקים, במקום מונה האישורים'),('שאלות פתוחות','שם המסך שהחליף את מסך ההחלטות')]
MIN_BYTES=150000
DATA_START=re.compile('const D\\s*=\\s*(?=[{\\[])|<script[^>]*id="wzData"[^>]*>\\s*(?=[{\\[])')
def page_chrome(html):
	A=html;B,C=[],0;E=json.JSONDecoder()
	for D in DATA_START.finditer(A):
		if D.start()<C:continue
		try:G,F=E.raw_decode(A,D.end())
		except ValueError:continue
		B.append(A[C:D.end()]);B.append('null');C=F
	B.append(A[C:]);return''.join(B)
def main():
	D=argparse.ArgumentParser();D.add_argument('path');D.add_argument('--lang',default='he',choices=('he','en'));D.add_argument('--artifact',action='store_true',help='תוצר לעמוד משותף: בלי doctype, ובלי מסלולי הורדה');E=D.parse_args()
	try:B=io.open(E.path,encoding='utf-8').read()
	except OSError as H:print('לא ניתן לקרוא את הקובץ: %s'%H);return 1
	C=[]
	for A in MUST_BE_REPLACED:
		if A in B:C.append('סמן הזרקה לא הוחלף: %s, ההזרקה לא הושלמה'%A)
	for A in VIEWS:
		if A not in B:C.append('מסך חסר: %s'%A)
	for A in INTERACTIONS:
		if A not in B:C.append('אינטראקציה חסרה: %s'%A)
	for A in STRUCTURE:
		if A not in B:C.append('רכיב מבנה חסר: %s'%A)
	G=page_chrome(B)
	for(A,F)in FORBIDDEN:
		if A in G:C.append('אסור בדף, %s (%s)'%(F,A))
	for A in APPROVAL_WORDS.findall(G)[:4]:C.append('אסור בדף, שפת אישור בטקסט שהמשתמש רואה: %s'%str(A)[:60])
	if E.lang=='he':
		for(A,F)in REQUIRED_HE:
			if A not in B:C.append('תווית חובה חסרה, %s (%s)'%(F,A))
	if len(B.encode('utf-8'))<MIN_BYTES:C.append('התוצר קטן מ-%d בתים; הנתונים או ספריית הגרפים כנראה לא נכנסו'%MIN_BYTES)
	if E.lang=='he':
		I='dir="rtl"'in B or'setAttribute("dir","rtl")'in B.replace(' ','')
		if not I:C.append('חסרה כיווניות rtl, ותוצר עברי חייב אותה')
		if'—'in B or'–'in B:C.append('נמצא מקף ארוך; אסור בכל תוצר')
	for A in re.findall('(?:src|href)="(http://[^"]{0,120})"',B):C.append('פנייה לא מאובטחת מהדף: %s'%A[:80])
	for A in re.findall('<(?:script|link)[^>]+(?:src|href)="(https://[^"]{0,120})"',B):C.append('הדף טוען מהרשת, ואסור לו: %s'%A[:80])
	if E.artifact:
		if B.lstrip()[:200].upper().startswith('<!DOCTYPE'):C.append('תוצר לעמוד משותף אינו נושא doctype')
		if'publishTarget": "artifact"'not in B and"publishTarget':'artifact'"not in B:C.append('בתוצר המשותף publishTarget אינו artifact')
	if C:
		print('נכשל, %d ממצאים:'%len(C))
		for J in C:print('  - %s'%J)
		print('אין למסור את התוצר. בנה מחדש מהתבנית שנמשכה מהשירות.');return 1
	print('עבר: התוצר הוא סביבת עבודה מלאה (%d מסכים, %d אינטראקציות, %d KB), ואין בו פעולת אישור'%(len(VIEWS),len(INTERACTIONS),len(B.encode('utf-8'))//1024));return 0
if __name__=='__main__':raise SystemExit(main())
