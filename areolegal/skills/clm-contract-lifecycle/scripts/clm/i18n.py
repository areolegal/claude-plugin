# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import contextlib
LANGS='he','en'
_state={'lang':'he'}
def norm(lang):return'en'if str(lang or'').strip().lower()[:2]=='en'else'he'
def lang():return _state['lang']
def en():return _state['lang']=='en'
def t(he,en_text):return en_text if _state['lang']=='en'else he
@contextlib.contextmanager
def using(value):
	A=_state['lang'];_state['lang']=norm(value)
	try:yield _state['lang']
	finally:_state['lang']=A
