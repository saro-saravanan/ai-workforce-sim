"""Scenario loading, inheritance, canonicalization, and hashing (spec §8.1)."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

SCHEMA_VERSION = "0.3"


def _deep_merge(base: dict, child: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in child.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_scenario_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def find_scenario(scen_dir: Path, sid: str) -> dict[str, Any]:
    for f in sorted(scen_dir.glob("*.json")):
        if f.name == "schema.json":
            continue
        d = load_scenario_file(f)
        if d.get("id") == sid:
            return d
    raise FileNotFoundError(f"scenario {sid!r} not found in {scen_dir}")


def resolve(scenario: dict[str, Any], scen_dir: Path, _depth: int = 0) -> dict[str, Any]:
    """Resolve inheritance: deep-merge levers/ensemble/overrides; shocks keyed by id; remove_shocks."""
    if _depth > 10:
        raise ValueError("scenario inheritance too deep (cycle?)")
    parent_id = scenario.get("parent")
    if parent_id is None:
        merged = copy.deepcopy(scenario)
    else:
        parent = resolve(find_scenario(scen_dir, parent_id), scen_dir, _depth + 1)
        merged = copy.deepcopy(parent)
        for key in ("id", "name", "description", "author", "created", "seed", "draws"):
            if key in scenario:
                merged[key] = scenario[key]
        merged["parent"] = parent_id
        for key in ("levers", "overrides", "ensemble", "horizon"):
            merged[key] = _deep_merge(parent.get(key, {}), scenario.get(key, {}))
        shocks = {s["id"]: s for s in parent.get("shocks", [])}
        for s in scenario.get("shocks", []):
            shocks[s["id"]] = s
        for rid in scenario.get("remove_shocks", []):
            shocks.pop(rid, None)
        merged["shocks"] = [shocks[k] for k in sorted(shocks)]
        merged.pop("remove_shocks", None)
    merged.setdefault("levers", {})
    merged.setdefault("overrides", {})
    merged.setdefault("shocks", [])
    merged.setdefault("ensemble", {"mechanisms": "all", "shapley": False})
    merged.setdefault("seed", 42)
    merged.setdefault("draws", 256)
    merged.setdefault("horizon", {"start": "2024Q1", "end": "2040Q4"})
    return merged


def canonical_json(scenario: dict[str, Any]) -> str:
    body = {k: v for k, v in scenario.items() if k not in ("created", "author", "description")}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def scenario_hash(scenario: dict[str, Any], spec_version: str, data_version: str) -> str:
    h = hashlib.sha256()
    h.update(canonical_json(scenario).encode())
    h.update(f"|spec={spec_version}|data={data_version}".encode())
    return "sha256:" + h.hexdigest()[:24]


def validate(scenario: dict[str, Any], schema_path: Path) -> None:
    schema = json.loads(schema_path.read_text())
    jsonschema.Draft202012Validator(schema).validate(scenario)


def diff(a: dict[str, Any], b: dict[str, Any], prefix: str = "") -> list[dict[str, Any]]:
    """Flat diff of two canonical scenarios: list of {path, from, to}."""
    out: list[dict[str, Any]] = []
    keys = set(a) | set(b)
    for k in sorted(keys):
        pa, pb = a.get(k), b.get(k)
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(pa, dict) and isinstance(pb, dict):
            out.extend(diff(pa, pb, path))
        elif pa != pb:
            out.append({"path": path, "from": pa, "to": pb})
    return out


def quarters(start: str, end: str) -> list[str]:
    def parse(q: str) -> tuple[int, int]:
        return int(q[:4]), int(q[-1])
    y, qq = parse(start)
    ye, qe = parse(end)
    out = []
    while (y, qq) <= (ye, qe):
        out.append(f"{y}Q{qq}")
        qq += 1
        if qq == 5:
            qq = 1
            y += 1
    return out
