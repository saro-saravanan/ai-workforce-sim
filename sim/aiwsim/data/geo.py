"""U.S. states GeoJSON from Natural Earth 1:110m admin-1 (public domain)."""

from __future__ import annotations

import json
from pathlib import Path


def build_us_states(raw_path: Path) -> dict:
    """Keep the 51 U.S. features; reduce properties to {fips, name, abbrev}."""
    src = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    feats = []
    for f in src["features"]:
        p = f["properties"]
        if p.get("iso_a2") != "US" and p.get("adm0_a3") != "USA":
            continue
        fips_raw = p.get("fips") or ""
        if fips_raw.startswith("US") and len(fips_raw) == 4:
            fips = fips_raw[2:]
        else:  # fall back to iso_3166_2 (US-MN) -> needs a postal->fips table; we only have fips here
            raise ValueError(f"no usable fips for {p.get('name')}: {fips_raw!r} / {p.get('iso_3166_2')!r}")
        feats.append({
            "type": "Feature",
            "properties": {"fips": fips, "name": p["name"], "abbrev": p["postal"]},
            "geometry": f["geometry"],
        })
    feats.sort(key=lambda f: f["properties"]["fips"])
    if len(feats) != 51:
        raise ValueError(f"expected 51 U.S. features, got {len(feats)}")
    return {"type": "FeatureCollection", "name": "us_states_110m", "features": feats}
