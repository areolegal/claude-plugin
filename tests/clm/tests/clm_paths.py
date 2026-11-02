"""Where the CLM suite finds what it tests.

The suite was delivered next to the skill (CLM/tests beside CLM/scripts). In the plugin it lives under
plugin/tests/clm/tests, while the code ships in areolegal/skills/clm-contract-lifecycle and the professional
references (references/<file>) are served content in server/content/clm-contract-lifecycle (the CLM add-on is
paid, so its references are not in the plugin). Every path the tests use comes from here.
"""
import os
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(TESTS)))
SKILL = os.path.join(PLUGIN, "areolegal", "skills", "clm-contract-lifecycle")
SCRIPTS = os.path.join(SKILL, "scripts")
HARNESS = os.path.join(TESTS, "template_harness.js")
REFS_DIR = os.environ.get("AREO_CLM_REFERENCES") or os.path.join(
    os.path.dirname(PLUGIN), "server", "content", "clm-contract-lifecycle")
VOICE = os.path.join(PLUGIN, "areolegal", "lib", "common", "voice_check.py")

if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)
