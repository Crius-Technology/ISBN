#!/usr/bin/env bash
# Download Open Library + DNB dumps and ingest them fully into Postgres.
#
# Robust against dropped connections: each download is retried with `curl -C -` (resume) until the
# local file size matches the server's Content-Length, and ONLY THEN is a `.done` marker written.
# Ingest never runs on a partial file — a download that cannot be completed aborts the run.
set -uo pipefail

cd "$(dirname "$0")/.."
DATA="${ISBN_DATA_DIR:-data}"
mkdir -p "$DATA"
LOG="$DATA/ingest.log"
MAX_ATTEMPTS=40

say() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$LOG"; }

remote_size() { # url -> bytes (via HEAD, following redirects)
  curl -sIL --connect-timeout 30 "$1" 2>/dev/null \
    | awk 'BEGIN{IGNORECASE=1}/^content-length:/{n=$2}END{gsub(/\r/,"",n);print n}'
}

local_size() { [ -f "$1" ] && stat -c%s "$1" || echo 0; }

dl() { # url dest  -> 0 on verified-complete download
  local url="$1" dest="$2" want have attempt
  if [ -f "$dest.done" ]; then say "download cached: $(basename "$dest")"; return 0; fi
  want=$(remote_size "$url")
  say "download $(basename "$dest"): server reports want=${want:-unknown} bytes"
  for attempt in $(seq 1 "$MAX_ATTEMPTS"); do
    have=$(local_size "$dest")
    if [ -n "$want" ] && [ "$have" = "$want" ]; then
      touch "$dest.done"; say "download complete: $(basename "$dest") ($have bytes)"; return 0
    fi
    say "attempt $attempt/$MAX_ATTEMPTS: have=$have want=${want:-?} — (re)starting curl -C -"
    curl -fSL -C - --retry 5 --retry-delay 10 --connect-timeout 30 "$url" -o "$dest" 2>>"$LOG" || true
    sleep 3
  done
  have=$(local_size "$dest")
  if [ -n "$want" ] && [ "$have" = "$want" ]; then touch "$dest.done"; return 0; fi
  say "DOWNLOAD FAILED: $(basename "$dest") have=$have want=${want:-?}"; return 1
}

ingest_ol() { uv run isbn-db ingest-openlibrary "$1" 2>&1 | tee -a "$LOG"; }
ingest_dnb() { uv run isbn-db ingest-dnb "$1" 2>&1 | tee -a "$LOG"; }

say "=== START full ingest ==="
uv run isbn-db init-db | tee -a "$LOG"

# --- Open Library editions (largest; ingest first) ---
OL="$DATA/ol_dump_editions_latest.txt.gz"
dl "https://openlibrary.org/data/ol_dump_editions_latest.txt.gz" "$OL" || { say "ABORT: OL download incomplete"; exit 1; }
say "ingesting Open Library editions"
ingest_ol "$OL"

# --- DNB MARC (5 files) ---
for n in 1 2 3 4 5; do
  F="$DATA/dnb_all_dnbmarc.$n.mrc.gz"
  dl "https://data.dnb.de/DNB/dnb_all_dnbmarc.$n.mrc.gz" "$F" || { say "ABORT: DNB file $n download incomplete"; exit 1; }
  say "ingesting DNB file $n"
  ingest_dnb "$F"
done

say "=== DONE full ingest ==="
uv run isbn-db stats 2>&1 | tee -a "$LOG"
say "=== STATS COMPLETE ==="
