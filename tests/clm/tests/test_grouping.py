from clm import grouping


def d(i, file, kind, cp="", date=None, rel=None):
    return {"id": i, "file": file, "doc_kind": kind, "counterparty": cp, "date": date,
            "relation": rel or {"kind": None, "parent_hint": None}}


def test_versions_group_and_base_template_joins_same_folder():
    docs = [
        d("t", "03 מיקור חוץ/הסכם מיקור חוץ.docx", "template"),
        d("v1", "03 מיקור חוץ/הסכם מיקור חוץ - הערות ספק.docx", "negotiation_version", date="2026-05-01"),
        d("v2", "03 מיקור חוץ/הסכם מיקור חוץ - הערות ספק מלא2.docx", "negotiation_version", date="2026-06-01"),
        d("x", "05 דוגמאות/הסכם מיקור חוץ.docx", "template"),
    ]
    g = grouping.group(docs)
    assert len(g["groups"]) == 1
    assert g["groups"][0]["doc_ids"] == ["t", "v1", "v2"] and g["groups"][0]["head_id"] == "v2"
    assert docs[0].get("base_version") is True and not docs[3].get("base_version")


def test_different_counterparties_do_not_merge():
    docs = [d("a", "r/Reseller Agreement.docx", "negotiation_version", cp="Babcom"),
            d("b", "r/Reseller Agreement.docx", "negotiation_version", cp="Matrix Ltd")]
    assert len(grouping.group(docs)["groups"]) == 2


def test_two_signed_same_topic_not_merged_and_flagged():
    docs = [d("a", "x/הסכם שירותים - חתום.docx", "signed", cp="ספק בע\"מ"),
            d("b", "x/הסכם שירותים - חתום.pdf", "signed", cp="ספק")]
    g = grouping.group(docs)
    assert len(g["groups"]) == 2
    assert g["review"][0]["kind"] == "ambiguous_group"


def test_signed_is_head_even_if_older():
    docs = [d("s", "x/הסכם ענן - חתום.docx", "signed", cp="ענן", date="2025-01-01"),
            d("n", "x/הסכם ענן - הערות.docx", "negotiation_version", cp="ענן", date="2026-01-01")]
    assert grouping.group(docs)["groups"][0]["head_id"] == "s"


def test_children_link_to_single_parent_or_become_orphans():
    docs = [d("m", "x/הסכם מסגרת שירותים - חתום.docx", "signed", cp="ספקטרה בע\"מ"),
            d("o", "x/הזמנת עבודה 1.docx", "order", cp="ספקטרה", rel={"kind": "order", "parent_hint": "הסכם מסגרת שירותים"}),
            d("z", "x/תיקון 2.docx", "amendment", cp="אחר בע\"מ", rel={"kind": "amendment", "parent_hint": ""})]
    g = grouping.group(docs)
    assert g["children"] == {"o": 0}
    assert any(r["kind"] == "orphan" for r in g["review"])
    assert any(gr["head_id"] == "z" for gr in g["groups"])


def test_topic_key_strips_version_noise():
    assert grouping.topic_key("x/הסכם מיקור חוץ - הערות ספק מלא2.docx") == "הסכם מיקור חוץ"
    assert grouping.topic_key("x/Babcom Reseller Agreement(9072101.1) (redline) 10-12-2025.docx") == "babcom reseller agreement"


def test_two_orders_same_counterparty_without_framework_stay_orphans():
    docs = [d("o1", "x/הזמנת עבודה 1.docx", "order", cp="ספקטרה"),
            d("o2", "x/הזמנת עבודה 2.docx", "order", cp="ספקטרה")]
    g = grouping.group(docs)
    assert g["children"] == {}
    assert [r["kind"] for r in g["review"]] == ["orphan", "orphan"]
    assert len(g["groups"]) == 2
    assert sorted(gr["doc_ids"][0] for gr in g["groups"]) == ["o1", "o2"]


def test_template_with_empty_counterparty_joins_versions_with_counterparty():
    docs = [d("t", "f/הסכם שירותים.docx", "template"),
            d("v", "f/הסכם שירותים - הערות ספק.docx", "negotiation_version", cp="ספק בע\"מ", date="2026-05-01")]
    g = grouping.group(docs)
    assert len(g["groups"]) == 1
    assert g["groups"][0]["doc_ids"] == ["t", "v"]
    assert docs[0].get("base_version") is True


def test_template_matching_two_counterparties_is_not_joined_and_flagged():
    docs = [d("t", "r/Reseller Agreement.docx", "template"),
            d("a", "r/Reseller Agreement.docx", "negotiation_version", cp="Babcom"),
            d("b", "r/Reseller Agreement.docx", "negotiation_version", cp="Matrix Ltd")]
    g = grouping.group(docs)
    assert not docs[0].get("base_version")
    assert all("t" not in gr["doc_ids"] for gr in g["groups"])
    assert [r["kind"] for r in g["review"]] == ["ambiguous_template"]


def test_order_with_contradicting_hint_becomes_orphan():
    docs = [d("m", "x/הסכם מסגרת שירותים - חתום.docx", "signed", cp="ספקטרה"),
            d("o", "x/הזמנת עבודה 1.docx", "order", cp="ספקטרה", rel={"kind": "order", "parent_hint": "הסכם תחזוקה"})]
    g = grouping.group(docs)
    assert g["children"] == {}
    assert any(r["kind"] == "orphan" for r in g["review"])
    assert any(gr["doc_ids"] == ["o"] for gr in g["groups"])


def test_norm_cp_treats_hebrew_gershayim_and_quote_alike():
    assert grouping.norm_cp("ספק בע״מ") == grouping.norm_cp('ספק בע"מ') == "ספק"


DATAHAR_FILE = "הסכמים/הסכם שירותי אירוח ענן מנוהל - דאטה-הר - חתום 10.04.2022.docx"
DATAHAR_CP = 'דאטה-הר אירוח מנוהל בע"מ'
DATAHAR_HINT = 'הסכם למתן שירותי אירוח ענן מנוהל מיום 10.04.2022 בין מדיקס לדאטה-הר אירוח מנוהל בע"מ'


def _datahar(hint, signed_date="2022-04-10"):
    parent = d("p", DATAHAR_FILE, "signed", cp=DATAHAR_CP, date=signed_date)
    parent["signed_date"] = signed_date
    child = d("a", "הסכמים/תיקון 1 דאטה-הר.docx", "amendment", cp=DATAHAR_CP,
              rel={"kind": "amendment", "parent_hint": hint})
    return grouping.group([parent, child])


def test_real_datahar_hint_with_extra_word_attaches():
    g = _datahar(DATAHAR_HINT)
    assert g["children"] == {"a": 0}
    assert not any(r["kind"] == "orphan" for r in g["review"])


def test_hint_naming_a_different_agreement_same_counterparty_still_orphans():
    g = _datahar("הסכם תחזוקה ותמיכה מיום 01.01.2020 בין מדיקס לדאטה-הר אירוח מנוהל בע\"מ")
    assert g["children"] == {}
    assert any(r["kind"] == "orphan" for r in g["review"])


def test_date_only_hint_attaches():
    assert _datahar("ההסכם מיום 10.4.2022")["children"] == {"a": 0}
    assert _datahar("ההסכם מיום 10.04.2022")["children"] == {"a": 0}


def test_wrong_date_only_hint_orphans():
    assert _datahar("ההסכם מיום 11.04.2022")["children"] == {}


def test_signed_date_falls_back_to_signed_head_date():
    parent = d("p", DATAHAR_FILE, "signed", cp=DATAHAR_CP, date="2022-04-10")
    child = d("a", "הסכמים/תיקון.docx", "amendment", cp=DATAHAR_CP, rel={"kind": "amendment", "parent_hint": "מיום 10.04.2022"})
    assert grouping.group([parent, child])["children"] == {"a": 0}


def test_same_signed_date_but_hint_names_a_different_agreement_orphans():
    g = _datahar('הסכם עיבוד מידע אישי מיום 10.04.2022 בין מדיקס לדאטה-הר אירוח מנוהל בע"מ')
    assert g["children"] == {}
    assert any(r["kind"] == "orphan" for r in g["review"])


def test_topic_tokens_supplied_by_counterparty_name_do_not_attach_a_foreign_dated_hint():
    parent = d("p", "הסכמים/הסכם דאטה-הר - חתום.docx", "signed", cp=DATAHAR_CP, date="2022-04-10")
    parent["signed_date"] = "2022-04-10"
    child = d("a", "הסכמים/תיקון.docx", "amendment", cp=DATAHAR_CP, rel={
        "kind": "amendment", "parent_hint": "הסכם תחזוקה בין מדיקס ובין דאטה-הר מיום 01.01.2019"})
    g = grouping.group([parent, child])
    assert g["children"] == {} and any(r["kind"] == "orphan" for r in g["review"])
    child["relation"]["parent_hint"] = "הסכם תחזוקה בין מדיקס ובין דאטה-הר"
    assert grouping.group([parent, child])["children"] == {}


def test_foreign_date_contradicts_even_when_most_topic_tokens_match():
    g = _datahar("הסכם למתן שירותי אירוח ענן מנוהל מיום 01.01.2019")
    assert g["children"] == {}
    g2 = _datahar("הסכם למתן שירותי אירוח ענן מנוהל מיום 10.4.2022")
    assert g2["children"] == {"a": 0}


# ---- סבב 3: כללי התאמה אחידים. יתום הוא הכישלון הבטוח, שיוך שגוי הוא המסוכן ----
COMPANY = 'מדיקס שירותי בריאות דיגיטליים בע"מ'


def _frameworks(*specs):
    docs = []
    for i, (file, signed, start) in enumerate(specs):
        p = d("p%d" % i, file, "signed", cp=DATAHAR_CP, date=signed)
        p["signed_date"], p["start_date"] = signed, start
        docs.append(p)
    return docs


CLOUD = ("הסכמים/הסכם שירותי אירוח ענן מנוהל - דאטה-הר - חתום 10.04.2022.docx", "2022-04-10", "2022-05-01")
GENERIC = ("הסכמים/הסכם שירותים - דאטה-הר - חתום.docx", "2023-01-01", "2023-02-01")


def _attach(hint, *specs, own_signed=None):
    child = d("a", "הסכמים/תיקון.docx", "amendment", cp=DATAHAR_CP, rel={"kind": "amendment", "parent_hint": hint})
    child["signed_date"] = own_signed
    g = grouping.group(_frameworks(*(specs or (CLOUD,))) + [child], company=COMPANY)
    return g["children"].get("a"), [r["kind"] for r in g["review"]]


def test_round3_orphans_probes_a_c_d_o():
    assert _attach("הסכם עיבוד מידע אישי מיום 10.04.2022 בין מדיקס לדאטה-הר")[0] is None
    assert _attach("הסכם שירותים מקצועיים לפיתוח מיום 01.01.2019", GENERIC)[0] is None
    assert _attach("הסכם תחזוקה בין מדיקס ובין דאטה-הר מיום 01.01.2019",
                   ("הסכמים/הסכם דאטה-הר - חתום.docx", "2022-04-10", None))[0] is None
    idx, kinds = _attach("הסכם סודיות מיום 10.04.2022")
    assert idx is None and "orphan" in kinds


def test_round3_attaches_probes_k_l_n_m_p_and_real_datahar():
    assert _attach(DATAHAR_HINT)[0] == 0
    assert _attach("הסכם למתן שירותי אירוח ענן מנוהל מיום 10.04.2022, כפי שתוקן ביום 01.01.2024")[0] == 0
    assert _attach("התיקון מיום 23.03.2025 להסכם מיום 10.04.2022")[0] == 0
    assert _attach("התיקון מיום 23.03.2025 להסכם מיום 10.04.2022", own_signed="2025-03-23")[0] == 0
    assert _attach("ההסכם מיום 10.4.2022 בין מדיקס לדאטה-הר")[0] == 0
    assert _attach("הסכם שירותי אירוח ענן מנוהל מיום 1.5.2022")[0] == 0
    assert _attach("הסכם למתן שירותי אירוח ענן מנוהל מיום 1.5.2022")[0] == 0
    assert _attach("הסכם למתן שירותי אירוח ענן מנוהל")[0] == 0


def test_round3_two_frameworks_pick_by_topic_and_date_and_orphan_when_tied():
    assert _attach("הסכם למתן שירותי אירוח ענן מנוהל מיום 10.04.2022", CLOUD, GENERIC)[0] == 0
    assert _attach("הסכם השירותים מיום 1.1.2023", CLOUD, GENERIC)[0] == 1
    same_day = ("הסכמים/הסכם תחזוקה - דאטה-הר - חתום.docx", "2022-04-10", None)
    idx, kinds = _attach("ההסכם מיום 10.04.2022", CLOUD, same_day)
    assert idx is None and "orphan" in kinds


def test_round3_orphan_is_default_without_any_matching_evidence():
    assert _attach("ההסכם הקודם")[0] is None
    assert _attach("")[0] == 0
    assert _attach("", CLOUD, GENERIC)[0] is None


# ---- סבב 4: שמות החברה והצד שכנגד אינם רעש בנושא ההורה; בהינט רק הצירוף המלא והמילה הראשונה ----
import pytest  # noqa: E402

ROUND4_ORPHAN = [
    ("A", "הסכם עיבוד מידע אישי מיום 10.04.2022 בין מדיקס לדאטה-הר", (CLOUD,)),
    ("C", "הסכם שירותים מקצועיים לפיתוח מיום 01.01.2019", (GENERIC,)),
    ("D", "הסכם תחזוקה בין מדיקס ובין דאטה-הר מיום 01.01.2019", (("הסכמים/הסכם דאטה-הר - חתום.docx", "2022-04-10", None),)),
    ("O", "הסכם סודיות מיום 10.04.2022", (CLOUD,)),
    ("S1", "הסכם גיבוי ענן", (CLOUD,)),
    ("S2", "הסכם שירותי בריאות מיום 10.04.2022", (CLOUD,)),
    ("S3", "הסכם אירוח מיום 10.04.2022", (CLOUD,)),
]

ROUND4_ATTACH = [
    ("datahar", DATAHAR_HINT, (CLOUD,), 0),
    ("K", "הסכם למתן שירותי אירוח ענן מנוהל מיום 10.04.2022, כפי שתוקן ביום 01.01.2024", (CLOUD,), 0),
    ("L", "התיקון מיום 23.03.2025 להסכם מיום 10.04.2022", (CLOUD,), 0),
    ("M", "הסכם שירותי אירוח ענן מנוהל מיום 1.5.2022", (CLOUD,), 0),
    ("M2", "הסכם למתן שירותי אירוח ענן מנוהל מיום 1.5.2022", (CLOUD,), 0),
    ("N", "ההסכם מיום 10.4.2022 בין מדיקס לדאטה-הר", (CLOUD,), 0),
    ("E", "הסכם למתן שירותי אירוח ענן מנוהל מיום 10.04.2022", (CLOUD, GENERIC), 0),
    ("F", "הסכם השירותים מיום 1.1.2023", (CLOUD, GENERIC), 1),
]


@pytest.mark.parametrize("name,hint,specs", ROUND4_ORPHAN, ids=[c[0] for c in ROUND4_ORPHAN])
def test_round4_probe_orphans(name, hint, specs):
    idx, kinds = _attach(hint, *specs)
    assert idx is None and "orphan" in kinds


@pytest.mark.parametrize("name,hint,specs,want", ROUND4_ATTACH, ids=[c[0] for c in ROUND4_ATTACH])
def test_round4_probe_attaches(name, hint, specs, want):
    idx, kinds = _attach(hint, *specs)
    assert idx == want and "orphan" not in kinds


def test_round4_two_same_day_frameworks_with_date_only_hint_orphan():
    same_day = ("הסכמים/הסכם תחזוקה - דאטה-הר - חתום.docx", "2022-04-10", None)
    idx, kinds = _attach("ההסכם מיום 10.04.2022 בין מדיקס לדאטה-הר", CLOUD, same_day)
    assert idx is None and "orphan" in kinds


def test_round4_parent_topic_keeps_name_words():
    """כלל A: אסימוני התוכן של הנושא הם אסימוני topic_key בלי מילות קישור בלבד."""
    assert grouping._topic_content(grouping.topic_key(CLOUD[0])) == ["שירותי", "אירוח", "ענן", "מנוהל"]


def test_round4_single_token_topic_needs_the_topic_phrase():
    """כלל B: נושא עם אסימון תוכן אחד ("שירותים") מתאים רק כשהנושא עצמו מופיע בהינט."""
    assert _attach("השירותים", GENERIC)[0] is None
    assert _attach("הסכם השירותים", GENERIC)[0] == 0


def test_round4_hint_names_stripped_as_full_phrase_and_first_word_only():
    """כלל C: מהינט מוסרים הצירוף המלא של כל שם, והמילה הראשונה של השם (גם עם אות שימוש). לא מילים אחרות."""
    full = 'ההסכם מיום 10.04.2022 בין מדיקס שירותי בריאות דיגיטליים בע"מ לבין דאטה-הר אירוח מנוהל בע״מ'
    assert _attach(full)[0] == 0
    assert _attach("ההסכם מיום 10.04.2022 בין המדיקס ודאטה-הר")[0] == 0
    hint = grouping._hint_info({"signed_date": None, "counterparty": DATAHAR_CP,
                                "relation": {"parent_hint": "הסכם שירותי בריאות ואירוח בין מדיקס לדאטה-הר"}}, COMPANY)
    assert hint["content"] == ["שירותי", "בריאות", "ואירוח"]


def test_round4_hint_content_computed_once_per_child(monkeypatch):
    """כלל D: אסימוני התוכן של ההינט מחושבים פעם אחת לכל מסמך משנה, לא לכל מועמד."""
    calls = []
    real = grouping._hint_info
    monkeypatch.setattr(grouping, "_hint_info", lambda child, company: calls.append(1) or real(child, company))
    _attach("הסכם השירותים מיום 1.1.2023", CLOUD, GENERIC)
    assert len(calls) == 1


def test_round4_amendment_signed_same_day_as_framework_with_date_only_hint_orphans():
    """כלל E: תאריך החתימה של התיקון עצמו אינו תאריך הינט, גם כשהוא זהה לתאריך המסגרת."""
    idx, kinds = _attach("ההסכם מיום 10.04.2022", own_signed="2022-04-10")
    assert idx is None and "orphan" in kinds


# ---- סבב 5: נושא שכולו שם או מילה כללית אינו התאמת נושא; ההתאמות רצות על ההינט בלי השמות ----
ALTIVO_CP = "Altivo Cloud Services Ireland Ltd."
ALTIVO = ("הסכמים/Altivo Cloud - Online Customer Agreement and Medix Supplemental Addendum - executed 04.11.2025.docx",
          "2025-11-04", None, ALTIVO_CP)
BARE = ("הסכמים/הסכם - דאטה-הר - חתום 10.04.2022.docx", "2022-04-10", "2022-05-01")
CPONLY = ("הסכמים/דאטה-הר - חתום 10.04.2022.docx", "2022-04-10", "2022-05-01")
CHOZE = ("הסכמים/חוזה - דאטה-הר - חתום.docx", "2022-04-10", "2022-05-01")
GEN1 = ("הסכמים/הסכם שירותים - דאטה-הר - חתום.docx", "2022-04-10", "2022-05-01")
COTOPIC = ("הסכמים/שירותי בריאות - דאטה-הר - חתום.docx", "2022-04-10", "2022-05-01")
U1_CP = 'אירוח ענן בע"מ'
U1_FW = ("הסכמים/הסכם שירותי גיבוי - אירוח ענן - חתום.docx", "2022-04-10", None, U1_CP)


def _attach5(hint, specs, cp=DATAHAR_CP, company=COMPANY, own_signed=None):
    docs = []
    for i, spec in enumerate(specs):
        file, signed, start = spec[:3]
        p = d("p%d" % i, file, "signed", cp=spec[3] if len(spec) > 3 else DATAHAR_CP, date=signed)
        p["signed_date"], p["start_date"] = signed, start
        docs.append(p)
    child = d("a", "הסכמים/תיקון.docx", "amendment", cp=cp, rel={"kind": "amendment", "parent_hint": hint})
    child["signed_date"] = own_signed
    g = grouping.group(docs + [child], company=company)
    return g["children"].get("a"), [r["kind"] for r in g["review"]]


ROUND5_ORPHAN = [
    ("Altivo-support", "Altivo Cloud Enterprise Support Agreement", (ALTIVO,), ALTIVO_CP, None),
    ("Altivo-dpa", "Data Processing Agreement with Altivo Cloud Services Ireland Ltd", (ALTIVO,), ALTIVO_CP, None),
    ("T1", "הסכם תחזוקה ותמיכה", (BARE,), DATAHAR_CP, None),
    ("T1c", "הסכם תחזוקה מיום 10.04.2022", (BARE,), DATAHAR_CP, None),
    ("T2", "הסכם תחזוקה בין מדיקס לדאטה-הר", (CPONLY,), DATAHAR_CP, None),
    ("T2b", "הסכם סודיות עם דאטה-הר מיום 10.04.2022", (CPONLY,), DATAHAR_CP, None),
    ("T3", "חוזה תחזוקה", (CHOZE,), DATAHAR_CP, None),
    ("T4", 'הסכם תחזוקה בין מדיקס שירותי בריאות דיגיטליים בע"מ לבין דאטה-הר', (COTOPIC,), DATAHAR_CP, None),
    ("T5", "הסכם שירותים מקצועיים לפיתוח תוכנה", (GEN1,), DATAHAR_CP, None),
    ("U1", "הסכם אירוח מיום 10.04.2022", (U1_FW,), U1_CP, None),
    ("S4", "הסכם שירותי אירוח אתרים", (CLOUD,), DATAHAR_CP, None),
    ("S7", "התיקון מיום 23.03.2025", (CLOUD,), DATAHAR_CP, "2025-03-23"),
    ("S8", "הסכם סודיות מיום 1.5.2022", (CLOUD,), DATAHAR_CP, None),
]


@pytest.mark.parametrize("name,hint,specs,cp,own", ROUND5_ORPHAN, ids=[c[0] for c in ROUND5_ORPHAN])
def test_round5_probe_orphans(name, hint, specs, cp, own):
    idx, kinds = _attach5(hint, specs, cp=cp, own_signed=own)
    assert idx is None and "orphan" in kinds


def test_round5_attaches_and_picks():
    assert _attach5(DATAHAR_HINT, (CLOUD,), company="")[0] == 0          # S6: בלי שם חברה
    assert _attach5("הסכם שירותים", (CLOUD, GENERIC))[0] == 1             # S5
    assert _attach5("הסכם השירותים מיום 1.1.2023", (CLOUD, GENERIC))[0] == 1  # F
    assert _attach5("הסכם השירותים", (GEN1,))[0] == 0                     # T6


def test_round5_topic_content_strips_names_and_generic_nouns():
    """כלל 1-2: נושא שכולו שם הצד שכנגד או מילה כללית אינו משאיר אסימוני תוכן."""
    names = grouping._name_noise(COMPANY, DATAHAR_CP)
    assert grouping._topic_content(grouping.topic_key(CPONLY[0]), names) == []
    assert grouping._topic_content(grouping.topic_key(CHOZE[0]), names) == []
    assert grouping._topic_content(grouping.topic_key(ALTIVO[0]), grouping._name_noise(ALTIVO_CP)) == ["cloud"]
    assert grouping._topic_content(grouping.topic_key(CLOUD[0]), names) == ["שירותי", "אירוח", "ענן", "מנוהל"]


def test_round5_first_distinctive_word_skips_stop_words():
    assert grouping._name_phrases('חברת החשמל לישראל בע"מ')[1] == ["החשמל"]
    assert grouping._name_phrases("The Company Acme Ltd")[1] == ["acme"]


def test_round5_date_only_needs_more_than_a_lone_first_name_word():
    """כלל 4: הינט שנותר בלי תוכן רק כי הוסרה ממנו מילה ראשונה יחידה של שם אינו התאמת תאריך בלבד."""
    assert _attach5("ההסכם מיום 10.4.2022 עם מדיקס", (CLOUD,))[0] is None
    assert _attach5("ההסכם מיום 10.4.2022 בין מדיקס לדאטה-הר", (CLOUD,))[0] == 0
    assert _attach5("ההסכם מיום 10.4.2022 בין דאטה-הר אירוח מנוהל", (CLOUD,))[0] == 0
