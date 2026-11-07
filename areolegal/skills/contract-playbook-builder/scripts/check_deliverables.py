# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,json,os,sys,zipfile
def _html_ok(path,must):
	try:
		with open(path,encoding='utf-8')as B:A=B.read()
	except(OSError,UnicodeDecodeError):return False
	return len(A)>2000 and all(B in A for B in must)
def check(word,workspace,wizard=None):
	C=word;B=workspace;A=[]
	if not C or not os.path.isfile(C):A.append('word: missing')
	else:
		try:
			with zipfile.ZipFile(C)as D:
				if'word/document.xml'not in D.namelist():A.append('word: not a valid docx')
		except(zipfile.BadZipFile,OSError):A.append('word: not a valid docx')
	if not B or not os.path.isfile(B):A.append('workspace: missing')
	elif not _html_ok(B,('AREO-KIT:BEGIN','<html')):A.append('workspace: not built from the template')
	if B and os.path.isfile(B)and not _html_ok(B,('"wizard_doc":','vApprove')):A.append('workspace: the decide-and-approve tab is missing (build with --wizard)')
	return A
def main(argv=None):A=argparse.ArgumentParser(description='שער המסירה: Word, וסביבת עבודה עם לשונית הכרעה ואישור');A.add_argument('--word',required=True);A.add_argument('--workspace',required=True);A.add_argument('--wizard',default=None,help='לא נדרש עוד: דף האישור משובץ בסביבת העבודה');B=A.parse_args(argv);C=check(B.word,B.workspace,B.wizard);print(json.dumps({'ok':not C,'problems':C},ensure_ascii=False));return 0 if not C else 2
if __name__=='__main__':sys.exit(main())
