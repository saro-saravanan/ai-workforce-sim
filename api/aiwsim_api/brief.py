"""Shareable brief export (Phase 4, contracts §16): Markdown or self-contained HTML, deterministic.

Every number in the brief is read from the results document; the narrative sentences come from
`explain.notes` and the deterministic insight candidates. An optional `narrative` (the chat
layer's reply, already grounded in tool results) is appended verbatim under its own heading and
labelled as model-written.
"""
from __future__ import annotations

import html
import json
from typing import Any

from aiwsim.data.regions import REGION_NAMES

from .insights import HEADLINE_LABELS, top_insights

ORDER = ["employment_pct_vs_baseline", "gdp_pct_vs_baseline", "real_wage_pct_vs_baseline", "wage_share_pp_vs_baseline"]


def _cell(series: dict[str, list[float]], t: int, unit: str) -> str:
    p50 = (series.get("p50") or series["central"])[t]
    if "p10" in series:
        return f"{p50:+.1f}{unit} [{series['p10'][t]:+.1f}, {series['p90'][t]:+.1f}]"
    return f"{p50:+.1f}{unit}"


def _count(v: float, unit: str, nd: int) -> str:
    """People in millions or thousands (a seven-digit count reads as false precision); other quantities as they are."""
    if unit or nd:
        return f"{v:,.{nd}f}{unit}"
    if abs(v) >= 1e6:
        return f"{v/1e6:.2f} million"
    if abs(v) >= 1e3:
        return f"{v/1e3:.0f} thousand"
    return f"{v:,.0f}"


def build_brief_md(doc: dict[str, Any], scenario: dict[str, Any] | None = None, region: str = "US",
                   narrative: str | None = None, compare: dict[str, Any] | None = None) -> str:
    m = doc["meta"]; q = m["quarters"]; t_end = len(q) - 1
    i30 = q.index("2030Q4") if "2030Q4" in q else t_end
    blk = doc["series"].get(region) or doc["series"]["US"]
    L: list[str] = []
    L.append(f"# {m.get('scenario_name') or m.get('scenario_id') or 'Scenario'} — AI workforce brief")
    L.append("")
    L.append(f"Region: **{region}**, {REGION_NAMES.get(region, region)} · Horizon: {q[0]}–{q[-1]} · Run: `{m['scenario_hash']}` · Spec {m['spec_version']} · Data {m['data_version']} · "
             f"{m['draws']} Monte Carlo draws, ensemble `{m['ensemble']}` · Generated {m['run_at']}")
    L.append("")
    L.append("All effects are relative to a frozen-AI counterfactual (no frontier AI after 2023). Brackets are the 10th–90th percentile across draws; "
             "the point value is the median draw.")
    L.append("")
    L.append("## Headline effects")
    L.append("")
    L.append(f"| Metric | {q[i30]} | {q[t_end]} | Sign confidence ({q[t_end]}) |")
    L.append("|---|---|---|---|")
    for k in ORDER:
        s = blk.get(k)
        if not s:
            continue
        unit = " pp" if k.endswith("_pp_vs_baseline") else "%"
        conf = (doc.get("confidence", {}).get(k, {}).get(q[t_end]) or {}).get("level", "n/a")
        L.append(f"| {HEADLINE_LABELS[k][0].upper() + HEADLINE_LABELS[k][1:]} | {_cell(s, i30, unit)} | {_cell(s, t_end, unit)} | {conf} |")
    for k, label, unit, nd in (("displaced_workers_cum", "Workers displaced (cumulative)", "", 0), ("unemployed_stock", "Unemployed above baseline", "", 0),
                               ("adoption_share", "Adoption (employment-weighted)", "%", 0), ("ai_spend_bn", "AI spend, $bn/yr", "", 0)):
        s = blk.get(k)
        if s:
            v30 = (s.get("p50") or s["central"])[i30]; v40 = (s.get("p50") or s["central"])[t_end]
            L.append(f"| {label} | {_count(v30, unit, nd)} | {_count(v40, unit, nd)} | |")
    L.append("")
    diff = doc.get("explain", {}).get("diff", [])
    L.append("## What changed vs the parent scenario")
    L.append("")
    if diff:
        L.append("| Lever | From | To | Mechanism |")
        L.append("|---|---|---|---|")
        for d in diff:
            L.append(f"| `{d['path']}` | {json.dumps(d.get('from'))} | {json.dumps(d.get('to'))} | {d.get('mechanism', '')} |")
    else:
        L.append("No lever differs from the parent (this is a baseline or preset run).")
    L.append("")
    if compare:
        L.append(f"## Paired comparison: {compare['a'].get('name') or compare['a']['hash']} → {compare['b'].get('name') or compare['b']['hash']}")
        L.append("")
        delta = compare.get("delta", {}).get("series", {})
        L.append(f"| Metric | Δ {q[i30]} | Δ {q[t_end]} |")
        L.append("|---|---|---|")
        for k in ORDER:
            s = delta.get(k)
            if s:
                unit = " pp"
                L.append(f"| {HEADLINE_LABELS[k][0].upper() + HEADLINE_LABELS[k][1:]} | {_cell(s, i30, unit)} | {_cell(s, t_end, unit)} |")
        L.append("")
        L.append(f"Paired over {compare.get('delta', {}).get('paired_draws', '?')} common draws (same seed), so the difference bands exclude shared parameter noise.")
        L.append("")
    L.append("## Findings")
    L.append("")
    for c in top_insights(doc, region, 3)["top"]:
        L.append(f"**{c['title']}.** {c['statement']}")
        L.append("")
        L.append(f"*Mechanism:* {c['mechanism']} *Confidence:* {c['confidence']}.")
        L.append("")
    L.append("## Model notes for this run")
    L.append("")
    L.append("The notes quote the central run (every parameter at its central value); the table above quotes the median draw, so the two differ by the skew of the parameter draws.")
    L.append("")
    for n in doc.get("explain", {}).get("notes", []):
        L.append(f"- {n}")
    L.append("")
    torn = doc.get("tornado", {}).get("employment_pct_vs_baseline", [])[:6]
    if torn:
        L.append(f"## What the {q[t_end]} employment effect is most sensitive to")
        L.append("")
        L.append("| Parameter | Range | Effect at low | Effect at high | Swing (pp) |")
        L.append("|---|---|---|---|---|")
        for r in torn:
            L.append(f"| {r['name']} ({r['param']}, {r['tag']}) | {r['low']}–{r['high']} | {r['effect_at_low']:+.1f}% | {r['effect_at_high']:+.1f}% | {r['swing']:.1f}{' ⚠ flips sign' if r.get('flips_sign') else ''} |")
        L.append("")
    regions = [x for x in m.get("regions", []) if x in doc["series"]]
    if len(regions) > 1:
        L.append(f"## Regions at {q[t_end]}")
        L.append("")
        L.append("| Region | Employment | GDP | Real wages | AI rents received, $bn | Net AI trade, $bn |")
        L.append("|---|---|---|---|---|---|")
        for x in regions:
            b = doc["series"][x]
            L.append(f"| {x} | {_cell(b['employment_pct_vs_baseline'], t_end, '%')} | {_cell(b['gdp_pct_vs_baseline'], t_end, '%')} | {_cell(b['real_wage_pct_vs_baseline'], t_end, '%')} | "
                     f"{(b['ai_rents_received_bn']['total'].get('p50') or b['ai_rents_received_bn']['total']['central'])[t_end]:,.0f} | "
                     f"{(b['net_ai_trade_bn'].get('p50') or b['net_ai_trade_bn']['central'])[t_end]:,.0f} |")
        L.append("")
    if narrative:
        L.append("## Narrative (model-written, grounded in the numbers above)")
        L.append("")
        L.append(narrative.strip())
        L.append("")
    L.append("## Method and provenance")
    L.append("")
    L.append(f"- Model specification v{m['spec_version']} (`docs/model-spec.md`): task exposure → capability and cost → adoption → labor flows → reduced-form macro, with a {m['draws']}-draw Monte Carlo and a {len(m.get('cells', []))}-cell structural ensemble.")
    L.append(f"- Capability units: {m.get('capability_units')}.")
    flags = m.get("data_flags", {})
    fixtures = [k for k, v in flags.items() if isinstance(v, str) and "FIXTURE" in v.upper()]
    if fixtures:
        L.append(f"- Data flagged as FIXTURE (structural placeholders pending ingestion): {', '.join(fixtures)}.")
    L.append(f"- Data version {m['data_version']}; run hash `{m['scenario_hash']}` reproduces this document from a clean clone with `aiwsim run`.")
    L.append("- Estimates labelled E in the parameter registry are the authors' judgement, not literature values; see `data/registry/params.yaml`.")
    L.append("")
    if scenario:
        L.append("## Appendix: scenario (canonical JSON)")
        L.append("")
        L.append("```json")
        L.append(json.dumps({k: v for k, v in scenario.items() if k not in ("created", "author")}, indent=2))
        L.append("```")
        L.append("")
    return "\n".join(L)


_CSS = """
body{font:15px/1.5 -apple-system,Segoe UI,Helvetica,Arial,sans-serif;max-width:900px;margin:32px auto;padding:0 20px;color:#1c1c1c;background:#fff}
h1{font-size:24px;margin:0 0 8px}h2{font-size:17px;margin:28px 0 8px;border-bottom:1px solid #ddd;padding-bottom:4px}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:8px 0}th,td{border:1px solid #e3e3e3;padding:5px 8px;text-align:left;vertical-align:top}
th{background:#f5f5f5}code{font:12.5px ui-monospace,Menlo,Consolas,monospace;background:#f3f3f3;padding:1px 4px;border-radius:3px}
pre{background:#f7f7f7;padding:12px;overflow:auto;font-size:12px;border-radius:6px}em{color:#555}
@media (prefers-color-scheme: dark){body{background:#151618;color:#e6e6e6}th{background:#222}td,th{border-color:#333}code,pre{background:#202225}em{color:#aaa}}
@media print{body{margin:0;max-width:none}}
"""


def md_to_html(md: str) -> str:
    """Small Markdown subset renderer (headings, paragraphs, tables, lists, code fences, bold/italic/code)."""
    import re

    def inline(s: str) -> str:
        s = html.escape(s, quote=False)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        return s

    out: list[str] = []
    lines = md.split("\n"); i = 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            j = i + 1; buf = []
            while j < len(lines) and not lines[j].startswith("```"):
                buf.append(lines[j]); j += 1
            out.append("<pre>" + html.escape("\n".join(buf)) + "</pre>"); i = j + 1; continue
        if ln.startswith("# "):
            out.append(f"<h1>{inline(ln[2:])}</h1>")
        elif ln.startswith("## "):
            out.append(f"<h2>{inline(ln[3:])}</h2>")
        elif ln.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")]); i += 1
            body = [r for r in rows if not all(set(c) <= set("-: ") for c in r)]
            if body:
                out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in body[0]) + "</tr></thead><tbody>"
                           + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body[1:]) + "</tbody></table>")
            continue
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def build_brief_html(md: str, title: str) -> str:
    return (f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title><style>{_CSS}</style></head><body>{_collapse_appendix(md_to_html(md))}</body></html>")


def _collapse_appendix(body: str) -> str:
    """The scenario JSON appendix folds behind a summary line so the page ends with the findings, not a wall of JSON."""
    marker = "<h2>Appendix: scenario (canonical JSON)</h2>"
    i = body.find(marker)
    if i < 0:
        return body
    return body[:i] + "<details><summary>Appendix: scenario (canonical JSON)</summary>" + body[i + len(marker):] + "</details>"
