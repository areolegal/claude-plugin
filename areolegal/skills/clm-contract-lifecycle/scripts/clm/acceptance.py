# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
from clm import catalog,dates
QUOTED='events','key_clauses','guarantees','commercials'
def metrics(data):B=data;D={A['id']:A for A in B['documents']};A,C=B['agreements'],B['events'];E=[A for A in A if A['doc_ids']and all(D.get(A,{}).get('doc_kind')in('template','non_agreement')for A in A['doc_ids'])];F=[A for A in A if A.get('type_code')is None];return{'agreements':len(A),'templates_in_register':len(E),'other_pct':round(1e2*len(F)/len(A),1)if A else .0,'events_without_quote':sum(1 for A in C if not A.get('refs')),'items_without_quote':sum(1 for A in QUOTED for C in B.get(A)or[]if not C.get('refs')),'bad_coverage':sum(1 for A in A if{A['category']for A in A.get('coverage',[])}!=set(catalog.CATEGORIES)),'generic_actions':sum(1 for A in C if any(B in(A.get('action')or'')for B in dates.GENERIC)),'auto_closed':sum(1 for A in C if A.get('state')not in dates.STATES)}
CRITERIA=[('agreements',lambda v:v>0,'יותר מ-0 הסכמים'),('templates_in_register',lambda v:v==0,'אפס תבניות ומסמכים שאינם הסכמים במאגר'),('other_pct',lambda v:v<5,'פחות מ-5% הסכמים מסוג שאינו בקטלוג'),('items_without_quote',lambda v:v==0,'ציטוט לכל פריט: מועדים, סעיפי מפתח, בטוחות ותנאים מסחריים'),('bad_coverage',lambda v:v==0,'היקף בדיקה לשש הקטגוריות בכל הסכם'),('generic_actions',lambda v:v==0,'אפס פעולות כלליות'),('auto_closed',lambda v:v==0,'אפס מועדים שנסגרו אוטומטית')]
def report(data):
	B=metrics(data);C,A=[],True
	for(D,F,G)in CRITERIA:E=F(B[D]);A=A and E;C.append('%s %s: %s'%('עבר'if E else'נכשל',G,B[D]))
	return A,C
