# -*- coding: utf-8 -*-
# Copyright (c) Areo. All rights reserved. Licensed under the terms at https://areo.co.il/legal/terms
import sys
from pathlib import Path
for _s in(sys.stdout,sys.stderr):
	try:_s.reconfigure(encoding='utf-8',errors='replace')
	except(AttributeError,ValueError):pass
LIB=Path(__file__).resolve().parents[3]/'lib'
if LIB.is_dir()and str(LIB)not in sys.path:sys.path.insert(0,str(LIB))
