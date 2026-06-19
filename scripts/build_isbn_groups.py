#!/usr/bin/env python3
"""Regenerate src/isbn_db/data/isbn_groups.json from the official ISBN RangeMessage.

The mapping (registration-group prefix -> country/language area) comes from the International ISBN
Agency. Run this to refresh it:

    curl -s https://www.isbn-international.org/export_rangemessage.xml -o data/RangeMessage.xml
    uv run python scripts/build_isbn_groups.py
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SRC = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/RangeMessage.xml")
OUT = Path("src/isbn_db/data/isbn_groups.json")


def main() -> int:
    root = ET.parse(SRC).getroot()
    groups: dict[str, str] = {}
    for group in root.findall(".//RegistrationGroups/Group"):
        prefix = (group.findtext("Prefix") or "").strip()  # e.g. "978-91"
        agency = (group.findtext("Agency") or "").strip()  # e.g. "Sweden"
        if prefix and agency:
            groups[prefix.replace("-", "")] = agency  # "97891" -> "Sweden"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(groups, ensure_ascii=False, sort_keys=True, indent=0), encoding="utf-8")
    print(f"wrote {OUT} with {len(groups)} groups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
