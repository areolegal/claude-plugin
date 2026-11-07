# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import os,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib
from playbook import status as S
AREO_TAG='הצעת Areo (לא מבוסס על מסמכי הלקוח)'
DOCS={'signed':'הסכמים של החברה','mostly_drafts':'מסמכים של החברה, רובם טיוטות ולא הסכמים חתומים','company_forms':'נוסחים שהחברה מציגה לצד שכנגד, ולא הסכמים חתומים','third_party_forms':'נוסחים שאינם הסכמים חתומים של החברה','unknown':'נוסחים שאינם הסכמים חתומים של החברה','theirs_paper':'נוסחים של הצד שכנגד שהחברה חתמה עליהם'}
PRELIMINARY={'mostly_drafts':'פלייבוק ראשוני. נבנה ברובו מטיוטות ולא מהסכמים חתומים.','company_forms':'פלייבוק ראשוני. נבנה מנוסחים שהחברה מציגה לצד שכנגד, ולא מהסכמים חתומים.','third_party_forms':'פלייבוק ראשוני. נבנה מנוסחים שאינם הסכמים חתומים של החברה.','unknown':'פלייבוק ראשוני. נבנה מנוסחים שאינם הסכמים חתומים של החברה.'}
DRAFTS_LINE=PRELIMINARY['mostly_drafts']
DOCS_EN={'signed':'company agreements','mostly_drafts':'company documents, most of them drafts and not signed agreements','company_forms':'forms the company presents to its counterparties, not signed agreements','third_party_forms':'forms that are not signed agreements of the company','unknown':'forms that are not signed agreements of the company','theirs_paper':'counterparty forms the company signed'}
NO_COMPANY_POSITION={'he':' אף עמדה בו אינה נשענת על מסמך של החברה: כל העמדות הן הצעת Areo.','en':' No position in it rests on a company document: every position is an Areo proposal.'}
PRELIMINARY_EN={'mostly_drafts':'Preliminary playbook. Built mostly from drafts, not from signed agreements.','company_forms':'Preliminary playbook. Built from forms the company presents to its counterparties, not from signed agreements.','third_party_forms':'Preliminary playbook. Built from forms that are not signed agreements of the company.','unknown':'Preliminary playbook. Built from forms that are not signed agreements of the company.'}
def docs(status,lang='he'):A=DOCS_EN if lang=='en'else DOCS;return A.get(status)or A['signed']
def agreement_units(model):A=model;B=(A.get('scope_summary')or{}).get('corpus_basis')or{};C=B.get('agreement_units');return S.company_agreements_counted(A)if isinstance(C,int)else None
def basis_line(units,origin,status=None):
	C=origin;A=units
	if not isinstance(A,int):return
	if A==0 or C=='market_built':return'נבנה לפי השוק, מותאם לפוזיציה של החברה, עם בדיקה רגולטורית מעמיקה. אין בו עמדה שנגזרה מהסכמי החברה, וכל עמדה בו מסומנת "%s".'%AREO_TAG
	B=docs(status)
	if A>=7 and C=='own_plus_market':return'נבנה מ-%d %s, בשילוב מחקר שוק. עמדה שמקורה בשוק מסומנת "%s".'%(A,B,AREO_TAG)
	if A>=20:return'נבנה מ-%d %s.'%(A,B)
	if A>=7:return'נבנה מ-%d %s. זה פחות מהמומלץ (כ-20), ולכן חלק מהעמדות נשענות על מעט משאים ומתנים.'%(A,B)
	if C=='own_plus_market':return'נבנה מ-%d %s, בשילוב מחקר שוק. עמדה שמקורה בשוק מסומנת "%s".'%(A,B,AREO_TAG)
	return'נבנה מ-%d %s בלבד. לא מומלץ לבנות פלייבוק מפחות מ-20 הסכמים, והחברה בחרה שלא לשלב מחקר שוק.'%(A,B)
def corpus_status(model):return S.corpus_status(model)
def line_for(model):A=model;B=basis_line(agreement_units(A),(A.get('scope_summary')or{}).get('corpus_origin'),docs_status(A));return B+honesty_tail(A)if B else B
def docs_status(model):A=model;B=corpus_status(A);return'theirs_paper'if B=='signed'and S.theirs_paper(A)else B
def honesty_tail(model,lang='he'):return NO_COMPANY_POSITION['en'if lang=='en'else'he']if S.no_company_position(model)else''
def mostly_drafts(model):return S.mostly_drafts(model)
def preliminary_line(model):return PRELIMINARY.get(corpus_status(model))
AREO_TAG_EN="Areo proposal (not based on the client's documents)"
FALLBACK_DOCS={'he':{'company_forms':'הנוסחים שהחברה מציגה לצד שכנגד','mostly_drafts':'המסמכים, שרובם טיוטות','third_party_forms':'המסמכים, שאינם הסכמים חתומים של החברה','unknown':'המסמכים, שמעמדם אינו ידוע','signed':'המסמכים'},'en':{'company_forms':'forms the company presents to its counterparties','mostly_drafts':'documents, most of them drafts','third_party_forms':'documents, which are not signed agreements of the company','unknown':'documents, whose status is unknown','signed':'documents'}}
FALLBACK_TEXT={'he':{'template_dep':'קו הנסיגה נלמד מהתבנית שלכם: הסטייה הזו נחתמה ב-%d משאים ומתנים.','template':'קו הנסיגה נלמד מהתבנית שלכם, ולא נמצאה ממנה סטייה שנחתמה בשני משאים ומתנים או יותר.','own_paper_majority':'קו הנסיגה נלמד מהנוסח שחוזר ב-%d מתוך %d ההסכמים על הנייר שלכם.','identical':'כל ההסכמים זהים בנושא הזה, ולכן אין ראיה לקו נסיגה. הצהוב הוא הצעת Areo.','documents_majority':'הירוק נלקח מהנוסח שחוזר ב-%d מתוך %d %s. אין בהם משא ומתן, ולכן אין ראיה לקו נסיגה, והצהוב הוא הצעת Areo.','none':'אין בנושא הזה נוסח בסיס, ולכן אין ראיה לקו נסיגה. הצהוב הוא הצעת Areo.','market':'קו הנסיגה נלקח ממחקר השוק, ומסומן "%s".'%AREO_TAG},'en':{'template_dep':'The fallback line is learned from your template: this departure was signed in %d negotiations.','template':'The fallback line is learned from your template, and no departure from it was signed in two negotiations or more.','own_paper_majority':'The fallback line is learned from the wording that repeats in %d of the %d agreements on your paper.','identical':'All the agreements are identical on this topic, so there is no evidence for a fallback line. The yellow is an Areo proposal.','documents_majority':'The green is taken from the wording that repeats in %d of the %d %s. They show no negotiation, so there is no evidence for a fallback line, and the yellow is an Areo proposal.','none':'There is no baseline wording on this topic, so there is no evidence for a fallback line. The yellow is an Areo proposal.','market':'The fallback line is taken from the market research, and is marked "%s".'%AREO_TAG_EN}}
def fallback_label(origin,model,lang='he'):
	G=model;F=origin;A=lang;B=F if isinstance(F,dict)else{};A='en'if A=='en'else'he';C=FALLBACK_TEXT[A];D=B.get('baseline');E=[A for A in B.get('baseline_refs')or[]if A];H=[A for A in(G or{}).get('source_log')or[]if isinstance(A,dict)and A.get('included')is not False]
	if B.get('identical_in_all')and D in('own_paper_majority','template'):return C['identical']
	if D=='template':I=[A.get('negotiations')for A in B.get('departures')or[]if isinstance(A,dict)and A.get('status')=='established'and isinstance(A.get('negotiations'),int)];return C['template_dep']%max(I)if I else C['template']
	if D=='own_paper_majority':J=sum(1 for A in H if A.get('paper')=='ours'and A.get('doc_role')not in('template','form'));return C['own_paper_majority']%(len(E),max(J,len(E)))
	if D=='documents_majority':K=sum(1 for A in H if A.get('doc_role')!='template');L=corpus_status(G or{});M=FALLBACK_DOCS[A].get(L,FALLBACK_DOCS[A]['signed']);return C['documents_majority']%(len(E),max(K,len(E)),M)
	if D in('none','market'):return C[D]
	return(B.get('label_en')if A=='en'else None)or B.get('label_he')or''
