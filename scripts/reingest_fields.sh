#!/usr/bin/env bash
# One-off: re-parse the DNB + OL dumps to backfill the Tier 1+2 fields (dewey, pub_country, etc.).
# --no-resume forces a full re-parse; the tier-merge upsert preserves higher-tier rows and the
# ISBN-derived geo columns. Ends by re-scoring, refreshing aggregates and building new indexes.
set -u
cd "$(dirname "$0")/.." || exit 1
log(){ echo "[reingest $(date -u +%FT%TZ)] $*" >>data/reingest.log; }

log "DNB re-ingest start (5 files)"
uv run isbn-db ingest-dnb data/dnb_all_dnbmarc.1.mrc.gz data/dnb_all_dnbmarc.2.mrc.gz \
  data/dnb_all_dnbmarc.3.mrc.gz data/dnb_all_dnbmarc.4.mrc.gz data/dnb_all_dnbmarc.5.mrc.gz \
  --no-resume >>data/reingest.log 2>&1
log "DNB done -> Open Library re-ingest start (12GB, slow)"
uv run isbn-db ingest-openlibrary data/ol_dump_editions_latest.txt.gz --no-resume >>data/reingest.log 2>&1
log "OL done -> score"
uv run isbn-db score >>data/reingest.log 2>&1
log "score done -> refresh-aggregates"
uv run isbn-db refresh-aggregates >>data/reingest.log 2>&1
log "refresh done -> build-search-index (CONCURRENTLY)"
uv run isbn-db build-search-index >>data/reingest.log 2>&1
log "ALL DONE"
