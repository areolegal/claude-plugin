#!/usr/bin/env python3
"""Validate that rendered playbook HTML is an interactive application workbench."""
import sys
from pathlib import Path

REQUIRED_COMMON = [
    'class="app-shell"', 'class="sidebar"', 'class="app-header"',
    'id="tabs"', 'id="overview"', 'id="segments"', 'id="matrix"',
    'id="topics"', 'id="decisions"', 'localStorage', 'downloadUpdated',
    'finalizePlaybook', 'class="footer-actions"'
]
REQUIRED_HE = ['<title>מדיניות חוזית</title>', '"family": "סוג החוזים"', '"title": "מדיניות חוזית"']
FORBIDDEN_HE = ['"family": "משפחת חוזים"', '<title>סביבת עבודה למדיניות חוזית</title>']
REQUIRED_EN = ['<title>Contract Policy</title>', '"family": "Contract types"', '"title": "Contract Policy"']


def main(path):
    text = Path(path).read_text(encoding='utf-8')
    errors = []
    for marker in REQUIRED_COMMON:
        if marker not in text:
            errors.append(f'missing application marker: {marker}')
    is_he = '<html lang="he"' in text
    for marker in (REQUIRED_HE if is_he else REQUIRED_EN):
        if marker not in text:
            errors.append(f'missing localized UI marker: {marker}')
    if is_he:
        for marker in FORBIDDEN_HE:
            if marker in text:
                errors.append(f'forbidden legacy UI label: {marker}')
    if errors:
        print('INVALID')
        for e in errors:
            print('-', e)
        return 1
    print('VALID')
    return 0

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('usage: validate_playbook_html.py OUTPUT.html')
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
