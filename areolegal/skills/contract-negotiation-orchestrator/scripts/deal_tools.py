#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
'כלי העסקה: השוואת מסמכי העסקה, הסכמים קיימים עם הצד שכנגד, צדדים בקורפוס, עובדות ומפת המונחים.'
import argparse,glob,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib,common.docx_tracked as dt
from common.cli import OutputRefused,guard_out,load_docx_or_explain
import content_checks as CC
SIGNED=re.compile('ולראיה באו הצדדים על החתום|חתימת הצדדים|/s/|signature of the parties|IN WITNESS WHEREOF',re.I)
KEY_CLAUSES={'exclusivity':'בלעדי|בלעדיות|exclusiv','term_renewal':'תקופת ההסכם|יתחדש|חידוש|הארכה|term of this agreement|renew','notice_deadlines':'הודעה מוקדמת|ימים מראש|לא יאוחר מ|prior written notice|days.? notice|no later than','termination':'סיום|לסיים|ביטול|terminat','confidentiality':'סודיות|מידע סודי|confidential','minimum':'מינימום|כמות מזערית|minimum'}
TOPICS={'precedence':'יגבר|יגברו|עדיפות|prevail|precedence|order of priority','liability_cap':'תקרת|הגבלת אחריות|limitation of liability|aggregate liability|liability cap','term_termination':'תקופת ההסכם|סיום|termination|term of','governing_law':'הדין החל|הדין ה\\S+ (?:יחול|חל)|יחול(?:ו)? (?:ה)?דין|יחולו (?:רק )?דיני|דיני מדינת|סמכות (?:ה)?שיפוט|governing law|governed by|construed in accordance with|jurisdiction|courts of'}
LAW_NAMES={'IL':('israel','israeli','state of israel','ישראל','מדינת ישראל','ישראלי','הישראלי','ישראליים'),'GB-EAW':('england','england and wales','english','wales','welsh','אנגליה','אנגליה ווילס','אנגלי','האנגלי','ווילס'),'GB-SCT':('scotland','scottish','scots','סקוטלנד','סקוטי','הסקוטי'),'GB-NIR':('northern ireland','צפון אירלנד'),'GB':('united kingdom','UK','U.K.','british','הממלכה המאוחדת','בריטניה','בריטי','הבריטי'),'IE':('ireland','irish','republic of ireland','אירלנד','אירי','האירי'),'US':('united states','united states of america','USA','U.S.A.','US','U.S.','federal law of the united states','ארצות הברית','ארה"ב','ארה״ב','אמריקאי','האמריקאי','אמריקני','האמריקני'),'US-NY':('new york','state of new york','ניו יורק'),'US-DE':('delaware','state of delaware','דלאוור','דלאוואר'),'US-CA':('california','state of california','קליפורניה'),'US-TX':('texas','state of texas','טקסס'),'US-NJ':('new jersey','state of new jersey',"ניו ג'רזי",'ניו ג׳רזי'),'US-MA':('massachusetts','commonwealth of massachusetts',"מסצ'וסטס"),'US-FL':('florida','state of florida','פלורידה'),'US-WA':('state of washington','וושינגטון'),'US-IL':('illinois','state of illinois','אילינוי'),'CA':('canada','canadian','קנדה','קנדי','הקנדי'),'CA-ON':('ontario','province of ontario','אונטריו'),'DE':('germany','german','federal republic of germany','גרמניה','גרמני','הגרמני'),'FR':('france','french','צרפת','צרפתי','הצרפתי'),'CH':('switzerland','swiss','שווייץ','שוויץ','שווייצרי','שוויצרי'),'NL':('netherlands','the netherlands','dutch','holland','amsterdam','הולנד','הולנדי','ההולנדי'),'BE':('belgium','belgian','brussels','בלגיה','בלגי'),'LU':('luxembourg','לוקסמבורג'),'AT':('austria','austrian','vienna','אוסטריה','אוסטרי'),'IT':('italy','italian','milan','rome','איטליה','איטלקי'),'ES':('spain','spanish','madrid','ספרד','ספרדי'),'PT':('portugal','portuguese','פורטוגל'),'SE':('sweden','swedish','stockholm','שוודיה','שוודי'),'DK':('denmark','danish','copenhagen','דנמרק'),'NO':('norway','norwegian','oslo','נורווגיה'),'FI':('finland','finnish','helsinki','פינלנד'),'PL':('poland','polish','warsaw','פולין'),'CZ':('czech republic','czechia','prague',"צ'כיה"),'GR':('greece','greek','athens','יוון'),'CY':('cyprus','cypriot','nicosia','קפריסין'),'MT':('malta','maltese','מלטה'),'SG':('singapore','singaporean','סינגפור','סינגפורי'),'HK':('hong kong','הונג קונג'),'JP':('japan','japanese','tokyo','יפן'),'CN':('china','chinese',"people's republic of china",'PRC','סין'),'IN':('india','indian','הודו'),'AU':('australia','australian','sydney','אוסטרליה'),'NZ':('new zealand','ניו זילנד'),'AE':('united arab emirates','UAE','dubai','abu dhabi','איחוד האמירויות','דובאי'),'BR':('brazil','brazilian','ברזיל'),'ZA':('south africa','south african','דרום אפריקה'),'KR':('south korea','republic of korea','דרום קוריאה')}
_LAW_RX=[]
for(_code,_names)in LAW_NAMES.items():
	for _n in _names:
		if re.search('[א-ת]',_n):_rx=re.compile('(?<![א-ת])[ובלמהשכ]{0,2}'+re.escape(_n)+'(?![א-ת])')
		elif len(_n.replace('.',''))<=3:_rx=re.compile('(?<![A-Za-z])'+re.escape(_n)+'(?![A-Za-z])')
		else:_rx=re.compile('(?<![A-Za-z])'+re.escape(_n)+'(?![A-Za-z])',re.I)
		_LAW_RX.append((len(_n),_rx,_code))
_LAW_RX.sort(key=lambda x:-x[0])
def law_codes(text):
	C=text or'';A=set()
	for(F,D,B)in _LAW_RX:
		def E(m,c=B):A.add(c);return' '*len(m.group(0))
		C=D.sub(E,C)
	for B in list(A):
		if'-'in B and B.split('-')[0]in A:A.discard(B.split('-')[0])
	return A
PARTY_RX=[re.compile('(?:^|\\n)\\s*(?:בין|ל?בין)\\s*:?\\s*([^\\n,;]{3,80}?)(?:\\s*,|\\s*\\(|\\s*ח\\.?פ|\\s*מספר|\\n)'),re.compile('\\bbetween\\s+([A-Z][^,\\n(]{2,80}?)\\s*(?:,|\\(|a company|incorporated)',re.I),re.compile('\\band\\s+([A-Z][^,\\n(]{2,80}?)\\s*(?:,|\\(|a company|incorporated)')]
NUM=re.compile('\\d[\\d,.]*')
def text_of(path):
	try:return dt.accept_all(path)
	except Exception:return[]
def paras_matching(paras,rx):return[(B,A)for(B,A)in enumerate(paras)if re.search(rx,A,re.I)]
def definitions(paras):
	A={}
	for(F,B)in enumerate(paras):
		for D in CC.DEF_PATTERNS:
			for E in D.finditer(B):
				for C in E.groups():
					if C:A.setdefault(C.strip(),B.strip()[:300])
	return A
def cmd_compare(a):
	G={}
	for H in a.docs:
		if not os.path.exists(H):print('אינו קיים: %s'%H);return 2
		R,S,T=load_docx_or_explain(H,loader=False)
		if R is None:print(S);return T
		G[os.path.basename(H)]=text_of(H)
	E=[];I={A:definitions(B)for(A,B)in G.items()};J=list(G)
	for(U,A)in enumerate(J):
		for B in J[U+1:]:
			for K in set(I[A])&set(I[B]):
				if re.sub('\\W+','',I[A][K])!=re.sub('\\W+','',I[B][K]):E.append({'topic':'definitions','documents':[A,B],'conflict':'המונח "%s" מוגדר אחרת בשני המסמכים'%K})
			for(F,P)in TOPICS.items():
				L,M=paras_matching(G[A],P),paras_matching(G[B],P)
				if not L or not M:continue
				if F in('liability_cap','term_termination'):
					N={B for(C,A)in L for B in NUM.findall(A)};O={B for(C,A)in M for B in NUM.findall(A)}
					if N and O and not N&O:E.append({'topic':F,'documents':[A,B],'conflict':'מספרים שונים (%s מול %s)'%(', '.join(sorted(N)[:4]),', '.join(sorted(O)[:4]))})
				elif F=='governing_law':
					C=law_codes('\n'.join(A for(B,A)in L));D=law_codes('\n'.join(A for(B,A)in M))
					if C and D and C!=D:E.append({'topic':F,'documents':[A,B],'codes':[sorted(C),sorted(D)],'conflict':'דין או שיפוט שונים (%s מול %s) / Different governing law or forum (%s vs %s)'%(', '.join(sorted(C)),', '.join(sorted(D)),', '.join(sorted(C)),', '.join(sorted(D)))})
					elif not C or not D:Q=[A for(A,B)in((A,C),(B,D))if not B];E.append({'topic':F,'documents':[A,B],'status':'unrecognised','conflict':'הדין או השיפוט לא זוהה ב-%s: לקרוא ולהשוות ביד / Governing law or forum not recognised in %s: read and compare manually'%(', '.join(Q),', '.join(Q))})
				else:E.append({'topic':F,'documents':[A,B],'conflict':'בשני המסמכים סעיף עדיפות: לבדוק שאינם סותרים'})
	V={'documents':J,'conflicts':E};print(json.dumps(V,ensure_ascii=False,indent=1));return 0
def corpus_files(root):return[A for A in sorted(glob.glob(os.path.join(root,'**','*.docx'),recursive=True))if not os.path.basename(A).startswith('~$')and'Areo-נתונים'not in A]
def party_names(paras):
	C='\n'.join(paras[:12]);A=[]
	for D in PARTY_RX:
		for E in D.finditer(C):
			B=re.sub('\\s+',' ',E.group(1)).strip(' :')
			if 3<=len(B)<=80 and B not in A:A.append(B)
	return A
def cmd_existing(a):
	G=[A for A in[a.counterparty]+list(a.related or[])if A];A=[]
	for D in corpus_files(a.root):
		B=text_of(D);C='\n'.join(B)
		if not SIGNED.search(C):continue
		E=[A for A in G if A and A in C];H=a.family and re.search(a.family,C[:2000],re.I)
		if not E and not H:continue
		I={A:[A[:400]for(B,A)in paras_matching(B,C)][:4]for(A,C)in KEY_CLAUSES.items()};A.append({'file':os.path.relpath(D,a.root),'matched_by':'counterparty'if E else'family','parties':party_names(B),'clauses':I})
	F={'counterparty':a.counterparty,'found':A}
	if not A:F['line']='לא נמצאו בתיקייה המחוברת הסכמים קודמים עם %s.'%(a.counterparty or'הצד שכנגד')
	print(json.dumps(F,ensure_ascii=False,indent=1));return 0
def cmd_parties(a):
	if a.out:
		try:guard_out(a.out)
		except OutputRefused as D:print('סירוב: %s'%D);return 1
	A=[]
	for E in corpus_files(a.root):
		B=text_of(E)
		if SIGNED.search('\n'.join(B)):
			for C in party_names(B):
				if C not in A:A.append(C)
	if a.out:
		with io.open(a.out,'w',encoding='utf-8')as F:json.dump({'documents':[{'counterparty':A}for A in A]},F,ensure_ascii=False,indent=1)
	print(json.dumps(A,ensure_ascii=False,indent=1));return 0
def _load(p):
	try:
		with io.open(p,encoding='utf-8')as A:return json.load(A)
	except(OSError,ValueError):return
def _fact(x,source,text_keys=('text','assumption','fact','question'),value_keys=('status','value','answer')):
	A=source
	if isinstance(x,dict):return{'fact':next((x[A]for A in text_keys if x.get(A)),json.dumps(x,ensure_ascii=False)),'value':next((x[A]for A in value_keys if x.get(A)is not None),None),'source':A}
	return{'fact':str(x),'value':None,'source':A}
def cmd_facts(a):
	A=[]
	for I in glob.glob(os.path.join(a.data,'playbooks','*','playbook-model.json'))+glob.glob(os.path.join(a.data,'playbook-model.json')):
		E=_load(I)or{};J='תשובות הקליטה של הפלייבוק (%s)'%os.path.relpath(I,a.data);G=(E.get('meta')or{}).get('intake_answers')or E.get('intake_answers')or{}
		for(B,F)in G.items()if isinstance(G,dict)else enumerate(G):A.append({'fact':B,'value':F,'source':J})
		for C in list((E.get('scope_summary')or{}).get('client_facts')or[])+list(((E.get('meta')or{}).get('build_request')or{}).get('client_facts')or[]):A.append(_fact(C,J,('fact','text','question'),('answer_verbatim','answer','value')))
	if a.transaction_id:
		N=os.path.join(a.data,'transactions',a.transaction_id,'risk-register.json');O=_load(N)or{}
		for C in(O.get('summary')or{}).get('assumptions')or[]:A.append(_fact(C,'מרשם הסיכונים של העסקה'))
	for K in glob.glob(os.path.join(a.data,'transactions','*','negotiation_state.json')):
		L=_load(K)or{};D=L.get('meta')or{}
		if a.counterparty and a.counterparty not in str(D.get('counterparty_name')or''):continue
		for C in L.get('client_answers')or[]:A.append(_fact(C,'קובץ המצב, %s'%D.get('transaction_id',os.path.basename(os.path.dirname(K))),('question','fact','text'),('answer','value')))
		H=(D.get('deal_context')or{}).get('facts')or[]
		for(B,F)in H.items()if isinstance(H,dict)else((A,None)for A in H):
			if F is None:
				M=_fact(B,'deal_context, %s'%D.get('transaction_id',''))
				if isinstance(B,dict)and B.get('source'):M['origin']=B['source']
				A.append(M)
			else:A.append({'fact':B,'value':F,'source':'deal_context, %s'%D.get('transaction_id','')})
	print(json.dumps({'facts':A},ensure_ascii=False,indent=1));return 0
def cmd_terms(a):
	if not os.path.exists(a.draft):print('אינו קיים: %s'%a.draft);return 2
	C,D,E=load_docx_or_explain(a.draft,loader=False)
	if C is None:print(D);return E
	A=text_of(a.draft);B='\n'.join(A);F=definitions(A);G='(?<![\\w\u0590-\u05ff])(?:ל?בין)(?![\\w\u0590-\u05ff])|\\bbetween\\b';H=list(CC.PARTY_LABELS)+[A for(A,B)in F.items()if re.search(G,B,re.I)];I={A:B.count(A)for A in dict.fromkeys(H)if re.search('(?<![\\w\u0590-\u05ff])'+re.escape(A)+'(?![\\w\u0590-\u05ff])',B)};print(json.dumps({'defined_terms':definitions(A),'party_labels':I},ensure_ascii=False,indent=1));return 0
def main(argv=None):sys.dont_write_bytecode=True;sys.stdout.reconfigure(encoding='utf-8',errors='replace');D=argparse.ArgumentParser(description=__doc__.split('\n')[0]);A=D.add_subparsers(dest='cmd',required=True);G=A.add_parser('compare-docs');G.add_argument('docs',nargs='+');B=A.add_parser('existing');B.add_argument('--root',required=True);B.add_argument('--counterparty');B.add_argument('--related',action='append');B.add_argument('--family',help='ביטוי לזיהוי משפחת ההסכם בכותרת ובפתיח');E=A.add_parser('parties');E.add_argument('--root',required=True);E.add_argument('--out',help='קובץ לשער האיכות (qa_gate.py --manifest), בתיקייה זמנית');C=A.add_parser('facts');C.add_argument('--data',required=True);C.add_argument('--transaction-id');C.add_argument('--counterparty');H=A.add_parser('terms');H.add_argument('draft');F=D.parse_args(argv);return{'compare-docs':cmd_compare,'existing':cmd_existing,'parties':cmd_parties,'facts':cmd_facts,'terms':cmd_terms}[F.cmd](F)
if __name__=='__main__':sys.exit(main())
