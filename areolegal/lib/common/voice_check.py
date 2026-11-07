# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,re,sys,zipfile
if __name__=='__main__':sys.dont_write_bytecode=True
_P='(?<![\\w\u0590-\u05ff])(?:[והבלמשכ]{0,3})'
_E='(?![\\w\u0590-\u05ff])'
_CODE='קוד פנימי: אף פעם לא מוצג'
_STD='(?!(?:ISO|IEC|AES|SHA|RSA|TLS|SSL|SOC|PCI|GPT|COVID|CVE|EN|BS|NIST|SP|UTF|HTTP|IPV|WCAG|W|I|K)-)'
FORBIDDEN=(_P+'מצב\\s*\\d+'+_E,'אף פעם לא מוצג: אמרו מה צריך לעשות','code'),('\\bmode\\s*\\d+\\b','never shown: say what needs to be done','code'),('\\b(?:R\\d{1,3}|[ANQSK]\\d{2,3}[a-z]?)\\b',_CODE,'code'),('\\b'+_STD+'[A-Z]{1,6}(?:-[A-Z]{2,12})*-\\d{1,6}\\b(?!-\\d)',_CODE,'code'),('\\b[A-Z]{1,4}\\d{1,4}#[A-Za-z]{0,2}\\d+\\b',_CODE,'code'),('(?<![\\w/\\\\.@:-])[a-z]+(?:_[a-z0-9]+)+(?![\\w/\\\\.@-])','שם שדה או ערך פנימי: אמרו אותו במילים','code'),('(?<![\\w/\\\\.@:${-])[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+(?![\\w/\\\\.@\\[(-])','ערך פנימי: אמרו אותו במילים','code'),('\\bUserDeclared\\b','הוצהר על ידכם / Declared by you','code'),(_P+'פלייבוק מוצע'+_E,'טיוטת מדיניות, מחכה לאישור שלכם','ui'),('\\bproposed playbook\\b','draft policy, awaiting your approval','ui'),(_P+'מציינ(?:י|ים) חוסר'+_E,'פרטים להשלים','sys'),(_P+'הנושא ונותן'+_E,'Areo, או התוצר עצמו: התגובה, הטיוטה, המדיניות','sys'),(_P+'המנסח'+_E,'Areo, או התוצר עצמו: הטיוטה','ui'),(_P+'סקיל(?:ים)?'+_E,'סוכן / סוכנים','sys'),(_P+'רכיבי המערכת'+_E,'סוכן / סוכנים, או התוצר עצמו','sys'),(_P+'הפעולה נספרה'+_E,'אף פעם לא מוצג ללקוח','sys'),('\\bexit code\\b|קוד יציאה','הבדיקה הממוחשבת עברה / לא עברה','sys'),('\\bred[ -]lines?\\b',"what we won't accept / לא מסכימים",'sys'),(_P+'קווים אדומים'+_E,'מה שלא מקבלים','sys'),(_P+'טעון אישור'+_E,'מחכה לאישור שלכם','ui'),(_P+'סבב\\s*\\d+'+_E,'התגובה הראשונה / התגובה לטיוטה שלהם','ui'),('\\d+\\s+(?:החלטות|הכרעות)'+_E,"מספר רק כשהוא עוזר להחליט: 'X סעיפים מחכים לך'",'ui'),(_P+'כירורגי(?:ים|ות|ת)?'+_E,'תיקונים בתוך הנוסח שלהם, בלי לשנות את המבנה','ui'),(_P+'חסו(?:ם|מה|מים|מות)'+_E,'לפני שליחה צריך עוד אישור אחד','ui'),('[\\"״“”]נבדק[\\"״“”]','אישור עורך דין, לאשר','ui'),(_P+'שער(?:\\s+(?:ה)?איכות)?'+_E,'בדיקה לפני שליחה','ui'),('\\bgate\\b','בדיקה לפני שליחה / check before sending','ui'),(_P+'פלייבוק(?:ים)?'+_E,'אין להזכיר מדיניות פנימית בעותק לצד שכנגד','ext'),('\\bplaybooks?\\b','internal policy is never mentioned in a copy for the counterparty','ext'),(_P+'מדיניות\\s+(?:ה)?חברה'+_E,'אין להזכיר מדיניות פנימית בעותק לצד שכנגד','ext'),('\\b(?:company|our)\\s+polic(?:y|ies)\\b','internal policy is never mentioned in a copy for the counterparty','ext'),(_P+'מסלול(?:ים)?'+_E,'מקובל עלינו / אפשר להתגמש / לא מסכימים','ui'),(_P+'ראי(?:ה|ות)'+_E,'דוגמאות מההסכמים שלכם','ui'),(_P+'קורפוס'+_E,'ההסכמים שלכם','ui'),(_P+'פוזיציה'+_E,'הצד שלכם בהסכם','ui'),(_P+'פרופורציונליות'+_E,'כמה לבקש, ביחס לגודל העסקה','ui'),(_P+'אשכול(?:ות)?'+_E,'סעיפים שקשורים זה לזה','ui'),(_P+'נגזר(?:ה|ו)?'+_E,'למדנו מההסכמים שלכם','ui'),(_P+'גזירה'+_E,'למדנו מההסכמים שלכם','ui'),(_P+'רכיב(?:ים)?'+_E,'סוכן / סוכנים, או התוצר עצמו','ui'),('\\bskills?\\b','agent / agents','ui'),(_P+'יש לציין'+_E,"בלי 'יש לציין'",'ui'),(_P+'בהתאם ל',"בלי 'בהתאם ל'",'ui'),('\\b(?:successfully|please)\\b',"in English: no 'please', no 'successfully'",'ui')
_RX=[(re.compile(A)if B=='code'else re.compile(A,re.I),C,B)for(A,C,B)in FORBIDDEN]
MODES='ui','document','external'
_FILE_EXT='\\.(?:docx?|xlsx?|pptx?|pdf|json|jsonl|md|html?|py|js|css|txt|csv|zip|png|jpe?g)\\b'
_SEG='(?:(?!\\.\\s)[^\\n`\\"”\'():;])*?'
_PATH_RX=re.compile('[`\\"“\'][^`\\"”\'\\n]*?(?:\\\\|://|'+_FILE_EXT+')[^`\\"”\'\\n]*[`\\"”\']|(?:[A-Za-z]:[\\\\/]|\\\\\\\\|\\.\\.?[\\\\/]|(?<![\\w\\u0590-\\u05FF])[\\w\\u0590-\\u05FF.-]+\\\\|(?<![\\w\\u0590-\\u05FF])(?:[\\w\\u0590-\\u05FF.-]+/){2,})(?:'+_SEG+_FILE_EXT+'|[^\\s`\\"”\'()]*)|'+_SEG+_FILE_EXT)
def strip_paths(text):return _PATH_RX.sub(' ',text or'')
def check_text(text,mode='ui'):
	A=text;A=strip_paths(A);B=[]
	for(I,C,E)in _RX:
		if E=='ext'and mode!='external':continue
		if mode in('document','external')and E=='ui':continue
		for D in I.finditer(A or''):B.append((D.start(),D.end(),D.group(0).strip(),C))
	F=[]
	for(G,H,J,C)in B:
		if any(A<=G and H<=B and B-A>H-G for(A,B,C,C)in B):continue
		F.append({'term':J,'say_instead':C})
	return F
_HEB_OR_LAT=re.compile('[A-Za-z\u0590-\u05ff]')
INTERNAL_VALUES={'טעון אישור','edge of the red line','פוזיציה','position'}
_LIBRARY=re.compile('^\\s*/\\*!|Chart\\.js|@license|\\bsourceMappingURL\\b')
def scripted_segments(path,text):
	C=text;A=[]
	if path.lower().endswith(('.html','.htm')):
		def F(m):A=m.group(1);return''if len(A)>150000 or _LIBRARY.search(A[:4000])else A
		D=re.sub('<script\\b[^>]*>(.*?)</script>',F,C,flags=re.S|re.I);A+=re.findall('"([^"\\n]{2,400})"',D);A+=re.findall('>([^<>{}\\n]{2,400})<',D)
	else:A+=re.findall('`([^`\\n]{3,600})`',C);A+=re.findall('"([^"\\n]{3,600})"',C);A+=re.findall('“([^”\\n]{3,600})”',C)
	E=[]
	for B in A:
		if B.strip().strip('.').casefold()in INTERNAL_VALUES:continue
		if not _HEB_OR_LAT.search(B)or re.search('\\.(py|json|md|html|docx|xlsx)\\b|--\\w|^\\s*[\\w./\\\\-]+\\s*$|get_resource|AREO_RT',B):continue
		if path.lower().endswith(('.html','.htm'))and _JS.search(B):continue
		E.append(B)
	return E
_JS=re.compile('\\$\\{|===|!==|=>|\\|\\||&&|[{};]|\\b[A-Za-z_$][\\w$]*\\(|^\\s*[,:)\\]]|[,:(]\\s*$|\\b\\w+:\\s*[\\w\'\\"]|\\w\\|\\w|\\b(?:const|let|var|function|return)\\b')
DOCX_PARTS=re.compile('^word/(?:document|header\\d*|footer\\d*|comments|footnotes|endnotes)\\.xml$')
_T=re.compile('<w:t(?: [^>]*)?>([^<]*)</w:t>')
def _unxml(s):return s.replace('&lt;','<').replace('&gt;','>').replace('&quot;','"').replace('&apos;',"'").replace('&amp;','&')
_ANCHOR=re.compile('^\\s*(?:מזהה הפקה|Issue ID) \\((?:אין לשנות|do not change)\\):')
def docx_segments(path,ours_only=None):
	D=ours_only;E=[]
	with zipfile.ZipFile(path)as B:
		F=B.read('word/document.xml').decode('utf-8','replace')if'word/document.xml'in B.namelist()else'';H=bool(re.search('<w:(?:ins|del) ',F))if D is None else D
		for C in B.namelist():
			if not DOCX_PARTS.match(C):continue
			I=F if C=='word/document.xml'else B.read(C).decode('utf-8','replace')
			for G in re.findall('<w:p[ >].*?</w:p>',I,flags=re.S):
				if H and C=='word/document.xml':A=' '.join(''.join(_T.findall(A))for A in re.findall('<w:ins [^>]*>(.*?)</w:ins>',G,flags=re.S))
				else:A=''.join(_T.findall(G))
				A=_unxml(A)
				if A.strip()and not _ANCHOR.match(A):E.append(A)
	return E
def check_docx(paths,mode='document'):
	A=[]
	for B in paths:
		for C in docx_segments(B):
			for D in check_text(C,mode):A.append(dict(D,file=B,text=C[:160]))
	return A
def check_files(paths,mode=None):
	C=paths;B=[];D=[A for A in C if A.lower().endswith('.docx')]
	if D:B+=check_docx(D,mode or'document')
	for A in C:
		if A.lower().endswith('.docx'):continue
		with io.open(A,encoding='utf-8',errors='replace')as F:G=F.read()
		for E in scripted_segments(A,G):
			for H in check_text(E,mode or'ui'):B.append(dict(H,file=A,text=E[:160]))
	return B
def main(argv=None):
	B=argparse.ArgumentParser(description='בדיקת הקול של Areo: מונחים פנימיים בנוסח ללקוח (areo-voice.md)');B.add_argument('--text',help="הודעה אחת לבדיקה, למשל הודעת המסירה, או פלט של סקריפט שנמסר ללקוח; '-' קורא מהקלט הסטנדרטי");B.add_argument('--files',nargs='+',help='קבצי md, html או docx לבדיקת הנוסחים שהלקוח רואה');B.add_argument('--docx',nargs='+',help='קובצי Word (מצב document): קודים ומילים של המערכת; במסמך עם מעקב שינויים, רק מה שאנחנו הוספנו');B.add_argument('--mode',choices=MODES,help="ui: נוסח ממשק וצ'אט (מחמיר); document: מסמך משפטי; external: עותק לצד שכנגד. ברירת מחדל: ui ל---text ולקבצי md ו-html, document ל-Word");B.add_argument('--json',action='store_true',help='פלט JSON');A=B.parse_args(argv)
	try:sys.stdout.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
	if not A.text and not A.files and not A.docx:B.error('נדרש --text, --files או --docx')
	if A.text=='-':A.text=io.TextIOWrapper(sys.stdin.buffer,encoding='utf-8',errors='replace').read()
	C=check_text(A.text,A.mode or'ui')if A.text else[]
	try:
		if A.files:C+=check_files(A.files,A.mode)
		if A.docx:C+=check_docx(A.docx,A.mode or'document')
	except(OSError,zipfile.BadZipFile)as E:print('לא נקרא כ-Word: %s'%E);return 2
	if A.json:print(json.dumps(C,ensure_ascii=False,indent=1))
	else:
		for D in C:print('%s%s -> %s'%('%s: '%D['file']if D.get('file')else'',D['term'],D['say_instead']))
		print('ממצאים: %d (findings: %d)'%(len(C),len(C)))
	return 3 if C else 0
if __name__=='__main__':sys.exit(main())
