# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
from playbook import decision_kit as DK
KIT_FIELDS='clause_anatomy','parameters','match_tests','undecided_zone','red_signals','purpose_for_company','external_rationale'
LABELS={'he':{'anatomy':'מה הסעיף קובע','purpose':'התכלית לחברה','cp':'מה הצד שכנגד ירצה','tests':'מבחני ההתאמה והפרמטרים','external':'הנימוק לצד השני','component':'הרכיב','same':'כמו בירוק','green':'ירוק','yellow':'צהוב','red':'אדום','protected_asset':'הנכס המוגן','failure_scenario':'תרחיש הכשל','why_this_side':'למה זה חשוב בצד שלנו','if_silent':'אם ההסכם שותק','their_interest':'האינטרס שלהם','their_move':'המהלך הצפוי','their_argument':'הטענה שלהם','our_reply':'התשובה שלנו','internal_allowance':'מה אפשר לתת','internal':'פנימי','param_heads':['הפרמטר','יחידה','ירוק','מדרגות בצהוב','רצפה','אדום'],'required':'חייב להופיע','forbidden':'אסור שיופיע','conditions':'תנאי הפרמטרים','undecided':'התאמה חלקית, נדרשת הכרעתך','nearest':'העמדה הקרובה','missing':'מה חסר להכרעה','signals':'סימני אדום','on':'נוגע ל','remedy':'נוסח הריפוי','yes':'כן','no':'לא'},'en':{'anatomy':'What the clause provides','purpose':'Purpose for the company','cp':'What the other side will want','tests':'Match tests and parameters','external':'The rationale for the other side','component':'Component','same':'Same as green','green':'Green','yellow':'Yellow','red':'Red','protected_asset':'Protected asset','failure_scenario':'Failure scenario','why_this_side':'Why it matters on our side','if_silent':'If the agreement is silent','their_interest':'Their interest','their_move':'Their likely move','their_argument':'Their argument','our_reply':'Our reply','internal_allowance':'What we can give','internal':'Internal','param_heads':['Parameter','Unit','Green','Yellow steps','Floor','Red'],'required':'Must appear','forbidden':'Must not appear','conditions':'Parameter conditions','undecided':'Partial match, your decision is needed','nearest':'Nearest position','missing':'Missing to decide','signals':'Red signals','on':'Concerns: ','remedy':'Cure wording','yes':'Yes','no':'No'}}
SILENT_TAGS={'he':{'contract_mechanism':'המנגנון בהסכם','legal_review_required':'טעון בדיקה משפטית','areo_anchor':'הצעה של Areo','statute_text':'לשון החוק'},'en':{'contract_mechanism':'Contract mechanism','legal_review_required':'Needs legal review','areo_anchor':'An Areo proposal','statute_text':'Statute text'}}
OPS={'he':{'>=':'לפחות %s','=>':'לפחות %s','<=':'לכל היותר %s','=<':'לכל היותר %s','>':'יותר מ-%s','<':'פחות מ-%s','==':'בדיוק %s','=':'בדיוק %s','!=':'לא %s'},'en':{'>=':'at least %s','=>':'at least %s','<=':'at most %s','=<':'at most %s','>':'more than %s','<':'less than %s','==':'exactly %s','=':'exactly %s','!=':'not %s'}}
def _lang(lang):return'en'if lang=='en'else'he'
def clean(v):
	if v is None or isinstance(v,(dict,list,tuple)):return''
	A=' '.join(str(v).split());return A.replace(' — ',', ').replace('—',', ').replace('–','-').replace(' ,',',').strip()
def _value(v,lang):
	if isinstance(v,bool):return LABELS[lang]['yes'if v else'no']
	if isinstance(v,float)and v.is_integer():return str(int(v))
	return clean(v)
def has_kit(rule):return any((rule or{}).get(A)for A in KIT_FIELDS)
def _params(rule):return[A for A in(rule or{}).get('parameters')or()if isinstance(A,dict)]
def _ref_label(ref,rule,lang):
	A=clean(ref)
	if A.startswith('anatomy.'):A=A[len('anatomy.'):]
	if A in DK.ANATOMY:return(DK.ANATOMY_EN if lang=='en'else DK.ANATOMY_HE)[A]
	if A.startswith('param:'):A=A[len('param:'):]
	for B in _params(rule):
		if B.get('id')==A:return clean(B.get('name'))
	return''
def _anatomy(rule,lang):
	I=(rule or{}).get('clause_anatomy')
	if not isinstance(I,dict):return[]
	B={A:DK.anatomy_of(rule,A)for A in DK.TRACKS};J=DK.ANATOMY_EN if lang=='en'else DK.ANATOMY_HE;F=[]
	for A in DK.ANATOMY:
		C=B['green'].get(A,'')
		if not any(B[C].get(A)for C in DK.TRACKS):continue
		D={'key':A,'label':J[A],'green':clean(C)}
		for E in('yellow','red'):G=B[E].get(A,'');H=bool(C)and G==C;D[E]=''if H else clean(G);D[E+'_same']=H
		F.append(D)
	return F
def _purpose(pf,lang):
	E=LABELS[lang];D=[]
	for A in('protected_asset','failure_scenario','why_this_side'):
		if clean(pf.get(A)):D.append({'key':A,'label':E[A],'value':clean(pf.get(A)),'tag':''})
	B=pf.get('if_silent');C,F='',''
	if isinstance(B,dict):C=clean(B.get('text'));F=SILENT_TAGS[lang].get(B.get('label')or'','')
	else:C=clean(B)
	if C:D.append({'key':'if_silent','label':E['if_silent'],'value':C,'tag':F})
	return D
def _cp(rule,pf,internal):
	D=clean(pf.get('counterparty_interest'))or clean(rule.get('counterparty_objective'));B=[]
	for A in pf.get('typical_moves')or():
		if not isinstance(A,dict):continue
		C={'move':clean(A.get('their_move')),'argument':clean(A.get('their_argument')),'reply':clean(A.get('our_reply_external'))}
		if internal and clean(A.get('internal_allowance')):C['internal']=clean(A.get('internal_allowance'))
		if any(C.values()):B.append(C)
	if not(D or B):return{}
	return{'interest':D,'moves':B}
def _param_rows(rule,lang):
	A=lang;C=[]
	for B in _params(rule):
		D=clean(B.get('name'))
		if not D:continue
		E=[_value(B,A)for B in B.get('yellow_steps')or()if _value(B,A)];C.append({'name':D,'unit':clean(B.get('unit')),'green':_value(B.get('green'),A),'yellow':(', ואז 'if A!='en'else', then ').join(E),'floor':_value(B.get('floor'),A),'red':_value(B.get('red_beyond'),A)})
	return C
def _item(x,rule,lang):
	if isinstance(x,dict):
		A=clean(x.get('test')or x.get('text'));B=_ref_label(x.get('ref'),rule,lang)
		if not A:return''
		return'%s (%s)'%(A,B)if B else A
	return clean(x)
def _condition(c,rule,lang):
	if not isinstance(c,dict):return clean(c)
	A=next((A for A in _params(rule)if A.get('id')==c.get('param')),{});B,C=clean(A.get('name')),clean(A.get('unit'));D=_value(c.get('value'),lang)
	if not(B and D):return''
	E=OPS[lang].get(clean(c.get('op')),'%s');return'%s %s'%(B,E%(D+(' '+C if C else'')))
def _tests(rule,lang):
	B=lang;A=rule;D=(A or{}).get('match_tests')
	if not isinstance(D,dict):return[]
	J=LABELS[B];F=[]
	for C in DK.TRACKS:
		E=D.get(C)if isinstance(D.get(C),dict)else{};G=[A for A in(_item(C,A,B)for C in E.get('required')or())if A];H=[A for A in(_item(C,A,B)for C in E.get('forbidden')or())if A];I=[A for A in(_condition(C,A,B)for C in E.get('parameter_conditions')or())if A]
		if G or H or I:F.append({'track':C,'label':J[C],'required':G,'forbidden':H,'conditions':I})
	return F
def _undecided(rule,lang):
	A=(rule or{}).get('undecided_zone')
	if isinstance(A,dict):B={'when':clean(A.get('when')),'nearest':LABELS[lang].get(A.get('nearest_track'))if A.get('nearest_track')in DK.TRACKS else'','missing':clean(A.get('missing'))};return B if B['when']else{}
	return{'when':clean(A),'nearest':'','missing':''}if clean(A)else{}
def _signals(rule,lang):
	B=[]
	for A in(rule or{}).get('red_signals')or():
		if isinstance(A,dict)and clean(A.get('signal')):B.append({'signal':clean(A.get('signal')),'on':_ref_label(A.get('ref'),rule,lang),'remedy':clean(A.get('remedy'))})
	return B
def _external(rule,lang):
	C=(rule or{}).get('external_rationale')
	if not isinstance(C,dict):return[]
	F=LABELS[lang];D=[]
	for A in DK.TRACKS:
		B=C.get(A);E=[clean(A)for A in(B if isinstance(B,list)else[B])if clean(A)]
		if E:D.append({'track':A,'label':F[A],'texts':E})
	return D
def view(rule,lang='he',internal=True):
	B=lang;A=rule;A=A or{}
	if not has_kit(A):return{}
	B=_lang(B);C=A.get('purpose_for_company')if isinstance(A.get('purpose_for_company'),dict)else{};D={'anatomy':_anatomy(A,B),'purpose':_purpose(C,B),'cp':_cp(A,C,internal),'params':_param_rows(A,B),'tests':_tests(A,B),'undecided':_undecided(A,B),'signals':_signals(A,B),'external':_external(A,B)};return{B:A for(B,A)in D.items()if A}
def has_tests_block(kit):return any((kit or{}).get(A)for A in('params','tests','undecided','signals'))
def external_texts(kit):A=[B for A in(kit or{}).get('external')or()for B in A['texts']];A+=[A['reply']for A in((kit or{}).get('cp')or{}).get('moves')or()if A.get('reply')];return A
def map_text(kit,fn,_key=''):
	A=kit
	if isinstance(A,dict):return{A:B if A in('key','track')else map_text(B,fn,A)for(A,B)in A.items()}
	if isinstance(A,list):return[map_text(A,fn,_key)for A in A]
	return fn(A)if isinstance(A,str)and A else A
