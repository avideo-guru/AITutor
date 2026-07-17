"""Cross-module identifiers.

Lives at the app root, imported by everything, importing nothing — deliberately.
`adaptive/` may not import `app.core`/`routes`/`models` and `verify/` may not
import tutor code at all (their import-cleanliness tests enforce this), so a
shared identifier cannot live in any of those layers. It lives here.

## ChapterId — `SUBJECT::chapter_slug::grade`

`chapter` looks like a column. It is not: it is a **system-wide identifier** that
three modules must agree on byte-for-byte, with no foreign key to keep them
honest.

    RAG ingest      →  chunks.chapter                = "PHY::mechanics::11"
    KC ingest       →  knowledge_components.chapter  = "PHY::mechanics::11"
    retrieval       →  where chapter = $1              ← exact string equality
    policy (B.2)    →  "explain this item"  → RAG scoped to the item's chapter

One inconsistent string and retrieval returns **zero chunks, silently** — no
error, no FK violation, just an LLM answering with no context and looking like a
bad prompt. That failure was found in A.2 by running the tool; this type is the
fix at the source. Both *write* boundaries (both ingests) parse through here, so
the two strings cannot drift apart without a loud failure at ingest time.

Deliberately NOT enforced at the *read* boundary (`retrieval`, `/v1/ask`): a
malformed chapter there already yields an empty result set rather than a wrong
one, and tightening it would change live request behaviour for no correctness
gain. Validate what you write; be liberal in what you match.
"""

import re
from dataclasses import dataclass

# The canonical grammar. `grade` is the school class (NCERT), which is what the
# pre-existing 'PHY::optics::12' meant — ray optics is class 12, mechanics is
# class 11. Inferred from that one example and since ratified; if it ever turns
# out to have meant a chapter number, this is the one place to change.
GRAMMAR = "SUBJECT::chapter_slug::grade"

SUBJECT_PATTERN = r"[A-Z]{2,6}"          # PHY, CHEM, MATH — matches chunks.subject
SLUG_PATTERN = r"[a-z][a-z0-9_]*"        # mechanics, ray_optics
GRADE_PATTERN = r"[6-9]|1[0-2]"          # school grades 6..12

# Exposed for pydantic models, which keep `chapter` a plain string on the wire
# (it is one) while still refusing a malformed one.
CHAPTER_PATTERN = rf"^{SUBJECT_PATTERN}::{SLUG_PATTERN}::({GRADE_PATTERN})$"
_CHAPTER_RE = re.compile(CHAPTER_PATTERN)


class InvalidChapterId(ValueError):
    """Raised with a message meant for a human at a terminal, not a stack trace."""


@dataclass(frozen=True, order=True)
class ChapterId:
    """A parsed chapter identifier. `str(cid)` is the canonical form and is the
    ONLY thing that should ever be written to a database column."""

    subject: str
    slug: str
    grade: int

    def __str__(self) -> str:
        return f"{self.subject}::{self.slug}::{self.grade}"

    @classmethod
    def parse(cls, raw: str) -> "ChapterId":
        if not isinstance(raw, str) or not _CHAPTER_RE.match(raw):
            raise InvalidChapterId(
                f"chapter {raw!r} is not a valid ChapterId.\n"
                f"  Grammar: {GRAMMAR}   e.g. 'PHY::mechanics::11'\n"
                f"  subject: uppercase, 2-6 letters (must match chunks.subject)\n"
                f"  slug:    lowercase snake_case\n"
                f"  grade:   school class, 6-12\n"
                "This string must be byte-identical everywhere it appears — "
                "retrieval matches it exactly, so a mismatch silently returns no "
                "context instead of raising."
            )
        subject, slug, grade = raw.split("::")
        return cls(subject=subject, slug=slug, grade=int(grade))

    @classmethod
    def is_valid(cls, raw: str) -> bool:
        return isinstance(raw, str) and bool(_CHAPTER_RE.match(raw))
