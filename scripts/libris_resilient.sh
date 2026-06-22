#!/usr/bin/env bash
# Self-resuming LIBRIS harvest.
#
# The LIBRIS OAI-PMH endpoint is slow (~5-8 records/sec) and occasionally drops the
# connection (SSL read timeout) mid-harvest. The harvest is checkpointed and resumable
# (completed chunks are skipped, mid-chunk resumptionToken is persisted in ingest_state),
# so this wrapper simply re-runs `ingest-libris` whenever it exits non-zero, picking up
# from the last checkpoint, until it completes cleanly.
#
# Usage:  nohup setsid scripts/libris_resilient.sh >/dev/null 2>&1 &
# Logs append to data/libris.log.
set -u
cd "$(dirname "$0")/.." || exit 1

for i in $(seq 1 500); do
  echo "[resilient $(date -u +%Y-%m-%dT%H:%M:%SZ)] attempt $i starting" >>data/libris.log
  if uv run isbn-db ingest-libris >>data/libris.log 2>&1; then
    echo "[resilient] harvest completed cleanly after $i attempt(s)" >>data/libris.log
    break
  fi
  echo "[resilient] attempt $i exited non-zero; resuming in 30s" >>data/libris.log
  sleep 30
done
