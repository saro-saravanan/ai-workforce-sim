"""Static export for the serverless demo (contracts §18).

Runs the listed scenarios (cached by hash like the API), then writes every document the web app
reads in static mode: run documents, paired compares against the first scenario, insight files,
briefs, lever catalogue, regions, actors, geo, and a manifest.

    uv run python -m aiwsim_api.export_static --out web/public/static --draws 200
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import time
from pathlib import Path
from typing import Any

from aiwsim import SPEC_VERSION

from . import service
from .brief import build_brief_html, build_brief_md
from .insights import top_insights
from .levers import lever_definitions

DEFAULT_SCENARIOS = ["baseline", "eu-delay-deepseek-2027", "preset-acemoglu-2024", "preset-goldman-2023", "preset-imf-2024"]


def _dump(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":")))


def _slim(doc: dict[str, Any]) -> dict[str, Any]:
    d = dict(doc); d["meta"] = {**doc["meta"], "static": True}
    d["occupations"] = [{k: v for k, v in o.items() if k != "by_region"} for o in doc["occupations"]]
    return d


def export(out: Path, scenario_ids: list[str], draws: int | None, log=print) -> dict[str, Any]:
    out.mkdir(parents=True, exist_ok=True)
    runs: list[dict[str, Any]] = []
    docs: dict[str, dict[str, Any]] = {}
    hashes: dict[str, str] = {}
    raw_scenarios: list[dict[str, Any]] = []
    for sid in scenario_ids:
        t0 = time.time()
        raw = service.find_scenario(sid)
        raw_scenarios.append(raw)
        h, doc = service.run_or_load(raw, draws=draws)
        docs[sid] = doc; hashes[sid] = h
        _dump(out / "runs" / f"{sid}.json", _slim(doc))
        runs.append({"id": sid, "name": doc["meta"].get("scenario_name"), "parent": raw.get("parent"), "description": raw.get("description", ""),
                     "preset": bool(raw.get("preset", False)), "hash": h, "draws": doc["meta"]["draws"], "ensemble": doc["meta"]["ensemble"], "file": f"runs/{sid}.json"})
        log(f"run {sid} → {h} ({time.time() - t0:.1f}s)")
    _dump(out / "scenarios.json", raw_scenarios)
    ref = scenario_ids[0]
    compares: list[dict[str, str]] = []
    insights: dict[str, str] = {}
    briefs: dict[str, dict[str, str]] = {}
    for sid in scenario_ids:
        doc = docs[sid]; h = hashes[sid]
        _dump(out / "insights" / f"{sid}.json", top_insights(doc, "US", 10)); insights[sid] = f"insights/{sid}.json"
        cmp = None
        if sid != ref:
            cmp = service.compare(hashes[ref], h)
            _dump(out / "compare" / f"{ref}__{sid}.json", cmp); compares.append({"a": ref, "b": sid, "file": f"compare/{ref}__{sid}.json"})
            _dump(out / "insights" / f"{sid}__vs__{ref}.json", top_insights(doc, "US", 10, compare=cmp)); insights[f"{sid}__vs__{ref}"] = f"insights/{sid}__vs__{ref}.json"
        md = build_brief_md(doc, service.scenario_of(doc), "US", compare=cmp)
        (out / "briefs").mkdir(exist_ok=True)
        (out / "briefs" / f"{sid}.md").write_text(md)
        (out / "briefs" / f"{sid}.html").write_text(build_brief_html(md, f"{doc['meta'].get('scenario_name') or sid} — brief"))
        briefs[sid] = {"md": f"briefs/{sid}.md", "html": f"briefs/{sid}.html"}
    _dump(out / "levers.json", lever_definitions())
    from .app import actors, regions
    _dump(out / "regions.json", regions()); _dump(out / "actors.json", actors())
    geo = {}
    for name, src in (("us_states", "us_states.geojson"), ("world", "world.geojson")):
        f = service.ROOT / "data" / "processed" / "geo" / src
        if f.exists():
            (out / "geo").mkdir(exist_ok=True)
            shutil.copy(f, out / "geo" / src.replace("_", "-")); geo[name] = f"geo/{src.replace('_', '-')}"
    c = service.ctx()
    manifest = {"generated_at": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"), "spec_version": SPEC_VERSION, "data_version": c.inputs.data_version,
                "draws": draws, "runs": runs, "compares": compares, "levers": "levers.json", "scenarios": "scenarios.json", "regions": "regions.json",
                "actors": "actors.json", "geo": geo, "insights": insights, "briefs": briefs}
    _dump(out / "manifest.json", manifest)
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1))
    log(f"wrote {sum(1 for _ in out.rglob('*') if _.is_file())} files to {out}")
    return manifest


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=str(service.ROOT / "web" / "public" / "static"))
    ap.add_argument("--draws", type=int, default=200)
    ap.add_argument("--scenarios", default=",".join(DEFAULT_SCENARIOS), help="comma-separated scenario ids; the first is the comparison reference")
    a = ap.parse_args(argv)
    export(Path(a.out), [s for s in a.scenarios.split(",") if s], a.draws)


if __name__ == "__main__":
    main()
