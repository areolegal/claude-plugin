# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re,zipfile
DOC_KINDS={'signed','draft','negotiation_version','template','amendment','schedule','order','non_agreement'}
NON_AGREEMENT=re.compile('(גילוי דעת|חוות דעת|מצגת|פרוטוקול|מכתב|memo|presentation)',re.I)
NEGOTIATION=re.compile('(הערות|redline|עקוב אחר שינויים|tracked|edits|טיוטה נגדית|markup)',re.I)
TEMPLATE=re.compile('(תבנית|template|\\(דוגמה\\)|sample)',re.I)
ORDER=re.compile('(הזמנת עבודה|statement of work|\\bsow\\b|order form|purchase order)',re.I)
AMENDMENT=re.compile('(תיקון|תוספת|amendment|addendum)',re.I)
SCHEDULE=re.compile('(נספח|schedule|annex|exhibit)',re.I)
SIGNED=re.compile('(?<!un)(?<!non )(?<!non_)(?<!non\\-)(?<!not )(?<!not_)(?<!not\\-)(?<!לא )(?<!לא_)(?<!לא\\-)(חתום|signed|executed)',re.I)
BLANKS=re.compile('(_{4,}|\\[\\s*_+\\s*\\]|\\.{6,})')
TOC_LEADER=re.compile('\\.{6,}\\s*\\d+\\s*$')
SIGNATURE_LINE=re.compile('^\\s*(חתימה|חתימת|שם|signature|name)\\b',re.I)
def count_blanks(paragraphs):
	A=0
	for B in paragraphs:
		if SIGNATURE_LINE.match(B):continue
		A+=len(BLANKS.findall(TOC_LEADER.sub('',B)))
	return A
def docx_signals(path):
	try:
		with zipfile.ZipFile(path)as B:A=B.read('word/document.xml').decode('utf-8','ignore');C='word/comments.xml'in B.namelist()
	except(KeyError,zipfile.BadZipFile,OSError):return{'readable':False}
	D=[re.sub('<[^>]+>','',A)for A in A.split('</w:p>')];return{'readable':True,'tracked_changes':'<w:ins 'in A or'<w:del 'in A,'comments':C,'blanks':count_blanks(D)}
DRAFT=re.compile('(טיוטה|\\bdraft\\b|unsigned|non[ _\\-]signed|not[ _\\-]signed|לא חתום)',re.I)
def says_draft(name):return bool(DRAFT.search(name)or NEGOTIATION.search(name))
def says_signed(name):A=name.replace('\\','/').split('/')[-1];return bool(SIGNED.search(A))
def suggest(name,signals=None):
	B=signals or{};A=re.sub('\\.(docx|pdf|doc|txt|md|eml)$','',name.replace('\\','/').split('/')[-1],flags=re.I)
	if NON_AGREEMENT.search(A):return'non_agreement',['שם הקובץ מעיד על מסמך שאינו הסכם']
	if B.get('tracked_changes')or B.get('comments'):return'negotiation_version',['עקוב אחר שינויים או הערות בקובץ']
	if NEGOTIATION.search(A):return'negotiation_version',['שם הקובץ מעיד על טיוטה עם הערות']
	if TEMPLATE.search(A):return'template',['שם הקובץ מעיד על תבנית']
	if ORDER.search(A):return'order',['שם הקובץ מעיד על הזמנת עבודה']
	if AMENDMENT.search(A):return'amendment',['שם הקובץ מעיד על תיקון']
	if SCHEDULE.search(A):return'schedule',['שם הקובץ מעיד על נספח']
	if SIGNED.search(A):return'signed',['שם הקובץ מעיד על הסכם חתום']
	if B.get('blanks',0)>=5:return'template',['שדות ריקים רבים בגוף המסמך']
	return'draft',['אין סימן מובהק בשם או בקובץ; ההכרעה בחילוץ']
