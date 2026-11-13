#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib,evidence_kind as E
if __name__=='__main__':sys.dont_write_bytecode=True
LAW_RX=re.compile('((?<![\\u0590-\\u05ff])(?:[וש]?(?:[בלכ]|ה|מה|[בלכ]ה)?)חוק\\s+(?!(?:את|אותו|אותה|אותם|אותן|כל)\\b)[\u0590-\u05ff\\"\'״׳]|תקנות\\s+[\u0590-\u05ff]|תקנה\\s+\\d+|הרשות\\s+ל|רשות\\s+(?:ה|ל)[\u0590-\u05ff]+|\\bGDPR\\b|\\bDirective\\b|\\bRegulation\\b|\\bPrivacy\\s+Protection\\s+(?:Law|Act)\\b|\\bAct\\s+\\d{4})',re.I)
SILENCE_RX=re.compile('(אינו מזכיר|אינם מזכירים|לא מוזכר|שותק|שתיקה|מסמך אחד בלבד אינו|does not mention|silent)',re.I)
REFERRAL_RX=re.compile('(נוסח הירוק|כמו בירוק|חזרה לנוסח|כנוסח הירוק|same as green|see green|as in green)',re.I)
AREO_RX=re.compile('(הצעת\\s+Areo|Areo proposal|areo_proposal|הצעת מערכת|ניסוח של המערכת)',re.I)
ELLIPSIS_RX=re.compile('\\s*(?:\\[\\s*\\.{3}\\s*\\]|\\[…\\]|…|\\.{3})\\s*')
DONE={'Performed','Completed','Partial','ApplicableSourcesFound','NoSpecificSourceIdentified'}
def norm(s):s=str(s or'');s=s.replace('\u200e','').replace('\u200f','').replace('\xa0',' ');s=re.sub("[‘’‚‛׳']","'",s);s=re.sub('[“”„״\\"]','"',s);s=re.sub('[‐-―]','-',s);return re.sub('\\s+',' ',s).strip().lower()
def load(path):
	with open(path,encoding='utf-8')as A:return json.load(A)
def doc_texts(extract):
	C=extract;B={}
	if not C:return B
	for A in C.get('documents',[]):D=[norm(A.get('text',''))for A in A.get('paragraphs',[])if isinstance(A,dict)];B[A.get('doc_id')or A.get('path')]={'path':A.get('path',''),'paras':D,'all':' '.join(D)}
	return B
def find_doc(texts,source_log,source_id):
	A=''
	for D in source_log or[]:
		if D.get('source_id')==source_id:A=norm(D.get('agreement_name',''))
	if not A:return
	B=A.rsplit('\\',1)[-1].rsplit('/',1)[-1]
	for(E,F)in texts.items():
		C=norm(F['path']).rsplit('\\',1)[-1].rsplit('/',1)[-1]
		if C==B or B in C or C in B:return E
def _src(ev):return ev.get('source_id')or(str(ev.get('source_ref')or'').split('#',1)[0]or None)
def _cid(ev):return ev.get('cite_id')or ev.get('evidence_id')or ev.get('source_ref')or''
AREO_VALUES='areo_proposal','market_standard','areo'
def _track_evidence(rule,color):B=color;A=(rule.get('traffic_light')or{}).get(B)or{};return A.get('evidence')or[A for A in rule.get('evidence')or[]if isinstance(A,dict)and A.get('track')==B]
def quote_findings(rule,model,texts,errors,warnings):
	H=errors;D=texts;I=rule.get('rule_id')
	for C in rule.get('evidence')or[]:
		E=C.get('quote')or''
		if not E.strip():continue
		F=find_doc(D,model.get('source_log'),_src(C));K=[norm(A)for A in ELLIPSIS_RX.split(E)if norm(A)];L=[D[F]]if F else list(D.values())
		for A in K:
			B=None
			for G in L:
				for J in G['paras']:
					if A in J:B=J;break
				if B or A in G['all']:B=B or G['all'];break
			if B is None:M='במסמך המקור'if F else'באף מסמך בקורפוס';H.append('%s %s: הציטוט אינו נמצא מילה במילה %s: «%s»'%(I,_cid(C),M,A[:70]))
			elif not ELLIPSIS_RX.search(E)and B.endswith(A)is False and not re.search('[.;:!?)\\"\']\\s*$',A)and len(B)>len(A)+25:H.append('%s %s: הציטוט נחתך באמצע משפט בלי סימון [...]: «%s…»'%(I,_cid(C),A[:50]))
def evidence_findings(rule,errors,warnings):
	D=errors;B=rule;E=B.get('rule_id')
	for A in('green','yellow','red'):
		C=(B.get('traffic_light')or{}).get(A)or{};F=_track_evidence(B,A);H=' '.join(str(C.get(A,''))for A in('notes','comments','position','label'));I=[str(C.get(A)or'')for A in('label','basis','source','basis_label')];G=any(A in AREO_VALUES for A in I)or bool(AREO_RX.search(H))
		if G and F:D.append('%s %s: הצעת Areo נושאת ציטוטים מהקורפוס. הצעת מערכת אינה נשענת על ראיה'%(E,A))
		if not G and not F and(C.get('position')or'').strip():D.append('%s %s: עמדה בלי ציטוט שאינה מסומנת כהצעת Areo'%(E,A))
def silence_findings(rule,errors,warnings):
	A=rule;F=A.get('rule_id');C=[A for A in A.get('evidence')or[]if(A.get('quote')or'').strip()];G={_src(A)for A in C}
	for B in('green','yellow','red'):
		H=(A.get('traffic_light')or{}).get(B)or{};D=' '.join(str(H.get(A,''))for A in('notes','comments','position'))
		if SILENCE_RX.search(D)and len(G)>=1 and B=='green':
			for E in C:
				if E.get('track')in('green','context')and SILENCE_RX.search(D):errors.append('%s %s: העמדה נשענת על שתיקה של מסמך, אך מסמך אחר (%s) מסדיר את הנושא. השתיקה אינה ראיה'%(F,B,_src(E)));break
def law_findings(rule,model,errors,warnings):
	A=rule;F=A.get('rule_id');G=(model.get('regulatory_research')or{}).get('status')or A.get('regulatory_status')or'NotResearched'
	if G in DONE and A.get('regulatory_status')in DONE:return
	H=' '.join(norm(A.get('quote',''))for A in A.get('evidence')or[])
	for B in('green','yellow','red'):
		I=(A.get('traffic_light')or{}).get(B)or{}
		for C in('position','proposed_clause','notes','comments'):
			for D in LAW_RX.finditer(str(I.get(C,''))):
				E=norm(D.group(0))
				if E and E not in H:errors.append('%s %s.%s: קביעת דין («%s») בלי מחקר רגולטורי ובלי ציטוט מקביל'%(F,B,C,D.group(0)[:30]));break
def duplicate_findings(rule,errors,warnings):
	E=rule.get('rule_id');C={}
	for B in rule.get('evidence')or[]:A=_src(B),norm(B.get('clause_ref',''));C.setdefault(A,[]).append(_cid(B))
	for(A,D)in C.items():
		if len(D)>1 and A[1]:errors.append('%s: ציטוט כפול (מסמך %s, %s): %s. כל מניין מחושב על ייחודיים בלבד'%(E,A[0],A[1],', '.join(map(str,D))))
def field_findings(rule,errors,warnings):
	E=errors;B=rule;D=B.get('rule_id')
	for C in('green','yellow','red'):
		A=(B.get('traffic_light')or{}).get(C)or{};F=norm(A.get('position',''))
		for J in A.get('match_criteria')or[]:
			if F and norm(J)==F:E.append('%s %s: תנאי ההתאמה זהה לכותרת העמדה. צריך מבחן שאפשר להחיל על טיוטה'%(D,C));break
		if C!='green'and REFERRAL_RX.search(str(A.get('proposed_clause',''))+' '+str(A.get('fallback_wording',''))):E.append('%s %s: הנוסח החלופי הוא הפניה למסלול אחר ולא נוסח'%(D,C))
		for G in('fallback_wording',):
			if isinstance(A.get(G),dict)and REFERRAL_RX.search(str(A[G].get('text',''))):E.append('%s %s: fallback_wording הוא הפניה למסלול אחר'%(D,C))
	H=str(B.get('importance')or B.get('priority')or'').lower();I=(B.get('traffic_light')or{}).get('yellow')or{}
	if H in('critical','high')and not I.get('fallback_2')and len(I.get('fallback_steps')or[])<2:warnings.append('%s: נושא %s בלי מדרגת נסיגה שנייה'%(D,H))
GREEN_OWN_BASES='template','own_paper_repeated','documents_majority','client_answer','company_request','areo_proposal','market_standard'
OWN_LABEL_RX=re.compile('(נוסח(?:ים)? שאתם מציגים|הנוסח שלכם|התבנית שלכם|your (?:form|template|wording)|form you present)',re.I)
def kind_findings(rule,model,ex_idx,src_rows,errors,warnings):
	F=ex_idx;B=rule;G=B.get('rule_id');H=(B.get('traffic_light')or{}).get('green')or{}
	if not(H.get('position')or'').strip()or H.get('basis')in('areo_proposal','market_standard'):return
	C=[]
	for A in B.get('evidence')or[]:
		if A.get('track')!='green':continue
		J=str(A.get('source_ref')or A.get('source_id')or'').split('#')[0];I=src_rows.get(J)or{};C.append(E.ev_kind(A,I,E.doc_for_source(I,F)))
	if not C:return
	D=[A for A in C if A!='unknown']
	if D and all(A=='counterparty_unchanged'for A in D):errors.append('%s green: כל הציטוטים התומכים הם נוסח של הצד שכנגד שלא שונה. אי-מחיקה אינה עמדה של החברה: העמדה תירשם כצהוב או כשאלה פתוחה, עם הסבר שהחברה לא הביעה עמדה'%G)
	elif not D and not F:warnings.append('%s green: סיווג הראיה (ev_kind) לא ידוע בלי קובץ חילוץ, ולכן כלל 2 לא נבדק'%G)
def red_findings(rule,errors,warnings):
	B=rule.get('rule_id');A=(rule.get('traffic_light')or{}).get('red')or{}
	if not(A.get('position')or'').strip():return
	C,D=E.red_response(A)
	if C is None:errors.append('%s red: אין נוסח תגובה (proposed_clause / response_wording) ואין fallback_pointer: yellow. עמדה בלי נוסח היא פער, לא עמדה'%B)
def rationale_findings(rule,errors,warnings):
	A=rule;G=A.get('rule_id');D=A.get('policy_rationale')or{}
	if not D:return
	H,B=E.rationale_complete(A)
	if H:return
	F=[A.split(':',1)[1]for A in B if A.startswith('repeats_position:')];C='%s: שכבת הנימוקים אינה שלמה (%s)'%(G,', '.join(B)[:160])
	if F:C+='. נימוק שחוזר על נוסח העמדה אינו נימוק'
	if D.get('rationale_status')=='Confirmed'and(F or any(A.startswith('empty:')for A in B)):errors.append(C+'. rationale_status: Confirmed אינו אפשרי')
	else:warnings.append(C+'. השכבה מוסתרת בתוצרים עד שתושלם')
def name_findings(rule,names,company,errors,warnings):
	D=errors;F=rule.get('rule_id')
	for C in('green','yellow','red'):
		J=(rule.get('traffic_light')or{}).get(C)or{};A=J.get('proposed_clause');G={'position':J.get('position')or''}
		if isinstance(A,dict):
			for B in('he','en'):
				if A.get(B):
					G['proposed_clause.'+B]=A[B];H=E.detect_lang(A[B])
					if H and H!=B:D.append('%s %s: proposed_clause.%s כתוב בשפה אחרת (%s) מהמפתח'%(F,C,B,H))
			if A.get('source_language')and not any(str(A.get(B)or'').strip()for B in('he','en')):D.append('%s %s: source_language נכתב בלי נוסח. שפה נגזרת מהטקסט, לא מברירת מחדל'%(F,C))
		elif isinstance(A,str)and A:G['proposed_clause']=A
		for(K,L)in G.items():
			I=E.name_hits(L,names,company)
			if I:D.append('%s %s.%s: שם צד קונקרטי בנוסח מדיניות (%s). יוחלף בתווית גנרית (%s)'%(F,C,K,', '.join(A['name']for A in I[:3]),', '.join(sorted({A['generic']for A in I}))))
def legal_findings(rule,model,errors,warnings):
	A=rule;B=A.get('rule_id');F=(A.get('traffic_light')or{}).get('red')or{};C=' '.join(str(F.get(A)or'')for A in('position','red_why','notes','meaning'));G=A.get('policy_rationale')or{};C+=' '+str(G.get('legal_risk_and_legal_framework')or'')
	if not E.legal_claim(C):return
	D=bool(A.get('regulatory_sources'))and A.get('regulatory_status')in DONE
	if A.get('walk_away')is True and not D:errors.append('%s: שובר עסקה שנימוקו טענת דין, בלי מקור רגולטורי (regulatory_sources). אינו מאושר בלי עיגון'%B)
	elif not D:warnings.append('%s: טענת דין במדיניות בלי מקור. תסומן "טעונה אימות" ותופנה למקור'%B)
def integrity_findings(rule,errors,warnings):
	F=rule.get('rule_id')
	for B in('green','yellow','red'):
		G=(rule.get('traffic_light')or{}).get(B)or{};A=G.get('proposed_clause')
		for C in[A]if isinstance(A,str)else[A.get('he'),A.get('en')]if isinstance(A,dict)else[]:
			D=E.integrity_flags(C)
			if D:warnings.append('%s %s: הנוסח המוצע טעון בדיקה אנושית (%s): «%s…»'%(F,B,', '.join(D),str(C)[:50]));break
def source_findings(model,errors,warnings):
	J=warnings;C=errors;B=model;F=[A for A in B.get('source_log')or[]if isinstance(A,dict)];M=(B.get('scope_summary')or{}).get('corpus_basis')or{};N={str(A).replace('\\','/').rsplit('/',1)[-1]for A in M.get('counted_agreements')or[]}
	for A in F:
		if not E.is_agreement(A)and A.get('included',True):
			K=str(A.get('file')or'').replace('\\','/').rsplit('/',1)[-1]
			if K and K in N:C.append('%s: מסמך שאינו הסכם (doc_role %s) נספר ב-counted_agreements. הוא שכבת ראיות נפרדת, לא הסכם'%(A.get('source_id'),A.get('doc_role')))
		O=' '.join(str(A.get(B)or'')for B in('status','source_label','label','short_name'))
		if OWN_LABEL_RX.search(O)and A.get('paper')!='ours':C.append('%s: תווית שאומרת שהנוסח של החברה על מסמך שאינו נייר החברה (paper: %s)'%(A.get('source_id'),A.get('paper')or'ריק'))
	for G in B.get('rules')or[]:
		for H in('green','yellow','red'):
			P=(G.get('traffic_light')or{}).get(H)or{}
			if OWN_LABEL_RX.search(str(P.get('source_label')or'')):
				L={str(A.get('source_ref')or'').split('#')[0]for A in G.get('evidence')or[]if A.get('track')==H};Q={(next((A for A in F if A.get('source_id')==B),{})or{}).get('paper')for B in L}
				if L and'ours'not in Q:C.append('%s %s: source_label אומרת שהנוסח של החברה, ואף מקור מצוטט אינו על נייר החברה'%(G.get('rule_id'),H))
	try:from playbook import sufficiency as R;I=R.assess(F,B.get('rules')or[]);D=I.get('level')if isinstance(I,dict)else getattr(I,'level',None)
	except Exception as S:D=None;J.append('בדיקת המספיקות לא רצה (playbook.sufficiency): %s'%S)
	if D in('thin','insufficient'):
		T=json.dumps((B.get('scope_summary')or{}).get('limitations')or[],ensure_ascii=False);U=json.dumps((B.get('scope_summary')or{}).get('client_facts')or[],ensure_ascii=False)
		if not re.search('(מספר|מדגם|הסכמים|agreements|sample|corpus|מאגר)',T+U,re.I):(C if D=='insufficient'else J).append('המאגר מתחת לסף המספיקות (%s) והמגבלה אינה רשומה ב-scope_summary.limitations'%D)
def run_checks(model,extract=None):
	F=extract;D=model;G=doc_texts(F)if F else{};H=E.doc_index(F)if F else{};I={A.get('source_id'):A for A in D.get('source_log')or[]if isinstance(A,dict)};J=E.party_names(D);K=D.get('company_name')or'';B,A=[],[]
	if not G:A.append('לא נמסר --extract: בדיקת הציטוטים מול המקור וסיווג הראיה (ev_kind) לא רצו')
	for C in D.get('rules')or[]:
		if G:quote_findings(C,D,G,B,A)
		evidence_findings(C,B,A);silence_findings(C,B,A);law_findings(C,D,B,A);duplicate_findings(C,B,A);field_findings(C,B,A);kind_findings(C,D,H,I,B,A);red_findings(C,B,A);rationale_findings(C,B,A);name_findings(C,J,K,B,A);legal_findings(C,D,B,A);integrity_findings(C,B,A)
	source_findings(D,B,A);return B,A
def main(argv=None):
	B=argparse.ArgumentParser();B.add_argument('model');B.add_argument('--extract');B.add_argument('--json');A=B.parse_args(argv);D=load(A.model);H=load(A.extract)if A.extract else E.find_extract(D,A.model);C,F=run_checks(D,H);G={'errors':C,'warnings':F,'rules':len(D.get('rules')or[])}
	if A.json:
		with open(A.json,'w',encoding='utf-8',newline='\n')as I:json.dump(G,I,ensure_ascii=False,indent=1)
	for J in C[:60]:print('כשל:',J)
	for K in F[:20]:print('אזהרה:',K)
	print('%d נושאים נבדקו: %d כשלים, %d אזהרות'%(G['rules'],len(C),len(F)));return 3 if C else 0
if __name__=='__main__':sys.exit(main())
