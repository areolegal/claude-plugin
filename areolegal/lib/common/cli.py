# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,os,sys
SOURCE_DIR_NAMES='מהצד-שכנגד','מהצד שכנגד','מהצד_שכנגד','קבצי-מקור','מקור','source','sources-in','from-counterparty','incoming'
PROTECTED_EXT='.docx','.doc','.docm','.dotx','.pdf','.xlsx','.pptx'
class OutputRefused(Exception):0
def no_bytecode():sys.dont_write_bytecode=True
def _key(p):return os.path.normcase(os.path.realpath(os.path.abspath(p)))
def guard_out(out,inputs=(),source_dirs=(),allow_existing_doc=False):
	B=out
	if not B or not str(B).strip():raise OutputRefused('חסר --out מפורש')
	A=_key(B)
	for D in inputs or():
		if D and _key(D)==A:raise OutputRefused('--out הוא קובץ קלט: %s. פלט לעולם אינו נכתב על קובץ קלט'%D)
	C=[A for A in A.replace('\\','/').split('/')if A];E={os.path.normcase(A)for A in SOURCE_DIR_NAMES}
	if any(A in E for A in C[:-1])or os.path.isdir(A)and C and C[-1]in E:raise OutputRefused('--out בתוך תיקיית מקור של הלקוח (%s): %s'%('/'.join(sorted({A for A in C if A in E})),B))
	for F in source_dirs or():
		G=_key(F)
		if A==G or A.startswith(G.rstrip('\\/')+os.sep):raise OutputRefused('--out בתוך תיקיית מקור של הלקוח: %s'%F)
	if not allow_existing_doc and os.path.isfile(A)and os.path.splitext(A)[1].lower()in PROTECTED_EXT:raise OutputRefused('--out הוא מסמך קיים (%s). פלט JSON או HTML נכתב רק לקובץ חדש או לקובץ פלט'%B)
	return os.path.abspath(B)
def parser(description,out_required=True,out_help=None):A=argparse.ArgumentParser(description=description);A.add_argument('--out',required=out_required,help=out_help or'קובץ הפלט. לעולם לא קובץ קלט ולא תיקיית מקור של הלקוח');return A
def write_json(out,data,inputs=()):
	import json;A=guard_out(out,inputs);B=os.path.dirname(A)
	if B:os.makedirs(B,exist_ok=True)
	with open(A,'w',encoding='utf-8')as C:json.dump(data,C,ensure_ascii=False,indent=1)
	return A
def run(main,argv=None):
	try:return main(argv)
	except OutputRefused as A:
		try:sys.stderr.reconfigure(encoding='utf-8')
		except Exception:pass
		print('refused: %s'%A,file=sys.stderr);return 2
def utf8_stdio():
	for A in(sys.stdout,sys.stderr):
		try:A.reconfigure(encoding='utf-8',errors='replace')
		except(AttributeError,ValueError):pass
DOCX_BAD_EXIT=2
OLE_MAGIC=b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'
STRICT_W='http://purl.oclc.org/ooxml/wordprocessingml/main'
DOCX_MESSAGES={'missing':('הקובץ לא נמצא: %s','File not found: %s'),'ole':('הקובץ %s אינו docx: זה קובץ Word ישן (DOC) או מסמך מוצפן בסיסמה. פתחו אותו ב-Word, הסירו את הסיסמה אם יש, ושמרו בשמירה בשם כ-"Word Document (.docx)".','%s is not a .docx: it is an old Word file (DOC) or a password-protected document. Open it in Word, remove the password if there is one, and use Save As "Word Document (.docx)".'),'not_zip':('הקובץ %s פגום, או שאינו מסמך Word (אינו ZIP תקין). פתחו אותו ב-Word ושמרו מחדש, או בקשו עותק תקין.','%s is corrupt or is not a Word document (not a valid ZIP). Open it in Word and save it again, or ask for a working copy.'),'no_document':('בקובץ %s אין word/document.xml: זה אינו מסמך Word (אולי Excel, PowerPoint או ZIP אחר).','%s has no word/document.xml: it is not a Word document (perhaps Excel, PowerPoint or another ZIP).'),'bad_xml':('הקובץ %s פגום: word/document.xml אינו XML תקין. פתחו אותו ב-Word ושמרו מחדש.','%s is corrupt: word/document.xml is not valid XML. Open it in Word and save it again.'),'strict':('המסמך %s שמור בתבנית Strict Open XML, שהכלי אינו קורא. פתחו אותו ב-Word ושמרו בשמירה בשם כ-"Word Document (.docx)" (לא "Strict Open XML Document").','%s is saved as Strict Open XML, which this tool does not read. Open it in Word and use Save As "Word Document (.docx)" (not "Strict Open XML Document").'),'unreadable':('לא ניתן לקרוא את %s כמסמך Word (%s).','%s cannot be read as a Word document (%s).')}
def docx_message(kind,path,detail=''):B,C=DOCX_MESSAGES[kind];A=(path,detail)if kind=='unreadable'else(path,);return B%A+'\n'+C%A
def docx_problem(path,strict_ok=False):
	B=path;import zipfile as F
	try:from common.paths import long_path as C
	except ImportError:C=lambda p:p
	A=os.path.basename(str(B))
	try:
		with open(C(str(B)),'rb')as G:D=G.read(8)
	except(FileNotFoundError,IsADirectoryError,NotADirectoryError):return'missing',docx_message('missing',B)
	except OSError as H:return'unreadable',docx_message('unreadable',A,type(H).__name__)
	if D==OLE_MAGIC:return'ole',docx_message('ole',A)
	try:
		with F.ZipFile(C(str(B)))as E:
			if'word/document.xml'not in E.namelist():return'no_document',docx_message('no_document',A)
			D=E.open('word/document.xml').read(4096).decode('utf-8','replace')
	except Exception:return'not_zip',docx_message('not_zip',A)
	if not strict_ok and STRICT_W in D:return'strict',docx_message('strict',A)
def load_docx_or_explain(path,loader=None,strict_ok=False):
	B=loader;A=path;C=docx_problem(A,strict_ok=strict_ok)
	if C:D,E=C;return None,E,1 if D=='missing'else DOCX_BAD_EXIT
	if B is False:return A,None,0
	if B is None:from docx import Document as B
	try:return B(A),None,0
	except Exception as F:return None,docx_message('unreadable',os.path.basename(str(A)),type(F).__name__),DOCX_BAD_EXIT
