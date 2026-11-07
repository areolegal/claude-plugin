# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import re
THEME_KEYS='primary_light','secondary_light','soft_light','on_light','primary_dark','secondary_dark','soft_dark','on_dark'
_HEX=re.compile('^#[0-9A-Fa-f]{6}$')
def valid_tokens(t):return isinstance(t,dict)and set(t)==set(THEME_KEYS)and all(_HEX.match(str(t[A]))for A in THEME_KEYS)
def profile_theme(profile):
	B=((profile or{}).get('branding')or{}).get('theme')or{};A=B.get('tokens')or{}
	if B.get('choice')!='yes':return
	A={B:A.get(B)for B in THEME_KEYS};return A if valid_tokens(A)else None
def apply_theme(data,profile):
	B=profile;C=((B or{}).get('branding')or{}).get('theme')or{};A=profile_theme(B)
	if not A:
		if C.get('choice')=='yes':return'מיתוג: אושר, אך הצבעים עוד לא נגזרו (build_profile.py --derive-theme). התוצר נבנה בעיצוב הרגיל'
		return
	for D in[data.setdefault('meta',{})]+[A.setdefault('meta',{})for A in(data.get('books')or{}).values()if isinstance(A,dict)]:D.setdefault('branding',{})['theme']=dict(A)
	return'מיתוג: צבעי המותג של הלקוח הוחלו (%s)'%A['primary_light']
