"""A.2: the knowledge-graph spec — parsing, validation, ordering, metrics.

Postgres can enforce self-loops (CHECK) and existence (FK) but **cannot express
acyclicity**, so this module is the integrity boundary and these tests are what
guard it. Every validation rule gets a test that proves it *fires* — a validator
whose rules are never exercised is a validator that quietly stops working.

No DB: kc_graph.py is pure by design. The upsert in kc.py needs Postgres and is
covered by the fresh-DB apply, not here.
"""

import pathlib

import pytest

from app.ingest.kc_graph import (
    Chapter,
    GraphError,
    KC,
    find_cycle,
    graph_hash,
    load,
    metrics,
    parse,
    to_dot,
    topo_order,
    validate,
)

SEED = pathlib.Path(__file__).resolve().parents[2] / "content" / "kc" / "phy_mechanics.yaml"


def _chapter(kcs, subject="PHY", chapter="PHY::mechanics::11"):
    return Chapter(subject=subject, chapter=chapter, kcs=tuple(kcs))


def _kc(id_, name=None, prereqs=(), root=False):
    return KC(id=id_, name=name or id_, prereqs=tuple(prereqs), root=root)


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def test_parses_the_documented_shape():
    ch = parse("""
subject: PHY
chapter: PHY::mechanics::11
knowledge_components:
  - id: phy.mech.vectors
    name: Vectors
  - id: phy.mech.projectile
    name: Projectile Motion
    prereqs:
      - phy.mech.vectors
""")
    assert ch.subject == "PHY" and ch.chapter == "PHY::mechanics::11"
    assert [k.id for k in ch.kcs] == ["phy.mech.vectors", "phy.mech.projectile"]
    assert ch.kcs[1].prereqs == ("phy.mech.vectors",)
    assert ch.edges == (("phy.mech.vectors", "phy.mech.projectile"),)


def test_prereqs_are_optional():
    ch = parse("subject: PHY\nchapter: PHY::m::11\nknowledge_components:\n"
               "  - id: a.b\n    name: A\n")
    assert ch.kcs[0].prereqs == ()


@pytest.mark.parametrize("text, why", [
    ("[]", "top level is a list"),
    ("subject: PHY\nchapter: PHY::m::11\n", "no knowledge_components"),
    ("subject: PHY\nknowledge_components: []\n", "no chapter"),
    ("chapter: PHY::m::11\nknowledge_components: []\n", "no subject"),
    ("subject: PHY\nchapter: PHY::m::11\nknowledge_components: []\n", "empty list"),
    ("subject: PHY\nchapter: PHY::m::11\nknowledge_components:\n  - name: no id\n", "no id"),
    ("subject: PHY\nchapter: PHY::m::11\nknowledge_components:\n  - id: a.b\n", "no name"),
])
def test_parse_rejects_malformed_specs(text, why):
    with pytest.raises(GraphError):
        parse(text)


def test_parse_rejects_unparseable_yaml():
    with pytest.raises(GraphError, match="not parseable"):
        parse("subject: PHY\n  chapter: bad indent\n   - x\n")


# ---------------------------------------------------------------------------
# validation — each rule must actually fire
# ---------------------------------------------------------------------------

def test_self_loop_is_rejected():
    with pytest.raises(GraphError, match="self-loop"):
        validate(_chapter([_kc("a.b", prereqs=["a.b"])]))


def test_duplicate_edge_is_rejected():
    with pytest.raises(GraphError, match="duplicate prereq"):
        validate(_chapter([_kc("a.b"), _kc("a.c", prereqs=["a.b", "a.b"])]))


def test_duplicate_id_is_rejected():
    with pytest.raises(GraphError, match="duplicate id"):
        validate(_chapter([_kc("a.b"), _kc("a.b")]))


def test_unknown_prereq_is_rejected():
    with pytest.raises(GraphError, match="does not exist"):
        validate(_chapter([_kc("a.b", prereqs=["a.typo"])]))


@pytest.mark.parametrize("bad_id", ["A.B", "no_dots", "a..b", ".a.b", "a.b.", "a b.c", "1.b"])
def test_malformed_ids_are_rejected(bad_id):
    with pytest.raises(GraphError, match="dotted path"):
        validate(_chapter([_kc(bad_id)]))


def test_isolated_node_is_rejected_unless_marked_root():
    lonely = [_kc("a.b"), _kc("a.c"), _kc("a.d", prereqs=["a.c"])]
    with pytest.raises(GraphError, match="isolated"):
        validate(_chapter(lonely))
    # explicitly standalone is allowed
    ok = [_kc("a.b", root=True), _kc("a.c"), _kc("a.d", prereqs=["a.c"])]
    validate(_chapter(ok))


def test_a_root_with_dependents_is_not_isolated():
    # No prereqs but something depends on it — an ordinary root, no flag needed.
    validate(_chapter([_kc("a.b"), _kc("a.c", prereqs=["a.b"])]))


@pytest.mark.parametrize("subject", ["phy", "Phy", "PHY1", ""])
def test_subject_must_match_the_chunks_convention(subject):
    with pytest.raises(GraphError, match="subject"):
        validate(_chapter([_kc("a.b", root=True)], subject=subject))


@pytest.mark.parametrize("chapter", [
    "Mechanics",                 # the obvious mistake: human-readable, matches no chunk
    "PHY::mechanics",            # missing the number
    "phy::mechanics::11",        # lowercase subject
    "PHY:mechanics:11",          # single colons
])
def test_chapter_must_match_the_chunks_convention(chapter):
    # retrieval does `where chapter = $2` — an exact match. A KC whose chapter
    # string doesn't equal its chunks' retrieves NOTHING, silently.
    with pytest.raises(GraphError, match="chunks.chapter|byte-identical|PHY::mechanics::11"):
        validate(_chapter([_kc("a.b", root=True)], chapter=chapter))


# ---------------------------------------------------------------------------
# cycles — the check Postgres cannot do
# ---------------------------------------------------------------------------

def test_two_node_cycle_is_detected():
    cyc = _chapter([_kc("a.b", prereqs=["a.c"]), _kc("a.c", prereqs=["a.b"])])
    assert find_cycle(cyc) is not None
    with pytest.raises(GraphError, match="Detected cycle"):
        validate(cyc)


def test_three_node_cycle_is_detected():
    cyc = _chapter([
        _kc("a.projectile", "Projectile Motion", ["a.vectors"]),
        _kc("a.vectors", "Vectors", ["a.kinematics"]),
        _kc("a.kinematics", "Kinematics", ["a.projectile"]),
    ])
    with pytest.raises(GraphError) as e:
        validate(cyc)
    msg = str(e.value)
    assert "Ingest failed." in msg and "Detected cycle:" in msg
    # names, not just ids — the message is for a human fixing YAML
    assert "Projectile Motion" in msg and "Vectors" in msg and "Kinematics" in msg
    assert "↓ requires" in msg


def test_cycle_report_is_deterministic():
    cyc = _chapter([
        _kc("a.b", prereqs=["a.d"]), _kc("a.c", prereqs=["a.b"]),
        _kc("a.d", prereqs=["a.c"]),
    ])
    assert find_cycle(cyc) == find_cycle(cyc)


def test_cycle_path_starts_and_ends_on_the_same_node():
    cyc = _chapter([_kc("a.b", prereqs=["a.c"]), _kc("a.c", prereqs=["a.b"])])
    path = find_cycle(cyc)
    assert path[0] == path[-1] and len(path) >= 3


def test_a_diamond_is_not_a_cycle():
    # a -> b, a -> c, b -> d, c -> d. Two paths to d; perfectly legal.
    diamond = _chapter([
        _kc("a.a"), _kc("a.b", prereqs=["a.a"]), _kc("a.c", prereqs=["a.a"]),
        _kc("a.d", prereqs=["a.b", "a.c"]),
    ])
    assert find_cycle(diamond) is None
    validate(diamond)


def test_deep_chain_does_not_blow_the_stack():
    # 3000 deep: a recursive DFS dies here. "The validator crashed" is a worse
    # failure than "your graph has a cycle".
    kcs = [_kc("a.n0")] + [_kc(f"a.n{i}", prereqs=[f"a.n{i-1}"]) for i in range(1, 3000)]
    ch = _chapter(kcs)
    assert find_cycle(ch) is None
    assert len(topo_order(ch)) == 3000


def test_deep_cycle_is_still_found():
    kcs = [_kc("a.n0", prereqs=["a.n999"])]
    kcs += [_kc(f"a.n{i}", prereqs=[f"a.n{i-1}"]) for i in range(1, 1000)]
    assert find_cycle(_chapter(kcs)) is not None


# ---------------------------------------------------------------------------
# ordering
# ---------------------------------------------------------------------------

def test_topo_order_puts_prereqs_first():
    ch = _chapter([
        _kc("a.d", prereqs=["a.b", "a.c"]), _kc("a.b", prereqs=["a.a"]),
        _kc("a.c", prereqs=["a.a"]), _kc("a.a"),
    ])
    order = topo_order(ch)
    pos = {k: i for i, k in enumerate(order)}
    for prereq, postreq in ch.edges:
        assert pos[prereq] < pos[postreq], f"{prereq} must precede {postreq}"


def test_topo_order_is_deterministic_across_runs():
    ch = load(SEED)
    assert topo_order(ch) == topo_order(ch)


def test_topo_order_breaks_ties_by_file_order_not_id():
    # Two roots, declared z-then-a. A set- or id-sorted implementation would
    # emit a first; the file's order is what a reviewer reads, so it wins.
    ch = _chapter([_kc("a.zebra"), _kc("a.apple"), _kc("a.c", prereqs=["a.zebra", "a.apple"])])
    assert topo_order(ch) == ["a.zebra", "a.apple", "a.c"]


def test_topo_order_covers_every_node():
    ch = load(SEED)
    assert sorted(topo_order(ch)) == sorted(k.id for k in ch.kcs)


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

def test_metrics_on_a_known_graph():
    #  a -> b -> c   and a lone marked root d
    ch = _chapter([
        _kc("a.a"), _kc("a.b", prereqs=["a.a"]), _kc("a.c", prereqs=["a.b"]),
        _kc("a.d", root=True),
    ])
    m = metrics(ch)
    assert m.nodes == 4
    assert m.edges == 2
    assert m.roots == 2                 # a.a and a.d
    assert m.leaves == 2                # a.c and a.d
    assert m.longest_chain == 3         # a -> b -> c
    assert m.cycles == 0
    assert m.components == 2            # the chain, and lonely d
    assert m.isolated == 1


def test_metrics_render_is_human_readable():
    out = metrics(load(SEED)).render()
    for label in ("Nodes:", "Edges:", "Roots:", "Leaves:", "Cycles:",
                  "Connected components:", "Longest chain:"):
        assert label in out


def test_metrics_catch_the_scenario_they_exist_for():
    # "Nodes: 51, Edges: 2" — the import that silently dropped the edges.
    broken = _chapter([_kc(f"a.n{i}", root=True) for i in range(51)])
    m = metrics(broken)
    assert m.nodes == 51 and m.edges == 0
    assert m.components == 51            # 51 islands screams louder than the count


# ---------------------------------------------------------------------------
# determinism / idempotency
# ---------------------------------------------------------------------------

def test_graph_hash_is_stable_across_loads():
    assert graph_hash(load(SEED)) == graph_hash(load(SEED))


def test_graph_hash_ignores_comments_and_key_order():
    a = parse("subject: PHY\nchapter: PHY::m::11\nknowledge_components:\n"
              "  - id: a.b\n    name: B\n")
    b = parse("# a comment\nchapter: PHY::m::11\nsubject: PHY\n"
              "knowledge_components:\n  - name: B\n    id: a.b\n")
    assert graph_hash(a) == graph_hash(b)


def test_graph_hash_changes_when_an_edge_changes():
    a = _chapter([_kc("a.b"), _kc("a.c", prereqs=["a.b"])])
    b = _chapter([_kc("a.b"), _kc("a.c")])
    assert graph_hash(a) != graph_hash(b)


def test_graph_hash_changes_when_a_name_changes():
    a = _chapter([_kc("a.b", "Vectors", root=True)])
    b = _chapter([_kc("a.b", "Vectors and scalars", root=True)])
    assert graph_hash(a) != graph_hash(b)


def test_dot_export_is_stable():
    ch = load(SEED)
    assert to_dot(ch) == to_dot(ch)


def test_dot_export_contains_every_node_and_edge():
    ch = load(SEED)
    dot = to_dot(ch)
    assert dot.startswith("digraph") and dot.rstrip().endswith("}")
    for k in ch.kcs:
        assert f'"{k.id}"' in dot
    for prereq, postreq in ch.edges:
        assert f'"{prereq}" -> "{postreq}"' in dot


# ---------------------------------------------------------------------------
# the real seed — these are the checks that matter on the actual content
# ---------------------------------------------------------------------------

def test_seed_file_exists_and_is_valid():
    validate(load(SEED))                 # raises with a readable message if not


def test_seed_is_acyclic():
    assert find_cycle(load(SEED)) is None


def test_seed_has_no_isolated_nodes():
    assert metrics(load(SEED)).isolated == 0


def test_seed_is_one_connected_graph():
    # A second component in a single chapter means a whole section was wired up
    # to nothing.
    assert metrics(load(SEED)).components == 1


def test_seed_is_sanely_sized():
    # Deliberately loose. This is a smoke alarm for "the import broke", NOT a
    # target: ADR-013 says telemetry decides granularity, not a number. If a real
    # curation change moves these, move the bounds and say why in the PR.
    m = metrics(load(SEED))
    assert 40 <= m.nodes <= 70, f"{m.nodes} KCs — deliberate, or an import bug?"
    assert m.edges >= m.nodes, "fewer edges than nodes: suspiciously disconnected"
    assert m.roots >= 1
    assert m.longest_chain >= 4, "no real prerequisite depth — is the DAG wired up?"


def test_seed_chapter_matches_the_chunks_convention():
    # The one string that must equal chunks.chapter exactly or RAG returns nothing.
    assert load(SEED).chapter == "PHY::mechanics::11"


def test_every_seed_prereq_resolves_within_the_chapter():
    ch = load(SEED)
    ids = {k.id for k in ch.kcs}
    for k in ch.kcs:
        for p in k.prereqs:
            assert p in ids, f"{k.id} -> {p} is a dangling prereq"


def test_seed_ids_share_the_chapter_prefix():
    for k in load(SEED).kcs:
        assert k.id.startswith("phy.mech."), f"{k.id} is not under phy.mech."


# ---------------------------------------------------------------------------
# the CLI — --check must never touch a database, and must never crash on the
# error path (that's where it earns its keep)
# ---------------------------------------------------------------------------

CYCLE_YAML = """
subject: PHY
chapter: PHY::mechanics::11
knowledge_components:
  - id: phy.mech.projectile
    name: Projectile Motion
    prereqs: [phy.mech.vectors]
  - id: phy.mech.vectors
    name: Vectors
    prereqs: [phy.mech.kinematics]
  - id: phy.mech.kinematics
    name: Kinematics
    prereqs: [phy.mech.projectile]
"""


def test_cli_check_on_the_real_seed_succeeds_and_prints_metrics(capsys):
    from app.ingest.kc import main
    assert main([str(SEED), "--check"]) == 0
    out = capsys.readouterr().out
    assert "Nodes:" in out and "Cycles:" in out and "Graph hash:" in out
    assert "nothing written" in out


def test_cli_check_writes_no_dot_unless_asked(tmp_path, capsys):
    from app.ingest.kc import main
    main([str(SEED), "--check"])
    assert not list(tmp_path.glob("*.dot"))


def test_cli_dot_flag_writes_a_renderable_file(tmp_path, capsys):
    from app.ingest.kc import main
    out_file = tmp_path / "kc.dot"
    assert main([str(SEED), "--check", "--dot", str(out_file)]) == 0
    dot = out_file.read_text(encoding="utf-8")
    assert dot.startswith("digraph") and "->" in dot


def test_cli_fails_with_exit_1_on_a_cycle(tmp_path, capsys):
    from app.ingest.kc import main
    spec = tmp_path / "cycle.yaml"
    spec.write_text(CYCLE_YAML, encoding="utf-8")
    assert main([str(spec), "--check"]) == 1
    err = capsys.readouterr().err
    assert "Ingest failed." in err and "Detected cycle:" in err
    assert "Projectile Motion" in err


def test_cli_fails_with_exit_1_on_a_missing_file(tmp_path, capsys):
    from app.ingest.kc import main
    assert main([str(tmp_path / "nope.yaml"), "--check"]) == 1
    assert "Ingest failed." in capsys.readouterr().err


def test_cli_reconfigures_stdio_for_unicode():
    """Regression: the cycle report contains '↓', and a Windows console is
    cp1252 — printing it raised UnicodeEncodeError, so the tool crashed exactly
    when it had found the cycle it exists to find. capsys can't reproduce a
    cp1252 stream, so assert the guard is wired instead of the symptom."""
    import io
    import sys

    from app.ingest.kc import _utf8_stdio

    class Cp1252Stream(io.TextIOWrapper):
        reconfigured = None

        def reconfigure(self, *, encoding=None, errors=None, **kw):
            type(self).reconfigured = (encoding, errors)

    fake = Cp1252Stream(io.BytesIO(), encoding="cp1252")
    real_out = sys.stdout
    try:
        sys.stdout = fake
        _utf8_stdio()
    finally:
        sys.stdout = real_out
    assert Cp1252Stream.reconfigured == ("utf-8", "replace")


def test_utf8_stdio_survives_a_stream_that_cannot_reconfigure():
    """Must not explode when stdout is something odd (a pytest capture object,
    a pipe wrapper). Failing to prettify output is never worth an exception."""
    import sys

    from app.ingest.kc import _utf8_stdio

    class Plain:
        pass

    real_out, real_err = sys.stdout, sys.stderr
    try:
        sys.stdout = sys.stderr = Plain()       # no .reconfigure at all
        _utf8_stdio()                            # must be a no-op, not a crash
    finally:
        sys.stdout, sys.stderr = real_out, real_err
