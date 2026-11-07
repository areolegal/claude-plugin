# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
from urllib.parse import unquote
CASE_LAW_HOSTS='court.gov.il','supreme.court.gov.il','elyon1.court.gov.il','takdin.co.il','psakdin.co.il','lawdata.co.il','dinonline.co.il','judgments.gov.il','caselaw.nationalarchives.gov.uk','find-case-law.service.gov.uk','bailii.org','judiciary.uk','supremecourt.uk','courts.ie','supremecourt.gov','uscourts.gov','courtlistener.com','casetext.com','casemine.com','leagle.com','nycourts.gov','courts.ca.gov','courts.delaware.gov','txcourts.gov','courts.state.ny.us','ttabvue.uspto.gov','pacer.gov','curia.europa.eu','hudoc.echr.coe.int','echr.coe.int','icj-cij.org','pca-cpa.org','italaw.com','canlii.org','austlii.edu.au','hklii.hk','nzlii.org','saflii.org','worldlii.org','commonlii.org','bger.ch','bundesgerichtshof.de','bverfg.de','bundesarbeitsgericht.de','courdecassation.fr','conseil-etat.fr','orzeczenia.ms.gov.pl','sn.pl','poderjudicial.es','cortedicassazione.it','rechtspraak.nl','ecourts.gov.in','sci.gov.in','elitigation.sg','judiciary.gov.sg','vlex.com','cylaw.org','fwc.gov.au','rechtsprechung-im-internet.de','openjur.de','dejure.org','juridat.be','stf.jus.br','stj.jus.br','jusbrasil.com.br','yargitay.gov.tr','danistay.gov.tr','kararlar.gov.tr'
CASE_LAW_PATHS=('nevo.co.il',re.compile('/(psika|psikasearch|psika_html|verdicts?)',re.I)),('gov.il',re.compile('(labor_court|court_verdicts|verdicts|/psika|judgments?|spokmanship_court|ruling-standards-violations|appeals-committee-decisions|registrar-decisions)',re.I)),('gov.uk',re.compile('/(employment-tribunal-decisions|employment-appeal-tribunal-decisions|tax-and-chancery-tribunal-decisions|administrative-appeals-chamber-decisions|immigration-asylum-chamber-decisions|residential-property-tribunal-decisions)',re.I)),('eur-lex.europa.eu',re.compile('(CELEX[:%3A]+6\\d|/juri|ECLI)',re.I)),('legifrance.gouv.fr',re.compile('/(juri|ceta|constit|cnil)/',re.I)),('mass.gov',re.compile('/orgs/(supreme-judicial-court|appeals-court|trial-court)|/info-details/massachusetts-law-about',re.I)),('law.cornell.edu',re.compile('/supremecourt|/supct',re.I)),('justia.com',re.compile('(^|/)cases?/|supreme\\.justia',re.I)),('gov.pl',re.compile('orzeczeni',re.I)),('boe.es',re.compile('/buscar/jurisprudencia',re.I)),('bka.gv.at',re.compile('judikatur',re.I)),('ejustice.just.fgov.be',re.compile('/cgi/juris|juridat',re.I)),('lexml.gov.br',re.compile('urn:lex:br:[^/?#]*(tribunal|justica|turma|jurisprudencia)|jurisprudencia',re.I)),('scholar.google.com',re.compile('/scholar_case|[?&]as_sdt=[^&]*[2-9]',re.I)),('data.uspto.gov',re.compile('^/ptab',re.I)),('uspto.gov',re.compile('/patents/ptab/(decisions|precedential)',re.I)),('epo.org',re.compile('(case-law-appeals|boards-of-appeal|/legal/case-law)',re.I)),('euipo.europa.eu',re.compile('boards-of-appeal',re.I)),('eppo.europa.eu',re.compile('(judgments?|verdicts?|convictions?)',re.I))
CASE_LAW_HOST_RX=re.compile('(^|[.\\-])(courts?|cour|gericht\\w*|tribunals?|judiciary|judicial|[a-z]*lii|caselaw|jurisprudence|juris|psika)([.\\-]|$)',re.I)
def _split(url):B=re.sub('^[a-z][a-z0-9+.\\-]*://','',(url or'').strip(),flags=re.I);A,D,C=B.partition('/');A=A.split('@')[-1].split(':')[0].lower().rstrip('.');return A,'/'+unquote(C).replace(chr(92),'/')
def _on(host,dom):return host==dom or host.endswith('.'+dom)
def case_law_url(url):
	A,C=_split(url)
	if not A:return
	for B in CASE_LAW_HOSTS:
		if _on(A,B):return'%s הוא אתר בית משפט או מאגר פסיקה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)'%A
	for(B,D)in CASE_LAW_PATHS:
		if _on(A,B)and D.search(C):return'%s%s הוא מדור פסיקה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)'%(A,C[:60])
	if CASE_LAW_HOST_RX.search(A):return'%s נראה כאתר בית משפט או מאגר פסיקה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)'%A
CITATION_RX=re.compile('(?<![\\w\u0590-\u05ff])[ובלמשכה]{0,2}(ע\\"?א|ע״א|רע\\"?א|רע״א|בג\\"?ץ|בג״ץ|דנ\\"?א|דנ״א|ע\\"?ע|ע״ע|ע\\"?פ|ע״פ|רע\\"?פ|ת\\"?א|ת״א|ה\\"?פ|ה״פ|עת\\"?ם|עת״ם|עע\\"?ם|עע״ם|ע\\"?מ|ע״מ|ס\\"?ע|ס״ע|ב\\"?ש|ב״ש|תא\\"?מ|תא״מ|ת\\"?צ|ת״צ|רע\\"?ב|רע״ב|דב\\"?ע|דב״ע)\\s*\\(?[\u0590-\u05ff\\"״\' -]*\\)?\\s*\\d{1,6}[-/]\\d{2,4}'),re.compile("\\[(1[5-9]|20)\\d{2}\\]\\s*(UKSC|UKPC|UKHL|EWCA|EWHC|UKUT|UKFTT|UKEAT|EAT|IESC|IEHC|SGCA|SGHC|HCA|NZSC|SCC|CSIH|CSOH|NICA|AC|QB|KB|Ch|WLR|All\\s?ER|Lloyd's\\s?Rep|IRLR|BCLC|ICR)\\b"),re.compile('\\bEWCA\\s+(Civ|Crim)\\b|\\bEWHC\\s+\\d+\\s*\\((Ch|QB|KB|Comm|TCC|Pat|IPEC|Admin|Fam)\\)'),re.compile('\\b(Case|Joined\\s+Cases|Cases)\\s+[CTF]-\\d{1,4}/\\d{2}\\b'),re.compile('\\bECLI:[A-Z]{2}:[A-Z0-9]+:\\d{4}:[A-Z0-9.]+'),re.compile('\\b\\d{1,4}\\s+(U\\.S\\.|S\\.\\s?Ct\\.|L\\.\\s?Ed\\.(\\s?2d)?|F\\.(2d|3d|4th)?|F\\.\\s?Supp\\.(\\s?[23]d)?|A\\.(2d|3d)|N\\.E\\.(2d|3d)|N\\.Y\\.S\\.(2d|3d)?|Cal\\.\\s?Rptr\\.(\\s?[23]d)?|Del\\.\\s?Ch\\.)\\s+\\d{1,5}\\b'),re.compile("\\b[A-Z][\\w.&'\\- ]{1,60}\\s+v\\.?\\s+[A-Z][\\w.&'\\- ]{1,60},?\\s+\\d{1,4}\\s+(U\\.S\\.|F\\.|S\\.\\s?Ct\\.)"),re.compile('\\bBGH,?\\s+(Urteil|Beschluss)\\b|\\bCass\\.\\s+(civ|com|soc)\\b',re.I)
def case_law_hits(text):
	A=[]
	for B in CITATION_RX:
		for C in B.finditer(text or''):A.append(C.group(0).strip())
	return A
CASE_LAW_EXTRA=re.compile('פס"ד|פס״ד|פסק הדין|פסקי הדין|הלכת\\s|הפסיקה קבעה|\\b[A-Z][A-Za-z&]+ v\\.? [A-Z][A-Za-z]+\\b')
def case_law_mentions(text):B=case_law_hits(text);A=CASE_LAW_EXTRA.search(text or'');return B+([A.group(0)]if A else[])
def case_law_problem(text,connector=None):
	if connector:return
	A=case_law_hits(text)
	if A:return'אזכור פסיקה בלי מחבר פסיקה סגור (כלל 1.1): %s'%'; '.join(A[:3])
def _walk_strings(obj):
	A=obj
	if isinstance(A,str):yield A
	elif isinstance(A,dict):
		for B in A.values():yield from _walk_strings(B)
	elif isinstance(A,(list,tuple)):
		for B in A:yield from _walk_strings(B)
def case_law_in_data(obj,connector=None):
	if connector:return[]
	A=[]
	for B in _walk_strings(obj):A.extend(case_law_hits(B))
	return A
