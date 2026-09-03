"""Classifier audit (Phase 9b): score the channel rules against the reviewer labels of the 120-statement sample."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .data.classify import CHANNELS, classify_text


def audit_agreement(root: Path, sample: Path | None = None, labels: Path | None = None) -> dict[str, Any]:
    sample = sample or root / "docs" / "classifier-audit-sample.md"
    labels = labels or root / "docs" / "classifier-audit-labels.csv"
    lab = {int(a): b.strip() for a, b in (l.split(",") for l in labels.read_text().splitlines()[1:] if l.strip())}
    rows = []
    for line in sample.read_text().splitlines():
        m = re.match(r"^\| (\d+) \| (\S+) ([^|]*)\| (.*?) \| (\S+) \| (\S+) \|$", line)
        if not m:
            continue
        k = int(m.group(1)); occ = m.group(2); text = m.group(4); assigned = m.group(5)
        rows.append({"row": k, "occ_code": occ, "text": text, "assigned_v2": assigned, "label": lab.get(k), "assigned_now": classify_text(text, occ)["channel"]})
    out: dict[str, Any] = {"n": len(rows), "rows": rows}
    for key in ("assigned_v2", "assigned_now"):
        agree = sum(r[key] == r["label"] for r in rows)
        by = {}
        for c in CHANNELS:
            rs = [r for r in rows if r[key] == c]
            ls = [r for r in rows if r["label"] == c]
            by[c] = {"assigned": len(rs), "precision": (sum(r["label"] == c for r in rs) / len(rs)) if rs else None,
                     "labelled": len(ls), "recall": (sum(r[key] == c for r in ls) / len(ls)) if ls else None}
        out[key] = {"agreement": agree / max(len(rows), 1), "by_channel": by}
    return out


def audit_markdown(res: dict[str, Any]) -> str:
    L = ["# Classifier audit: rules against the reviewer labels", "",
         f"{res['n']} statements (`docs/classifier-audit-sample.md`, labels in `docs/classifier-audit-labels.csv`). Precision: share of the statements the rules put on a channel that the reviewer put there too; recall: share of the reviewer's statements for a channel that the rules found.", ""]
    for key, name in (("assigned_v2", "rules v2 (Phase 9)"), ("assigned_now", "rules now")):
        r = res[key]
        L += [f"## {name}: agreement {100*r['agreement']:.0f}%", "", "| Channel | Assigned | Precision | Labelled | Recall |", "|---|---|---|---|---|"]
        for c, v in r["by_channel"].items():
            pr = "—" if v["precision"] is None else f"{100*v['precision']:.0f}%"; rc = "—" if v["recall"] is None else f"{100*v['recall']:.0f}%"
            L.append(f"| {c} | {v['assigned']} | {pr} | {v['labelled']} | {rc} |")
        L.append("")
    dis = [r for r in res["rows"] if r["assigned_now"] != r["label"]]
    L += ["## Remaining disagreements", "", "| # | Occupation | Statement | Rules now | Reviewer |", "|---|---|---|---|---|"]
    L += [f"| {r['row']} | {r['occ_code']} | {r['text'][:110]} | {r['assigned_now']} | {r['label']} |" for r in dis]
    return "\n".join(L) + "\n"
