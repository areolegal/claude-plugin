# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import calendar,datetime as dt,re
UNITS='days','business_days','weeks','months','years','hours'
KINDS='fixed','relative','recurring','renewal_notice','term_end','event','ongoing','survival'
QUALIFIERS='reasonable','promptly','without_delay','other'
STATUSES='computed','to_complete','needs_verification','needs_legal_review','event_driven','ongoing'
IL_NAMES='il','israel','ישראל'
EN_MONTHS='January','February','March','April','May','June','July','August','September','October','November','December'
DAY_NAMES={'monday':0,'mon':0,'tuesday':1,'tue':1,'wednesday':2,'wed':2,'thursday':3,'thu':3,'friday':4,'fri':4,'saturday':5,'sat':5,'sunday':6,'sun':6,'שני':0,'שלישי':1,'רביעי':2,'חמישי':3,'שישי':4,'שבת':5,'ראשון':6,'יום שני':0,'יום שלישי':1,'יום רביעי':2,'יום חמישי':3,'יום שישי':4,'יום ראשון':6}
FRI_SAT='IL','SA','KW','QA','BH','OM','JO','EG'
DEFAULT_WEEKEND=5,6
JURIS_NAMES={'IL':('israel','israeli','isr','state of israel','ישראל','ישראלי','הישראלי','ישראלית','הישראלית'),'GB':('united kingdom','uk','gbr','great britain','britain','british','england','english','wales','welsh','england and wales','scotland','scottish','northern ireland','בריטניה','אנגליה','הבריטי','האנגלי','אנגלי','בריטי'),'US':('united states','usa','us','american','new york','delaware','california','texas','florida','illinois','massachusetts','new jersey','washington','ארצות הברית','ארה"ב','ניו יורק','דלאוור','קליפורניה','האמריקאי','אמריקאי'),'DE':('germany','german','deu','גרמניה','הגרמני','גרמני'),'FR':('france','french','fra','צרפת','הצרפתי','צרפתי'),'NL':('netherlands','dutch','nld','holland','הולנד','ההולנדי','הולנדי'),'IE':('ireland','irish','irl','אירלנד','האירי','אירי'),'CY':('cyprus','cypriot','cyp','קפריסין','הקפריסאי','קפריסאי'),'CH':('switzerland','swiss','che','שווייץ','שוויץ','השווייצרי','שווייצרי'),'AE':('united arab emirates','uae','emirati','dubai','abu dhabi','difc','adgm','איחוד האמירויות','דובאי'),'SA':('saudi arabia','saudi','sau','ksa','ערב הסעודית','סעודיה','הסעודי'),'KW':('kuwait','kuwaiti','kwt','כווית'),'QA':('qatar','qatari','qat','קטאר'),'BH':('bahrain','bahraini','bhr','בחריין'),'OM':('oman','omani','omn','עומאן'),'JO':('jordan','jordanian','jor','ירדן','הירדני'),'EG':('egypt','egyptian','egy','מצרים','המצרי'),'IT':('italy','italian','ita','איטליה'),'ES':('spain','spanish','esp','ספרד'),'SG':('singapore','sgp','סינגפור'),'HK':('hong kong','hkg','הונג קונג'),'CA':('canada','canadian','can','קנדה'),'AU':('australia','australian','aus','אוסטרליה')}
_JURIS_KEYS=sorted(((C,A)for(A,B)in JURIS_NAMES.items()for C in B),key=lambda x:-len(x[0]))
T={'he':{'unit':{'days':('יום אחד','%d ימים'),'business_days':('יום עסקים אחד','%d ימי עסקים'),'weeks':('שבוע אחד','%d שבועות'),'months':('חודש אחד','%d חודשים'),'years':('שנה אחת','%d שנים'),'hours':('שעה אחת','%d שעות')},'before':'לפני','after':'אחרי','anchor':{'signing_date':'מועד החתימה','effective_date':'מועד התחילה','end_date':'תום התקופה הראשונה','term_end':'תום התקופה הנוכחית','renewal_date':'מועד החידוש הקרוב'},'obl':'המועד של %s','fixed':'מועד קבוע בהסכם: %s','by':'עד %s = %s','missing':'[להשלים] חסר: %s','calc':'%s %s %s (%s) = %s','clear':'; ספירה שמרנית של ימים שלמים','bd':'; טעון אימות: ימי המנוחה לפי סמכות השיפוט, %s (%s); החגים לא נוכו','bd_def':'; טעון אימות: ימי המנוחה לפי הגדרת "יום עסקים" בהסכם%s (%s)%s; החגים לא נוכו','bd_cal':'; לוח החגים: %s','bd_assumed':'; טעון אימות: סמכות השיפוט אינה ידועה, ולכן הונח שימי המנוחה הם %s; החגים לא נוכו','clause_ref':', סעיף %s','clause_paren':' (סעיף %s)','days':('שני','שלישי','רביעי','חמישי','שישי','שבת','ראשון'),'and':' ו','send_by':'; המסירה נחשבת %s אחרי השליחה%s, ולכן מועד השליחה: %s','cutoff':'; מסירה אחרי השעה %s%s אינה נחשבת לאותו יום','notice_unclear':'; טעון אימות: סעיף ההודעות%s קובע מסירה נחשבת או שעת סגירה שלא חושבו (%s), ולכן ייתכן שיש לשלוח מוקדם יותר','hours':'; טעון אימות: %d שעות עוגלו ל-%d ימים','clamp':'; היום קוצץ לסוף החודש','term':'%s ועוד %s, עד היום שלפניו = %s','term_given':'תום התקופה כתוב בהסכם: %s','renewed':'; התחדש %s, כל פעם ל-%s, עד %s','times':('פעם אחת','%d פעמים'),'expired':'ההסכם הסתיים ב-%s, אחרי מספר החידושים המרבי','no_renewal':'אין חידוש אוטומטי בהסכם','window_closed':'; חלון ההודעה למחזור שמסתיים ב-%s נסגר ב-%s, ולכן מוצג המחזור הבא','recurring':'כל %s, החל מ-%s; המועד הקרוב: %s','recurring_end':'כל %s, החל מ-%s; אין מועד נוסף עד %s','event':'תלוי באירוע: %s','event_off':'%s מ%s','ongoing':'חובה מתמשכת','ongoing_until':'חובה מתמשכת עד %s (%s)','survival':'שורדת את סיום ההסכם: %s אחרי הסיום','survival_if':'; אם ההסכם יסתיים בתום התקופה הנוכחית (%s): עד %s','survival_ind':'שורדת את סיום ההסכם, בלי הגבלת זמן','qualifier':'טעון בדיקה משפטית: המועד אינו קצוב בהסכם (%s)','qual':{'reasonable':'זמן סביר','promptly':'מיד','without_delay':'ללא דיחוי','other':'לשון עמומה'},'il':'ישראל (שישי ושבת)','intl':'שבת וראשון','notice_period':'תקופת ההודעה'},'en':{'unit':{'days':('1 day','%d days'),'business_days':('1 business day','%d business days'),'weeks':('1 week','%d weeks'),'months':('1 month','%d months'),'years':('1 year','%d years'),'hours':('1 hour','%d hours')},'before':'before','after':'after','anchor':{'signing_date':'the signing date','effective_date':'the effective date','end_date':'the end of the initial term','term_end':'the end of the current term','renewal_date':'the next renewal date'},'obl':'the date of %s','fixed':'Fixed date in the agreement: %s','by':'By %s = %s','missing':'[to complete] missing: %s','calc':'%s %s %s (%s) = %s','clear':'; conservative count of clear days','bd':'; needs verification: weekend days per the jurisdiction, %s (%s); holidays not deducted','bd_def':'; needs verification: weekend days per the agreement\'s "Business Day" definition%s (%s)%s; holidays not deducted','bd_cal':'; holiday calendar: %s','bd_assumed':'; needs verification: the jurisdiction is not known, so the weekend was assumed to be %s; holidays not deducted','clause_ref':', clause %s','clause_paren':' (clause %s)','days':('Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'),'and':' and ','send_by':'; notice is deemed received %s after sending%s, so send by: %s','cutoff':'; delivery after %s%s is not deemed received that day','notice_unclear':'; needs verification: the notices clause%s sets deemed receipt or a cut-off time that was not computed (%s), so notice may have to be sent earlier','hours':'; needs verification: %d hours rounded up to %d days','clamp':'; day clamped to the end of the month','term':'%s plus %s, to the day before = %s','term_given':'End of term stated in the agreement: %s','renewed':'; renewed %s, each for %s, to %s','times':('once','%d times'),'expired':'The agreement ended on %s, after the maximum number of renewals','no_renewal':'The agreement has no automatic renewal','window_closed':'; the notice window for the term ending %s closed on %s, so the next term is shown','recurring':'Every %s, starting %s; next: %s','recurring_end':'Every %s, starting %s; no further date until %s','event':'Event driven: %s','event_off':'%s from %s','ongoing':'Continuing obligation','ongoing_until':'Continuing obligation until %s (%s)','survival':'Survives termination: %s after termination','survival_if':'; if the agreement ends at the end of the current term (%s): until %s','survival_ind':'Survives termination, without time limit','qualifier':'Needs legal review: the agreement sets no fixed period (%s)','qual':{'reasonable':'reasonable time','promptly':'promptly','without_delay':'without delay','other':'vague wording'},'il':'Israel (Friday and Saturday)','intl':'Saturday and Sunday','notice_period':'notice period'}}
def _t(lang):return T['en'if str(lang or'').lower().startswith('en')else'he']
def parse(s):
	if not s:return
	if isinstance(s,dt.date):return s
	try:return dt.date.fromisoformat(str(s)[:10])
	except ValueError:return
def fmt(d,lang='he'):
	if d is None:return''
	if str(lang or'').lower().startswith('en'):return'%d %s %d'%(d.day,EN_MONTHS[d.month-1],d.year)
	return'%d.%d.%d'%(d.day,d.month,d.year)
def iso(d):return None if d is None else d.isoformat()
def add_months(d,n):A=d.month-1+n;B,A=d.year+A//12,A%12+1;C=calendar.monthrange(B,A)[1];return dt.date(B,A,min(d.day,C)),d.day>C
def jurisdiction_code(j):
	B=re.sub('\\s+',' ',str(j or'').replace('״','"').strip()).casefold()
	if not B:return
	C=re.fullmatch('([a-z]{2})(-[a-z]{2,3})?',B)
	if C:A=C.group(1).upper();return'GB'if A=='UK'else A
	for(D,A)in _JURIS_KEYS:
		if re.search('(?<![\\w])%s(?![\\w])'%re.escape(D.casefold()),B):return A
def weekend_of(agreement):
	B=agreement or{};E=B.get('business_days')if isinstance(B.get('business_days'),dict)else{};A=[]
	for F in E.get('weekend')or[]:
		C=str(F).strip().casefold()
		if C in DAY_NAMES and DAY_NAMES[C]not in A:A.append(DAY_NAMES[C])
	if A:return tuple(sorted(A)),'defined',None
	D=jurisdiction_code(B.get('jurisdiction'))
	if D:return(4,5)if D in FRI_SAT else DEFAULT_WEEKEND,'jurisdiction',D
	return DEFAULT_WEEKEND,'assumed',None
def weekend_days(jurisdiction):return weekend_of({'jurisdiction':jurisdiction})[0]
def shift(d,n,unit,sign,weekend=(5,6)):
	B=sign;A=unit
	if A=='days':return d+dt.timedelta(days=B*n),False,0
	if A=='weeks':return d+dt.timedelta(days=B*7*n),False,0
	if A=='months':C,D=add_months(d,B*n);return C,D,0
	if A=='years':C,D=add_months(d,B*12*n);return C,D,0
	if A=='hours':F=-(-n//24);return d+dt.timedelta(days=B*F),False,F
	if A=='business_days':
		E,G=d,n
		while G>0:
			E+=dt.timedelta(days=B)
			if E.weekday()not in weekend:G-=1
		return E,False,0
	raise ValueError('unit %r'%A)
def span(off,lang):A=off;B=_t(lang);C,D=B['unit'][A['unit']];return C if int(A['n'])==1 else D%int(A['n'])
class Ctx:
	def __init__(A,agreement,as_of,lang='he',obligations=None):B=lang;A.a=agreement or{};A.d=A.a.get('dates')or{};A.as_of=parse(as_of)or dt.date.today();A.lang=B;A.t=_t(B);A.weekend,A.weekend_src,A.juris=weekend_of(A.a);C=A.a.get('notice_delivery');A.nd=C if isinstance(C,dict)and C else None;A.obls={A.get('id'):A for A in obligations or[]};A.fmt=lambda d:fmt(d,B);A.done={};A.term=A._term()
	def _term(A):
		C,D=A.t,A.d;B={'end_date':None,'term_end':None,'calc':'','renewals':0,'expired':False,'clamp':False,'missing':C['anchor']['end_date']};H=parse(D.get('effective_date'))
		if not H and not D.get('end_date')and D.get('initial_term'):B['missing']=C['anchor']['effective_date']
		E=parse(D.get('end_date'))
		if E:B['calc']=C['term_given']%A.fmt(E)
		elif H and D.get('initial_term'):J=D['initial_term'];N,O,L=shift(H,int(J['n']),J['unit'],1,A.weekend);E=N-dt.timedelta(days=1);B['clamp']=O;B['calc']=C['term']%(A.fmt(H),span(J,A.lang),A.fmt(E))
		if not E:return B
		B['end_date']=E;F=E;I=D.get('auto_renewal')
		if I and I.get('period'):
			K,M,G=I['period'],I.get('max_renewals'),0
			while F<A.as_of and(M is None or G<int(M)):P,L,L=shift(F+dt.timedelta(days=1),int(K['n']),K['unit'],1,A.weekend);F,G=P-dt.timedelta(days=1),G+1
			B['renewals']=G
			if G:Q=C['times'][0]if G==1 else C['times'][1]%G;B['calc']+=C['renewed']%(Q,span(K,A.lang),A.fmt(F))
			if F<A.as_of:B['expired']=True
		elif F<A.as_of:B['expired']=True
		B['term_end']=F;return B
	def renewal_notice(A):
		B,D=A.t,A.d.get('auto_renewal')
		if not D or not D.get('period'):return None,B['no_renewal'],'computed'
		if not D.get('notice'):return None,B['missing']%B['notice_period'],'to_complete'
		C=A.term['term_end']
		if C is None:return None,B['missing']%A.term['missing'],'to_complete'
		if A.term['expired']:return None,B['expired']%A.fmt(C),'computed'
		F=D['notice'];M=D.get('by')in(None,'either','us','both')
		def G(end):D,H,G=A._before(end,F);C=B['calc']%(span(F,A.lang),B['before'],B['anchor']['term_end'],A.fmt(end),A.fmt(D));C,E=A._notes(C,F,G,False,'computed');return A.send_by(D,C,E)if M else(D,C,E)
		H='';E,I,J=G(C)
		if E<A.as_of:
			K=D.get('max_renewals')
			if K is not None and A.term['renewals']>=int(K):return None,B['expired']%A.fmt(C),'computed'
			L=D['period'];N,O,O=shift(C+dt.timedelta(days=1),int(L['n']),L['unit'],1,A.weekend);H=B['window_closed']%(A.fmt(C),A.fmt(E));C=N-dt.timedelta(days=1);E,I,J=G(C)
		return E,I+H,J
	def send_by(E,d,calc,status):
		D=calc;C=status;A,F=E.nd,E.t
		if not A or d is None:return d,D,C
		H=F['clause_ref']%A['clause']if A.get('clause')else'';B=A.get('deemed_after');I=isinstance(B,dict)and B.get('unit')in UNITS and str(B.get('n','')).isdigit()
		if I and int(B['n'])>0:G,J,K=shift(d,int(B['n']),B['unit'],-1,E.weekend);D+=F['send_by']%(span(B,E.lang),H,E.fmt(G));D,C=E._notes(D,B,K,J,C);d=G
		elif B or A.get('text')and not A.get('cutoff_time'):L=F['clause_paren']%A['clause']if A.get('clause')else'';D+=F['notice_unclear']%(L,A.get('text')or str(B));return d,D,'needs_verification'if C=='computed'else C
		if A.get('cutoff_time'):
			M=' (%s)'%A['tz']if A.get('tz')else'';D+=F['cutoff']%(A['cutoff_time'],M)
			if not A.get('tz'):C='needs_verification'if C=='computed'else C
		return d,D,C
	def _before(C,d,off):
		A=off;B,D,E=shift(d,int(A['n']),A['unit'],-1,C.weekend)
		if A.get('clear_days'):B-=dt.timedelta(days=1)
		return B,D,E
	def _notes(E,calc,off,hd,clamp,status):
		C=off;B=status;A=calc;D=E.t
		if C.get('clear_days'):A+=D['clear']
		if C['unit']=='business_days':A+=E._bd_note();B='needs_verification'
		if hd:A+=D['hours']%(int(C['n']),hd);B='needs_verification'
		if clamp:A+=D['clamp'];B='needs_verification'
		return A,B
	def _days(C):B=C.t;A=[B['days'][A]for A in C.weekend];return B['and'].join(A)if len(A)<3 else', '.join(A[:-1])+B['and']+A[-1]
	def _bd_note(A):
		B=A.t
		if A.weekend_src=='defined':C=A.a.get('business_days')or{};D=B['clause_ref']%C['clause']if C.get('clause')else'';E=B['bd_cal']%', '.join(str(A)for A in C['calendars'])if C.get('calendars')else'';return B['bd_def']%(D,A._days(),E)
		if A.weekend_src=='jurisdiction':return B['bd']%(A.juris,A._days())
		return B['bd_assumed']%A._days()
	def anchor(B,name):
		A=name;C=B.t
		if isinstance(A,str)and parse(A):return parse(A),B.fmt(parse(A))
		if A in('signing_date','effective_date'):return parse(B.d.get(A)),C['anchor'][A]
		if A=='end_date':return B.term['end_date'],C['anchor'][A]if B.term['end_date']else B.term['missing']
		if A=='term_end':return B.term['term_end'],C['anchor'][A]if B.term['term_end']else B.term['missing']
		if A=='renewal_date':G=B.term['term_end'];return G+dt.timedelta(days=1)if G else None,C['anchor'][A]
		if isinstance(A,str)and A.startswith('custom:'):
			E=A[7:];D=(B.d.get('anchors')or{}).get(E)
			if isinstance(D,dict):return parse(D.get('date')),D.get('label')or E
			return parse(D),E
		if isinstance(A,str)and A.startswith('obl:'):
			H=A[4:];F=B.obls.get(H);I=C['obl']%((F or{}).get('title')or H)
			if F is None:return None,I
			J=B.compute(F);return parse(J['due_date']),I
		return None,str(A)
	def compute(B,o):
		C=o.get('id')
		if C in B.done:return B.done[C]
		B.done[C]={'due_date':None,'calc':'','date_status':'to_complete'};A=B._compute(o.get('timing')or{});E=(o.get('timing')or{}).get('kind')
		if o.get('type')in('notice','renewal_notice')and o.get('obligor')in('us','both')and E in('fixed','relative')and A.get('due_date'):F,G,H=B.send_by(parse(A['due_date']),A['calc'],A['date_status']);A=dict(A,due_date=iso(F),calc=G,date_status=H)
		D=(o.get('timing')or{}).get('qualifier')
		if D:A['calc']=B.t['qualifier']%B.t['qual'].get(D,D)+('; '+A['calc']if A['calc']else'');A['date_status']='needs_legal_review'
		B.done[C]=A;return A
	def _compute(A,tm):
		F=tm;B,H=A.t,F.get('kind');C=lambda d,c,s,**A:dict({'due_date':iso(d),'calc':c,'date_status':s},**A)
		if H=='fixed':G=parse(F.get('date'));return C(G,B['fixed']%A.fmt(G),'computed')if G else C(None,B['missing']%'date','to_complete')
		if H=='relative':
			I,L=A.anchor(F.get('anchor'))
			if I is None:return C(None,B['missing']%L,'to_complete')
			D=F.get('offset')or{'n':0,'unit':'days','direction':'after'}
			if D.get('direction')=='before':G,N,O=A._before(I,D)
			else:G,N,O=shift(I,int(D['n']),D['unit'],1,A.weekend)
			if int(D['n'])==0:E=B['by']%(L,A.fmt(G))
			else:E=B['calc']%(span(D,A.lang),B[D.get('direction','after')],L,A.fmt(I),A.fmt(G))
			E,J=A._notes(E,D,O,N,'computed');return C(G,E,J)
		if H=='renewal_notice':G,E,J=A.renewal_notice();return C(G,E,J)
		if H=='term_end':
			K=A.term['term_end']
			if K is None:return C(None,B['missing']%A.term['missing'],'to_complete')
			J='needs_verification'if A.term['clamp']else'computed';return C(K,A.term['calc'],J)
		if H=='recurring':P,E,J=A.occurrences(F,A.as_of,None,first_only=True);return C(P[0]if P else None,E,J)
		if H=='event':D=F.get('offset');Q=F.get('event')or'';R=B['event_off']%(span(D,A.lang),Q)if D else Q;return C(None,B['event']%R,'event_driven')
		if H=='ongoing':
			if F.get('until'):
				I,L=A.anchor(F['until'])
				if I:return C(I,B['ongoing_until']%(A.fmt(I),L),'ongoing')
			return C(None,B['ongoing'],'ongoing')
		if H=='survival':
			M=F.get('period')
			if M in(None,'indefinite'):return C(None,B['survival_ind'],'ongoing')
			E=B['survival']%span(M,A.lang);K=A.term['term_end']
			if K:S,T,T=shift(K,int(M['n']),M['unit'],1,A.weekend);E+=B['survival_if']%(A.fmt(K),A.fmt(S))
			return C(None,E,'ongoing')
		return C(None,B['missing']%'timing','to_complete')
	def occurrences(A,tm,frm,to,first_only=False):
		D=tm;K=A.t;C=D.get('every')or{};B,S=A.anchor(D.get('start'))
		if B is None or not C.get('n'):return[],K['missing']%S,'to_complete'
		L='computed';F=M=False
		if D.get('start_offset'):
			E=D['start_offset']
			if E.get('direction')=='before':B,F,M=A._before(B,E)
			else:B,F,M=shift(B,int(E['n']),E['unit'],1,A.weekend)
		G=None
		if D.get('until'):G,O=A.anchor(D['until'])
		elif A.term['term_end']:G=A.term['term_end']
		P=to or frm+dt.timedelta(days=3660);I,N=[],0
		while N<2000:
			Q=int(C['n'])*N
			if C['unit']in('months','years'):H,T=add_months(B,Q*(12 if C['unit']=='years'else 1));F=F or T
			else:H,O,O=shift(B,Q,C['unit'],1,A.weekend)
			N+=1
			if G and H>G or H>P:break
			if H>=frm:
				I.append(H)
				if first_only:break
		R=span(C,A.lang)
		if I:J=K['recurring']%(R,A.fmt(B),A.fmt(I[0]))
		else:J=K['recurring_end']%(R,A.fmt(B),A.fmt(G or P))
		E=dict(C,n=C['n']);J,L=A._notes(J,E,M,F,L);return I,J,L
def compute_all(agreement,obligations,as_of=None,lang='he'):B=obligations;A=Ctx(agreement,as_of,lang,B);D={B.get('id'):A.compute(B)for B in B};C={'end_date':iso(A.term['end_date']),'term_end':iso(A.term['term_end']),'renewals':A.term['renewals'],'expired':A.term['expired'],'calc':A.term['calc']};E,F,G=A.renewal_notice();C['renewal_notice']={'date':iso(E),'calc':F,'date_status':G};return D,C
