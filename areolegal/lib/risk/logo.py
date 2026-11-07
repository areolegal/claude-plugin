# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import base64,io,os,struct,sys
if __name__=='__main__':sys.dont_write_bytecode=True
try:from common.cli import guard_out,parser,run,write_json;from common.paths import long_path
except ImportError:import sys as _sys;_sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))));from common.cli import guard_out,parser,run,write_json;from common.paths import long_path
MAX_BYTES=153600
MAX_PX=240
_MIME={b'\x89PNG':'image/png',b'\xff\xd8\xff':'image/jpeg',b'GIF8':'image/gif',b'RIFF':'image/webp'}
class LogoError(Exception):0
def _mime(b):
	for(B,A)in _MIME.items():
		if b.startswith(B):
			if A=='image/webp'and b[8:12]!=b'WEBP':continue
			return A
def _png_size(b):
	if b.startswith(b'\x89PNG\r\n\x1a\n')and b[12:16]==b'IHDR':return struct.unpack('>II',b[16:24])
def data_uri(b,mime):return'data:%s;base64,%s'%(mime,base64.b64encode(b).decode('ascii'))
def uri_bytes(uri):return len(uri)*3//4
def logo_data_uri(path,max_bytes=MAX_BYTES,max_px=MAX_PX):
	E=max_px;C=max_bytes
	with open(long_path(path),'rb')as L:D=L.read()
	F=_mime(D)
	if not F:raise LogoError('הקובץ אינו תמונה מוכרת (PNG, JPEG, GIF או WebP)')
	G=_png_size(D)
	if uri_bytes(data_uri(D,F))<=C and(G is None or max(G)<=E*2):return data_uri(D,F)
	try:from PIL import Image as H
	except ImportError:raise LogoError('הלוגו %d קילובייט, מעל %d, ואין Pillow להקטנה: לבקש מהלקוח לוגו קטן מ-%d קילובייט'%(len(D)//1024,C//1024,C//1024))
	I=H.open(io.BytesIO(D));I.load()
	for J in(E,E*3//4,E//2,E//3):
		A=I.copy();A.thumbnail((J,J))
		if A.mode in('P','LA','RGBA')or'transparency'in A.info:
			B=io.BytesIO();A.convert('RGBA').save(B,'PNG',optimize=True)
			if uri_bytes(data_uri(B.getvalue(),'image/png'))<=C:return data_uri(B.getvalue(),'image/png')
			K=H.new('RGB',A.size,(255,255,255));K.paste(A.convert('RGBA'),mask=A.convert('RGBA').split()[-1]);A=K
		A=A.convert('RGB')
		for M in(85,70,55):
			B=io.BytesIO();A.save(B,'JPEG',quality=M,optimize=True)
			if uri_bytes(data_uri(B.getvalue(),'image/jpeg'))<=C:return data_uri(B.getvalue(),'image/jpeg')
	raise LogoError('לא ניתן להקטין את הלוגו מתחת ל-%d קילובייט'%(C//1024))
def main(argv=None):
	C=parser('הלוגו כ-data URI של עד 150 קילובייט',out_required=False);C.add_argument('--logo',required=True,help='קובץ הלוגו מהפרופיל (קריאה בלבד)');A=C.parse_args(argv);B=logo_data_uri(A.logo)
	if A.out:
		D=guard_out(A.out,[A.logo])
		with open(D,'w',encoding='ascii')as E:E.write(B)
	print('%s %d bytes'%(B[:30],uri_bytes(B)));return 0
if __name__=='__main__':sys.exit(run(main))
