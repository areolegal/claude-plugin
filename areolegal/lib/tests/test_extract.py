# -*- coding: utf-8 -*-
"""בדיקות ל-risk/extract_corpus.py על מסמך Word סינתטי קטן שנבנה בתוך הבדיקה: קבל הכול / דחה הכול
(ins, del, moveFrom, moveTo), כל אופני ההסתרה, תיבת טקסט שנספרת פעם אחת, בועות עם הקטע המעוגן, וכותרת עליונה."""
import json

import pytest
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from risk.extract_corpus import body_text, extract, main, reject_all_equals  # noqa: E402

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
WP = 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
FX = ROOT / 'tests' / 'fixtures' / 'risk'

CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
      '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="xml" ContentType="application/xml"/>'
      '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
      '</Types>')
RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
        '</Relationships>')


def r(text, rpr=''):
    return '<w:r>%s<w:t xml:space="preserve">%s</w:t></w:r>' % (('<w:rPr>%s</w:rPr>' % rpr) if rpr else '', text)


def make_docx(path, body, header=None, comments=None, settings=True):
    doc = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
           '<w:document xmlns:w="%s" xmlns:wp="%s"><w:body>%s<w:sectPr/></w:body></w:document>') % (W, WP, body)
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr('[Content_Types].xml', CT)
        z.writestr('_rels/.rels', RELS)
        z.writestr('word/document.xml', doc)
        if header:
            z.writestr('word/header1.xml', '<w:hdr xmlns:w="%s"><w:p>%s</w:p></w:hdr>' % (W, r(header)))
        if comments:
            z.writestr('word/comments.xml', '<w:comments xmlns:w="%s">%s</w:comments>' % (W, ''.join(
                '<w:comment w:id="%s" w:author="%s" w:date="2026-10-14T10:00:00Z"><w:p>%s</w:p></w:comment>'
                % (cid, au, r(tx)) for cid, au, tx in comments)))
        if settings:
            z.writestr('word/settings.xml', '<w:settings xmlns:w="%s"><w:trackRevisions/></w:settings>' % W)


BODY = (
    # 0: tracked replacement inside one paragraph, plus a comment range
    '<w:p>' + r('התשלום ישולם בתוך ') +
    '<w:del w:id="1" w:author="a"><w:r><w:delText>30</w:delText></w:r></w:del>'
    '<w:ins w:id="2" w:author="a">' + r('60') + '</w:ins>' +
    '<w:commentRangeStart w:id="7"/>' + r(' יום מתום החודש') + '<w:commentRangeEnd w:id="7"/>' + '</w:p>'
    # 1: moved text
    '<w:p><w:moveFrom w:id="3" w:author="a">' + r('סעיף שהועבר') + '</w:moveFrom></w:p>'
    '<w:p><w:moveTo w:id="4" w:author="a">' + r('סעיף שהועבר') + '</w:moveTo></w:p>'
    # 2: hidden text, all kinds
    '<w:p>' + r('גלוי. ') + r('מוסתר א', '<w:vanish/>') + r('מוסתר ב', '<w:color w:val="FEFEFE"/>') +
    r('מוסתר ג', '<w:sz w:val="6"/>') + r('מוסתר ד', '<w:webHidden/>') + r('גלוי', '<w:vanish w:val="0"/>') + '</w:p>'
    # 3: paragraph that holds a text box with its own paragraph
    '<w:p>' + r('לפני התיבה ') + '<w:r><w:drawing><wp:inline><w:txbxContent><w:p>' + r('בתוך התיבה') +
    '</w:p></w:txbxContent></wp:inline></w:drawing></w:r>' + r('אחרי התיבה') + '</w:p>'
)


def test_accept_reject_and_hidden(tmp_path):
    p = tmp_path / 'resp.docx'
    make_docx(p, BODY, header='כותרת עליונה', comments=[('7', 'עורכת הדין', 'ביקשתם 30 יום')])
    d = extract(str(p))
    paras = d['parts']['word/document.xml']
    p0 = paras[0]
    assert p0['text_accept_all'] == 'התשלום ישולם בתוך 60 יום מתום החודש'
    assert p0['text_reject_all'] == 'התשלום ישולם בתוך 30 יום מתום החודש'
    assert p0['changed'] is True
    moved = [x for x in paras if 'שהועבר' in (x['text_accept_all'] + x['text_reject_all'])]
    assert [x['text_accept_all'] for x in moved] == ['', 'סעיף שהועבר']
    assert [x['text_reject_all'] for x in moved] == ['סעיף שהועבר', '']
    hid = next(x for x in paras if x['text_accept_all'].startswith('גלוי.'))
    hows = sorted(h['how'] for h in hid['hidden'])
    assert hows == ['color', 'font_size', 'vanish', 'webHidden']
    assert 'מוסתר א' in hid['text_accept_all']  # הטקסט נשאר בנוסח; ההסתרה מסומנת לצדו
    assert d['hidden_total'] == 4
    assert d['tracked']['ins'] == 1 and d['tracked']['del'] == 1 and d['tracked']['moveFrom'] == 1
    assert d['track_revisions_on'] is True
    # comments with anchored text
    c = d['comments'][0]
    assert c['author'] == 'עורכת הדין' and c['text'] == 'ביקשתם 30 יום'
    assert c['anchored_text'] == 'יום מתום החודש'
    # header part is extracted too
    assert d['parts']['word/header1.xml'][0]['text_accept_all'] == 'כותרת עליונה'


def test_textbox_paragraph_counted_once(tmp_path):
    p = tmp_path / 'tb.docx'
    make_docx(p, BODY)
    d = extract(str(p))
    txt = body_text(d)
    assert txt.count('בתוך התיבה') == 1
    outer = next(x for x in d['parts']['word/document.xml'] if x['text_accept_all'].startswith('לפני התיבה'))
    assert 'בתוך התיבה' not in outer['text_accept_all']
    inner = next(x for x in d['parts']['word/document.xml'] if x['text_accept_all'] == 'בתוך התיבה')
    assert inner.get('in_textbox') is True


def test_reject_all_equals_received(tmp_path):
    recv = tmp_path / 'recv.docx'
    resp = tmp_path / 'resp.docx'
    make_docx(recv, '<w:p>' + r('התשלום ישולם בתוך 30 יום מתום החודש') + '</w:p>')
    make_docx(resp, BODY.split('<w:p><w:moveFrom')[0])
    same, diffs = reject_all_equals(extract(str(resp)), extract(str(recv)))
    assert same and diffs == []
    # שינוי שלא סומן במעקב: "דחה הכול" כבר אינו שווה לטיוטה שהתקבלה
    make_docx(resp, '<w:p>' + r('התשלום ישולם בתוך 45 יום מתום החודש') + '</w:p>')
    same, diffs = reject_all_equals(extract(str(resp)), extract(str(recv)))
    assert not same and diffs == [0]


def test_cli_writes_corpus(tmp_path):
    p = tmp_path / 'a.docx'
    make_docx(p, BODY)
    out = tmp_path / 'corpus.json'
    assert main(['--out', str(out), str(p)]) == 0
    data = json.loads(out.read_text(encoding='utf-8'))
    assert data[0]['file'] == 'a.docx' and 'word/document.xml' in data[0]['parts']


def test_cli_never_overwrites_an_input_document(tmp_path):
    """רגרסיה (סבב 4, קריטי): argv קצר דרס את ההסכם של הלקוח ב-JSON. עכשיו אין פלט בלי --out מפורש,
    ו---out שהוא קובץ קלט, מסמך קיים או נתיב בתיקיית "מהצד-שכנגד" נדחה, והקלט נשאר בייט לבייט."""
    from common.cli import OutputRefused
    from risk.extract_corpus import run
    p = tmp_path / 'a.docx'
    make_docx(p, BODY)
    before = p.read_bytes()
    # הצורה הישנה: <out> <doc>. ההסכם אינו נדרס (argparse דורש --out ויוצא)
    with pytest.raises(SystemExit):
        main([str(p)])
    with pytest.raises(SystemExit):
        main(['extract_corpus.py', str(p)])
    with pytest.raises(OutputRefused):
        main(['--out', str(p), str(p)])
    with pytest.raises(OutputRefused):
        main(['--out', str(tmp_path / 'x.json'), str(p), '--out', str(p)])
    src = tmp_path / 'מהצד-שכנגד'
    src.mkdir()
    with pytest.raises(OutputRefused):
        main(['--out', str(src / 'corpus.json'), str(p)])
    with pytest.raises(OutputRefused):
        main(['--out', str(tmp_path / 'corpus.docx'), str(p)])   # סיומת שאינה json
    assert run(main, ['--out', str(p), str(p)]) == 2
    assert p.read_bytes() == before
    assert not (src / 'corpus.json').exists()


def test_round2_corpus_fixture_reject_all_matches():
    """הקורפוס של סבב 2 (C1ב): "דחה הכול" של התגובה שלנו שווה לטיוטה שהתקבלה, 26 פסקאות."""
    data = json.loads((FX / 'c1b_corpus.json').read_text(encoding='utf-8'))
    same, diffs = reject_all_equals(data[1], data[0])
    assert same, diffs
