# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys
from collections import Counter
from datetime import date
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text,docx_paragraphs,guard_out,family_matches,normalize_role
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
WINDOW=420
def R(*A):return re.compile('|'.join(A),re.I)
ISO_CODES='ILS','NIS','USD','EUR','GBP','CHF','JPY','CNY','CAD','AUD','NZD','SGD','HKD','INR','AED','SEK','NOK','DKK','PLN','CZK','HUF','RON','TRY','BRL','MXN','ZAR','KRW'
CUR='(?:₪|ש\\"ח|ש״ח|שקלים|שקל|\\$|€|£|¥|(?<![A-Za-z])(?-i:%s)(?![A-Za-z])|דולר|אירו|יורו|ליש\\"ט|ליש״ט|פאונד|לירות\\s+שטרלינג|(?i:dollars?|euros?|pounds?(?:\\s+sterling)?))'%'|'.join(ISO_CODES)
CUR_RX=re.compile(CUR)
CUR_CODE={'₪':'ILS','ש"ח':'ILS','ש״ח':'ILS','שקלים':'ILS','שקל':'ILS','NIS':'ILS','€':'EUR','אירו':'EUR','יורו':'EUR','euro':'EUR','euros':'EUR','£':'GBP','ליש"ט':'GBP','ליש״ט':'GBP','פאונד':'GBP','pound':'GBP','pounds':'GBP','dollar':'$','dollars':'$','דולר':'$'}
def currency_of(s):
	B=CUR_RX.search(s or'')
	if not B:return
	A=re.sub('\\s+',' ',B.group(0))
	if A in ISO_CODES:return'ILS'if A=='NIS'else A
	if A.startswith('לירות')or A.lower().endswith('sterling'):return'GBP'
	return CUR_CODE.get(A.lower(),A)
SPELLED=re.compile('[A-Za-z\\u0590-\\u05FF]+[\\s\\-]*\\(\\s*(\\d{1,4})\\s*\\)')
def normalize(t):return SPELLED.sub('\\1',t)
PARAMS=[('תנאי תשלום',R('תנאי\\s+ה?תשלום','שוטף\\s*\\+','מועד\\s+ה?תשלום','חשבונית','payment\\s+terms','\\bnet\\s+\\d','payment\\s+terms','\\bnet\\s+\\d','invoice','due\\s+and\\s+payable'),R('שוטף\\s*\\+?\\s*(\\d{1,3})','(?:תוך|בתוך|בטרם|לא\\s+יאוחר\\s+מ)\\s*(\\d{1,3})\\s+ימים?','\\bnet\\s+(\\d{1,3})\\b','\\bnet\\s+(\\d{1,3})\\b','within\\s+(\\d{1,3})\\s+days','(\\d{1,3})\\s+days\\s+of\\s+(?:the\\s+)?invoice'),'ימים','כמה ימים מקבלת החשבונית ועד התשלום'),('הודעה מוקדמת לסיום',R('סיום\\s+ה?הסכם','לסיים\\s+את\\s+ה?הסכם','אי[\\s\\-־]?חידוש','ביטול\\s+ה?הסכם','הודעה\\s+מוקדמת','termination\\s+for\\s+convenience','terminat','non[\\s\\-]?renewal','for\\s+convenience','prior\\s+written\\s+notice'),R('(\\d{1,3})\\s+ימים?\\s+מראש','של\\s+(\\d{1,3})\\s+ימים?','לפחות\\s+(\\d{1,3})\\s+ימים?','(\\d{1,2})\\s+חודשים?\\s+מראש',"(\\d{1,3})\\s+days['’]?\\s+(?:prior\\s+)?written\\s+notice","(?:at\\s+least\\s+)?(\\d{1,3})\\s+days['’]?\\s+notice","(\\d{1,2})\\s+months['’]?\\s+(?:prior\\s+)?notice"),'ימים','כמה ימי הודעה מראש נדרשים לסיום ההתקשרות'),('תקופת ריפוי הפרה',R('הפרה\\s+יסודית','לא\\s+תוקנה','תוקנה\\s+ה?הפרה','תקופת\\s+ריפוי','cure\\s+period','material\\s+breach','cure\\s+period','fails?\\s+to\\s+cure','remed(?:y|ied)'),R('(?:בתוך|תוך)\\s+(\\d{1,3})\\s+ימים?','(\\d{1,3})\\s+ימים?\\s+ממועד\\s+ה?הודעה','within\\s+(\\d{1,3})\\s+days','within\\s+(\\d{1,3})\\s+days','(\\d{1,3})[\\s\\-]day\\s+cure'),'ימים','כמה ימים לתיקון הפרה לפני שהיא מזכה בביטול'),('תקופת ההתקשרות הראשונה',R('תקופת\\s+ה?(?:הסכם|התקשרות|שירות|ההתקשרות)','ההסכם\\s+יעמוד\\s+בתוקפו','initial\\s+term','initial\\s+term','this\\s+agreement\\s+shall\\s+(?:commence|be\\s+effective)','continue\\s+in\\s+(?:full\\s+force|effect)','shall\\s+remain\\s+in\\s+effect','term\\s+of\\s+this\\s+agreement'),R('(?:של|למשך|בת)\\s+(\\d{1,3})\\s+חודשים?','(?:של|למשך|בת)\\s+(\\d{1,2})\\s+שנים?','(\\d{1,3})\\s+חודשים?','(\\d{1,2})\\s+שנים?','(?:period|term)\\s+of\\s+(\\d{1,3})\\s+(?:months?|years?)','(?:for|of)\\s+(\\d{1,3})\\s+months?','(?:for|of)\\s+(\\d{1,2})\\s+years?','(\\d{1,2})\\s+years?\\s+from','(\\d{1,3})\\s+months?\\s+from'),'חודשים או שנים','אורך התקופה הראשונה של ההתקשרות'),('הארכה אוטומטית',R('תוארך\\s+אוטומטית','חידוש\\s+אוטומטי','יתחדש\\s+מאליו','automatically\\s+renew','אלא\\s+אם\\s+הודיע','automatically\\s+renew','successive','unless\\s+either\\s+party','renewal\\s+term'),R('(?:נוספ(?:ת|ות)\\s+)?(?:בת|של)\\s+(\\d{1,3})\\s+(?:חודשים?|שנים?)','(\\d{1,3})\\s+חודשים?','(\\d{1,2})\\s+שנים?','(?:successive|additional|further)\\s+(?:periods?|terms?)\\s+of\\s+(\\d{1,3})\\s+(?:months?|years?)','(\\d{1,2})[\\s\\-]year\\s+(?:renewal|period)','(\\d{1,3})[\\s\\-]month\\s+(?:renewal|period)'),'חודשים או שנים','אורך תקופת ההארכה האוטומטית'),('תקרת אחריות',R('הגבלת\\s+אחריות','גבולות\\s+אחריות','תקרת\\s+ה?אחריות','אחריות(?:ו|ה|ם)?\\s+ה?כוללת','אחריות(?:ו|ה|ם)?\\s+ה?מצטברת','limitation\\s+of\\s+liability','aggregate\\s+liability','limitation\\s+of\\s+liability','aggregate\\s+liability','total\\s+liability','limited\\s+liability','in\\s+no\\s+event'),R('ששולמ(?:ו|ה)\\s+ב[\\-]?(\\d{1,2})\\s+ה?חודשים','(\\d{1,2})\\s+ה?חודשים\\s+שקדמו','לא\\s+תעלה\\s+על\\s+(?:סך\\s+)?(?:של\\s+)?([\\d,]{3,})','פי\\s+(\\d{1,2})\\s+מ','מוגבלת\\s+ל(?:סך\\s+)?([\\d,]{3,})','(\\d{1,2})\\s+חודשי\\s+תמורה','(נזק\\s+עקיף)','(?:fees|amounts)\\s+paid[^.]{0,60}?(\\d{1,2})\\s+months','(\\d{1,2})\\s+months\\s+(?:preceding|prior)','exceed[^.]{0,40}?'+CUR+'\\s?([\\d,]{4,})','exceed[^.]{0,40}?([\\d,]{4,})\\s?'+CUR,'(indirect,?\\s+consequential)'),'סכום או מכפיל','כיצד מוגבלת האחריות בניירות שלך'),('גבול אחריות ביטוחי',R('אישור\\s+קיום\\s+ביטוח','גבול\\s+אחריות','סכום\\s+ביטוח','פוליס','ביטוח\\s+אחריות','insurance','insurance','policy\\s+limits?','commercial\\s+general\\s+liability'),R('([\\d,]{4,})\\s*'+CUR,'בגבול\\s+אחריות\\s+של\\s+([\\d,]{4,})','סכום\\s+ביטוח\\s+של\\s+([\\d,]{4,})',CUR+'\\s?([\\d,]{4,})'),'סכום ומטבע','גבול האחריות הביטוחי הנדרש'),('ריבית פיגורים',R('ריבית\\s+פיגורים','פיגור\\s+בתשלום','איחור\\s+בתשלום','late\\s+payment','late\\s+payment','overdue','interest\\s+on'),R('(\\d{1,2}(?:\\.\\d+)?)\\s*%','בשיעור\\s+של\\s+(\\d{1,2}(?:\\.\\d+)?)','(\\d{1,2}(?:\\.\\d+)?)\\s*%\\s*per\\s+(?:month|annum)','(\\d{1,2}(?:\\.\\d+)?)\\s*%'),'אחוז','שיעור ריבית הפיגורים הנהוג'),('תמלוגים או עמלה',R('תמלוגים','עמלה','royalt','commission','royalt','commission','discount','margin','reseller\\s+price'),R('בשיעור\\s+(?:של\\s+)?(\\d{1,2}(?:\\.\\d+)?)\\s*%','(\\d{1,2}(?:\\.\\d+)?)\\s*%','(\\d{1,2}(?:\\.\\d+)?)\\s*%'),'אחוז','שיעור התמלוגים או העמלה'),('שרידות חובת הסודיות',R('סודיות','מידע\\s+סודי','confidentialit','confidential','survive'),R('(\\d{1,2})\\s+שנים?\\s+מ(?:מועד\\s+)?(?:ה?סיום|תום)','למשך\\s+(\\d{1,2})\\s+שנים?','(\\d{1,2})\\s+years?\\s+(?:after|following)','(\\d{1,2})\\s+years?\\s+(?:after|following|from)','period\\s+of\\s+(\\d{1,2})\\s+years?'),'שנים','כמה זמן שורדת חובת הסודיות אחרי הסיום'),('אי תחרות',R('אי[\\s\\-־]?תחרות','לא\\s+יתחרה','הגבלת\\s+עיסוק','non[\\s\\-]?compet','non[\\s\\-]?compet','shall\\s+not\\s+compete','no\\s+solicitation'),R('(\\d{1,2})\\s+חודשים?','(\\d{1,2})\\s+שנים?','(\\d{1,2})\\s+(?:months?|years?)'),'חודשים או שנים','משך הגבלת אי התחרות'),('מקדמה או פיקדון',R('פיקדון','מקדמה','ערבות\\s+בנקאית','בטוחה','security\\s+deposit','deposit','advance\\s+payment','prepayment','bank\\s+guarantee'),R('([\\d,]{4,})\\s*'+CUR,'בסך\\s+(?:של\\s+)?([\\d,]{4,})','(\\d{1,2})\\s+חודשי\\s+(?:תשלום|דמי)',CUR+'\\s?([\\d,]{4,})'),'סכום','גובה הפיקדון או הערבות הנהוג')]
def derive(texts):
	K=texts;E=[]
	for(L,V,W,M,N)in PARAMS:
		F,O,P=Counter(),{},{}
		for(Q,X,R,a)in K:
			C=set()
			for S in V.finditer(R):
				Y=max(0,S.start()-WINDOW//3);G=R[Y:S.start()+WINDOW]
				for B in W.finditer(G):
					A=next((A for A in B.groups()if A),None)
					if not A:continue
					A=A.replace(',','');T=currency_of(G[B.start():B.end()+12])if len(A)>=4 else None
					if T:A='%s %s'%(A,T)
					C.add(A);O.setdefault(A,{'source_file':Q,'family':X,'quote':re.sub('\\s+',' ',G[max(0,B.start()-90):B.start()+130]).strip()})
			if C:P[Q]=sorted(C)
			for Z in C:F[Z]+=1
		if not F:E.append({'parameter':L,'unit':M,'question':N,'value':None,'status':'לא נגזר','note':'לא אותר בניירות של הלקוח, יש לשאול את המשתמש'});continue
		D=F.most_common();U,H=D[0]
		if len(D)>1 and D[1][1]==H:I='שנוי, יותר מערך שכיח אחד'
		elif H>=2:I='מבוסס'
		else:I='מופע יחיד, טעון אישור'
		J=O.get(U,{});E.append({'parameter':L,'unit':M,'question':N,'value':U,'status':I,'support':'%d מתוך %d מסמכים'%(H,len(K)),'distribution':[{'value':A,'documents':B}for(A,B)in D[:6]],'per_document':P,'source_file':J.get('source_file'),'source_family':J.get('family'),'quote':J.get('quote')})
	return E
def doc_role(d):return d.get('company_role')or(d.get('company_role_candidates')or[None])[0]
def main():
	D=argparse.ArgumentParser();D.add_argument('--registry',required=True);D.add_argument('--out',required=True);D.add_argument('--all-documents',action='store_true',help='לגזור מכל המסמכים החוזיים ולא רק מהתבניות המאושרות');D.add_argument('--family',help='משפחת ההסכם של העסקה (family במרשם, או שם או כינוי שלה)');D.add_argument('--role',help='התפקיד של החברה בעסקה: company_role_code (<תפקיד החברה>) או תווית המרשם');A=D.parse_args();guard_out(A.out,[A.registry]);T=json.load(io.open(A.registry,encoding='utf-8'));C=T.get('documents',[])
	if not A.all_documents:C=[A for A in C if A.get('approved_current')]
	U=len(C)
	if A.family:C=[B for B in C if family_matches(B.get('family'),[A.family])]
	I=normalize_role(A.role)if A.role else None
	if I:C=[A for A in C if doc_role(A)==I]
	if U and not C:print('אין במרשם מסמכים של המשפחה והתפקיד שנמסרו (--family, --role). ערכים לא נגזרו, ויש לשאול את המשתמש.');sys.exit(2)
	if not C:print('אין מסמכים לגזירה. יש להריץ תחילה את build_template_registry.py.');sys.exit(2)
	G=[]
	for E in C:
		J=os.path.join(E.get('folder',''),E['file'])
		if J.lower().endswith('.docx'):V='base'if E.get('approved_current_basis')=='redline_base'else'final';K=' '.join(docx_paragraphs(J,limit=20000,mode=V))
		else:K=io.open(J,encoding='utf-8',errors='ignore').read()
		if K:G.append((E['file'],E.get('family'),normalize(K),doc_role(E)))
	L=[]
	for H in G:
		if(H[1],H[3])not in L:L.append((H[1],H[3]))
	B=[]
	for(O,P)in L:Q=[A for A in G if(A[1],A[3])==(O,P)];B.append({'family':O,'company_role':P,'documents_scanned':len(Q),'parameters':derive(Q)})
	R=B[0]['parameters']if len(B)==1 else[];W={'generated_at':date.today().isoformat(),'documents_scanned':len(G),'family':A.family or(B[0]['family']if len(B)==1 else None),'company_role':I or(B[0]['company_role']if len(B)==1 else None),'groups':B,'scope':'כל המסמכים החוזיים'if A.all_documents else'תבניות מאושרות בלבד','source':'נגזר מהניירות של הלקוח, אינו ברירת מחדל כללית','method':'לכל פרמטר עוגן נושאי, והערך נחפש רק בחלון שסביבו. ערך שאותר מחוץ להקשרו אינו נספר.','parameters':R,'mixed_groups_note':None if len(B)<=1 else'ההסכמים שייכים ליותר ממשפחה אחת או מתפקיד אחד של החברה, ולכן אין ערך אחד לכל פרמטר. הרץ שוב עם --family ו---role של העסקה, או קרא את הצירוף המתאים ב-groups.','usage_rule':'ערך נגזר מוצג למשתמש לאישור או לשינוי, ואינו נכנס לטיוטה בלי אישור. ערך שסטטוסו שנוי או מופע יחיד מוצג כשאלה ולא כברירת מחדל. כשקיים פלייבוק, עמדת הפלייבוק גוברת על הערך הנגזר. הפיזור בין ההסכמים חשוב לא פחות מהערך השכיח: פיזור רחב מעיד שאין לחברה עמדה אחידה, וזה עצמו ממצא.'};M=os.path.dirname(os.path.abspath(A.out))
	if M and not os.path.isdir(M):os.makedirs(M)
	io.open(A.out,'w',encoding='utf-8').write(json.dumps(W,ensure_ascii=False,indent=2));print('נגזרו ברירות מחדל מ-%d מסמכים'%len(G))
	if len(B)>1:
		print('  שים לב: %d צירופים של משפחה ותפקיד. הרץ עם --family ו---role של העסקה:'%len(B))
		for N in B:print('    %s / %s: %d מסמכים'%(N['family']or'לא זוהתה',N['company_role']or'לא צוין',N['documents_scanned']))
	for F in R:
		S=''
		if F.get('distribution')and len(F['distribution'])>1:S='  פיזור: '+', '.join('%s (%d)'%(A['value'],A['documents'])for A in F['distribution'][:4])
		print('  %-26s %-8s %-22s%s'%(F['parameter'],F['value']or'לא נגזר',F.get('support',''),S))
if __name__=='__main__':main()
