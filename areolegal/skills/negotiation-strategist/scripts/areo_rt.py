# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import os,sys,tempfile
def _newest_rt_dir():
	B,C=None,-1.
	try:F=os.listdir(tempfile.gettempdir())
	except OSError:return
	for D in F:
		if not D.startswith('areo-rt-'):continue
		A=os.path.join(tempfile.gettempdir(),D)
		if os.path.isdir(os.path.join(A,'lib','common')):
			try:E=os.path.getmtime(A)
			except OSError:continue
			if E>C:B,C=A,E
	return B
def areo_lib():
	C=os.path.dirname(os.path.abspath(__file__))
	for A in(os.environ.get('AREO_RT'),os.path.join(C,'..','..','..'),_newest_rt_dir()):
		if A:
			B=os.path.normpath(os.path.join(A,'lib'))
			if os.path.isdir(os.path.join(B,'common')):return B
def ensure_lib():
	A=areo_lib()
	if A and A not in sys.path:sys.path.append(A)
	return A
