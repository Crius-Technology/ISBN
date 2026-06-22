"""MARC country code -> ISO 3166-1 alpha-2.

Both MARC 008/15-17 (DNB, LIBRIS) and Open Library's ``publish_country`` use the Library of Congress
MARC Country Codes, which include sub-national codes (US states, Canadian provinces, UK constituent
countries, Australian states). Those are rolled up to their parent sovereign ISO code so
``pub_country`` is a clean country dimension. Only high-confidence codes are mapped; unknown,
obsolete or uncertain codes return ``None`` (better a null than a wrong country).
"""

from __future__ import annotations

# US state + DC codes -> US (Puerto Rico keeps its own ISO code, added below).
_US = (  # noqa: SIM905
    "aku alu aru azu cau cou ctu dcu deu flu gau hiu iau idu ilu inu ksu kyu lau mau mdu meu miu "
    "mnu mou msu mtu nbu ncu ndu nhu nju nmu nvu nyu ohu oku oru pau riu scu sdu tnu txu utu vau "
    "vtu wau wiu wvu wyu xxu"
).split()
_CA = "abc bcc mbc nkc nfc nsc ntc nuc onc pic quc snc ykc xxc".split()  # noqa: SIM905
_GB = "enk stk wlk nik xxk".split()  # noqa: SIM905
_AU = "aca xna qea tma vra wea xoa xra at".split()  # noqa: SIM905

# Plain sovereign codes — only entries verified against the LoC MARC list. Tricky pairs:
# au=Austria (at=Australia) · is=Israel (ic=Iceland) · sw=Sweden (sz=Switzerland) ·
# cc=China (ch=Taiwan) · sa=South Africa · ci=Croatia · sl would be Sierra Leone, omitted.
_PLAIN: dict[str, str] = {
    "gw": "DE", "fr": "FR", "it": "IT", "sp": "ES", "ne": "NL", "be": "BE", "sz": "CH", "au": "AT",
    "sw": "SE", "dk": "DK", "no": "NO", "fi": "FI", "ic": "IS", "po": "PT", "gr": "GR", "ie": "IE",
    "pl": "PL", "hu": "HU", "lu": "LU", "rm": "RO", "bu": "BG", "al": "AL", "mm": "MT",
    "xr": "CZ", "xo": "SK", "rb": "RS", "bn": "BA", "ci": "HR", "xv": "SI", "er": "EE", "lv": "LV",
    "li": "LT", "un": "UA", "bw": "BY", "ru": "RU", "tu": "TR", "cy": "CY",
    "ja": "JP", "cc": "CN", "ch": "TW", "hk": "HK", "ko": "KR", "ii": "IN", "pk": "PK", "ce": "LK",
    "np": "NP", "th": "TH", "vm": "VN", "io": "ID", "my": "MY", "si": "SG", "ph": "PH", "af": "AF",
    "is": "IL", "ir": "IR", "iq": "IQ", "le": "LB", "sy": "SY", "ae": "AE",
    "mx": "MX", "bl": "BR", "ag": "AR", "cl": "CL", "pe": "PE", "ve": "VE", "cu": "CU", "nz": "NZ",
    "sa": "ZA",
}

MARC_TO_ISO2: dict[str, str] = {}
for _c in _US:
    MARC_TO_ISO2[_c] = "US"
for _c in _CA:
    MARC_TO_ISO2[_c] = "CA"
for _c in _GB:
    MARC_TO_ISO2[_c] = "GB"
for _c in _AU:
    MARC_TO_ISO2[_c] = "AU"
MARC_TO_ISO2.update(_PLAIN)
MARC_TO_ISO2["pru"] = "PR"  # Puerto Rico keeps its own ISO code


def to_iso2(code: str | None) -> str | None:
    """Map a MARC country code to an ISO 3166-1 alpha-2 code, or ``None`` if unknown/historical."""
    if not code:
        return None
    return MARC_TO_ISO2.get(code.strip().lower().rstrip("|"))
