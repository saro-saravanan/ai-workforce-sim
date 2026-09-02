"""AI supply-side actors (spec §3.1) and their public release history (contracts §11).

``ACTORS`` is transcribed from public information (region, role, weights posture) with E-tagged
model quantities (frontier lag, cadence, availability by region).  List prices are the vendor's
published per-million-token prices for the lab's frontier tier at the date in ``price_note``,
blended 3:1 input:output; tagged S with "verify at ingest" because they were transcribed from
memory in a sandbox without web access.  ``RELEASES`` is a transcription of major releases
2023-03 .. 2026-06 whose dates the author is confident of; fewer, correct rows beat coverage.
Both are replaced by ``aiwsim.data.ingest.epoch_models``.
"""

from __future__ import annotations

import math

import polars as pl

from aiwsim.data.regions import REGION_IDS

ACTORS_TAG = "partial:public_actor_facts;E(lags,cadence,availability);S(prices, verify at ingest)"
RELEASES_TAG = "transcribed public release history; verify via ingest/epoch_models.py"
PRICE_VERIFY = "verify at ingest"


def blended_price(input_usd: float, output_usd: float) -> float:
    """Blended USD per million tokens at a 3:1 input:output mix."""
    return round((3.0 * input_usd + output_usd) / 4.0, 3)


def _a(**fields) -> dict:
    return fields


# actor_id, name, region, role, weights_posture, frontier_lag_q, releases_per_year,
# (input $/Mtok, output $/Mtok, price note) or None, availability rule, note
ACTORS: list[dict] = [
    _a(actor_id="openai", name="OpenAI", region_id="US", role="lab", weights_posture="closed",
         frontier_lag_quarters=0, releases_per_year=3,
         price=(1.25, 10.0, "GPT-5 list price, Aug 2025"), avail="us_closed", note=""),
    _a(actor_id="anthropic", name="Anthropic", region_id="US", role="lab", weights_posture="closed",
         frontier_lag_quarters=0, releases_per_year=3,
         price=(5.0, 25.0, "Claude Opus 4.5 list price, Nov 2025"), avail="us_closed", note=""),
    _a(actor_id="google_deepmind", name="Google DeepMind", region_id="US", role="lab", weights_posture="closed",
         frontier_lag_quarters=0, releases_per_year=3,
         price=(2.0, 12.0, "Gemini 3 Pro list price (<=200k context), Nov 2025"), avail="us_closed",
         note="Alphabet; research base in London, home region taken as US (parent, cloud, capex)"),
    _a(actor_id="meta", name="Meta", region_id="US", role="lab", weights_posture="open-lagged",
         frontier_lag_quarters=2, releases_per_year=2, price=None, avail="meta",
         note="no first-party API list price; Llama served by third parties"),
    _a(actor_id="xai", name="xAI", region_id="US", role="lab", weights_posture="closed",
         frontier_lag_quarters=1, releases_per_year=3,
         price=(3.0, 15.0, "Grok 4 list price, Jul 2025"), avail="us_closed", note=""),
    _a(actor_id="microsoft", name="Microsoft", region_id="US", role="lab", weights_posture="closed",
         frontier_lag_quarters=1, releases_per_year=2, price=None, avail="us_closed",
         note="cloud (Azure); resells OpenAI models at OpenAI list prices, own MAI/Phi models"),
    _a(actor_id="amazon", name="Amazon", region_id="US", role="lab", weights_posture="closed",
         frontier_lag_quarters=2, releases_per_year=2,
         price=(2.5, 12.5, "Amazon Nova Premier list price, Mar 2025"), avail="us_closed",
         note="cloud (AWS Bedrock); own Nova models plus Anthropic and others"),
    _a(actor_id="nvidia", name="NVIDIA", region_id="US", role="compute", weights_posture="closed",
         frontier_lag_quarters=0, releases_per_year=2, price=None, avail="export_control",
         note="accelerators; CN availability reflects H20/H200 case-by-case licensing (E)"),
    _a(actor_id="mistral", name="Mistral AI", region_id="EU", role="lab", weights_posture="open-lagged",
         frontier_lag_quarters=3, releases_per_year=2,
         price=(2.0, 6.0, "Mistral Large 2 list price, Jul 2024"), avail="everywhere", note="France"),
    _a(actor_id="aleph_alpha", name="Aleph Alpha", region_id="EU", role="lab", weights_posture="closed",
         frontier_lag_quarters=5, releases_per_year=2, price=None, avail="home_half", note="Germany"),
    _a(actor_id="asml", name="ASML", region_id="EU", role="chokepoint", weights_posture="closed",
         frontier_lag_quarters=0, releases_per_year=2, price=None, avail="export_control",
         note="lithography; Netherlands; CN availability reflects EUV ban and DUV licensing (E)"),
    _a(actor_id="deepseek", name="DeepSeek", region_id="CN", role="lab", weights_posture="open-frontier",
         frontier_lag_quarters=2, releases_per_year=3,
         price=(0.28, 0.42, "DeepSeek-V3.2 API list price, Sep 2025"), avail="cn_open", note=""),
    _a(actor_id="alibaba", name="Alibaba (Qwen)", region_id="CN", role="lab", weights_posture="open-lagged",
         frontier_lag_quarters=2, releases_per_year=3, price=None, avail="cn_open",
         note="Qwen3-Max international list price not transcribed with confidence"),
    _a(actor_id="bytedance", name="ByteDance", region_id="CN", role="lab", weights_posture="closed",
         frontier_lag_quarters=3, releases_per_year=2, price=None, avail="cn_closed",
         note="Doubao/Seed; CNY pricing on Volcano Engine not transcribed"),
    _a(actor_id="moonshot", name="Moonshot AI", region_id="CN", role="lab", weights_posture="open-lagged",
         frontier_lag_quarters=3, releases_per_year=2,
         price=(0.6, 2.5, "Kimi K2 API list price, Jul 2025"), avail="cn_open", note=""),
    _a(actor_id="zhipu", name="Zhipu AI", region_id="CN", role="lab", weights_posture="open-lagged",
         frontier_lag_quarters=3, releases_per_year=2,
         price=(0.6, 2.2, "GLM-4.5 API list price, Jul 2025"), avail="cn_open", note=""),
    _a(actor_id="baidu", name="Baidu", region_id="CN", role="lab", weights_posture="closed",
         frontier_lag_quarters=4, releases_per_year=2, price=None, avail="cn_closed",
         note="ERNIE; CNY pricing on Qianfan not transcribed"),
    _a(actor_id="tencent", name="Tencent", region_id="CN", role="lab", weights_posture="closed",
         frontier_lag_quarters=3, releases_per_year=2, price=None, avail="cn_closed",
         note="Hunyuan; CNY pricing not transcribed"),
    _a(actor_id="samsung", name="Samsung", region_id="KR", role="lab", weights_posture="closed",
         frontier_lag_quarters=6, releases_per_year=2, price=None, avail="home_half",
         note="Gauss models; also HBM memory supplier (not modelled as compute here)"),
    _a(actor_id="softbank", name="SoftBank", region_id="JP", role="lab", weights_posture="closed",
         frontier_lag_quarters=6, releases_per_year=2, price=None, avail="home_half",
         note="SB Intuitions; OpenAI partner (Stargate, SB OpenAI Japan)"),
    _a(actor_id="naver", name="Naver", region_id="KR", role="lab", weights_posture="closed",
         frontier_lag_quarters=6, releases_per_year=2, price=None, avail="home_half",
         note="HyperCLOVA X; KRW pricing not transcribed"),
    _a(actor_id="sakana", name="Sakana AI", region_id="JP", role="lab", weights_posture="closed",
         frontier_lag_quarters=6, releases_per_year=2, price=None, avail="home_half", note=""),
    _a(actor_id="tsmc", name="TSMC", region_id="TW", role="chokepoint", weights_posture="closed",
         frontier_lag_quarters=0, releases_per_year=2, price=None, avail="export_control",
         note="foundry; CN availability reflects advanced-node export controls (E)"),
]


def availability(rule: str, home: str) -> dict[str, float]:
    """Availability V_{a,r} in [0,1] per region for the rule named in ``ACTORS`` (all E)."""
    if rule == "us_closed":  # export / licensing regime: not offered in China
        return {r: (0.0 if r == "CN" else 1.0) for r in REGION_IDS}
    if rule == "meta":  # open weights downloadable everywhere; licence and export posture in CN
        return {r: (0.5 if r == "CN" else 1.0) for r in REGION_IDS}
    if rule == "everywhere":
        return dict.fromkeys(REGION_IDS, 1.0)
    if rule == "cn_open":  # open weights; procurement caution in the U.S. and EU
        return {r: (0.5 if r in ("US", "EU") else 1.0) for r in REGION_IDS}
    if rule == "cn_closed":
        return {r: (1.0 if r == "CN" else 0.2) for r in REGION_IDS}
    if rule == "home_half":
        return {r: (1.0 if r == home else 0.5) for r in REGION_IDS}
    if rule == "export_control":  # compute / chokepoint: sold everywhere, licensed into China
        return {r: (0.3 if r == "CN" else 1.0) for r in REGION_IDS}
    raise ValueError(rule)


def actors_frame() -> pl.DataFrame:
    rows = []
    for a in ACTORS:
        av = availability(a["avail"], a["region_id"])
        price = a["price"]
        rows.append({
            "actor_id": a["actor_id"], "name": a["name"], "region_id": a["region_id"], "role": a["role"],
            "weights_posture": a["weights_posture"], "frontier_lag_quarters": a["frontier_lag_quarters"],
            "releases_per_year": a["releases_per_year"],
            "price_frontier_usd_per_mtok": blended_price(price[0], price[1]) if price else None,
            **{f"avail_{r}": av[r] for r in REGION_IDS},
            "source_tag": ACTORS_TAG,
            "price_note": f"{price[2]}; input {price[0]} / output {price[1]} USD per Mtok, blended 3:1; {PRICE_VERIFY}"
                          if price else "",
            "availability_rule": a["avail"], "note": a["note"],
        })
    return pl.DataFrame(rows, schema_overrides={"price_frontier_usd_per_mtok": pl.Float64})


# ------------------------------------------------------------------------------------------------
# releases (actor_id, model, date, open_weights, note)
# ------------------------------------------------------------------------------------------------
RELEASES: list[tuple[str, str, str, int, str]] = [
    ("openai", "GPT-4", "2023-03-14", 0, ""),
    ("anthropic", "Claude 2", "2023-07-11", 0, ""),
    ("meta", "Llama 2", "2023-07-18", 1, "community licence"),
    ("naver", "HyperCLOVA X", "2023-08-24", 0, "Korean-language model; not frontier"),
    ("baidu", "ERNIE 4.0", "2023-10-17", 0, ""),
    ("openai", "GPT-4 Turbo", "2023-11-06", 0, ""),
    ("google_deepmind", "Gemini 1.0", "2023-12-06", 0, "Ultra / Pro announced"),
    ("mistral", "Mixtral 8x7B", "2023-12-11", 1, "Apache 2.0"),
    ("google_deepmind", "Gemini 1.5 Pro", "2024-02-15", 0, "announcement; 1M-token context"),
    ("mistral", "Mistral Large", "2024-02-26", 0, ""),
    ("anthropic", "Claude 3", "2024-03-04", 0, "Opus / Sonnet / Haiku"),
    ("xai", "Grok-1", "2024-03-17", 1, "weights released Apache 2.0"),
    ("meta", "Llama 3", "2024-04-18", 1, "8B / 70B"),
    ("deepseek", "DeepSeek-V2", "2024-05-06", 1, ""),
    ("openai", "GPT-4o", "2024-05-13", 0, ""),
    ("anthropic", "Claude 3.5 Sonnet", "2024-06-20", 0, ""),
    ("meta", "Llama 3.1", "2024-07-23", 1, "405B"),
    ("mistral", "Mistral Large 2", "2024-07-24", 1, "weights under the Mistral Research License"),
    ("openai", "o1-preview", "2024-09-12", 0, "reasoning model"),
    ("alibaba", "Qwen2.5", "2024-09-19", 1, ""),
    ("tencent", "Hunyuan-Large", "2024-11-05", 1, "389B MoE"),
    ("amazon", "Amazon Nova", "2024-12-03", 0, "Nova Pro / Lite / Micro at re:Invent"),
    ("openai", "o1", "2024-12-05", 0, ""),
    ("google_deepmind", "Gemini 2.0 Flash", "2024-12-11", 0, ""),
    ("deepseek", "DeepSeek-V3", "2024-12-26", 1, ""),
    ("deepseek", "DeepSeek-R1", "2025-01-20", 1, "MIT licence"),
    ("bytedance", "Doubao-1.5-pro", "2025-01-22", 0, ""),
    ("xai", "Grok 3", "2025-02-17", 0, ""),
    ("anthropic", "Claude 3.7 Sonnet", "2025-02-24", 0, ""),
    ("openai", "GPT-4.5", "2025-02-27", 0, "research preview"),
    ("baidu", "ERNIE 4.5", "2025-03-16", 0, "weights opened 2025-06-30"),
    ("google_deepmind", "Gemini 2.5 Pro", "2025-03-25", 0, "experimental release"),
    ("meta", "Llama 4", "2025-04-05", 1, "Scout / Maverick"),
    ("openai", "GPT-4.1", "2025-04-14", 0, ""),
    ("openai", "o3", "2025-04-16", 0, "with o4-mini"),
    ("alibaba", "Qwen3", "2025-04-29", 1, ""),
    ("anthropic", "Claude 4", "2025-05-22", 0, "Opus 4 / Sonnet 4"),
    ("xai", "Grok 4", "2025-07-09", 0, ""),
    ("moonshot", "Kimi K2", "2025-07-11", 1, "1T MoE"),
    ("zhipu", "GLM-4.5", "2025-07-28", 1, ""),
    ("openai", "gpt-oss-120b", "2025-08-05", 1, "Apache 2.0; with gpt-oss-20b"),
    ("anthropic", "Claude Opus 4.1", "2025-08-05", 0, ""),
    ("openai", "GPT-5", "2025-08-07", 0, ""),
    ("deepseek", "DeepSeek-V3.1", "2025-08-21", 1, ""),
    ("anthropic", "Claude Sonnet 4.5", "2025-09-29", 0, ""),
    ("moonshot", "Kimi K2 Thinking", "2025-11-06", 1, ""),
    ("google_deepmind", "Gemini 3 Pro", "2025-11-18", 0, ""),
    ("anthropic", "Claude Opus 4.5", "2025-11-24", 0, ""),
    ("anthropic", "Claude Mythos Preview", "2026-03-01", 0,
     "month precision; date and horizon from series/metr_horizons.csv"),
    ("openai", "GPT-5.6 Sol", "2026-06-26", 0,
     "date is the series/metr_horizons.csv entry date (METR); release date to verify"),
]


def releases_frame(metr: pl.DataFrame) -> pl.DataFrame:
    """``actor_releases.csv``; capability_index = log2(METR 50% horizon minutes) where the model
    name matches ``series/metr_horizons.csv``, else null."""
    horizon = {m: float(h) for m, h in zip(metr["model"], metr["horizon_minutes_p50"]) if h is not None}
    rows = []
    for actor_id, model, date, open_w, note in RELEASES:
        h = horizon.get(model)
        rows.append({
            "actor_id": actor_id, "model": model, "date": date,
            "capability_index": round(math.log2(h), 3) if h else None,
            "open_weights": open_w, "note": note, "source_tag": RELEASES_TAG,
        })
    df = pl.DataFrame(rows, schema_overrides={"capability_index": pl.Float64})
    known = {a["actor_id"] for a in ACTORS}
    unknown = sorted(set(df["actor_id"]) - known)
    if unknown:
        raise ValueError(f"releases for unknown actors: {unknown}")
    return df.sort(["date", "actor_id", "model"])
