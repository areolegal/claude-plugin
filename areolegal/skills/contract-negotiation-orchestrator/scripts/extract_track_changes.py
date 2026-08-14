"""
extract_track_changes.py

חילוץ של תיקונים בעקוב אחר שינויים והערות מתוך קובץ DOCX.
הפלט הוא JSON מובנה שמשמש את הסקריפטים האחרים בסקיל.

שימוש:
    python extract_track_changes.py input.docx --output changes.json
    python extract_track_changes.py input.docx --output changes.json --compare-to-previous prev.docx

הקובץ מטפל ב:
    - w:ins (הוספות)
    - w:del (מחיקות)
    - w:moveTo / w:moveFrom (העברות)
    - w:comment (הערות שוליים)
    - w:author (זיהוי המחבר של כל שינוי)
"""

import argparse
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Namespaces ב-DOCX
NS = {
    'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'w14': 'http://schemas.microsoft.com/office/word/2010/wordml',
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
                comments_data[cid] = {
                    'id': cid,
                    'author': author,
                    'date': date,
                    'text': text,
                }
        except KeyError:
            pass

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

    return {
        'changes': changes,
        'comments': comments,
        'total_changes': len(changes),
        'total_comments': len(comments),
    }


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


def main():
    parser = argparse.ArgumentParser(description='חילוץ track changes מקובץ DOCX')
    parser.add_argument('input', help='קובץ DOCX קלט')
    parser.add_argument('--output', default='changes.json', help='קובץ פלט JSON')
    parser.add_argument('--compare-to-previous', help='קובץ DOCX מסבב קודם להשוואה')
    parser.add_argument('--no-merge', action='store_true', help='בטל מיזוג של מחיקה והוספה לתיקון')

    args = parser.parse_args()

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


if __name__ == '__main__':
    main()
