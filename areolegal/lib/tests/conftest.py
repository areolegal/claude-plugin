# -*- coding: utf-8 -*-
"""קליטת אישור כותבת עותק מקומי ל-~/Areo-playbooks-local. בבדיקות הוא נכתב לתיקייה זמנית (AREO_LOCAL_COPY_BASE),
גם דרך סקריפט שרץ כתהליך נפרד ויורש את הסביבה. תיקיית הבית עצמה לא משתנה (Chrome ומחזיק המפתחות תלויים בה)."""
import pytest


@pytest.fixture(autouse=True)
def _temp_local_copy(tmp_path_factory, monkeypatch):
    monkeypatch.setenv("AREO_LOCAL_COPY_BASE", str(tmp_path_factory.mktemp("local-copy")))
