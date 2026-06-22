#!/usr/bin/env bash
# Download the free Library of Congress "Books All 2016" MARC dataset (43 parts, ~10 GB) from the
# Internet Archive mirror. Resumable (curl -C -) with per-file .done markers; safe to re-run.
set -u
cd "$(dirname "$0")/.." || exit 1
mkdir -p data/loc
log(){ echo "[loc-fetch $(date -u +%FT%TZ)] $*" >>data/loc_fetch.log; }
BASE="https://archive.org/download/marc_loc_2016"

log "downloading 43 LoC parts (~10 GB)"
fail=0
for i in $(seq -w 1 43); do
  f="BooksAll.2016.part${i}.utf8"
  [ -f "data/loc/$f.done" ] && continue
  log "fetch $f"
  if curl -fsSL -C - --retry 6 --retry-delay 15 -A "Mozilla/5.0" "$BASE/$f" -o "data/loc/$f"; then
    touch "data/loc/$f.done"
  else
    log "FAILED $f"; fail=$((fail+1))
  fi
done
if [ "$fail" -eq 0 ]; then log "DOWNLOAD COMPLETE"; else log "DOWNLOAD INCOMPLETE ($fail failed)"; fi
