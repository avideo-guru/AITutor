"""Migration hygiene — [[ADR-011]]'s rules, enforced instead of documented.

These are cheap static checks (no DB, no deps). They deliberately do NOT prove a
migration *works* — only a fresh-database apply does that, and that needs
Postgres:

    docker run -d --name pg -e POSTGRES_PASSWORD=test -p 55432:5432 \
        pgvector/pgvector:pg16
    # stub the Supabase-managed bits the migrations reference:
    #   create schema auth; create table auth.users(id uuid primary key);
    #   create schema if not exists extensions;
    cat supabase/migrations/*.sql | psql "postgres://postgres:test@localhost:55432/postgres"

    # or, with the CLI:  supabase db reset

That belongs in CI (there is none in this repo yet — see docs/Status.md). Until
then these catch the failure modes that are *silent*: a filename that sorts
wrong, a duplicate timestamp, a guard that no-ops.
"""

import pathlib
import re
from datetime import datetime

import pytest

MIGRATIONS = pathlib.Path(__file__).resolve().parents[2] / "supabase" / "migrations"

# <UTC timestamp>_<snake_case>.sql — the Supabase CLI's convention and the
# ledger's key. Lexical order must equal chronological order, which this format
# guarantees and a human-readable prefix ("0008_", "a1_") would not.
NAME_RE = re.compile(r"^(\d{14})_[a-z0-9_]+\.sql$")

# The squashed baseline is allowed `if not exists` so it can be applied to a
# project that already has the P0 objects; its header says so. Nothing else is.
BASELINE = "20260716120000_baseline_p0_p1.sql"


def _migrations() -> list[pathlib.Path]:
    return sorted(MIGRATIONS.glob("*.sql"))


def test_migrations_directory_exists_and_is_not_empty():
    assert MIGRATIONS.is_dir(), f"{MIGRATIONS} missing — the schema lives here now"
    assert _migrations(), "no migrations found"


@pytest.mark.parametrize("path", _migrations(), ids=lambda p: p.name)
def test_filename_is_timestamp_underscore_snake_case(path):
    assert NAME_RE.match(path.name), (
        f"{path.name} must be <YYYYMMDDHHMMSS>_<snake_case>.sql — "
        "sequence numbers collide across our two branches and git merges them "
        "without a conflict (ADR-011)"
    )


@pytest.mark.parametrize("path", _migrations(), ids=lambda p: p.name)
def test_timestamp_is_a_real_utc_datetime(path):
    stamp = NAME_RE.match(path.name).group(1)
    # Catches 20261345000000 — which sorts fine and is nonsense.
    datetime.strptime(stamp, "%Y%m%d%H%M%S")


def test_timestamps_are_unique():
    stamps = [NAME_RE.match(p.name).group(1) for p in _migrations()]
    dupes = {s for s in stamps if stamps.count(s) > 1}
    assert not dupes, f"duplicate migration timestamps {dupes} — apply order is undefined"


def test_lexical_order_equals_chronological_order():
    paths = _migrations()                       # sorted lexically by glob+sorted
    stamps = [NAME_RE.match(p.name).group(1) for p in paths]
    assert stamps == sorted(stamps), "lexical order != chronological order"


@pytest.mark.parametrize(
    "path", [p for p in _migrations() if p.name != BASELINE], ids=lambda p: p.name
)
def test_new_migrations_do_not_use_if_not_exists(path):
    """ADR-011 rule 4. `if not exists` answers 'something vaguely compatible is
    already there', not 'the schema evolved as intended'. On a drifted database
    it no-ops and reports success — the failure mode that hid the drift this ADR
    exists to end. Let it fail loudly.

    (`create index concurrently if not exists` is the documented exception; add
    it here with a comment if a migration ever needs one.)"""
    sql = path.read_text(encoding="utf-8")
    body = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )
    assert "if not exists" not in body.lower(), (
        f"{path.name} uses 'if not exists' — see ADR-011 rule 4"
    )


@pytest.mark.parametrize("path", _migrations(), ids=lambda p: p.name)
def test_migration_has_a_header_comment(path):
    """A migration is the record of why a schema change happened. `git log`
    rots; the file is what the next person reads."""
    first = path.read_text(encoding="utf-8").lstrip().splitlines()[0]
    assert first.startswith("--"), f"{path.name} starts without a header comment"


def test_schema_sql_is_demoted_and_not_a_second_source_of_truth():
    """backend/schema.sql must stay a pointer. If DDL reappears in it, we are
    back to two disagreeing histories (ADR-011)."""
    schema = MIGRATIONS.parents[1] / "backend" / "schema.sql"
    if not schema.exists():
        return                                   # deleted outright is fine too
    body = "\n".join(
        line for line in schema.read_text(encoding="utf-8").splitlines()
        if not line.strip().startswith("--")
    )
    assert not body.strip(), (
        "backend/schema.sql contains SQL again — it is a pointer, not the "
        "schema. Add a migration instead (ADR-011)."
    )
