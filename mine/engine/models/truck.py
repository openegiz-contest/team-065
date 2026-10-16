"""
Haul-truck physics: rimpull/speed-on-grade, cycle-time components, fuel burn, tyre wear.
Equations from mine/docs/03_domain.md §2.3, §2.4, §2.7, §2.10.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import constants as C

G = 9.81  # m/s^2


def total_resistance_pct(grade_pct: float, rr_pct: float) -> float:
    """TR = GR + RR (% of GVW). 03_domain.md §2.3."""
    return grade_pct + rr_pct


def speed_on_grade_kmh(
    gvw_t: float,
    net_power_kw: float,
    grade_pct: float,
    rr_pct: float,
    drive: str = "mechanical",
    gear_max_kmh: float | None = None,
) -> float:
    """
    Power-limited speed on a grade segment. 03_domain.md §2.3:
        TR = GR + RR
        F_req = m*g*TR/100
        v_power = eta_d * P_net / F_req
        v = min(v_power, v_gear_max)
    Downhill (negative grade) is retarder-limited, handled by the caller via speed caps,
    not by this function (this function only returns the power-limited uphill/flat speed).
    """
    tr_pct = total_resistance_pct(grade_pct, rr_pct)
    if tr_pct <= 0:
        tr_pct = 0.1  # avoid division by zero/negative on flat or downhill; caller applies retarder cap instead
    eta_d = C.ETA_D_ELECTRIC if drive == "electric" else C.ETA_D_MECHANICAL
    f_req_n = gvw_t * 1000.0 * G * (tr_pct / 100.0)
    v_power_ms = eta_d * (net_power_kw * 1000.0) / f_req_n
    v_power_kmh = v_power_ms * 3.6
    if gear_max_kmh is not None:
        return min(v_power_kmh, gear_max_kmh)
    return v_power_kmh


def segment_speed_kmh(
    truck_class: str,
    loaded: bool,
    grade_pct: float,
    rr_pct: float,
    trolley_assist: bool = False,
    cold_speed_cap_kmh: float | None = None,
    visibility_speed_cap_kmh: float | None = None,
) -> float:
    """
    Full speed model for one road segment, combining the power/grade model with the
    site speed-cap bands of 03_domain.md §2.3 (table) and §5.5 (visibility/cold caps).
    trolley_assist doubles speed-on-grade up a loaded ramp per §6.4/§11-S12 (up to +100%).
    """
    spec = C.TRUCK_SPECS[truck_class]
    gvw_t = spec["gvw_t"] if loaded else spec["gvw_t"] - spec["payload_t"]
    power_kw = spec["net_power_kw"]
    max_speed = spec["max_speed_loaded_kmh"] if loaded else spec["max_speed_loaded_kmh"] * 1.1

    if grade_pct >= 1.0:
        # uphill ramp: power-limited
        v = speed_on_grade_kmh(gvw_t, power_kw, grade_pct, rr_pct, gear_max_kmh=max_speed)
        if trolley_assist and loaded:
            v = v * (1.0 + C.TROLLEY_SPEED_GAIN)
        cap = C.SPEED_CAP_RAMP_LOADED if loaded else C.SPEED_CAP_RAMP_EMPTY
        v = min(v, cap if not trolley_assist else cap * (1.0 + C.TROLLEY_SPEED_GAIN))
    elif grade_pct <= -1.0:
        # downhill: retarder-limited, not power-limited
        cap = C.SPEED_CAP_DOWNRAMP_LOADED if loaded else C.SPEED_CAP_DOWNRAMP_EMPTY
        v = cap
    else:
        # flat haul road: power-limited but typically capped by site rule
        v = speed_on_grade_kmh(gvw_t, power_kw, max(rr_pct, 0.5), rr_pct, gear_max_kmh=max_speed)
        cap = C.SPEED_CAP_FLAT_LOADED if loaded else C.SPEED_CAP_FLAT_EMPTY
        v = min(v, cap)

    if cold_speed_cap_kmh is not None:
        v = min(v, cold_speed_cap_kmh)
    if visibility_speed_cap_kmh is not None:
        v = min(v, visibility_speed_cap_kmh)
    return max(v, 1.0)  # avoid zero/negative, equipment always crawls at least 1 km/h


def segment_travel_time_min(length_m: float, speed_kmh: float) -> float:
    if speed_kmh <= 0:
        speed_kmh = 1.0
    hours = (length_m / 1000.0) / speed_kmh
    return hours * 60.0


def passes_per_truck(payload_t: float, bucket_m3: float, fill: float = C.FILL_FACTOR,
                      rho_loose: float = C.RHO_LOOSE_T_M3) -> int:
    """n_pass = ceil(payload / (V_bucket * fill * rho_loose)). 03_domain.md §2.4."""
    per_pass_t = bucket_m3 * fill * rho_loose
    return max(1, math.ceil(payload_t / per_pass_t))


def load_time_min(n_pass: int, t_swing_min: float = C.LOAD_SWING_MEAN_MIN) -> float:
    """Load = n_pass * t_swing + 0.1 min. 03_domain.md §2.4."""
    return n_pass * t_swing_min + 0.1


def fuel_burn_lph(rated_power_kw: float, load_factor: float,
                   bsfc_kg_per_kwh: float = C.BSFC_KG_PER_KWH,
                   rho_diesel: float = C.RHO_DIESEL_KG_L) -> float:
    """FC(L/h) = P_rated(kW) * LF * BSFC / rho_diesel. 03_domain.md §2.7."""
    return rated_power_kw * load_factor * bsfc_kg_per_kwh / rho_diesel


def tyre_wear_multiplier(rr_pct: float, overload_frac: float = 0.0, temp_c: float = 15.0) -> float:
    """k = 1 + 0.03*(RR%-2) + 0.5*I(overload>10%) + 0.2*I(T<-25C). 03_domain.md §2.10."""
    k = 1.0 + 0.03 * (rr_pct - 2.0)
    if overload_frac > 0.10:
        k += 0.5
    if temp_c < -25.0:
        k += 0.2
    return k


def tkph(mean_tyre_load_t: float, mean_cycle_speed_kmh: float) -> float:
    """TKPH_site = Q_mean_tyre_load(t) * V_mean_cycle(km/h). 03_domain.md §2.10."""
    return mean_tyre_load_t * mean_cycle_speed_kmh


@dataclass
class CycleTimeBreakdown:
    spot_load_min: float
    load_min: float
    haul_loaded_min: float
    queue_dump_min: float
    spot_dump_min: float
    haul_empty_min: float
    queue_shovel_min: float

    @property
    def total_min(self) -> float:
        return (self.spot_load_min + self.load_min + self.haul_loaded_min + self.queue_dump_min
                + self.spot_dump_min + self.haul_empty_min + self.queue_shovel_min)


def truck_productivity_tph(payload_t: float, cycle_min: float, availability: float,
                            utilisation: float, job_efficiency: float = C.JOB_EFFICIENCY_E) -> float:
    """Q_truck(t/h) = Payload * 60 / T_cycle * A * U * E. 03_domain.md §2.6."""
    if cycle_min <= 0:
        return 0.0
    return payload_t * 60.0 / cycle_min * availability * utilisation * job_efficiency


def shovel_productivity_tph(t_swing_s: float, bucket_m3: float, fill: float, rho_loose: float,
                             availability: float, utilisation: float,
                             job_efficiency: float = C.JOB_EFFICIENCY_E) -> float:
    """Q_shovel(t/h) = (3600/t_swing_s) * V_b * fill * rho_loose * A * U * E. 03_domain.md §2.6."""
    if t_swing_s <= 0:
        return 0.0
    return (3600.0 / t_swing_s) * bucket_m3 * fill * rho_loose * availability * utilisation * job_efficiency


def match_factor(n_trucks: int, t_load_min: float, n_shovels: int, t_cycle_min: float) -> float:
    """MF = (N_trucks * t_load) / (N_shovels * T_cycle). 03_domain.md §2.6 (Douglas 1964)."""
    if n_shovels <= 0 or t_cycle_min <= 0:
        return 0.0
    return (n_trucks * t_load_min) / (n_shovels * t_cycle_min)


if __name__ == "__main__":
    # Sanity checks against 03_domain.md §2.3. NOTE: the domain doc's own 793F worked example
    # ("0.80 x 1.848e6 / (386e3 x 9.81 x 0.125) = 3.90 m/s = 14.0 km/h") is internally inconsistent --
    # that division, with eta_d=0.80 applied as written, equals 3.12 m/s = 11.2 km/h; 3.90 m/s only
    # follows if eta_d is dropped (=1.0). The doc's 785C example (9.5 km/h) IS internally consistent
    # with eta_d=0.80. We implement the stated formula exactly (eta_d applied), which reproduces the
    # 785C example precisely and keeps the 793F result inside the doc's own segment-speed table band
    # (10-14 km/h loaded ramp, §2.3 table) -- i.e. correct-formula fidelity over copying a doc arithmetic slip.
    v793 = speed_on_grade_kmh(386.0, 1848.0, 10.0, 2.5, gear_max_kmh=60.0)
    assert 10.0 <= v793 <= 14.0, f"793F loaded 10% grade expected within table band 10-14 km/h, got {v793:.2f}"
    v785 = speed_on_grade_kmh(249.0, 1005.0, 10.0, 2.5, gear_max_kmh=55.0)
    assert abs(v785 - 9.5) < 0.5, f"785C loaded 10% grade expected ~9.5 km/h, got {v785:.2f}"
    n = passes_per_truck(136.0, 22.0, fill=0.90, rho_loose=C.RHO_LOOSE_T_M3)
    assert n == 4, f"785C expected 4 passes, got {n}"
    print("models/truck.py self-check OK:", v793, v785, n)
