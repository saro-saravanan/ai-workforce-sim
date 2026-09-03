"""aiwsim command line: run, calibrate, data build/status, validate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import SPEC_VERSION


def find_root(start: Path | None = None) -> Path:
    p = (start or Path.cwd()).resolve()
    for cand in (p, *p.parents):
        if (cand / "scenarios" / "schema.json").exists():
            return cand
    raise SystemExit("repository root not found (no scenarios/schema.json above cwd)")


def cmd_run(args: argparse.Namespace) -> int:
    from .pipeline import Context, load_scenario_by_path_or_id, run_scenario
    root = find_root()
    ctx = Context(root)
    scen = load_scenario_by_path_or_id(ctx, args.scenario)
    doc, raw = run_scenario(ctx, scen, draws=args.draws, ensemble=args.ensemble, with_channels=not args.no_channels,
                            with_tornado=not args.no_tornado, workers=args.workers)
    out = Path(args.out) if args.out else root / "data" / "cache" / f"{scen['id']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, separators=(",", ":")))
    np.savez_compressed(out.with_suffix(".npz"), **raw)
    m = doc["meta"]; q = m["quarters"]; s = doc["series"]["US"]
    print(f"scenario {scen['id']} hash {m['scenario_hash']} draws {m['draws']} ensemble {m['ensemble']} timing {m['timing_s']} -> {out}")

    def band(name: str, i: int, unit: str = "%") -> str:
        x = s[name]
        if "p10" in x:
            return f"{x['central'][i]:+6.2f}{unit} [{x['p10'][i]:+6.2f}, {x['p90'][i]:+6.2f}]"
        return f"{x['central'][i]:+6.2f}{unit}"
    for i in (q.index("2027Q4"), q.index("2030Q4"), q.index("2035Q4"), len(q) - 1):
        print(f"  {q[i]}: horizon {s['capability_horizon_hours']['central'][i]:8.1f}h  adopt {s['adoption_share']['central'][i]:5.1f}%  "
              f"emp {band('employment_pct_vs_baseline', i)}  realw {band('real_wage_pct_vs_baseline', i)}  gdp {band('gdp_pct_vs_baseline', i)}  "
              f"wshare {band('wage_share_pp_vs_baseline', i, 'pp')}")
    for n in doc["explain"]["notes"]:
        print("  -", n)
    if doc.get("tornado"):
        print("  tornado (employment 2040):", ", ".join(f"{r['param']} {r['swing']:.2f}" for r in doc["tornado"]["employment_pct_vs_baseline"][:6]))
    return 0


def cmd_calibrate(args: argparse.Namespace) -> int:
    from .calibrate import fit, write_fitted
    root = find_root()
    from .pipeline import Context, load_scenario_by_path_or_id
    ctx = Context(root)
    scen = load_scenario_by_path_or_id(ctx, "baseline")
    fitted = fit(ctx.inputs, ctx.params_for(scen), scen)
    out = write_fitted(root, fitted)
    print(json.dumps(fitted, indent=2)); print("->", out)
    return 0


def cmd_data(args: argparse.Namespace) -> int:
    root = find_root()
    from .data import build as data_build
    from .data import fetch as data_fetch
    if args.action == "fetch":
        data_fetch.fetch_all(root, force=args.force)
    elif args.action == "build":
        if not args.no_fetch and data_fetch.missing(root):
            print("raw inputs missing or stale; fetching pinned sources (aiwsim data fetch)")
            data_fetch.fetch_all(root)
        status = data_build.build_all(root)
        for k, v in status.items():
            print(f"  {k:28s} {v}")
    else:
        data_build.status(root)
    return 0


def cmd_diag(args: argparse.Namespace) -> int:
    """Phase 9 diagnostics (review §2.4): threshold-seed sensitivity and the classifier audit sample."""
    from .diagnostics import classifier_sample, seed_table, threshold_seed_sensitivity
    root = find_root()
    if args.action == "threshold-seeds":
        from .pipeline import Context
        ctx = Context(root)
        rows = threshold_seed_sensitivity(ctx, seeds=tuple(int(s) for s in args.seeds.split(",")), regions=tuple(args.regions.split(",")), scenario=args.scenario)
        print(seed_table(rows))
    else:
        out = Path(args.out) if args.out else root / "docs" / "classifier-audit-sample.md"
        classifier_sample(root, n=args.n, seed=args.seed, out=out)
        print(f"-> {out}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    import pytest
    root = find_root()
    return pytest.main(["-q", str(root / "sim" / "tests")])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aiwsim", description=f"AI workforce impact simulation (spec v{SPEC_VERSION})")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("--scenario", required=True, help="scenario id or path"); r.add_argument("--out")
    r.add_argument("--draws", type=int, default=None, help="Monte Carlo draws (default: scenario's, 200)")
    r.add_argument("--ensemble", choices=["all", "central"], default=None); r.add_argument("--workers", type=int, default=None)
    r.add_argument("--no-channels", action="store_true"); r.add_argument("--no-tornado", action="store_true"); r.set_defaults(fn=cmd_run)
    c = sub.add_parser("calibrate"); c.set_defaults(fn=cmd_calibrate)
    d = sub.add_parser("data"); d.add_argument("action", choices=["fetch", "build", "status"])
    d.add_argument("--force", action="store_true", help="fetch: re-download every raw file"); d.add_argument("--no-fetch", action="store_true", help="build: fail instead of fetching missing raw inputs")
    d.set_defaults(fn=cmd_data)
    v = sub.add_parser("validate"); v.set_defaults(fn=cmd_validate)
    g = sub.add_parser("diag", help="Phase 9 diagnostics: threshold-seeds (markdown table), classifier-sample (audit table)")
    g.add_argument("action", choices=["threshold-seeds", "classifier-sample"])
    g.add_argument("--seeds", default="0,1,2", help="threshold-seeds: comma-separated seeds (0 = reference hash)")
    g.add_argument("--regions", default="US", help="threshold-seeds: comma-separated regions to run"); g.add_argument("--scenario", default="baseline")
    g.add_argument("--n", type=int, default=120, help="classifier-sample: statements to sample, stratified by channel")
    g.add_argument("--seed", type=int, default=20260903, help="classifier-sample: sampling seed"); g.add_argument("--out", help="classifier-sample: output markdown path")
    g.set_defaults(fn=cmd_diag)
    args = ap.parse_args(argv)
    return int(args.fn(args))


if __name__ == "__main__":
    sys.exit(main())
