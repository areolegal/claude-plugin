# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import base64,colorsys,io,math,re,struct,sys,zlib
if __name__=='__main__':sys.dont_write_bytecode=True
MIN_TEXT=4.5
MIN_LARGE=3.
MAX_SHIFT=.4
MAX_SHIFT_DARK=.6
MAX_LOGO_BYTES=153600
SURFACES={'light':['#FFFFFF','#F4F7F5','#F0F3F6','#E7EDEA'],'dark':['#0E1016','#151923','#1A1F2B','#202636']}
ON_BRAND_CANDIDATES={'light':['#FFFFFF','#10221C','#04140E'],'dark':['#04140E','#0E1016','#FFFFFF']}
AREO_DEFAULT={'light':{'accent':'#0B8C66','accent-bg':'#E1F5EC','accent-ink':'#0B6B4F','on-brand':'#FFFFFF'},'dark':{'accent':'#2FE6A6','accent-bg':'rgba(47,230,166,.12)','accent-ink':'#7DF2C8','on-brand':'#04140E'}}
TOKEN_KEYS='accent','accent-bg','accent-ink','on-brand'
NOTICE={'he':'הצבעים של הלוגו שלכם לא עומדים בבדיקת הקריאות (ניגודיות), ולכן העמודים נשארו בצבעי Areo. הלוגו מוצג כרגיל. אפשר לשלוח גרסה של הלוגו בצבעים כהים וחדים יותר.','en':'Your logo colours do not pass the readability (contrast) check, so the pages stay in Areo colours. The logo is shown as usual. You can send a version of the logo in darker, stronger colours.'}
class BrandError(Exception):0
def hex_to_rgb(h):
	h=h.strip().lstrip('#')
	if len(h)==3:h=''.join(A*2 for A in h)
	return tuple(int(h[A:A+2],16)for A in(0,2,4))
def rgb_to_hex(rgb):return'#%02X%02X%02X'%tuple(max(0,min(255,int(round(A))))for A in rgb)
def _lin(c):c=c/255.;return c/12.92 if c<=.03928 else((c+.055)/1.055)**2.4
def luminance(rgb):A,B,C=(_lin(A)for A in rgb);return .2126*A+.7152*B+.0722*C
def contrast(a,b):A=luminance(hex_to_rgb(a)if isinstance(a,str)else a);B=luminance(hex_to_rgb(b)if isinstance(b,str)else b);C,D=max(A,B),min(A,B);return(C+.05)/(D+.05)
def mix(a,b,t):return tuple(a[A]*(1-t)+b[A]*t for A in range(3))
def _hls(rgb):A,B,C=colorsys.rgb_to_hls(*(A/255. for A in rgb));return A,B,C
def _from_hls(h,l,s):return tuple(A*255 for A in colorsys.hls_to_rgb(h,max(.0,min(1.,l)),s))
def fit(rgb,bgs,target,direction):
	B=direction;E,F,G=_hls(rgb);C=rgb;H=int((MAX_SHIFT if B<0 else MAX_SHIFT_DARK)/.005)+1
	for I in range(H):
		A=F+B*.005*I
		if A<0 or A>1:break
		C=_from_hls(E,A,G);D=tuple(round(A)for A in C)
		if min(contrast(D,A)for A in bgs)>=target:return D
def _flat(accent,alpha,surface):return mix(hex_to_rgb(surface),accent,alpha)
def derive_theme(rgb,theme):
	B=theme;D=SURFACES[B];N=D[1];I=-1 if B=='light'else 1;A=fit(rgb,D,MIN_TEXT,I)
	if A is None:return
	if B=='light':J=mix(A,(255,255,255),.88);K=rgb_to_hex(J);H=J;L=_from_hls(*(lambda h,l,s:(h,l-.06,s))(*_hls(A)))
	else:K='rgba(%d,%d,%d,.12)'%tuple(A);H=_flat(A,.12,N);L=_from_hls(*(lambda h,l,s:(h,l+.08,s))(*_hls(A)))
	G=fit(L,D+[rgb_to_hex(H)],MIN_TEXT,I)
	if G is None:return
	O,P,Q=_hls(A);E=_from_hls(O,P+(-.05 if B=='light'else-.06),Q);E=tuple(round(A)for A in E);C=None
	for F in ON_BRAND_CANDIDATES[B]:
		if min(contrast(F,A),contrast(F,E))>=MIN_TEXT:C=F;break
	if C is None:
		E=A
		for F in ON_BRAND_CANDIDATES[B]:
			if contrast(F,A)>=MIN_TEXT:C=F;break
	if C is None:return
	M=[('accent/'+B+' surfaces (text)',min(contrast(A,B)for B in D),MIN_TEXT),('accent-ink/accent-bg',contrast(G,H),MIN_TEXT),('accent-ink/surfaces',min(contrast(G,A)for A in D),MIN_TEXT),('on-brand/accent',contrast(C,A),MIN_TEXT),('on-brand/brand-2',contrast(C,E),MIN_TEXT),('accent/surfaces (controls)',min(contrast(A,B)for B in D),MIN_LARGE)]
	if any(A[1]<A[2]for A in M):return
	return{'tokens':{'accent':rgb_to_hex(A),'accent-bg':K,'accent-ink':rgb_to_hex(G),'on-brand':C},'brand-2':rgb_to_hex(E),'accent_rgb':tuple(A),'checks':[(A,round(B,2),C)for(A,B,C)in M]}
def derive_tokens(candidates):
	for A in candidates:
		B=derive_theme(A,'light');C=derive_theme(A,'dark')
		if B and C:return B,C,A
_NAMED={'black':'#000000','white':'#ffffff','red':'#ff0000','blue':'#0000ff','green':'#008000','navy':'#000080','yellow':'#ffff00','orange':'#ffa500','purple':'#800080','teal':'#008080','gray':'#808080','grey':'#808080','maroon':'#800000','olive':'#808000','lime':'#00ff00','aqua':'#00ffff','cyan':'#00ffff','fuchsia':'#ff00ff','magenta':'#ff00ff','silver':'#c0c0c0','gold':'#ffd700','pink':'#ffc0cb','brown':'#a52a2a','crimson':'#dc143c','indigo':'#4b0082','darkblue':'#00008b','darkgreen':'#006400','darkred':'#8b0000','royalblue':'#4169e1'}
_HEXRE=re.compile('#([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-zA-Z])')
_RGBRE=re.compile('rgba?\\(\\s*(\\d{1,3})\\s*[, ]\\s*(\\d{1,3})\\s*[, ]\\s*(\\d{1,3})')
_SVGPROP=re.compile('(?:fill|stroke|stop-color|color)\\s*[:=]\\s*["\\\']?\\s*([^;"\\\'>]+)',re.I)
def _svg_colors(text):
	if re.search('<script|\\bon[a-z]+\\s*=|javascript:',text,re.I):raise BrandError('קובץ ה-SVG מכיל קוד פעיל ולכן לא נקרא. שלחו לוגו כקובץ SVG נקי, או כ-PNG.\nThe SVG file contains active code, so it was not read. Send a clean SVG, or a PNG.')
	C={}
	for F in _SVGPROP.finditer(text):
		B=F.group(1).strip().lower();A=None;D=_HEXRE.search(B);E=_RGBRE.search(B)
		if D:A=hex_to_rgb(D.group(1))
		elif E:A=tuple(min(255,int(A))for A in E.groups())
		elif B in _NAMED:A=hex_to_rgb(_NAMED[B])
		if A:C[A]=C.get(A,0)+1
	return C
def _paeth(a,b,c):A=a+b-c;B,C,D=abs(A-a),abs(A-b),abs(A-c);return a if B<=C and B<=D else b if C<=D else c
def _png_counts(raw):
	P=raw
	if not P.startswith(b'\x89PNG\r\n\x1a\n'):raise BrandError('הקובץ אינו PNG תקין.')
	I,X,Q,R=8,[],None,None;L=Y=D=G=a=None
	while I+8<=len(P):
		b,M=struct.unpack('>I4s',P[I:I+8]);S=P[I+8:I+8+b];I+=12+b
		if M==b'IHDR':L,Y,D,G,h,h,a=struct.unpack('>IIBBBBB',S)
		elif M==b'PLTE':Q=S
		elif M==b'tRNS':R=S
		elif M==b'IDAT':X.append(S)
		elif M==b'IEND':break
	if L is None or not X:raise BrandError('קובץ ה-PNG פגום.')
	if a:raise _NeedPillow('PNG בשזירה')
	J={0:1,2:3,3:1,4:2,6:4}.get(G)
	if J is None:raise BrandError('סוג צבע לא נתמך ב-PNG.')
	c=zlib.decompress(b''.join(X));d=J*D;H=(L*d+7)//8;E=max(1,d//8);e=max(1,int(math.sqrt(L*Y/4e4)));N=bytearray(H);Z={};T=0
	for i in range(Y):
		U=c[T];B=bytearray(c[T+1:T+1+H]);T+=1+H
		if U==1:
			for A in range(E,H):B[A]=B[A]+B[A-E]&255
		elif U==2:
			for A in range(H):B[A]=B[A]+N[A]&255
		elif U==3:
			for A in range(H):F=B[A-E]if A>=E else 0;B[A]=B[A]+(F+N[A]>>1)&255
		elif U==4:
			for A in range(H):F=B[A-E]if A>=E else 0;j=N[A-E]if A>=E else 0;B[A]=B[A]+_paeth(F,N[A],j)&255
		N=B
		if i%e:continue
		for V in range(0,L,e):
			if D==8:W=V*J;k=B[W:W+J];C=list(k)
			elif D==16:W=V*J*2;C=[B[W+2*A]for A in range(J)]
			else:f=8//D;l=B[V//f];m=8-D*(V%f+1);g=l>>m&(1<<D)-1;C=[g if G==3 else g*255//((1<<D)-1)]
			F=255
			if G==0:K=(C[0],)*3
			elif G==2:K=tuple(C[:3])
			elif G==3:
				O=C[0]
				if not Q or O*3+3>len(Q):continue
				K=tuple(Q[O*3:O*3+3])
				if R and O<len(R):F=R[O]
			elif G==4:K,F=(C[0],)*3,C[1]
			else:K,F=tuple(C[:3]),C[3]
			if F>=128:Z[K]=Z.get(K,0)+1
	return Z
class _NeedPillow(Exception):0
def _pillow_counts(raw):
	try:from PIL import Image
	except ImportError:raise BrandError('קובץ הלוגו בפורמט שדורש רכיב קריאה נוסף שאינו מותקן (JPG, GIF, WebP או PNG בשזירה). שלחו את הלוגו כ-PNG רגיל או כ-SVG.\nThis logo format needs an extra image reader that is not installed (JPG, GIF, WebP or interlaced PNG). Send the logo as a plain PNG or an SVG.')
	try:B=Image.open(io.BytesIO(raw));B.load()
	except Exception:raise BrandError('קובץ הלוגו פגום או שאינו תמונה. שלחו קובץ אחר.\nThe logo file is damaged or is not an image.')
	C=B.convert('RGBA');C.thumbnail((200,200));A={}
	for(D,E,F,G)in C.getdata():
		if G>=128:A[D,E,F]=A.get((D,E,F),0)+1
	return A
def sniff(raw):
	A=raw
	if A.startswith(b'\x89PNG'):return'png'
	if A[:3]==b'\xff\xd8\xff':return'jpg'
	if A[:4]==b'GIF8':return'gif'
	if A[:4]==b'RIFF'and A[8:12]==b'WEBP':return'webp'
	B=A[:600].lstrip(b'\xef\xbb\xbf \r\n\t').lower()
	if B.startswith(b'<?xml')or B.startswith(b'<svg')or b'<svg'in B:return'svg'
def logo_counts(raw,use_pillow=None):
	B=raw;A=sniff(B)
	if A is None:raise BrandError('פורמט הלוגו לא מוכר. שלחו PNG או SVG.\nUnknown logo format. Send a PNG or an SVG.')
	if A=='svg':return A,_svg_colors(B.decode('utf-8','replace'))
	if A=='png'and use_pillow is not True:
		try:return A,_png_counts(B)
		except _NeedPillow:pass
		except(zlib.error,struct.error,IndexError):raise BrandError('קובץ ה-PNG פגום. שלחו קובץ אחר.\nThe PNG file is damaged.')
	return A,_pillow_counts(B)
def dominant_colors(counts):
	L=counts
	if not L:raise BrandError('לא נמצאו צבעים בלוגו (שקוף או ריק). שלחו לוגו אחר.\nNo colours were found in the logo.')
	M={}
	for(A,B)in L.items():
		N=tuple(A>>3 for A in A);G=M.setdefault(N,[0,0,0,0]);G[0]+=B
		for O in range(3):G[O+1]+=A[O]*B
	J=[]
	for(N,(B,S,T,G))in M.items():A=S/B,T/B,G/B;W,K,C=_hls(A);J.append([A,B,K,C])
	J.sort(key=lambda x:-x[1]);H=[]
	for E in J:
		for D in H:
			if sum((E[0][A]-D[0][A])**2 for A in range(3))<40**2:P=D[1]+E[1];D[0]=tuple((D[0][A]*D[1]+E[0][A]*E[1])/P for A in range(3));D[1]=P;break
		else:H.append(E)
	U=float(sum(A[1]for A in H));F,I=[],[]
	for(A,B,K,C)in H:
		A=tuple(int(round(A))for A in A);K=_hls(A)[1];C=_hls(A)[2];Q=min(A)>=235;V=max(A)<=24
		if Q and C<.5:continue
		if C>=.25 and not V:F.append((B*(.4+C),A))
		elif not Q:I.append((B,A))
	if not F and not I:raise BrandError('הלוגו כולו לבן או שקוף ואין בו צבע לגזור ממנו מותג. שלחו לוגו אחר.\nThe logo is all white or transparent, so there is no colour to build a brand from.')
	F.sort(key=lambda x:-x[0]);I.sort(key=lambda x:-x[0]);R=[B for(A,B)in F if A/(U or 1)>=.02]or[A for(B,A)in F[:1]];R+=[A for(B,A)in I];return R
def _rgba(rgb,a):A=rgb;return'rgba(%d,%d,%d,%s)'%(A[0],A[1],A[2],a)
def _theme_block(sel,tk,brand2,accent_rgb):C=accent_rgb;B=brand2;A=tk['accent'];return'%s{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s;--brand:%s;--brand-2:%s;--grad:linear-gradient(120deg,%s 0%%,%s 100%%);--glow:0 0 0 1px %s,0 8px 30px %s}'%(sel,A,tk['accent-bg'],tk['accent-ink'],tk['on-brand'],A,B,A,B,_rgba(C,'.35'),_rgba(C,'.18'))
LOGO_CSS='.client-logo{max-height:34px;max-width:190px;width:auto;height:auto;object-fit:contain;flex:0 0 auto;margin-inline-end:14px;border-radius:3px}\nhtml[dir="rtl"] .client-logo{object-position:right center}\nhtml[dir="ltr"] .client-logo{object-position:left center}\n@media print{.client-logo{max-height:28px}}'
def _logo_plate(logo_rgb):
	B=luminance(logo_rgb);A=''
	if B<.18:A+=':root:not([data-theme="light"]) .client-logo{background:#FFFFFF;padding:4px 8px}\n'
	if B>.45:A+=':root[data-theme="light"] .client-logo{background:#10221C;padding:4px 8px}\n'
	return A
def _data_uri(raw,kind):
	A=raw;C={'png':'image/png','jpg':'image/jpeg','gif':'image/gif','webp':'image/webp','svg':'image/svg+xml'}[kind]
	if len(A)>MAX_LOGO_BYTES:
		if kind=='svg':raise BrandError('קובץ הלוגו גדול מ-%d קילובייט. שלחו גרסה קטנה יותר.\nThe logo file is larger than %d KB.'%(MAX_LOGO_BYTES//1024,MAX_LOGO_BYTES//1024))
		try:from PIL import Image;B=Image.open(io.BytesIO(A));B.load();B.thumbnail((240,240));D=io.BytesIO();B.convert('RGBA').save(D,'PNG',optimize=True);A,C=D.getvalue(),'image/png'
		except Exception:raise BrandError('קובץ הלוגו גדול מ-%d קילובייט. שלחו גרסה קטנה יותר.\nThe logo file is larger than %d KB.'%(MAX_LOGO_BYTES//1024,MAX_LOGO_BYTES//1024))
		if len(A)>MAX_LOGO_BYTES:raise BrandError('קובץ הלוגו גדול מ-%d קילובייט גם אחרי הקטנה.\nThe logo is still too large after resizing.'%(MAX_LOGO_BYTES//1024))
	return'data:%s;base64,%s'%(C,base64.b64encode(A).decode('ascii'))
def build_brand(logo,lang='he',use_pillow=None):
	G=lang;D=logo
	if D is None or D==''or D==b'':return
	G='en'if str(G).lower().startswith('en')else'he'
	if isinstance(D,(bytes,bytearray)):H=bytes(D)
	else:
		try:
			with open(D,'rb')as M:H=M.read()
		except OSError:raise BrandError('קובץ הלוגו לא נמצא או לא נפתח. בדקו את הנתיב ושלחו שוב.\nThe logo file was not found.')
	N,O=logo_counts(H,use_pillow);I=dominant_colors(O);J=derive_tokens(I);P=_data_uri(H,N);C={'logo':P,'candidates':[rgb_to_hex(A)for A in I[:6]],'lang':G}
	if J is None:C.update(fallback=True,notice=NOTICE[G],source=None,tokens={A:dict(B)for(A,B)in AREO_DEFAULT.items()},checks=[],widget_css='');K=LOGO_CSS+'\n'+_logo_plate(I[0])
	else:E,F,L=J;C.update(fallback=False,notice='',source=rgb_to_hex(L),tokens={'light':E['tokens'],'dark':F['tokens']},checks=[('light '+A,B,C)for(A,B,C)in E['checks']]+[('dark '+A,B,C)for(A,B,C)in F['checks']]);K=_theme_block(':root:not([data-theme="light"])',F['tokens'],F['brand-2'],F['accent_rgb'])+'\n'+_theme_block(':root[data-theme="light"]',E['tokens'],E['brand-2'],E['accent_rgb'])+'\n'+LOGO_CSS+'\n'+_logo_plate(L);A,B=E['tokens'],F['tokens'];C['widget_css']='.af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}\n@media (prefers-color-scheme:dark){.af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}}\n:root[data-mode="dark"] .af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}\n:root[data-mode="light"] .af{--accent:%s;--accent-bg:%s;--accent-ink:%s;--on-brand:%s}'%((A['accent'],A['accent-bg'],A['accent-ink'],A['on-brand'])+(B['accent'],B['accent-bg'],B['accent-ink'],B['on-brand'])+(B['accent'],B['accent-bg'],B['accent-ink'],B['on-brand'])+(A['accent'],A['accent-bg'],A['accent-ink'],A['on-brand']))
	C['css']=K.strip();C['html']='<style id="client-brand">\n'+C['css']+'\n</style>';return C
def merge_into_payload(payload,brand):
	C=payload;A=brand
	if A is None:return C
	B=C.setdefault('meta',{}).setdefault('branding',{});B['css']=A['css'];B['logo']=A['logo'];B['notice']=A['notice'];B['fallback']=A['fallback'];return C
def apply_to_html(html,brand):
	C=brand;A=html
	if C is None:return A
	B=A.find('</head>')
	if B<0:return A
	return A[:B]+C['html']+'\n'+A[B:]
def main(argv=None):
	import json
	try:from common.cli import guard_out,parser,run,write_json
	except ImportError:import os;sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.cli import guard_out,parser,run,write_json
	C=parser('מיתוג לקוח מלוגו: אסימונים סגורים, בדיקת ניגודיות והודעה',out_required=False);C.add_argument('--logo',required=True,help='קובץ לוגו (PNG או SVG, ובהתקנה עם Pillow גם JPG)');C.add_argument('--lang',default='he',choices=('he','en'));A=C.parse_args(argv)
	try:B=build_brand(A.logo,A.lang)
	except BrandError as D:
		try:sys.stdout.reconfigure(encoding='utf-8')
		except Exception:pass
		print(D);return 3
	if A.out:E=write_json(A.out,B,[A.logo]);print('written',E)
	print('fallback'if B['fallback']else'branded',B['source'],B['notice']);return 0
if __name__=='__main__':sys.exit(main())
