# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import base64,json,os,re,subprocess,sys,tempfile
from pathlib import Path
MAX_BYTES=20971520
EMAIL_RE=re.compile('^[^@\\s<>\\"\']+@[^@\\s<>\\"\']+\\.[^@\\s<>\\"\']+$')
_APPLESCRIPT='\non run argv\n  set subj to item 1 of argv\n  set html to item 2 of argv\n  set fpath to item 3 of argv\n  tell application "Microsoft Outlook"\n    set m to make new outgoing message with properties {subject:subj, content:html}\n    repeat with i from 4 to count of argv\n      make new recipient at m with properties {email address:{address:(item i of argv)}}\n    end repeat\n    if fpath is not "" then make new attachment at m with properties {file:POSIX file fpath}\n    open m\n    activate\n  end tell\nend run\n'
_POWERSHELL="\n$s = Get-Content -Raw -Encoding UTF8 $args[0] | ConvertFrom-Json\n$o = New-Object -ComObject Outlook.Application\n$m = $o.CreateItem(0)\n$m.To = ($s.to -join ';')\n$m.Subject = $s.subject\n$m.HTMLBody = $s.html\nif ($s.file) { [void]$m.Attachments.Add($s.file) }\n$m.Display()\n"
def _safe_name(name):
	A=name;A=re.sub('[\\\\/:*?"<>|\\x00-\\x1f]','',(A or'').strip())or'מסמך.docx'
	if not A.lower().endswith('.docx'):A+='.docx'
	return A[:180]
def _result(opened,**A):return json.dumps(dict(opened=opened,**A),ensure_ascii=False)
def open_mail_draft(args,runner=subprocess.run,platform=sys.platform):
	H=platform;G=runner;A=args;D=[A.strip()for A in A.get('to')or[]if isinstance(A,str)and EMAIL_RE.match(A.strip())]
	if not D:return _result(False,reason='bad_recipient')
	I=str(A.get('subject')or'')[:255];J=str(A.get('body_html')or'')[:200000];C=''
	if A.get('file_base64'):
		try:E=base64.b64decode(A['file_base64'],validate=True)
		except Exception:return _result(False,reason='bad_file')
		if not E or len(E)>MAX_BYTES:return _result(False,reason='bad_file')
		B=Path(tempfile.mkdtemp(prefix='areo-mail-'));os.chmod(B,448);K=B/_safe_name(A.get('file_name'));K.write_bytes(E);C=str(K)
	if H=='darwin':
		if not Path('/Applications/Microsoft Outlook.app').exists():return _result(False,reason='no_outlook')
		F=G(['osascript','-e',_APPLESCRIPT,I,J,C,*D],capture_output=True,text=True,timeout=60)
	elif H.startswith('win'):B=Path(tempfile.mkdtemp(prefix='areo-mail-'));L=B/'spec.json';L.write_text(json.dumps({'to':D,'subject':I,'html':J,'file':C},ensure_ascii=False),encoding='utf-8');M=B/'open.ps1';M.write_text(_POWERSHELL,encoding='utf-8');F=G(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-File',str(M),str(L)],capture_output=True,text=True,timeout=60)
	else:return _result(False,reason='unsupported_system')
	if F.returncode!=0:return _result(False,reason='outlook_refused',detail=(F.stderr or'')[-300:])
	return _result(True,app='Outlook',attached=bool(C))
