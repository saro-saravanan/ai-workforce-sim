"""aiwsim command line: run, calibrate, data build/status, validate."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

from . import SPEC_VERSION
from .engine import channel_decomposition, run_central
from .inputs import load_inputs
from .params import apply_levers, apply_overrides, central_params
from .results import build_results
from .scenario import load_scenario_file, resolve, scenario_hash, validate


def find_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for cand in (p, *p.parents):
        if (cand / "scenarios" / "schema.json").exists():
            return cand
    raise SystemExit("repository root not found (no scenarios/schema.json above cwd)")


def prepare(root: Path, scenario_path: Path):
    inp = load_inputs(root)
    raw = load_scenario_file(scenario_path)
    scen = resolve(raw, root / "scenarios")
    validate(scen, root / "scenarios" / "schema.json")
    p = central_params(root / "data" / "processed" / "params" / "registry.yaml")
    p = apply_levers(p, scen.get("levers", {}))
    p = apply_overrides(p, scen.get("overrides", {}))
    return inp, scen, p


def cmd_run(args: argparse.Namespace) -> int:
    root = find_root()
    t0 = time.perf_counter()
    inp, scen, p = prepare(root, Path(args.scenario))
    shash = scenario_hash(scen, SPEC_VERSION, inp.data_version)
    r = run_central(inp, p, scen)
    t1 = time.perf_counter()
    channels = None if args.no_channels else channel_decomposition(inp, p, scen, r)
    doc = build_results(inp, r, scen, shash, channels)
    doc["meta"]["timing_s"] = {"central": round(t1 - t0, 3), "total": round(time.perf_counter() - t0, 3)}
    out = Path(args.out) if args.out else root / "data" / "cache" / f"{scen['id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")))
    q = r.quarters
    print(f"scenario {scen['id']} hash {shash}  data {inp.data_version}  central {t1-t0:.2f}s  -> {out}")
    for i in (q.index("2027Q4"), q.index("2030Q4"), q.index("2035Q4"), len(q) - 1):
        print(f"  {q[i]}: horizon {r.horizon_hours[i]:8.1f}h  adopt(emp) {100*r.adoption_emp[i]:5.1f}%  emp {100*r.employment_pct[i]:+6.2f}%  "
              f"realw {100*r.real_wage_pct[i]:+6.2f}%  gdp {100*r.gdp_pct[i]:+6.2f}%  tfp {100*r.tfp_pct[i]:+5.2f}%  "
              f"wshare {r.wage_share_pp[i]:+5.2f}pp  displaced {r.displaced_cum[i]/1e6:5.2f}M")
    if args.diag:
        Dw = (r.D * r.N0).sum(axis=0) / r.N0.sum(axis=0); Uw = (r.U * r.N0).sum(axis=0) / r.N0.sum(axis=0)
        print("  year   C   D(emp-w)  U(emp-w)  Q/Q0    mu     XS    emp%   nomw%  P%   tfp%  gdp%")
        for i in range(0, len(q), 4):
            print(f"  {q[i][:4]}  {r.C[i]:5.1f}  {Dw[i]:7.3f}  {Uw[i]:7.3f}  {r.q_ratio[i]:6.3f} {r.mu[i]:+6.3f} {r.xs[i]:6.3f} "
                  f"{100*r.employment_pct[i]:+6.1f} {100*r.nominal_wage_pct[i]:+6.1f} {100*(np.exp(r.ln_P[i])-1):+5.1f} {100*r.tfp_pct[i]:+5.1f} {100*r.gdp_pct[i]:+6.1f}")
    for n in doc["explain"]["notes"]:
        print("  -", n)
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from .calibrate import fit, write_fitted
    root = find_root()
    inp, scen, p = prepare(root, root / "scenarios" / "baseline.json")
    fitted = fit(inp, p, scen)
    out = write_fitted(root, fitted)
    print(json.dumps(fitted, indent=2)); print("->", out)
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    root = find_root()
    from .data import build as data_build
    if args.action == "build":
        status = data_build.build_all(root)
        for k, v in status.items():
            print(f"  {k:28s} {v}")
    else:
        data_build.status(root)
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    import pytest
    root = find_root()
    return pytest.main(["-q", str(root / "sim" / "tests")])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aiwsim", description=f"AI workforce impact simulation (spec v{SPEC_VERSION})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--scenario", required=True); r.add_argument("--out"); r.add_argument("--seed", type=int, default=42)
    r.add_argument("--no-channels", action="store_true"); r.add_argument("--diag", action="store_true"); r.set_defaults(fn=cmd_run)
    c = sub.add_parser("calibrate"); c.set_defaults(fn=cmd_calibrate)
    d = sub.add_parser("data"); d.add_argument("action", choices=["build", "status"]); d.set_defaults(fn=cmd_data)
    v = sub.add_parser("validate"); v.set_defaults(fn=cmd_validate)
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
