# -*- coding: utf-8 -*-
"""policy_match לכל סעיף מפתח: match / differs רק כשיש פלייבוק שמתאים להסכם, אחרת not_compared."""
import os
import sys

import clm_paths  # noqa: E402,F401  (puts the skill scripts on sys.path)
from clm.assemble import POLICY_MATCH, policy_match  # noqa: E402


def test_values_from_extraction_kept_when_a_playbook_matches():
    assert policy_match({"policy_match": "match"}, "הספק") == "match"
    assert policy_match({"policy_match": "differs"}, "the Supplier") == "differs"


def test_no_playbook_or_bad_value_is_not_compared():
    assert policy_match({"policy_match": "match"}, None) == "not_compared"
    assert policy_match({"policy_match": "תואם"}, "הספק") == "not_compared"
    assert policy_match({}, "הספק") == "not_compared"
    assert set(POLICY_MATCH) == {"match", "differs", "not_compared"}
