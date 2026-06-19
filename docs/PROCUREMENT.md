# Paid Source Procurement

The free authoritative sources (Open Library, DNB, LIBRIS) are ingested automatically. The remaining
priority-market coverage requires **paid trade feeds**, which must be procured manually. The ingest
code is already built and tested — once a file is delivered, ingest is one command.

## 🇬🇧 UK — NielsenIQ BookData (priority)

The UK ISBN agency. The free alternative (British Library / BNB linked-data dumps) is currently
**offline** following the BL's cyberattack, so Nielsen is the realistic UK source.

**What to request** (matches our one-time-cost preference):
- Product: **NielsenIQ BookData — bulk metadata file**, UK + Ireland title coverage.
- Delivery: **one-off load** (not the annual subscription), as **ONIX 3.0** (reference tags).
  - Nielsen also offer their own flat format and ONIX 2.1 — ask for **ONIX 3.0** to match the ingester.
- Scope: full file, all in-print + recent out-of-print, with ISBN-13, title, contributors,
  publisher/imprint, publication date, language, BIC/Thema subjects, extent (page count), and
  (optionally) price.
- License: confirm the data may be **stored and analysed internally** (and redistribution terms if
  that ever matters).

**Contact:** `infobookresearch@nielseniq.com` — request a quote for a one-off bulk load.
**Expected cost:** quote-based; flagged earlier as fitting the few-k one-time budget for a one-off load.

**Once the file arrives:**
```bash
uv run isbn-db ingest-onix /path/to/nielsen_bookdata.onix.xml --source nielsen
```
Source `nielsen` is registered as Tier.REGISTRAR (markets GB), so it wins over Open Library on merge.

## 🇩🇪 DE — VLB / MVB (optional enrichment)

German Books-in-Print (~2.5M in-print). DNB (free, CC0) already gives authoritative German coverage,
so VLB is optional — useful for in-print status, price, and trade richness DNB lacks.
- Request an **ONIX 3.0** export from MVB (`mvb-online.com`).
- Ingest the same way: `uv run isbn-db ingest-onix /path/to/vlb.onix.xml --source vlb`
  (the `vlb` registry entry is Tier.REGISTRAR, markets DE/AT/CH).

## 🇳🇴 NO — Bokbasen (optional)

Norway has no open bulk source (National Library exposes only APIs/NORMARC). Bokbasen is the
commercial vendor. If pursued, request ONIX 3.0 and ingest with `--source bokbasen` (after adding a
`bokbasen` registry entry mapped to the ONIX path).

---
*The ONIX ingester (`src/isbn_db/ingest/onix.py`) is namespace-agnostic ONIX 3.0 reference-tag,
streaming and resumable, and unit-tested against sample products. It needs no changes to accept a
real Nielsen/VLB file — only the file itself.*
