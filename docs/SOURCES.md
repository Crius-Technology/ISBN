---
title: "ISBN / Book-Metadata Sources"
type: reference
status: draft
author: "Crius Technology"
sidebar_label: Sources
sidebar_position: 4
tags:
  - isbn
  - sources
---

# ISBN / Book-Metadata Sources

Research catalogue of where to obtain valid ISBN data for building this database. Structured form
lives in [`src/isbn_db/sources.py`](../src/isbn_db/sources.py). Priority markets: **UK & Germany**,
then **US**, then **Norway & Sweden**. Preference for **one-time** acquisitions; quality over cost.

## Quality tiers (merge priority, high → low)

1. **Registrar / trade feed** — official ISBN agencies, publisher-submitted. Most authoritative.
2. **National library** — curated cataloguing, authoritative per country.
3. **Aggregator** — scraped/compiled (broad but noisier).
4. **Crowd-sourced** — volunteer-edited (broad, uneven completeness).

## Per-market recommendations

### 🇩🇪 Germany
| Source | Tier | Cost | License | Notes |
|--------|------|------|---------|-------|
| **DNB (Deutsche Nationalbibliothek)** | National | **Free** | **CC0** | Bulk MARC21/RDF/CSV + OAI-PMH. Best free German backbone, redistributable. |
| **VLB / MVB** | Registrar | Paid (one-off load) | License | German Books-in-Print: ~2.5M in-print + 3.6M archived, ONIX. Trade richness (price/availability). |

### 🇬🇧 UK
| Source | Tier | Cost | License | Notes |
|--------|------|------|---------|-------|
| **NielsenIQ BookData** | Registrar | Paid (**one-off load available**) | License | UK ISBN agency, 51M+ records, daily-updated. `infobookresearch@nielseniq.com`. |
| **British Library / BNB** | National | Free | Open | British National Bibliography as open/linked data. |

### 🇺🇸 US
| Source | Tier | Cost | License | Notes |
|--------|------|------|---------|-------|
| **Library of Congress** | National | Free | Open (R&D) | ~25M+ MARC records, bulk download. |
| **Bowker Books In Print** | Registrar | Enterprise | License | US/AU ISBN agency, 40M+ titles, gold standard. Use only if budget allows. |

### 🇸🇪 Sweden / 🇳🇴 Norway
| Source | Tier | Cost | License | Notes |
|--------|------|------|---------|-------|
| **LIBRIS (Nat. Lib. Sweden, data.kb.se)** | National | Free | Open | Bulk raw-data download. |
| **Nasjonalbiblioteket (NO)** | National | Free | Open | Metadata + DHLAB APIs. |
| **Bokbasen (NO)** | Registrar | Paid | License | Primary Norwegian commercial vendor. |

## Cross-market breadth & gap-fill
| Source | Tier | Cost | License | Role |
|--------|------|------|---------|------|
| **Open Library dumps** | Crowd | Free | **Public domain** | Global backbone, ~20M editions, monthly JSON/TSV. ~93% English coverage. |
| **ISBNdb** | Aggregator | Cheap ($10–300/mo or bulk export) | License | ~110M titles, 19 fields incl. **retail prices**. Best cheap gap-fill. |
| **Anna's Archive all-ISBNs** | Aggregator | Free torrents | ⚠️ grey area | Largest open list of *all known ISBNs*. **Gap analysis only**, not for redistribution. |
| **Google Books API** | Aggregator | Free | ⚠️ no redistribution | Rich descriptions/covers but ~36% records had metadata errors. **Enrichment only**. |
| **WorldCat / OCLC** | National | Free basic / paid | Restrictive | Largest union catalogue; reference/spot-check only. |

## Licensing summary
- **Redistributable in a product**: DNB (CC0), Open Library (public domain), LoC, LIBRIS, BL — plus
  any paid feed per its license (Nielsen/VLB/Bowker/ISBNdb).
- **Internal / enrichment only**: Google Books, WorldCat, Anna's Archive.
- Free sources are strong for English (~80–93%) but weaker on non-English — national-library dumps
  are what lift DE/NO/SE quality.

## Recommended acquisition order
1. **Free authoritative backbone (€0):** DNB + Open Library + LoC + LIBRIS + BL + Nasjonalbiblioteket.
2. **Targeted paid one-offs:** Nielsen (UK one-off load), VLB (DE), ISBNdb bulk export — within the
   few-k budget.
3. **Reference-only:** Anna's Archive (gap analysis), Google Books (field enrichment).
