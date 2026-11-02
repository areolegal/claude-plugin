"""
extract_track_changes.py

חילוץ של תיקונים בעקוב אחר שינויים והערות מתוך קובץ DOCX.
הפלט הוא JSON מובנה שמשמש את הסקריפטים האחרים בסקיל.

שימוש:
    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/extract_track_changes.py" input.docx --output changes.json
    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/extract_track_changes.py" input.docx --output changes.json --compare-to-previous prev.docx

הקובץ מטפל ב:
    - w:ins (הוספות)
    - w:del (מחיקות)
    - w:moveTo / w:moveFrom (העברות)
    - w:comment (הערות שוליים)
    - word/commentsExtended.xml (שרשורים: w15:paraIdParent ו-w15:done). לכל בועה parent_id (הבועה שהיא עונה
      לה), thread_root_id (בועת השורש) ו-done, וברשימה threads כל שרשור עם התשובות שלו. כך מזהים בועה של הצד
      שכנגד שעונה בשרשור לבועה שלנו, הסימן החזק ביותר לסבב המשך (בדיקה עצמאית S1c, H4, 28.10.2026)
    - w:author (זיהוי המחבר של כל שינוי)
"""

import argparse
from datetime import date as _date


def _he_date(d):
    # כלל 3.6: D.M.YYYY בטקסט בעברית (הסקריפט אינו מייבא את lib; state_builder.display_date הוא המקבילה)
    return '%d.%d.%d' % (d.day, d.month, d.year)

import json
import os
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError באמצע הפלט
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

# הספרייה המשותפת נותנת guard_out ו-load_docx_or_explain. בלעדיה הסקריפט רץ עם שתי בדיקות מינימליות: הפלט לעולם אינו
# נכתב על קובץ קלט או על מסמך קיים (הרצה S1d: --output <הטיוטה>.docx דרס את הטיוטה של הצד שכנגד ב-JSON), וקובץ שאינו
# docx מקבל הודעה ולא traceback
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
    import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא
    from common.cli import OutputRefused, guard_out, load_docx_or_explain
except ImportError:
    class OutputRefused(Exception):
        pass

    def guard_out(out, inputs=()):
        k = os.path.normcase(os.path.realpath(out))
        if any(p and os.path.normcase(os.path.realpath(p)) == k for p in inputs):
            raise OutputRefused('--output הוא קובץ קלט: %s' % out)
        if os.path.isfile(k) and k.lower().endswith(('.docx', '.doc', '.docm', '.dotx', '.pdf', '.xlsx', '.pptx')):
            raise OutputRefused('--output הוא מסמך קיים: %s' % out)
        return os.path.abspath(out)

    def load_docx_or_explain(path, loader=None, strict_ok=False):
        if not os.path.exists(path):
            return None, 'הקובץ לא נמצא: %s\nFile not found: %s' % (path, path), 1
        try:
            with zipfile.ZipFile(path) as z:
                z.getinfo('word/document.xml')
            return path, None, 0
        except Exception as e:  # noqa: BLE001
            n = os.path.basename(path)
            return None, 'לא ניתן לקרוא את %s כמסמך Word (%s).\n%s cannot be read as a Word document (%s).' % (
                n, type(e).__name__, n, type(e).__name__), 2

# Namespaces ב-DOCX
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
    'w15': 'http://schemas.microsoft.com/office/word/2012/wordml',
}

# רישום namespaces ל-ElementTree
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)


def _q(tag):
    """המרת w:tag ל-{namespace}tag עבור ElementTree."""
    prefix, name = tag.split(':')
    return f'{{{NS[prefix]}}}{name}'


def _get_text_from_run(run_elem):
    """חילוץ הטקסט מתוך w:r."""
    texts = []
    for t in run_elem.iter(_q('w:t')):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


def _get_paragraph_index(para, all_paras):
    """החזרת אינדקס של פסקה ברשימה הכוללת."""
    for i, p in enumerate(all_paras):
        if p is para:
            return i
    return -1


def _get_paragraph_text(para):
    """חילוץ הטקסט המלא של פסקה."""
    texts = []
    for t in para.iter(_q('w:t')):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)


def _get_paragraph_first_words(para, n=5):
    """המילים הראשונות של פסקה (לזיהוי מיקום)."""
    text = _get_paragraph_text(para).strip()
    words = text.split()
    return ' '.join(words[:n])


def extract_track_changes(docx_path):
    """חילוץ כל ה-track changes וההערות מקובץ DOCX."""
    docx_path = Path(docx_path)
    if not docx_path.exists():
        raise FileNotFoundError(f'קובץ לא נמצא: {docx_path}')

    changes = []
    comments = []

    with zipfile.ZipFile(docx_path, 'r') as zf:
        # קריאת המסמך הראשי
        with zf.open('word/document.xml') as f:
            doc_tree = ET.parse(f)
        doc_root = doc_tree.getroot()

        # קריאת ההערות אם קיימות
        comments_data = {}
        try:
            with zf.open('word/comments.xml') as f:
                comments_tree = ET.parse(f)
            comments_root = comments_tree.getroot()
            for comment in comments_root.iter(_q('w:comment')):
                cid = comment.get(_q('w:id'))
                author = comment.get(_q('w:author'))
                date = comment.get(_q('w:date'))
                text = ''
                for t in comment.iter(_q('w:t')):
                    if t.text:
                        text += t.text
                paras = list(comment.iter(_q('w:p')))
                comments_data[cid] = {
                    'id': cid,
                    'author': author,
                    'date': date,
                    'text': text,
                    # מזהה הפסקה האחרונה של הבועה: אליו מצביע commentsExtended
                    'para_id': paras[-1].get(_q('w14:paraId')) if paras else None,
                }
        except KeyError:
            pass

        # שרשורים: paraIdParent מצביע על בועת השורש (כך Word כותב), ו-done הוא "בוצע"
        ext = {}
        try:
            with zf.open('word/commentsExtended.xml') as f:
                for e in ET.parse(f).getroot().iter(_q('w15:commentEx')):
                    ext[e.get(_q('w15:paraId'))] = (e.get(_q('w15:paraIdParent')), e.get(_q('w15:done')) == '1')
        except KeyError:
            pass
        by_pid = {c['para_id']: c for c in comments_data.values() if c.get('para_id')}
        for c in comments_data.values():
            parent_pid, done = ext.get(c.get('para_id'), (None, False))
            c['parent_id'] = by_pid[parent_pid]['id'] if parent_pid in by_pid else None
            c['done'] = done
        for c in comments_data.values():
            cur, seen = c, set()
            while cur.get('parent_id') in comments_data and cur['id'] not in seen:
                seen.add(cur['id'])
                cur = comments_data[cur['parent_id']]
            c['thread_root_id'] = cur['id']

        # מעבר על כל הפסקאות
        body = doc_root.find(_q('w:body'))
        if body is None:
            return {'changes': [], 'comments': []}

        all_paras = list(body.iter(_q('w:p')))

        for para_idx, para in enumerate(all_paras):
            para_text = _get_paragraph_text(para)
            first_words = _get_paragraph_first_words(para)
            paragraph_locator = first_words if first_words else f'פסקה ריקה {para_idx}'

            # חילוץ הוספות
            for ins in para.iter(_q('w:ins')):
                author = ins.get(_q('w:author'), 'unknown')
                date = ins.get(_q('w:date'), '')
                ins_text = ''
                for r in ins.iter(_q('w:r')):
                    ins_text += _get_text_from_run(r)
                if ins_text:
                    changes.append({
                        'type': 'insertion',
                        'paragraph_index': para_idx,
                        'paragraph_locator': paragraph_locator,
                        'paragraph_full_text': para_text,
                        'old_text': '',
                        'new_text': ins_text,
                        'author': author,
                        'date': date,
                    })

            # מחיקה בתוך הוספה של מחבר אחר (הצד שכנגד מחק בעקוב אחר שינויים את מה שהוספנו): inside_insertion_by
            outer_ins = {}
            for ins in para.iter(_q('w:ins')):
                for inner in ins.iter(_q('w:del')):
                    outer_ins[id(inner)] = ins.get(_q('w:author'), 'unknown')

            # חילוץ מחיקות
            for d in para.iter(_q('w:del')):
                author = d.get(_q('w:author'), 'unknown')
                date = d.get(_q('w:date'), '')
                del_text = ''
                # ב-deletion, הטקסט נמצא ב-w:delText בתוך w:r
                for dt in d.iter(_q('w:delText')):
                    if dt.text:
                        del_text += dt.text
                if del_text:
                    changes.append({
                        'type': 'deletion',
                        'paragraph_index': para_idx,
                        'paragraph_locator': paragraph_locator,
                        'paragraph_full_text': para_text,
                        'old_text': del_text,
                        'new_text': '',
                        'author': author,
                        'date': date,
                        'inside_insertion_by': outer_ins.get(id(d)),
                    })

            # חילוץ הפניות להערות בפסקה
            for cmnt_ref in para.iter(_q('w:commentReference')):
                cid = cmnt_ref.get(_q('w:id'))
                if cid in comments_data:
                    cdata = comments_data[cid].copy()
                    cdata['paragraph_index'] = para_idx
                    cdata['paragraph_locator'] = paragraph_locator
                    cdata['paragraph_full_text'] = para_text
                    comments.append(cdata)

    # תשובה בשרשור שאין לה עוגן משלה במסמך נכנסת בכל זאת, במקום של השורש שלה
    listed = {c['id'] for c in comments}
    for cid, c in comments_data.items():
        if cid not in listed:
            root = next((x for x in comments if x['id'] == c.get('thread_root_id')), None)
            cdata = c.copy()
            for k in ('paragraph_index', 'paragraph_locator', 'paragraph_full_text'):
                cdata[k] = root.get(k) if root else None
            comments.append(cdata)
            listed.add(cid)
    threads = {}
    for c in comments:
        threads.setdefault(c.get('thread_root_id') or c['id'], []).append(c['id'])
    thread_list = []
    for root_id, ids in threads.items():
        root = comments_data.get(root_id) or {}
        replies = [comments_data[i] for i in ids if i != root_id and i in comments_data]
        thread_list.append({
            'root_id': root_id,
            'root_author': root.get('author'),
            'done': bool(root.get('done')),
            'replies': [{'id': r['id'], 'author': r['author'], 'date': r['date']} for r in replies],
            # מחבר אחר מזה של השורש ענה בשרשור: למשל הצד שכנגד לבועה שלנו
            'answered_by_other': any(r['author'] != root.get('author') for r in replies),
        })

    return {
        'changes': changes,
        'comments': comments,
        'threads': thread_list,
        'total_changes': len(changes),
        'total_comments': len(comments),
        'future_dated': future_dated(changes, comments_data.values()),
    }


def future_dated(changes, comments, today=None):
    """שינויים ובועות שמתוארכים אחרי היום. אזהרה בקליטה, לא חוסמת: התאריכים אינם משתנים, אבל התשובות שלנו יתוארכו
    היום ויופיעו לפני הבועות שהן עונות להן (S1d-R2, 28.10.2026)."""
    day = (today or _date.today()).isoformat()
    out = [{'kind': 'comment', 'author': c.get('author'), 'date': c.get('date')} for c in comments
           if (c.get('date') or '')[:10] > day]
    out += [{'kind': ch.get('type'), 'author': ch.get('author'), 'date': ch.get('date')} for ch in changes
            if (ch.get('date') or '')[:10] > day]
    return out


def merge_paired_changes(extracted):
    """מיזוג מחיקה והוספה צמודות לתיקון אחד.

    כשמשתמש מתקן טקסט ב-Word, זה מופיע כשתי פעולות נפרדות (מחיקה ואז הוספה)
    באותה הפסקה. כאן אנחנו מזהים את הזוגות וממזגים אותם לתיקון אחד.
    """
    changes = extracted['changes']
    if not changes:
        return extracted

    merged = []
    skip_next = False

    for i, ch in enumerate(changes):
        if skip_next:
            skip_next = False
            continue

        # האם זו מחיקה שאחריה הוספה באותה הפסקה ואותו מחבר?
        if (i + 1 < len(changes)
                and ch['type'] == 'deletion'
                and changes[i + 1]['type'] == 'insertion'
                and ch['paragraph_index'] == changes[i + 1]['paragraph_index']
                and ch['author'] == changes[i + 1]['author']):
            merged.append({
                'type': 'modification',
                'paragraph_index': ch['paragraph_index'],
                'paragraph_locator': ch['paragraph_locator'],
                'paragraph_full_text': ch['paragraph_full_text'],
                'old_text': ch['old_text'],
                'new_text': changes[i + 1]['new_text'],
                'author': ch['author'],
                'date': ch['date'],
            })
            skip_next = True
        else:
            merged.append(ch)

    extracted['changes'] = merged
    extracted['total_changes'] = len(merged)
    return extracted


def compare_rounds(current_extracted, previous_extracted):
    """השוואה בין סבב נוכחי לסבב קודם.

    הפלט הוא רשימת שינויים מסווגים לפי המצב מהסבב הקודם:
        NEW - שינוי שלא היה בסבב הקודם.
        REPEATED - שינוי שכבר הוצע ונדחה בסבב הקודם.
        EVOLVED - שינוי באותה קטגוריה אבל בנוסח שונה.
    """
    current_changes = current_extracted['changes']
    previous_changes = previous_extracted['changes']

    # יצירת hash פשוט לכל שינוי לפי הפסקה והטקסט
    def change_signature(ch):
        return (ch.get('paragraph_locator', ''), ch.get('new_text', ''), ch.get('old_text', ''))

    prev_sigs = {change_signature(ch): ch for ch in previous_changes}
    prev_paragraphs = {ch['paragraph_locator']: ch for ch in previous_changes}

    classified = []
    for ch in current_changes:
        sig = change_signature(ch)
        if sig in prev_sigs:
            ch['comparison_status'] = 'REPEATED'
            ch['previous_round'] = prev_sigs[sig]
        elif ch['paragraph_locator'] in prev_paragraphs:
            ch['comparison_status'] = 'EVOLVED'
            ch['previous_round'] = prev_paragraphs[ch['paragraph_locator']]
        else:
            ch['comparison_status'] = 'NEW'
        classified.append(ch)

    current_extracted['changes'] = classified
    current_extracted['comparison_done'] = True
    return current_extracted


def main(argv=None):
    parser = argparse.ArgumentParser(description='חילוץ track changes מקובץ DOCX')
    parser.add_argument('input', help='קובץ DOCX קלט')
    parser.add_argument('--output', default='changes.json',
                        help='קובץ פלט JSON. לעולם לא קובץ הקלט, מסמך קיים או תיקיית מקור של הלקוח')
    parser.add_argument('--compare-to-previous', help='קובץ DOCX מסבב קודם להשוואה')
    parser.add_argument('--no-merge', action='store_true', help='בטל מיזוג של מחיקה והוספה לתיקון')

    args = parser.parse_args(argv)

    # הפלט נבדק לפני כל קריאה: לא על אחד הקלטים, לא על docx קיים ולא בתיקיית מקור (קוד 1, כמו בשאר נקודות הכניסה)
    try:
        guard_out(args.output, inputs=[args.input, args.compare_to_previous])
    except OutputRefused as exc:
        print('סירוב: %s' % exc)
        return 1
    # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback של zipfile
    for p in [args.input] + ([args.compare_to_previous] if args.compare_to_previous else []):
        ok, msg, code = load_docx_or_explain(p, loader=False)
        if ok is None:
            print(msg)
            return code

    # חילוץ הסבב הנוכחי
    print(f'מחלץ track changes מ: {args.input}')
    extracted = extract_track_changes(args.input)

    if not args.no_merge:
        extracted = merge_paired_changes(extracted)

    # השוואה אם יש סבב קודם
    if args.compare_to_previous:
        print(f'משווה לסבב קודם: {args.compare_to_previous}')
        prev = extract_track_changes(args.compare_to_previous)
        if not args.no_merge:
            prev = merge_paired_changes(prev)
        extracted = compare_rounds(extracted, prev)

    # שמירה
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(extracted, f, ensure_ascii=False, indent=2)

    print(f'נשמר: {output_path}')
    print(f'סה"כ שינויים: {extracted["total_changes"]}')
    print(f'סה"כ הערות: {extracted["total_comments"]}')
    fut = extracted.get('future_dated') or []
    if fut:
        print('אזהרה (לא חוסמת): %d בועות או שינויים מתוארכים אחרי היום (%s), עד %s (%s). תשובות שלנו יתוארכו היום, '
              'ולכן יופיעו לפניהם. התאריכים לא שונו' % (len(fut), _he_date(_date.today()),
                                                       _he_date(_date.fromisoformat(max(x['date'] for x in fut)[:10])),
                                                       ', '.join(sorted({x['author'] or '?' for x in fut}))))
    return 0


if __name__ == '__main__':
    sys.exit(main())
