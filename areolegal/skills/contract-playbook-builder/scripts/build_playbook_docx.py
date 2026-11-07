#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import argparse,datetime,io,json,os,re,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import areo_lib,basis_line,evidence_kind as E,voice_scrub
from common import rtl
from common.cli import OutputRefused,guard_out
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH,WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Cm,Pt,RGBColor
from playbook import market_counts as MC,status as S,surfaces_render as R
try:from playbook import validate_model as VM
except ImportError:VM=None
try:from obligations.model import LABELS as OBL_LABELS
except ImportError:OBL_LABELS={}
INK='16191F'
INK_SOFT='5B6472'
LINE='D7DBE0'
BRAND='0B6B4F'
NAVY='12314F'
GREEN,GREEN_BG='0F6B4C','E9F5F0'
AMBER,AMBER_BG='8A6212','FBF2DF'
RED,RED_BG='9E2723','FAEBEA'
SURF='F5F7F9'
FONT='Arial'
FONT_HE='David'
LANG='he'
MODEL={}
TRACKS_HE={'green':('ירוק: העמדה המועדפת',GREEN,GREEN_BG),'yellow':('צהוב: הפשרה האפשרית',AMBER,AMBER_BG),'red':('אדום: לא מתקבל',RED,RED_BG)}
TRACKS=TRACKS_HE
IMPORTANCE={'critical':('קריטית',RED),'high':('גבוהה',AMBER),'medium':('בינונית',INK_SOFT),'low':('נמוכה',INK_SOFT)}
IMPORTANCE_HE=IMPORTANCE
CONFIDENCE={'High':'גבוהה','Medium':'בינונית','Low':'נמוכה'}
REQ={'Required':'חובה','Recommended':'מומלץ','Optional':'רשות','Conditional':'מותנה','Prohibited':'אסור'}
POLICY={'Confirmed':'נקבע במדיניות כתובה של החברה','Unclear':'לא ברור, טעון הכרעה'}
POSTURE={'hold_green':'מחזיקים בירוק','offer_yellow':'מציעים את הצהוב'}
READ_STATUS={'read':'נקרא','partially_read':'נקרא חלקית','located_not_read':'אותר, לא נקרא'}
EFFECTS=[('company_effect','ההשפעה על החברה'),('as_discloser_effect','כשהחברה מגלה'),('as_recipient_effect','כשהחברה מקבלת')]
MEANING_CODES='Approved','AgreeWithComments','NotApproved'
BRIEF_WORDS=15
HEB=re.compile('[\u0590-\u05ff]')
RAT=[('executive_policy_rationale','תקציר נימוק המדיניות'),('protected_interest_and_clause_purpose','מטרת הסעיף והאינטרס המוגן'),('legal_risk_and_legal_framework','החשיפה המשפטית והמסגרת הנורמטיבית'),('contractual_risk_allocation_mechanism','מנגנון חוזי והקצאת סיכון'),('company_role_and_policy_fit','הצד של החברה וההתאמה למדיניות'),('business_operational_impact','ההשלכה העסקית והתפעולית'),('internal_evidence_rationale','דוגמאות מההסכמים של החברה'),('market_practice_assessment','מקובלות שוק'),('tradeoff_statement','האיזון שנבחר'),('related_clause_rationale','סעיפים קשורים'),('uncertainties_and_limitations','אי-ודאות ומגבלות')]
PERSP=[('legal_analysis','ניתוח משפטי'),('business_analysis','ניתוח עסקי'),('internal_corpus_findings','מה עולה מההסכמים של החברה'),('internal_contracting_trend','מגמת התקשרות פנימית'),('external_market_trend','מגמת שוק חיצונית')]
EN_TABLES={'TRACKS':{'green':('Green: preferred position',GREEN,GREEN_BG),'yellow':('Yellow: possible compromise',AMBER,AMBER_BG),'red':('Red: not acceptable',RED,RED_BG)},'IMPORTANCE':{'critical':('Critical',RED),'high':('High',AMBER),'medium':('Medium',INK_SOFT),'low':('Low',INK_SOFT)},'CONFIDENCE':{'High':'High','Medium':'Medium','Low':'Low'},'REQ':{'Required':'Required','Recommended':'Recommended','Optional':'Optional','Conditional':'Conditional','Prohibited':'Prohibited'},'POLICY':{'Confirmed':"Set in the company's written policy",'Unclear':'Unclear, needs a decision'},'POSTURE':{'hold_green':'Hold the green','offer_yellow':'Offer the yellow'},'READ_STATUS':{'read':'Read','partially_read':'Partially read','located_not_read':'Located, not read'},'EFFECTS':[('company_effect','Effect on the company'),('as_discloser_effect','When the company discloses'),('as_recipient_effect','When the company receives')],'RAT':[('executive_policy_rationale','Policy rationale summary'),('protected_interest_and_clause_purpose','Purpose of the clause and the protected interest'),('legal_risk_and_legal_framework','Legal exposure and the normative framework'),('contractual_risk_allocation_mechanism','Contractual mechanism and risk allocation'),('company_role_and_policy_fit',"The company's side and fit with the policy"),('business_operational_impact','Business and operational impact'),('internal_evidence_rationale',"Examples from the company's agreements"),('market_practice_assessment','Market practice'),('tradeoff_statement','The balance chosen'),('related_clause_rationale','Related clauses'),('uncertainties_and_limitations','Uncertainty and limitations')],'PERSP':[('legal_analysis','Legal analysis'),('business_analysis','Business analysis'),('internal_corpus_findings',"What the company's agreements show"),('internal_contracting_trend','Internal contracting trend'),('external_market_trend','External market trend')],'DRAFTED_HE':{'same_side':'Our side','other_side':'The counterparty','negotiated':'Negotiated','neutral_model':'Balanced model','unknown':'Unknown'},'POINT_HE':(('ours','In our favour'),('middle','Middle'),('theirs','In their favour')),'SOURCES_HEAD':'Sources the playbook relies on'}
HE_TABLES={}
TX={'he':{'until':'%s עד %s','not_stated':'לא צוין','unknown':'לא ידוע','open':'פתיחה','research_date':'תאריך המחקר: %s','market_sources':'מקורות השוק','src_heads':['#','גוף','מסמך','תאריך','ניסח / לטובת מי','קישור'],'range_head':'הטווח לכל נושא','point_sources':'%s, מקורות: %s','no_certainty':'ודאות לא צוינה','unverified_point':'ממצא לא מאומת, פחות משלושה מקורות','needs_verify':'%s: טעון אימות (%s)','located_not_read':'אותר, לא נקרא','partially_read':'נקרא חלקית','read':'נקרא','not_verified':'מה לא אומת','legal_sources':'מקורות הדין','legal_heads':['#','מקור','גוף','נקרא','קישור'],'limitations':'מגבלות','corpus_none':'אין הסכמים של החברה מהסוג הזה','corpus_files':'%d הסכמים של החברה (מתוך %d קבצים)','corpus_n':'%d הסכמים של החברה','playbook':'פלייבוק חוזי','cover_one':'חלק א: המדיניות. חלק ב: הנימוקים והנספחים','cover_full':'הגרסה המלאה','cover_short':'הגרסה המקוצרת','coverage':'כיסוי הסעיפים','ledger':'ספר הכיסוי','coverage_line':'כוסו %d מתוך %d סעיפים; %d נושאים חדשים; %d סעיפים ייחודיים לבדיקתכם','role':'הצד של החברה','version':'גרסה','produced':'הופק בתאריך','updated':'עדכון אחרון','confidential':'חסוי. הוכן לצורך קבלת ייעוץ משפטי ומיועד לשימוש פנימי בלבד.','draft_note':'טיוטה מקצועית. חובה בדיקת עורך דין לפני הסתמכות או שליחה.','ev_heads':['ההסכם','סעיף','הנוסח שנמצא'],'anchors':'עיגונים בדין','importance':'רמת חשיבות','presence':'כלל נוכחות','clause_kind':'סוג הסעיף','status':'מעמד','proposed':'טיוטה, מחכה לאישור שלכם','confidence':'רמת ביטחון','legal_review':'טעון בדיקה משפטית','id':'מזהה','round1':'בתגובה הראשונה: ','translation':'תרגום, לבדיקה','position':'העמדה: ','red_position':'לא מתקבל: ','red_cure':'הנוסח החלופי שמציעים במקום: ','red_cure_green':'נוסח הירוק שלמעלה.','company_effect':'ההשפעה על החברה: ','source':'מקור: ','legal_rationale':'נימוק משפטי','full_why':'הנימוק המלא והדוגמאות: בחלק ב, נושא %d','brief':'העמדות בקצרה','brief_heads':['הנושא','ירוק','צהוב','אדום','בתגובה הראשונה'],'persp':'פרספקטיבת החברה','why_policy':'מדוע נבחרה מדיניות זו','evidence':'דוגמאות מההסכמים','header':'%s · פלייבוק %s','footer':'%s · %s · חסוי · עמוד ','company':'החברה','families':'הסכמי החברה','snapshot':'תמונת מצב','fam_type':'סוג ההסכמים','topics':'נושאי מדיניות','analyzed':'הסכמי החברה שנותחו','market_research':'מחקר שוק','dates':'טווח תאריכים','pb_status':'מעמד הפלייבוק','part_a':'חלק א: המדיניות לפי נושא','part_b':'חלק ב: הנימוקים','part_b_draft':'טיוטה: שכבת הנימוקים אינה שלמה. ב-%d מתוך %d נושאים הנימוק חסר או חוזר על נוסח העמדה, ואינו מוצג כאן עד שייכתב.','no_why':'אין במודל נימוק מלא מעבר למה שמודפס בכרטיסים.','by_topic':'מדיניות לפי נושא','annex':'נספח: ההסכמים שנותחו','annex_heads':['ההסכם','הצד שכנגד','מעמד הקריאה'],'title':'פלייבוק חוזי - %s','file':'%s - פלייבוק %s - %s - %s.docx','depts':'מחלקות אחראיות','depts_set':'המחלקות שנקבעו','depts_heads':['סוג החיוב','תמצית','המחלקה האחראית','מקור'],'depts_proposed':'מחלקות שהוצעו מתוך ההסכמים, ועוד לא נקבעו','proposed_heads':['המחלקה','הנוסח בהסכם','מקור'],'needs_verification':'טעון אימות','clause_ref':'סעיף %s'},'en':{'until':'%s to %s','not_stated':'Not stated','unknown':'Unknown','open':'Open','research_date':'Research date: %s','market_sources':'Market sources','src_heads':['#','Body','Document','Date','Drafted by / in whose favour','Link'],'range_head':'The range for each topic','point_sources':'%s, sources: %s','no_certainty':'Certainty not stated','unverified_point':'Unverified finding, fewer than three sources','needs_verify':'%s: needs verification (%s)','hebrew_note':'Note: the positions and explanations in this document are written in Hebrew, the language the playbook was built in. The proposed contract wording is in English where the source agreements are in English. Ask Areo to translate the policy text if you need it in English.','located_not_read':'located, not read','partially_read':'partially read','read':'Read','not_verified':'What was not verified','legal_sources':'Legal sources','legal_heads':['#','Source','Body','Read','Link'],'limitations':'Limitations','corpus_none':'The company has no agreements of this type','corpus_files':'%d company agreements (out of %d files)','corpus_n':'%d company agreements','playbook':'Contract playbook','cover_one':'Part A: the policy. Part B: the rationale and annexes','cover_full':'Full version','cover_short':'Short version','coverage':'Clause coverage','ledger':'Coverage ledger','coverage_line':'Covered %d of %d clauses; %d new topics; %d unique clauses for your review','role':"Company's side",'version':'Version','produced':'Produced on','updated':'Last updated','confidential':'Confidential. Prepared for the purpose of obtaining legal advice, for internal use only.','draft_note':'Professional draft. Review by a lawyer is required before reliance or sending.','ev_heads':['Agreement','Clause','The wording found'],'anchors':'Legal grounding','importance':'Importance','presence':'Presence rule','clause_kind':'Clause type','status':'Status','proposed':'Draft, awaiting your approval','confidence':'Confidence','legal_review':'Needs legal review','id':'ID','round1':'In the first response: ','translation':'Translation, for review','position':'Position: ','red_position':'Not acceptable: ','red_cure':'Cure wording we propose instead: ','red_cure_green':'the green wording above.','company_effect':'Effect on the company: ','source':'Source: ','legal_rationale':'Legal rationale','full_why':'Full rationale and examples: Part B, topic %d','brief':'Positions at a glance','brief_heads':['Topic','Green','Yellow','Red','First response'],'persp':"The company's perspective",'why_policy':'Why this policy was selected','evidence':'Examples from the agreements','header':'%s · %s playbook','footer':'%s · %s · Confidential · Page ','company':'The company','families':"The company's agreements",'snapshot':'Overview','fam_type':'Agreement type','topics':'Policy topics','analyzed':'Company agreements analysed','market_research':'Market research','dates':'Date range','pb_status':'Playbook status','part_a':'Part A: the policy by topic','part_b':'Part B: the rationale','part_b_draft':'Draft: the rationale layer is incomplete. In %d of %d topics the rationale is missing or repeats the position wording, and it is not shown here until it is written.','no_why':'The model has no full rationale beyond what the cards show.','by_topic':'Policy by topic','annex':'Annex: the agreements analysed','annex_heads':['Agreement','Counterparty','Reading status'],'title':'Contract playbook - %s','file':'%s - %s playbook - %s - %s.docx','depts':'Responsible departments','depts_set':'Departments set by the company','depts_heads':['Obligation type','Summary','Responsible department','Source'],'depts_proposed':'Departments proposed from the agreements, not yet set','proposed_heads':['Department','Wording in the agreement','Source'],'needs_verification':'Needs verification','clause_ref':'clause %s'}}
def tx(key):return TX[LANG][key]
def set_lang(lang):
	global LANG;_LANG_NOW[0]='en'if str(lang or'').lower().startswith('en')else'he';g=globals()
	if not HE_TABLES:HE_TABLES.update({k:g[k]for k in EN_TABLES})
	LANG='en'if lang=='en'else'he';g.update(EN_TABLES if LANG=='en'else HE_TABLES)
AREO_TAG_EN="Areo proposal (not based on the client's documents)"
DOCS_EN=basis_line.DOCS_EN
PRELIMINARY_EN=basis_line.PRELIMINARY_EN
def basis_line_en(units,origin,status=None):
	if not isinstance(units,int):return
	if units==0 or origin=='market_built':return'Built from the market, adapted to the company\'s position, with in-depth regulatory review. It contains no position derived from the company\'s agreements, and every position in it is marked "%s".'%AREO_TAG_EN
	docs=DOCS_EN.get(status)or DOCS_EN['signed']
	if units>=7 and origin=='own_plus_market':return'Built from %d %s, combined with market research. A position that comes from the market is marked "%s".'%(units,docs,AREO_TAG_EN)
	if units>=20:return'Built from %d %s.'%(units,docs)
	if units>=7:return'Built from %d %s. This is fewer than recommended (about 20), so some positions rest on few negotiations.'%(units,docs)
	if origin=='own_plus_market':return'Built from %d %s, combined with market research. A position that comes from the market is marked "%s".'%(units,docs,AREO_TAG_EN)
	return'Built from %d %s only. Building a playbook from fewer than 20 agreements is not recommended, and the company chose not to add market research.'%(units,docs)
def basis_line_for(model):
	if LANG=='en':line=basis_line_en(basis_line.agreement_units(model),(model.get('scope_summary')or{}).get('corpus_origin'),basis_line.docs_status(model));return line+basis_line.honesty_tail(model,'en')if line else line
	return basis_line.line_for(model)
def preliminary_for(model):
	if LANG=='en':return PRELIMINARY_EN.get(basis_line.corpus_status(model))
	return basis_line.preliminary_line(model)
def coverage_line(model):
	c=model.get('coverage')or{}
	def num(*names):
		for n in names:
			if isinstance(c.get(n),int):return c[n]
	units=num('units','units_total')
	if units is None:return
	unmapped=num('unmapped_units','units_unmapped')or 0;return tx('coverage_line')%(units-unmapped,units,num('topics_new')or 0,num('unique_units','units_unique')or 0)
def ledger_line(model):
	if VM is None:return
	lines=VM.coverage_ledger_lines(model,LANG);return lines[0]if lines else None
_BAD_NAME={'"':None,':':' -','/':'-','\\':'-','?':'','*':'','<':'(','>':')','|':'-'}
def safe_filename(name,lang='he'):
	out=[]
	for ch in name:
		if ch=='"':out.append('״'if lang=='he'else"'")
		elif ch in _BAD_NAME:out.append(_BAD_NAME[ch])
		elif ord(ch)<32:continue
		else:out.append(ch)
	return' '.join(''.join(out).split()).strip(' .')
PPR_ORDER=['pStyle','keepNext','keepLines','pageBreakBefore','numPr','pBdr','shd','tabs','bidi','spacing','ind','contextualSpacing','jc','outlineLvl','rPr']
def _el(tag,**attrs):
	e=OxmlElement(tag)
	for(k,v)in attrs.items():e.set(qn('w:'+k),v)
	return e
def _local(tag):return tag.split('}')[-1]
TBLPR_ORDER=['tblStyle','tblpPr','tblOverlap','bidiVisual','tblStyleRowBandSize','tblStyleColBandSize','tblW','jc','tblCellSpacing','tblInd','tblBorders','shd','tblLayout','tblCellMar','tblLook','tblCaption','tblDescription','tblPrChange']
SECTPR_ORDER=['footnotePr','endnotePr','type','pgSz','pgMar','paperSrc','pgBorders','lnNumType','pgNumType','cols','formProt','vAlign','noEndnote','titlePg','textDirection','bidi','rtlGutter','docGrid','printerSettings','sectPrChange']
def put_ordered(parent,el,order):
	name=_local(el.tag);old=parent.find(qn('w:'+name))
	if old is not None:parent.remove(old)
	idx=order.index(name)if name in order else 99
	for child in parent:
		c=_local(child.tag)
		if(order.index(c)if c in order else 99)>idx:child.addprevious(el);return el
	parent.append(el);return el
def ppr_put(p,el):
	ppr=p._p.get_or_add_pPr();name=_local(el.tag);old=ppr.find(qn('w:'+name))
	if old is not None:ppr.remove(old)
	idx=PPR_ORDER.index(name)if name in PPR_ORDER else 99
	for child in ppr:
		c=_local(child.tag)
		if(PPR_ORDER.index(c)if c in PPR_ORDER else 99)>idx:child.addprevious(el);return el
	ppr.append(el);return el
def shade(p,fill):ppr_put(p,_el('w:shd',val='clear',color='auto',fill=fill))
def bar(p,color,size=18,side='start'):
	ppr=p._p.get_or_add_pPr();b=ppr.find(qn('w:pBdr'))
	if b is None:b=ppr_put(p,_el('w:pBdr'))
	old=b.find(qn('w:'+side))
	if old is not None:b.remove(old)
	b.append(_el('w:'+side,val='single',sz=str(size),space='8',color=color))
def rtl_p(p):
	if LANG=='he':ppr_put(p,_el('w:bidi'))
_SCRUB=[None]
def _scrub(text):
	if _SCRUB[0]is None or _SCRUB[0][0]is not MODEL:_SCRUB[0]=MODEL,voice_scrub.Scrubber(MODEL,_LANG_NOW[0])
	return _SCRUB[0][1].text(text)
_LANG_NOW=['he']
def run(p,text,size=11,bold=False,color=INK,italic=False,ltr=False):
	r=p.add_run(_scrub(text));r.font.name=FONT;r.font.size=Pt(size);r.bold=bold;r.italic=italic;r.font.color.rgb=RGBColor.from_string(color);rpr=r._r.get_or_add_rPr();rf=rpr.find(qn('w:rFonts'))
	if rf is None:rf=_el('w:rFonts');rpr.insert(0,rf)
	he=LANG=='he';latin=FONT_HE if he and HEB.search(text or'')else FONT
	for k in('ascii','hAnsi'):rf.set(qn('w:'+k),latin)
	rf.set(qn('w:cs'),FONT_HE if he else FONT)
	if not he:return r
	if ltr:rtl.set_run_ltr(r)
	else:rpr.append(_el('w:rtl'))
	return r
def ext_link(p,text,url,size=9):rid=p.part.relate_to(url,RT.HYPERLINK,is_external=True);r=run(p,text,size,False,BRAND);r.font.underline=True;h=_el('w:hyperlink');h.set(qn('r:id'),rid);p._p.remove(r._r);h.append(r._r);p._p.append(h);return h
URL_RX=re.compile('https?://[^\\s,;)\\]]+')
def record_urls(d):
	mr=d.get('market_research')or{};out=set()
	for key in('sources','external_sources','findings','source_refs'):
		for x in mr.get(key)or():
			if isinstance(x,dict):out|={u.rstrip('/')for u in(x.get('url'),x.get('final_url'))if u}
	for x in list((d.get('regulatory_research')or{}).get('sources')or())+list(d.get('external_sources')or()):
		if isinstance(x,dict)and x.get('url'):out.add(x['url'].rstrip('/'))
	return out
def linked(p,text,size=9.5,color=INK_SOFT,known=None):
	pos=0
	for m in URL_RX.finditer(text):
		if m.start()>pos:run(p,text[pos:m.start()].rstrip(', '),size,False,color)
		url=m.group(0).rstrip('.')
		if known is None or url.rstrip('/')in known:ext_link(p,' '+re.sub('^https?://(www\\.)?','',url).split('/')[0],url,size)
		pos=m.start()+len(url)
	if pos<len(text):run(p,text[pos:],size,False,color)
def bookmark(p,name):i=str(len(list(p.part.element.iter(qn('w:bookmarkStart'))))+1);pos=1 if p._p.pPr is not None else 0;p._p.insert(pos,_el('w:bookmarkStart',id=i,name=name));p._p.append(_el('w:bookmarkEnd',id=i))
def link(p,text,anchor,size=9.5,color=BRAND):r=run(p,text,size,False,color);r.font.underline=True;h=_el('w:hyperlink',anchor=anchor,history='1');p._p.remove(r._r);h.append(r._r);p._p.append(h);return h
def para(doc,text='',size=11,bold=False,color=INK,before=0,after=4,line=1.15,container=None,italic=False):
	p=(container or doc).add_paragraph();rtl_p(p);pf=p.paragraph_format;pf.space_before=Pt(before);pf.space_after=Pt(after);pf.line_spacing=line
	if text:run(p,text,size,bold,color,italic)
	return p
def table_borders(tbl,color=LINE):
	tpr=tbl._tbl.tblPr;b=_el('w:tblBorders')
	for edge in('top','left','bottom','right','insideH','insideV'):b.append(_el('w:'+edge,val='single',sz='4',space='0',color=color))
	put_ordered(tpr,b,TBLPR_ORDER)
	if LANG=='he':put_ordered(tpr,_el('w:bidiVisual'),TBLPR_ORDER)
def cell_text(cell,text,bold=False,size=10,color=INK,fill=None):
	cell.text='';p=cell.paragraphs[0];rtl_p(p);p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(2);run(p,text,size,bold,color)
	if fill:cell._tc.get_or_add_tcPr().append(_el('w:shd',val='clear',color='auto',fill=fill))
def clause(v):
	if isinstance(v,dict):
		src=v.get('source_language')
		for k in('en','text','he')if LANG=='en'else('he','text','en'):
			t=v.get(k)
			if isinstance(t,str)and t.strip():lang='en'if k=='en'or not HEB.search(t)else'he';return t,lang,lang==LANG and src not in(None,'',LANG)
		return'',LANG,False
	t=txt(v);return t,'he'if not t or HEB.search(t)else'en',False
def txt(v):
	if v is None or v is False:return''
	if isinstance(v,str):return v
	if isinstance(v,dict):return clause(v)[0]
	if isinstance(v,(list,tuple)):return'; '.join(t for t in(txt(x)for x in v)if t)
	return str(v)
def s(v,limit=None,verbatim=False):
	t=' '.join(txt(v).split())
	if not verbatim:t=t.replace('—',', ').replace('–','-').replace(' ,',',')
	return t[:limit]if limit else t
def words(v,n=BRIEF_WORDS):w=s(v).split();return' '.join(w[:n])+('...'if len(w)>n else'')
def roles_label(sc):return' / '.join(x['label']for x in sc.get('company_roles')or[]if isinstance(x,dict)and x.get('label'))
def date_range(v):
	if isinstance(v,dict):a,b=s(v.get('from')or v.get('start')),s(v.get('to')or v.get('end'));return tx('until')%(a,b)if a and b else a or b
	return s(v,120)
def clean_company(v):
	t=' '.join(str(v or'').split())
	for sep in(', ח.פ',' ח.פ'):
		if sep in t and'['in t.split(sep,1)[1][:20]:t=t.split(sep,1)[0]
	return t.strip(' ,')
def short_role(v):
	t=' '.join(str(v or'').split())
	for sep in(' — ',' - ','(',',',';','.'):
		if sep in t:t=t.split(sep)[0]
	return t.strip()or tx('not_stated')
EN_MONTHS='January','February','March','April','May','June','July','August','September','October','November','December'
def date_text(iso):
	try:dd=datetime.date.fromisoformat(str(iso or'')[:10])
	except ValueError:return
	if LANG=='en':return'%d %s %d'%(dd.day,EN_MONTHS[dd.month-1],dd.year)
	return'%d.%d.%d'%(dd.day,dd.month,dd.year)
def produced_on(d):raw=(d.get('generated_at')or d.get('last_updated')or'')[:10];return date_text(raw)or date_text(datetime.date.today().isoformat())
def base(doc):
	st=doc.styles['Normal'];st.font.name=FONT;st.font.size=Pt(11);st.element.rPr.rFonts.set(qn('w:cs'),FONT_HE if LANG=='he'else FONT)
	for sec in doc.sections:
		sec.left_margin=sec.right_margin=Cm(2.2);sec.top_margin=Cm(2.);sec.bottom_margin=Cm(1.8)
		if LANG=='he':put_ordered(sec._sectPr,_el('w:bidi'),SECTPR_ORDER);put_ordered(sec._sectPr,_el('w:rtlGutter'),SECTPR_ORDER)
SOURCES_HEAD='המקורות שעליהם נשען הפלייבוק'
NOT_READ='located_not_read','excluded','blocked'
DRAFTED_HE={'same_side':'הצד שלנו','other_side':'הצד שכנגד','negotiated':'נוהל עליו משא ומתן','neutral_model':'מודל מאוזן','unknown':'לא ידוע'}
POINT_HE=('ours','לטובתנו'),('middle','באמצע'),('theirs','לטובתם')
def he_date(v):return date_text(v)or s(v,20)
def table(doc,heads,rows,widths):
	t=doc.add_table(rows=1,cols=len(heads));table_borders(t)
	for(i,head)in enumerate(heads):cell_text(t.rows[0].cells[i],head,True,9,NAVY,SURF)
	for row in rows:
		c=t.add_row().cells
		for(i,v)in enumerate(row):
			if isinstance(v,tuple):c[i].text='';p=c[i].paragraphs[0];rtl_p(p);ext_link(p,v[0],v[1],8.5)
			else:cell_text(c[i],v,False,8.5)
	for r in t.rows:
		for(cell,w)in zip(r.cells,widths):cell.width=Cm(w)
	para(doc,after=8)
def sources_chapter(doc,d,num):
	mr=d.get('market_research')or{};rr=d.get('regulatory_research')or{};refs=[r for r in mr.get('source_refs')or()if isinstance(r,dict)and r.get('read_status')not in NOT_READ];legal=[x for x in rr.get('sources')or()if isinstance(x,dict)]
	if not refs and not legal:return False
	h1(doc,tx_sources_head(),num)
	if LANG=='en':sentence=MC.basis_sentence(d,lang='en')
	else:import market_research;sentence=market_research.fixed_sentence(d)or MC.basis_sentence(d)
	if sentence:para(doc,s(sentence),10.5,after=4)
	if mr.get('research_date'):para(doc,tx('research_date')%he_date(mr['research_date']),9.5,color=INK_SOFT,after=8)
	if refs:h3(doc,tx('market_sources'));table(doc,tx('src_heads'),[[s(r.get('source_id'),8),s(r.get('issuing_body'),60),s(r.get('document'),80),he_date(r.get('doc_date'))or tx('not_stated'),DRAFTED_HE.get(r.get('drafted_by'),tx('unknown')),(tx('open'),r.get('final_url')or r.get('url'))if r.get('final_url')or r.get('url')else'']for r in refs],(1.,3.2,4.6,1.8,2.8,1.6))
	ranges=[x for x in mr.get('ranges')or()if isinstance(x,dict)]
	if ranges:
		h3(doc,tx('range_head'))
		for rng in ranges:
			p=para(doc,after=1);run(p,s(rng.get('topic')or rng.get('rule_id')),10,True,INK)
			for(key,label)in POINT_HE:
				pt=rng.get(key)
				if isinstance(pt,dict)and pt.get('source_ids'):text=tx('point_sources')%(s(pt.get('certainty'))or tx('no_certainty'),', '.join(pt['source_ids']))
				elif key=='theirs'and rng.get('theirs_note'):text=s(rng['theirs_note'])
				else:text=tx('unverified_point')
				q=para(doc,after=1);run(q,label+': ',9.5,True,INK_SOFT);run(q,text,9.5,False,INK)
	open_items=[s(u.get('text')or u.get('label'))for u in mr.get('unverified_findings')or()if isinstance(u,dict)];open_items+=[tx('needs_verify')%(s(x.get('title')),tx('located_not_read')if x.get('read_status')=='located_not_read'else tx('partially_read'))for x in legal if x.get('read_status')in('located_not_read','partially_read')]
	if open_items:
		h3(doc,tx('not_verified'))
		for x in open_items:q=para(doc,after=3);bar(q,AMBER,12);linked(q,x,known=record_urls(d))
	if legal:h3(doc,tx('legal_sources'));table(doc,tx('legal_heads'),[[s(x.get('source_id'),8),s(x.get('title'),90),s(x.get('issuer'),40),READ_STATUS.get(x.get('read_status'))if x.get('read_status')in('read','partially_read')else READ_STATUS['located_not_read'],(tx('open'),x['url'])if x.get('url')else'']for x in legal],(1.,6.4,3.4,2.4,1.6))
	lim=mr.get('limitations')
	if lim:
		h3(doc,tx('limitations'))
		for x in[lim]if isinstance(lim,str)else lim:linked(para(doc,after=3),s(x),known=record_urls(d))
	return True
def tx_sources_head():return SOURCES_HEAD
def h1(doc,text,num=''):
	p=para(doc,before=20,after=2)
	if num:run(p,num+'   ',18,True,BRAND)
	run(p,text,18,True,NAVY);bar(para(doc,after=10),LINE,8,'top')
def h2(doc,text,anchor=None):
	p=para(doc,before=14,after=4);run(p,text,13.5,True,NAVY)
	if anchor:bookmark(p,anchor)
	return p
def status_para(container,tag,text,size,before=0,after=4):p=container.add_paragraph();rtl_p(p);p.paragraph_format.space_before=Pt(before);p.paragraph_format.space_after=Pt(after);R.add_status_control(p,tag,text,size,lang=LANG);return p
def h3(doc,text):run(para(doc,before=9,after=2),text,11,True,INK_SOFT)
def fam_role(fams):
	for f in fams:
		if isinstance(f,dict)and f.get('company_role'):return f['company_role']
	return''
def corpus_label(model,scope):
	units=basis_line.agreement_units(model);files=(scope.get('corpus_basis')or{}).get('files')
	if units is None:
		units=scope.get('total_document_count')
		if not isinstance(units,int):return tx('not_stated')
	if units==0:return tx('corpus_none')
	status=basis_line.corpus_status(model)
	if status!='signed':
		name='%d %s'%(units,basis_line.docs(status,LANG))
		if isinstance(files,int)and files!=units:return'%s (%s'%(name,tx('corpus_files').split('(',1)[1]%files)
		return name
	if isinstance(files,int)and files!=units:return tx('corpus_files')%(units,files)
	return tx('corpus_n')%units
def cover(doc,m):
	run(para(doc,before=150,after=2),m['company'],13,True,BRAND);run(para(doc,after=0),tx('playbook'),30,True,NAVY);run(para(doc,after=6),m['family'],16,False,INK_SOFT);status_para(doc,R.STATUS_TAG,m['st']['label'],11,after=14);bar(para(doc,after=16),BRAND,26,'top');run(para(doc,after=6),{'one':tx('cover_one'),True:tx('cover_full'),False:tx('cover_short')}[m['full']],11,True,BRAND)
	if m['basis']:run(para(doc,after=4),m['basis'],10.5,False,INK)
	if m['preliminary']:run(para(doc,after=4),m['preliminary'],10.5,True,INK_SOFT)
	rows=[(tx('role'),m['role']),(tx('version'),m['version']),(tx('produced'),m['date'])]
	if m['updated']and m['updated']!=m['date']:rows.append((tx('updated'),m['updated']))
	for(k,v)in rows:p=para(doc,after=3);run(p,k+': ',10.5,True,INK_SOFT);run(p,v,10.5,False,INK)
	p=para(doc,before=18,after=0);shade(p,SURF);bar(p,BRAND,18);run(p,tx('confidential'),9.5,True,INK_SOFT);p=para(doc,after=0);shade(p,SURF);run(p,tx('draft_note'),9.5,False,INK_SOFT);p.runs[-1].add_break(WD_BREAK.PAGE)
def kv(doc,rows):
	t=doc.add_table(rows=0,cols=2);table_borders(t)
	for(k,v)in rows:
		c=t.add_row().cells;cell_text(c[0],k,True,10,INK_SOFT,SURF)
		if isinstance(v,tuple):c[1].text='';p=c[1].paragraphs[0];rtl_p(p);R.add_status_control(p,v[0],v[1],10,lang=LANG)
		else:cell_text(c[1],v,False,10)
		c[0].width=Cm(4.6);c[1].width=Cm(11.2)
	para(doc,after=8)
def ev_table(doc,ev):
	t=doc.add_table(rows=1,cols=3);table_borders(t)
	for(i,head)in enumerate(tx('ev_heads')):cell_text(t.rows[0].cells[i],head,True,9.5,NAVY,SURF)
	for e in ev:c=t.add_row().cells;cell_text(c[0],s(e.get('agreement')or e.get('source_document'),40),False,9);cell_text(c[1],s(e.get('clause_ref'),18),False,9);cell_text(c[2],s(e.get('quote')or e.get('text'),verbatim=True),False,9,INK_SOFT)
	for row in t.rows:row.cells[0].width=Cm(4.);row.cells[1].width=Cm(2.);row.cells[2].width=Cm(9.8)
	para(doc,after=8)
def anchors(doc,r,limit):
	srcs=[s(x,limit)for x in r.get('regulatory_sources')or[]if x]
	if not srcs:return
	h3(doc,tx('anchors'))
	for a in srcs:p=para(doc,after=2);bar(p,LINE,8);run(p,a,9.5,False,INK_SOFT)
def legal_review(r):
	v=r.get('legal_review_required')
	if isinstance(v,list):return any(not(isinstance(x,dict)and x.get('checked_by'))for x in v)
	return bool(v)
def status_line(doc,r,st):
	p=para(doc,after=4);shade(p,SURF);first=[True]
	def item(label,value,color=INK,bold=False):
		if not value:return
		run(p,(''if first[0]else'     ')+label+'  ',9.5,True,INK_SOFT);run(p,value,9.5,bold,color);first[0]=False
	imp=IMPORTANCE.get(str(r.get('importance')or'').lower())
	if imp:item(tx('importance'),imp[0],imp[1],True)
	pres=r.get('presence_rule')or{};req=pres.get('requirement')if isinstance(pres,dict)else pres
	if req:item(tx('presence'),REQ.get(req,s(req,30)))
	item(tx('clause_kind'),s(r.get('clause_kind'),20))
	if r.get('policy_status')=='Confirmed':item(tx('status'),POLICY['Confirmed'])
	elif r.get('policy_status')=='Unclear':item(tx('status'),POLICY['Unclear'])
	else:item(tx('status'),tx('proposed'))
	conf=CONFIDENCE.get(s(r.get('confidence')or r.get('confidence_level')));item(tx('confidence'),conf)
	if legal_review(r):item('',tx('legal_review'),RED,True)
	posture=POSTURE.get(r.get('round1_posture'))
	if posture:q=para(doc,after=8);run(q,tx('round1'),9.5,True,INK_SOFT);run(q,posture,9.5,False,INK)
def track(doc,r,key,st):
	blk=(r.get('traffic_light')or{}).get(key)or{};text,lang,translated=clause(blk.get('proposed_clause')or blk.get('fallback_wording'));meaning=''if blk.get('meaning')in MEANING_CODES else s(blk.get('meaning'));position=s(blk.get('position'))
	if not(text or meaning or position):return False
	title,color,fill=TRACKS[key]
	def line(after=2):q=para(doc,after=after);bar(q,color,22);shade(q,fill);return q
	p=para(doc,before=8,after=2);bar(p,color,22);shade(p,fill);run(p,title,11,True,color);origin=blk.get('fallback_origin')or r.get('fallback_origin')or{}if key=='yellow'else{};olabel=basis_line.fallback_label(origin,MODEL,LANG)if isinstance(origin,dict)and origin else None
	if olabel:run(line(),s(olabel),9.5,False,INK_SOFT,italic=True)
	body=' '.join(text.split()).replace('—',', ').replace('–','-')if text else meaning
	if key=='red'and text:
		if position:q=line();run(q,tx('red_position'),9.5,True,INK_SOFT);run(q,position,9.5,False,INK);position=''
		gtext=clause(((r.get('traffic_light')or{}).get('green')or{}).get('proposed_clause'))[0];q=line();run(q,tx('red_cure'),9.5,True,INK_SOFT)
		if gtext and' '.join(gtext.split())==' '.join(text.split()):run(q,tx('red_cure_green'),9.5,False,INK);body=''
	if body:
		run(line(),body,10.5,False,INK,ltr=lang=='en'and bool(text))
		if translated:run(line(),tx('translation'),9,True,INK_SOFT)
	if position and position!=body:q=line();run(q,tx('position'),9.5,True,INK_SOFT);run(q,position,9.5,False,INK)
	if meaning and text:run(line(),meaning,9.5,False,INK_SOFT,italic=True)
	for(field,label)in EFFECTS:
		if blk.get(field):q=line();run(q,label+': ',9.5,True,INK_SOFT);run(q,s(blk[field]),9.5,False,INK)
	role_names={str(x.get('role')):s(x.get('label'))for x in(MODEL.get('scope_summary')or{}).get('company_roles')or()if isinstance(x,dict)and x.get('role')}
	for(k,v)in(blk.get('role_effects')or{}).items()if isinstance(blk.get('role_effects'),dict)else():
		if s(v):
			q=line();head=tx('company_effect');name=role_names.get(str(k))or s(k)
			if name:head='%s (%s): '%(head.rstrip(': '),name)
			run(q,head,9.5,True,INK_SOFT);run(q,s(v),9.5,False,INK)
	src=s(blk.get('source_label')or blk.get('label'))
	if src:q=line();run(q,tx('source'),9,True,INK_SOFT);run(q,src,9,False,INK_SOFT)
	if r.get('rule_id'):k=S.cell_key(r['rule_id'],key);q=line(after=6);R.add_status_control(q,R.CELL_TAG+k,R.cell_status_text(None,st,k),8.5,lang=LANG)
	return True
def has_rationale(r):pr=r.get('policy_rationale')or{};cp=r.get('company_perspective')or{};return bool(any(pr.get(k)for(k,_)in RAT)or any(cp.get(k)for(k,_)in PERSP)or r.get('regulatory_sources')or r.get('evidence'))
def topic(doc,r,n,full,st):
	h2(doc,'%d. %s'%(n,s(r.get('topic_name'))),'card_%d'%n);status_line(doc,r,st)
	if r.get('clause_issue'):para(doc,s(r['clause_issue']),10.5,after=8,color=INK_SOFT)
	for key in('green','yellow','red'):track(doc,r,key,st)
	pr=r.get('policy_rationale')or{}
	if full=='card':
		if pr.get('executive_policy_rationale'):h3(doc,tx('legal_rationale'));para(doc,s(pr['executive_policy_rationale']),10.5,after=6)
		anchors(doc,r,160)
		if has_rationale(r)and E.rationale_complete(r)[0]:p=para(doc,after=6);link(p,tx('full_why')%n,'why_%d'%n)
	elif not full:
		if pr.get('executive_policy_rationale'):h3(doc,tx('legal_rationale'));para(doc,s(pr['executive_policy_rationale']),10.5,after=6)
		anchors(doc,r,160)
	else:rationale(doc,r,pr)
	bar(para(doc,before=6,after=10),LINE,6,'top')
def brief(doc,rules,num):
	h1(doc,tx('brief'),num);t=doc.add_table(rows=1,cols=5);table_borders(t)
	for(i,head)in enumerate(tx('brief_heads')):cell_text(t.rows[0].cells[i],head,True,9.5,NAVY,SURF)
	for(n,r)in enumerate(rules,1):
		c=t.add_row().cells;c[0].text='';p=c[0].paragraphs[0];rtl_p(p);link(p,'%d. %s'%(n,s(r.get('topic_name'))),'card_%d'%n,9);tl=r.get('traffic_light')or{}
		for(j,key)in enumerate(('green','yellow','red'),1):blk=tl.get(key)or{};fallback=''if blk.get('meaning')in MEANING_CODES else blk.get('meaning');cell_text(c[j],words(blk.get('position')or fallback),False,9)
		cell_text(c[4],POSTURE.get(r.get('round1_posture'),''),False,9)
	for row in t.rows:
		for(cell,w)in zip(row.cells,(4.,3.4,3.4,3.4,1.9)):cell.width=Cm(w)
	para(doc,after=8)
def rationale(doc,r,pr):
	cp=r.get('company_perspective')or{}
	if any(cp.get(k)for(k,_)in PERSP):
		h3(doc,tx('persp'))
		for(k,label)in PERSP:
			if cp.get(k):p=para(doc,after=4);run(p,label+': ',10,True,INK_SOFT);run(p,s(cp[k]),10,False,INK)
	if any(pr.get(k)for(k,_)in RAT):
		h3(doc,tx('why_policy'))
		for(k,label)in RAT:
			if pr.get(k):p=para(doc,after=4);run(p,label+': ',10,True,INK_SOFT);run(p,s(pr[k]),10,False,INK)
	anchors(doc,r,None)
	if r.get('evidence'):h3(doc,tx('evidence'));ev_table(doc,r['evidence'])
def source_ref(v):
	if isinstance(v,dict):
		parts=[s(v.get('agreement'),80)]
		if v.get('clause'):parts.append(tx('clause_ref')%s(v.get('clause'),20))
		if not any(parts)and v.get('citation_id'):parts=[s(v.get('citation_id'),20)]
		return', '.join(x for x in parts if x)
	return s(v,120)
def departments_chapter(doc,d):
	resp=[s(x,80)for x in d.get('responsible_departments')or()if s(x)];prop=[x for x in d.get('departments_proposed')or()if isinstance(x,dict)and x.get('name')];asg=[x for x in d.get('obligation_assignments')or()if isinstance(x,dict)and x.get('type')]
	if not(resp or prop or asg):return False
	types=(OBL_LABELS.get(LANG)or{}).get('type')or{};h2(doc,tx('depts'),'departments')
	if resp:kv(doc,[(tx('depts_set'),', '.join(resp))])
	if asg:
		rows=[]
		for x in asg:
			dept=s(x.get('department'),80)
			if x.get('needs_verification'):dept='%s (%s)'%(dept,tx('needs_verification'))if dept else tx('needs_verification')
			rows.append([types.get(x['type'])or s(x['type'],40),s(x.get('summary'),160),dept,source_ref(x.get('source'))])
		table(doc,tx('depts_heads'),rows,[3.2,5.6,3.4,3.6])
	if prop:h3(doc,tx('depts_proposed'));table(doc,tx('proposed_heads'),[[s(x.get('name'),80),s(x.get('quote'),300,verbatim=True),source_ref(x.get('source'))]for x in prop],[3.4,8.8,3.6])
	return True
def header_footer(doc,m):
	for sec in doc.sections:p=sec.header.paragraphs[0];rtl_p(p);run(p,tx('header')%(m['company'],m['family']),8.5,True,INK_SOFT);status_para(sec.header,R.STATUS_TAG,m['st']['label'],8,after=0);p=sec.footer.paragraphs[0];rtl_p(p);p.alignment=WD_ALIGN_PARAGRAPH.CENTER;run(p,tx('footer')%(m['company'],m['family']),8.5,False,INK_SOFT);p._p.append(_el('w:fldSimple',instr='PAGE'))
def build(d,prof,out,full,lang=None,model_path=None):
	global MODEL;MODEL=d;set_lang(S.deliverable_lang(d,prof,lang));sc=d.get('scope_summary')or{};fams=sc.get('contract_families')or[];st=S.gate_status(d,model_path,lang=LANG);role=sc.get('company_role')or fam_role(fams)or roles_label(sc);m={'company':clean_company(company_name(prof))or tx('company'),'family':', '.join(f.get('contract_family_name','')if isinstance(f,dict)else str(f)for f in fams)or tx('families'),'role':short_role(role),'role_full':s(role,600),'version':str(d.get('version')or'1.0'),'date':produced_on(d),'corpus':corpus_label(d,sc),'basis':basis_line_for(d)or'','preliminary':preliminary_for(d),'updated':produced_on({'last_updated':d.get('last_updated')})if d.get('last_updated')else'','full':full,'st':st};doc=Document();base(doc);cover(doc,m);header_footer(doc,m)
	if LANG=='en'and hebrew_content(d):para(doc,tx('hebrew_note'),10,False,INK_SOFT,before=4,after=8)
	h1(doc,tx('snapshot'),'1');rows=[(tx('fam_type'),m['family']),(tx('role'),m['role_full']or m['role']),(tx('topics'),str(len(d['rules']))),(tx('analyzed'),m['corpus'])]
	if coverage_line(d):rows.append((tx('coverage'),coverage_line(d)))
	if ledger_line(d):rows.append((tx('ledger'),ledger_line(d)))
	if MC.basis_sentence(d,lang=LANG):rows.append((tx('market_research'),MC.basis_sentence(d,lang=LANG)))
	rows+=[(tx('dates'),date_range(sc.get('date_range'))or tx('not_stated')),(tx('pb_status'),(R.STATUS_TAG,st['label']))];kv(doc,rows);status_para(doc,R.SUMMARY_TAG,R.summary_text(st),10,after=8);lim=sc.get('limitations')
	if lim:
		h3(doc,tx('limitations'))
		for x in[lim]if isinstance(lim,str)else lim:q=para(doc,after=4);bar(q,AMBER,12);run(q,s(x),10,False,INK_SOFT)
	n=2
	if sources_chapter(doc,d,str(n)):n+=1
	brief(doc,d['rules'],str(n));n+=1
	if full=='one':
		h1(doc,tx('part_a'),str(n))
		for(i,r)in enumerate(d['rules'],1):topic(doc,r,i,'card',st)
		departments_chapter(doc,d);h1(doc,tx('part_b'),str(n+1));with_why=[(i,r)for(i,r)in enumerate(d['rules'],1)if has_rationale(r)and E.rationale_complete(r)[0]];missing=len(d['rules'])-len(with_why)
		if missing and d['rules']:para(doc,tx('part_b_draft')%(missing,len(d['rules'])),10.5,bold=True,color=INK_SOFT)
		if not with_why:para(doc,tx('no_why'),10.5,color=INK_SOFT)
		for(i,r)in with_why:h2(doc,'%d. %s'%(i,s(r.get('topic_name'))),'why_%d'%i);rationale(doc,r,r.get('policy_rationale')or{});bar(para(doc,before=6,after=10),LINE,6,'top')
	else:
		h1(doc,tx('by_topic'),str(n))
		for(i,r)in enumerate(d['rules'],1):topic(doc,r,i,full,st)
		departments_chapter(doc,d)
	if full and d.get('source_log'):
		h1(doc,tx('annex'),str(n+2 if full=='one'else n+1));t=doc.add_table(rows=1,cols=3);table_borders(t)
		for(i,head)in enumerate(tx('annex_heads')):cell_text(t.rows[0].cells[i],head,True,9.5,NAVY,SURF)
		for src in d['source_log']:
			if not isinstance(src,dict):continue
			c=t.add_row().cells;cell_text(c[0],s(src.get('agreement_name')or src.get('document_name')or src.get('title')or src.get('file'),40),False,9);cell_text(c[1],s(src.get('counterparty'),40)or tx('not_stated'),False,9);rs=src.get('read_status');cell_text(c[2],READ_STATUS.get(rs)or s(rs,40)or tx('not_stated'),False,9)
	author=m['company']if m['company']!=tx('company')else''
	if LANG=='en':R.enforce_ltr_document(doc,author=author,title=tx('title')%m['family'])
	else:rtl.enforce_document(doc,author=author,title=tx('title')%m['family']);doc.core_properties.language='he-IL'
	doc.save(out);return out
def hebrew_content(d):
	rules=[r for r in d.get('rules')or[]if isinstance(r,dict)]
	if not rules:return str(d.get('output_language')or'').lower().startswith('he')
	heb=sum(1 for r in rules if re.search('[\u0590-\u05ff]',str(r.get('topic_name')or'')+str(((r.get('traffic_light')or{}).get('green')or{}).get('position')or'')));return heb/len(rules)>.2
def company_name(prof):
	if LANG=='en'and str(prof.get('organization_name_en')or'').strip():return prof['organization_name_en']
	return prof.get('organization_name')
def spec_filename(d,prof,lang):set_lang(lang);sc=d.get('scope_summary')or{};fams=sc.get('contract_families')or[];company=clean_company(company_name(prof))or tx('company');family=', '.join(f.get('contract_family_name','')if isinstance(f,dict)else str(f)for f in fams)or tx('families');role=short_role(sc.get('company_role')or fam_role(fams)or roles_label(sc));name=tx('file')%(company,family,role,produced_on(d));return safe_filename(name[:-len('.docx')],LANG)+'.docx'
def is_built_playbook(path):
	import zipfile
	try:
		with zipfile.ZipFile(path)as z:core=z.read('docProps/core.xml').decode('utf-8','replace')
	except Exception:return False
	m=re.search('<dc:title>([^<]*)</dc:title>',core);title=m.group(1)if m else'';return any(title.startswith(TX[k]['title'].split('%s')[0])for k in TX)
def main():
	ap=argparse.ArgumentParser(description='בונה את מסמך הפלייבוק ב-Word מהמודל הקנוני');ap.add_argument('--model',required=True,help='playbook-model.json');ap.add_argument('--profile',required=True,help='פרופיל-לקוח.json');ap.add_argument('--version',default='one',choices=['one','short','full'],help='one (ברירת המחדל) = קובץ אחד בשני חלקים: המדיניות, ואחריה הנימוקים והנספחים. short ו-full נשארו לפלייבוקים ישנים');ap.add_argument('--out',help='נתיב הקובץ. תו שאסור בשם קובץ ב-Windows מוחלף בתו בטוח');ap.add_argument('--out-dir',help='תיקיית הסוג: שם הקובץ נבנה לפי word-export-spec.md, בשפת המסמך');ap.add_argument('--lang',choices=['he','en'],help='שפת המסמך. בלעדיו: deliverable_language מהפרופיל או מהמודל, וברירת המחדל עברית');a=ap.parse_args()
	if not(a.out or a.out_dir):ap.error('נדרש --out או --out-dir')
	d=json.load(io.open(a.model,encoding='utf-8'));prof=json.load(io.open(a.profile,encoding='utf-8'))
	if not d.get('rules'):print('במודל אין כללים. אין ממה לבנות מסמך.');return 1
	lang=S.deliverable_lang(d,prof,a.lang)
	if a.out:folder,name=os.path.split(a.out);out=os.path.join(folder,safe_filename(name,lang)or'playbook.docx')
	else:out=os.path.join(a.out_dir,spec_filename(d,prof,lang))
	try:out=guard_out(out,inputs=[a.model,a.profile],allow_existing_doc=os.path.isfile(out)and is_built_playbook(out))
	except OutputRefused as exc:print('refused: %s'%exc);return 2
	build(d,prof,out,{'one':'one','full':True,'short':False}[a.version],lang,model_path=a.model);print('נבנה %s (%s, %d נושאים, שפה: %s)'%(out,{'one':'קובץ אחד בשני חלקים','full':'מלאה','short':'מקוצרת'}[a.version],len(d['rules']),lang));print('לפני מסירה: verify_playbook_docx.py על הקובץ. קוד יציאה 3 = אין למסור.');return 0
if __name__=='__main__':raise SystemExit(main())
