"""Knowledge-graph spec: parse, validate, measure, order, render.

Pure — no DB, no I/O beyond reading the YAML text. `kc.py` is the thing that
talks to Postgres; everything here is testable without one.

**This module is the integrity boundary.** Postgres can enforce "no self-loop"
(a CHECK) and "every prereq exists" (an FK), but it *cannot* express "acyclic" —
so A→B→A inserts cleanly and silently makes the frontier query nonsense. The
database cannot defend itself here, which means validation is not a nicety
bolted onto the ingest: it is the only thing standing between a typo and a
knowledge graph that lies. Hence: every check is a hard failure, and the caller
must never write a partial graph.

Determinism is the other contract ([[ADR-014]]): the same YAML must produce the
same rows, the same order, and the same hash, forever. That is what makes
re-running the seed a no-op instead of a diff.
"""

import hashlib
import re
from dataclasses import dataclass, field

import yaml

from app.ids import ChapterId, InvalidChapterId

# Mirrors `knowledge_components.id`: a human-readable path, lowercase, dotted.
# Reviewable in a diff — a wrong prereq should be visible to a human reader.
ID_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

SUBJECT_RE = re.compile(r"^[A-Z]{2,6}$")

# The chapter grammar lives in app.ids, not here. Two modules each holding their
# own copy of a shared identifier's rules is how the two strings drift apart —
# which is the exact bug this validation exists to prevent.


class GraphError(Exception):
    """Validation failed. The message is written to be read by a human at a
    terminal who has to go fix a YAML file."""


@dataclass(frozen=True)
class KC:
    id: str
    name: str
    prereqs: tuple[str, ...] = ()
    root: bool = False              # asserts "intentionally standalone"


@dataclass(frozen=True)
class Chapter:
    subject: str
    chapter: str
    kcs: tuple[KC, ...]

    @property
    def by_id(self) -> dict[str, KC]:
        return {k.id: k for k in self.kcs}

    @property
    def edges(self) -> tuple[tuple[str, str], ...]:
        """(prereq, postreq), in deterministic file order."""
        return tuple(
            (p, k.id) for k in self.kcs for p in k.prereqs
        )


@dataclass
class Metrics:
    nodes: int = 0
    edges: int = 0
    roots: int = 0
    leaves: int = 0
    max_depth: int = 0
    longest_chain: int = 0
    cycles: int = 0
    components: int = 0
    isolated: int = 0

    def render(self) -> str:
        return "\n".join([
            "Knowledge graph",
            f"  Nodes:                 {self.nodes}",
            f"  Edges:                 {self.edges}",
            f"  Roots:                 {self.roots}",
            f"  Leaves:                {self.leaves}",
            f"  Maximum depth:         {self.max_depth}",
            f"  Longest chain:         {self.longest_chain}",
            f"  Cycles:                {self.cycles}",
            f"  Connected components:  {self.components}",
            f"  Isolated nodes:        {self.isolated}",
        ])


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

def parse(text: str) -> Chapter:
    """YAML → Chapter. Structural errors only; graph errors are validate()'s."""
    try:
        raw = yaml.safe_load(text)          # safe_load: never construct objects
    except yaml.YAMLError as e:
        raise GraphError(f"YAML is not parseable:\n{e}") from e

    if not isinstance(raw, dict):
        raise GraphError("top level must be a mapping with subject/chapter/knowledge_components")

    for key in ("subject", "chapter", "knowledge_components"):
        if key not in raw:
            raise GraphError(f"missing required top-level key: {key!r}")

    entries = raw["knowledge_components"]
    if not isinstance(entries, list) or not entries:
        raise GraphError("knowledge_components must be a non-empty list")

    kcs = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise GraphError(f"knowledge_components[{i}] is not a mapping")
        if "id" not in e or "name" not in e:
            raise GraphError(f"knowledge_components[{i}] needs both 'id' and 'name'")
        prereqs = e.get("prereqs") or []
        if not isinstance(prereqs, list):
            raise GraphError(f"{e['id']}: prereqs must be a list")
        kcs.append(KC(
            id=str(e["id"]),
            name=str(e["name"]),
            prereqs=tuple(str(p) for p in prereqs),
            root=bool(e.get("root", False)),
        ))

    return Chapter(subject=str(raw["subject"]), chapter=str(raw["chapter"]),
                   kcs=tuple(kcs))


def load(path) -> Chapter:
    import pathlib
    return parse(pathlib.Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# validate — every failure here is fatal
# --------------------------------------------------------------------------

def find_cycle(chapter: Chapter) -> list[str] | None:
    """One cycle as a node-id path (first == last), or None.

    Iterative DFS with an explicit stack: a recursive version blows Python's
    stack on a deep chain, and "the validator crashed" is a much worse failure
    mode than "the graph has a cycle". Deterministic: nodes and their prereqs
    are walked in file order, so the *same* cycle is reported every run.
    """
    by_id = chapter.by_id
    WHITE, GREY, BLACK = 0, 1, 2
    colour = {k.id: WHITE for k in chapter.kcs}

    for start in chapter.kcs:
        if colour[start.id] != WHITE:
            continue
        # stack of (node, iterator over its prereqs), path mirrors the greys
        stack: list[tuple[str, list[str]]] = [(start.id, list(by_id[start.id].prereqs))]
        path = [start.id]
        colour[start.id] = GREY
        while stack:
            node, todo = stack[-1]
            if not todo:
                colour[node] = BLACK
                stack.pop()
                path.pop()
                continue
            nxt = todo.pop(0)
            if nxt not in by_id:
                continue                       # unknown ref — caught separately
            if colour[nxt] == GREY:            # back-edge: cycle
                cut = path.index(nxt)
                return path[cut:] + [nxt]
            if colour[nxt] == WHITE:
                colour[nxt] = GREY
                path.append(nxt)
                stack.append((nxt, list(by_id[nxt].prereqs)))
    return None


def _format_cycle(chapter: Chapter, cycle: list[str]) -> str:
    by_id = chapter.by_id
    lines = []
    for i, node in enumerate(cycle):
        lines.append(f"  {by_id[node].name}  ({node})")
        if i < len(cycle) - 1:
            lines.append("    ↓ requires")
    return "\n".join(lines)


def validate(chapter: Chapter) -> None:
    """Raise GraphError on the first class of problem found, listing every
    instance of it. Raises rather than returns: a caller that has to remember to
    check a return value is a caller that will forget, and the cost of forgetting
    is a corrupt graph."""
    problems: list[str] = []

    if not SUBJECT_RE.match(chapter.subject):
        problems.append(
            f"subject {chapter.subject!r} must be uppercase letters (e.g. 'PHY') "
            "to match chunks.subject"
        )
    try:
        parsed = ChapterId.parse(chapter.chapter)
    except InvalidChapterId as e:
        problems.append(str(e))
    else:
        # A KC graph that says subject: PHY but chapter: CHEM::… would write two
        # columns that contradict each other, and filtering by either would give a
        # different answer.
        if parsed.subject != chapter.subject:
            problems.append(
                f"subject {chapter.subject!r} disagrees with the chapter's subject "
                f"{parsed.subject!r} in {chapter.chapter!r}"
            )
    if problems:
        raise GraphError("Ingest failed.\n\n" + "\n".join(problems))

    # --- ids ---------------------------------------------------------------
    seen: set[str] = set()
    for k in chapter.kcs:
        if not ID_RE.match(k.id):
            problems.append(f"id {k.id!r} must be a lowercase dotted path (phy.mech.vectors)")
        if k.id in seen:
            problems.append(f"duplicate id: {k.id!r}")
        seen.add(k.id)
        if not k.name.strip():
            problems.append(f"{k.id}: name is empty")
    if problems:
        raise GraphError("Ingest failed.\n\n" + "\n".join(problems))

    # --- edges -------------------------------------------------------------
    for k in chapter.kcs:
        for p in k.prereqs:
            if p == k.id:
                problems.append(f"{k.id}: is its own prerequisite (self-loop)")
            if p not in seen:
                problems.append(
                    f"{k.id}: prereq {p!r} does not exist "
                    f"(typo, or a KC from another chapter that isn't seeded yet)"
                )
        if len(set(k.prereqs)) != len(k.prereqs):
            dupes = {p for p in k.prereqs if k.prereqs.count(p) > 1}
            problems.append(f"{k.id}: duplicate prereq(s) {sorted(dupes)}")
    if problems:
        raise GraphError("Ingest failed.\n\n" + "\n".join(problems))

    # --- acyclicity — the check Postgres cannot do for us -------------------
    cycle = find_cycle(chapter)
    if cycle:
        raise GraphError(
            "Ingest failed.\n\nDetected cycle:\n\n"
            + _format_cycle(chapter, cycle)
            + "\n\nA KC cannot transitively require itself — the frontier query would "
              "never unlock any of these."
        )

    # --- isolated nodes ----------------------------------------------------
    has_dependents = {p for k in chapter.kcs for p in k.prereqs}
    for k in chapter.kcs:
        if not k.prereqs and k.id not in has_dependents and not k.root:
            problems.append(
                f"{k.id} ({k.name!r}) is isolated: nothing requires it and it requires "
                "nothing. That is almost always a forgotten edge. If it really is "
                "standalone, mark it `root: true`."
            )
    if problems:
        raise GraphError("Ingest failed.\n\n" + "\n".join(problems))


# --------------------------------------------------------------------------
# order / measure / render
# --------------------------------------------------------------------------

def topo_order(chapter: Chapter) -> list[str]:
    """Prereqs before dependents. Deterministic: Kahn's algorithm with ties
    broken by *file order*, not by set iteration or by id — so the ordering a
    reviewer sees in the YAML is the ordering the tool emits, and two runs can
    never disagree. Assumes validate() has passed."""
    order_index = {k.id: i for i, k in enumerate(chapter.kcs)}
    indegree = {k.id: len(k.prereqs) for k in chapter.kcs}
    dependents: dict[str, list[str]] = {k.id: [] for k in chapter.kcs}
    for k in chapter.kcs:
        for p in k.prereqs:
            dependents[p].append(k.id)

    ready = sorted([i for i, d in indegree.items() if d == 0], key=order_index.get)
    out: list[str] = []
    while ready:
        node = ready.pop(0)
        out.append(node)
        newly = []
        for d in dependents[node]:
            indegree[d] -= 1
            if indegree[d] == 0:
                newly.append(d)
        ready = sorted(ready + newly, key=order_index.get)
    if len(out) != len(chapter.kcs):
        raise GraphError("topological sort failed — validate() should have caught a cycle")
    return out


def metrics(chapter: Chapter) -> Metrics:
    by_id = chapter.by_id
    dependents: dict[str, list[str]] = {k.id: [] for k in chapter.kcs}
    for k in chapter.kcs:
        for p in k.prereqs:
            if p in dependents:
                dependents[p].append(k.id)

    roots = [k.id for k in chapter.kcs if not k.prereqs]
    leaves = [k.id for k in chapter.kcs if not dependents[k.id]]
    isolated = [k.id for k in chapter.kcs if not k.prereqs and not dependents[k.id]]

    cycle = find_cycle(chapter)
    depth: dict[str, int] = {}
    longest = 0
    if not cycle:
        for node in topo_order(chapter):
            prereqs = by_id[node].prereqs
            depth[node] = 1 + max((depth[p] for p in prereqs if p in depth), default=0)
        longest = max(depth.values(), default=0)

    # Undirected connected components — a second, disconnected island of KCs is
    # usually a whole forgotten section rather than a typo.
    adj: dict[str, set[str]] = {k.id: set() for k in chapter.kcs}
    for a, b in chapter.edges:
        if a in adj and b in adj:
            adj[a].add(b)
            adj[b].add(a)
    unseen = {k.id for k in chapter.kcs}
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            n = stack.pop()
            for m in adj[n]:
                if m in unseen:
                    unseen.remove(m)
                    stack.append(m)

    return Metrics(
        nodes=len(chapter.kcs), edges=len(chapter.edges), roots=len(roots),
        leaves=len(leaves), max_depth=longest, longest_chain=longest,
        cycles=1 if cycle else 0, components=components, isolated=len(isolated),
    )


def graph_hash(chapter: Chapter) -> str:
    """Stable digest of the graph's *content* (not the file's bytes — comments
    and key order don't count). Re-running the seed prints the same hash iff
    nothing meaningful changed, which is the cheap idempotency check."""
    h = hashlib.sha256()
    h.update(f"{chapter.subject}\n{chapter.chapter}\n".encode())
    for k in sorted(chapter.kcs, key=lambda k: k.id):
        h.update(f"{k.id}\x1f{k.name}\x1f{','.join(sorted(k.prereqs))}\n".encode())
    return h.hexdigest()[:16]


def to_dot(chapter: Chapter) -> str:
    """Graphviz. Not for users — for us. When someone asks "why is Rolling
    unlocking before Torque?", reading a rendered graph beats reading YAML:

        python -m app.ingest.kc <spec> --dot kc.dot && dot -Tpng kc.dot -o kc.png
    """
    lines = [
        f'digraph "{chapter.chapter}" {{',
        "  rankdir=LR;",
        '  node [shape=box, style=rounded, fontname="Helvetica", fontsize=10];',
        '  edge [color="#888888"];',
    ]
    roots = {k.id for k in chapter.kcs if not k.prereqs}
    for k in chapter.kcs:                       # file order = stable output
        label = k.name.replace('"', '\\"')
        fill = ' style="rounded,filled" fillcolor="#e6f1fb"' if k.id in roots else ""
        lines.append(f'  "{k.id}" [label="{label}"{fill}];')
    for prereq, postreq in chapter.edges:
        lines.append(f'  "{prereq}" -> "{postreq}";')
    lines.append("}")
    return "\n".join(lines) + "\n"
