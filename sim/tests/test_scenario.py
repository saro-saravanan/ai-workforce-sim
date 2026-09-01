from pathlib import Path

from aiwsim.scenario import (
    canonical_json,
    diff,
    load_scenario_file,
    quarters,
    resolve,
    scenario_hash,
    validate,
)

ROOT = Path(__file__).resolve().parents[2]
SC = ROOT / "scenarios"


def test_quarters():
    q = quarters("2024Q1", "2040Q4")
    assert len(q) == 68 and q[0] == "2024Q1" and q[-1] == "2040Q4" and q[4] == "2025Q1"


def test_resolve_inheritance_and_shocks():
    base = resolve(load_scenario_file(SC / "baseline.json"), SC)
    child = resolve(load_scenario_file(SC / "example-eu-delay-deepseek-2027.json"), SC)
    assert child["levers"]["capability"] == base["levers"]["capability"]
    assert child["levers"]["regulation"]["EU"]["ai_act"] == "delayed_2y"
    assert [s["id"] for s in child["shocks"]] == ["deepseek-open-2027"]
    validate(base, SC / "schema.json"); validate(child, SC / "schema.json")
    d = diff(base, child)
    paths = {x["path"] for x in d}
    assert "levers.regulation.EU.ai_act" in paths and "shocks" in paths


def test_hash_stable_and_sensitive():
    base = resolve(load_scenario_file(SC / "baseline.json"), SC)
    h1 = scenario_hash(base, "0.2", "d1"); h2 = scenario_hash(base, "0.2", "d1"); h3 = scenario_hash(base, "0.2", "d2")
    assert h1 == h2 != h3
    assert canonical_json(base) == canonical_json(dict(reversed(list(base.items()))))
