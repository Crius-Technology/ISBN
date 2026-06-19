"""Command-line entry point: init the DB, ingest sources, show stats.

Examples:
    uv run isbn-db init-db
    uv run isbn-db ingest-openlibrary data/ol_dump_editions.txt.gz --limit 5000
    uv run isbn-db ingest-dnb data/dnb_all_dnbmarc.1.mrc.gz
    uv run isbn-db stats
"""

from __future__ import annotations

import argparse
import os
import sys

from . import geo, quality
from .db import connect, init_db
from .ingest import libris, onix
from .ingest.common import open_gzip_text, run_ingest
from .ingest.dnb import SOURCE as DNB_SOURCE
from .ingest.dnb import iter_editions_from_path
from .ingest.openlibrary import SOURCE as OL_SOURCE
from .ingest.openlibrary import iter_editions


def _log(msg: str) -> None:
    print(msg, flush=True)


def cmd_init_db(_args: argparse.Namespace) -> int:
    init_db()
    _log("schema ready")
    return 0


def cmd_ingest_openlibrary(args: argparse.Namespace) -> int:
    dump_file = os.path.basename(args.path)
    records = iter_editions(open_gzip_text(args.path))
    run_ingest(OL_SOURCE, dump_file, records, limit=args.limit, resume=not args.no_resume, log=_log)
    return 0


def cmd_ingest_dnb(args: argparse.Namespace) -> int:
    for path in args.paths:
        dump_file = os.path.basename(path)
        records = iter_editions_from_path(path)
        run_ingest(DNB_SOURCE, dump_file, records, limit=args.limit, resume=not args.no_resume, log=_log)
    return 0


def cmd_ingest_libris(args: argparse.Namespace) -> int:
    result = libris.harvest(from_year=args.from_year, to_year=args.to_year, resume=not args.no_resume, log=_log)
    _log(f"[libris] DONE: {result['valid']:,} records across {result['chunks']} chunks")
    return 0


def cmd_ingest_onix(args: argparse.Namespace) -> int:
    dump_file = os.path.basename(args.path)
    records = onix.iter_editions_from_path(args.path, source=args.source)
    run_ingest(args.source, dump_file, records, limit=args.limit, resume=not args.no_resume, log=_log)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    n = quality.score_all(rescore=args.rescore, log=_log)
    _log(f"[quality] DONE: scored {n:,} rows")
    return 0


def cmd_derive_areas(args: argparse.Namespace) -> int:
    n = geo.derive_all(redo=args.redo, log=_log)
    _log(f"[geo] DONE: set registration_area on {n:,} rows")
    return 0


def cmd_areas(_args: argparse.Namespace) -> int:
    with connect() as conn:
        _log("editions by registration area (top 20):")
        for area, n in conn.execute(
            "SELECT coalesce(registration_area,'(unknown)'), count(*) FROM editions GROUP BY 1 ORDER BY 2 DESC LIMIT 20"
        ).fetchall():
            _log(f"  {area:28s} {n:,}")
    return 0


def cmd_quality(_args: argparse.Namespace) -> int:
    with connect() as conn:
        row = conn.execute(
            "SELECT count(*) FILTER (WHERE quality_score IS NOT NULL), round(avg(quality_score),1) FROM editions"
        ).fetchone()
        _log(f"scored: {row[0]:,}  avg score: {row[1]}")
        _log("score buckets:")
        for lo, n in conn.execute(
            "SELECT (quality_score/10*10) bucket, count(*) FROM editions "
            "WHERE quality_score IS NOT NULL GROUP BY 1 ORDER BY 1 DESC"
        ).fetchall():
            _log(f"  {lo:3d}-{lo + 9:<3d} {n:,}")
        _log("most common flags:")
        for flag, n in conn.execute(
            "SELECT f, count(*) FROM editions, unnest(quality_flags) f GROUP BY f ORDER BY 2 DESC LIMIT 10"
        ).fetchall():
            _log(f"  {flag:18s} {n:,}")
    return 0


def cmd_stats(_args: argparse.Namespace) -> int:
    with connect() as conn:
        total = conn.execute("SELECT count(*) FROM editions").fetchone()[0]
        _log(f"editions total: {total:,}")
        _log("by source:")
        for source, n in conn.execute(
            "SELECT source, count(*) FROM editions GROUP BY source ORDER BY 2 DESC"
        ).fetchall():
            _log(f"  {source:14s} {n:,}")
        _log("ingest_state:")
        for row in conn.execute(
            "SELECT source, dump_file, lines_read, records_valid, records_upserted, status "
            "FROM ingest_state ORDER BY source, dump_file"
        ).fetchall():
            _log(f"  {row[0]:6s} {row[1]:40s} lines={row[2]:,} valid={row[3]:,} up={row[4]:,} [{row[5]}]")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="isbn-db")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create tables").set_defaults(func=cmd_init_db)

    p_ol = sub.add_parser("ingest-openlibrary", help="ingest an Open Library editions dump")
    p_ol.add_argument("path")
    p_ol.add_argument("--limit", type=int, default=None, help="stop after N valid records (testing)")
    p_ol.add_argument("--no-resume", action="store_true")
    p_ol.set_defaults(func=cmd_ingest_openlibrary)

    p_dnb = sub.add_parser("ingest-dnb", help="ingest one or more DNB MARC dumps")
    p_dnb.add_argument("paths", nargs="+")
    p_dnb.add_argument("--limit", type=int, default=None)
    p_dnb.add_argument("--no-resume", action="store_true")
    p_dnb.set_defaults(func=cmd_ingest_dnb)

    p_lib = sub.add_parser("ingest-libris", help="harvest the Swedish national bibliography via OAI-PMH")
    p_lib.add_argument("--from-year", type=int, default=2002)
    p_lib.add_argument("--to-year", type=int, default=2026)
    p_lib.add_argument("--no-resume", action="store_true")
    p_lib.set_defaults(func=cmd_ingest_libris)

    p_onix = sub.add_parser("ingest-onix", help="ingest an ONIX 3.0 file (e.g. Nielsen UK, VLB DE)")
    p_onix.add_argument("path")
    p_onix.add_argument("--source", default="nielsen", help="source key from the registry (nielsen, vlb, ...)")
    p_onix.add_argument("--limit", type=int, default=None)
    p_onix.add_argument("--no-resume", action="store_true")
    p_onix.set_defaults(func=cmd_ingest_onix)

    p_score = sub.add_parser("score", help="compute per-record quality scores")
    p_score.add_argument("--rescore", action="store_true", help="recompute all rows (not just unscored)")
    p_score.set_defaults(func=cmd_score)

    p_area = sub.add_parser("derive-areas", help="derive registration_area from each ISBN")
    p_area.add_argument("--redo", action="store_true", help="recompute all rows")
    p_area.set_defaults(func=cmd_derive_areas)

    sub.add_parser("areas", help="show editions by ISBN registration area").set_defaults(func=cmd_areas)
    sub.add_parser("quality", help="show quality score distribution and common flags").set_defaults(func=cmd_quality)
    sub.add_parser("stats", help="show row counts and ingest progress").set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
