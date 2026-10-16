"""
Haul-road PM10 dust (US EPA AP-42 §13.2.2) and post-blast gas re-entry/dispersion.
03_domain.md §5.1, §5.2.
"""
from __future__ import annotations

import math

from . import constants as C

LB_PER_KG = 2.20462


def pm10_lb_per_vmt(silt_pct: float, mean_vehicle_weight_short_tons: float,
                     k: float = C.PM10_AP42_K, a: float = C.PM10_AP42_A, b: float = C.PM10_AP42_B) -> float:
    """E(lb/VMT) = k*(s/12)^a*(W/3)^b. 03_domain.md §5.1 AP-42."""
    return k * (silt_pct / 12.0) ** a * (mean_vehicle_weight_short_tons / 3.0) ** b


def pm10_kg_per_vkm(silt_pct: float, mean_vehicle_weight_t: float) -> float:
    """Convenience: kg of PM10 per vehicle-km, converting short tons and miles -> SI."""
    short_tons = mean_vehicle_weight_t * 1.10231
    e_lb_vmt = pm10_lb_per_vmt(silt_pct, short_tons)
    e_kg_vmt = e_lb_vmt / LB_PER_KG
    return e_kg_vmt / 1.60934  # per VMT (mile) -> per km


def controlled_pm10_kg_per_vkm(uncontrolled_kg_per_vkm: float, watering_efficiency: float,
                                ambient_temp_c: float) -> float:
    """
    Watering control cuts PM10 by 50-75%% typical, but is "not possible below about 0C" --
    winter relies on chemical suppressants or no control. 03_domain.md §5.1.
    """
    if ambient_temp_c < 0.0:
        efficiency = 0.0
    else:
        efficiency = watering_efficiency
    return uncontrolled_kg_per_vkm * (1.0 - efficiency)


def gas_reentry_time_min(stability_class_f: bool, wind_ms: float) -> float:
    """
    Post-blast re-entry time. Base rule >= 30 min after firing + gas test (§5.2). Under a winter
    inversion (stability class F, wind < 2 m/s) clearance is 3-5x longer (§5.2); we also expose
    the explicit §11-S8 scenario value (re-entry 30 -> 150 min).
    """
    base = C.GAS_REENTRY_BASE_MIN
    if stability_class_f and wind_ms < 2.0:
        return base * 5.0
    return base


if __name__ == "__main__":
    e = pm10_kg_per_vkm(8.0, 276.0)  # 793F mean weight ~276 t, §5.1 worked example
    assert 1.8 < e < 2.8, e  # 03_domain.md §5.1 worked example: ~2.3 kg/vehicle-km uncontrolled
    c = controlled_pm10_kg_per_vkm(e, C.WATERING_CONTROL_EFFICIENCY, 15.0)
    assert c < e
    c_winter = controlled_pm10_kg_per_vkm(e, C.WATERING_CONTROL_EFFICIENCY, -20.0)
    assert c_winter == e  # no control possible below 0C
    print("models/dust.py self-check OK:", e, c, c_winter)
