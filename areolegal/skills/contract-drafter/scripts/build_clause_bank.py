# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys
from datetime import date
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text,docx_paragraphs,guard_out
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
HEADING_INLINE=re.compile('^(?:סעיף\\s+)?(\\d+(?:\\.\\d+)*)\\s*[:\\.\\)]\\s*(.{2,70}?)\\s*$')
HEADING_SPLIT=re.compile('^(?:סעיף\\s+)?(\\d+(?:\\.\\d+)*)\\s*[:\\.\\)]\\s+(.{2,70}?)[\\.:]\\s+(.{40,})$',re.S)
TOPICS=[('הגדרות ופרשנות',['הגדרות','פרשנות','definitions','interpretation']),('מהות ההתקשרות והיקפה',['מהות ההתקשרות','היקף ההתקשרות','היקף השירותים','מתן השירותים','מהות ההסכם','scope of','the services','appointment','grant of rights','engagement','scope','the services']),('תקופה, חידוש וסיום',['תקופת','סיום','פקיעה','השבה','ביטול ההסכם','חידוש','הודעה מוקדמת','השעיה','term and termination','termination','renewal','expiration','term','effect of termination','suspension']),('אופציות והארכה',['אופציה','אופציית','מימוש האופציה','הארכת ההתקשרות','זכות סירוב','option to','right of first refusal']),('תמורה ותנאי תשלום',['תמורה','תשלום','תמלוגים','דמי שימוש','מחירון','הצמדה','ריבית פיגורים','התחשבנות','payment','fees','consideration','royalt','price','pricing','invoic','discount','taxes']),('סודיות',['סודיות','מידע סודי','אי גילוי','היקף החשיפה','השבת המידע','השמדת','גילוי הנדרש','גילוי על פי דין','confidential']),('קניין רוחני ומותג',['קניין רוחני','זכויות יוצרים','סימני מסחר','המותג','רישיון שימוש','שימוש מותר','בעלות בנתונים','intellectual property','trademark','proprietary rights','ownership','branding','marks']),('אחריות והגבלתה',['הגבלת אחריות','גבולות אחריות','אחריות והגבלתה','אחריות הצדדים','תקרת אחריות','נזק תוצאתי','limitation of liability','disclaimer','limited liability','limitation on liability','no consequential','disclaimer of warranties']),('שיפוי',['שיפוי','לשפות','indemnif']),('ביטוח',['ביטוח','פוליסה','אישור קיום ביטוחים','חובת גילוי','מקרה ביטוח','insurance']),('הגנת הפרטיות ואבטחת מידע',['הגנת הפרטיות','מידע אישי','אבטחת מידע','עיבוד מידע','data protection','personal data','privacy','security']),('ציות, אנטי שוחד וסנקציות',['ציות','אנטי שוחד','שחיתות','סנקציות','אמברגו','anti-bribery','compliance','sanctions','anti-corruption','export law','export control','trade compliance']),('רמת שירות, תמיכה ותחזוקה',['רמת שירות','sla','זמני תגובה','תמיכה','זמינות','תחזוקה','תקלות','תיקונים','service level','maintenance','support','maintenance and support','availability']),('אי תחרות ואי שידול',['אי תחרות','אי-תחרות','אי שידול','אי-שידול','הגבלת עיסוק','non-compete','non-solicit','no solicitation']),('דיווח, ספרים וביקורת',['דיווח','ספרים','ביקורת','audit','reporting','books and records','reports','records','audit rights']),('התחייבויות הצדדים',['התחייבויות','מצגים','מצג','יחסי הצדדים','היעדר מצג','representations','warranties','undertakings','obligations','covenants']),('ערבויות וביטחונות',['ערבות','ביטחונות','פיקדון','שטר חוב','guarantee','security deposit']),('קיזוז ועיכבון',['קיזוז','עיכבון','set-off','lien']),('המחאה והסבה',['המחאת','הסבת','העברת זכויות','איסור העברה','העברת הזכויות','assignment']),('שינויים והתאמות',['שינויים','התאמות','שינוי ההסכם','amendment','change order']),('כוח עליון',['כוח עליון','force majeure']),('הפרה, סעדים ותרופות',['הפרה','סעדים','תרופות','פיצוי מוסכם','breach','remedies']),('הודעות',['הודעות','מסירת הודעות','notices','notice']),('דין, סמכות שיפוט ויישוב מחלוקות',['דין וסמכות','סמכות שיפוט','הדין החל','בוררות','יישוב מחלוקות','governing law','jurisdiction','dispute resolution','arbitration']),('שונות',['שונות','שלמות ההסכם','ויתור','נפרדות','כותרות','miscellaneous','entire agreement','severability','waiver'])]
CORE_TOPICS='הגדרות ופרשנות','תקופה, חידוש וסיום','הפרה, סעדים ותרופות','המחאה והסבה','הודעות','דין, סמכות שיפוט ויישוב מחלוקות','שונות'
def norm(s):return re.sub('[\\-־–]',' ',s.lower())
def topic_of(heading,body):
	F=norm(heading)
	for(A,B)in TOPICS:
		for G in B:
			if norm(G)in F:return A,'כותרת הסעיף'
	H=norm(body[:600]);D,C=None,0
	for(A,B)in TOPICS:
		E=sum(H.count(norm(A))for A in B)
		if E>C:D,C=A,E
	if C>=2:return D,'גוף הסעיף, טעון אישור'
	return None,None
NOT_A_HEADING=re.compile('^\\d{1,2}\\.\\d{1,2}\\.\\d{4}$|₪|^\\d+$|בין הצדדים|מצד אחד|^(?:reseller|master|mutual|software|services?|distribution|license)?\\s*(?:agreement|contract)\\s*$|^witnesseth|^background\\s*$|^recitals?\\s*$|^preamble\\s*$|^הואיל\\s*$',re.I)
def looks_like_bare_heading(p):
	p=p.strip().rstrip('.:')
	if not 3<=len(p)<=70:return False
	if p.endswith((',',';'))or p.count(' ')>8:return False
	A=[A for A in re.split('\\s+',p)if A]
	if not A:return False
	B=[A for A in A if re.match('^[A-Za-z]',A)]
	if B and len(B)==len(A):
		if p.isupper():return True
		C=sum(1 for A in A if A[:1].isupper())
		if C>=max(1,len(A)-1):return True
		return False
	if re.search('[\u0590-\u05ff]',p)and not p.endswith('.'):return True
	return False
def split_clauses(paras):
	E=paras;C=[]
	for(B,D)in enumerate(E):
		if NOT_A_HEADING.search(D.strip()):continue
		A=HEADING_INLINE.match(D.strip())
		if A and not re.match('^\\d{1,2}\\.\\d{1,2}\\.\\d{4}',D.strip()):C.append((B,A.group(1),A.group(2).strip(' :.-'),''));continue
		A=HEADING_SPLIT.match(D.strip())
		if A:C.append((B,A.group(1),A.group(2).strip(' :.-'),A.group(3).strip()));continue
		if looks_like_bare_heading(D)and B+1<len(E)and len(E[B+1])>120:C.append((B,None,D.strip().rstrip('.:'),''))
	G=[]
	for(H,(B,J,I,K))in enumerate(C):
		L=C[H+1][0]if H+1<len(C)else len(E);F=' '.join([K]+E[B+1:L]).strip();F=re.sub('\\s+',' ',F)
		if len(I)<3 or len(F)<60:continue
		G.append((J,I,F))
	return G
def main():
	F=argparse.ArgumentParser();F.add_argument('--registry',required=True);F.add_argument('--out',required=True);F.add_argument('--max-chars',type=int,default=2500,help='אורך מרבי לנוסח שנשמר, כדי שהבנק לא יתנפח');C=F.parse_args();guard_out(C.out,[C.registry]);Q=json.load(io.open(C.registry,encoding='utf-8'));E=[A for A in Q.get('documents',[])if A.get('approved_current')]
	if not E:print('אין תבניות מאושרות במרשם. יש להריץ תחילה את build_template_registry.py.');sys.exit(2)
	D,G=[],[]
	for A in E:
		I=os.path.join(A.get('folder',''),A['file'])
		if I.lower().endswith('.docx'):R='base'if A.get('approved_current_basis')=='redline_base'else'final';J=docx_paragraphs(I,mode=R)
		else:J=io.open(I,encoding='utf-8',errors='ignore').read().split('\n')
		if not J:continue
		for(S,N,K)in split_clauses(J):O,T=topic_of(N,K);U={'topic':O,'topic_basis':T,'heading':N,'clause_number':S,'source_file':A['file'],'source_folder':A.get('folder'),'family':A.get('family'),'company_role_candidates':A.get('company_role_candidates',[]),'side':'טעון בירור: המסמך הוא redline ולא נקבע מי סימן את השינויים'if A.get('approved_current_basis')=='redline_base'else'נייר הלקוח','usable_as_house_wording':A.get('approved_current_basis')!='redline_base','language':A.get('language'),'text':K[:C.max_chars],'truncated':len(K)>C.max_chars};(D if O else G).append(U)
	B={}
	for P in D:B.setdefault(P['topic'],[]).append(P)
	for H in B:B[H].sort(key=lambda x:-len(x['text']))
	L={'generated_at':date.today().isoformat(),'source':'נוסחים שנלקחו כלשונם מהתבניות המאושרות של הלקוח','templates_used':[A['file']for A in E],'topics_found':sorted(B.keys()),'topics_missing':[A for A in CORE_TOPICS if A not in B],'topics_missing_by_family':{A:[B for B in CORE_TOPICS if B not in{B['topic']for B in D if B['family']==A}]for A in sorted({A.get('family')or''for A in E})},'topics_not_found':[A for(A,C)in TOPICS if A not in B and A not in CORE_TOPICS],'topics_not_found_note':'נושאים שאינם בכל סוג הסכם ולא נמצא להם נוסח בית. אינם חסר: רלוונטיים רק כשהפלייבוק או ההסכם עצמו מעלים אותם.','clauses':D,'unmatched_clauses':[{'heading':A['heading'],'clause_number':A['clause_number'],'source_file':A['source_file']}for A in G],'precedence':'הפלייבוק גובר על בנק הסעיפים. הבנק גובר על ניסוח חדש. נוסח שנושאו נקבע לפי גוף הסעיף בלבד מסומן כך בדף הליווי, עם שם ההסכם והסעיף שממנו נלקח.','side_warning':'סעיף שסומן usable_as_house_wording=false נלקח ממסמך שלא נקבע מאיזה צד הוא מנוסח. אין להשתמש בו כלשון בית ואין להכניסו לטיוטה לפני שהמשתמש קבע מי סימן את השינויים במסמך המקור. הכנסת נוסח שנכתב מהצד האחר מנסחת את ההסכם נגד האינטרס של הלקוח.','unresolved_side':sorted({A['source_file']for A in D if not A['usable_as_house_wording']})};M=os.path.dirname(os.path.abspath(C.out))
	if M and not os.path.isdir(M):os.makedirs(M)
	io.open(C.out,'w',encoding='utf-8').write(json.dumps(L,ensure_ascii=False,indent=2));print('נאספו %d סעיפים מתוך %d תבניות מאושרות, ב-%d נושאים'%(len(D),len(E),len(B)))
	for H in sorted(B,key=lambda x:-len(B[x])):print('  %-30s %d נוסחים'%(H,len(B[H])))
	if L['topics_missing']:print('נושאים כלליים שאין להם נוסח בית: '+', '.join(L['topics_missing']))
	if G:print('%d סעיפים לא שויכו לנושא ונשמרו לעיון'%len(G))
if __name__=='__main__':main()
