# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import hashlib,html as _html,io,json,os,re,sys
from urllib.parse import urlsplit
if __name__=='__main__':sys.dont_write_bytecode=True
try:from.entity_store import has_secret;from.page_text import PdfTextUnavailable,decode_page,excerpt_in,norm,page_text
except ImportError:sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from entity_store import has_secret;from page_text import PdfTextUnavailable,decode_page,excerpt_in,norm,page_text
try:from common.case_law import case_law_hits,case_law_url;from common.cli import guard_out,parser,run,write_json;from common.net import client_detail_in_query,url_allowed;from common.paths import long_path;from common.terms import terms_re
except ImportError:sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.case_law import case_law_hits,case_law_url;from common.cli import guard_out,parser,run,write_json;from common.net import client_detail_in_query,url_allowed;from common.paths import long_path;from common.terms import terms_re
LENS8=['legal','financial','operational','technology','regulatory','reputational','insurance','force_majeure']
KINDS={'clause','silence','vague_term','back_to_back','external','hidden_text','untracked_change'}
META_KEYS={'company','scope','transaction_id','party_terms','scope_label','source_ref','source_version','annexes_reviewed','annexes_missing','deal_value','generated_at','last_updated','docAccess','publishTarget','branding','display_language','prepared_for_counsel','user_focus','counterparty','document_title','position','mutual_primary_role','playbook_ref','benchmark_status','paper_type'}
RISK_KEYS={'id','risk_no','kind','name','description','hidden_text','primary_lens','lens','inherent','severity_level','controls','residual','exposure','scenario','critical_detail','anchors','treatment_direction','playbook_flag','certainty','external_source_ids','side','decision','drafted_by','regulatory_basis','created_by_response','concession_refs','states','event','impact','control_ref','exposure_state'}
FORBIDDEN_RISK={'mitigation','feasibility_basis','leverage_window','owner','mitigation_channel','category','estimated_amount','ratio_to_deal_value'}
DEF_TYPES={'contradiction','ambiguity','missing_annex','missing_agreement','undefined_term','inconsistent_term','broken_reference','precedence_missing','version_mismatch','language_mismatch','leftover_text','blank_field','unilateral_document','cumulative_requirement'}
TEXT_STATUS={'agreed','counterparty_draft','their_draft','our_unsent_response','our_sent_response','our_draft'}
OUR_TEXT_STATUS='our_unsent_response','our_sent_response','our_draft'
APPROVED_DOMAINS=()
APPROVED_SOURCES_ENV='AREO_APPROVED_SOURCES'
APPROVED_SOURCES_FILE='מקורות-מאושרים.json'
def default_sources_path():return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),APPROVED_SOURCES_FILE)
def sources_path(path=None):return path or os.environ.get(APPROVED_SOURCES_ENV)or default_sources_path()
ENTITY_PURPOSE='entity'
ENTITY_DOMAINS=()
MEDIA_EXCLUDED='facebook.com','fb.com','instagram.com','x.com','twitter.com','linkedin.com','tiktok.com','youtube.com','youtu.be','reddit.com','t.me','telegram.org','whatsapp.com','threads.net','medium.com','substack.com','blogspot.com','wordpress.com','wix.com','tumblr.com','quora.com','wikipedia.org','fxp.co.il','rotter.net','tapuz.co.il','glassdoor.com','trustpilot.com','google.com','bing.com','duckduckgo.com','yahoo.com','dnb.com','bdi.co.il','opencorporates.com','creditsafe.com','zoominfo.com','crunchbase.com','coface.com'
COURT_DOMAINS='court.gov.il','takdin.co.il','psakdin.co.il','nevo.co.il','courtlistener.com','bailii.org','pacer.gov','uscourts.gov','judiciary.uk','rechtspraak.nl','justia.com','casetext.com','curia.europa.eu','hudoc.echr.coe.int','lexisnexis.com','westlaw.com'
MEDIA_MARKERS=re.compile('(?:^|[.\\-/])(?:blogs?|forums?|community|talk|board)(?:[.\\-/]|$)',re.I)
SOURCE_ORIGINS='playbook','documents'
MEDIA_LABEL={'he':'אות לא מאומת, מהתקשורת','en':'Unverified signal, from the media'}
INTENT_PHRASES=['בכוונה','במזיד','בזדון','ביודעין','בכוונת מכוון','במתכוון','במכוון','בכוונו','בחוסר תום לב','בכוונה תחילה','ניסה להונות','ניסתה להונות','מתכוון להונות','מתכוונת להונות','כוונה פלילית','intentionally','deliberately','wilfully','willfully','knowingly','in bad faith','with intent','intended to','tried to defraud','fraudulent intent','malicious']
CASE_LAW_WORDS=['פסק דין','פסק הדין','בית המשפט קבע','בית הדין קבע','נפסק','ruling','judgment','the court held','court ruled','verdict']
BLOCKED_PHRASES=['תוחלת נזק','סיכון מצטבר','תיאבון סיכון','אינו ייעוץ משפטי','מודל שפה','קו אדום','חבילת ויתורים','חלון מינוף','ישימות','אם הצד השני ידחה','ודאית','מהיום הראשון','אין בקרה','מופר','הפרנו','לא נעמוד','לא תקוים','אינה ניתנת לקיום','לחץ פנימי','יודע ש','עמדת נסיגה','פלייבוק באחוזים','להתעקש','לדרוש','הצד שכנגד יטען','אומדן','משוער','חלוקת השווי','expected loss','aggregate risk','cumulative risk','risk appetite','not legal advice','language model','red line','concession package','leverage window','feasibility','if the other side rejects','if the counterparty rejects','certainly','from day one','no control in place','no controls in place','is breached','we breached','we will not comply','cannot be complied with','internal pressure','knows that','fallback position','% compliance','compliance %','percent compliance','insist on','to demand','the counterparty will argue','the other side will argue','estimate','estimated','value split','split of value','allocation of value']
ADVICE_ONLY={'לדרוש','להתעקש','to demand','insist on'}
ADVICE_PATH=re.compile('treatment_direction|bottom_line|breaking_fix|proposed_fix|neutralizes|deal_one_line')
CODE_RE=re.compile('\\b(?:R-?\\d{2}|Q\\d+|V-\\d+|REG\\d+|SEG-\\d+|APR-\\d+|RSK-\\d+|DEF-\\d+|CMB-\\d+|ENT-\\d+|SRC-\\d+)\\b|כלל \\d|\\bסבב \\d|\\d+\\s*[xX×]\\s*\\d+')
DOC_NAME_PATH=re.compile('^\\.documents\\[\\d+\\]\\.title$|^\\.meta\\.source_version\\.title$|^\\.meta\\.document_title$|\\.anchors\\[\\d+\\]\\.document$|\\.locations\\[\\d+\\]\\.document$|\\.caps\\[\\d+\\]\\.document$|\\.imported_from$|\\.shared_with\\[\\d+\\]$|\\.states\\.current\\.version$|\\.states\\.proposed\\[\\d+\\]\\.markup_version$|\\.states\\.agreed\\.accepted_version$')
ROUND_RE=re.compile('\\bסבב \\d')
CURRENCY_CODE_RE=re.compile('\\b(?:ILS|NIS|USD|EUR|GBP|CHF|JPY|CNY|CAD|AUD|NZD|SGD|HKD|INR|AED|SEK|NOK|DKK|PLN|CZK|HUF|RON|TRY|BRL|MXN|ZAR|KRW)\\b')
SKIP_TEXT=re.compile('(\\.id$|_id$|\\.file$|source_ref$|source_version|\\.logo$|\\.url$|typed_url|final_url|\\.sha256|risk_ids|\\.lens(\\[\\d+\\])?$|\\.kind$|\\.type$|\\.status$|\\.combo_id|\\.currency|primary_lens|playbook_flag|certainty|drafted_by|\\.mode$|\\.role$|urlSource|text_status|sign_as_is|\\.label$|\\.result$|\\.prevails$|missing_identifiers|\\.question\\[\\d+\\]|external_source_ids|transaction_id|\\.scope$|display_language|benchmark_status|\\.saved_at|\\.at$|\\.date$|defined_at|generated_at|last_updated|set_at|offered_at|\\.country$|\\.excerpt$|search_log|raw_copies|\\.query|state_clause_id|regulatory_basis|\\.basis$|version_date|\\.side$|docAccess|deal_value\\.source|\\.meta\\.user_focus$|cross_checks|concession_refs)')
QUOTED_USER_TEXT='.meta.user_focus',
CASE_LAW_EXEMPT=re.compile('\\.quote$|\\.quotes\\[\\d+\\]$|\\.excerpt$|\\.anchors\\[\\d+\\]\\.text$')
LIMITS={'risks[].name':70,'risks[].treatment_direction':70,'risks[].anchors[].clause':30,'summary.bottom_line[]':160,'summary.deal_one_line':100,'summary.key_dates[].what':45,'summary.key_dates[].consequence':45,'summary.key_dates[].window':40,'summary.key_dates[].clause':30,'document_defects[].topic':25,'document_defects[].risk_created':120,'document_defects[].proposed_fix':70,'document_defects[].locations[].quote':120,'document_defects[].prevails_basis':100,'dangerous_combinations[].why_together':220,'dangerous_combinations[].breaking_fix':80,'dangerous_combinations[].neutralizes':100,'summary.not_checked[].item':110,'summary.not_checked[].why':80,'summary.assumptions[]':200,'coverage[].note':80,'risks[].critical_detail.what_happens':300,'risks[].critical_detail.why_not_protected':300,'risks[].residual.treated_how':70,'summary.money_picture.exposures[].what':60,'summary.money_picture.exposures[].reason':80}
MAX_KEY_DATES=5
TREATED_STATUS='our_unsent_response','our_sent_response','our_draft','agreed'
TREATED_MAX_SCORE=8
DELETED_RE=re.compile('נמחק|נמחקה|נמחקו|הוסר|הוסרה|הוסרו|הוחזר לנוסח|\\bdeleted\\b|\\bremoved\\b|\\bstruck\\b',re.I)
HIDDEN_ASKS='approve_terms','send_information'
AMOUNT_SOURCES='contract','client'
DEAL_VALUE_FILES='negotiation_state.json','strategy-data.json'
ISO_CURRENCIES='ILS|NIS|USD|EUR|GBP|CHF|JPY|CNY|CAD|AUD|NZD|SGD|HKD|INR|AED|SAR|QAR|KWD|BHD|OMR|EGP|JOD|SEK|NOK|DKK|ISK|PLN|CZK|HUF|RON|BGN|TRY|RUB|BRL|MXN|ARS|CLP|COP|PEN|ZAR|KRW|TWD|THB|MYR|IDR|PHP|VND'
_CUR='(?:ש"ח|ש״ח|שקלים|שקל|₪|ליש"ט|ליש״ט|לירות שטרלינג|לירה שטרלינג|דולר(?:ים)?|אירו|יורו|פרנק(?:ים)?|ין|דירהם|£|\\$|€|¥|Fr\\.|S\\$|A\\$|C\\$|HK\\$|\\b(?:'+ISO_CURRENCIES+')\\b)'
_AMT='(?:\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?|\\d+(?:\\.\\d+)?\\s*(?:אלף|מיליון|מיליארד|[kKmM]|bn|million|billion)\\b|\\d{4,})'
_VALUE_AMT=re.compile('(?:'+_AMT+'\\s*'+_CUR+'|'+_CUR+'\\s*'+_AMT+')')
_VALUE_CTX=re.compile('לשנה|בשנה|שנתי|לחודש|בחודש|תמורה|שווי|ההסכם המסחרי|היקף ההתקשרות|per year|annual|per month|monthly|consideration|contract value|deal value|\\bfees?\\b',re.I)
MONEY_MAX=None
INS_CAP_RATIO=2
WORDS_WARN,WORDS_FAIL=2800,3200
FIXED_REFS={'פתיח','מבוא','הגדרות','חתימות','בלוק החתימות','בלוק הצדדים','כותרת','נספחים','preamble','recitals','definitions','signatures','signature page','signature block','cover page','order form','title','annexes','schedules','exhibits','parties'}
_ANNEX_RE=re.compile('^(?:נספח|annex|schedule|exhibit|appendix|attachment|addendum)\\s+[^\\s;]{1,20}(\\s[^\\s;]{1,20})?$',re.I)
_NUM='\\d+[א-ת]?(?:\\.\\d+[א-ת]?)*(?:\\([א-תa-z0-9]{1,3}\\))*'
_REF_RE=re.compile('^(?:[^\\d;,]{1,30}?,?\\s)?(?:סעיף |סעיפים |פסקה |section |sections |clause |clauses |article |para |paragraph |§\\s?)?'+_NUM+'(?:\\s*(?:,|ו-?)\\s*'+_NUM+')*$',re.I)
def clause_ref_ok(s):
	s=(s or'').strip()
	if not s:return False
	for A in re.split('\\s*;\\s*',s):
		for B in('חדש אחרי ','new after ','New after '):
			if A.startswith(B):A=A[len(B):].strip()
		if A.lower()in FIXED_REFS or _ANNEX_RE.match(A):continue
		if all(A.strip().lower()in FIXED_REFS or _ANNEX_RE.match(A.strip())for A in A.split(',')):continue
		if not _REF_RE.match(A):return False
	return True
def load_amendments(items):
	B=[]
	for A in items or[]:B.append({'match':re.compile(A['match']),'name':A['name'],'in_force':A['in_force'],'topic':re.compile(A['topic'])if A.get('topic')else None,'exclude':re.compile(A['exclude'])if A.get('exclude')else None})
	return B
DECISION_KEYS={'status','basis','state_clause_id','state_clause_ids','note','decided_at'}
APPROVAL_PHRASES=['ממתין לאישור','ממתינה לאישור','ממתינים לאישור','טעון אישור מנכ','אישור מנכ"ל','אישור מנכ״ל','אישור המנכ"ל','אישור המנכ״ל','טבלת הסמכויות','מוצע לקבלה','awaiting approval','pending approval','subject to CEO approval']
SIDES='as_obligor','as_beneficiary','both','as_discloser','as_recipient'
RULE_ID_RE=re.compile('^(?:R-?\\d+|mandatory_list:.*|rule:.*)$')
AREO_UA_PREFIX='AreoLegal-research/'
AREO_UA_CONTACT=re.compile('AreoLegal\\b.*contact: [A-Za-z0-9._%+\\-]+@[A-Za-z0-9.\\-]+\\.[A-Za-z]{2,}\\)$')
BROWSER_UA=re.compile('Mozilla/|Chrome/|Safari/|Firefox/|Edg/|Gecko',re.I)
_TERM_CACHE={}
def _term(phrase):
	A=phrase
	if A not in _TERM_CACHE:_TERM_CACHE[A]=terms_re([A])
	return _TERM_CACHE[A]
def _load_sources_file(path):
	A=path;A=sources_path(A)
	if not A or not os.path.isfile(long_path(A)):return None,None
	try:
		with io.open(long_path(A),encoding='utf-8-sig')as B:return json.load(B),A
	except(OSError,ValueError):return None,None
def _norm_dom(d):d=(d or'').strip().lower().rstrip('/').rstrip('.');return d[4:]if d.startswith('www.')else d
def _src_rules(src):
	A=src;C,I,D=_norm_dom(A.get('domain')).partition('/')
	if A.get('status')!='approved'or not C:return[]
	B=[A for A in A.get('allowed_paths')or[]if(A or'').strip('/')]
	if D:B=B or['/'+D]
	H=any((A.get(B)or'').strip()for B in A if B.startswith('usage_restriction'));E=A.get('restriction_kind')
	if(H or E=='paths')and not B and E!='content':return[]
	F=(''if A.get('include_subdomains')else'=')+C;G=[F+'/'+A.strip().lstrip('/')for A in B]or[F];G+=['='+_norm_dom(A)for A in A.get('include_hosts')or[]if _norm_dom(A)];return G
def _page_rule(pg):
	if pg.get('status')!='approved'or not pg.get('url'):return
	A=urlsplit(pg['url']);B=_norm_dom(A.hostname)
	if not B:return
	C=[A for A in A.query.split('&')if re.match('(?i)(officeid|topicid|type)=',A)];return'='+B+(A.path.rstrip('/')or'')+('?'+'&'.join(C)if C else'')
def _case_law_entries(block):
	A=block
	if isinstance(A,list):return A
	if isinstance(A,dict):
		if A.get('sources')or A.get('domains'):return list(A.get('sources')or[])+list(A.get('domains')or[])
		return[B for A in A.get('jurisdictions')or[]for B in A.get('sources')or[]]
	return[]
def _case_law_rules(data):
	C=[]
	for A in _case_law_entries((data or{}).get('case_law_only')):
		if isinstance(A,str):A={'domain':A}
		B=_norm_dom(A.get('domain'))
		if not B:continue
		D=[A for A in A.get('paths')or[]if(A or'').strip('/')];C+=['!'+B+'/'+A.lstrip('/')for A in D]or['!'+B]
	return C
def _rules_of(jurisdictions,pages=True):
	A=[]
	for B in jurisdictions or[]:
		for D in B.get('sources')or[]:A+=_src_rules(D)
		for E in B.get('pages')or[]if pages else[]:
			C=_page_rule(E)
			if C:A.append(C)
	return A
class Rules(tuple):refuse=()
def _rules_obj(allowed,refuse):A=Rules(allowed);A.refuse=tuple(refuse);return A
def approved_domains(path=None,purpose=None):
	B=path;A,B=_load_sources_file(B)
	if not A:return(),None
	C=_rules_of(A.get('jurisdictions'))
	if purpose==ENTITY_PURPOSE:C+=_rules_of((A.get('entity_check')or{}).get('jurisdictions'),pages=False)
	if not C:return(),None
	return _rules_obj(dict.fromkeys(C),_case_law_rules(A)),B
def media_rule(path=None):B,D=_load_sources_file(path);A=((B or{}).get('entity_check')or{}).get('media')or{};C=tuple(dict.fromkeys([A.strip().lower()for A in A.get('excluded_domains')or()]+list(MEDIA_EXCLUDED)));return{'excluded':C,'label':{'he':A.get('label_he')or MEDIA_LABEL['he'],'en':A.get('label_en')or MEDIA_LABEL['en']}}
def _host_in(host,doms):return any(host==A or host.endswith('.'+A)for A in doms)
def media_problem(url,path=None,purpose=ENTITY_PURPOSE):
	if purpose!=ENTITY_PURPOSE:return'תקשורת רק בבדיקת רקע על הצד שכנגד (--purpose entity)'
	B=urlsplit(url or'');A=(B.hostname or'').lower()
	if B.scheme not in('http','https')or not A:return'כתובת שאינה http או https'
	C=case_law_url(url)
	if C:return'בית משפט או מאגר פסיקה: אסור תמיד (כלל 1.1); הליכים משפטיים הם משימה לעורך הדין. %s'%C
	if _host_in(A,COURT_DOMAINS)or re.search('(?:^|\\.)courts?\\.',A):return'בית משפט או מאגר פסיקה: אסור תמיד (כלל 1.1); הליכים משפטיים הם משימה לעורך הדין'
	if _host_in(A,media_rule(path)['excluded']):return'אינו כלי תקשורת מבוסס (רשת חברתית, בלוג, פורום, מנוע חיפוש או מאגר מסחרי): %s'%A
	if MEDIA_MARKERS.search(A)or MEDIA_MARKERS.search('/'+(B.path or'').strip('/').split('/')[0]+'/'):return'בלוג או פורום: %s'%A
	return''
def source_class(url,path=None,purpose=None):
	B=purpose;A=url
	if case_law_url(A):return
	if domain_ok(A,approved_domains(path,B)[0]):return'official'
	return'media'if B==ENTITY_PURPOSE and not media_problem(A,path,B)else None
def domain_ok(url,rules):A=rules;return url_allowed(url,tuple(A or())+tuple(getattr(A,'refuse',())))
def ua_problem(ua):
	A=ua;A=str(A)
	if not A.startswith(AREO_UA_PREFIX)or BROWSER_UA.search(A):return'user_agent שאינו המזהה של Areo (%s): אסור מזהה דפדפן'%A[:40]
	if not AREO_UA_CONTACT.search(A):return'user_agent בלי שם הארגון וכתובת קשר (%s): נדרש "AreoLegal ... contact: <email>"'%A[:60]
	return''
ISO_TS=re.compile('^\\d{4}-\\d{2}-\\d{2}(?:T\\d{2}:\\d{2}:\\d{2}(?:\\.\\d+)?(?:Z|[+-]\\d{2}:\\d{2}))?$')
TS_KEY=re.compile('(?:_at|^at|saved_at|looked_up_at|defined_at)$')
def profile_status(profile):A=profile or{};C=(A.get('regulatory_footprint_primary')or[])+(A.get('regulatory_footprint_secondary')or[]);B=A.get('public_market')or{};return{'confirmed_regulators':[A.get('regulator_name','')for A in C if A.get('applicability_status')=='Confirmed'and A.get('regulator_name')],'activities':[A for A in((A.get('sector')or{}).get('financial_activity')or[])+((A.get('sector')or{}).get('activities')or[])if A],'listed':bool(B.get('listed')),'venues':[A for A in B.get('venues')or[]if A]}
def profile_facts(profile):return[A for A in profile_status(profile)['confirmed_regulators']if len(A)>=4]
def lvl(score):A=score;return'critical'if A>=16 else'high'if A>=9 else'medium'if A>=4 else'low'
def _walk(o,path=''):
	A=path
	if isinstance(o,dict):
		for(C,B)in o.items():yield from _walk(B,A+'.'+C)
	elif isinstance(o,list):
		for(D,B)in enumerate(o):yield from _walk(B,'%s[%d]'%(A,D))
	elif isinstance(o,str):yield(A,o)
def _limit_paths(reg):
	C=reg;D=C.get('summary')or{}
	for A in C.get('risks')or[]:
		yield('risks[].name','risk %s.name'%A.get('id'),A.get('name'));yield('risks[].treatment_direction','risk %s.treatment_direction'%A.get('id'),A.get('treatment_direction'))
		for H in A.get('anchors')or[]:yield('risks[].anchors[].clause','risk %s.anchor.clause'%A.get('id'),H.get('clause'))
		I=A.get('critical_detail')or{};yield('risks[].critical_detail.what_happens','risk %s.critical_detail'%A.get('id'),I.get('what_happens'));yield('risks[].critical_detail.why_not_protected','risk %s.critical_detail'%A.get('id'),I.get('why_not_protected'))
	for K in D.get('bottom_line')or[]:yield('summary.bottom_line[]','summary.bottom_line',K)
	yield('summary.deal_one_line','summary.deal_one_line',D.get('deal_one_line'))
	for L in D.get('key_dates')or[]:
		for B in('what','consequence','window','clause'):yield('summary.key_dates[].'+B,'key_dates.'+B,L.get(B))
	for G in C.get('document_defects')or[]:
		for B in('topic','risk_created','proposed_fix','prevails_basis'):yield('document_defects[].'+B,'%s.%s'%(G.get('id'),B),G.get(B))
		for M in G.get('locations')or[]:yield('document_defects[].locations[].quote','%s.quote'%G.get('id'),M.get('quote'))
	for E in C.get('dangerous_combinations')or[]:
		for B in('why_together','breaking_fix','neutralizes'):yield('dangerous_combinations[].'+B,'%s.%s'%(E.get('combo_id'),B),E.get(B))
	for F in D.get('not_checked')or[]:yield('summary.not_checked[].item','not_checked.item',F.get('item'));yield('summary.not_checked[].why','not_checked.why',F.get('why'))
	for H in D.get('assumptions')or[]:yield('summary.assumptions[]','summary.assumptions',H)
	for E in C.get('coverage')or[]:yield('coverage[].note','coverage %s.note'%E.get('lens'),E.get('note'))
	for A in C.get('risks')or[]:yield('risks[].residual.treated_how','risk %s.residual.treated_how'%A.get('id'),(A.get('residual')or{}).get('treated_how'))
	for(J,F)in enumerate((D.get('money_picture')or{}).get('exposures')or[]):yield('summary.money_picture.exposures[].what','money_picture.exposures[%d].what'%J,F.get('what'));yield('summary.money_picture.exposures[].reason','money_picture.exposures[%d].reason'%J,F.get('reason'))
def concessions(state):
	B=[]
	for A in(state or{}).get('deliberate_concessions')or[]:
		if A.get('report_as','accepted_risk')!='accepted_risk'or A.get('reopened_in_round'):continue
		B.append({'clause_ref':A.get('clause_ref')or A.get('clause_id'),'topic':A.get('topic')or A.get('what')or''})
	return B
def deliberate_waivers(state):
	D=state;B={}
	if not D:return B
	for A in D.get('deliberate_concessions')or[]:
		if A.get('report_as','accepted_risk')!='accepted_risk'or A.get('reopened_in_round'):continue
		F=A.get('clause_ref')or A.get('clause_id')
		if F:B[F]=A.get('topic')or A.get('what')or''
	G=reopened_refs(D)
	for E in D.get('clauses')or[]:
		if E.get('clause_id')in G:continue
		for C in E.get('concession_history')or[]:
			if C.get('kind')=='reopen':B.pop(E.get('clause_id'),None)
			elif C.get('who')=='us'and(C.get('deliberate')is True or str(C.get('in_exchange_for')or'').startswith('ויתור מכוון')):B[E.get('clause_id')]=C.get('what')or''
	return B
def reopened_refs(state):return{A.get('clause_ref')or A.get('clause_id'):A.get('reopened_in_round')for A in(state or{}).get('deliberate_concessions')or[]if A.get('reopened_in_round')}
def state_clause_ids(state):A=state;B={A.get('clause_id')for A in(A or{}).get('clauses')or[]if A.get('clause_id')};return B|set(((A or{}).get('numbering_map')or{}).keys())
def numbering_consistent(where,mapped):A=re.findall('\\d+[א-ת]?(?:\\.\\d+[א-ת]?)*',where or'');B=set(re.findall('\\d+[א-ת]?(?:\\.\\d+[א-ת]?)*',mapped or''));return all(A in B for A in A)
_TYPED_SUB=re.compile('^\\s*\\(([a-z]{1,3}|[ivxlc]{1,5}|\\d{1,2}|[א-ת]{1,2})\\)',re.I)
CLAUSE_TEXT_KEYS='current_text','agreed_text','pending_text'
def map_entry_doubt(state,sc,mapped,quote=''):
	A=mapped;A=(A or'').strip()
	if not re.search('\\d',A)or not clause_ref_ok(A):return'הרשומה במפה אינה מספר סעיף (%r)'%A
	B=[str(A.get(B)or'')for A in(state or{}).get('clauses')or[]if A.get('clause_id')==sc for B in CLAUSE_TEXT_KEYS if A.get(B)]
	if any(_TYPED_SUB.match(A)for A in B)and'('not in A:return'הסעיף נפתח בתת-סעיף מוקלד, והרשומה במפה (%s) היא מונה של רשימה'%A
	C=norm(quote or'')
	if C and B and not any(C in norm(A)for A in B):return'הציטוט אינו בטקסט הסעיף %s שבקובץ המצב: הוא מפסקה אחרת'%sc
	return''
def deal_value_hint(deal_dir,state=None):
	I=deal_dir;E=state;F=[]
	if E is not None:F.append(('negotiation_state.json',E))
	for B in DEAL_VALUE_FILES:
		if E is not None and B=='negotiation_state.json':continue
		J=os.path.join(I or'',B)
		if I and os.path.isfile(long_path(J)):
			try:
				with io.open(long_path(J),encoding='utf-8-sig')as L:F.append((B,json.load(L)))
			except(OSError,ValueError):continue
	for(B,K)in F:
		C=str(((K.get('meta')or{}).get('deal_context')or{}).get('estimated_value')or'').strip()
		if C and C not in('לא ידוע','unknown','Unknown')and _VALUE_AMT.search(C):return B,C[:80]
		for(M,G)in _walk(K):
			for D in _VALUE_AMT.finditer(G):
				H=max(0,D.start()-40);A=G[H:D.end()+40]
				if _VALUE_CTX.search(A):
					if H and' 'in A[:D.start()-H]:A=A.split(' ',1)[1]
					if D.end()+40<len(G)and' 'in A[-20:]:A=A.rsplit(' ',1)[0]
					return B,A.strip()[:90]
def money_problem(a,where):
	B=where
	if not isinstance(a,dict)or a.get('value')is None:return[]
	A=[]
	if a.get('source')not in AMOUNT_SOURCES:A.append('%s: סכום בלי מקור מההסכם או מהלקוח (אין אומדן של המודל)'%B)
	if not(a.get('source_ref')or'').strip():A.append('%s: סכום בלי source_ref (הסעיף, או התשובה של הלקוח)'%B)
	if a.get('source')=='contract'and not(a.get('calc')or'').strip():A.append('%s: סכום מההסכם בלי calc (החישוב בשורה אחת, או "כלשון הסעיף")'%B)
	try:float(a.get('value'))
	except(TypeError,ValueError):A.append('%s: value אינו מספר'%B)
	return A
def _num(a):
	try:return float((a or{}).get('value'))
	except(TypeError,ValueError):return
def money_size(x):
	A=x.get('range')or{}
	if A.get('high_unlimited'):return float('inf')
	for B in(_num(A.get('high')),_num(x.get('amount')),_num(A.get('low'))):
		if B is not None:return B
	return-1.
def check_money_picture(reg,idset,err,warn):
	P=idset;A=err;c=reg.get('summary')or{};H=c.get('money_picture')
	if H is None:warn('summary.money_picture','חסר: התמונה הכספית בראש הדוח נבנית רק מסכומים שבסיכונים ומשווי העסקה (מרשם ישן). בהרצה חדשה: עד שלוש החשיפות הגדולות, הביטוח ושווי העסקה');return
	U=H.get('exposures')or[]
	for(K,I)in enumerate(U):
		B='money_picture.exposures[%d]'%K;V=I.get('risk_ids')or[]
		if not V or any(A not in P for A in V):A(B,'risk_ids חסר או לא קיים')
		if not(I.get('what')or'').strip():A(B,'what חובה: החשיפה במילים')
		W,C=I.get('amount')or{},I.get('range')or{}
		for J in money_problem(W,B+'.amount')+money_problem(C.get('low'),B+'.range.low')+money_problem(C.get('high'),B+'.range.high'):A(B,J)
		X=W.get('value')is not None;Y=_num(C.get('low'))is not None or _num(C.get('high'))is not None or bool(C.get('high_unlimited'))
		if X and Y:A(B,'סכום מדויק וטווח יחד: טווח רק כשאין סכום מדויק')
		if not X and not Y and not(I.get('reason')or'').strip():A(B,'בלי סכום, בלי טווח ובלי reason: כשאין סכום מהמסמכים, הסיבה במשפט אחד')
		Z,Q=_num(C.get('low')),_num(C.get('high'))
		if Z is not None and Q is not None and Z>Q:A(B,'קצה תחתון גדול מהעליון')
		if C.get('high_unlimited')and Q is not None:A(B,'high_unlimited יחד עם high')
		d={A for A in((C.get('low')or{}).get('currency'),(C.get('high')or{}).get('currency'))if A}
		if len(d)>1:A(B,'שני קצות הטווח במטבעות שונים')
	a=[money_size(A)for A in U]
	if a!=sorted(a,reverse=True):warn('money_picture.exposures','לא לפי הגודל: בלתי מוגבל ראשון, אחריו הסכום או הקצה העליון')
	L=H.get('insurance')or{}
	for E in('required','held'):
		for J in money_problem(L.get(E),'money_picture.insurance.'+E):A('money_picture.insurance',J)
	if(L.get('held')or{}).get('value')is not None and L['held'].get('source')=='contract':A('money_picture.insurance.held','הכיסוי שבידינו אינו נלמד מההסכם: מסמך מבטח או מסירת הלקוח (client)')
	M=H.get('caps')or[]
	for(K,D)in enumerate(M):
		for J in money_problem(D,'money_picture.caps[%d]'%K):A('money_picture.caps',J)
		if D.get('unlimited')and D.get('value')is not None:A('money_picture.caps[%d]'%K,'unlimited יחד עם value')
	R=H.get('cross_checks')or{}
	for E in('insurance_vs_cap','cap_aggregation'):
		for F in R.get(E)or[]:
			if isinstance(F,str)and F not in P and re.match('^\\s*[A-Z]+-\\d+\\s*[:,\\s]',F):A('money_picture.cross_checks.'+E,'מזהה סיכון בלבד, בלי טקסט אחריו: %r'%F[:40])
			elif F not in P:A('money_picture.cross_checks.'+E,'risk id לא קיים: %r'%str(F)[:40])
	S=L.get('required')or{};G=_num(S)
	for D in M:
		N=_num(D);e=not(S.get('currency')and D.get('currency'))or S.get('currency')==D.get('currency');O=None
		if G is not None and D.get('unlimited'):O='ביטוח בסך %s מול אחריות בלתי מוגבלת'%format(G,',.0f')
		elif G and N and e and max(G,N)/min(G,N)>=INS_CAP_RATIO:O='ביטוח בסך %s מול תקרה של %s'%(format(G,',.0f'),format(N,',.0f'))
		if O and not R.get('insurance_vs_cap'):A('money_picture.cross_checks.insurance_vs_cap','%s (%s): פער של פי %d ומעלה הוא ממצא; נדרש סיכון או צירוף, ומספרו כאן'%(O,D.get('clause')or D.get('document')or'',INS_CAP_RATIO));break
	b={A.get('document')for A in M if A.get('document')};T=[A for A in M if A.get('imported_from')]
	if(len(b)>1 or T)and not R.get('cap_aggregation'):A('money_picture.cross_checks.cap_aggregation','תקרות ב-%s%s: היחס ביניהן (נצברות או תקרה אחת) הוא ממצא; נדרש סיכון או צירוף, ומספרו כאן'%(', '.join(sorted(b)),' (מיובאת מ-%s)'%T[0].get('imported_from')if T else''))
def validate(reg,corpus=None,deal_dir=None,state=None,profile=None,playbook_status=None,known_amendments=None,approved_sources=None,case_law_connector=None):
	y=playbook_status;e=deal_dir;L=state;I=reg;AE,AF=[],[];I={A:B for(A,B)in(I or{}).items()if A!='pre_send_fixes'}
	def A(where,msg):AE.append('%s: %s'%(where,msg))
	def R(where,msg):AF.append('%s: %s'%(where,msg))
	Al,Am=approved_domains(approved_sources)
	if not Am and((I or{}).get('research')or{}).get('sources_checked'):A('research','קובץ המקורות המאושרים (מקורות-מאושרים.json) לא נקרא: אין רשימת נפילה, ולכן אף מקור אינו מאושר. לשמור את הקובץ ולהעביר --approved-sources')
	H=I.get('meta')or{};Z=I.get('summary')or{};h=H.get('source_version')or{};V=h.get('text_status')
	for F in H:
		if F not in META_KEYS:A('meta','שדה לא מוכר: %s'%F)
	for F in('company','scope','generated_at','source_version','counterparty'):
		if not H.get(F):A('meta','חסר שדה חובה %s'%F)
	if'annexes_reviewed'in I:A('root','annexes_reviewed בשורש המרשם')
	if H.get('scope')=='deal'and not re.match('^deal_[^_]+_\\d{4}-\\d{2}-\\d{2}$',H.get('transaction_id')or''):A('meta.transaction_id','במצב deal נדרש deal_<slug>_<YYYY-MM-DD> מקובץ המצב')
	if V not in TEXT_STATUS:A('meta.source_version','text_status לא חוקי')
	z=(H.get('counterparty')or{}).get('name','')or''
	if not z.strip()or re.search('\\[[^\\]]*\\]|להשלים',z):A('meta.counterparty.name','שם ריק או מציין מקום')
	i=I.get('entity_research')or{}
	if'(השם לא מולא בהסכם)'in z and not i.get('missing_identifiers'):A('meta.counterparty.name','"השם לא מולא בהסכם" בלי missing_identifiers')
	q=H.get('branding')or{}
	if set(q)-{'logo','theme'}:A('meta.branding','שדות נוספים תחת branding')
	if'theme'in q:
		from common.branding import valid_tokens as An
		if not An(q['theme']):A('meta.branding.theme','צבעי המותג: שמונה ערכי #RRGGBB מהפרופיל (branding.theme.tokens), כמו שהם')
	A0=q.get('logo')or''
	if A0 and(not A0.startswith('data:image/')or len(A0)*3/4>153600):A('meta.branding.logo','לא תמונה מוטמעת, או מעל 150 קילובייט')
	if not H.get('prepared_for_counsel'):R('meta','אין שם עורך דין: הדוח יציג אזהרת חיסיון')
	AG=H.get('position')=='הדדי'or bool(H.get('mutual_primary_role'))
	if H.get('position')=='הדדי'and not H.get('mutual_primary_role'):A('meta','הסכם הדדי בלי mutual_primary_role')
	if H.get('benchmark_status')not in(None,'approved','draft','none'):A('meta.benchmark_status','ערך לא חוקי')
	a=H.get('deal_value')or{}
	if a.get('amount')is not None:
		for G in money_problem({'value':a.get('amount'),'source':a.get('source'),'source_ref':a.get('source_ref'),'calc':a.get('calc')or'כלשון הסעיף'},'meta.deal_value'):A('meta.deal_value',G)
		if(a.get('basis')or'').strip()in('','לא ידוע','unknown'):A('meta.deal_value','סכום בלי basis (שנתי או כולל)')
	else:
		if a.get('source')in AMOUNT_SOURCES:R('meta.deal_value','מקור %s בלי סכום'%a.get('source'))
		AH=deal_value_hint(e,L)if e or L is not None else None
		if AH:R('meta.deal_value','ריק, אבל בתיקיית העסקה יש נתון על התמורה (%s: "%s"). לגזור ממנו, עם ציון המקור (source: client או contract, ו-source_ref); השאלה רק כשאין מקור'%AH)
	if y is not None and H.get('playbook_ref'):
		Ao='approved'if y.get('playbook_status')=='Approved'else'draft'
		if H.get('benchmark_status')!=Ao:A('meta.benchmark_status','%s, אבל המעמד הנגזר של הפלייבוק הוא %s (playbook/status.py)'%(H.get('benchmark_status'),y.get('playbook_status')))
	AI={A.get('title'):A for A in I.get('documents')or[]};AJ={}
	for M in corpus or[]:Ap=' '.join(B['text_accept_all']for A in M['parts'].values()for B in A);Aq=' '.join(B['text_reject_all']for A in M['parts'].values()for B in A);AJ[M['file']]=norm(Ap),norm(Aq)
	def A1(a,where):
		B=where
		if a.get('document')not in AI:A(B,'עוגן למסמך שאינו ב-documents: %r'%a.get('document'));return
		if re.search('\\.json|פלייבוק|פרופיל|negotiation_state',a.get('document')or''):A(B,'עוגן לקובץ פנימי')
		if corpus is None:return
		E=AI[a.get('document')];D=AJ.get(E.get('file'))
		if not D:A(B,'אין טקסט מקור למסמך %s'%E.get('file'));return
		C=norm(a.get('quote'))
		if not C:A(B,'ציטוט ריק');return
		if E.get('role')=='our_response':F=C in D[0]
		else:F=C in D[0]or C in D[1]
		if not F:A(B,'הציטוט לא נמצא מילה במילה: %s'%C[:60])
	Q=I.get('risks')or[];AK=[A.get('id')for A in Q];l=set(AK)
	if len(l)!=len(AK):A('risks','מזהים כפולים')
	if sorted(A.get('risk_no')or 0 for A in Q)!=list(range(1,len(Q)+1)):A('risks','risk_no אינו רציף מ-1')
	AL={'critical':4,'high':3,'medium':2,'low':1};AM=sorted(Q,key=lambda r:r.get('risk_no')or 0)
	def A2(r):
		A=r.get('states')
		if isinstance(A,dict):
			B=A.get('agreed')or{}
			if B.get('score')is not None and B.get('acceptance_evidence')and B.get('effectiveness')in('effective','partial','not_effective'):return B['score']
			if(A.get('current')or{}).get('score')is not None:return A['current']['score']
			return(r.get('inherent')or{}).get('score')or 0
		return(r.get('residual')or{}).get('score')or(r.get('inherent')or{}).get('score')or 0
	for(J,W)in zip(AM,AM[1:]):
		if(AL.get(W.get('severity_level'),0),A2(W))>(AL.get(J.get('severity_level'),0),A2(J)):A('risks','risk_no %s לפני %s אינו לפי חומרה'%(J.get('risk_no'),W.get('risk_no')))
	A3,Ar={},0
	for C in Q:
		B='risk %s'%C.get('id')
		for F in C:
			if F in FORBIDDEN_RISK:A(B,'שדה שיצא מהסכמה: %s'%F)
			elif F not in RISK_KEYS:A(B,'שדה לא מוכר: %s'%F)
		for F in('estimated_amount','ratio_to_deal_value'):
			if F in(C.get('exposure')or{}):A(B,'שדה אומדן שיצא: %s'%F)
		if C.get('kind')not in KINDS:A(B,'kind לא חוקי')
		if C.get('primary_lens')not in LENS8:A(B,'primary_lens לא חוקי')
		for S in C.get('lens')or[]:
			if S not in LENS8:A(B,'lens לא חוקי %s'%S)
		if len((C.get('name')or'').split())>16:A(B,'שם ארוך מ-15 מילים')
		f,b=C.get('inherent')or{},C.get('residual')or{}
		for r in(f,b):
			if r and r.get('score')!=(r.get('severity')or 0)*(r.get('likelihood')or 0):A(B,'ניקוד אינו מכפלה')
		A4=lvl(A2(C))
		if C.get('severity_level')is not None and C.get('severity_level')!=A4:A(B,'severity_level לא נגזר נכון (%s במקום %s)'%(C.get('severity_level'),A4))
		if A4=='critical':
			Ar+=1;m=C.get('critical_detail')or{}
			if not m.get('what_happens')or not m.get('why_not_protected'):A(B,'קריטי בלי critical_detail')
		s=C.get('anchors')or[]
		if not s and C.get('certainty')!='hypothesis':A(B,'סיכון בלי עוגן חייב להיות השערה')
		for(c,J)in enumerate(s):
			A1(J,'%s anchor %d'%(B,c))
			if J.get('clause')and not clause_ref_ok(J['clause']):A('%s anchor %d'%(B,c),'הפניה לסעיף שלא בתבנית: %r'%J['clause'])
		if s:
			d=s[0].get('clause'),C.get('primary_lens')
			if d in A3:A(B,'אותו עוגן ראשון ואותה עדשה כמו %s'%A3[d])
			A3[d]=C.get('id')
		if AG and C.get('side')not in SIDES:A(B,'side חובה בהסכם הדדי')
		if not AG and C.get('side')not in(None,''):A(B,'side רק בהסכם הדדי')
		for D in C.get('controls')or[]:
			if D.get('basis')=='proposed_text'and V not in OUR_TEXT_STATUS:A(B,'proposed_text בנוסח שאינו התגובה שלנו או הטיוטה שלנו')
		if C.get('kind')=='hidden_text'and f.get('score')is not None:
			A5=(C.get('hidden_text')or{}).get('asks_for')
			if f['score']<(16 if A5 in HIDDEN_ASKS else 9):A(B,'טקסט מוסתר: הגולמי %s לפחות (%s)'%('קריטי'if A5 in HIDDEN_ASKS else'גבוה','מבקש לאשר תנאים או להעביר מידע'if A5 in HIDDEN_ASKS else'r1-intake.md, טקסט מוסתר'))
		AN=[A for A in C.get('controls')or[]if A.get('in_place')is not False]
		if b.get('treated'):
			if V not in TREATED_STATUS:A(B,'"טופל" רק בנוסח שלנו או בנוסח מוסכם; בטיוטה של הצד השני הסיכון עוד לא טופל')
			if not AN:A(B,'"טופל" בלי בקרה קיימת שמתעדת את הטיפול (controls)')
			if not(b.get('treated_how')or'').strip():A(B,'"טופל" בלי treated_how: מה נעשה ובאיזה סעיף, במשפט אחד')
			if f.get('score')is not None and(b.get('score')or 0)>=f['score']:A(B,'"טופל", אבל הדירוג השיורי אינו נמוך מהגולמי')
			if(b.get('score')or 0)>TREATED_MAX_SCORE:A(B,'"טופל" בדרגה שיורית %s: מה שטופל במסמך הוא בינוני לכל היותר; אם החשיפה נשארת, היא אינה "טופל" (controls ו-residual בלבד)'%{'critical':'קריטי','high':'גבוה'}.get(lvl(b.get('score')or 0),lvl(b.get('score')or 0)))
		elif V in TREATED_STATUS and f.get('score')is not None and b.get('score')==f.get('score')and any(DELETED_RE.search(A.get('description')or'')for A in AN):R(B,'בקרה קיימת אומרת שהמקור נמחק בנוסח שנבדק, אבל הדירוג השיורי זהה לגולמי (%s). סיכון שטופל בתוך המסמך: residual נמוך, treated: true ו-treated_how (r3-scoring.md, סיכון גולמי וסיכון שיורי)'%{'critical':'קריטי','high':'גבוה','medium':'בינוני','low':'נמוך'}.get(C.get('severity_level'),C.get('severity_level')))
		N=(C.get('exposure')or{}).get('amount')or{}
		if N.get('value')is not None:
			if N.get('source')not in('contract','client'):A(B,'סכום בלי מקור מההסכם או מהלקוח')
			if N.get('source')=='contract'and not(N.get('source_ref')and N.get('calc')):A(B,'סכום מההסכם בלי סעיף וחישוב')
		if C.get('playbook_flag')not in('none','red_line','deviates_from_benchmark'):A(B,'playbook_flag לא חוקי')
		if C.get('playbook_flag')=='red_line'and H.get('benchmark_status')!='approved':A(B,'playbook_flag red_line ("מעבר למה שאנחנו מקבלים") רק מול פלייבוק מאושר')
		if C.get('regulatory_basis')not in(None,'law_verified','law_claimed','commercial'):A(B,'regulatory_basis לא חוקי')
		K=C.get('decision')or{}
		for F in K:
			if F not in DECISION_KEYS:A(B,'שדה לא מוכר ב-decision: %s (אין שדות אישור: החלטה 1, הכרעת המשתמש היא ההחלטה)'%F)
		if K and K.get('status')not in(None,'open','mitigating','accepted'):A(B,'decision.status לא חוקי: %s (אין מצב "ממתין לאישור")'%K.get('status'))
		if K.get('basis')=='deliberate_waiver'and K.get('status')!='accepted':A(B,'ויתור מכוון חייב decision.status "accepted"')
		if K.get('basis')=='deliberate_waiver':
			for T in[K.get('state_clause_id')]+list(K.get('state_clause_ids')or[]):
				if T and RULE_ID_RE.match(str(T)):A(B,'decision.state_clause_id %s הוא מזהה כלל; נדרש מזהה הסעיף בקובץ המצב'%T)
		U=C.get('concession_refs')
		if U is not None:
			if not isinstance(U,list)or not U or not all(isinstance(A,str)and A.strip()for A in U):A(B,'concession_refs: רשימה של מזהי סעיפים מקובץ המצב (clause_ref של כל ויתור)');U=[]
			if K.get('basis')!='deliberate_waiver':A(B,'concession_refs רק בסיכון שהתקבל בוויתור מכוון (decision.basis: deliberate_waiver)')
			if len(set(U))>1 and C.get('severity_level')in('critical','high'):A(B,'ויתור מכוון קריטי או גבוה נשאר סיכון נפרד; האיחוד רק לבינוניים ולנמוכים באותה עדשה')
			for T in U:
				if RULE_ID_RE.match(T):A(B,'concession_refs: %s הוא מזהה כלל; נדרש מזהה הסעיף בקובץ המצב'%T)
			if K.get('state_clause_id')and U and K['state_clause_id']not in U:A(B,'decision.state_clause_id %s אינו ב-concession_refs'%K['state_clause_id'])
			As={A.get('state_clause_id')for A in C.get('anchors')or[]};AO=sorted({A for A in U if A not in As})
			if len(set(U))>1 and AO:A(B,'concession_refs בלי עוגן משלו (anchors[].state_clause_id): %s. לכל ויתור עוגן עם הסעיף והציטוט, כדי שהסעיף יופיע ברשימה בפרק 1'%', '.join(AO))
		if C.get('created_by_response')and V not in OUR_TEXT_STATUS:A(B,'created_by_response רק בנוסח שאנחנו מציעים (התגובה או הטיוטה שלנו)')
		At={A.get('id')for A in(I.get('research')or{}).get('sources_checked')or[]}
		for AP in C.get('external_source_ids')or[]:
			if AP not in At:A(B,'external_source_id לא קיים: %s'%AP)
		if C.get('certainty')=='fact':R(B,'certainty fact: לוודא שזה רק תיאור הסעיף')
	Au=list(_walk({A:B for(A,B)in I.items()if A!='meta'}))
	for C in Q:
		j=C.get('name')or''
		for(G,E)in Au:
			if j and j in E and not G.endswith('.name'):A('risk %s'%C.get('id'),'השם חוזר כלשונו בשדה %s'%G);break
	Av={A.get('lens'):A for A in I.get('coverage')or[]}
	for S in LENS8:
		D=Av.get(S)
		if not D:A('coverage','עדשה %s לא דווחה'%S);continue
		if D.get('status')not in('findings','none_found','not_checked'):A('coverage','status לא חוקי ב-%s'%S)
		if D.get('status')in('none_found','not_checked')and not D.get('note'):A('coverage','חסר note ב-%s'%S)
		AQ=sorted(A.get('id')for A in Q if A.get('primary_lens')==S)
		if sorted(D.get('risk_ids')or[])!=AQ:A('coverage','risk_ids ב-%s אינם תואמים לעדשה הראשית'%S)
		if D.get('status')=='findings'and not AQ:A('coverage','findings בלי סיכונים ב-%s'%S)
	for D in I.get('coverage')or[]:
		if D.get('lens')not in LENS8:A('coverage','עדשה לא מוכרת %s'%D.get('lens'))
	if Z.get('sign_as_is')not in('yes','with_fixes','no'):A('summary','sign_as_is לא חוקי')
	A6=Z.get('bottom_line')or[]
	if not 3<=len(A6)<=4:A('summary.bottom_line','צריך 3 עד 4 משפטים')
	if any('אפשר לחתום'in A for A in A6):R('summary.bottom_line','חוזר על התווית')
	A7=Z.get('key_dates')or[]
	if len(A7)>MAX_KEY_DATES:A('summary.key_dates','יותר מ-%d'%MAX_KEY_DATES)
	for F in A7:
		if F.get('date')is None:
			if not F.get('window'):A('summary.key_dates','date ריק בלי window')
		elif not re.match('^\\d{4}-\\d{2}-\\d{2}$',str(F['date'])):A('summary.key_dates','date לא ISO')
		if F.get('clause')and not clause_ref_ok(F['clause']):A('summary.key_dates','הפניה לסעיף שלא בתבנית: %r'%F['clause'])
	AR=deliberate_waivers(L);AS=reopened_refs(L);AT=state_clause_ids(L);AU=(L or{}).get('numbering_map')or{};Aw=bool(h.get('user_requested'))and V in('counterparty_draft','their_draft')
	if L is not None and L.get('text_status')and not Aw:
		if{'their_draft':'counterparty_draft'}.get(V,V)!={'their_draft':'counterparty_draft'}.get(L['text_status'],L['text_status']):
			if h.get('file')or h.get('title'):R('meta.source_version.text_status','נסרק %s (%s), והנוסח האחרון בקובץ המצב הוא %s: שורת הכותרת אומרת איזה נוסח נבדק'%(V,h.get('title')or h.get('file'),L['text_status']))
			else:A('meta.source_version.text_status','%s, אבל בקובץ המצב text_status הוא %s, ולא צוין איזה מסמך נסרק (source_version.file או title)'%(V,L['text_status']))
	A8=((L or{}).get('meta')or{}).get('paper_type')or(L or{}).get('paper_type')
	if A8 and H.get('paper_type')!=A8:A('meta.paper_type','בקובץ המצב paper_type הוא %s, ובמרשם %s: להעתיק אותו כמו שהוא (במכרז אחרי זכייה התנאים ברובם אינם פתוחים למשא ומתן, והדוח אומר זאת)'%(A8,H.get('paper_type')))
	def AV(ref):return' (הוויתור נפתח מחדש בסבב %s: הסיכון אינו "התקבל")'%AS[ref]if ref in AS else''
	if L is not None:
		AW=set()
		for C in Q:
			K=C.get('decision')or{}
			if K.get('basis')=='deliberate_waiver':AW|={A for A in[K.get('state_clause_id')]+list(K.get('state_clause_ids')or[])+[A for A in C.get('concession_refs')or[]if isinstance(A,str)]if A}
		for D in concessions(L):
			k=D['clause_ref']
			if not k:A('state.deliberate_concessions','ויתור בלי clause_ref: %s'%D['topic']);continue
			if k not in AT:A('state.deliberate_concessions','clause_ref %s (%s) אינו מזהה סעיף בקובץ המצב%s'%(k,D['topic'],' (זה מזהה כלל)'if RULE_ID_RE.match(str(k))else''))
			if k not in AW:A('state.deliberate_concessions','הוויתור המכוון %s (%s) אינו מופיע כסיכון שהתקבל'%(k,D['topic']))
		for C in Q:
			for J in C.get('anchors')or[]:
				g=J.get('state_clause_id')
				if g and g not in AT:A('risk %s'%C.get('id'),'state_clause_id %s אינו בקובץ המצב'%g)
				j=AU.get(g)if g else None
				if g in AU and J.get('clause')and not numbering_consistent(J['clause'],j):A9=map_entry_doubt(L,g,j,J.get('quote'));(R if A9 else A)('risk %s'%C.get('id'),'clause %r אינו תואם ל-numbering_map (%s)%s'%(J['clause'],j,': %s. state_clause_id נשאר; המפה של הנושא ונותן טעונה תיקון'%A9 if A9 else''))
			K=C.get('decision')or{}
			for Y in[K.get('state_clause_id')]+list(K.get('state_clause_ids')or[]):
				if Y and Y not in AR:A('risk %s'%C.get('id'),'decision.state_clause_id %s אינו ויתור מכוון בקובץ המצב%s'%(Y,AV(Y)))
			for Y in C.get('concession_refs')or[]:
				if isinstance(Y,str)and Y not in AR:A('risk %s'%C.get('id'),'concession_refs: %s אינו ויתור מכוון בקובץ המצב%s'%(Y,AV(Y)))
		AX={}
		for C in Q:
			if(C.get('decision')or{}).get('basis')=='deliberate_waiver'and C.get('severity_level')not in('critical','high'):AX.setdefault(C.get('primary_lens'),[]).append(C.get('id'))
		for(S,AY)in sorted(AX.items(),key=lambda x:str(x[0])):
			if len(AY)>1:R('risks','ויתורים מכוונים בעדשה %s בכמה סיכונים (%s): לאחד לסיכון "התקבל" אחד, עם concession_refs של כל הוויתורים (r3-scoring.md, ויתורים מכוונים)'%(S,', '.join(AY)))
		Ax=L.get('playbook_resolution')or(L.get('playbook_status')or{}).get('playbook_resolution')or{}
		if Ax.get('activation_ok')is False:
			for C in Q:
				if C.get('playbook_flag')not in(None,'none'):A('risk %s'%C.get('id'),'סימון פלייבוק, אבל בקובץ המצב activation_ok הוא false')
	AZ=I.get('dangerous_combinations')or[]
	for D in AZ:
		B=D.get('combo_id')
		if D.get('type')not in('combination','chain','neutralizer'):A(B,'type לא חוקי')
		if not D.get('clauses')or not D.get('breaking_fix')or not D.get('why_together'):A(B,'clauses, why_together ו-breaking_fix חובה')
		if D.get('type')=='neutralizer'and not D.get('neutralizes'):A(B,'neutralizes חובה בנטרול')
		if'why_dangerous_together'in D:A(B,'שדה ישן why_dangerous_together')
		if any(A not in l for A in D.get('risk_ids')or[]):A(B,'risk_ids לא קיים')
		for T in D.get('clauses')or[]:
			if not clause_ref_ok(str(T)):A(B,'הפניה לסעיף שלא בתבנית: %r'%T)
		for(c,J)in enumerate(D.get('anchors')or[]):A1(J,'%s anchor %d'%(B,c))
	for M in I.get('document_defects')or[]:
		B=M.get('id')
		if M.get('type')not in DEF_TYPES:A(B,'type לא חוקי')
		if M.get('prevails')not in('first','second','none'):A(B,'prevails לא חוקי')
		if M.get('prevails')in('first','second')and not M.get('prevails_basis'):A(B,'prevails_basis חובה כשיש הכרעה')
		if M.get('type')=='contradiction'and len([A for A in M.get('locations')or[]if A.get('quote')])<2:A(B,'סתירה בלי שני מיקומים עם ציטוט')
		for(c,Aa)in enumerate(M.get('locations')or[]):
			if Aa.get('quote'):A1(Aa,'%s loc %d'%(B,c))
		if any(A not in l for A in M.get('risk_ids')or[]):A(B,'risk_ids לא קיים')
	check_money_picture(I,l,A,R)
	if not case_law_connector:
		for(t,E)in _walk(I):
			if SKIP_TEXT.search(t)or t in QUOTED_USER_TEXT or CASE_LAW_EXEMPT.search(t):continue
			Ab=case_law_hits(E)
			if Ab:A(t,'אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1): %s. פסיקה רק ממה שמחבר סגור החזיר; בלעדיו "טעון בדיקה משפטית"'%'; '.join(Ab[:2]))
	for(d,Ay,AA)in _limit_paths(I):
		if AA and len(AA)>LIMITS[d]:A(Ay,'ארוך מ-%d תווים (%d): לקצר לפני הבנייה'%(LIMITS[d],len(AA)))
	O=I.get('research')or{}
	if O.get('mode')not in('not_permitted','approved_sources','documents_only'):A('research','mode לא חוקי')
	if O.get('mode')=='approved_sources':R('research.mode','ערך ישן: אין אימות רגולטורי ברשת, ובהרצה חדשה הערך הוא not_permitted')
	elif O.get('mode')in('not_permitted','documents_only'):
		for F in('search_log','raw_copies'):
			if O.get(F):A('research.'+F,'יציאה לרשת במרשם שאינו מתיר אותה (mode %s). דרישה שלא אומתה במסמכים או בפלייבוק מסומנת "טעון בדיקה משפטית"'%O.get('mode'))
		for E in O.get('sources_checked')or[]:
			if E.get('origin')not in SOURCE_ORIGINS:A(E.get('id')or'research.sources_checked','מקור שנבדק ברשת במרשם שאינו מתיר אותה (mode %s): רק מקור מהפלייבוק או מהמסמכים (origin: playbook | documents)'%O.get('mode'))
	Az={A.get('source_id'):A for A in O.get('confidence')or[]};A_={A.get('id')for A in O.get('sources_checked')or[]if A.get('origin')in SOURCE_ORIGINS}
	for D in O.get('confidence')or[]:
		if D.get('label')not in('high','medium'):A('research.confidence','תווית לא חוקית')
		if D.get('label')=='high'and D.get('source_id')in A_:A('research.confidence','ודאות גבוהה למקור שלא נפתח בהרצה (%s): בינונית, עם הסיבה'%D.get('source_id'))
		if D.get('label')=='medium'and not D.get('why'):A('research.confidence','ודאות בינונית בלי why')
	Ac={}
	for P in O.get('raw_copies')or[]:
		for F in('final_url','typed_url'):
			if P.get(F):
				Ac[P[F]]=P
				if has_secret(P[F]):A('research.raw_copies','כתובת עם טוקן או חתימה: %s'%F)
	for E in O.get('sources_checked')or[]:
		B=E.get('id')or'?'
		for F in('source','url','date'):
			if not E.get(F):A(B,'חסר %s'%F)
		B0=re.sub('^https?://([^/:]+).*$','\\1',E.get('url')or'').lower()
		if not domain_ok(E.get('url')or'',Al):A(B,'דומיין או נתיב שאינו ברשימה המורשית: %s'%B0)
		if has_secret(E.get('url')or''):A(B,'כתובת עם טוקן או חתימה')
		for Ad in('corroborations','verification','single_source_reason','signal','quotes'):
			if Ad in E:A(B,'שדה אימות או אות שיצא: %s'%Ad)
		AB=E.get('version_date')
		for N in load_amendments(known_amendments):
			if N.get('topic')and not N['topic'].search((E.get('subject')or'')+' '+(E.get('taken')or'')):continue
			if N.get('exclude')and N['exclude'].search(E.get('source')or''):continue
			if AB and N['match'].search((E.get('source')or'')+' '+(E.get('subject')or''))and AB<N['in_force']:
				D=Az.get(E.get('id'))or{}
				if D.get('label')!='medium'or N['name']not in(D.get('why')or''):A(B,'נוסח מ-%s קודם ל%s (בתוקף מ-%s): ודאות בינונית עם הסיבה, ופרק 5'%(AB,N['name'],N['in_force']))
				if'אומת'in(E.get('taken')or'')+(E.get('finding')or''):A(B,'"אומת" על נוסח שקודם ל%s'%N['name'])
		if E.get('origin')not in(None,)+SOURCE_ORIGINS:A(B,'origin לא חוקי (playbook | documents)')
		if e and E.get('origin')not in SOURCE_ORIGINS:
			P=Ac.get(E.get('url'))
			if not P:A(B,'אין עותק גולמי');continue
			Ae=long_path(os.path.join(e,P.get('file')or''))
			if not os.path.exists(Ae):A(B,'העותק הגולמי לא נמצא');continue
			with open(Ae,'rb')as AC:W=AC.read()
			if hashlib.sha256(W).hexdigest()!=P.get('sha256'):A(B,'הגיבוב אינו תואם')
			if P.get('stored')=='excerpt_window'and not(P.get('full_sha256')and P.get('full_size_bytes')):A(B,'חלון מתוך מסמך גדול בלי full_sha256 ו-full_size_bytes של המסמך המלא')
			if E.get('excerpt'):
				u=None
				if P.get('text_file'):
					Af=long_path(os.path.join(e,P['text_file']))
					if not os.path.exists(Af):A(B,'text_file לא נמצא')
					else:
						with open(Af,'rb')as AC:Ag=AC.read()
						if P.get('text_sha256')and hashlib.sha256(Ag).hexdigest()!=P['text_sha256']:A(B,'הגיבוב של text_file אינו תואם')
						u=Ag.decode('utf-8','replace')
				else:
					try:u=page_text(W)
					except PdfTextUnavailable as B1:A(B,'אין שכבת טקסט לעותק ה-PDF (%s): לשמור text_file לצדו'%B1)
				if u is not None and not excerpt_in(E['excerpt'],u):A(B,'הקטע המילולי לא נמצא בעותק הגולמי')
	for(c,Ah)in enumerate(O.get('search_log')or[]):
		AD=Ah.get('user_agent')
		if AD is not None and ua_problem(AD):A('search_log[%d]'%c,ua_problem(AD))
		n=client_detail_in_query(Ah.get('query')or'',[H.get('company')]if H.get('company')else())
		if n:A('search_log','פרט של הלקוח או מספר בשאילתה (%s)'%n[:20])
	if len(O.get('search_log')or[])>10*max(1,len(O.get('question')or[])):A('search_log','יותר מעשר שאילתות לשאלה')
	if profile:
		B2=profile_facts(profile)
		for J in Z.get('assumptions')or[]:
			n=[A for A in B2 if A in J]
			if n:A('summary.assumptions','הנחה על עובדה שהפרופיל קובע (%s): מה שבפרופיל אינו הנחה לאישור'%', '.join(n))
	if i.get('status')not in(None,'not_requested','requested','done'):A('entity_research','status לא חוקי')
	for T in(i.get('risks_up')or[])+(i.get('risks_down')or[]):
		if T not in l:A('entity_research','risk id לא קיים %s'%T)
	if i.get('status')=='done'and e:
		Ai=i.get('report_file')
		if not Ai or not os.path.exists(long_path(os.path.join(e,Ai))):A('entity_research','report_file חסר')
	B3=str(H.get('display_language')or'he').strip().lower()[:2]in('he','iw','עב')
	for(G,E)in _walk(I):
		if G.startswith('.meta.branding')or G in QUOTED_USER_TEXT:continue
		for Aj in APPROVAL_PHRASES:
			if _term(Aj).search(E):A(G,'נוסח של שרשרת אישורים: %s (החלטה 1: סיכון שהתקבל הוא הכרעת המשתמש)'%Aj)
		d=re.sub('\\[\\d+\\]$','',G).rsplit('.',1)[-1]
		if TS_KEY.search(d)and E and'T'in E and not ISO_TS.match(E):A(G,'חותמת זמן בלי שניות או בלי היסט: %s (ISO 8601 מלא, למשל 2026-10-14T17:14:00+03:00)'%E)
		if'—'in E or'–'in E:
			if not(G.endswith('.quote')or G.endswith('.excerpt')):A(G,'מקף ארוך')
		if SKIP_TEXT.search(G)or G.endswith('.quote'):continue
		for W in BLOCKED_PHRASES:
			if W in ADVICE_ONLY and not ADVICE_PATH.search(G):continue
			if _term(W).search(E)and not G.startswith('.meta.playbook_ref'):A(G,'ביטוי חסום: %s'%W)
		B4=bool(DOC_NAME_PATH.search(G));o=next((A for A in CODE_RE.finditer(E)if not(B4 and ROUND_RE.fullmatch(A.group(0)))),None)or B3 and CURRENCY_CODE_RE.search(E)
		if o:A(G,'קוד פנימי או קוד מטבע בטקסט מוצג: %s'%o.group(0))
	v=set();Ak=(H.get('deal_value')or{}).get('amount')
	if Ak is not None:v.add(int(Ak))
	for C in Q:
		w=((C.get('exposure')or{}).get('amount')or{}).get('value')
		if w is not None:v.add(int(w))
	p=Z.get('money_picture')or{}
	for J in[A.get('amount')for A in p.get('exposures')or[]]+[(A.get('range')or{}).get(B)for A in p.get('exposures')or[]for B in('low','high')]+[(p.get('insurance')or{}).get(A)for A in('required','held')]+list(p.get('caps')or[]):
		if _num(J)is not None:v.add(int(_num(J)))
	for(G,E)in _walk(I):
		if SKIP_TEXT.search(G)or G.endswith('.quote')or'.research'in G:continue
		for o in re.finditer('(\\d{1,3}(?:,\\d{3})+|\\d{4,})\\s*ש"ח',E):
			w=int(o.group(1).replace(',',''))
			if w not in v:A(G,'סכום בטקסט שאינו במרשם: %s'%o.group(0))
	X=[]
	for C in Q:
		X+=[C.get('name')or'',C.get('treatment_direction')or'']
		if C.get('anchors'):X.append((C['anchors'][0].get('quote')or'')[:90])
		if C.get('severity_level')=='critical':m=C.get('critical_detail')or{};X+=[m.get('what_happens')or'',m.get('why_not_protected')or'']
	for M in I.get('document_defects')or[]:X+=[M.get('topic')or'',M.get('risk_created')or'',M.get('proposed_fix')or'',M.get('prevails_basis')or'']+[A.get('quote')or''for A in M.get('locations')or[]]
	for D in AZ:X+=[D.get('why_together')or'',D.get('breaking_fix')or'',D.get('neutralizes')or'']
	X+=A6+[Z.get('deal_one_line')or'']+list(Z.get('assumptions')or[]);X+=[(A.get('what')or'')+' '+(A.get('consequence')or'')for A in A7];X+=[A.get('item')or''for A in Z.get('not_checked')or[]];X+=[(A.get('what')or'')+' '+(A.get('reason')or'')for A in p.get('exposures')or[]];x=len(' '.join(X).split())
	if x>WORDS_FAIL:A('words','גוף הדוח %d מילים, מעל %d'%(x,WORDS_FAIL))
	elif x>WORDS_WARN:R('words','גוף הדוח %d מילים'%x)
	return AE,AF
BLOCKING_MATCH='registration_no','name_exact','alias','name_only'
def validate_entity_report(rep,approved_sources=None,purpose=ENTITY_PURPOSE,case_law_connector=None):
	S=approved_sources;K=purpose;C=rep;B=[];c,d=approved_domains(S,K)
	if not d and C.get('sources'):B.append('sources: קובץ המקורות המאושרים לא נקרא: אין רשימת נפילה, ולכן אף מקור רשמי אינו מאושר')
	e=C.get('meta')or{};T=((e.get('counterparty')or{}).get('country')or'').upper()
	for(A,F)in enumerate(C.get('confidence')or[]):
		if F.get('label')not in('high','medium'):B.append('confidence[%d]: תווית לא חוקית'%A)
		if not(F.get('why')or'').strip():B.append('confidence[%d]: why חובה, גם בוודאות גבוהה'%A)
	for(A,D)in enumerate(C.get('red_flags')or[]):
		L=D.get('match_on')
		if D.get('blocking')and L not in BLOCKING_MATCH:B.append('red_flags[%d]: חוסם רק בהתאמה (מספר רישום, שם זהה או כינוי רשמי), לא %r'%(A,L))
		if L=='near'and D.get('blocking'):B.append('red_flags[%d]: התאמה קרובה אינה חוסמת'%A)
		if T and T!='IL'and re.search('לא נמצא רישום',D.get('summary')or''):B.append('red_flags[%d]: היעדר רישום בישראל של ישות זרה אינו ממצא'%A)
	for H in('raw_copies','sources','lookups'):
		for(A,U)in enumerate(C.get(H)or[]):
			for D in('url','typed_url','final_url'):
				if U.get(D)and has_secret(U[D]):B.append('%s[%d].%s: כתובת עם טוקן או חתימה'%(H,A,D))
	for(A,G)in enumerate(C.get('lookups')or[]):
		if G.get('result')=='blocked':
			f=[A for A in C.get('not_checked')or[]if(G.get('source')or'\x00')in(A.get('item')or'')or(A.get('why')or'').startswith('נחסם')]
			if not f:B.append('lookups[%d]: מקור שנחסם בלי משימה לעורך הדין ב-not_checked'%A)
		if G.get('bypass')or re.search('captcha.?solv|proxy|user.?agent.?spoof',json.dumps(G),re.I):B.append('lookups[%d]: עקיפה של חסימה אסורה'%A)
		M=G.get('user_agent')
		if M is not None and ua_problem(M):B.append('lookups[%d]: %s'%(A,ua_problem(M)))
	N={}
	for(A,E)in enumerate(C.get('sources')or[]):
		g=re.sub('^https?://([^/:]+).*$','\\1',E.get('url')or'').lower();F=E.get('class')or'official';N[E.get('no')]=F
		if F not in('official','media'):B.append('sources[%d]: class לא חוקי (official | media)'%A)
		elif case_law_url(E.get('url')or''):B.append('sources[%d]: %s'%(A,case_law_url(E.get('url')or'')))
		elif F=='official'and not domain_ok(E.get('url')or'',c):B.append('sources[%d]: דומיין או נתיב שאינו ברשימה המורשית: %s'%(A,g))
		elif F=='media':
			V=media_problem(E.get('url')or'',S,K)
			if V:B.append('sources[%d]: %s'%(A,V))
			for D in('outlet','url','published','date'):
				if not E.get(D):B.append('sources[%d]: מקור תקשורתי בלי %s (כלי התקשורת, קישור, תאריך פרסום ותאריך בדיקה)'%(A,D))
	def O(nos):return any(N.get(A)=='official'for A in nos or())
	for(A,D)in enumerate(C.get('red_flags')or[]):
		if not O(D.get('source_nos')):B.append('red_flags[%d]: דגל אדום בלי מקור רשמי: אות מהתקשורת אינו בסיס יחיד לממצא'%A)
	if(C.get('who')or{}).get('source_nos')and not O(C['who']['source_nos']):B.append('who: הזהות רק ממקור רשמי, לא מהתקשורת')
	for(A,P)in enumerate(C.get('effect_on_risks')or[]):
		if P.get('change')in('up','down')and P.get('source_nos')and not O(P['source_nos']):B.append('effect_on_risks[%d]: שינוי בדרגה רק מממצא רשמי, לא מאות תקשורתי'%A)
	for(A,I)in enumerate(C.get('media_signals')or[]):
		W=I.get('source_nos')or[]
		if not W or any(N.get(A)!='media'for A in W):B.append('media_signals[%d]: אות תקשורתי נשען רק על מקור תקשורתי ב-sources (class: media)'%A)
		if I.get('blocking'):B.append('media_signals[%d]: אות תקשורתי אינו חוסם; ממצא חוסם רק ממקור רשמי'%A)
		if I.get('subject','entity')!='entity':B.append('media_signals[%d]: אות רק על הצד שכנגד כתאגיד; אין מידע על אדם פרטי מעבר למרשם הרשמי'%A)
		for X in CASE_LAW_WORDS:
			if _term(X).search(I.get('summary')or''):B.append('media_signals[%d]: ידיעה על הליך משפטי אינה אות (%s): משימה לעורך הדין'%(A,X));break
	if C.get('media_signals')and K!=ENTITY_PURPOSE:B.append('media_signals: תקשורת רק בבדיקת רקע על הצד שכנגד (--purpose entity)')
	J=[('who',(C.get('who')or{}).get('text'))];J+=[('red_flags[%d]'%A,B.get('summary'))for(A,B)in enumerate(C.get('red_flags')or[])];J+=[('media_signals[%d]'%A,B.get('summary'))for(A,B)in enumerate(C.get('media_signals')or[])];J+=[('effect_on_risks[%d]'%A,B.get('why'))for(A,B)in enumerate(C.get('effect_on_risks')or[])]
	for(Y,Q)in J:
		Z=[]if case_law_connector else case_law_hits(Q or'')
		if Z:B.append('%s: אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1): %s'%(Y,'; '.join(Z[:2])))
		for a in INTENT_PHRASES:
			if Q and _term(a).search(Q):B.append('%s: ייחוס כוונה (%s): מתארים מה המקור אומר, ולא כוונה'%(Y,a));break
	for(b,E)in _walk(C):
		H=re.sub('\\[\\d+\\]$','',b).rsplit('.',1)[-1]
		if TS_KEY.search(H)and E and'T'in E and not ISO_TS.match(E):B.append('%s: חותמת זמן בלי שניות או בלי היסט: %s'%(b,E))
	for(A,R)in enumerate(C.get('raw_copies')or[]):
		if R.get('stored')not in(None,'page','excerpt_window','match_window'):B.append('raw_copies[%d]: stored לא חוקי'%A)
		if(R.get('full_size_bytes')or 0)>204800 and R.get('stored')in(None,'page'):B.append('raw_copies[%d]: קובץ מלא גדול נשמר בתיקיית הלקוח'%A)
	return B
def _load(p):
	with io.open(long_path(p),encoding='utf-8')as A:return json.load(A)
def main(argv=None):
	B=parser('בדיקת risk-register.json',out_required=False,out_help='דוח השגיאות (JSON); לא קובץ קלט');B.add_argument('register');B.add_argument('--corpus');B.add_argument('--deal');B.add_argument('--state');B.add_argument('--profile');B.add_argument('--playbook-status');B.add_argument('--entity');B.add_argument('--amendments',help='JSON: רשימת התיקונים הידועים (load_amendments)');B.add_argument('--approved-sources',help='מקורות-מאושרים.json שנשמר לדיסק (ברירת מחדל: %s)'%APPROVED_SOURCES_ENV);B.add_argument('--case-law-connector',help='שם מחבר הפסיקה הסגור שהלקוח חיבר בהפעלה הזו (כלל 1.1). בלעדיו, אזכור פסק דין בטקסט המוצג הוא שגיאה');B.add_argument('--purpose',choices=(ENTITY_PURPOSE,),help='entity: בדיקת רקע על הצד שכנגד, המטרה היחידה שמתירה את מקורות בדיקת הרקע ואת התקשורת (דוח בדיקת הרקע נבדק כך גם בלעדיו)');A=B.parse_args(argv);E=_load(A.register);C,D=validate(E,_load(A.corpus)if A.corpus else None,A.deal,_load(A.state)if A.state else None,_load(A.profile)if A.profile else None,_load(A.playbook_status)if A.playbook_status else None,_load(A.amendments)if A.amendments else None,A.approved_sources,A.case_law_connector)
	if A.entity:C+=['entity '+A for A in validate_entity_report(_load(A.entity),A.approved_sources,A.purpose or ENTITY_PURPOSE,A.case_law_connector)]
	sys.stdout.reconfigure(encoding='utf-8')
	for F in D:print('WARN',F)
	for G in C:print('ERR ',G)
	print('errors: %d warnings: %d'%(len(C),len(D)))
	if A.out:write_json(A.out,{'errors':C,'warnings':D},inputs=[A for A in(A.register,A.corpus,A.state,A.profile,A.playbook_status,A.entity,A.amendments)if A])
	return 1 if C else 0
if __name__=='__main__':sys.exit(run(main))
