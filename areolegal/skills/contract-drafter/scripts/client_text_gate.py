# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,re
HEB_CH=re.compile('[\u0590-\u05ff]')
HEB_RUN=re.compile('[\u0590-\u05ff][\u0590-\u05ff"\'״׳ -]*')
CODE_RX=re.compile('(?<![\\w-])(?:R\\d{1,3}|(?:DOC|AGR|REG|MAND|PB|DEAL)-[\\w.]*\\d[\\w.]*)(?![\\w-])|\\bmode\\s*\\d|מצב\\s*\\d|\\bstate\\s*\\d',re.I)
LOCAL_PATH_RX=re.compile('(?<![A-Za-z0-9])[A-Za-z]:[\\\\/](?![\\\\/])\\S{2,}|[\\\\/]Users[\\\\/]|OneDrive|(?<![\\w.])\\.\\./')
PLAYBOOK_RX=re.compile('פלייבוק|פלי"בוק|\\bplaybook\\b',re.I)
HOLD_RX=re.compile('ממתי(?:ן|נה|נים|נות)\\s+ל(?:אישור|בדיקת)\\s+(?:של\\s+)?(?:עורך|עורכת|יועץ|היועץ|הממונה)|טעונ?(?:ה|ים|ות|ן)\\s+אישור\\s+(?:של\\s+)?(?:עורך|עורכת|יועץ|היועץ)|טרם\\s+(?:נבדק|אושר)\\w*\\s+(?:ב?יד[יי]|על[\\s-]ידי)\\s+(?:עורך|עורכת|יועץ)|אל\\s+תשלח\\w*\\s+(?:עד|לפני)\\s+(?:ש|אישור)|אין\\s+לשלוח\\s+(?:עד|לפני)\\s+(?:ש|אישור)|\\bpending\\s+(?:lawyer|legal|counsel|attorney)\\s+(?:review|approval)|\\bawait(?:s|ing)\\s+(?:lawyer|legal|counsel|attorney)\\b|\\bnot\\s+(?:yet\\s+)?(?:reviewed|approved)\\s+by\\s+(?:a\\s+)?(?:lawyer|counsel|attorney)\\b|\\bdo\\s+not\\s+send\\s+(?:until|before)\\b',re.I)
NO_SOURCE_NOTE='AREO לא מצאה מקור מורשה לנקודה זו'
NO_SOURCE_NOTE_EN='AREO did not find an approved source for this point'
STYLE_ONLY='בהתאם ל','יש לציין','please','successfully'
ANNEX_REF=re.compile('^[A-Z]-\\d{1,2}$')
def english_parties(d,prof,rtl,clean):
	D=clean;B=prof
	if rtl:return d,[]
	B=B or{};C,F=D(B.get('organization_name')),D(B.get('organization_name_en'));d=json.loads(json.dumps(d));E=[]
	for G in(d.get('meta')or{}).get('parties')or[]:
		A=D(G.get('name'))
		if not HEB_CH.search(A):continue
		if F and C and(A==C or C in A or A in C):G['name']=F
		else:E.append(A)
	if E:return d,['העסקה באנגלית, אבל השם הרשום באנגלית חסר: %s. שואלים את הלקוח מה השם הרשום של הצד באנגלית (אצל החברה: organization_name_en בפרופיל), ולא מתעתקים.'%', '.join(E)]
	return d,[]
def client_text_problems(paths,rtl,docx_text,voice_check=None):
	H=voice_check;A=[]
	for(F,I)in enumerate(paths):
		if not I:continue
		D=('הטיוטה','דף הליווי')[F];B=docx_text(I,limit=2000000)[0]
		for C in LOCAL_PATH_RX.finditer(B):A.append('%s: נתיב מקומי של קובץ בטקסט: "%s". כותבים את שם הקובץ בלבד.'%(D,C.group(0)[:60]));break
		for C in CODE_RX.finditer(B):A.append('%s: קוד או מונח פנימי בטקסט: "%s". מנסחים אותו במילים של הלקוח.'%(D,C.group(0)))
		for C in HOLD_RX.finditer(B)if F==1 else():A.append('%s: נוסח של שער אישור או עצירה: "%s". הטיוטה נמסרת נקייה, אחרי השאלות, בלי המתנה לאישור.'%(D,C.group(0)))
		if F==0:
			for J in(NO_SOURCE_NOTE,NO_SOURCE_NOTE_EN):
				if J.lower()in B.lower():A.append('הטיוטה: נוסח פנימי של Areo ("%s") בגוף ההסכם. בגוף ההסכם רק "[להשלמה]"; השורה המלאה נשארת בדף הליווי.'%J)
			for C in PLAYBOOK_RX.finditer(B):A.append('%s: המילה "%s" אינה נכנסת לטקסט ההסכם.'%(D,C.group(0)))
		if H:
			for E in H(B,'document'if F==0 else'ui'):
				if E['term'].lower().startswith(STYLE_ONLY):continue
				if not ANNEX_REF.match(E['term'])and not any(E['term']in A for A in A):A.append('%s: "%s" (%s)'%(D,E['term'],E['say_instead']))
		if not rtl:
			K=sorted({A.group(0).strip()for A in HEB_RUN.finditer(B)})
			if K:A.append('%s: עסקה באנגלית, ובטקסט יש עברית: %s. מתרגמים או מורידים.'%(D,', '.join(K[:6])))
	G=[]
	for L in A:
		if L not in G:G.append(L)
	return G[:12]
