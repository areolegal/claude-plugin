#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,hashlib,json,os,re,sys,zipfile
from pathlib import Path
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from xml.etree import ElementTree as ET
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
_LIB=Path(__file__).resolve().parents[3]/'lib'
if _LIB.is_dir()and str(_LIB)not in sys.path:sys.path.insert(0,str(_LIB))
try:from common.cli import OutputRefused,guard_out,load_docx_or_explain
except ImportError:
	class OutputRefused(Exception):0
	def guard_out(out,inputs=()):
		A=out;B=os.path.normcase(os.path.realpath(A))
		if any(A and os.path.normcase(os.path.realpath(A))==B for A in inputs):raise OutputRefused('--out is an input file: %s'%A)
		if os.path.isfile(B)and B.lower().endswith(('.docx','.doc','.pdf')):raise OutputRefused('--out is an existing document: %s'%A)
		return os.path.abspath(A)
	def load_docx_or_explain(path,loader=None,strict_ok=False):
		A=path
		try:
			with zipfile.ZipFile(A)as C:C.getinfo('word/document.xml')
			return A,None,0
		except Exception as B:return None,'לא ניתן לקרוא את %s כמסמך Word (%s).\n%s cannot be read as a Word document (%s).'%(os.path.basename(A),type(B).__name__,os.path.basename(A),type(B).__name__),2
HEB=re.compile('[\\u0590-\\u05ff]')
LAT=re.compile('[A-Za-z]')
W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
try:from build_translation_docx import sniff,seg_hash,collect
except ImportError:sniff=seg_hash=collect=None
CUR_WORDS={'₪':'ILS','nis':'ILS','ש"ח':'ILS','ש״ח':'ILS','שח':'ILS','שקל':'ILS','שקלים':'ILS','שקלים חדשים':'ILS','new israeli shekels':'ILS','shekels':'ILS','shekel':'ILS','$':'USD','us$':'USD','dollar':'USD','dollars':'USD','us dollars':'USD','דולר':'USD','דולרים':'USD','דולר ארה"ב':'USD','דולר ארה״ב':'USD','דולר אמריקאי':'USD','€':'EUR','euro':'EUR','euros':'EUR','אירו':'EUR','יורו':'EUR','£':'GBP','pound':'GBP','pounds':'GBP','pounds sterling':'GBP','sterling':'GBP','ליש"ט':'GBP','ליש״ט':'GBP','לירות שטרלינג':'GBP','לירה שטרלינג':'GBP','swiss francs':'CHF','swiss franc':'CHF','francs':'CHF','franc':'CHF','fr.':'CHF','פרנק':'CHF','פרנקים':'CHF','פרנק שווייצרי':'CHF','פרנקים שווייצריים':'CHF','פרנק שוויצרי':'CHF','¥':'JPY','yen':'JPY','ין':'JPY','ין יפני':'JPY','yuan':'CNY','renminbi':'CNY','יואן':'CNY','₹':'INR','rupees':'INR','rupee':'INR','רופי':'INR','₩':'KRW','won':'KRW','₽':'RUB','roubles':'RUB','rubles':'RUB','רובל':'RUB','₺':'TRY','turkish lira':'TRY','לירה טורקית':'TRY','c$':'CAD','canadian dollars':'CAD','canadian dollar':'CAD','דולר קנדי':'CAD','a$':'AUD','australian dollars':'AUD','australian dollar':'AUD','דולר אוסטרלי':'AUD','hk$':'HKD','hong kong dollars':'HKD','s$':'SGD','singapore dollars':'SGD','nz$':'NZD','swedish kronor':'SEK','swedish krona':'SEK','כתר שוודי':'SEK','norwegian kroner':'NOK','כתר נורווגי':'NOK','danish kroner':'DKK','כתר דני':'DKK','zloty':'PLN','złoty':'PLN','זלוטי':'PLN','forint':'HUF','koruna':'CZK','rand':'ZAR','dirham':'AED','dirhams':'AED','דירהם':'AED','real':'BRL','reais':'BRL','pesos':'MXN','peso':'MXN'}
ISO_4217='ILS','USD','EUR','GBP','CHF','JPY','CNY','INR','KRW','RUB','TRY','CAD','AUD','HKD','SGD','NZD','SEK','NOK','DKK','PLN','HUF','CZK','RON','BGN','ZAR','AED','SAR','QAR','KWD','BHD','OMR','JOD','EGP','MAD','BRL','MXN','ARS','CLP','COP','PEN','THB','MYR','IDR','PHP','VND','TWD','UAH','KZT','ISK','NGN','KES','XAU','XAG'
_CW='|'.join(sorted((re.escape(A)for A in CUR_WORDS),key=len,reverse=True))
_ISO='|'.join(ISO_4217)
_AMT='\\d[\\d,.]*\\d|\\d'
_CUR='(?-i:%s)(?![A-Za-z])|%s'%(_ISO,_CW)
CUR_AFTER=re.compile('(%s)\\s?(%s)(?![\\w\u0590-\u05ff])'%(_AMT,_CUR),re.I)
CUR_BEFORE=re.compile('(?<![\\w\u0590-\u05ff])(%s)\\s?(%s)'%(_CUR,_AMT),re.I)
PCT_WORDS=re.compile('(\\d+(?:[.,]\\d+)?)\\s?(?:%|אחוזים|אחוז|percent|per cent|pct\\.?)(?![\\w\u0590-\u05ff])',re.I)
_GROUPED=re.compile('^\\d{1,3}(?P<g>[.,\xa0\u202f ])\\d{3}(?:(?P=g)\\d{3})*(?:(?P<d>[.,])\\d+)?$')
def norm_num(v):
	A=v.strip();B=_GROUPED.match(A)
	if B and(B.group('d')is None or B.group('d')!=B.group('g')):
		C=B.group('g')
		if C=='.'and B.group('d')is None and A.count('.')==1:return A
		E,D=(A.rsplit(B.group('d'),1)+[''])[:2]if B.group('d')else(A,'');return E.replace(C,'')+('.'+D if D else'')
	if re.match('^\\d+,\\d{1,2}$',A)or re.match('^\\d+,\\d{4,}$',A):return A.replace(',','.')
	return A
def _cur_code(tok):A=tok;return A.upper()if A.upper()in ISO_4217 and A.isupper()else CUR_WORDS.get(A.lower())
STAMP_STYLE='areostamp'
def text_of(path,skipped=None):
	B=skipped;A=Path(path);from build_translation_docx import sniff,pdf_paragraphs as I;C=sniff(str(A))
	if C=='pdf':
		J,D=I(str(A))
		if D:raise SystemExit('%s: %s'%(A.name,D))
		return'\n'.join(J)
	if C=='docx':
		with zipfile.ZipFile(A)as K:L=K.read('word/document.xml')
		M=ET.fromstring(L);E=[]
		for F in M.iter(W+'p'):
			G=''.join(A.text or''for A in F.iter(W+'t'));H=F.find(W+'pPr/'+W+'pStyle')
			if H is not None and(H.get(W+'val')or'').lower()==STAMP_STYLE:
				if B is not None:B.append(G)
				continue
			E.append(G)
		return'\n'.join(E)
	return A.read_text(encoding='utf-8')
STAMP_LINE=re.compile('^\\s*(?:produced on|last updated|translation for reference|draft\\b|הופק בתאריך|עדכון אחרון|תרגום לעיון|טיוטה\\b)',re.I)
def hf_paragraphs(path):
	A=[];from build_translation_docx import sniff
	if sniff(str(path))!='docx':return A
	with zipfile.ZipFile(path)as E:
		for B in sorted(E.namelist()):
			if not re.match('^word/(header|footer)\\d*\\.xml$',B):continue
			G=ET.fromstring(E.read(B))
			for C in G.iter(W+'p'):
				D=''.join(A.text or''for A in C.iter(W+'t')).strip();F=C.find(W+'pPr/'+W+'pStyle')
				if not D or F is not None and(F.get(W+'val')or'').lower()==STAMP_STYLE or STAMP_LINE.match(D):continue
				A.append((B,D,C.find(W+'pPr/'+W+'bidi')is not None))
	return A
HEB_YEAR=re.compile('^57\\d\\d$')
def currencies(text):
	C=[]
	for A in CUR_AFTER.finditer(text):
		B=_cur_code(A.group(2))
		if B:C.append((A.start(),A.end(),'%s %s'%(B,norm_num(A.group(1)))))
	for A in CUR_BEFORE.finditer(text):
		B=_cur_code(A.group(1))
		if B and not any(B<A.end()and A.start()<C for(B,C,D)in C):C.append((A.start(),A.end(),'%s %s'%(B,norm_num(A.group(2)))))
	return[B for(A,A,B)in sorted(C)]
MONTHS={B:A+1 for(A,B)in enumerate(['january','february','march','april','may','june','july','august','september','october','november','december'])}
MONTHS.update({B:A+1 for(A,B)in enumerate(['ינואר','פברואר','מרץ','אפריל','מאי','יוני','יולי','אוגוסט','ספטמבר','אוקטובר','נובמבר','דצמבר'])})
_MON='|'.join(sorted(MONTHS,key=len,reverse=True))
DATE_WORDS=re.compile('(?<!\\d)(\\d{1,2})(?:st|nd|rd|th)?\\s+(?:of\\s+|ב)?(%s),?\\s+(\\d{4})|(%s)\\s+(\\d{1,2}),\\s+(\\d{4})'%(_MON,_MON),re.I)
DATE_NUM=re.compile('(?<![\\d.])(\\d{1,2})[./](\\d{1,2})[./](\\d{4})(?!\\d)(?!\\.\\d)')
DATE_ISO=re.compile('(?<!\\d)(\\d{4})-(\\d{2})-(\\d{2})(?!\\d)')
def norm_dates(text):
	A=text
	def B(m):
		if m.group(1):A,B,C=m.group(1),MONTHS[m.group(2).lower()],m.group(3)
		else:B,A,C=MONTHS[m.group(4).lower()],m.group(5),m.group(6)
		return' %s-%02d-%02d '%(C,B,int(A))
	A=DATE_WORDS.sub(B,A);A=DATE_NUM.sub(lambda m:' %s-%02d-%02d '%(m.group(3),int(m.group(2)),int(m.group(1))),A);return A
def tokens(text):A=text;A=PCT_WORDS.sub(lambda m:m.group(1)+'%',A);A=norm_dates(A);C=DATE_ISO.findall(A);A=DATE_ISO.sub(' ',A);B=[A for A in[norm_num(A[:-1])+'%'if A.endswith('%')else norm_num(A)for A in re.findall('(?<![\\w])(?:\\d{1,4}(?:[.,]\\d+)*%?|\\d{1,2}[./-]\\d{1,2}[./-]\\d{2,4})(?![\\w])',A)]if not HEB_YEAR.match(A)];B=B+['%s-%s-%s'%A for A in C];D=re.findall('(?m)^\\s*(\\d+(?:\\.\\d+){0,4})[.)]?\\s+',A);return{'numeric_tokens':B,'currency_tokens':currencies(A),'section_numbers':D}
def multiset_diff(a,b):from collections import Counter as A;B,C=A(a),A(b);return list((B-C).elements()),list((C-B).elements())
def target_lang(text):A,B=len(HEB.findall(text)),len(LAT.findall(text));return'he'if A and A>=B else'en'
def canonical_name(doc_id,lang):A=re.sub('[^A-Za-z0-9_.-]+','-',doc_id or'').strip('-.')or'document';return'translation-integrity-%s-%s.json'%(A[:60],lang)
def unique(path):
	A=path
	if not os.path.exists(A):return A
	C,D=os.path.splitext(A);B=2
	while os.path.exists('%s (%d)%s'%(C,B,D)):B+=1
	return'%s (%d)%s'%(C,B,D)
REPORT_SCHEMA='areo-translation-integrity/2'
MANIFEST_SCHEMA='areo-translation-manifest/1'
_HB='\u0590-\u05ff'
_L='(?<![A-Za-z0-9_%s])'%_HB
_R='(?![A-Za-z0-9_%s])'%_HB
MECHANICAL_CHECKS=['manifest_matches_source_hash','every_segment_has_one_target_or_reason','missing_or_duplicate_segment','source_changed_segment','footnotes_comments_tables_headings_annexes_covered','untranslated_copy_detected','built_file_matches_manifest','fields_bookmarks_references_attached','numbers_currencies_dates_per_segment','glossary_terms_per_segment','modality_shall_may_per_segment','negation_per_segment','exception_per_segment','deadline_per_segment','amount_and_party_attachment_per_obligation','cross_references_per_segment']
JUDGEMENT_CHECKS=['whether_the_target_wording_really_carries_the_same_obligation','obligations_without_an_explicit_marker','trigger_and_condition_equivalence','remedy_and_liability_scope','defined_term_use_in_context','non_equivalent_concepts','scanned_text_read_against_the_image','emphasis_that_carries_meaning']
NEVER_CLAIMED='This report compares two texts mechanically and lists what still needs a human read. It does not assess legal validity or legal equivalence.\nהדוח משווה שני טקסטים באופן ממוכן ומפרט מה עדיין טעון קריאה אנושית. הוא אינו קובע תוקף משפטי או שקילות משפטית.'
def _rx(alts,pre=''):return re.compile(_L+pre+'(?:'+'|'.join(alts)+')'+_R,re.I)
_H=lambda w:w+'(?:ת|ים|ות|ם|ן)?'
RULES=[('exc',_rx(['except(?:ing)?(?: that| for)?','unless','save(?: for| that)','other than','excluding','exclusive of','apart from','with the exception of','but for','barring','למעט','אלא\\s+אם(?:\\s+כן)?','פרט\\s+ל\\S*','מלבד'],'ו?')),('prohib',_rx(['(?:shall|must|may|will|can) not','cannot','(?:is|are) not (?:permitted|allowed|entitled|authori[sz]ed) to','(?:is|are) (?:prohibited|forbidden|barred|precluded) from','shall refrain from','(?:agrees|undertakes|covenants) not to','אינ(?:ו|ה|ם|ן)\\s+רשאי(?:ת|ם|ן|ות)?','לא\\s+(?:יהיה|יהיו|תהיה|תהיינה)\\s+רשאי(?:ת|ם|ן|ות)?','אסור(?:ה|ים|ות)?','מנוע(?:ה|ים|ות)?','מתחייב(?:ת|ים|ות)?\\s+שלא','(?:יימנע|תימנע|יימנעו|תימנעו)','לא\\s+(?:יוכל|תוכל|יוכלו)'],'ו?')),('perm',_rx(['(?:shall|will) (?:be entitled|have the right|be permitted|be free|be authori[sz]ed) to','(?:is|are) (?:entitled|permitted|allowed|authori[sz]ed|free) to','(?:has|have) the (?:right|option|discretion) to','(?:at|in) (?:its|his|her|their|the) (?:sole |absolute |own |reasonable )*discretion','רשאי(?:ת|ם|ן|ות)?','זכאי(?:ת|ם|ן|ות)?','מותר','בשיקול\\s+דעת(?:ו|ה|ם|ן)(?:\\s+ה(?:בלעדי|מוחלט))?','(?:הזכות|זכות)\\s+ל','יוכל|תוכל|יוכלו'],'ו?')),('duty',_rx(['shall','must','(?:is|are) (?:required|obliged|obligated|bound) to','(?:undertakes?|agrees?|covenants?|commits?) to','will','(?:has|have|needs?) to','מתחייב(?:ת|ים|ות)?','חייב(?:ת|ים|ות)?','מחויב(?:ת|ים|ות)?','נדרש(?:ת|ים|ות)?','יידרש(?:ו)?','על(?:יו|יה|יהם|יהן)\\s+ל(?=[א-ת])','על\\s+ה(?!ידי)[א-ת]+\\s+ל(?=[א-ת])'],'ו?')),('perm',_rx(['may','can'])),('neg',_rx(['not','no(?!\\.\\s*\\d)','never','neither','nor','none','nothing','nobody','without',"[A-Za-z]+n\\'t",'לא','אין','אינ(?:ו|ה|ם|ן)','איננ(?:ו|ה)','ללא','בלי','מבלי','שלא','לעולם\\s+לא'],'ו?')),('cond',_rx(['if','upon','in the event(?: that| of)?','where','when','whenever','once','provided(?:,? however,?)? that','subject to','prior to','following','after','before','as of','from the date','in case(?: of)?','אם','ככל\\s+ש','במקרה\\s+(?:ש|של)','כאשר','בעת','לאחר','לפני','בכפוף\\s+ל','בהתקיים','ובלבד\\s+ש','בתנאי\\s+ש','מרגע','מיום','עם\\s+(?:קרות|קבלת|התקיימות)','בהינתן'],'ו?'))]
REMEDIES={'indemnity':'indemnif|hold harmless|שיפוי|ישפה|תשפה|לשפות|ישפו','liability':'liab|אחראי|אחריות|אחראית|אחראים','damages':'damages|compensat|פיצוי|יפצה|לפצות|נזק|נזקים','termination':'terminat|rescind|ביטול|יבטל|לבטל|מבטל|הפסקת ההסכם|יסיים|לסיים','cure':'\\bcure\\b|rectif|לתקן|יתקן|תיקון ההפרה','penalty':'penalt|liquidated damages|late fee|interest on|קנס|פיצוי מוסכם|ריבית','refund':'refund|reimburs|credit note|החזר|יחזיר|השבה|זיכוי','injunction':'injunct|specific performance|צו מניעה|אכיפה|סעד','limitation':'limit(?:ed|ation) (?:of|to)|\\bcap(?:ped)?\\b|shall not exceed|aggregate liability|מוגבל|הגבלת|תקרה|לא יעלה על','uncapped':'unlimited|without limit|uncapped|ללא הגבלה|בלתי מוגבל'}
ACTIONS={'pay':'\\bpay|payment|שיל[םמ]|תשלום|ישלם|לשלם|תשלם|ישלמו','deliver':'deliver|supply|provide|יספק|לספק|אספקה|ימסור|למסור|מסירה','notify':'notify|notice|inform|יודיע|להודיע|הודעה|ימסור הודעה','return':'\\breturn|\\brestore|יחזיר|להחזיר','confidential':'confidential|keep secret|סודיות|בסוד|יסוד','comply':'comply|compliance|יעמוד ב|לעמוד ב|יקיים|לקיים|ציות','repair':'\\brepair|replace|fix|יתקן|לתקן|יחליף|להחליף','insure':'insur|ביטוח|יבטח|לבטח','assign':'\\bassign|transfer|delegate|המחאה|להמחות|יעביר|להעביר','report':'\\breport|account for|דיווח|ידווח|לדווח','maintain':'maintain|preserve|keep|ישמור|לשמור|יתחזק'}
NUMWORDS={'one':1,'two':2,'three':3,'four':4,'five':5,'six':6,'seven':7,'eight':8,'nine':9,'ten':10,'eleven':11,'twelve':12,'fifteen':15,'twenty':20,'thirty':30,'forty':40,'fifty':50,'sixty':60,'ninety':90,'hundred':100,'אחד':1,'שניים':2,'שני':2,'שלושה':3,'ארבעה':4,'חמישה':5,'שישה':6,'שבעה':7,'שמונה':8,'תשעה':9,'עשרה':10,'חמישה עשר':15,'עשרים':20,'שלושים':30,'ארבעים':40,'חמישים':50,'שישים':60,'תשעים':90,'מאה':100}
_NW='|'.join(sorted((re.escape(A)for A in NUMWORDS),key=len,reverse=True))
UNITS={'day':'day','days':'day','week':'week','weeks':'week','month':'month','months':'month','year':'year','years':'year','hour':'hour','hours':'hour','יום':'day','ימים':'day','שבוע':'week','שבועות':'week','חודש':'month','חודשים':'month','שנה':'year','שנים':'year','שעה':'hour','שעות':'hour','ימי עסקים':'day','ימי עבודה':'day','ימי בנקאות':'day'}
_UN='|'.join(sorted((re.escape(A)for A in UNITS),key=len,reverse=True))
DURATION=re.compile(_L+'(?P<n>\\d+|%s)(?:\\s*\\((?P<n2>\\d+)\\))?\\s+(?P<dt>business |working |banking |calendar )?(?P<u>%s)'%(_NW,_UN)+_R,re.I)
PLACEHOLDER=re.compile('\\[(?:להשלים|to complete|TBC)[^\\]]*\\]|\\[●\\]|\\[\\s*\\]',re.I)
DEFMARK=re.compile('\\((?:להלן|hereinafter|hereafter|the|each|together)?:?\\s*[\\"“”״\\\']+[^\\"“”״\\\']{2,40}[\\"“”״\\\']+\\s*\\)',re.I)
REFWORD='(?:sections?|clauses?|articles?|paragraphs?|schedules?|annex(?:es|ure)?|appendix|appendices|exhibits?|סעיפים|סעיף|פרק|נספח|תוספת|לוח|סעיף קטן)'
XREF=re.compile(_L+'[ובלכמש]{0,2}'+REFWORD+'(?!\\s+(?:מע["״\\\']?מ|מס\\b|מיסים|מסים))'+"\\s+((?:[A-Za-z]|[א-ת]\\'?|\\d)[\\w.()א-ת\\'’״-]*)",re.I)
HE2LAT=dict(zip('אבגדהוזחטיכלמנסעפצקרשת','abcdefghijklmnopqrstuv'))
HE2LAT.update({'ך':'k','ם':'m','ן':'n','ף':'q','ץ':'r'})
PASSIVE_BY=re.compile('(?:\\bby\\s+(?:the\\s+)?|על[\\s-]ידי\\s+|בידי\\s+)$',re.I)
def _norm_ref(r):r=re.sub('[\\\'’״"]','',r).rstrip('.,;:)');r=re.sub('[א-ת]',lambda m:HE2LAT.get(m.group(0),m.group(0)),r);return r.lower()
def refs_of(text):return[_norm_ref(A.group(1))for A in XREF.finditer(text)if _norm_ref(A.group(1))]
def _words_to_n(tok):A=tok;return str(NUMWORDS.get(A.lower(),A))if not A.isdigit()else A
def durations(text):
	C=[]
	for A in DURATION.finditer(text):D=A.group('n2')or _words_to_n(A.group('n'));B=A.group('u').lower();E=(A.group('dt')or'').strip().lower()in('business','working','banking')or B in('ימי עסקים','ימי עבודה','ימי בנקאות');C.append((A.start(),A.end(),'D %s %s%s'%(D,UNITS.get(B,B),' business'if E else'')))
	return C
def quants(text):
	D=text;B=[]
	for A in CUR_AFTER.finditer(D):
		C=_cur_code(A.group(2))
		if C:B.append((A.start(),A.end(),'%s %s'%(C,norm_num(A.group(1)))))
	for A in CUR_BEFORE.finditer(D):
		C=_cur_code(A.group(1))
		if C and not any(B<A.end()and A.start()<C for(B,C,D)in B):B.append((A.start(),A.end(),'%s %s'%(C,norm_num(A.group(2)))))
	for A in PCT_WORDS.finditer(D):B.append((A.start(),A.end(),A.group(1)+'%'))
	for(E,F,G)in durations(D):
		if not any(A<F and E<B for(A,B,C)in B):B.append((E,F,G))
	return sorted(B)
def _scan(text):
	A,B=text,[]
	for(E,C)in RULES:
		for D in C.finditer(A):B.append((E,D.start(),D.end()))
		A=C.sub(lambda m:' '*len(m.group(0)),A)
	return sorted(B,key=lambda x:x[1])
def _cats(table,text):return sorted(A for(A,B)in table.items()if re.search(B,text,re.I))
GENERIC_PARTIES=[{'id':'other_party','en':['the other party','the counterparty'],'he':['הצד השני','הצד האחר','הצד שכנגד']},{'id':'all_parties','en':['each party','either party','both parties','each of the parties'],'he':['כל צד','שני הצדדים','כל אחד מהצדדים']},{'id':'party_a','en':['party a','the first party'],'he':['צד א',"צד א'",'הצד הראשון']},{'id':'party_b','en':['party b','the second party'],'he':['צד ב',"צד ב'",'הצד השני']}]
_term_cache={}
def _term_rx(term):
	B=term
	if B in _term_cache:return _term_cache[B]
	A=re.sub('\\s+',' ',B.strip())
	if re.search('[\u0590-\u05ff]',A):D=A[1:]if len(A)>3 and A.startswith('ה')else A;C=re.compile('(?<![A-Za-z0-9_%s])[ושבלכמ]{0,2}ה?%s(?:ים|ות|ו|ה|ם|ן|י)?%s'%(_HB,re.escape(D).replace('\\ ','\\s+'),_R))
	else:C=re.compile(_L+"(?:the\\s+)?%s(?:'s|s)?"%re.escape(A).replace('\\ ','\\s+')+_R,re.I)
	_term_cache[B]=C;return C
def find_parties(text,pmap):
	A=[]
	for D in pmap:
		for H in('he','en'):
			for I in D.get(H,[]):
				for E in _term_rx(I).finditer(text):A.append((E.start(),E.end(),D['id']))
	A.sort(key=lambda x:(-(x[1]-x[0]),x[0]));F,G=[],[]
	for(B,C,J)in A:
		if not any(B<D and A<C for(A,D)in F):F.append((B,C));G.append((B,C,J))
	return sorted(G)
def _lang_of_term(t):return'he'if re.search('[\u0590-\u05ff]',t)else'en'
def load_party_map(glossary_entries,extra):
	B=[dict(A)for A in GENERIC_PARTIES]
	for A in list(glossary_entries)+list(extra or[]):
		if A.get('role')=='party'or A.get('party'):B.append({'id':A.get('id')or(A.get('en')or A.get('he')or['?'])[0],'he':A.get('he',[]),'en':A.get('en',[])})
	return B
def load_glossary(path):
	A=json.loads(Path(path).read_text(encoding='utf-8-sig'));I='';E=A
	if isinstance(A,dict):
		I=str(A.get('glossary_version')or A.get('version')or A.get('id')or'');E=A.get('terms')or A.get('entries')or A.get('glossary')
		if E is None:E=[{'source':B,'target':A}for(B,A)in A.items()if isinstance(A,(str,list))]
	J=[];K='source','target','src','tgt','he','en','hebrew','english','term','translation','term_he','term_en','source_term','target_term','approved_translation'
	for(L,B)in enumerate(E or[]):
		if not isinstance(B,dict):continue
		D={'id':str(B.get('id')or B.get('term_id')or L),'he':[],'en':[],'status':str(B.get('status')or'approved').lower(),'role':B.get('role')or('party'if B.get('party')else'')}
		for G in K:
			C=B.get(G)
			for F in[C]if isinstance(C,str)else C if isinstance(C,list)else[]:
				for H in re.split('\\s*[;|]\\s*',str(F)):
					if H.strip():D[_lang_of_term(H)].append(H.strip())
		for G in('alternates','variants','allowed'):
			C=B.get(G)
			for F in C if isinstance(C,list)else[]:D[_lang_of_term(str(F))].append(str(F))
		if D['he']or D['en']:J.append(D)
	return I,J
def glossary_findings(src,tgt,src_lang,tgt_lang,entries):
	D=[]
	for A in entries:
		if A['status']not in('approved','approved_term','מאושר'):continue
		B,C=A.get(src_lang,[]),A.get(tgt_lang,[])
		if not B or not C:continue
		if any(_term_rx(A).search(src)for A in B)and not any(_term_rx(A).search(tgt)for A in C):D.append({'type':'glossary_term_missing','severity':'error','detail':'approved term %r is in the source but none of %r is in the target'%(B[0],C)})
	return D
def level2_pair(src,tgt,src_lang,tgt_lang,entries):
	C=tgt;B=src;A=[];K,L=tokens(B),tokens(C)
	for(D,M)in(('numeric_tokens','number_mismatch'),('currency_tokens','currency_mismatch'),('section_numbers','section_number_mismatch')):
		E,F=multiset_diff(K[D],L[D])
		if E or F:A.append({'type':M,'severity':'error','detail':{'missing_in_target':E,'extra_in_target':F}})
	G,H=len(PLACEHOLDER.findall(B)),len(PLACEHOLDER.findall(C))
	if G!=H:A.append({'type':'placeholder_count_mismatch','severity':'error','detail':{'source':G,'target':H}})
	I,J=len(DEFMARK.findall(B)),len(DEFMARK.findall(C))
	if I!=J:A.append({'type':'definition_marker_mismatch','severity':'review','detail':{'source':I,'target':J}})
	A+=glossary_findings(B,C,src_lang,tgt_lang,entries);return A
def _parts(text,pmap_hits,qs,found):
	G=text;H,I=[],0
	for A in re.finditer('(?<=[.;])\\s+(?=\\S)|\\n',G):H.append((I,A.start()));I=A.end()
	H.append((I,len(G)));L=[]
	for(C,D)in H:
		if D<=C:continue
		E=[A for A in pmap_hits if C<=A[0]<D];J=[E[A][0]for A in range(1,len(E))if any(E[A-1][0]<B[0]<E[A][0]for B in qs)]
		if not J:
			F=[A for A in found if A[0]in('duty','perm','prohib')and C<=A[1]<D]
			for K in range(1,len(F)):M=G[F[K-1][2]:F[K][1]];A=list(re.finditer('[,;]|\\band\\b|\\sו(?=[\u0590-\u05ff])',M));J.append(F[K-1][2]+(A[-1].start()if A else len(M)//2))
		B=[C]+sorted(set(J))+[D];L+=[(B[A],B[A+1])for A in range(len(B)-1)if B[A+1]>B[A]]
	return L
def obligation_view(text,pmap):
	A=text;B=_scan(A);K=find_parties(A,pmap);L=quants(A);M=[]
	for(C,E)in _parts(A,K,L,B):
		D=[A for A in K if C<=A[0]<E];H=[A for A in B if A[0]in('duty','perm','prohib')and C<=A[1]<E];N=A[C:E];F,G=None,'none';I=[B for B in D if PASSIVE_BY.search(A[max(C,B[0]-14):B[0]])]
		if I:F,G=I[0][2],'high'
		elif H:
			O=H[0];J=[A for A in D if A[0]<O[2]]
			if J:F=J[-1][2];G='high'if len({A[2]for A in J})==1 else'low'
			elif D:F,G=D[0][2],'low'
		elif D:F=D[0][2];P=len(re.match('^[^A-Za-z\u0590-\u05ff]*',A[C:E]).group(0));G='high'if D[0][0]-C-P<=25 else'low'
		M.append({'text':N.strip(),'quants':[A[2]for A in L if C<=A[0]<E],'obligor':F,'confidence':G,'passive':bool(I),'cues':[A[0]for A in H]})
	Q=sorted({A[0]for A in B if A[0]in('duty','perm','prohib')});return{'classes':Q,'neg':sum(1 for A in B if A[0]=='prohib')+sum(1 for A in B if A[0]=='neg'),'exc':sum(1 for A in B if A[0]=='exc'),'cond':sum(1 for A in B if A[0]=='cond'),'durations':sorted(A[2]for A in durations(A)),'remedies':_cats(REMEDIES,A),'actions':_cats(ACTIONS,A),'refs':sorted(refs_of(A)),'parts':M}
def _diff(a,b):return multiset_diff(a,b)
def level3_pair(src,tgt,pmap,tgt_lang):
	A,B=obligation_view(src,pmap),obligation_view(tgt,pmap);O=[]
	def C(code,sev,detail=''):O.append({'type':code,'severity':sev,'detail':detail})
	D,E=set(A['classes']),set(B['classes'])
	if D and E and D!=E:
		if('perm'in E)!=('perm'in D):C('modality_changed','error','source %s -> target %s (duty/permission differ)'%(sorted(D),sorted(E)))
		elif('prohib'in E)==('prohib'in D):C('modality_changed','review','source %s -> target %s'%(sorted(D),sorted(E)))
	elif D and not E and not(tgt_lang=='he'and D=={'duty'}):C('modality_not_expressed','review','source %s, no explicit modal marker in the target'%sorted(D))
	elif E and not D and'perm'in E:C('permission_added','review','the target says may/רשאי; the source has no explicit modal')
	if A['neg']and not B['neg']:C('negation_dropped','error','the source negates (%d), the target does not'%A['neg'])
	elif B['neg']and not A['neg']:C('negation_added','error','the target negates (%d), the source does not'%B['neg'])
	elif A['neg']!=B['neg']and(A['neg']-B['neg'])%2:C('negation_parity','review','negations: source %d, target %d'%(A['neg'],B['neg']))
	if A['exc']and not B['exc']:C('exception_dropped','error','the source has %d exception marker(s) (except/unless/למעט...), the target none'%A['exc'])
	elif B['exc']and not A['exc']:C('exception_added','error','the target has %d exception marker(s), the source none'%B['exc'])
	elif A['exc']!=B['exc']:C('exception_count','review','exception markers: source %d, target %d'%(A['exc'],B['exc']))
	if bool(A['cond'])!=bool(B['cond']):C('trigger_not_expressed'if A['cond']else'trigger_added','review','condition/trigger wording present in the %s only'%('source'if A['cond']else'target'))
	J,K=_diff(A['durations'],B['durations'])
	if J or K:C('deadline_changed','error',{'missing_in_target':J,'extra_in_target':K})
	J,K=_diff(A['refs'],B['refs'])
	if J or K:C('cross_reference_changed','error',{'missing_in_target':J,'extra_in_target':K})
	L,M=set(A['remedies']),set(B['remedies'])
	if L!=M:C('remedy_scope_differs','review',{'only_in_source':sorted(L-M),'only_in_target':sorted(M-L)})
	if A['actions']and B['actions']and not set(A['actions'])&set(B['actions']):C('action_differs','review',{'source':A['actions'],'target':B['actions']})
	F,I=A['parts'],B['parts']
	if len(F)!=len(I):
		if sum(1 for A in F+I if A['quants']or A['obligor'])>2 and(len(F)>1 or len(I)>1):C('clause_structure_differs','review','source %d obligation parts, target %d'%(len(F),len(I)))
	else:
		for(N,(G,H))in enumerate(zip(F,I),1):
			if G['quants']!=H['quants']and len(F)>1:
				P=sorted(B for A in F for B in A['quants'])==sorted(B for A in I for B in A['quants'])
				if P:C('amounts_swapped','error','obligation %d: source %s, target %s (all values preserved, attached to the wrong obligation)'%(N,G['quants'],H['quants']))
			if G['obligor']and H['obligor']and G['obligor']!=H['obligor']:Q='error'if G['confidence']==H['confidence']=='high'else'review';C('obligor_changed',Q,'obligation %d: source obligor %s, target obligor %s'%(N,G['obligor'],H['obligor']))
			elif bool(G['obligor'])!=bool(H['obligor']):C('obligor_not_identified','review','obligation %d: party named in only one side'%N)
	return O,A,B
def view_has_cues(v):return bool(v['classes']or v['neg']or v['exc']or v['cond']or v['durations']or v['remedies']or any(A['obligor']for A in v['parts']))
def _norm_ws(t):return re.sub('\\s+',' ',t or'').strip()
def _has_letters(t):return bool(re.search('[A-Za-z\u0590-\u05ff]',t))
def level1(man,src_path,tgt_path):
	P=src_path;G=man;Q,K,M,Y=[],[],[],[]
	def B(code,detail,sid=None):Q.append({'code':code,'id':sid,'detail':detail})
	if G.get('manifest_schema')!=MANIFEST_SCHEMA:B('MANIFEST_INVALID','manifest_schema must be %s'%MANIFEST_SCHEMA)
	I=G.get('segments')or[];Z=hashlib.sha256(open(P,'rb').read()).hexdigest()
	if G.get('source_sha256')!=Z:B('SOURCE_CHANGED','the source file is not the version the manifest was made from (manifest %s, file %s)'%((G.get('source_sha256')or'')[:12],Z[:12]))
	a,R=set(),{}
	for A in I:
		H=A.get('part'),A.get('index')
		if A.get('id')in R or H in a:B('DUPLICATE_SEGMENT','the segment appears twice in the manifest',A.get('id'))
		R[A.get('id')]=A;a.add(H)
	J=None;i=sniff(P)
	if i in('docx','pdf'):
		try:
			j,k=collect(P);J={A['id']:A for A in j}
			for(C,b)in J.items():
				if C not in R:B('MISSING_SEGMENT','a segment of the source (%s) is not in the manifest: %s'%(b['kind'],b['source'][:50]),C)
			S=G.get('tracked_changes')
			if not isinstance(S,dict)or'layer'not in S:B('TRACKED_CHANGES_NOT_RECORDED','the manifest does not record the tracked-changes layer')
			else:
				D,N=k['tracked_changes'],S
				if(D['insertions'],D['deletions'],D['moves'])!=(N.get('insertions'),N.get('deletions'),N.get('moves')):B('SOURCE_CHANGED','tracked changes differ from the manifest (source %s, manifest %s)'%({A:D[A]for A in('insertions','deletions','moves')},{A:N.get(A)for A in('insertions','deletions','moves')}))
				if D['insertions']or D['deletions']or D['moves']:Y.append('The source has a tracked-changes layer (%d insertions, %d deletions, %d moves): the translation covers the text with insertions shown and deletions omitted.'%(D['insertions'],D['deletions'],D['moves']))
		except ImportError as l:M.append('source re-extraction (a required library is missing: %s)'%l)
	else:M.append('source re-extraction (the source is a plain-text file)')
	T={}
	for A in I:
		C,H,E=A.get('id'),A.get('kind')or'body',A.get('source')or'';U=T.setdefault(H,{'segments':0,'translated':0,'untranslated_with_reason':0});U['segments']+=1;V=J.get(C)if J is not None else None
		if H=='scanned':
			if not A.get('source_confirmed'):K.append({'code':'SCANNED_SEGMENT_UNCONFIRMED','id':C,'kind':H,'detail':'text read from an image is not marked source_confirmed'})
			M.append('scanned text %s against the image (judgement step)'%C)
		elif J is not None:
			if V is None:B('EXTRA_SEGMENT','the manifest has a segment that is not in the source',C)
			elif _norm_ws(V['source'])!=_norm_ws(E)or seg_hash(V['source'])!=A.get('source_hash'):B('SOURCE_CHANGED_SEGMENT','the source text of this segment is not what was translated',C)
		F,L=_norm_ws(A.get('target')),_norm_ws(A.get('not_translated_reason'))
		if F and L:B('AMBIGUOUS_SEGMENT','has both a target and a not_translated_reason',C)
		elif not F and not L:B('MISSING_TARGET','no target and no stated reason: %s'%E[:50],C)
		elif L:
			U['untranslated_with_reason']+=1
			if not(L.lower().startswith('immaterial:')and not _has_letters(E)):K.append({'code':'UNTRANSLATED_SEGMENT','id':C,'kind':H,'reason':L,'source':E[:80]})
		else:U['translated']+=1
	c={};d=' '.join(A.get('source','')for A in I);e=[A for A in I if _norm_ws(A.get('target'))and _norm_ws(A.get('target'))!=_norm_ws(A.get('source'))];W=target_lang(d)if d.strip()else'';f=target_lang(' '.join(A.get('target','')for A in e))if e else'';c.update(source=W,target=f)
	for A in I:
		F,E=_norm_ws(A.get('target')),_norm_ws(A.get('source'))
		if F and E==F and W!=f and len(E.split())>=3 and(HEB.search(E)if W=='he'else LAT.search(E)):B('UNTRANSLATED_COPY','the target is the source text copied unchanged and not marked as untranslated',A.get('id'))
	g={}
	for A in I:
		F=_norm_ws(A.get('target')).lower()
		if len(F)>=25:g.setdefault(F,[]).append(A)
	for(F,O)in g.items():
		if len({A.get('source_hash')for A in O})>1:B('DUPLICATE_TARGET','one target text is used for %d different source segments: %s'%(len(O),[A.get('id')for A in O][:6]),O[0].get('id'))
	if not _norm_ws(G.get('glossary_version')):B('GLOSSARY_VERSION_NOT_RECORDED','the manifest does not record the glossary id/version (write "none" when no glossary applies)')
	if G.get('scanned_text_unread'):K.append({'code':'SCANNED_TEXT_UNREAD','id':None,'kind':'scanned','detail':'the source has pages with no text layer that were not read'})
	X={A:T.get(A,{'segments':0,'translated':0,'untranslated_with_reason':0})for A in('footnote','endnote','comment','table','heading','annex','header','footer')};h='complete'if not Q and not K else'incomplete';m={'status':h,'may_present_as_complete':h=='complete','findings':Q,'material_gaps':K,'by_kind':T,'footnotes':X['footnote'],'endnotes':X['endnote'],'comments':X['comment'],'notes':Y,'languages':c,'rule':'A segment with no target needs a stated reason; any such segment except a source with no words ("immaterial:") is a material gap and blocks presenting the translation as complete.'};return m,J,M
def structure(man,src_path,tgt_path):
	J=tgt_path;A,G,B=[],[],[];K,L=sniff(src_path),sniff(J)
	if not(K=='docx'and L=='docx'):B.append('built file compared with the manifest, and fields/bookmarks/references attachment (needs a Word source and a Word target)');return{'status':'not_checked','findings':A,'warnings':G},B
	try:M,Q=collect(J)
	except ImportError as N:B.append('built file comparison (a required library is missing: %s)'%N);return{'status':'not_checked','findings':A,'warnings':G},B
	O={A['id']:A for A in M}
	for C in man.get('segments')or[]:
		D=C.get('id');I=O.get(D)
		if I is None:
			if C.get('kind')!='scanned':A.append({'code':'BUILT_FILE_MISSING_SEGMENT','id':D,'detail':'the built file has no text at this place'})
			continue
		P=_norm_ws(C.get('target'))or _norm_ws(C.get('source'))
		if _norm_ws(I['source'])!=P:A.append({'code':'BUILT_FILE_DIFFERS_FROM_MANIFEST','id':D,'detail':'the text in the built file is not the manifest target'})
		E,H=C.get('features')or{},I.get('features')or{}
		for F in('fields','bookmarks','hyperlinks','note_refs','comment_refs','drawings'):
			if E.get(F,0)!=H.get(F,0):A.append({'code':'ATTACHMENT_LOST','id':D,'detail':'%s: source %s, built %s'%(F,E.get(F,0),H.get(F,0))})
		if E.get('emphasis_runs',0)!=H.get('emphasis_runs',0)and E.get('emphasis_runs',0):G.append({'code':'EMPHASIS_CHANGED','id':D,'detail':'emphasised runs: source %s, built %s (judgement: does the emphasis carry meaning?)'%(E.get('emphasis_runs'),H.get('emphasis_runs'))})
	return{'status':'fail'if A else'pass','findings':A,'warnings':G},B
def run_manifest_checks(man,src_path,tgt_path,glossary=None,parties=None,verifier=None):
	X=glossary;W=tgt_path;Q=src_path;D=verifier;C=man;R,Y=X if X else('',[]);g=load_party_map(Y,list(parties or[])+list(C.get('parties')or[]));B,j,Z=level1(C,Q,W);J,h=structure(C,Q,W)
	if R and C.get('glossary_version')and R!=C.get('glossary_version'):B['findings'].append({'code':'GLOSSARY_VERSION_DIFFERS','id':None,'detail':'glossary file %s, manifest %s'%(R,C.get('glossary_version'))});B['status'],B['may_present_as_complete']='incomplete',False
	K,F=B['languages']['source'],B['languages']['target'];G,H,I,a=[],[],[],0
	if K and F and K!=F:
		for E in C.get('segments')or[]:
			L,M=_norm_ws(E.get('source')),_norm_ws(E.get('target'))
			if not L or not M:continue
			N=E.get('id')
			for S in level2_pair(L,M,K,F,Y):G.append(dict(S,id=N,kind=E.get('kind')))
			i,b,c=level3_pair(L,M,g,F)
			for S in i:H.append(dict(S,id=N,kind=E.get('kind')))
			d=[A['type']for A in G+H if A['id']==N]
			if view_has_cues(b)or view_has_cues(c)or d:I.append({'id':N,'kind':E.get('kind'),'source':L,'target':M,'flags':d,'source_cues':{A:b[A]for A in('classes','neg','exc','cond','durations','remedies','actions','refs')},'target_cues':{A:c[A]for A in('classes','neg','exc','cond','durations','remedies','actions','refs')}})
			else:a+=1
		I.sort(key=lambda q:0 if q['flags']else 1)
	else:Z.append('per-segment checks (the source and target languages could not be told apart: %r/%r)'%(K,F))
	O=[A for A in G if A['severity']=='error'];P=[A for A in H if A['severity']=='error'];e=[A for A in G+H if A['severity']=='review'];A={'status':'not_performed','findings':[],'reviewed':0};T={A['id']for A in I}
	if D:A['source_sha256_matches']=D.get('source_sha256')==hashlib.sha256(open(Q,'rb').read()).hexdigest();U=set(D.get('segments_reviewed')or[]);A.update(verifier=D.get('verifier'),reviewed=len(U&T),unreviewed=sorted(T-U)[:50],findings=D.get('findings')or[]);A['status']='performed'if A['source_sha256_matches']and not T-U else'stale_source_version'if not A['source_sha256_matches']else'partial'
	V=[A for A in A['findings']if A.get('severity')=='error'and not A.get('resolved')];f=not O and not P;return{'coverage':B,'structural_integrity':J,'segment_checks':{'level2_numbers_dates_terms':{'status':'fail'if O else'pass','errors':O,'review':[A for A in G if A['severity']=='review']},'level3_obligations':{'status':'fail'if P else'pass','errors':P,'review':[A for A in H if A['severity']=='review']},'segments_without_any_obligation_cue':a},'linguistic_legal_review':{'status':A['status'],'performed_by':'clean-context verifier read'if D else None,'mechanical_checks':MECHANICAL_CHECKS,'judgement_checks':JUDGEMENT_CHECKS,'items_for_review':len(I),'review_flags':len(e),'queue':I,'verifier':A,'note':"The queue is the input of the verifier: every segment with an obligation cue or a flag, source and target side by side, flagged ones first. The verifier answers per segment id, without the translator's reasoning."},'not_checked':sorted(set(Z+h)|{'obligations written without an explicit marker (for example a bare Hebrew future verb) are not detected mechanically'}),'summary':{'coverage':B['status'],'structure':J['status'],'mechanical_errors':len(O)+len(P),'review_flags':len(e),'review':A['status'],'verifier_blocking':len(V)},'pass':B['status']=='complete'and J['status']!='fail'and f and not V,'may_present_as_checked_and_complete':B['status']=='complete'and J['status']=='pass'and f and A['status']=='performed'and not V}
def load_json(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def main():
	C=argparse.ArgumentParser();C.add_argument('source');C.add_argument('target');C.add_argument('--out');C.add_argument('--out-dir',help='without --out: the report is written here under the canonical name translation-integrity-<id>-<en|he>.json');C.add_argument('--id',help='with --out-dir: transaction_id, or a short Latin id of the document (default: the source file name)');C.add_argument('--manifest',help='segments.json made by build_translation_docx.py extract and filled by the translator: turns on the per-segment checks (coverage, numbers/terms, obligations)');C.add_argument('--glossary',help='the approved glossary JSON (מילון-מונחים.json): per-segment defined-term check');C.add_argument('--parties',help='JSON list of party roles [{"id","he":[..],"en":[..]}] for the obligor check');C.add_argument('--verifier-result',help='JSON written by the clean-context verifier read: source_sha256, segments_reviewed, findings');C.add_argument('--review-queue-out',help='write the verifier input (segment pairs with cues, flagged first) here');A=C.parse_args();from build_translation_docx import sniff,KIND_MSG as S
	for J in(A.source,A.target):
		K=sniff(J)
		if K in S:print(S[K]%(Path(J).name,Path(J).name));raise SystemExit(1 if K=='missing'else 2)
		if K=='docx':
			b,c,d=load_docx_or_explain(J,loader=False)
			if b is None:print(c);raise SystemExit(d)
	T,U=[],[];N=text_of(A.target,U);V=tokens(text_of(A.source,T));e=tokens(N);B={'schema':REPORT_SCHEMA,'source_version':{'file':Path(A.source).name,'sha256':hashlib.sha256(open(A.source,'rb').read()).hexdigest()},'checks':{},'pass':True,'ignored_stamp_paragraphs':{'source':T,'target':U},'disclaimer':NEVER_CLAIMED,'legal_validity':'not_assessed'}
	for E in V:
		F,G=multiset_diff(V[E],e[E]);B['checks'][E]={'missing_in_target':F,'extra_in_target':G}
		if F or G:B['pass']=False
	f,O=hf_paragraphs(A.source),hf_paragraphs(A.target);g,h=tokens('\n'.join(A[1]for A in f)),tokens('\n'.join(A[1]for A in O));L={}
	for E in('numeric_tokens','currency_tokens'):
		F,G=multiset_diff(g[E],h[E]);L[E]={'missing_in_target':F,'extra_in_target':G}
		if F or G:B['pass']=False
	P=target_lang(N);W=[A[1][:60]for A in O if(P=='he')!=A[2]and(P=='he'or not HEB.search(A[1]))];Q=target_lang(text_of(A.source));X=[A[1][:60]for A in O if Q!=P and(Q=='he'and HEB.search(A[1])and not LAT.search(A[1])or Q=='en'and LAT.search(A[1])and not HEB.search(A[1])and len(LAT.findall(A[1]))>8)];L['wrong_direction']=W;L['untranslated']=X
	if W or X:B['pass']=False
	B['checks']['headers_footers']=L
	if A.manifest:
		try:H=load_json(A.manifest);i=load_glossary(A.glossary)if A.glossary else None;j=load_json(A.parties)if A.parties else None;k=load_json(A.verifier_result)if A.verifier_result else None
		except(OSError,ValueError)as I:print('refused: cannot read a --manifest/--glossary/--parties/--verifier-result file (%s)'%type(I).__name__,file=sys.stderr);raise SystemExit(2)
		M=run_manifest_checks(H,A.source,A.target,i,j,k)
		if not A.glossary:M['not_checked'].append('defined terms against the glossary (no --glossary file was supplied)')
		B['manifest_mode']=True;B['manifest']={'file':Path(A.manifest).name,'glossary_version':H.get('glossary_version'),'tracked_changes':H.get('tracked_changes'),'parts':H.get('parts'),'segments':len(H.get('segments')or[])}
		for Y in('coverage','structural_integrity','segment_checks','linguistic_legal_review','not_checked','summary','may_present_as_checked_and_complete'):B[Y]=M[Y]
		B['pass']=B['pass']and M['pass']
		if A.review_queue_out:
			R=os.path.abspath(A.review_queue_out)
			try:R=guard_out(R,inputs=[A.source,A.target,A.manifest])
			except OutputRefused as I:print('refused: %s'%I,file=sys.stderr);raise SystemExit(2)
			Path(R).write_text(json.dumps({'source_version':B['source_version'],'instructions':'Read each pair cold, without the reasoning of the translation. Per segment id say whether the target carries the same obligor, action, duty-vs-permission, negation, amount, trigger, deadline, exception and remedy as the source. Return JSON {verifier, source_sha256, segments_reviewed:[ids], findings:[{id,type,severity,note}]}. Do not assess legal validity.','queue':M['linguistic_legal_review']['queue']},ensure_ascii=False,indent=1),encoding='utf-8')
	else:Z='No --manifest was supplied: only the legacy global counts (numbers, currencies, section numbers, headers and footers) were checked. Coverage, per-segment checks and obligation checks were NOT checked.'+chr(10)+'לא סופק --manifest: נבדקו רק הספירות הגלובליות הישנות. כיסוי, בדיקות לפי קטע ובדיקת התחייבויות לא נבדקו.';B['manifest_mode']=False;B['warnings']=['NO_MANIFEST: '+Z];B['coverage']={'status':'not_checked','may_present_as_complete':False};print('warning: '+Z,file=sys.stderr)
	a=json.dumps(B,ensure_ascii=False,indent=2);D=A.out
	if not D and A.out_dir:D=unique(os.path.join(A.out_dir,canonical_name(A.id or Path(A.source).stem,target_lang(N))))
	if D:
		try:D=guard_out(D,inputs=[A.source,A.target])
		except OutputRefused as I:print('refused: %s'%I,file=sys.stderr);raise SystemExit(2)
		if os.path.dirname(D):os.makedirs(os.path.dirname(D),exist_ok=True)
		Path(D).write_text(a+'\n',encoding='utf-8')
	print(a);raise SystemExit(0 if B['pass']else 1)
if __name__=='__main__':main()
