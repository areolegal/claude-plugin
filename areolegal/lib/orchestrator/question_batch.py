# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
from orchestrator.state_builder import SITUATIONS
from orchestrator import proportionality as P
LABEL={'he':'נדרשת הכרעתך','en':'Your decision is needed'}
BLOCKS='צריך לפני שליחה, תשובה של מילה אחת'
TXT={'he':{'sit':'מצב','blocks':BLOCKS,'rec':' המלצה: %s.','asked':'כבר נשאלה','free':'הסכם בלי תמורה','opts':['לאשר את כל ההמלצות','לשנות שורה'],'group':'כמה נושאים דומים:\n   | הנושא | ההמלצה |\n'},'en':{'sit':'situation','blocks':'needed before sending, one-word answer','rec':' Recommendation: %s.','asked':'already asked','free':'agreement without consideration','opts':['Approve all recommendations','Change a row'],'group':'Several similar topics:\n   | Topic | Recommendation |\n'}}
STANCE={'he':{'text':'איך להחיל את הפלייבוק בעסקה הזו? לפי הפלייבוק: העמדה שבפלייבוק בכל סעיף. מחמירה: מחזיקים בעמדה המועדפת גם במקום שהפלייבוק מתיר לוותר, ומבקשים גם בנושאים משניים. מקלה: מקבלים נוסח שלהם שבטווח שהפלייבוק מתיר, ומבקשים רק בנושאים החשובים. מה שלא מקבלים נשאר כך בכל גישה.','rec':'לפי הפלייבוק','opts':['לפי הפלייבוק (ההמלצה)','גישה מחמירה יותר','גישה מקלה יותר']},'en':{'text':'How should the playbook be applied in this deal? By the playbook: the playbook position in each clause. Stricter: hold the preferred position even where the playbook allows a concession, and ask on minor topics too. More lenient: accept their wording where it is within the range the playbook allows, and ask only on the important topics. What you never accept stays the same in every approach.','rec':'By the playbook','opts':['By the playbook (recommended)','A stricter approach','A more lenient approach']}}
STANCE_VALUES='playbook','stricter','lenient'
NAME_EN={'he':{'lawyer_name_en':('באיזה שם באנגלית לחתום על ההערות לצד השני?','<השם באנגלית>'),'entity_name_en':('מה השם הרשום של החברה באנגלית, כפי שהוא מופיע במרשם?','<השם הרשום באנגלית>')},'en':{'lawyer_name_en':('Which English name should sign the comments to the other side?','<the name in English>'),'entity_name_en':("What is the company's registered name in English?",'<the registered name>')}}
COMMENT_NAME={'he':('באיזה שם לרשום את ההערות שיוצאות לצד השני?','המחלקה המשפטית, %s','המחלקה המשפטית'),'en':('Which name should sign the comments to the other side?','Legal Department, %s','Legal Department')}
def comment_name_item(profile,lang='he'):
	A=profile or{}
	if A.get('lawyer_name'):return[]
	D,E,F=COMMENT_NAME[_lang(lang)];B=A.get('organization_name')or'';C=E%B if B else F;return[{'key':'lawyer_name','kind':'lawyer_name','situation':None,'blocks_sending':True,'text':D,'recommendation':C,'options':[C]}]
def english_name_items(profile,lang='he'):
	A=profile or{};B=NAME_EN[_lang(lang)];C=[]
	if A.get('lawyer_name')and not A.get('lawyer_name_en'):C.append({'key':'lawyer_name_en','kind':'lawyer_name_en','situation':None,'blocks_sending':True,'text':B['lawyer_name_en'][0],'options':[B['lawyer_name_en'][1]]})
	if A.get('organization_name')and not A.get('organization_name_en'):C.append({'key':'entity_name_en','kind':'entity_name_en','situation':None,'blocks_sending':True,'text':B['entity_name_en'][0],'options':[B['entity_name_en'][1]]})
	return C
def stance_item(lang='he'):A=STANCE[_lang(lang)];return{'key':'stance','kind':'stance','text':A['text'],'recommendation':A['rec'],'options':list(A['opts']),'situation':None,'blocks_sending':False}
ACTIVATION={'he':{'text':'בהסכמים שמהם למדנו את המדיניות אין צד שני מסוג %s. איך להחיל אותה בעסקה הזו?','rec':'להחיל ולסמן כל הבדל','opts':['להחיל ולסמן כל הבדל (מומלץ)','להחיל כמו שהיא']},'en':{'text':'The agreements we learned the policy from have no other party of type %s. How should it be applied in this deal?','rec':'Apply it and flag every difference','opts':['Apply it and flag every difference (recommended)','Apply it as is']}}
ACTIVATION_OPEN={'he':'במדיניות עוד אין עמדה מול צד שני מסוג %s ("%s"). איך להחיל אותה בעסקה הזו?','en':'The policy has no position yet for another party of type %s ("%s"). How should it be applied in this deal?'}
KIND_LABELS={'he':{'public_body':'גוף ציבורי','university':'מוסד להשכלה גבוהה או אוניברסיטה','non_profit':'עמותה, חל"צ, הקדש או מלכ"ר','npo':'עמותה, חל"צ, הקדש או מלכ"ר','government_company':'חברה ממשלתית','foreign':'צד זר','large_enterprise':'תאגיד גדול','large':'תאגיד גדול','sme':'עסק קטן או בינוני','small':'עסק קטן או בינוני','consumer':'צרכן','individual':'אדם, כולל עוסק יחיד','company':'חברה','group':'חברה בקבוצה'},'en':{'public_body':'public body','university':'university','non_profit':'non-profit or charity','npo':'non-profit or charity','government_company':'government company','foreign':'foreign party','large_enterprise':'large enterprise','large':'large enterprise','sme':'SME','small':'SME','consumer':'consumer','individual':'individual','company':'company','group':'group company'}}
def kind_label(kind,lang='he'):A=kind;B=A if isinstance(A,(list,tuple))else str(A or'').split(',');C=KIND_LABELS[_lang(lang)];return', '.join(C.get(str(A).strip().lower(),str(A).strip())for A in B if str(A).strip())
def activation_item(resolution,lang='he',kind_segment=None):
	C=lang;A=resolution or{}
	if A.get('activation_ok')is not False or kind_segment or A.get('kind_segment'):return
	D=ACTIVATION[_lang(C)];E=kind_label(A.get('counterparty_kind'),C)or'?';B=[A for A in A.get('activation_reasons')or()if isinstance(A,dict)];F=D['text']%E
	if B and all(A.get('code')=='open_question'for A in B):F=ACTIVATION_OPEN[_lang(C)]%(E,B[0].get('question')or B[0].get('text')or'')
	return{'key':'playbook_activation','kind':'activation','situation':4,'text':F,'recommendation':D['rec'],'options':list(D['opts']),'blocks_sending':False}
def _lang(lang):return'en'if str(lang or'').lower()[:2]=='en'else'he'
def label_for(situation,blocks_sending=False,lang='he'):
	B=situation;A=lang
	if B not in SITUATIONS:raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r'%(B,))
	A=_lang(A);C=TXT[A];return'%s (%s)'%(LABEL[A],C['blocks'])if blocks_sending else LABEL[A]
def _line(n,it,lang='he'):A=it;B=' '.join('[%s]'%A for A in A.get('options',[]));C=TXT[_lang(lang)]['rec']%A['recommendation'].rstrip('.')if A.get('recommendation')else'';D='**%s:** '%label_for(A['situation'],A.get('blocks_sending'),lang)if A.get('situation')else'';return('%d. %s%s%s %s'%(n,D,A['text'].rstrip(),C,B)).rstrip()
def answer_type(it):return'free'if any('<'in str(A)and'>'in str(A)for A in it.get('options')or())else'choice'
def build_batch(items,no_consideration=False,asked_before=(),max_questions=8,status_line=None,lang='he',strategy=None,round_number=None):
	S=strategy;R=status_line;L=lang;G=max_questions;H=TXT[_lang(L)];C=_lang(L);e=set(asked_before or());B,M,T,U=[],[],set(),set()
	for A in items:
		if A.get('situation')is not None and A['situation']not in SITUATIONS:raise ValueError('אין מצב עשירי ל"נדרשת הכרעתך": %r'%(A['situation'],))
		E=A.get('key')or A['text'];I=' '.join(str(A.get('text')or'').split())
		if E in e or E in T or I and I in U:M.append({'key':E,'why':H['asked']});continue
		if I:U.add(I)
		if no_consideration and A.get('kind')=='deal_card_value':M.append({'key':E,'why':H['free']});continue
		T.add(E);A=dict(A);A['text']=A.get('text')or'';D=strategy_marks(S,item_clause_ids(A),A.get('clause'))if S else None
		if D and(D.get('red_line_edge')or D.get('packages')):
			A['strategy_marks']=D;A['red_line_edge']=bool(D.get('red_line_edge'))or bool(A.get('red_line_edge'));F=marks_text(D,C)
			if F.strip()not in A['text']:A['text']=A['text'].rstrip()+F
		if A.get('kind')=='composite':A=composite_item(A,C,round_number)
		if A.get('kind')=='counter_tighter':
			A['situation']=2;F=COUNTER_EDGE[C]%_short((A.get('strategy_marks')or{}).get('red_line_edge',[''])[0]or'?')if A.get('red_line_edge')else COUNTER[C]
			if F.strip()not in A['text']:A['text']=A['text'].rstrip()+F
		N=requires_explicit(A)
		if N:
			A['requires_explicit']=True;A['requires_explicit_why']=N
			if N=='operational'or A.get('operational'):
				V=operational_owner(A,C);A['owner_question']=OWNER_Q[C]%V
				if A['owner_question'].strip()not in A['text']:A['text']=A['text'].rstrip()+A['owner_question']
				W=OWNER_OPT[C]%V
				if W not in(A.get('options')or()):A['options']=list(A.get('options')or())+[W]
			if EXPLICIT_NOTE[C].strip()not in A['text']:A['text']=A['text'].rstrip()+EXPLICIT_NOTE[C]
		if A.get('kind')=='legal_review':continue
		B.append(A)
	B.sort(key=lambda x:(not x.get('blocks_sending'),0 if x.get('kind')=='stance'else x.get('situation')or 99))
	if len(B)>G:
		J,X=[],{}
		for A in B:
			if A.get('situation')and not A.get('blocks_sending')and not(A.get('requires_explicit')and answer_type(A)=='choice'):X.setdefault((A['situation'],answer_type(A)),[]).append(A)
			else:J.append(A)
		for((O,Y),P)in sorted(X.items()):
			if len(P)==1:J.append(P[0]);continue
			f='\n'.join('   | %s | %s |'%(A['text'].rstrip('.'),A.get('recommendation',''))for A in P);J.append({'key':'situation-%d'%O if Y=='choice'else'situation-%d-%s'%(O,Y),'situation':O,'options':list(H['opts']),'text':H['group']+f})
		B=J
	Q=[A for A in B if A.get('kind')in PROCESS_KINDS and not A.get('situation')and not A.get('blocks_sending')]
	if len(Q)>1:B=[A for A in B if A not in Q]+[process_group(Q,C)]
	g,K,Z=[],[],0
	if len(B)>G:a=lambda q:q.get('blocks_sending')or q.get('requires_explicit');b=[A for A in B if a(A)];c=[A for A in B if not a(A)];d=max(0,G-len(b));K.extend(c[d:]);h={id(A)for A in b+c[:d]};B=[A for A in B if id(A)in h];Z=max(0,len(B)-G)
	i=(COUNT_NONE[C]if not B else COUNT_ONE[C]if len(B)==1 else COUNT_LINE[C]%len(B))+(COUNT_OVER[C]%len([A for A in B if A.get('blocks_sending')or A.get('requires_explicit')])if Z else'')+(COUNT_MORE[C]%len(K)if K else'');j=([R]if R else[])+[i]+[_line(A,B,L)for(A,B)in enumerate(B,1)];return{'text':'\n'.join(j),'questions':B,'skipped':M,'requires_explicit':[A.get('key')for A in B if A.get('requires_explicit')],'memos':[A['memo']for A in B if A.get('memo')],'deferred':[A.get('key')for A in g],'applied_by_recommendation':[A.get('key')for A in K]}
PROCESS_KINDS='stance','components','research_referral','file_prefix','bubble_language','entity_name_en','lawyer_name_en','lawyer_name'
COUNT_LINE={'he':'לפני שנכין את התגובה: %d שאלות.','en':'Before we prepare the response: %d questions.'}
COUNT_ONE={'he':'לפני שנכין את התגובה: שאלה אחת.','en':'Before we prepare the response: one question.'}
COUNT_NONE={'he':'אין שאלות. ממשיכים להכנת התגובה.','en':'No questions. We are preparing the response.'}
COUNT_OVER={'he':' %d מהן דורשות את ההכרעה שלכם, ולכן הן כאן גם מעבר ל-8. אחרי התשובות העבודה רצה עד הסוף בלי עצירה.','en':' %d of them need your decision, so they are here even beyond 8. After your answers the work runs to the end without stopping.'}
COUNT_MORE={'he':' %d נושאים קטנים הכרענו לפי ההמלצה, ותוכלו לעבור עליהם בסוף.','en':' We decided %d minor topics by the recommendation; you can review them at the end.'}
PROCESS_HEAD={'he':'ועוד כמה שאלות קצרות:','en':'And a few short questions:'}
LETTERS={'he':'אבגדהוזחטי','en':'abcdefghij'}
def process_group(items,lang='he'):
	C=items;A=_lang(lang);D=[]
	for(E,B)in enumerate(C):F=' '.join('[%s]'%A for A in B.get('options')or());G=TXT[A]['rec']%B['recommendation'].rstrip('.')if B.get('recommendation')else'';D.append('(%s) %s%s %s'%(LETTERS[A][E%len(LETTERS[A])],B['text'].rstrip(),G,F))
	return{'key':'process','kind':'process','situation':None,'blocks_sending':False,'group_keys':[A.get('key')or A.get('text')for A in C],'options':[],'text':PROCESS_HEAD[A]+' '+' '.join(A.rstrip()for A in D)}
ROUND_MATRIX={'opening':{'goal':{'he':'פתיחה: עמדה מלאה ומנומקת','en':'Opening: a full, reasoned position'},'retreat':{'he':'לפי round1_posture: hold_green הירוק; offer_yellow הנסיגה הראשונה בלבד. לעולם לא הנסיגה האחרונה','en':'Per round1_posture: hold_green the green; offer_yellow the first fallback only. Never the last fallback'},'max_sentences':4,'max_words':100,'tone':{'he':'ענייני ומנומק, בגוף ראשון רבים ("We have..."), בלי פתיח קבוע','en':'Factual and reasoned, first person plural ("We have..."), no set opener'},'on_acceptance':{'he':'קבלה של שינוי שלהם: אין בועה. כשהם נימקו בבועה: תשובה בשרשור במשפט עובדתי אחד ("We accept this change.")','en':'Accepting their change: no comment. If they explained it in a comment: a one-sentence factual reply in the thread'}},'response':{'goal':{'he':'תגובה: רק מה שהשתנה, והתשובות שלהם בשרשור','en':'Response: only what changed, and their replies in the threads'},'retreat':{'he':'מדרגה אחת לכל היותר, תמורת תזוזה שלהם; לא הנסיגה האחרונה. אחרי דחייה אחת: מדרגת ביניים, גם כשבפלייבוק נסיגה אחת בלבד: הירוק בלי הרכיבים שהם דחו במפורש ושאינם בקו האדום, ועם הנסיגה הראשונה (או זכות הסיום של השירות המושפע). הצעה נגדית שלהם שהדוקה מהנסיגה האחרונה אבל סבירה: נדרשת הכרעתך (מצב 2), עם המלצה','en':'At most one step, in return for movement on their side; not the last fallback. After one rejection: an intermediate step, also when the playbook has a single fallback: the green without the components they expressly rejected that are not in the red line, plus the first fallback (or the right to end the affected service). A reasonable counter tighter than our last fallback: your decision is needed (situation 2)'},'max_sentences':3,'max_words':60,'tone':{'he':'משיב לנימוק שלהם ומוסיף רק מה שחדש. בלי "כפי שהסברנו" ובלי לחזור על נימוק שנדחה','en':'Answers their reasoning and adds only what is new. No "as explained" and no repeated rejected reasoning'},'on_acceptance':{'he':'הצעה שלנו שהתקבלה: אין בועה ואין תשובה, גם לא ל-"Agreed" שלהם. שינוי שלהם שקיבלנו: כמו בסבב 1','en':'Our proposal accepted: no comment and no reply, not even to their "Agreed". Their change we accept: as in round 1'}},'closing':{'goal':{'he':'סגירה: חבילות, ומה שנשאר מוצג למשתמש','en':'Closing: packages, and what is left goes to the user'},'retreat':{'he':"הנסיגה האחרונה רק אחרי הצגה בצ'אט ורישום ב-posture_confirmation. מעבר לה: STUCK או WALK-AWAY, נדרשת הכרעתך (מצב 2)",'en':'The last fallback only after it was shown in chat and recorded in posture_confirmation. Beyond it: STUCK or WALK-AWAY, your decision is needed (situation 2)'},'max_sentences':2,'max_words':40,'tone':{'he':'סגירה: ניסוח חבילה ("נוכל לקבל X, ובלבד ש-Y"), בלי פתח כללי לשיחה','en':'Closing: package wording ("We can accept X, provided that Y"), no general invitation to talk'},'on_acceptance':{'he':'כמו בסבב 2, והשרשורים של נושאים שנסגרו מסומנים "בוצע" (round_tools.py resolve-threads), ואינם נענים','en':'As in round 2, and threads on closed topics are marked done (round_tools.py resolve-threads), with no reply'}}}
ESCALATION_ROUNDS=4
ESCALATION_WEEKS=6
BANNED={'all':['^\\s*(?:agreed|accepted|noted|מוסכם|מקובל|מקובל עלינו)\\s*[.!]?\\s*$','ההכרעה הייתה ברורה','the (?:decision|position) was clear'],'repeat':['^\\s*(?:as (?:previously |we have )?explained|as (?:stated|noted|mentioned) (?:previously|before|above)|further to our (?:previous )?comment)','^\\s*(?:כפי שהסברנו|כפי שציינו|כאמור בסבב הקודם|כאמור בהערתנו)'],'closing':['happy to discuss|open to discuss|glad to discuss|נשמח לדון|פתוחים לדיון|נשמח לשוחח']}
PRECEDENCE='גוברות|יגבר|יגברו|עדיפות|prevail|precedence|order of priority'
def round_row(round_number,lang='he'):from orchestrator.state_builder import stage_for_round as D;C=D(round_number);A=ROUND_MATRIX[C];B=_lang(lang);return{'stage':C,'goal':A['goal'][B],'retreat':A['retreat'][B],'max_sentences':A['max_sentences'],'max_words':A['max_words'],'tone':A['tone'][B],'on_acceptance':A['on_acceptance'][B]}
def _sentences(text):import re;A=[A for A in re.split('(?<=[.!?;])\\s+(?=[A-Z"“(א-ת0-9])',(text or'').strip())if A.strip()];return len(A)
def _words(text):return len((text or'').split())
INTERMEDIATE='intermediate','intermediate_step'
SYNONYMS={'cost':('cost','expense','charge','עלות','הוצא','חשבון'),'expense':('cost','expense','charge','עלות','הוצא','חשבון'),'report':('report','certification','דוח','הסמכ'),'consent':('consent','approval','הסכמה','אישור'),'עלות':('cost','expense','עלות','הוצא','חשבון'),'דוח':('report','דוח')}
STOP={'the','and','for','with','that','this','from','any','all','its','their','our','shall','will','of','to','in','on','by','or','be','is','are','a','an','first','party','third','של','על','את'}
DROPPED='\\b(?:removed|deleted|dropped|withdrawn|no longer|we have taken out|we do not (?:pursue|insist))\\b|הסרנו|ויתרנו|נמחק|הוסר|אינו עוד|איננו עומדים'
WILL_REVERT='\\bwill (?:revert|come back|get back|propose|send (?:you )?(?:a|our) (?:proposal|counter))|\\btaking instructions\\b|\\brevert to you\\b|נחזור אליכם|נחזור עם הצעה|נעביר הצעה|נבדוק ונחזור'
_CUR_CODE='(?-i:\\b(?:USD|EUR|GBP|ILS|NIS|CHF|SGD|JPY|CNY|RMB|HKD|AUD|CAD|NZD|SEK|NOK|DKK|PLN|CZK|HUF|INR|AED|SAR|ZAR|BRL|MXN|KRW|TRY|RON|BGN|ISK)\\b)'
_CUR_WORD='(?:ש"ח|ש״ח|שקלים|שקל|ש"ח חדשים|דולר(?:ים)?|אירו|יורו|ליש"ט|ליש״ט|לירות שטרלינג|לירה שטרלינג|פרנק(?:ים)?|ין|dollars?|euros?|pounds? sterling|pounds?|sterling|francs?|yen|shekels?)'
_NUM_AMT='\\d[\\d,.]*(?:\\s?(?:million|billion|thousand|m|bn|k|מיליון|מיליארד|אלף))?'
AMOUNT='[£$€₪¥₣₹]\\s?\\d[\\d,.]*|'+_CUR_CODE+'\\s?'+_NUM_AMT+'|\\b'+_NUM_AMT+'\\s?(?:'+_CUR_CODE+'|'+_CUR_WORD+'(?![\\w\u0590-\u05ff])|million|מיליון)'
INSURANCE='insurance|insured|indemnity insurance|cover\\b|ביטוח|פוליס'
def _component_terms(item):
	B=item;import re
	if isinstance(B,dict):E=list(B.get('terms')or())or re.findall('[\\w\u0590-\u05ff-]+',str(B.get('component')or''))
	else:E=re.findall('[\\w\u0590-\u05ff-]+',str(B or''))
	C=set()
	for A in E:
		A=A.lower().strip('-')
		if len(A)<3 or A in STOP:continue
		D=A[:-1]if A.endswith('s')and len(A)>4 else A;C.add(D)
		for(F,G)in SYNONYMS.items():
			if D.startswith(F)or F.startswith(D):C.update(G)
	return C
def _has_term(text,terms):import re;B=(text or'').lower();C=lambda t:'[והבכלמש]{0,3}'if re.match('[א-ת]',t)else'';return next((A for A in terms if re.search('(?<![\\w\u0590-\u05ff])%s%s'%(C(A),re.escape(A)),B)),None)
def _content_words(s):import re;return{A for A in re.findall('[\\w\u0590-\u05ff]+',(s or'').lower())if len(A)>2 and A not in STOP}
def thread_of(threads,comment_id):
	B=comment_id
	for A in threads or():
		if str(A.get('root_id'))==str(B)or any(str(A.get('id'))==str(B)for A in A.get('entries')or()):return A
def rejected_argument_findings(d,previous=(),threads=None):
	import re;C=[];H=d.get('their_rejected')or()
	if not H:return C
	D=list(previous or())
	if not D and d.get('reply_to_comment'):K=thread_of(threads,d['reply_to_comment']);D=[A.get('text')or''for A in(K or{}).get('entries')or()if A.get('ours')and not A.get('new')]
	D=D+[A for A in(d.get('previous_external_comment'),)if A];L=d.get('external_comment')or'';M=' '.join(str(d.get(A)or'')for A in('new','new_text','text'));N=(d.get('user_decision')or{}).get('answer_kind')=='explicit'
	for A in H:
		F=A.get('component')if isinstance(A,dict)else str(A);I=isinstance(A,dict)and bool(A.get('red_line'));E=_component_terms(A)
		if not E:continue
		if not I and not N and _has_term(M,E):C.append({'code':'ROUND_REJECTED_COMPONENT_REOFFERED','id':d.get('id'),'message':'הרכיב "%s" נדחה במפורש ואינו בקו האדום, והוא חוזר בנוסח החדש. מדרגת ביניים מוותרת עליו'%F})
		B=[A for A in _split_sentences(L)if _has_term(A,E)]
		if not B:continue
		if not I:
			B=[A for A in B if not re.search(DROPPED,A,re.I)]
			if not B:continue
			C.append({'code':'ROUND_REPEATS_REJECTED_ARGUMENT','id':d.get('id'),'message':'הבועה חוזרת על טיעון ברכיב שהצד השני דחה ("%s"): "%s". רכיב שוויתרנו עליו אינו נטען שוב'%(F,B[0][:90])});continue
		O=[A for B in D for A in _split_sentences(B)if _has_term(A,E)]
		for J in B:
			G=_content_words(J)
			if any(G and len(G&_content_words(A))>=.5*len(G)for A in O):C.append({'code':'ROUND_REPEATS_REJECTED_ARGUMENT','id':d.get('id'),'message':'הבועה חוזרת על הנימוק שלנו מהסבב הקודם ברכיב שנדחה ("%s"): "%s". עונים לנימוק שלהם, או מוסיפים נימוק חדש'%(F,J[:90])});break
	return C
def _split_sentences(text):import re;return[A.strip()for A in re.split('(?<=[.!?;])\\s+',(text or'').strip())if A.strip()]
def round_violations(decisions,round_number,state=None,lang='he',threads=None):
	Q=threads;P=state;O=round_number;K=decisions;import re as B;from orchestrator.state_builder import stage_for_round as V;W=(K or{}).get('decisions',[])if isinstance(K,dict)else list(K or[]);C=V(O);I=ROUND_MATRIX[C];D=[];X={A.get('clause_id')for A in((P or{}).get('posture_confirmation')or{}).get('items')or()};Y={A.get('clause_id')for A in(P or{}).get('clauses')or()if any(isinstance(A,dict)and A.get('by')=='them'and int(A.get('round')or 0)==int(O)for A in A.get('rejections')or())};R={}
	for A in W:
		E=A.get('id')
		if C!='opening':
			Z=(A.get('user_decision')or{}).get('answer_kind')=='explicit'
			if(A.get('their_rejected')or E in Y)and A.get('offered_now')=='green'and A.get('op')in('replace','replace_span','insert_paragraph')and not Z and not(A.get('no_step_reason')or'').strip()and A.get('status')!='STUCK':D.append({'code':'ROUND_HOLD_AFTER_REJECTION','id':E,'message':'אחרי דחייה אחת ההכרעה מחזירה את הירוק. ברירת המחדל היא מדרגת ביניים (offered_now: intermediate), גם כשבפלייבוק נסיגה אחת בלבד: הירוק בלי הרכיבים שהם דחו במפורש ושאינם בקו האדום, ועם הנסיגה הראשונה, או זכות הסיום של השירות המושפע. אין מדרגה אפשרית: no_step_reason'})
			D+=rejected_argument_findings(A,threads=Q);F=thread_of(Q,A.get('reply_to_comment'))if A.get('reply_to_comment')else None
			if F and any(A.get('new')and not A.get('ours')and B.search(WILL_REVERT,A.get('text')or'',B.I)for A in F.get('entries')or()):
				if A.get('op')in('replace','replace_span','insert_paragraph','delete_paragraph')or _sentences(A.get('external_comment')or'')>1:D.append({'code':'ROUND_ARGUES_PENDING_PROPOSAL','id':E,'message':'הצד השני כתב שיחזור עם הצעה: אין שינוי בנוסח ואין טיעון חדש בבועה (משפט אחד לכל היותר). היעד והנסיגה לסבב הבא נקבעים בשאלה פנימית'})
			if F and F.get('root_ours')and not F.get('done')and A.get('op')in CHANGE_OPS and any(A.get('ours')and not A.get('new')for A in F.get('entries')or())and not B.search(REPLACES_RE,A.get('external_comment')or'',B.I):D.append({'code':'ROUND_STALE_PROPOSAL','id':E,'message':'עמדה חדשה בשרשור %s, שבו ההצעה הקודמת שלנו עדיין עומדת: התשובה פותחת ב-"%s"'%(F.get('root_id'),REPLACES[_bubble_lang(A.get('external_comment'))])})
		G=(A.get('external_comment')or'').strip()
		if G:
			L=B.sub(REPLACES_SENT,' ',G,flags=B.I).strip()or G;S,T=_sentences(L),_words(L)
			if S>I['max_sentences']or T>I['max_words']:D.append({'code':'ROUND_COMMENT_LONG','id':E,'message':'בועה של %d משפטים ו-%d מילים; בסבב %s עד %d משפטים ו-%d מילים'%(S,T,C,I['max_sentences'],I['max_words'])})
			J=' '.join(B.sub('[^\\w\u0590-\u05ff ]',' ',L.lower()).split()[:4])
			if len(J.split())==4:R.setdefault(J,[]).append(E)
			a=BANNED['all']+(BANNED['repeat']if C!='opening'else[])+(BANNED['closing']if C=='closing'else[])
			for U in a:
				if B.search(U,G,B.I):D.append({'code':'ROUND_BANNED_PHRASE','id':E,'message':'ניסוח אסור בסבב %s: %s'%(C,B.search(U,G,B.I).group(0).strip())});break
		if A.get('status')=='STUCK'and C!='closing'and A.get('escalation_basis')!='final_position'and(A.get('user_decision')or{}).get('answer_kind')!='explicit':D.append({'code':'ROUND_EARLY_STUCK','id':E,'message':'STUCK בסבב %s בלי בסיס: ברירת המחדל אחרי דחייה אחת היא MOVING, מדרגה אחת בנימוק חדש. הסלמה מוקדמת רק כשהצד השני כתב שהעמדה סופית (escalation_basis: final_position) או בהוראה מפורשת של המשתמש'%C})
		b=A.get('at_last_fallback')or A.get('offered_now')=='last_fallback'
		if b:
			c=C=='closing'and(E in X or(A.get('user_decision')or{}).get('answer_kind')=='explicit')
			if not c:D.append({'code':'ROUND_LAST_FALLBACK','id':E,'message':'נסיגה אחרונה בסבב %s%s'%(C,''if C=='closing'else": מותרת רק מסבב 3, אחרי הצגה בצ'אט")+(''if C!='closing'else' בלי רישום ב-posture_confirmation')})
		for H in A.get('dependents')or():
			if isinstance(H,dict)and H.get('keep'):
				M=(H.get('reason')or'').strip()
				if not M:D.append({'code':'DEPENDENT_KEEP_NO_REASON','id':E,'message':'תלוי (פסקה %s) נשאר בלי נימוק'%H.get('para')})
				elif B.search(PRECEDENCE,M,B.I)and len(M.split())<25:D.append({'code':'DEPENDENT_KEEP_PRECEDENCE','id':E,'message':'תלוי (פסקה %s) נשאר בהסתמך על סעיף גוברות, שהצד השני עלול לדחות: הכרעה עקבית בתלוי עצמו'%H.get('para')})
	for(J,N)in R.items():
		if len(N)>2:D.append({'code':'ROUND_REPEATED_OPENING','id':', '.join(str(A)for A in N),'message':'%d בועות פותחות ב-"%s": בלי פתיח מתוסרט שחוזר'%(len(N),J)})
	return D
COUNTER={'he':' זו אינה חריגה מקו אדום: הנוסח שלהם אינו מבטל את ההגנה, רק הדוק מהנסיגה. ההמלצה לגופו של עניין.','en':' This is not a red-line exception: their wording does not remove the protection, it is only tighter than our fallback. The recommendation is on the merits.'}
ESCALATION_WHY={'he':{'rejected_twice':'ההצעה שלנו, או המדרגה שאחריה, נדחתה בשני סבבים בלי תזוזה שלהם','final_position':'הצד השני כתב שהעמדה שלו סופית'},'en':{'rejected_twice':'our proposal, or the next step after it, was rejected in two rounds with no movement on their side','final_position':'the other side wrote that its position is final'}}
AMOUNT_REC={'he':{'silent':'לסמן מול הנוסח שחזר, עם הסכום שהחברה מחזיקה בפועל, ולא להחזיר גורפת לנוסח שנשלח','cert':'; אישור ביטוח (certificate of insurance) במקום הפוליסה','opts':['לסמן מול הנוסח שחזר, עם הסכום בפועל'],'q':'השינוי שלהם בסעיף %s נוגע לסכום (%s%s). מה הסכום שהחברה מחזיקה בפועל?','ins':', ביטוח','q_opts':['<הסכום בפועל>','לא ידוע: להחזיר לנוסח שנשלח']},'en':{'silent':'Mark against the returned wording, with the amount the company actually holds, rather than a blanket revert to the sent wording','cert':'; a certificate of insurance instead of the policy','opts':['Mark against the returned wording, with the actual amount'],'q':'Their change in clause %s concerns an amount (%s%s). What amount does the company actually hold?','ins':', insurance','q_opts':['<the actual amount>','Unknown: revert to the sent wording']}}
PREPARE={'he':{'text':'בסעיף %s הצד השני כתב שיחזור עם הצעה ("%s"). מה היעד שלנו, ומה הנסיגה, כדי להיות מוכנים לסבב הבא?','rec':'לקבוע עכשיו, פנימית, יעד ונסיגה. בסבב הזה אין שינוי בנוסח ואין טיעון חדש בבועה','opts':['יעד: <..>; נסיגה: <..>','לקבוע כשתגיע ההצעה']},'en':{'text':'In clause %s the other side wrote that it will come back with a proposal ("%s"). What is our target, and our fallback, so that we are ready for the next round?','rec':'Set the target and the fallback now, internally. In this round: no change to the wording and no new argument in the comment','opts':['Target: <..>; fallback: <..>','Decide when the proposal arrives']}}
def diff_window(a,b,ctx=60,mark=True):
	H=ctx;a,b=' '.join((a or'').split()),' '.join((b or'').split());A=0
	while A<min(len(a),len(b))and a[A]==b[A]:A+=1
	C=0
	while C<min(len(a),len(b))-A and a[len(a)-1-C]==b[len(b)-1-C]:C+=1
	def D(ch):return bool(ch)and(ch.isalnum()or ch in',.')
	def B(s,i):return D(s[i:i+1])
	if B(a,A)or B(b,A):
		while A>0 and D(a[A-1]):A-=1
	if B(a,len(a)-C-1)or B(b,len(b)-C-1):
		while C>0 and D(a[len(a)-C]):C-=1
	def E(s):
		D=len(s)-C;E,F=max(0,A-H),min(len(s),D+H)
		if E and' 'in s[E:A]:E=s.index(' ',E,A)+1
		if F<len(s)and' 'in s[D:F]:F=s.rindex(' ',D,F)
		B=s[A:D]
		if mark:
			G=B.strip();I,J=B[:len(B)-len(B.lstrip())],B[len(B.rstrip()):]if G else'';B=I+('**%s**'%G if G else'**[ריק]**')+J
			if not G and s[D:D+1]not in('',' '):B+=' '
			if not G and s[A-1:A]not in('',' '):B=' '+B
		return('...'if E else'')+s[E:A]+B+s[D:F]+('...'if F<len(s)else'')
	if a==b:return(a[:2*H]+('...'if len(a)>2*H else''),)*2
	return E(a),E(b)
def amount_item(clause,amount,insurance,round_number,para,lang='he'):B=insurance;C=_lang(lang);A=AMOUNT_REC[C];return{'key':'amount:r%s:%s'%(round_number,para),'kind':'internal_amount','situation':3,'blocks_sending':False,'text':A['q']%(clause,amount,A['ins']if B else''),'recommendation':A['silent']+(A['cert']if B else''),'options':list(A['q_opts'])}
def round_items(compare=None,state=None,round_number=None,lang='he',strategy=None):
	Q=state;O=compare;E=round_number;import re as F;from orchestrator.state_builder import stage_for_round as d;B=_lang(lang);C=B=='he';e=bool(E)and d(E)=='closing';D=[];f=set();U=set();Y=stale_target_items(O,Q,E,B,strategy);g={A.get('para')for A in Y}
	for A in(O or{}).get('clauses')or():
		if A.get('classification')not in('their_silent','their_tracked'):continue
		V=A.get('received_para')if A.get('received_para')is not None else A.get('sent_para');Z=A.get('they_opened_with')if A.get('classification')=='their_silent'else A.get('they_added');R=[B for B in F.findall(AMOUNT,Z or'',F.I)if B not in(A.get('we_sent')or'')];a=bool(F.search(INSURANCE,Z or'',F.I))
		if R and V not in g:D.append(amount_item(A.get('clause')or'?',R[0],a,E,V,B))
		if A.get('classification')!='their_silent':continue
		b='silent:r%s:%s'%(E,V);f.add(b);W,X=diff_window(A.get('we_sent'),A.get('they_opened_with'))
		if not C:W,X=W.replace('**[ריק]**','**[empty]**'),X.replace('**[ריק]**','**[empty]**')
		h=' (סעיף מוסכם)'if C and A.get('reopens_closed')else' (an agreed clause)'if A.get('reopens_closed')else'';J='להחזיר בעקוב אחר שינויים לנוסח שנשלח, עם בועה עניינית שהשינוי לא סומן'if C else'Revert to the sent wording in tracked changes, with a factual comment that the change was not marked'
		if A.get('reopens_closed'):J+='. בסעיף מוסכם זו החזרה לנוסח המוסכם (kind: restore_agreed), ולא פתיחה מחדש: הסעיף נשאר מוסכם'if C else'. In an agreed clause this restores the agreed wording (kind: restore_agreed), and is not a reopening: the clause stays agreed'
		K=['להחזיר','לקבל, עם בועה']if C else['Revert','Accept, with a comment'];L=COND_WORDING[_bubble_lang(A.get('we_sent'))]if F.search(APPROVAL,A.get('they_opened_with')or'',F.I)and not F.search(APPROVAL,A.get('we_sent')or'',F.I)else None;K=K+[CONDITION[B]['opt']%(L or CONDITION[B]['generic'])]
		if L and not A.get('reopens_closed')and not R:J=CONDITION[B]['rec']%L
		elif L:J+=CONDITION[B]['alt']%L
		if R:J=AMOUNT_REC[B]['silent']+(AMOUNT_REC[B]['cert']if a else'');K=AMOUNT_REC[B]['opts']+K
		D.append({'key':b,'kind':'silent_change','situation':9,'blocks_sending':True,'text':('שינוי שלא סומן בסעיף %s%s. נשלח: "%s". חזר: "%s".'if C else'Unmarked change in clause %s%s. Sent: "%s". Returned: "%s".')%(A.get('clause')or'?',h,W,X),'recommendation':J,'options':K})
	for G in(O or{}).get('threads')or():
		c=next((A for A in G.get('entries')or()if A.get('new')and not A.get('ours')and F.search(WILL_REVERT,A.get('text')or'',F.I)),None)
		if c:i=' '.join((c.get('text')or'').split())[:160];D.append({'key':'prepare:%s:r%s'%(G.get('root_id'),E),'kind':'internal_prepare','situation':None,'blocks_sending':False,'text':PREPARE[B]['text']%(G.get('clause')or G.get('para')or'?',i),'recommendation':PREPARE[B]['rec'],'options':list(PREPARE[B]['opts'])})
	for A in(Q or{}).get('clauses')or():
		H=A.get('clause_id');S=A.get('contract_ref')or H;M=A.get('reopened_by_counterparty')or{}
		if M and int(M.get('round')or 0)==int(E or M.get('round')or 0)and'their_silent'not in(M.get('classification')or()):D.append({'key':'reopened:%s:r%s'%(H,M.get('round')),'kind':'reopened_closed','situation':None,'text':('הצד שכנגד פתח מחדש סעיף מוסכם: %s.'if C else'The other side reopened an agreed clause: %s.')%S,'recommendation':'להחזיר בעקוב אחר שינויים לנוסח המוסכם, עם בועה קצרה שהנוסח הוסכם'if C else'Revert to the agreed wording, with a short comment','options':['להחזיר','לקבל את הפתיחה (הוראה רשומה)']if C else['Revert','Accept the reopening (recorded instruction)']})
		I=A.get('escalation')or{}
		if A.get('status')=='STUCK'and I and int(I.get('round')or 0)==int(E or I.get('round'))and I.get('basis')!='user_instruction':j=ESCALATION_WHY[B].get(I.get('basis'),ESCALATION_WHY[B]['rejected_twice']);D.append({'key':'escalation:%s:r%s'%(H,I.get('round')),'kind':'escalation','situation':None,'text':('%s: %s (STUCK). מוצעת שיחה לפני סבב נוסף.'if C else'%s: %s (STUCK). A call before another round is proposed.')%(S,j),'recommendation':'שיחה בין הצדדים לפני סבב נוסף, ובבועה רק ההצעה לשיחה והנימוק החדש'if C else'A call before another round, and in the comment only the call proposal and the new reasoning','options':['להציע שיחה','מדרגה אחת עם נימוק חדש','להחזיק']if C else['Propose a call','One step with new reasoning','Hold']})
		if A.get('status')=='ACCEPTED_PENDING'and A.get('held_for')=='talking_point':
			if e:T=commercial_of(Q,H);N=HELD_CLOSING[B];D.append({'key':'held:%s:r%s'%(H,E),'kind':'held_for_call','situation':5,'clause_ids':[H],'requires_explicit':True,'commercial_topic':T,'text':N['text']%(S,N['commercial']%P.COMMERCIAL_LABELS[B][T]if T else''),'recommendation':N['rec_raise']if T else N['rec_waive'],'options':list(N['opts'])});U.add(H);continue
			D.append({'key':'held:%s:r%s'%(H,E),'kind':'held_for_call','situation':None,'text':('%s עומד לשיחה. השיחה התקיימה, ומה סוכם?'if C else'%s is held for the call. Did the call take place, and what was agreed?')%S,'recommendation':'לא להעלות בכתב בלי הוראה'if C else'Do not raise it in writing without an instruction','options':['לא התקיימה','התקיימה: <מה סוכם>']if C else['Not yet','It did: <what was agreed>']});U.add(H)
	for G in(O or{}).get('orphaned_terms')or():D.append({'key':'term:%s'%G.get('term'),'kind':'orphaned_term','situation':None,'text':('המונח "%s" משמש ב-%s, וההגדרה שלו (ב-%s) נמחקה בנוסח שלהם.'if C else'The term "%s" is used in %s, and its definition (in %s) was deleted in their wording.')%(G.get('term'),', '.join(A for A in G.get('used_in')or()if A)or'?',G.get('defined_in')or'?'),'recommendation':'להחזיר את ההגדרה בעקוב אחר שינויים, או לתקן את הסעיף שמשתמש במונח'if C else'Restore the definition in tracked changes, or fix the clause that uses the term','options':['להחזיר את ההגדרה','לתקן את הסעיף']if C else['Restore the definition','Fix the clause']})
	D+=Y;D+=commercial_items(Q,B,skip=U);return D
EXPLICIT_NOTE={'he':' כאן צריך תשובה שלכם לנושא הזה עצמו; "תפעלו לפי ההמלצה" לא מספיק.','en':' This needs your own answer on this topic; "follow the recommendation" is not enough.'}
AMOUNT_KINDS='internal_amount','composite','stale_target'
OPERATIONAL='\\b\\d+\\s*(?:hours?|business days?|working days?|minutes?)\\b|\\bSLA\\b|\\buptime\\b|response time|\\d+\\s*(?:שעות|דקות|ימי עבודה)|זמן תגובה|זמינות השירות|רמת שירות'
SECURITY='(?:information|data|cyber|IT)\\s+security|security\\s+(?:incident|breach|event|measures)|data\\s+(?:breach|loss)|personal data breach|cyber|clearance|vetting|אבטחת (?:ה)?מידע|אירוע (?:אבטח|סייבר)|סייבר|דליפ(?:ת|ה) (?:ה)?מידע|פריצה למערכ|סיווג ביטחוני|בדיקה ביטחונית'
OPS_OWNER='\\bSLA\\b|\\buptime\\b|response time|service levels?|זמן תגובה|זמינות השירות|רמ(?:ת|ות) (?:ה)?שירות'
OWNERS={'he':{'security':'אבטחת המידע','operations':'התפעול','other':'הגורם האחראי בחברה'},'en':{'security':'information security','operations':'operations','other':'the responsible team'}}
OWNER_Q={'he':' שאלה אל %s: האם אפשר לעמוד בזה בפועל?','en':' Question for %s: can this be met in practice?'}
OWNER_OPT={'he':'לבדוק קודם עם %s','en':'Check with %s first'}
COUNTER_EDGE={'he':' האסטרטג סימן את הנושא כגבול הקו האדום ("%s"): זו הכרעה על הקו האדום, ולא הצעה נגדית סבירה רגילה.','en':' The strategist marked this topic as the edge of the red line ("%s"): this is a red-line decision, not an ordinary reasonable counter.'}
def _blob(it):return' '.join(str(it.get(A)or'')for A in('text','gap','recommendation'))
def is_operational(it):import re;return bool((it or{}).get('operational'))or bool(re.search(OPERATIONAL,_blob(it or{}),re.I))
def operational_owner(it,lang='he'):
	import re;A=_lang(lang)
	if(it or{}).get('owner'):return it['owner']
	if re.search(SECURITY,_blob(it or{}),re.I):return OWNERS[A]['security']
	return OWNERS[A]['operations']if re.search(OPS_OWNER,_blob(it or{}),re.I)else OWNERS[A]['other']
def requires_explicit(it,decision=None):
	A=it;import re;A=A or{};C=decision or{}
	if A.get('requires_explicit')or C.get('requires_explicit'):return A.get('requires_explicit_why')or'flagged'
	B=A.get('kind')or C.get('kind')
	if A.get('situation')==2:return'beyond_playbook'
	if B=='counter_tighter':return'counter_tighter'
	if B in('paper_type','tender_stage'):return'tender'
	if A.get('red_line_edge')or C.get('red_line_edge'):return'red_line_edge'
	if A.get('situation')is None and B not in AMOUNT_KINDS:return
	if B in AMOUNT_KINDS or A.get('amount')or re.search(AMOUNT,_blob(A),re.I):return'amount'
	if is_operational(A):return'operational'
EDGE_RE='גבול הקו האדום|edge of the red line|red[- ]line (?:boundary|edge)'
MARKS={'he':{'head':' האסטרטג סימן:','edge':' גבול הקו האדום: %s.','pkg':' חבילה: %s%s.','ret':', בתמורה ל: %s'},'en':{'head':' The strategist marked:','edge':' edge of the red line: %s.','pkg':' package: %s%s.','ret':', in return for: %s'}}
def _short(s,n=140):s=' '.join(str(s or'').split());return s if len(s)<=n else s[:n-3].rstrip()+'...'
def item_clause_ids(it):
	A=[]
	for B in('clause_ids','applies_to'):A+=[B for B in(it or{}).get(B)or()if B and B not in A]
	if(it or{}).get('clause_id')and it['clause_id']not in A:A.append(it['clause_id'])
	return A
def _refs(text):
	import re;C=set()
	for(A,B,D)in re.findall('(\\d+(?:\\.\\d+)?)(?:\\s*-\\s*(\\d+(?:\\.\\d+)?))?((?:\\([a-z0-9]+\\))*)',str(text or''),re.I):
		C.add((A+D).lower())
		if B and'.'in A and'.'in B and A.split('.')[0]==B.split('.')[0]:
			for E in range(int(A.split('.')[1]),int(B.split('.')[1])+1):C.add('%s.%d'%(A.split('.')[0],E))
	return C
def strategy_marks(strategy,clause_ids=(),clause_ref=None):
	F=clause_ref;import re;G=(strategy or{}).get('clauses')or[];J=set(clause_ids or());H=_refs(F)if F else set();B=[A for A in G if A.get('id')in J]or([A for A in G if H&_refs(A.get('title'))]if H else[])
	if not B:return
	A={'clause':B[0].get('id'),'title':B[0].get('title'),'red_line_edge':[],'packages':[],'red_line':''}
	for D in B:
		I=''
		for C in D.get('tree')or():
			if C.get('side')=='them':I=C.get('text')or''
			elif re.search(EDGE_RE,str(C.get('risk')or''),re.I):A['red_line_edge'].append(I or C.get('text')or'')
		for E in(D.get('bargain')or{}).get('midpoints')or():A['packages'].append({'point':E.get('point'),'in_return':E.get('in_return'),'criterion':E.get('criterion')})
		A['red_line']=A['red_line']or((D.get('lines')or{}).get('red')or{}).get('what')or''
	return A
def marks_text(marks,lang='he'):
	D=marks;A=MARKS[_lang(lang)];B=A['head']
	for E in(D.get('red_line_edge')or[])[:1]:B+=A['edge']%_short(E).rstrip('.')
	for C in(D.get('packages')or[])[:2]:B+=A['pkg']%(_short(C.get('point')).rstrip('.'),A['ret']%_short(C.get('in_return')).rstrip('.')if C.get('in_return')else'')
	return B
UNLIMITED='no limit|unlimited|uncapped|without limit|not be limited|ללא הגבלה|ללא תקרה|בלתי מוגבל'
CAP_COMPONENT='תקר|הגבלת (ה)?אחריות|גבול (ה)?אחריות|liabilit|\\bcap\\b|\\bcapped\\b|limitation|'+UNLIMITED
DIRECTIONS='lower_better','higher_better'
def side_direction(our_side):0
def component_direction(c,it=None):
	A=it;import re;A=A or{}
	for B in(c.get('direction'),A.get('direction')):
		if B in DIRECTIONS:return B
	C=' '.join(str(A or'')for A in(c.get('name'),c.get('topic'),A.get('topic'),A.get('title')))
	if not re.search(CAP_COMPONENT,C,re.I):return
	return side_direction(A.get('our_side'))
COMPOSITE={'he':{'head':'סעיף %s, רכיב אחר רכיב.','keep':' נשמר כפי שהציעו (בירוק או טוב ממנו): %s.','trade':' מוצע לקבל כחלק מחבילה, אף שזה מעבר ליעד ולנסיגה שמסרתם: %s. מחייב הכרעה מפורשת שלכם.','neg':' משא ומתן רק על: %s.','stale':' היעד שמסרתם%s נמסר לפני שההצעה שלהם הגיעה, ולכן אינו מוחל כמו שהוא: מה נשמר, ועל מה מנהלים משא ומתן?','stale_round':' בסבב %s','stale_target':' ("%s")','retrade':' ההצעה הנגדית ברכיב "%s" (%s) מבקשת יותר מ-%s שהם הציעו, ברכיב שכבר בירוק: זו חזרה מהתקדמות שלהם, והיא עלולה לעכב את הסגירה.','give_back':' ההצעה הנגדית ברכיב "%s" (%s) גרועה לנו מ-%s שהם הציעו: לא מחזירים ליעד, ונשארים עם המספר שלהם.','nodir':' ברכיב %s לא נקבע בפלייבוק אם מספר גבוה או נמוך טוב לחברה: מה הכיוון, ומה היעד?','rec':'להשאיר את %s, ולנהל משא ומתן רק על %s','rec_keep':'לקבל את %s כפי שהציעו','pkg':'; חבילה: %s','opts':['לפי ההמלצה','יעד אחר לכל רכיב: <..>'],'opt_target':'היעד שמסרתם: %s'},'en':{'head':'Clause %s, component by component.','keep':' Kept as they offered (green or better): %s.','trade':' Proposed to accept as part of a package, although it is beyond the target and fallback you gave: %s. Needs your express decision.','neg':' Negotiate only: %s.','stale':' The target you gave%s was given before their offer arrived, so it is not applied as is: what is kept, and what is negotiated?','stale_round':' in round %s','stale_target':' ("%s")','retrade':' The counter on "%s" (%s) asks for more than the %s they offered, in a component already in green: this walks back their movement and may delay closing.','give_back':' The counter on "%s" (%s) is worse for us than the %s they offered: we do not go back to the target, and keep their number.','nodir':' For %s the playbook does not say whether a higher or a lower number is better for the company: which way, and what is the target?','rec':'Keep %s, and negotiate only %s','rec_keep':'Accept %s as offered','pkg':'; package: %s','opts':['As recommended','Another target per component: <..>'],'opt_target':'The target you gave: %s'}}
MEMO={'he':{'title':'**תזכיר החלטה, סעיף %s** (פנימי, להנהלה)','cols':'| | |\n|---|---|','rows':(('their','ההצעה שלהם'),('target','היעד שלנו'),('last_fallback','הנסיגה הפנימית שלנו (לא נמסרה לצד השני)'),('insurance','הכיסוי הביטוחי'),('contract_value','שווי החוזה')),'missing':'לא נמסר','rec':'**ההמלצה:** %s','mandate':'**נדרשת הרחבת מנדט:** ההצעה שלהם מעבר לנסיגה האחרונה. העותק למשלוח אינו מתקדם בנושא הזה עד הכרעה מפורשת.'},'en':{'title':'**Decision memo, clause %s** (internal, for management)','cols':'| | |\n|---|---|','rows':(('their','Their offer'),('target','Our target'),('last_fallback','Our internal fallback (not disclosed to them)'),('insurance','Insurance cover'),('contract_value','Contract value')),'missing':'not provided','rec':'**Recommendation:** %s','mandate':'**Mandate extension needed:** their offer is beyond our last fallback. The send copy does not move on this topic until an express decision.'}}
def parse_amount(s):
	import re
	if s is None or s=='':return
	if isinstance(s,(int,float)):return float(s)
	if re.search(UNLIMITED,str(s),re.I):return float('inf')
	A=re.search('(\\d[\\d,]*(?:\\.\\d+)?)\\s*(million|מיליון|m\\b|k\\b)?',str(s),re.I)
	if not A:return
	C=float(A.group(1).replace(',',''));B=(A.group(2)or'').lower();return C*(1e6 if B in('million','מיליון','m')else 1e3 if B=='k'else 1)
def _better(a,b,direction):return a<b if direction=='lower_better'else a>b
def analyse_component(c,direction=None,offer_round=None):
	A=c.get('direction')or direction;B,D,F=parse_amount(c.get('their')),parse_amount(c.get('ours')),parse_amount(c.get('green'));E=c.get('their_track')in('green','better','trade')or c.get('their_track')is None and None not in(B,F)and bool(A)and not _better(F,B,A);C=[]
	if not A and c.get('their_track')is None:C.append('direction_unknown')
	if None not in(B,D)and A and D!=B:
		if E and _better(D,B,A):C.append('retrade')
		elif _better(B,D,A):C.append('give_back')
	G,H=c.get('target_round'),c.get('offer_round')or offer_round
	if G and H and int(G)<int(H):C.append('stale_target')
	I=bool(c.get('beyond_last_fallback')or c.get('their_track')=='red'or B==float('inf')and A=='lower_better');return{'status':'keep'if E else'negotiate','flags':C,'beyond_last_fallback':I and not E,'trade':c.get('their_track')=='trade'}
def decision_memo(m,lang='he'):
	A=MEMO[_lang(lang)];B=[A['title']%(m.get('clause')or'?'),A['cols']]
	for(C,D)in A['rows']:B.append('| %s | %s |'%(D,_short(m.get(C),200)or A['missing']))
	B+=[A['rec']%(m.get('package')or'?'),A['mandate']];return'\n'.join(B)
def composite_item(it,lang='he',round_number=None):
	A=it;from orchestrator.state_builder import stage_for_round as T;N=_lang(lang);B=COMPOSITE[N];C=[dict(B,**analyse_component(B,component_direction(B,A),A.get('offer_round')))for B in A.get('components')or()];K=lambda c:'%s (%s)'%(c.get('name'),c.get('their'));D=[K(A)for A in C if A['status']=='keep'and not A.get('trade')];L=[K(A)for A in C if A.get('trade')];G=[K(A)for A in C if A['status']=='negotiate'];I={B for A in C for B in A['flags']};H=B['head']%(A.get('clause')or'?')+(B['keep']%', '.join(D)if D else'')+(B['trade']%', '.join(L)if L else'')+(B['neg']%', '.join(G)if G else'')
	if'stale_target'in I:O=next((A.get('target_round')for A in C if'stale_target'in A['flags']),None);J=(A.get('exposure')or{}).get('target');H+=B['stale']%((B['stale_round']%O if O else'')+(B['stale_target']%_short(J,120)if J else''))
	for E in C:
		if'retrade'in E['flags']:H+=B['retrade']%(E.get('name'),E.get('ours'),E.get('their'))
		if'give_back'in E['flags']:H+=B['give_back']%(E.get('name'),E.get('ours'),E.get('their'))
	P=[A.get('name')for A in C if'direction_unknown'in A['flags']]
	if P:H+=B['nodir']%', '.join(str(A)for A in P)
	D=D+L;M=A.get('package')or(B['rec']%(', '.join(D),', '.join(G))if D and G else B['rec_keep']%', '.join(D)if D else A.get('recommendation')or'')
	if A.get('package')and D and G and A['package']!=A.get('recommendation'):M=B['rec']%(', '.join(D),', '.join(G))+B['pkg']%A['package']
	if A.get('text'):H+=' '+A['text'].strip()
	Q=list(B['opts']);J=(A.get('exposure')or{}).get('target')
	if'stale_target'in I and J:Q.insert(1,B['opt_target']%_short(J,80))
	F=dict(A,text=H,recommendation=M,options=Q,requires_explicit=True,requires_explicit_why='amount',amount=True,components=C);R=round_number or A.get('round')
	if R and(L or T(R)=='closing'and any(A['beyond_last_fallback']for A in C)):S=dict(A.get('exposure')or{});S.setdefault('their',', '.join(K(A)for A in C));F['memo']=decision_memo(dict(S,clause=A.get('clause'),package=M),N);F.update(situation=2,blocks_sending=True)
	elif'stale_target'in I:F['situation']=3
	elif I&{'retrade','give_back'}:F['situation']=5
	elif'direction_unknown'in I and not F.get('situation'):F['situation']=3
	return F
PREP_KEY='^prepare:(?P<root>[^:]+):r(?P<r>\\d+)$'
EXCLUSION='(?:save that|except(?: that)?|provided that|other than|excluding|but no limit)[^;]*'
STALE={'he':{'general':'תקרה כללית','amount':'הסכום שהציעו','excl':'החרגות בלי תקרה','rec':'להשאיר את %s כתקרה הכללית, ולהחליף את ההחרגות הבלתי מוגבלות בתקרה נפרדת לנושאים שהוחרגו, קשורה לכיסוי הביטוחי%s','rec_one':'לבחון את %s מול הירוק לפני שמחזירים ליעד','ins':' (%s)','pkg':'; חבילת האסטרטג: %s'},'en':{'general':'general cap','amount':'the amount they offered','excl':'uncapped exclusions','rec':'Keep %s as the general cap, and replace the uncapped exclusions with a separate cap for the excluded matters, tied to the insurance cover%s','rec_one':'Test %s against the green before returning to the target','ins':' (%s)','pkg':"; the strategist's package: %s"}}
def _our_side(state):A=((state or{}).get('meta')or{}).get('position')or{};return A.get('playbook_side')or A.get('our_side_in_agreement')or''
def _insurance_of(state):
	E=state;import re as A
	for B in(((E or{}).get('meta')or{}).get('deal_context')or{}).get('facts')or():
		C=B.get('fact')if isinstance(B,dict)else str(B)
		if A.search(INSURANCE,C or'',A.I)and A.search(AMOUNT,C or'',A.I):return C
	for D in reversed((E or{}).get('user_decisions')or()):
		if str(D.get('id')or'').startswith('amount:')and A.search(AMOUNT,D.get('answer')or'',A.I):return D['answer']
	return''
def stale_target_items(compare,state,round_number,lang='he',strategy=None):
	S=strategy;L=compare;F=state;E=round_number;import re as A;W=_lang(lang);C=STALE[W]
	if not L or not F or not E:return[]
	X={str(A.get('root_id')):A for A in L.get('threads')or()};M=(F.get('meta')or{}).get('deal_context')or{};N=M.get('estimated_value')if str(M.get('estimated_value')or'').strip()not in('','לא ידוע','unknown')else''
	if not N:N=next((B.get('fact')for B in M.get('facts')or()if isinstance(B,dict)and A.search('תמורה|שווי|fees|value|consideration',B.get('fact')or'',A.I)and A.search(AMOUNT,B.get('fact')or'')and not A.search(INSURANCE,B.get('fact')or'',A.I)),'')
	T=[]
	for G in F.get('user_decisions')or():
		H=A.match(PREP_KEY,str(G.get('id')or''))
		if not H or int(H.group('r'))>=int(E)or G.get('answer_kind')!='explicit':continue
		I=X.get(H.group('root'));D=I and next((A for A in L.get('clauses')or()if A.get('received_para')==I.get('para')and A.get('classification')in('their_tracked','their_silent')),None)
		if not D:continue
		J=D.get('they_added')if D['classification']=='their_tracked'else D.get('they_opened_with');K=[A for A in A.findall(AMOUNT,J or'',A.I)if A not in(D.get('we_sent')or'')]
		if not K:continue
		Y=G.get('answer')or'';O=A.split('נסיגה\\s*:|fallback\\s*:',Y,1,flags=A.I);B=A.search(EXCLUSION,J or'',A.I);B=B.group(0).strip()if B and A.search(UNLIMITED,B.group(0),A.I)else'';Z=bool(B)or bool(A.search(CAP_COMPONENT,J or'',A.I));U=[{'name':C['general']if Z else C['amount'],'their':K[0],'their_track':'trade'if B else None,'target_round':int(H.group('r')),'offer_round':int(E)}]
		if B:U.append({'name':C['excl'],'their':_short(B,120),'their_track':'red','beyond_last_fallback':True})
		P=_insurance_of(F);Q=C['rec']%(K[0],C['ins']%_short(P,80)if P else'')if B else C['rec_one']%K[0];a=strategy_marks(S,G.get('applies_to'),D.get('clause'))if S else None;R=(a or{}).get('packages')or[];V=next((B for B in R if A.search(INSURANCE,'%s %s'%(B.get('point'),B.get('criterion')),A.I)),R[0]if R else None)
		if V:Q+=C['pkg']%_short(V.get('point'),120)
		b=D.get('clause')or I.get('clause')or'?';T.append({'key':'restate:%s:r%s'%(H.group('root'),E),'kind':'composite','clause':b,'our_side':_our_side(F),'clause_ids':list(G.get('applies_to')or()),'offer_round':int(E),'components':U,'recommendation':Q,'package':Q,'situation':3,'exposure':{'their':_short(J,200),'target':O[0].strip(' .;,'),'last_fallback':O[1].strip(' .;,')if len(O)>1 else'','insurance':P,'contract_value':N},'round':int(E),'para':I.get('para')})
	return T
HELD_CLOSING={'he':{'text':'%s עמד לשיחה, והשיחה לא התקיימה או שלא נרשם מה סוכם.%s בסבב סגירה: להעלות עכשיו בכתב, או לוותר ביודעין?','commercial':' זה נושא מסחרי מחייב (%s).','rec_raise':'להעלות עכשיו בכתב, בבועה קצרה בנוסח חבילה. זו פתיחה מכוונת של סעיף שקיבלנו, ונרשמת כך עם הוראתך (reopen)','rec_waive':'לוותר ביודעין, ולרשום ויתור מכוון עם נימוק','opts':['להעלות עכשיו בכתב','לוותר ביודעין','השיחה התקיימה (לפרט מה סוכם)']},'en':{'text':'%s was held for the call, and the call did not take place or what was agreed was not recorded.%s In a closing round: raise it now in writing, or waive it knowingly?','commercial':' This is a binding commercial topic (%s).','rec_raise':'Raise it now in writing, in a short package-style comment. This deliberately reopens a clause we accepted, and is recorded as such with your instruction (reopen)','rec_waive':'Waive it knowingly, and record a deliberate concession with a reason','opts':['Raise it now in writing','Waive it knowingly','The call took place (say what was agreed)']}}
COMMERCIAL_Q={'he':{'text':'ויתור מכוון ב%s על נושא מסחרי מחייב (%s): "%s". נושא כזה אינו ויתור בלי שאלה נפרדת: להעלות בכתב, או לוותר ביודעין?','closed':' הסעיף כבר הוסכם: העלאה מחדש רק בהוראה רשומה (negotiation_state.py reopen).','rec':'להעלות בכתב בסבב הזה, בבועה קצרה','rec_closed':'לוותר ביודעין: הסעיף הוסכם, ופתיחה מחדש תעלה סבב','opts':['להעלות בכתב','לוותר ביודעין'],'opts_closed':['לוותר ביודעין','לפתוח מחדש: הוראה רשומה']},'en':{'text':'A deliberate concession in %s on a binding commercial topic (%s): "%s". Such a topic is not conceded without a separate question: raise it in writing, or waive it knowingly?','closed':' The clause is already agreed: raising it again only on a recorded instruction (negotiation_state.py reopen).','rec':'Raise it in writing in this round, in a short comment','rec_closed':'Waive it knowingly: the clause is agreed, and reopening it costs a round','opts':['Raise it in writing','Waive it knowingly'],'opts_closed':['Waive it knowingly','Reopen: recorded instruction']}}
def commercial_of(state,cid):
	C=state
	for A in(C or{}).get('deliberate_concessions')or():
		if isinstance(A,dict)and A.get('clause_ref')==cid and P.commercial_topic(A):return P.commercial_topic(A)
	for B in(C or{}).get('talking_points')or():
		if isinstance(B,dict)and cid in(B.get('clause_ids')or())and P.commercial_topic(B):return P.commercial_topic(B)
def commercial_items(state,lang='he',skip=()):
	D=state;G=_lang(lang);B=COMMERCIAL_Q[G];J={A.get('clause_id'):A for A in(D or{}).get('clauses')or()if isinstance(A,dict)};K=(D or{}).get('numbering_map')or{};H,I=[],set(skip or())
	for C in(D or{}).get('deliberate_concessions')or():
		if not isinstance(C,dict):continue
		A,E=C.get('clause_ref'),P.commercial_topic(C)
		if not E or A in I or C.get('reopened_in_round')or(C.get('user_decision')or{}).get('answer_kind')=='explicit':continue
		I.add(A);F=(J.get(A)or{}).get('status')=='CLOSED';H.append({'key':'commercial:%s'%A,'kind':'commercial_concession','situation':5,'clause_ids':[A],'requires_explicit':True,'commercial_topic':E,'text':B['text']%(K.get(A)or A,P.COMMERCIAL_LABELS[G][E],_short(C.get('topic')))+(B['closed']if F else''),'recommendation':B['rec_closed']if F else B['rec'],'options':list(B['opts_closed']if F else B['opts'])})
	return H
READY='in a position to finali[sz]e|ready to (?:sign|finali[sz]e|execute|proceed to sign)|proceed to (?:signature|signing)|finali[sz]e (?:this|the) agreement|מוכנים לחתום|מוכנים לסיים|נוכל לחתום|נוכל לסיים'
def ready_signal(compare):
	import re
	for B in(compare or{}).get('threads')or():
		for A in B.get('entries')or():
			if A.get('new')and not A.get('ours')and re.search(READY,A.get('text')or'',re.I):return{'root_id':B.get('root_id'),'text':' '.join((A.get('text')or'').split())[:200]}
APPROVAL='approv|consent|הסכמ|אישור'
COND_WORDING={'en':'such approval not to be unreasonably withheld or delayed','he':'ובלבד שהאישור לא יסורב ולא יעוכב שלא באופן סביר'}
CONDITION={'he':{'opt':'לקבל בתנאי: %s','generic':'<התנאי>','rec':'לקבל בתנאי: השינוי שלהם נשאר, ומסמנים עליו בעקוב אחר שינויים "%s" (kind: accept_with_condition)','alt':'. חלופה: לקבל בתנאי ("%s", kind: accept_with_condition); בסעיף מוסכם זו פתיחה מחדש, בהוראה רשומה'},'en':{'opt':'Accept on a condition: %s','generic':'<the condition>','rec':'Accept on a condition: their change stays, and we mark "%s" on it in tracked changes (kind: accept_with_condition)','alt':'. Alternative: accept on a condition ("%s", kind: accept_with_condition); in an agreed clause this is a reopening, on a recorded instruction'}}
CHANGE_OPS='replace','replace_span','insert_paragraph','delete_paragraph'
REPLACES={'en':'This replaces our earlier proposal.','he':'זה מחליף את ההצעה הקודמת שלנו.'}
REPLACES_RE='replaces our (?:earlier|previous) proposal|מחליפ[הא]? את ההצעה הקודמת'
REPLACES_SENT='\\s*(?:This replaces our (?:earlier|previous) proposal|זה מחליף את ההצעה הקודמת שלנו)\\.?\\s*'
def _bubble_lang(text):import re;return'he'if re.search('[א-ת]',text or'')else'en'
