#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import json,pathlib,os,sys,urllib.error,urllib.parse,urllib.request
from pathlib import Path
DEFAULT_API_URL='https://areo.co.il'
PROTOCOL_VERSION='2024-11-05'
PLUGIN_VERSION='1.29.7'
SERVER_INFO={'name':'areolegal','version':'1.0.4'}
SERVER_INSTRUCTIONS='AreoLegal: write every message the user sees in the user\'s interface language: Hebrew unless the client profile (display_language) says English. This includes short progress notes between tool calls (\'בודק את הטיוטה\', \'בונה את המודל\'). An English line in a Hebrew conversation looks like a malfunction to the client. כל טקסט שהלקוח רואה, גם הודעת ביניים של שתי מילים, הוא בעברית. When the user asks for Areo ("Areo", "areo", "פתחו את Areo", "המערכת"), the FIRST thing in the reply, before any tool call or skill load, is this welcome, as written (three short lines): \'ברוכים הבאים ל-Areo. Areo היא מערכת העבודה החוזית של המחלקה המשפטית: היא בונה את המדיניות החוזית שלכם מתוך ההסכמים, מגיבה לטיוטות של הצד השני לפי המדיניות, ומנסחת הסכמים חדשים על הנייר שלכם. המערכת נפתחת עכשיו לצד השיחה, ולוקח לה דקה או שתיים.\' Opening the system takes a minute or two, and the client must never wait in front of an empty screen.'
TIMEOUT=60
def config_paths():
	A=[];B=os.environ.get('CLAUDE_PLUGIN_DATA')
	if B:A.append(Path(B)/'license.json')
	A.append(Path.home()/'.areolegal'/'license.json');return A
TOOLS=[{'name':'license_status','description':'Check the AreoLegal subscription status for this machine. Call this first when any AreoLegal skill starts, and whenever another AreoLegal tool reports a license problem.','inputSchema':{'type':'object','properties':{},'additionalProperties':False}},{'name':'activate','description':"Activate AreoLegal on this machine by saving the customer's license key locally and validating it against the AreoLegal service. Use during setup/onboarding when the user provides their license key.",'inputSchema':{'type':'object','properties':{'license_key':{'type':'string','description':'License key from areolegal purchase'}},'required':['license_key'],'additionalProperties':False}},{'name':'list_resources','description':'List the professional reference resources available for an AreoLegal skill. skill is one of: contract-playbook-builder, contract-negotiation-orchestrator, contract-setup-diagnostician. Requires an active subscription.','inputSchema':{'type':'object','properties':{'skill':{'type':'string'}},'required':['skill'],'additionalProperties':False}},{'name':'get_resource','description':"Fetch one AreoLegal professional reference resource (methodology, taxonomy, legal anchors, templates, schemas) by skill and resource name, e.g. get_resource(skill='contract-negotiation-orchestrator', name='policy_taxonomy.md'). Requires an active subscription. The content is licensed to the subscriber only.",'inputSchema':{'type':'object','properties':{'skill':{'type':'string'},'name':{'type':'string'}},'required':['skill','name'],'additionalProperties':False}},{'name':'mark_setup','description':"Record locally, on this machine only, that AreoLegal setup has completed and where the company profile folder is. Call this ONCE, at the end of a successful run of contract-setup-diagnostician, right after the profile file is saved. Nothing is sent to the AreoLegal service. Every later skill reads this back from license_status as 'local_setup', and uses it to tell an existing customer who forgot to connect their folder apart from a genuinely new one -- without it, the skill re-runs onboarding and creates a second, diverging company profile.",'inputSchema':{'type':'object','properties':{'profile_folder':{'type':'string','description':'Folder holding Areo-נתונים, as the user sees it. Absolute path is fine.'},'entity':{'type':'string','description':'Optional. Organisation name, for a recognisable prompt later.'}},'additionalProperties':False}},{'name':'save_profile','description':'Save the public copy of the organisation profile at Areo, once, right after setup saved the profile file (and after a profile update or an added entity). Pass the JSON object that build_profile.py --areo-copy produced, unchanged. Only public organisation fields are kept; nothing else is stored.','inputSchema':{'type':'object','properties':{'profile':{'type':'object'}},'required':['profile'],'additionalProperties':False}},{'name':'get_profile','description':"Read the organisation profile Areo keeps for this licence's organisation (public company fields only, no signatories). Call it at the start of setup, before asking any question: when it is found, offer to use it instead of asking the company questions again.",'inputSchema':{'type':'object','properties':{},'additionalProperties':False}},{'name':'save_app_link','description':"Remember the address of this user's Areo system (a claude.ai artifact) after it was published for the first time or moved. Pass url, slug when known, and scope: personal (the user's own system) or shared (the department's system, built from its shared folder). Only the link is kept, never content.",'inputSchema':{'type':'object','properties':{'url':{'type':'string'},'slug':{'type':'string'},'scope':{'type':'string','enum':['personal','shared']}},'required':['url'],'additionalProperties':False}},{'name':'get_app_link','description':"Read the address of this user's Areo system, so the system is updated in place instead of published again. Call it when the folder holds no link for this user.",'inputSchema':{'type':'object','properties':{},'additionalProperties':False}},{'name':'record_action','description':'Count one completed output (the only usage information Areo receives). Pass exactly the four fields that record_action.py printed: skill, action, count, date. When the script printed nothing, do not call this.','inputSchema':{'type':'object','properties':{'skill':{'type':'string'},'action':{'type':'string'},'count':{'type':'integer'},'date':{'type':'string'}},'required':['skill','action'],'additionalProperties':False}},{'name':'save_resource','description':"Download one AreoLegal resource straight to a file on this machine and return only the path and size -- the file's content is NEVER returned into the conversation. ALWAYS use this instead of get_resource for deliverable HTML templates and any other large file that is passed to a build script rather than read: it avoids carrying tens of thousands of tokens of markup through the conversation and re-writing them by hand. Use get_resource only for methodology text you actually need to read. Requires an active subscription.",'inputSchema':{'type':'object','properties':{'skill':{'type':'string'},'name':{'type':'string'},'path':{'type':'string','description':'Where to write the file, relative to the working directory.'}},'required':['skill','name','path'],'additionalProperties':False}},{'name':'open_mail_draft','description':'Open a new email in Outlook on this computer, ready to send: recipients, subject, the text and the Word file attached. Runs only on this machine; nothing is sent to the Areo service and nothing is sent by email: the lawyer reviews the message and presses Send in Outlook.','inputSchema':{'type':'object','properties':{'to':{'type':'array','items':{'type':'string'}},'subject':{'type':'string'},'body_html':{'type':'string'},'file_name':{'type':'string'},'file_base64':{'type':'string'}},'required':['to'],'additionalProperties':False}}]
def read_config():
	for A in config_paths():
		try:return json.loads(A.read_text(encoding='utf-8'))
		except(OSError,ValueError):continue
	return{}
def write_config(cfg,restrict=False):
	for A in config_paths():
		try:
			A.parent.mkdir(parents=True,exist_ok=True);A.write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
			if restrict:A.chmod(384)
			return True
		except OSError:continue
	return False
def local_setup():
	A=read_config().get('setup')or{}
	if not A.get('completed_at'):return{'completed':False}
	return{'completed':True,'completed_at':A.get('completed_at'),'profile_folder':A.get('profile_folder')or'','entity':A.get('entity')or''}
def license_key():return os.environ.get('AREOLEGAL_LICENSE_KEY')or read_config().get('license_key','')
def api_url():A=os.environ.get('AREOLEGAL_API_URL')or read_config().get('api_url')or DEFAULT_API_URL;return A.rstrip('/')
def now_iso():import datetime as A;return A.date.today().isoformat()
def device_id():
	A=read_config()
	if A.get('device_id'):return A['device_id']
	import getpass as C,hashlib as D,platform as E;F=f"{E.node()}|{C.getuser()}|{Path.home()}";B=D.sha256(F.encode()).hexdigest()[:16];A['device_id']=B;write_config(A);return B
def http_get(path,key):
	D=urllib.request.Request(api_url()+path,headers={'Authorization':'Bearer '+key,'User-Agent':f"areolegal-mcp/{PLUGIN_VERSION}",'X-Areo-Device':device_id()})
	try:
		with urllib.request.urlopen(D,timeout=TIMEOUT)as B:return B.status,json.loads(B.read().decode('utf-8'))
	except urllib.error.HTTPError as A:
		try:C=json.loads(A.read().decode('utf-8'))
		except ValueError:C={}
		return A.code,C
	except(urllib.error.URLError,OSError)as A:return 0,{'error':str(A)}
def http_post(path,key,payload):
	D=urllib.request.Request(api_url()+path,data=json.dumps(payload,ensure_ascii=False).encode('utf-8'),method='POST',headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':f"areolegal-mcp/{PLUGIN_VERSION}",'X-Areo-Device':device_id()})
	try:
		with urllib.request.urlopen(D,timeout=TIMEOUT)as B:return B.status,json.loads(B.read().decode('utf-8'))
	except urllib.error.HTTPError as A:
		try:C=json.loads(A.read().decode('utf-8'))
		except ValueError:C={}
		return A.code,C
	except(urllib.error.URLError,OSError)as A:return 0,{'error':str(A)}
NO_KEY_MSG="לא נמצא רישיון AreoLegal במחשב הזה. אם יש למשתמש מפתח רישיון, הפעל את הכלי activate עם המפתח. אם אין, הפנה אותו לרכישת מנוי באתר AreoLegal.\n(No AreoLegal license key found on this machine. If the user has a key, call the 'activate' tool with it; otherwise direct them to purchase a subscription.)"
CONN_ERR_MSG='שירות AreoLegal אינו זמין כרגע (בעיית תקשורת). נסה שוב בעוד רגע. אם הבעיה נמשכת, בדוק חיבור לאינטרנט או פנה לתמיכה.\n(Connection error: {err})'
def denial_text(status,body):
	B=status;A=body.get('message')or body.get('detail')or''
	if B in(401,403):return'המנוי ל-AreoLegal אינו פעיל או שהמפתח שגוי. יש לחדש את המנוי באתר AreoLegal ואז לנסות שוב. '+(f"\nפרטים: {A}"if A else'')+'\n(Subscription inactive or invalid key — the user must renew before this skill can continue. Do not attempt to proceed without the licensed content.)'
	if B==404:return f"Resource not found. פרטים: {A or'not found'}"
	return f"AreoLegal service error (HTTP {B}). {A}"
def call_tool(name,args):
	D=args;C=name
	if C=='open_mail_draft':sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)));from mail_local import open_mail_draft as L;return L(D)
	if C=='activate':
		E=(D.get('license_key')or'').strip()
		if not E:return'לא סופק מפתח רישיון. (No license key provided.)'
		B,A=http_get('/v1/license/status',E)
		if B==0:return CONN_ERR_MSG.format(err=A.get('error','unknown'))
		if B!=200 or A.get('status')not in('active','trialing'):return denial_text(B if B!=200 else 403,A)
		G=read_config();G['license_key']=E;J=False
		for F in config_paths():
			try:F.parent.mkdir(parents=True,exist_ok=True);F.write_text(json.dumps(G,ensure_ascii=False,indent=2),encoding='utf-8');F.chmod(384);J=True
			except OSError:continue
		if not J:return'שגיאה בשמירת הרישיון מקומית. (Failed to persist the license locally.)'
		return'הרישיון הופעל בהצלחה במחשב הזה. סטטוס מנוי: '+json.dumps(A,ensure_ascii=False)
	if C=='mark_setup':
		K=(D.get('profile_folder')or'').strip();G=read_config();H=G.get('setup')or{};H.setdefault('completed_at',now_iso())
		if K:H['profile_folder']=K[:500]
		else:H.pop('profile_folder',None)
		if(D.get('entity')or'').strip():H['entity']=D['entity'].strip()[:200]
		G['setup']=H
		if not write_config(G):return'Error: could not persist the setup marker locally.'
		return json.dumps({'local_setup':local_setup(),'note':'Stored on this machine only; nothing was sent to the service.'},ensure_ascii=False)
	E=license_key()
	if not E:return NO_KEY_MSG
	if C=='get_app_link':
		B,A=http_get('/v1/app-link',E)
		if B==0:return CONN_ERR_MSG.format(err=A.get('error','unknown'))
		if B!=200:return denial_text(B,A)
		return json.dumps(A,ensure_ascii=False)
	if C=='save_app_link':
		I={A:str(D[A])for A in('url','slug','scope')if D.get(A)};B,A=http_post('/v1/app-link',E,I)
		if B==0:return CONN_ERR_MSG.format(err=A.get('error','unknown'))
		if B!=200:return denial_text(B,A)
		return json.dumps(A,ensure_ascii=False)
	if C=='get_profile':
		B,A=http_get('/v1/profile',E)
		if B==0:return CONN_ERR_MSG.format(err=A.get('error','unknown'))
		if B!=200:return denial_text(B,A)
		return json.dumps(A,ensure_ascii=False)
	if C in('save_profile','record_action'):
		if C=='save_profile':B,A=http_post('/v1/profile',E,{'profile':D.get('profile')})
		else:I={A:D[A]for A in('skill','action','count','date')if A in D};B,A=http_post('/v1/actions',E,I)
		if B==0:return CONN_ERR_MSG.format(err=A.get('error','unknown'))
		if B!=200:return denial_text(B,A)
		return json.dumps(A,ensure_ascii=False)
	if C=='license_status':F='/v1/license/status'
	elif C=='list_resources':F=f"/v1/resources/{urllib.parse.quote(str(D.get('skill','')))}"
	elif C in('get_resource','save_resource'):M=urllib.parse.quote(str(D.get('skill','')));N=urllib.parse.quote(str(D.get('name','')));F=f"/v1/resources/{M}/{N}"
	else:return f"Unknown tool: {C}"
	B,A=http_get(F,E)
	if B==0:return CONN_ERR_MSG.format(err=A.get('error','unknown'))
	if B!=200:return denial_text(B,A)
	if C=='get_resource':return A.get('content','')
	if C=='save_resource':return save_to_disk(A.get('content',''),str(D.get('path','')))
	if C=='license_status':A['local_setup']=local_setup()
	return json.dumps(A,ensure_ascii=False,indent=2)
def save_to_disk(content,dest):
	C=content;B=dest
	if not B:return'Error: path is required.'
	A=pathlib.Path(B).expanduser()
	if A.is_absolute()or'..'in A.parts:return"Error: path must be relative to the working directory and may not contain '..'. Received: %s"%B
	try:A.parent.mkdir(parents=True,exist_ok=True);A.write_text(C,encoding='utf-8')
	except OSError as D:return'Error: could not write %s (%s)'%(B,D)
	return json.dumps({'path':str(A),'bytes':len(C.encode('utf-8')),'note':'Saved. Pass this path to the build script; do not read the file.'},ensure_ascii=False)
def handle(msg):
	C=msg;A=C.get('method');B=C.get('id')
	if A=='initialize':E=(C.get('params')or{}).get('protocolVersion')or PROTOCOL_VERSION;return{'jsonrpc':'2.0','id':B,'result':{'protocolVersion':E,'capabilities':{'tools':{}},'serverInfo':SERVER_INFO,'instructions':SERVER_INSTRUCTIONS}}
	if A=='notifications/initialized':return
	if A=='ping':return{'jsonrpc':'2.0','id':B,'result':{}}
	if A=='tools/list':return{'jsonrpc':'2.0','id':B,'result':{'tools':TOOLS}}
	if A=='tools/call':D=C.get('params')or{};F=call_tool(D.get('name',''),D.get('arguments')or{});return{'jsonrpc':'2.0','id':B,'result':{'content':[{'type':'text','text':F}]}}
	if B is not None:return{'jsonrpc':'2.0','id':B,'error':{'code':-32601,'message':f"Method not found: {A}"}}
def main():
	for A in sys.stdin:
		A=A.strip()
		if not A:continue
		try:C=json.loads(A)
		except ValueError:continue
		try:B=handle(C)
		except Exception as D:
			B=None
			if C.get('id')is not None:B={'jsonrpc':'2.0','id':C.get('id'),'error':{'code':-32603,'message':f"Internal error: {D}"}}
		if B is not None:sys.stdout.write(json.dumps(B,ensure_ascii=False)+'\n');sys.stdout.flush()
if __name__=='__main__':main()
