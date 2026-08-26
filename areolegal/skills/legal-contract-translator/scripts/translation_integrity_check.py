#!/usr/bin/env python3
import argparse, json, re, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

W='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def text_of(path):
    p=Path(path)
    if p.suffix.lower()=='.docx':
        with zipfile.ZipFile(p) as z:
            xml=z.read('word/document.xml')
        root=ET.fromstring(xml)
        parts=[]
        for para in root.iter(W+'p'):
            parts.append(''.join(t.text or '' for t in para.iter(W+'t')))
        return '\n'.join(parts)
    return p.read_text(encoding='utf-8')

def tokens(text):
    # Numeric integrity: dates, percentages, currency-like values and section-number patterns.
    nums=re.findall(r'(?<![\w])(?:\d{1,4}(?:[.,]\d+)*%?|\d{1,2}[./-]\d{1,2}[./-]\d{2,4})(?![\w])', text)
    currencies=re.findall(r'(?:[$€£₪]\s?\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP|ILS|NIS))', text, flags=re.I)
    headings=re.findall(r'(?m)^\s*(\d+(?:\.\d+){0,4})[.)]?\s+', text)
    return {'numeric_tokens': nums, 'currency_tokens': currencies, 'section_numbers': headings}

def multiset_diff(a,b):
    from collections import Counter
    ca,cb=Counter(a),Counter(b)
    return list((ca-cb).elements()), list((cb-ca).elements())

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('source'); ap.add_argument('target'); ap.add_argument('--out')
    args=ap.parse_args()
    s=tokens(text_of(args.source)); t=tokens(text_of(args.target))
    report={'checks':{},'pass':True}
    for key in s:
        missing,extra=multiset_diff(s[key],t[key])
        report['checks'][key]={'missing_in_target':missing,'extra_in_target':extra}
        if missing or extra: report['pass']=False
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.out: Path(args.out).write_text(text+'\n',encoding='utf-8')
    print(text)
    raise SystemExit(0 if report['pass'] else 1)
if __name__=='__main__': main()
