# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys
from collections import Counter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text,docx_paragraphs,docx_num_formats,guard_out
try:sys.stdout.reconfigure(encoding='utf-8')
except(AttributeError,ValueError):pass
AUTO_FMT={'decimal':'ספרות','hebrew1':'אותיות עבריות','hebrew2':'אותיות עבריות','lowerLetter':'אותיות לטיניות קטנות','upperLetter':'אותיות לטיניות גדולות','lowerRoman':'ספרות רומיות קטנות','upperRoman':'ספרות רומיות גדולות','bullet':'תבליט'}
def detect_numbering(paras,path=None):
	B=E=F=C=D=0
	for A in paras:
		if re.match('^\\d+\\.\\d+\\.\\d+[\\.\\s]',A):F+=1
		elif re.match('^\\d+\\.\\d+[\\.\\s]',A):E+=1
		elif re.match('^\\d+[\\.\\)]\\s',A):B+=1
		if re.match("^[אבגדהוזחט]['׳]\\s",A):C+=1
		elif re.match('^\\([אבגדהוזחט]\\)\\s',A):D+=1
	if B+E+F+C+D<3 and path:
		J=docx_num_formats(path);H=[AUTO_FMT.get(A,A)for(A,B)in J if A!='bullet']
		if H:
			G=[]
			for I in H:
				if I not in G:G.append(I)
			return'מספור אוטומטי של Word (%s)'%', '.join(G[:3])
	if F>=3:return'עשרוני תלת רמתי (1, 1.1, 1.1.1)'
	if E>=3:return'עשרוני דו רמתי (1, 1.1)'
	if B>=3 and C+D>=3:return'עשרוני בסעיפים ראשיים, אותיות עבריות בסעיפי משנה'
	if B>=3:return'עשרוני חד רמתי (1, 2, 3)'
	if C+D>=3:return'אלפביתי עברי'
DEF_PATTERNS=[('(להלן: "X")','\\(להלן:\\s*[""״"]'),('(להלן "X")','\\(להלן\\s+[""״"]'),('("X")','\\(\\s*[""״"][^""״"]{2,40}[""״"]\\s*\\)'),('hereinafter "X"','\\(hereinafter[:,]?\\s+(?:the\\s+)?["“]'),('(the "X")','\\(the\\s+["“]')]
SIGN_PATTERNS=[('ולראיה באו הצדדים על החתום','ולראיה\\s+באו\\s+הצדדים\\s+על\\s+החתום'),('ובאו הצדדים על החתום','ובאו\\s+הצדדים\\s+על\\s+החתום'),('ולראיה באנו על החתום','ולראיה\\s+באנו\\s+על\\s+החתום'),('IN WITNESS WHEREOF','IN\\s+WITNESS\\s+WHEREOF')]
PREAMBLE_PATTERNS=[('הואיל וכן הואיל, בסיום: לפיכך הוסכם','הואיל'),('WHEREAS','WHEREAS')]
ANNEX_PATTERNS=[("נספח א', נספח ב'","נספח\\s+[אבגדה]['׳]"),('נספח 1, נספח 2','נספח\\s+\\d'),('תוספת ראשונה','תוספת\\s+(?:ראשונה|שנייה|שלישית)'),('Exhibit A / Schedule 1','(?:Exhibit\\s+[A-D]|Schedule\\s+\\d)')]
EN_NAME="([A-Z](?:[\\w'\\-]|\\.(?=\\w))*(?:\\s+(?:[A-Z](?:[\\w'\\-]|\\.(?=\\w))*|of|and|the))*)"
EN_STATE_PREFIX='(?:the\\s+)?(?:(?i:State|Commonwealth|Province|Republic|Federal\\s+Republic|Kingdom|Grand\\s+Duchy|Emirate|Canton)\\s+of\\s+(?:the\\s+)?)?'
LAW_EN=[re.compile('(?i:governed\\s+by|construed|interpreted|enforced|governing\\s+law)[^.;]{0,90}?(?i:laws?)\\s+(?i:of)\\s+'+EN_STATE_PREFIX+EN_NAME),re.compile('(?i:laws?)\\s+(?i:of)\\s+'+EN_STATE_PREFIX+EN_NAME+'(?=[^.;]{0,60}(?i:shall|will)\\s+govern)')]
EN_ADJ={'English and Welsh':'אנגליה ווילס','English':'אנגליה','Welsh':'אנגליה ווילס','Scottish':'סקוטלנד','Scots':'סקוטלנד','Northern Irish':'צפון אירלנד','British':'הממלכה המאוחדת','German':'גרמניה','French':'צרפת','Swiss':'שווייץ','Dutch':'הולנד','Irish':'אירלנד','Cypriot':'קפריסין','Israeli':'ישראל','New York':'ניו יורק','Delaware':'דלאוור','Californian':'קליפורניה','California':'קליפורניה','Texan':'טקסס','Texas':'טקסס','New Jersey':"ניו ג'רזי",'Massachusetts':"מסצ'וסטס",'Florida':'פלורידה','Illinois':'אילינוי','Singaporean':'סינגפור','Singapore':'סינגפור','Hong Kong':'הונג קונג','Italian':'איטליה','Spanish':'ספרד','Portuguese':'פורטוגל','Belgian':'בלגיה','Luxembourg':'לוקסמבורג','Austrian':'אוסטריה','Swedish':'שוודיה','Danish':'דנמרק','Norwegian':'נורווגיה','Finnish':'פינלנד','Polish':'פולין','Czech':"צ'כיה",'Greek':'יוון','Maltese':'מלטה','Japanese':'יפן','Chinese':'סין','Indian':'הודו','Canadian':'קנדה','Ontario':'אונטריו','Australian':'אוסטרליה','New Zealand':'ניו זילנד','Brazilian':'ברזיל','South African':'דרום אפריקה','Korean':'דרום קוריאה'}
_EN_ADJ_ALT='|'.join(re.escape(A)for A in sorted(EN_ADJ,key=len,reverse=True))
LAW_EN_ADJ=[re.compile('(?i:governed\\s+by|construed|interpreted|enforced|governing\\s+law|subject\\s+to)[^.;]{0,60}?\\b('+_EN_ADJ_ALT+')\\s+(?i:laws?)\\b'),re.compile('\\b('+_EN_ADJ_ALT+')\\s+(?i:laws?)(?=[^.;]{0,40}(?i:shall|will)\\s+(?i:govern|apply))')]
LAW_HE_CONTEXT='הדין\\s+החל|יחולו|יחול\\s|יפורש|יפורשו|כפוף\\s+ל|בכפוף\\s+ל|ייקבע\\s+על\\s+פי|יוכרע\\s+לפי|דין\\s+חל|הדין\\s+השולט'
LAW_HE=re.compile('(?:^|[\\s(])[ול]?(?:דיני|חוקי)\\s+(מדינת\\s+)?([א-ת][א-ת\'׳\\"״\\-]+)(?:\\s+([א-ת][א-ת\'׳\\-]+))?')
LAW_HE_ADJ=re.compile('(?:^|[\\s(])[ולב]?ה?(?:דין|חוק|משפט)\\s+ה([א-ת]{3,}י)(?![א-ת])')
HE_MULTI={'ניו':('יורק',"ג'רזי",'ג׳רזי','זילנד'),'הונג':('קונג',),'הממלכה':('המאוחדת',),'ארצות':('הברית',),'דרום':('אפריקה','קוריאה'),'איחוד':('האמירויות',)}
HE_NOT_PLACE='הגנת','מס','מיסים','עבודה','חוזים','נזיקין','קניין','ביטוח','תחרות','חברות','ניירות','פרטיות','צרכנות','בוררות','ראיות','הסכם','ההסכם','הצדדים','אחרים','כלשהם'
HE_ADJ={'ישראלי':'ישראל','אנגלי':'אנגליה','סקוטי':'סקוטלנד','בריטי':'הממלכה המאוחדת','גרמני':'גרמניה','צרפתי':'צרפת','הולנדי':'הולנד','קנדי':'קנדה','אוסטרלי':'אוסטרליה','בלגי':'בלגיה','אוסטרי':'אוסטריה','פולני':'פולין','פורטוגלי':'פורטוגל','הודי':'הודו','שווייצרי':'שווייץ','אירי':'אירלנד','קפריסאי':'קפריסין','אמריקאי':'ארצות הברית','אמריקני':'ארצות הברית','סינגפורי':'סינגפור','יפני':'יפן','איטלקי':'איטליה','ספרדי':'ספרד'}
NAME_HE={'israel':'ישראל','england':'אנגליה','england and wales':'אנגליה ווילס','the united kingdom':'הממלכה המאוחדת','united kingdom':'הממלכה המאוחדת','new york':'ניו יורק','delaware':'דלאוור','california':'קליפורניה','germany':'גרמניה','france':'צרפת','the netherlands':'הולנד','netherlands':'הולנד','switzerland':'שווייץ','singapore':'סינגפור','ireland':'אירלנד','cyprus':'קפריסין','japan':'יפן','italy':'איטליה','spain':'ספרד','luxembourg':'לוקסמבורג','the united states':'ארצות הברית','united states':'ארצות הברית'}
def _en_name(raw):A=re.sub('(?:[\\s,]+(?:and|of|the))+$','',raw.strip(' ,.')).strip(' ,.');return NAME_HE.get(A.lower(),A)
def detect_law(t):
	for E in LAW_EN:
		for A in E.finditer(t):
			C=_en_name(A.group(1))
			if C:return'דיני %s'%C,re.sub('\\s+',' ',t[max(0,A.start()-30):A.end()+60]).strip()
	for E in LAW_EN_ADJ:
		for A in E.finditer(t):
			G=next((B for B in EN_ADJ if B.lower()==A.group(1).lower()),None)
			if G:return'דיני %s'%EN_ADJ[G],re.sub('\\s+',' ',t[max(0,A.start()-30):A.end()+60]).strip()
	for H in re.finditer(LAW_HE_CONTEXT,t):
		I,J=max(0,H.start()-90),H.start()+220;D=t[I:J]
		for A in LAW_HE.finditer(D):
			K,B,F=A.group(1),A.group(2),A.group(3)
			if not K and(B in HE_NOT_PLACE or B.startswith('ה')and B not in('הולנד','הודו','הונג')):continue
			C=B+(' '+F if F and F in HE_MULTI.get(B,())else'');return'דיני %s'%C,re.sub('\\s+',' ',D).strip()
		for A in LAW_HE_ADJ.finditer(D):
			if A.group(1)in HE_ADJ:return'דיני %s'%HE_ADJ[A.group(1)],re.sub('\\s+',' ',D).strip()
	return None,None
FORUM_CITIES=[]
FORUM_CONTEXT='סמכות\\s+(?:שיפוט|השיפוט|מקומית|ייחודית)|סמכות\\s+בלעדית|exclusive\\s+jurisdiction|venue\\b|jurisdiction\\s+of\\s+the\\s+courts|submit\\s+to\\s+the|courts\\s+of\\b'
FORUM_EN=re.compile('(?i:courts?)\\s+(?i:of|in|located\\s+in|sitting\\s+in)\\s+'+EN_STATE_PREFIX+'(?:(?i:the\\s+)?(?i:City|County|Borough)\\s+of\\s+)?'+"([A-Z](?:[\\w'\\-]|\\.(?=\\w))*(?:(?:\\s+|,\\s*)(?:[A-Z](?:[\\w'\\-]|\\.(?=\\w))*|of|and|the))*)")
FORUM_HE=re.compile('בתי\\s+ה?משפט\\s+(?:ה?מוסמכים\\s+)?ב(?:מדינת\\s+|עיר\\s+)?([א-ת][א-ת\'׳\\"״\\-]+)(?:\\s+([א-ת][א-ת\'׳\\-]+))?')
ARBITRATION='יימסר\\s+לבורר|יוכרע\\s+בבוררות|הליך\\s+בוררות|\\barbitration\\b'
def detect_forum(t):
	F=re.search(ARBITRATION,t,re.I);G=None
	for I in re.finditer(FORUM_CONTEXT,t,re.I):
		A=re.sub('\\s+',' ',t[max(0,I.start()-120):I.start()+420]).strip();B=next((B for(B,C)in FORUM_CITIES if re.search(C,A)),None)
		if not B:
			H=FORUM_EN.search(A)
			if H and _en_name(H.group(1)):J=_en_name(H.group(1));B=('בתי המשפט ב'if re.match('[א-ת]',J)else'בתי המשפט ב-')+J
			else:
				C=FORUM_HE.search(A);D=re.search("במחוז\\s+([א-ת'׳\\-]+)(?:\\s+([א-ת'׳\\-]+))?",A)
				if C and C.group(1)=='מחוז'and D:E=D.group(2)if D.group(2)and D.group(2)not in('בלבד','או','תהא','הנתונה','ושם')and not D.group(2).startswith('ו')else'';B='בתי המשפט במחוז %s'%(D.group(1)+(' '+E if E else''))
				elif C and not C.group(1).startswith('מחוז'):K,E=C.group(1),C.group(2);B='בתי המשפט ב%s'%(K+(' '+E if E and E in HE_MULTI.get(K,())else''))
		if B:
			if F:return B+', בכפוף לסעיף בוררות',A
			return B,A
		if G is None:G=A
	if F:return'בוררות',re.sub('\\s+',' ',t[max(0,F.start()-60):F.start()+200]).strip()
	if G:return'נקבעה סמכות שיפוט בלי ציון מקום מזוהה',G
	return None,None
_GENERIC_LABELS=['החברה','הצד הראשון','הצד השני','Company','Party A','Party B']
PARTY_COUNTED={'החברה','הצד הראשון','הצד השני'}
_EXTRA_LABELS=[]
def _label_form(w):
	w=w.strip()
	if re.match('[A-Za-z]',w):w=re.sub('^the\\s+','',w,flags=re.I);return' '.join(A[:1].upper()+A[1:]for A in w.split())
	return w
PARTY_LABELS=[]
for _w in _GENERIC_LABELS+_EXTRA_LABELS:
	_w=_label_form(_w)
	if _w and _w not in PARTY_LABELS:PARTY_LABELS.append(_w)
def find_first(t,patterns,window=140):
	for(B,C)in patterns:
		A=re.search(C,t,re.I)
		if A:D=max(0,A.start()-30);E=re.sub('\\s+',' ',t[D:A.start()+window]).strip();return B,E
	return None,None
def detect_date_format(t):
	if re.search('\\b\\d{1,2}\\.\\d{1,2}\\.\\d{4}\\b',t):return'יום.חודש.שנה'
	if re.search('\\b\\d{1,2}/\\d{1,2}/\\d{4}\\b',t):return'יום/חודש/שנה'
	if re.search('ביום\\s+\\d{1,2}\\s+ב?[א-ת]+\\s+\\d{4}',t):return'מילולי (ביום 3 במרץ 2026)'
def detect_language(t):
	A=len(re.findall('[א-ת]',t));B=len(re.findall('[A-Za-z]',t))
	if A>B*2:return'עברית'
	if B>A*2:return'אנגלית'
	return'דו לשוני'
class Convention:
	def __init__(A,name,question):A.name=name;A.question=question;A.votes=Counter();A.evidence={}
	def add(B,value,source,quote=None):
		A=value
		if not A:return
		B.votes[A]+=1;B.evidence.setdefault(A,{'source':source,'quote':quote})
	def resolve(A,total):
		E=total
		if not A.votes:return{'name':A.name,'question':A.question,'value':None,'status':'לא נלמדה','note':'לא אותרה מוסכמה בתבניות המאושרות, יש לשאול את המשתמש'}
		B=A.votes.most_common();F,C=B[0];H=B[1][1]if len(B)>1 else 0
		if C==H:D='שנויה'
		elif C>=max(2,(E+1)//2):D='מבוססת'
		else:D='טעונה אישור'
		G=A.evidence.get(F,{});return{'name':A.name,'question':A.question,'value':F,'status':D,'support':'%d מתוך %d תבניות מאושרות'%(C,E),'alternatives':[{'value':A,'count':B}for(A,B)in B[1:4]],'source_file':G.get('source'),'example':G.get('quote')}
def main():
	I=argparse.ArgumentParser();I.add_argument('--registry',required=True);I.add_argument('--out',required=True);G=I.parse_args();guard_out(G.out,[G.registry]);P=json.load(io.open(G.registry,encoding='utf-8'));M=[A for A in P.get('documents',[])if A.get('approved_current')]
	if not M:print('אין תבניות מאושרות במרשם. יש להריץ תחילה את build_template_registry.py ולאשר תבניות מול המשתמש.');sys.exit(2)
	D={'numbering':Convention('מבנה המספור','כיצד ממוספרים הסעיפים וסעיפי המשנה'),'defined':Convention('סימון מונחים מוגדרים','כיצד מוגדר מונח בפעם הראשונה'),'preamble':Convention('מבוא ההסכם','האם ההסכם נפתח בהואילים'),'signature':Convention('נוסח סגירת החתימה','מהי שורת החתימה הנהוגה'),'annex':Convention('שמות הנספחים','כיצד ממוספרים הנספחים'),'law':Convention('הדין החל','מהו הדין החל שבתבניות'),'forum':Convention('סמכות השיפוט','היכן נקבעת סמכות השיפוט'),'date':Convention('מבנה התאריך','כיצד נכתבים תאריכים בגוף ההסכם'),'language':Convention('שפת ההסכם','באיזו שפה נערכות התבניות')};N=Counter();J=[]
	for C in M:
		E=os.path.join(C.get('folder',''),C['file'])
		try:
			if E.lower().endswith('.docx'):A=docx_text(E)[0]
			else:A=io.open(E,encoding='utf-8',errors='ignore').read()
		except Exception as Q:print('  דילוג על %s: %s'%(C['file'],Q));continue
		if not A or len(A)<500:continue
		J.append(C['file']);F=C['file'];R=docx_paragraphs(E)if E.lower().endswith('.docx')else A.split('\n');D['numbering'].add(detect_numbering(R,E),F)
		for(S,T)in(('defined',DEF_PATTERNS),('preamble',PREAMBLE_PATTERNS),('signature',SIGN_PATTERNS),('annex',ANNEX_PATTERNS)):U,V=find_first(A,T);D[S].add(U,F,V)
		W,X=detect_law(A);D['law'].add(W,F,X);Y,Z=detect_forum(A);D['forum'].add(Y,F,Z);D['date'].add(detect_date_format(A),F);D['language'].add(detect_language(A),F)
		for H in PARTY_LABELS:
			if re.search('["״“”]%s["״“”]'%re.escape(H),A)or H in PARTY_COUNTED and len(re.findall('\\b%s\\b'%re.escape(H),A))>=5:N[H]+=1
	K=len(J);B={'generated_at':__import__('datetime').date.today().isoformat(),'source':'נלמד מתוך התבניות המאושרות של הלקוח בלבד','templates_scanned':K,'template_files':J,'conventions':[D[A].resolve(K)for A in['language','numbering','defined','preamble','annex','signature','law','forum','date']],'party_labels':[{'label':A,'templates':B}for(A,B)in N.most_common(8)],'confirmation_required':[],'disclaimer':'המוסכמות נלמדו בספירה אוטומטית מהתבניות של הלקוח, והדף הנלווה אומר על כמה מסמכים כל אחת נשענת. מוסכמה שנויה נשאלת בשאלה אחת בסבב השאלות, ואחרי התשובה הטיוטה נמסרת נקייה, בלי המתנה לאישור עורך דין.'};import governing_law as a;O=next((A for A in B['conventions']if A.get('value')and str(A['value']).startswith('דיני ')and A.get('status')not in('שנויה','טעונה אישור','לא נלמדה')),None);B['governing_law']=a.code(O['value'])if O else None;B['confirmation_required']=[A['name']for A in B['conventions']if A['status']in('שנויה','טעונה אישור','לא נלמדה')];C=os.path.dirname(os.path.abspath(G.out))
	if C and not os.path.isdir(C):os.makedirs(C)
	io.open(G.out,'w',encoding='utf-8').write(json.dumps(B,ensure_ascii=False,indent=2));print('נלמדו %d תבניות מאושרות'%K)
	for L in B['conventions']:print('  %-24s %-46s %s'%(L['name'],(L['value']or'לא נלמדה')[:46],L['status']))
	if B['party_labels']:print('  כינויי צדדים נפוצים: '+', '.join(A['label']for A in B['party_labels'][:5]))
	if B['confirmation_required']:print('טעון אישור המשתמש: '+', '.join(B['confirmation_required']))
if __name__=='__main__':main()
