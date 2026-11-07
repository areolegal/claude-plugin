# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
SIGNING_BLANKS={'he':'________ (יושלם בחתימה)','en':'________ (to be completed at signing)'}
SIGNING_BLANK=SIGNING_BLANKS['he']
COMPANY_PREFIXES='51','52'
OTHER_PREFIXES={'55':'שותפות','56':'חברת חוץ','57':'אגודה שיתופית','58':'עמותה','50':'גוף ציבורי','53':'גוף ציבורי או מוסד','54':'גוף ציבורי או מוסד','59':'גוף ציבורי או מוסד'}
ISRAELI_FORMS='חברה ממשלתית','עמותה','אגודה שיתופית','חברת חוץ','חל״צ','חל"צ','Government company','Non-profit association (amuta)','Public benefit company (PBC)','Cooperative society','Foreign company registered in Israel'
ALLOWED_SOURCES='profile','signed_agreement','incorporation_certificate','letterhead','client_answer'
COMPLETE_AT_SIGNING=re.compile('נשלים\\s+(לפני|ב)\\s*(ה)?חתימה|יושלם\\s+(לפני|ב)\\s*(ה)?חתימה|נמלא\\s+(לפני|ב)\\s*(ה)?חתימה|complete(d)?\\s+(at|before)\\s+signing|to be completed at signing')
def check_digit_ok(num):
	if not re.fullmatch('\\d{9}',num):return False
	B=0
	for(C,D)in enumerate(num):A=int(D)*(1 if C%2==0 else 2);B+=A if A<10 else A-9
	return B%10==0
def normalize(raw):return re.sub('[\\s\\-.\u200e\u200f]','',str(raw or''))
def israeli_registry(profile):
	B=profile or{};C=str(B.get('incorporation_country')or B.get('incorporation_country_name')or'').strip();A=str(B.get('organization_type')or'').strip()
	if A.startswith('חברת חוץ'):return True
	if C:return C.upper()in('IL','ISR','ISRAEL')or C=='ישראל'
	if A.startswith('חברה זרה')or A.startswith('Foreign company (not'):return False
	if A.startswith(ISRAELI_FORMS):return True
def validate_company_number(raw,expect_company=True,israeli=True):
	B=normalize(raw);A={'raw':raw,'number':B,'valid':False,'kind':None}
	if not B:A['reason']='missing';return A
	if israeli is False:A.update(valid=True,reason='foreign_not_checked',kind='foreign');return A
	if not B.isdigit():A['reason']='not_digits';return A
	if len(B)!=9:A['reason']='wrong_length';A['length']=len(B);return A
	if not check_digit_ok(B):A['reason']='bad_check_digit';return A
	C=B[:2];A['kind']='company'if C in COMPANY_PREFIXES else OTHER_PREFIXES.get(C,'unknown_prefix')
	if expect_company and C not in COMPANY_PREFIXES and C not in OTHER_PREFIXES:A['reason']='not_company';return A
	A['valid']=True;A['reason']='ok';return A
def validate_person_id(raw):
	B=raw;A=normalize(B)
	if not A.isdigit()or not 5<=len(A)<=9:return{'raw':B,'number':A,'valid':False,'reason':'wrong_length'}
	A=A.zfill(9);C=check_digit_ok(A);return{'raw':B,'number':A,'valid':C,'reason':'ok'if C else'bad_check_digit'}
def resolve_company_number(profile_value,document_values=(),folder_names=(),israeli=True):
	G=israeli;F=profile_value;A,D=[],[]
	if F:A.append(('profile',validate_company_number(F,israeli=G)))
	for(E,H)in document_values:
		if E not in ALLOWED_SOURCES:D.append((E,H));continue
		A.append((E,validate_company_number(H,israeli=G)))
	for I in folder_names:D.append(('folder_name',I))
	C=sorted({A['number']for(B,A)in A if A['valid']});B={'checks':A,'ignored':D,'number':None}
	if not A:B.update(status='missing',ask=True)
	elif len(C)>1:B.update(status='conflict',ask=True)
	elif len(C)==1 and all(A['valid']for(B,A)in A):B.update(status='confirmed',ask=False,number=C[0])
	elif len(C)==1:B.update(status='invalid',ask=True,recommended=C[0])
	else:B.update(status='invalid',ask=True)
	return B
def signing_blank(lang='he'):return SIGNING_BLANKS.get(lang,SIGNING_BLANKS['he'])
def is_complete_at_signing(answer):A=answer;return bool(A and COMPLETE_AT_SIGNING.search(str(A)))
def detail_for_draft(detail,answer=None,value=None,validator=None,lang='he'):
	B=validator;A=value
	if A is not None:
		C=True if B is None else B(A).get('valid',False)
		if C:return A,'value'
	if is_complete_at_signing(answer):return signing_blank(lang),'signing_blank'
	return None,'open'
