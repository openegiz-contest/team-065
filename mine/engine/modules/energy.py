"""
modules/energy.py -- diesel + grid energy/CO2 accounting and the trolley-assist tradeoff.
03_domain.md §2.7, §6.1-§6.4.
"""
from __future__ import annotations

from models import constants as C
from models.truck import fuel_burn_lph


def truck_fuel_lph(truck_class: str, phase: str, idle_multiplier: float = 1.0) -> float:
    """Load factor by cycle phase, 03_domain.md §2.7."""
    spec = C.TRUCK_SPECS[truck_class]
    gross_kw = spec["gross_power_kw"]
    if phase in ("haul_loaded",):
        lf = C.LOAD_FACTOR_HAUL_LOADED
        return fuel_burn_lph(gross_kw, lf)
    if phase in ("haul_empty",):
        lf = C.LOAD_FACTOR_HAUL_EMPTY
        return fuel_burn_lph(gross_kw, lf)
    if phase in ("loading", "dumping", "spot_load", "spot_dump"):
        lf = C.LOAD_FACTOR_SPOT_DUMP
        return fuel_burn_lph(gross_kw, lf)
    # queueing / idle
    idle_base = C.IDLE_FUEL_LH_793F if truck_class in ("CAT793F", "KOM830E") else C.IDLE_FUEL_LH_785C
    return idle_base * idle_multiplier


def grid_energy_kwh(power_draw_kw: float, dt_h: float) -> float:
    return power_draw_kw * dt_h


def co2_from_energy(fuel_l: float, grid_kwh: float, grid_ef_kg_kwh: float = C.GRID_CO2_KG_PER_KWH) -> float:
    """kg CO2 from diesel litres + grid kWh. 03_domain.md §6.3."""
    return fuel_l * C.DIESEL_CO2_KG_PER_L + grid_kwh * grid_ef_kg_kwh


def trolley_tradeoff(n_trucks_on_ramp: float, dt_h: float, grid_ef_kg_kwh: float = C.GRID_CO2_KG_PER_KWH
                      ) -> dict:
    """
    03_domain.md §6.4 / §11-S12: trolley assist on the 1.2km main ramp cuts diesel on that
    stretch by >90%% and adds grid draw. We approximate the diesel baseline on that stretch as a
    793F/830E-class truck at the haul_loaded load factor for the ramp's transit time, and compare
    the diesel-cost-avoided to the grid-cost-added and to the net CO2 change (which can be
    *positive* on the coal-heavy Kazakh grid -- the "trolley carbon paradox").
    Returns per-hour deltas (negative = reduction) for diesel_l, grid_kwh, cost_usd, co2_kg.
    """
    if n_trucks_on_ramp <= 0:
        return {"diesel_l_h": 0.0, "grid_kwh_h": 0.0, "cost_usd_h": 0.0, "co2_kg_h": 0.0}

    baseline_diesel_lph_per_truck = fuel_burn_lph(C.TRUCK_SPECS["KOM830E"]["gross_power_kw"],
                                                   C.LOAD_FACTOR_HAUL_LOADED)
    diesel_saved_lph = n_trucks_on_ramp * baseline_diesel_lph_per_truck * C.TROLLEY_DIESEL_CUT
    # Energy-conservation link (03_domain.md §6.4): grid kWh needed = diesel litres displaced *
    # 4.2 kWh/L (not an independent assumption -- see constants.py for the derivation).
    grid_added_kwh_h = diesel_saved_lph * C.TROLLEY_GRID_KWH_PER_L_DISPLACED

    diesel_cost_saved = diesel_saved_lph * C.DIESEL_PRICE_USD_PER_L
    grid_cost_added = grid_added_kwh_h * C.GRID_TARIFF_USD_PER_KWH
    net_cost_usd_h = grid_cost_added - diesel_cost_saved  # negative = net saving

    co2_diesel_saved_kg = diesel_saved_lph * C.DIESEL_CO2_KG_PER_L
    co2_grid_added_kg = grid_added_kwh_h * grid_ef_kg_kwh
    net_co2_kg_h = co2_grid_added_kg - co2_diesel_saved_kg  # positive = CO2 increase

    return {
        "diesel_l_h": -diesel_saved_lph,
        "grid_kwh_h": grid_added_kwh_h,
        "cost_usd_h": net_cost_usd_h,
        "co2_kg_h": net_co2_kg_h,
    }


if __name__ == "__main__":
    t_central = trolley_tradeoff(n_trucks_on_ramp=3.0, dt_h=1.0, grid_ef_kg_kwh=0.80)
    # 03_domain.md §11-S12: cost should fall (net saving, i.e. negative cost delta)...
    assert t_central["cost_usd_h"] < 0.0, t_central
    # ...but at the central 0.80 kg/kWh grid factor (above the 0.64 breakeven, §6.4), CO2 should RISE
    # -- the "trolley carbon paradox".
    assert t_central["co2_kg_h"] > 0.0, t_central
    t_clean = trolley_tradeoff(n_trucks_on_ramp=3.0, dt_h=1.0, grid_ef_kg_kwh=0.30)
    # On a cleaner grid (below the 0.64 breakeven), CO2 should instead FALL.
    assert t_clean["co2_kg_h"] < 0.0, t_clean
    print("modules/energy.py self-check OK:", t_central, t_clean)
