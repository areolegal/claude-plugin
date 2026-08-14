#!/usr/bin/env python3
import argparse, hashlib, json, os, re
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

def normalized_stem(name):
    s = Path(name).stem.lower()
    s = re.sub(r'\b(v|ver|version|rev|draft|final|signed)[-_ ]?\d*[a-z]?\b', ' ', s)
    s = re.sub(r'\b20\d{2}[-_. ]\d{1,2}[-_. ]\d{1,2}\b', ' ', s)
    s = re.sub(r'[^a-z0-9\u0590-\u05ff]+', ' ', s)
    return ' '.join(s.split())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--out', default='corpus-manifest.json')
    args = ap.parse_args()
    root = Path(args.root).resolve()
    rows = []
    by_hash = {}
    for p in sorted(root.rglob('*')):
        if not p.is_file(): continue
        digest = sha256(p)
        row = {
            'path': str(p.relative_to(root)), 'size': p.stat().st_size,
            'mtime': p.stat().st_mtime, 'sha256': digest,
            'extension': p.suffix.lower(), 'normalized_stem': normalized_stem(p.name)
        }
        by_hash.setdefault(digest, []).append(row['path'])
        rows.append(row)
    duplicates = [v for v in by_hash.values() if len(v) > 1]
    out = {'root': str(root), 'file_count': len(rows), 'files': rows, 'exact_duplicate_groups': duplicates}
    Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"wrote {args.out}: {len(rows)} files, {len(duplicates)} exact-duplicate groups")

if __name__ == '__main__':
    main()
