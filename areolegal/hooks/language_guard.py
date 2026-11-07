#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,re,sys
HEB=re.compile('[\u0590-\u05ff]')
LAT=re.compile('[A-Za-z]')
NOISE=re.compile('```.*?```|`[^`]*`|https?://\\S+|\\[[^\\]]*\\]\\([^)]*\\)|\\S+\\.(?:docx|html|json|md|py|pdf)\\b',re.S)
def letters(text):A=NOISE.sub(' ',text or'');return len(HEB.findall(A)),len(LAT.findall(A))
def messages(path):
	C,D=[],''
	with open(path,encoding='utf-8')as F:
		for G in F:
			try:B=json.loads(G)
			except ValueError:continue
			H=B.get('message')if isinstance(B.get('message'),dict)else{};A=H.get('content')
			if B.get('type')=='user':
				if isinstance(A,str):C.append(A)
				elif isinstance(A,list):C+=[A.get('text','')for A in A if isinstance(A,dict)and A.get('type')=='text']
			elif B.get('type')=='assistant'and isinstance(A,list):
				E=[A.get('text','')for A in A if isinstance(A,dict)and A.get('type')=='text']
				if any(A.strip()for A in E):D='\n'.join(E)
	return C,D
def main():
	try:
		A=json.load(sys.stdin)
		if A.get('stop_hook_active'):return 0
		B=A.get('transcript_path')or''
		with open(B,encoding='utf-8')as D:
			if'areolegal'not in D.read():return 0
		E,F=messages(B);G,H=letters(' '.join(E))
		if G<=H:return 0
		I,C=letters(F)
		if C<80 or C<=2*I:return 0
	except Exception:return 0
	print(json.dumps({'decision':'block','reason':'ההודעה האחרונה ללקוח נכתבה באנגלית, והשיחה בעברית. כתוב את אותה הודעה מחדש בעברית מלאה, בלי לשנות את התוכן, את המספרים ואת שמות הקבצים, ובלי להוסיף הסבר על השינוי. The last message to the client is in English; rewrite the same message in Hebrew.'},ensure_ascii=False));return 0
if __name__=='__main__':sys.exit(main())
