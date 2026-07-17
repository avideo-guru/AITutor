"""Item specs: parse and lint. Pure — no DB, no network.

**Content is code, and this is its type checker.** Bad content should fail the
same way bad Python does: loudly, before it lands, with a message that says
which line to go fix. Everything here runs against files only, so it runs in CI
with no database.

The rule that shapes the rest ([[ADR-016]]): **an item the verification engine
cannot grade must never enter the bank.** Every item's `answer` is checked by
handing the gold back to `GoldAnswerChecker` and demanding a PASS. If the
checker can't grade the item at lint time, it can't grade it at 2am when a
student answers it — and B.2 would silently store `correct = null` forever.

Format (`content/items/*.yaml`):

    subject: PHY
    chapter: PHY::mechanics::11
    items:
      - slug: phy.mech.projectile_ground.q001
        kc:   phy.mech.projectile_ground
        stem: |
          A ball is projected at $30^\\circ$ ... Find the range.
        answer:
          value: 20.4
          unit: m
        hints:
          - Resolve the initial velocity into components.
        source: NCERT Exemplar Physics XI, Q4.12

`difficulty` is deliberately NOT a field — Elo owns it ([[ADR-012]]), and the
linter rejects the key rather than ignoring it, because an author who writes
`difficulty: hard` deserves to be told it does nothing.
"""

import hashlib
import json
import re
import uuid
from dataclasses import dataclass

import yaml

from app.ids import ChapterId, InvalidChapterId
from app.verify.base import Claim, Outcome
from app.verify.checkers.gold import GoldAnswerChecker

# Stable namespace for item uuid5s. NEVER change this: it is what makes
# `id = f(slug)` reproducible from the YAML alone, forever.
ITEM_NAMESPACE = uuid.UUID("6f9b1f6e-7f1a-5a3e-9c2d-1f0a7b4c8d21")

SLUG_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z0-9_]+)+$")

# Keys an author might reasonably write that we must reject rather than ignore.
BANNED_KEYS = {
    "difficulty": "Elo owns difficulty and learns it from attempts (ADR-012); "
                  "authoring it would be overwritten and mislead the author",
    "id": "items are identified by `slug`; the uuid is derived from it",
    "rating": "same as difficulty — derived, never authored",
}
REQUIRED_KEYS = ("slug", "kc", "stem", "answer", "source")


class ItemError(Exception):
    """Lint failure. Message is for a human fixing YAML."""


@dataclass(frozen=True)
class Item:
    slug: str
    kc: str
    stem: str
    answer: dict
    source: str
    hints: tuple[str, ...] = ()

    @property
    def uuid(self) -> uuid.UUID:
        """Derived from the slug, so the same YAML yields the same row id on any
        machine, with or without a database."""
        return uuid.uuid5(ITEM_NAMESPACE, self.slug)

    @property
    def content_hash(self) -> str:
        """Change/duplicate detection — NOT identity (that's the slug, ADR-015).
        Canonical JSON so key order in the YAML can't change the hash."""
        payload = json.dumps(
            {"stem": _normalize_stem(self.stem), "answer": self.answer, "kc": self.kc},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class ItemSet:
    subject: str
    chapter: str
    items: tuple[Item, ...]


def _normalize_stem(stem: str) -> str:
    """Collapse whitespace so re-indenting a YAML block doesn't read as an edit."""
    return re.sub(r"\s+", " ", stem).strip()


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

def parse(text: str) -> ItemSet:
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise ItemError(f"YAML is not parseable:\n{e}") from e

    if not isinstance(raw, dict):
        raise ItemError("top level must be a mapping with subject/chapter/items")
    for key in ("subject", "chapter", "items"):
        if key not in raw:
            raise ItemError(f"missing required top-level key: {key!r}")
    entries = raw["items"]
    if not isinstance(entries, list) or not entries:
        raise ItemError("items must be a non-empty list")

    items = []
    for i, e in enumerate(entries):
        if not isinstance(e, dict):
            raise ItemError(f"items[{i}] is not a mapping")
        where = e.get("slug", f"items[{i}]")
        for banned, why in BANNED_KEYS.items():
            if banned in e:
                raise ItemError(f"{where}: remove `{banned}` — {why}")
        missing = [k for k in REQUIRED_KEYS if k not in e]
        if missing:
            raise ItemError(f"{where}: missing required key(s) {missing}")
        answer = e["answer"]
        if not isinstance(answer, dict):
            raise ItemError(f"{where}: `answer` must be a mapping, e.g. {{value: 9.8, unit: 'm/s^2'}}")
        hints = e.get("hints") or []
        if not isinstance(hints, list):
            raise ItemError(f"{where}: `hints` must be a list")
        items.append(Item(
            slug=str(e["slug"]), kc=str(e["kc"]), stem=str(e["stem"]),
            answer=answer, source=str(e["source"]),
            hints=tuple(str(h) for h in hints),
        ))

    return ItemSet(subject=str(raw["subject"]), chapter=str(raw["chapter"]),
                   items=tuple(items))


def load(path) -> ItemSet:
    import pathlib
    return parse(pathlib.Path(path).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# the gradeability gate — the reason this linter earns its keep
# --------------------------------------------------------------------------

def canonical_response(answer: dict) -> str | None:
    """The answer a perfect student would type. Used to ask the checker whether
    this gold is gradeable at all."""
    if "choices" in answer:
        choices = answer["choices"]
        if isinstance(choices, (list, tuple)):
            return ",".join(str(c) for c in choices)
        return str(choices)
    if answer.get("value") is not None:
        unit = answer.get("unit")
        return f"{answer['value']} {unit}" if unit else str(answer["value"])
    return None


def check_gradeable(item: Item) -> None:
    """Hand the gold back to the real checker and demand a PASS.

    This is the whole point of linting content: if `GoldAnswerChecker` cannot
    grade the canonical correct answer, then no student answer will ever be
    gradeable either — B.2 would store `correct = null` (INAPPLICABLE) forever
    and the item would silently never teach anyone anything. Better to fail here,
    where a human is looking at the file."""
    response = canonical_response(item.answer)
    if response is None:
        raise ItemError(
            f"{item.slug}: `answer` has neither `value` nor `choices`, so nothing "
            f"can grade it. Got keys {sorted(item.answer)}."
            + ("\n  `expr` alone needs the sympy checker, which lands with P5.0 "
               "(ADR-009) — give a numeric `value` as well for now."
               if "expr" in item.answer else "")
        )

    verdict = GoldAnswerChecker().check(Claim(
        kind="final_answer", domain="curated", response=response, gold=item.answer,
    ))
    if verdict.outcome is not Outcome.PASS:
        raise ItemError(
            f"{item.slug}: the verifier cannot grade this item — it returned "
            f"{verdict.outcome.value.upper()} ({verdict.reason}) when checking the "
            f"gold answer {response!r} against its own gold. An item that cannot "
            "be graded must not enter the bank (ADR-016)."
        )


# --------------------------------------------------------------------------
# lint
# --------------------------------------------------------------------------

def lint(items: ItemSet, kc_ids: set[str], kc_chapter: str | None = None) -> None:
    """Every rule is fatal. `kc_ids` comes from the KC spec file, not the DB:
    content validates against content, so this runs in CI."""
    problems: list[str] = []

    try:
        parsed = ChapterId.parse(items.chapter)
    except InvalidChapterId as e:
        raise ItemError("Lint failed.\n\n" + str(e))
    if parsed.subject != items.subject:
        problems.append(
            f"subject {items.subject!r} disagrees with the chapter's subject "
            f"{parsed.subject!r} in {items.chapter!r}"
        )
    if kc_chapter and items.chapter != kc_chapter:
        problems.append(
            f"chapter {items.chapter!r} != the KC graph's {kc_chapter!r}. These must "
            "be identical or the items belong to a chapter whose KCs live elsewhere."
        )
    if problems:
        raise ItemError("Lint failed.\n\n" + "\n".join(problems))

    seen_slugs: set[str] = set()
    stems_by_kc: dict[str, dict[str, str]] = {}

    for item in items.items:
        if not SLUG_RE.match(item.slug):
            problems.append(
                f"{item.slug!r}: slug must be a lowercase dotted path, conventionally "
                "<kc_id>.qNNN (phy.mech.projectile_ground.q001)"
            )
        if item.slug in seen_slugs:
            problems.append(f"{item.slug}: duplicate slug — slugs are identity (ADR-015)")
        seen_slugs.add(item.slug)

        # exactly one KC. A list would silently take the first one.
        if not isinstance(item.kc, str) or not item.kc:
            problems.append(f"{item.slug}: `kc` must be exactly one knowledge-component id")
        elif item.kc not in kc_ids:
            problems.append(
                f"{item.slug}: kc {item.kc!r} is not in the KC graph "
                "(typo, or the graph hasn't been seeded with it yet)"
            )

        if not item.stem.strip():
            problems.append(f"{item.slug}: stem is empty")
        if not item.source.strip():
            problems.append(
                f"{item.slug}: `source` is required — attribution is a licensing "
                "obligation for NCERT/JEE material, not metadata garnish"
            )

        # duplicate stems WITHIN a kc: the adaptive loop would serve the same
        # question twice and read the second attempt as independent evidence of
        # mastery. Across KCs it's legitimate (same setup, different question).
        norm = _normalize_stem(item.stem)
        bucket = stems_by_kc.setdefault(item.kc, {})
        if norm in bucket:
            problems.append(
                f"{item.slug}: stem duplicates {bucket[norm]} within kc {item.kc} — "
                "the loop would serve it twice and double-count the evidence"
            )
        else:
            bucket[norm] = item.slug

        try:
            check_gradeable(item)
        except ItemError as e:
            problems.append(str(e))

    # Identical content under two slugs collides on content_hash's unique index
    # at insert time; say so here instead of surfacing a Postgres error.
    by_hash: dict[str, str] = {}
    for item in items.items:
        h = item.content_hash
        if h in by_hash:
            problems.append(
                f"{item.slug}: identical content to {by_hash[h]} (same content_hash) — "
                "would violate items.content_hash unique"
            )
        by_hash[h] = item.slug

    if problems:
        raise ItemError("Lint failed.\n\n" + "\n".join(f"  - {p}" for p in problems))


def coverage(items: ItemSet, kc_ids: set[str]) -> dict:
    """Per-KC item counts + the KCs with none. Not a lint failure — a report.

    An adaptive loop needs a difficulty ladder per KC (~5-6 items); a KC with one
    item cannot adapt, it can only serve. This is the number that says whether
    the bank is ready for B.2, and it is the one worth watching during curation.
    """
    counts: dict[str, int] = {k: 0 for k in kc_ids}
    for item in items.items:
        if item.kc in counts:
            counts[item.kc] += 1
    covered = {k: n for k, n in counts.items() if n}
    return {
        "items": len(items.items),
        "kcs_total": len(kc_ids),
        "kcs_covered": len(covered),
        "kcs_uncovered": sorted(k for k, n in counts.items() if n == 0),
        "per_kc": counts,
        "thin": sorted(k for k, n in counts.items() if 0 < n < 5),
    }
