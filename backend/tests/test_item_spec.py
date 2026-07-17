"""A.3: the item pipeline — content is code, this is its type checker.

Every lint rule gets a test that proves it FIRES. A linter whose rules are never
exercised is a linter that quietly stops working, and the whole premise of this
phase is that bad content should fail like bad Python.

The gradeability gate is the rule that matters most: an item the verification
engine cannot grade must never reach a student, because B.2 would store
`correct = null` forever and the item would silently teach nobody.
"""

import pathlib

import pytest

from app.ids import ChapterId, InvalidChapterId
from app.ingest.item_spec import (
    ITEM_NAMESPACE,
    Item,
    ItemError,
    ItemSet,
    canonical_response,
    check_gradeable,
    coverage,
    lint,
    load,
    parse,
)
from app.ingest.kc_graph import load as load_kc

ROOT = pathlib.Path(__file__).resolve().parents[2]
ITEMS = ROOT / "content" / "items" / "phy_mechanics.yaml"
KC = ROOT / "content" / "kc" / "phy_mechanics.yaml"

KC_IDS = {k.id for k in load_kc(KC).kcs}


def _item(slug="a.b.q001", kc="phy.mech.free_fall", stem="Find v.",
          answer=None, source="src", hints=()):
    return Item(slug=slug, kc=kc, stem=stem,
                answer=answer if answer is not None else {"value": 1.0, "unit": "m"},
                source=source, hints=tuple(hints))


def _set(items, chapter="PHY::mechanics::11", subject="PHY"):
    return ItemSet(subject=subject, chapter=chapter, items=tuple(items))


# ---------------------------------------------------------------------------
# ChapterId — the identifier with no FK to protect it
# ---------------------------------------------------------------------------

def test_chapter_id_round_trips():
    cid = ChapterId.parse("PHY::mechanics::11")
    assert (cid.subject, cid.slug, cid.grade) == ("PHY", "mechanics", 11)
    assert str(cid) == "PHY::mechanics::11"


def test_chapter_id_matches_the_pre_existing_optics_string():
    # The convention was set by 'PHY::optics::12' before this type existed; the
    # grammar has to accept it or we've redefined the identifier under the RAG
    # corpus's feet.
    assert str(ChapterId.parse("PHY::optics::12")) == "PHY::optics::12"


@pytest.mark.parametrize("bad", [
    "Mechanics",              # the obvious mistake — matches zero chunks
    "PHY::mechanics",         # no grade
    "phy::mechanics::11",     # lowercase subject
    "PHY:mechanics:11",       # single colons
    "PHY::Mechanics::11",     # capitalised slug
    "PHY::mechanics::13",     # not a school grade
    "PHY::mechanics::11 ",    # trailing space — invisible, fatal
    "",
])
def test_chapter_id_rejects_malformed(bad):
    with pytest.raises(InvalidChapterId):
        ChapterId.parse(bad)


def test_chapter_id_is_orderable_and_hashable():
    a, b = ChapterId.parse("PHY::mechanics::11"), ChapterId.parse("PHY::optics::12")
    assert a < b and len({a, b, ChapterId.parse("PHY::mechanics::11")}) == 2


# ---------------------------------------------------------------------------
# parsing + banned keys
# ---------------------------------------------------------------------------

def test_parses_the_documented_shape():
    s = parse("""
subject: PHY
chapter: PHY::mechanics::11
items:
  - slug: phy.mech.free_fall.q001
    kc: phy.mech.free_fall
    stem: Drop a stone.
    answer: {value: 3.0, unit: s}
    source: NCERT
""")
    assert s.items[0].slug == "phy.mech.free_fall.q001"
    assert s.items[0].answer == {"value": 3.0, "unit": "s"}


@pytest.mark.parametrize("banned", ["difficulty", "rating", "id"])
def test_authoring_a_derived_field_is_rejected_not_ignored(banned):
    # An author who writes `difficulty: hard` deserves to be told it does
    # nothing, rather than have it silently dropped (ADR-012: Elo owns it).
    with pytest.raises(ItemError, match=banned):
        parse(f"""
subject: PHY
chapter: PHY::mechanics::11
items:
  - slug: a.b.q001
    kc: phy.mech.free_fall
    stem: x
    answer: {{value: 1}}
    source: s
    {banned}: 3
""")


@pytest.mark.parametrize("missing", ["slug", "kc", "stem", "answer", "source"])
def test_required_keys(missing):
    fields = {"slug": "a.b.q001", "kc": "phy.mech.free_fall", "stem": "x",
              "answer": "{value: 1}", "source": "s"}
    del fields[missing]
    body = "\n".join(f"    {k}: {v}" for k, v in fields.items())
    with pytest.raises(ItemError, match="missing required key"):
        parse(f"subject: PHY\nchapter: PHY::mechanics::11\nitems:\n  -\n{body}\n")


def test_answer_must_be_a_mapping():
    with pytest.raises(ItemError, match="must be a mapping"):
        parse("subject: PHY\nchapter: PHY::mechanics::11\nitems:\n"
              "  - slug: a.b.q001\n    kc: phy.mech.free_fall\n    stem: x\n"
              "    answer: '3 m'\n    source: s\n")


# ---------------------------------------------------------------------------
# the gradeability gate (ADR-016)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("answer, expected", [
    ({"value": 9.8, "unit": "m/s^2"}, "9.8 m/s^2"),
    ({"value": 42}, "42"),
    ({"choices": ["B"]}, "B"),
    ({"choices": ["A", "C", "D"]}, "A,C,D"),
])
def test_canonical_response(answer, expected):
    assert canonical_response(answer) == expected


@pytest.mark.parametrize("answer", [
    {"value": 2.0, "unit": "s"},
    {"value": 28.28, "unit": "m/s"},
    {"choices": ["B"]},
    {"choices": ["A", "C", "D"]},
    {"value": 42},
])
def test_gradeable_answers_pass(answer):
    check_gradeable(_item(answer=answer))


def test_symbolic_only_gold_is_rejected_until_sympy_lands():
    # GoldAnswerChecker returns INAPPLICABLE for expr-only (ADR-009). An item it
    # can't grade would store correct=null forever, so it must not enter the bank.
    with pytest.raises(ItemError, match="sympy|P5.0|cannot grade"):
        check_gradeable(_item(answer={"expr": "v**2/(2*g)"}))


def test_gold_with_no_answer_is_rejected():
    with pytest.raises(ItemError, match="neither .value. nor .choices."):
        check_gradeable(_item(answer={"note": "see solution"}))


def test_the_gate_asks_the_real_checker_not_a_reimplementation():
    # `{value: twenty}` survives the shape checks and yields a canonical response
    # ("twenty"), so only the REAL checker can reject it — it returns
    # INAPPLICABLE ("no number in response"). If this passes, the gate is wired to
    # GoldAnswerChecker rather than re-deriving what "gradeable" means.
    with pytest.raises(ItemError, match="cannot grade"):
        check_gradeable(_item(answer={"value": "twenty", "unit": "m"}))


def test_an_answer_key_with_no_usable_value_is_caught_before_the_checker():
    with pytest.raises(ItemError, match="neither .value. nor .choices."):
        check_gradeable(_item(answer={"value": None, "unit": "m"}))


def test_lint_reports_an_ungradeable_item_with_its_slug():
    bad = _item(slug="phy.mech.free_fall.q009", answer={"expr": "x**2"})
    with pytest.raises(ItemError, match="phy.mech.free_fall.q009"):
        lint(_set([bad]), KC_IDS)


# ---------------------------------------------------------------------------
# lint rules
# ---------------------------------------------------------------------------

def test_unknown_kc_is_rejected():
    with pytest.raises(ItemError, match="not in the KC graph"):
        lint(_set([_item(kc="phy.mech.does_not_exist")]), KC_IDS)


def test_duplicate_slug_is_rejected():
    a = _item(slug="phy.mech.free_fall.q001", stem="one")
    b = _item(slug="phy.mech.free_fall.q001", stem="two")
    with pytest.raises(ItemError, match="duplicate slug"):
        lint(_set([a, b]), KC_IDS)


@pytest.mark.parametrize("bad", ["Q001", "no_dots", "a..b", "phy.mech.q 1", "1.b"])
def test_malformed_slug_is_rejected(bad):
    with pytest.raises(ItemError, match="slug must be"):
        lint(_set([_item(slug=bad)]), KC_IDS)


def test_duplicate_stem_within_a_kc_is_rejected():
    # The loop would serve the same question twice and read the second attempt as
    # independent evidence of mastery.
    a = _item(slug="phy.mech.free_fall.q001", kc="phy.mech.free_fall", stem="Find v.")
    b = _item(slug="phy.mech.free_fall.q002", kc="phy.mech.free_fall", stem="Find v.")
    with pytest.raises(ItemError, match="duplicates"):
        lint(_set([a, b]), KC_IDS)


def test_duplicate_stem_detection_ignores_whitespace_reflow():
    a = _item(slug="phy.mech.free_fall.q001", stem="Find  v\n  now.")
    b = _item(slug="phy.mech.free_fall.q002", stem="Find v now.")
    with pytest.raises(ItemError, match="duplicates"):
        lint(_set([a, b]), KC_IDS)


def test_same_stem_under_different_kcs_is_allowed():
    # Legitimate: the same physical setup asked about two different concepts.
    a = _item(slug="phy.mech.free_fall.q001", kc="phy.mech.free_fall", stem="A ball falls.")
    b = _item(slug="phy.mech.newton_second.q001", kc="phy.mech.newton_second",
              stem="A ball falls.", answer={"value": 2.0, "unit": "s"})
    lint(_set([a, b]), KC_IDS)


def test_identical_content_under_two_slugs_is_rejected():
    # Would violate items.content_hash unique at insert; say so in our words.
    a = _item(slug="phy.mech.free_fall.q001", kc="phy.mech.free_fall", stem="Same.")
    b = _item(slug="phy.mech.free_fall.q002", kc="phy.mech.free_fall", stem="Same.")
    with pytest.raises(ItemError):
        lint(_set([a, b]), KC_IDS)


def test_empty_source_is_rejected():
    with pytest.raises(ItemError, match="source"):
        lint(_set([_item(source="  ")]), KC_IDS)


def test_empty_stem_is_rejected():
    with pytest.raises(ItemError, match="stem is empty"):
        lint(_set([_item(stem="   ")]), KC_IDS)


def test_chapter_must_match_the_kc_graphs_chapter():
    with pytest.raises(ItemError, match="KC graph"):
        lint(_set([_item()], chapter="PHY::optics::12"),
             KC_IDS, kc_chapter="PHY::mechanics::11")


def test_subject_must_agree_with_the_chapter():
    with pytest.raises(ItemError, match="disagrees"):
        lint(_set([_item()], subject="CHEM"), KC_IDS)


def test_lint_lists_every_problem_not_just_the_first():
    bad = [
        _item(slug="phy.mech.free_fall.q001", kc="phy.mech.nope"),
        _item(slug="phy.mech.free_fall.q002", source=""),
    ]
    with pytest.raises(ItemError) as e:
        lint(_set(bad), KC_IDS)
    msg = str(e.value)
    assert "nope" in msg and "source" in msg      # both, in one run


# ---------------------------------------------------------------------------
# determinism (ADR-015)
# ---------------------------------------------------------------------------

def test_item_uuid_is_derived_from_the_slug_and_is_stable():
    import uuid as _uuid
    item = _item(slug="phy.mech.free_fall.q001")
    assert item.uuid == _uuid.uuid5(ITEM_NAMESPACE, "phy.mech.free_fall.q001")
    assert item.uuid == _item(slug="phy.mech.free_fall.q001").uuid


def test_different_slugs_give_different_uuids():
    assert _item(slug="a.b.q001").uuid != _item(slug="a.b.q002").uuid


def test_uuid_survives_a_stem_edit_so_attempts_are_not_orphaned():
    # The reason slug exists (ADR-015): proofreading must not destroy identity.
    before = _item(slug="a.b.q001", stem="Find teh speed.")
    after = _item(slug="a.b.q001", stem="Find the speed.")
    assert before.uuid == after.uuid
    assert before.content_hash != after.content_hash    # but the change is visible


def test_content_hash_is_stable_and_ignores_reflow():
    a = _item(stem="A ball  is\n  dropped.")
    b = _item(stem="A ball is dropped.")
    assert a.content_hash == b.content_hash == a.content_hash


def test_content_hash_changes_with_the_answer():
    assert _item(answer={"value": 1.0}).content_hash != _item(answer={"value": 2.0}).content_hash


def test_content_hash_ignores_answer_key_order():
    a = _item(answer={"value": 1.0, "unit": "m"})
    b = _item(answer={"unit": "m", "value": 1.0})
    assert a.content_hash == b.content_hash


# ---------------------------------------------------------------------------
# coverage — the number that says whether B.2 can adapt
# ---------------------------------------------------------------------------

def test_coverage_counts_and_flags_thin_kcs():
    items = [_item(slug=f"phy.mech.free_fall.q{i:03d}", kc="phy.mech.free_fall",
                   stem=f"Q{i}") for i in range(6)]
    items.append(_item(slug="phy.mech.newton_second.q001", kc="phy.mech.newton_second"))
    cov = coverage(_set(items), KC_IDS)
    assert cov["items"] == 7
    assert cov["kcs_covered"] == 2
    assert cov["per_kc"]["phy.mech.free_fall"] == 6
    # 6 items = a ladder; 1 item = servable but not adaptable.
    assert "phy.mech.newton_second" in cov["thin"]
    assert "phy.mech.free_fall" not in cov["thin"]
    assert "phy.mech.torque" in cov["kcs_uncovered"]


# ---------------------------------------------------------------------------
# the real seed
# ---------------------------------------------------------------------------

def test_seed_item_file_lints_clean():
    items = load(ITEMS)
    kc = load_kc(KC)
    lint(items, {k.id for k in kc.kcs}, kc_chapter=kc.chapter)


def test_seed_items_are_all_gradeable_by_the_real_checker():
    for item in load(ITEMS).items:
        check_gradeable(item)


def test_seed_is_honest_about_being_a_format_seed_not_the_bank():
    # If this starts failing because someone curated the real ~300, delete it.
    cov = coverage(load(ITEMS), KC_IDS)
    assert cov["kcs_covered"] < cov["kcs_total"], "bank complete? update the docs + Status"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_check_passes_on_the_seed(capsys):
    from app.ingest.items import main
    assert main([str(ITEMS), "--kc", str(KC), "--check"]) == 0
    out = capsys.readouterr().out
    assert "Items:" in out and "KCs covered:" in out and "nothing written" in out


def test_cli_check_fails_with_exit_1_on_a_bad_item(tmp_path, capsys):
    from app.ingest.items import main
    spec = tmp_path / "bad.yaml"
    spec.write_text("""
subject: PHY
chapter: PHY::mechanics::11
items:
  - slug: phy.mech.free_fall.q001
    kc: phy.mech.imaginary
    stem: x
    answer: {value: 1, unit: m}
    source: s
""", encoding="utf-8")
    assert main([str(spec), "--kc", str(KC), "--check"]) == 1
    assert "not in the KC graph" in capsys.readouterr().err


def test_cli_fails_on_a_missing_file(tmp_path, capsys):
    from app.ingest.items import main
    assert main([str(tmp_path / "nope.yaml"), "--kc", str(KC), "--check"]) == 1
    assert "No such file" in capsys.readouterr().err
