# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
HEB=re.compile('[א-ת]')
P={'he':{'terminate':'לסיים|סיום|לבטל את ההסכם','breach':'הפרה|הפר','payment':'תשלום|לשלם','dispute':'חולק|במחלוקת|מחלוקת','d_amount':'סכום|חיוב|שיעור','d_timing':'מועד','setoff':'לקזז|קיזוז|קוזז','term_right':'רשאי לסיים|רשאי לבטל|יסתיים|סיום מיידי','handover':'העברה מסודרת|יעביר[^.\\n]{0,40}(תוצרים|העבודה|המידע|החומרים|הנכס|המושכר|הציוד)|תקופת מעבר|חפיפה|השבת (המושכר|הנכס|הציוד|החומרים)|יחזיר[^.\\n]{0,30}(המושכר|הנכס|הציוד)','ongoing_ctx':'שירותים|תוצרים|אספקה|יספק|המושכר|רישיון|תחזוקה|הפצה|העבודה','conf':'סודיות|בסוד|מידע סודי','conf_duty':'ישמור|לא יגלה|לא ימסור|לא יעביר|ישמרו','law_exc':'(לפי|על פי|מכוח) (כל )?דין|צו (של )?(בית משפט|שיפוטי)|רשות מוסמכת|דרישת רשות|רגולטור|רשות מפקחת','adv_exc':'יועצ(יו|יה|יהם|ים)[^.\\n]{0,20}(המקצועיים|המשפטיים)|רו(א|אה|אי) ה?חשבון|המבקר הפנימי|מבקר הפנים','tp_exc':'(התקבל|שקיבל|קיבל|שהגיע)[^.\\n]{0,60}מצד שלישי','indep':'פותח[^.\\n]{0,20}באופן עצמאי|פיתוח עצמאי|פיתח[^.\\n]{0,20}באופן עצמאי','pay_term':'(ישולם|ישולמו|תשולם|משולמת|ישלם|התשלום|התמורה|דמי \\S+)[^.\\n]{0,80}(בתוך|תוך|מתום|ממועד|(?<!באופן )(?<!בסיס )שוטף(?![\\u05d0-\\u05ea]))','pay_latest':'המועד המאוחר ביותר|המועד המרבי|המועד המירבי|לפי המוקדם|לפי המאוחר','pay_cap_safe':'או (את )?ה?מועד המי?רבי (ה?קבוע |ש)?ב?(דין|חוק)[^.;\\n]{0,40}?,? לפי המוקדם','days':'\\d+\\s*(יום|ימים|ימי עסקים)|\\[\\s*\\d+\\s*\\]\\s*(יום|ימים|ימי עסקים)'},'en':{'terminate':'terminat','breach':'breach','payment':'pay','dispute':'disput','d_amount':'amount|liability|quantum|sum','d_timing':'timing|due date|when due|time of payment','setoff':'set[- ]?off','term_right':'may terminate|right to terminate|immediate termination|terminate this agreement','handover':'hand ?over|transition (period|assistance|services)|orderly (transfer|transition)|deliver (all )?(work|deliverables|materials)|return (of )?the (premises|equipment|goods)|vacate','ongoing_ctx':'\\bservices\\b|deliverables|\\bsupply\\b|premises|licen[cs]e|maintenance|distribut|work product','conf':'Confidential Information|in confidence|confidential','conf_duty':'shall not (disclose|make any public|use)|shall (keep|hold)[^.\\n]{0,40}confiden|(are|as|treat[^.\\n]{0,30}as) Confidential Information','law_exc':'required by (applicable )?law|compelled[^.\\n]{0,20}by law|court order|legal process|regulatory|supervisory authority|governmental authority|competent authority','adv_exc':'advis[eo]rs?|auditors?|accountants?','tp_exc':'(received|obtained|acquired)[^.\\n]{0,80}from a third party|from a third party','indep':'independently developed|developed independently','pay_term':'(shall be paid|shall pay|payable|payment)[^.\\n]{0,80}(within|net|from the end|after receipt|following)','pay_latest':'whichever is (earlier|later)|latest (date|time) permitted|maximum (period|term) permitted','pay_cap_safe':'or (within )?the maximum (period|term) permitted (by|under) (the )?(applicable )?law[^.;\\n]{0,40}?,? whichever is (the )?earlier','days':'\\d+\\s*(calendar |business )?days|net\\s*\\d+'}}
MSG={'GAP_DISPUTE_CARVEOUT':'זכות סיום בעילת אי-תשלום בלי חריג מחלוקת שחל על סכום, מועד וקיזוז','GAP_TERMINATION_HANDOVER':'זכות סיום בלי חובת חפיפה והעברה מסודרת','GAP_CONFIDENTIALITY_EXCEPTIONS':'חובת סודיות בלי החריגים שהחברה עצמה צריכה','GAP_PAYMENT_WORDING':'נוסח תשלום שאינו נוקב מספר ימים, או שמפנה למועד מרבי בדין'}
DOCUMENT_CODES=()
ALL_CODES=tuple(MSG)
def detect_lang(text):return'he'if len(HEB.findall(text or''))>=len(re.findall('[A-Za-z]',text or''))else'en'
def _f(code,extra='',span=None):A=extra;return{'code':code,'message_he':MSG[code]+(': '+A if A else''),'span':span}
def sentences(text):
	C=[]
	for B in re.finditer('[^.?!;\\n]+(?:[.?!;]+|$)',text or''):
		A=B.group(0)
		if A.strip():D=len(A)-len(A.lstrip());C.append((A.strip(),B.start()+D,B.start()+D+len(A.strip())))
	return C
def _s(rx,text,flags=0):return re.search(rx,text or'',flags)
def _paragraphs(doc):return[A for A in(doc or'').split('\n')if A.strip()]
def _dedupe(F):
	B,C=set(),[]
	for A in F:
		D=A['code'],A['message_he'],A['span']
		if D not in B:B.add(D);C.append(A)
	return C
def check_wording(text,lang,topic=None,context=None):
	K=topic;J=text;F=lang;F=F if F in P else detect_lang(J);A=P[F];H=context or{};I=H.get('accept_text')or J;B=re.I if F=='en'else 0;D=[];C=J or'';N=sentences(C)
	if _s(A['terminate'],C,B)and _s(A['breach'],C,B):
		L=[(C,D,E)for(C,D,E)in N if _s(A['dispute'],C,B)]
		if not L and _s(A['payment'],C,B):D.append(_f('GAP_DISPUTE_CARVEOUT','אין חריג למחלוקת'))
		O=_s(A['setoff'],I,B)
		for(M,Q,R)in L:
			G=[C for(C,D)in(('סכום','d_amount'),('מועד','d_timing'))if not _s(A[D],M,B)]
			if O and not _s(A['setoff'],M,B):G.append('קיזוז')
			if G:D.append(_f('GAP_DISPUTE_CARVEOUT','החריג אינו חל על '+', '.join(G),(Q,R)))
	E=_s(A['term_right'],C,B)
	if E and _s(A['ongoing_ctx'],I,B)and not _s(A['handover'],I,B):D.append(_f('GAP_TERMINATION_HANDOVER','',(E.start(),E.end())))
	if(K=='confidentiality'or _s(A['conf'],C,B))and(K=='confidentiality'or _s(A['conf_duty'],C,B)):
		S=('גילוי לפי דין או לפי דרישת רשות',A['law_exc']),('יועצים, רואה החשבון והמבקר הפנימי',A['adv_exc']),('מידע שהתקבל כדין מצד שלישי',A['tp_exc']),('פיתוח עצמאי',A['indep']);G=[A for(A,C)in S if not _s(C,I,B)]
		if G:D.append(_f('GAP_CONFIDENTIALITY_EXCEPTIONS','חסרים: '+'; '.join(G)))
	if _s(A['pay_term'],C,B):
		T=re.sub(A['pay_cap_safe'],lambda k:' '*len(k.group(0)),C,flags=B)if H.get('allow_statutory_cap')and _s(A['days'],C,B)else C;E=_s(A['pay_latest'],T,B)
		if E:D.append(_f('GAP_PAYMENT_WORDING','הפניה ל"מועד מאוחר ביותר" או ל"לפי המוקדם"',(E.start(),E.end())))
		if not _s(A['days'],C,B):D.append(_f('GAP_PAYMENT_WORDING','אין מספר ימים'))
	if not H.get('accept_text'):D+=check_document(C,[C],F,H)
	U=set(H.get('waived')or());return _dedupe([A for A in D if A['code']not in U])
def check_document(accept_text,touched,lang,context=None):A=lang;A=A if A in P else detect_lang(accept_text);B=context or{};C=[];D=set(B.get('waived')or());return _dedupe([A for A in C if A['code']not in D])
