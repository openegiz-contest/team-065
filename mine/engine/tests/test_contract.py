"""
Contract between mine/setup/model.json (the twins Ditto starts with) and what this engine
publishes. Every feature a twin declares must be one the engine keeps updating, and every
feature the engine publishes must exist on that twin, otherwise the twin carries frozen values
next to live ones. Runs without network, MQTT or Docker.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import engine  # noqa: E402
from scenarios import BASELINE_EFFECTIVE  # noqa: E402
from simulation import Simulation  # noqa: E402

MODEL = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "setup", "model.json"))
NS = "kz.kyzyltas.mine:"
WRITTEN_BY_UI = {"scenario"}


class _AlwaysDue:
    def due(self, name, interval_s, now):
        return True


class _Capture:
    def __init__(self):
        self.feats: dict[str, dict] = {}

    def enqueue(self, name, feats):
        self.feats.setdefault(name, {}).update(feats)


def _published() -> dict[str, dict]:
    sim, base = Simulation(seed=42, label="r"), Simulation(seed=42, label="b")
    for _ in range(30):
        sim.step(12, BASELINE_EFFECTIVE)
        base.step(12, BASELINE_EFFECTIVE)
    cap = _Capture()
    engine._publish_all(cap, _AlwaysDue(), 0.0, sim, base, BASELINE_EFFECTIVE)
    return cap.feats


def _instances() -> dict[str, dict]:
    model = json.load(open(MODEL, encoding="utf-8"))
    return {t["thingId"][len(NS):]: t for t in model if not t["attributes"].get("_isType")}


def test_every_published_twin_exists_in_model():
    missing = sorted(set(_published()) - set(_instances()))
    assert not missing, f"engine publishes to twins that setup never creates: {missing}"


def test_every_model_twin_is_kept_live():
    idle = sorted(set(_instances()) - set(_published()) - WRITTEN_BY_UI)
    assert not idle, f"twins the engine never updates: {idle}"


def test_feature_sets_match():
    pub = _published()
    problems = []
    for name, twin in _instances().items():
        if name in WRITTEN_BY_UI:
            continue
        declared = set(twin.get("features", {}))
        live = set(pub.get(name, {}))
        if declared != live:
            problems.append(f"{name}: setup-only={sorted(declared - live)} engine-only={sorted(live - declared)}")
    assert not problems, "\n".join(problems)


def test_feature_value_types_match():
    # InfluxDB rejects a field whose type changes, so the initial value type must match.
    pub = _published()
    problems = []
    for name, twin in _instances().items():
        for f, body in twin.get("features", {}).items():
            if name in pub and f in pub[name]:
                a = body["properties"]["value"]
                b = pub[name][f]["properties"]["value"]
                if isinstance(a, str) != isinstance(b, str):
                    problems.append(f"{name}.{f}: setup {type(a).__name__} vs engine {type(b).__name__}")
    assert not problems, "\n".join(problems)


if __name__ == "__main__":
    import traceback

    tests = [(n, fn) for n, fn in dict(globals()).items() if n.startswith("test_") and callable(fn)]
    failures = 0
    for name, fn in tests:
        try:
            fn()
            print(f"PASS {name}")
        except Exception:
            failures += 1
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    raise SystemExit(1 if failures else 0)
