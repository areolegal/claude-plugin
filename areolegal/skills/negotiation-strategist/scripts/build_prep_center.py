# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,io,json,os,re,sys,tempfile,urllib.parse
from pathlib import Path
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from areo_rt import ensure_lib
import validate_data as vd
ensure_lib()
try:from common.cli import OutputRefused,guard_out
except ImportError:
	class OutputRefused(Exception):0
	def guard_out(out,inputs=()):
		A=out;B=os.path.normcase(os.path.realpath(A))
		if any(A and os.path.normcase(os.path.realpath(A))==B for A in inputs):raise OutputRefused('--out הוא קובץ קלט: %s'%A)
		if os.path.isfile(B)and B.lower().endswith(('.docx','.doc','.pdf','.xlsx','.pptx')):raise OutputRefused('--out הוא מסמך קיים: %s'%A)
		return os.path.abspath(A)
DATA_DIR='Areo-נתונים'
TEMPLATE_NAME='prep-center-template'
SKILL_DIRS='מהתוסף','תוכן מהשרת','skills','runtime'
DEFAULT_TEMPLATE=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),'assets',TEMPLATE_NAME+'.html')
def is_temp_copy(path):
	A=os.path.normcase(os.path.realpath(path));B=os.path.normcase(os.path.realpath(tempfile.gettempdir())).rstrip('\\/')+os.sep
	if not A.startswith(B):return False
	C=[A.lower()for A in A[len(B):].split(os.sep)[:-1]];return not any(A in SKILL_DIRS for A in C)
PLACEHOLDER='__STRATEGY_DATA__'
def load(p):return io.open(p,encoding='utf-8').read()
def derive_urls(data):
	C=data.setdefault('meta',{});B=C.get('docAccess')or{'mode':'local'};C['docAccess']=B
	if B.get('mode')!='base'or not B.get('baseUrl'):return 0
	F=B['baseUrl'].rstrip('/');D=0
	for A in data.get('footnotes',[])or[]:
		E=A.get('file')
		if not E or A.get('webUrl')or A.get('urlSource')=='none':continue
		A['webUrl']=F+'/'+urllib.parse.quote(E);A['urlSource']='derived';D+=1
	return D
def inject(tpl,data):
	A=tpl;C=json.dumps(data,ensure_ascii=False).replace('—',', ').replace('–','-').replace('</','<\\/')
	if A.count(PLACEHOLDER)!=1:sys.exit('שגיאה: מציין המיקום %s חייב להופיע פעם אחת בתבנית, נמצא %d'%(PLACEHOLDER,A.count(PLACEHOLDER)))
	B=A.replace(PLACEHOLDER,C)
	if'—'in B or'–'in B:sys.exit('שגיאה: מקף ארוך זלג לתוצר')
	return B
TITLES={'he':'Areo | מרכז היערכות למשא ומתן','en':'Areo | Negotiation prep centre'}
def _he_en(v):v=str(v or'').strip().lower();return'en'if v[:2]=='en'or v in('english','אנגלית')else'he'
THEME_KEYS='primary_light','secondary_light','soft_light','on_light','primary_dark','secondary_dark','soft_dark','on_dark'
def apply_theme(data,profile):
	B=((profile or{}).get('branding')or{}).get('theme')or{};A={A:(B.get('tokens')or{}).get(A)for A in THEME_KEYS}
	if B.get('choice')!='yes':return
	if not all(re.match('^#[0-9A-Fa-f]{6}$',str(A or''))for A in A.values()):return'מיתוג: אושר, אך הצבעים עוד לא נגזרו (build_profile.py --derive-theme). התוצר נבנה בעיצוב הרגיל'
	data.setdefault('meta',{}).setdefault('branding',{})['theme']=A;return'מיתוג: צבעי המותג של הלקוח הוחלו (%s)'%A['primary_light']
def resolve_lang(data,lang_arg=None,profile=None):
	A=data.setdefault('meta',{});D=profile or{};C=lang_arg or D.get('deliverable_language')or A.get('deliverable_language')or A.get('display_language')or A.get('lang')or'he';C=str(C).strip().lower()
	if C=='both':
		B=_he_en(D.get('display_language')or A.get('display_language')or'he');A['display_language']=B
		if not A.get('agreement_language'):print('אזהרה: deliverable_language הוא both בלי meta.agreement_language. מייל הסיכום ייכתב בשפת המרכז (%s)'%B)
	else:B=_he_en(C)
	A['deliverable_language']=B;return B
def localize_shell(html,lang):
	A=html
	if lang!='en':return A
	A=A.replace('<html lang="he" dir="rtl">','<html lang="en" dir="ltr">',1);return A.replace('<title>%s</title>'%TITLES['he'],'<title>%s</title>'%TITLES['en'],1)
def to_artifact(html,lang='he'):
	A=html;B=re.search('<title>.*?</title>',A,re.S);C=re.search('<body[^>]*>(.*)</body>',A,re.S)
	if not(B and C):sys.exit('שגיאה: מבנה התבנית אינו כצפוי, לא ניתן להפיק תוכן לפרסום')
	D=re.findall('<style>.*?</style>|<script>.*?</script>',A[:A.index('<body')],re.S);E,F=('ltr','en')if lang=='en'else('rtl','he');return B.group(0)+'\n'+'\n'.join(D)+'\n<script>document.documentElement.setAttribute("dir","%s");document.documentElement.setAttribute("lang","%s");</script>\n'%(E,F)+C.group(1).strip()+'\n'
EXT_TXT={'he':{'dir':'rtl','hello':'שלום,','intro':'בהמשך לשיחתנו, להלן עיקרי הדברים:','close':'נשמח לתגובתכם.','regards':'בברכה,','fill':'[להשלמה]','subj':'הנדון: '},'en':{'dir':'ltr','hello':'Hello,','intro':'Following our conversation, the main points are:','close':'We look forward to your response.','regards':'Kind regards,','fill':'[to be completed]','subj':'Subject: '}}
def render_external(view,lang):C=view;import html as A;B=EXT_TXT['en'if lang=='en'else'he'];F,D=C['meta'],C['outbound'];E=D.get('subject')or F.get('agreement')or B['fill'];G=[A['text']for A in D.get('items',[])];H='\n'.join('<li>%s</li>'%A.escape(B)for B in G)or'<li>%s</li>'%A.escape(B['fill']);I=json.dumps(C,ensure_ascii=False).replace('</','<\\/');return'<!DOCTYPE html>\n<html lang="%s" dir="%s"><head><meta charset="utf-8"><title>%s</title></head><body>\n<p>%s%s</p><p>%s</p><p>%s</p><ul>\n%s\n</ul><p>%s</p><p>%s</p>\n<script type="application/json" id="outbound-data">%s</script>\n</body></html>\n'%('en'if lang=='en'else'he',B['dir'],A.escape(E),A.escape(B['subj']),A.escape(E),A.escape(B['hello']),A.escape(B['intro']),H,A.escape(B['close']),A.escape(B['regards']),I)
def check_state(data,state):
	E=data;D=state;C=[];F=E.get('meta')or{};A=None
	for J in('round_number','current_round','round'):
		G=D.get(J,(D.get('meta')or{}).get(J)if isinstance(D.get('meta'),dict)else None)
		if isinstance(G,int)and not isinstance(G,bool):A=G;break
	if A is not None and isinstance(F.get('round_number'),int)and F['round_number']!=A:C.append('מצב העסקה בסבב %s והנתונים בסבב %s'%(A,F['round_number']))
	B=(E.get('proposal')or{}).get('base')or{}
	if A is not None and isinstance(B.get('round_number'),int)and B['round_number']!=A:C.append('הצעת השינוי נשענת על סבב %s ומצב העסקה בסבב %s'%(B['round_number'],A))
	H=D.get('last_updated')
	if H and B.get('state_updated')and str(B['state_updated'])!=str(H):C.append('הצעת השינוי נשענת על גרסה %s של קובץ המצב, והחי הוא %s'%(B['state_updated'],H))
	I=(E.get('practice')or{}).get('base_round')
	if A is not None and isinstance(I,int)and I!=A:C.append('התרגול נעשה בסבב %s ומצב העסקה בסבב %s'%(I,A))
	return C
def client_roots(*E):
	B=set()
	for C in E:
		if not C:continue
		D=Path(os.path.abspath(C))
		for A in[D]+list(D.parents):
			if A.name==DATA_DIR:B.add(str(A.parent))
			elif A.is_dir()and(A/DATA_DIR).is_dir():B.add(str(A))
	return B
def template_in_client_folder(template,*C):
	A=template;D=os.path.normcase(os.path.abspath(A))
	for B in sorted(client_roots(A,*C)):
		if D.startswith(os.path.normcase(B).rstrip('\\/')+os.sep):return B
def main(argv=None):
	C=argparse.ArgumentParser();C.add_argument('--data',required=True);C.add_argument('--template',help='רשות. בלעדיו: העותק שבתוסף, %s'%DEFAULT_TEMPLATE);C.add_argument('--out');C.add_argument('--external-out',dest='external_out');C.add_argument('--state');C.add_argument('--artifact');C.add_argument('--lang',choices=('he','en','both'));C.add_argument('--profile');C.add_argument('--keep-template',action='store_true',help='לא למחוק את העותק הזמני של התבנית אחרי הבנייה');A=C.parse_args(argv)
	if not A.out and not A.artifact and not A.external_out:sys.exit('שגיאה: יש לציין --out, --artifact או --external-out')
	Q=bool(A.template)
	if(A.out or A.artifact)and not A.template:A.template=DEFAULT_TEMPLATE
	if A.template and not os.path.isfile(A.template):sys.exit('שגיאה: התבנית אינה קיימת: %s'%A.template)
	H=template_in_client_folder(A.template,A.data,A.out,A.artifact,A.profile)if A.template else None
	if H:print('סירוב: --template בתוך תיקיית הלקוח או Areo-נתונים (%s). התבנית היא תוכן של Areo ונארזת בתוסף: מריצים בלי --template, והעותק שבתוסף נקרא (%s).\nRefused: --template is inside the client folder. Run without --template to use the copy bundled with the plugin.'%(H,DEFAULT_TEMPLATE));return 2
	try:
		for I in(A.out,A.artifact,A.external_out):
			if I:guard_out(I,inputs=[A.data,A.template,A.profile,A.state])
	except OutputRefused as E:print('סירוב: %s'%E);return 1
	B=json.load(io.open(A.data,encoding='utf-8'));J=json.load(io.open(A.profile,encoding='utf-8'))if A.profile else{}
	if A.state:
		K=check_state(B,json.load(io.open(A.state,encoding='utf-8')))
		if K:print('נדרש רענון, לא נכתב דבר (קוד 3):\n  '+'\n  '.join(K));return 3
	F=resolve_lang(B,A.lang,J);L=apply_theme(B,J);M=localize_shell(load(A.template),F)if A.template and(A.out or A.artifact)else'';R=derive_urls(B);S=(B.get('meta',{}).get('docAccess')or{}).get('mode','local')
	if A.external_out:
		G=vd.external_view(B);T=_he_en((B.get('meta')or{}).get('agreement_language')or F);N=render_external(G,T);O=vd.leak_check(N.encode('utf-8'),B)
		if O:print('הדלפה מילולית בעותק לצד השני, לא נכתב (קוד 4). שדות פנימיים שתוכנם נמצא:\n  '+'\n  '.join(O));return 4
		for U in G['outbound']['items']:
			if vd.WORDLIST.search(U['text']):print('אזהרה: בנוסח לצד השני מונח של משא ומתן פנימי: בדיקת רשימת מילים משלימה, נדרשת סקירה')
		io.open(A.external_out,'w',encoding='utf-8',newline='\n').write(N);print('עותק לצד השני נכתב: %d פריטים מאושרים. בדיקת תוכן מדויק עברה (הדלפה בניסוח מחדש אינה ניתנת להוכחה בקוד: נדרשת סקירת עורך דין)'%len(G['outbound']['items']))
	if A.out:D=json.loads(json.dumps(B));D['meta']['publishTarget']='local';io.open(A.out,'w',encoding='utf-8').write(inject(M,D))
	if A.artifact:D=json.loads(json.dumps(B));D['meta']['publishTarget']='artifact';io.open(A.artifact,'w',encoding='utf-8').write(to_artifact(inject(M,D),F))
	P=B.get('footnotes',[])or[];V=sum(1 for A in P if A.get('webUrl'));print('מצב גישה: %s. ציטוטים עם קישור למסמך: %d מתוך %d. נגזרו כעת: %d'%(S,V,len(P),R))
	if L:print(L)
	if Q and not A.keep_template and os.path.basename(A.template).lower().startswith(TEMPLATE_NAME)and is_temp_copy(A.template):
		try:os.remove(A.template);print('העותק הזמני של התבנית נמחק: %s'%A.template)
		except OSError as E:print('אזהרה: העותק הזמני של התבנית לא נמחק (%s): %s'%(type(E).__name__,A.template))
	return 0
if __name__=='__main__':sys.exit(main())
