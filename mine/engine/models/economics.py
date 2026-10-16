"""
Revenue, margin, CO2 and cut-off-grade economics. 03_domain.md §3.4, §9.3.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import constants as C


@dataclass
class KpiSnapshot:
    tph: float
    cu_tph: float
    au_ozph: float
    nsr_usd_h: float
    margin_usd_h: float
    energy_kwh_h: float
    fuel_l_h: float
    co2_t_h: float


def cu_tph(tph: float, f_cu_pct: float, r_cu: float) -> float:
    """Cu_t/h = TPH * f_Cu * R_Cu. 03_domain.md §9.3."""
    return tph * (f_cu_pct / 100.0) * r_cu


def au_ozph(tph: float, g_au_gt: float, r_au: float) -> float:
    """Au_oz/h = TPH * g_Au * R_Au / 31.1035. 03_domain.md §9.3."""
    return tph * g_au_gt * r_au / 31.1035


def nsr_usd_h(cu_tph_val: float, au_ozph_val: float, p_cu_usd_t: float, p_au_usd_oz: float,
              tc_rc_usd_t: float, pay_cu: float = C.PAY_CU, pay_au: float = C.PAY_AU) -> float:
    """
    NSR/h = Cu_t/h*pay_Cu*(P_Cu - RC*2204.6) - (Cu_t/h/c)*(TC+freight) + Au_oz/h*pay_Au*P_Au - MET
    03_domain.md §9.3. We fold RC into TC/RC per tonne of concentrate terms (simplified: TC/RC is
    already expressed $/t concentrate in the twin's price feed, so we subtract it directly per
    tonne of Cu metal via the mass-pull relationship handled by the caller, keeping this function
    a pure per-metal revenue calc plus a flat TC/RC deduction proportional to Cu tonnes).
    """
    rev_cu = cu_tph_val * pay_cu * p_cu_usd_t
    rev_au = au_ozph_val * pay_au * p_au_usd_oz
    tc_rc_cost = cu_tph_val * tc_rc_usd_t  # [D] simplified: $/t Cu metal equivalent deduction
    met = (rev_cu * C.MET_CU_FRACTION) + (rev_au * C.MET_AU_FRACTION)
    return rev_cu + rev_au - tc_rc_cost - met


def margin_usd_h(nsr: float, tph: float, strip_ratio: float, energy_kwh_h: float,
                  fuel_l_h: float, grid_tariff_usd_kwh: float = C.GRID_TARIFF_USD_PER_KWH,
                  diesel_price_usd_l: float = C.DIESEL_PRICE_USD_PER_L,
                  cost_proc_ga_usd_t: float = C.COST_PROCESSING_USD_T_ORE + C.COST_GA_USD_T_ORE,
                  cost_mine_usd_t_moved: float = C.COST_MINING_USD_T_MOVED) -> float:
    """Margin/h = NSR - TPH*(c_proc+c_GA) - TPH*(1+SR)*c_mine - E_kWh*tariff - Fuel_L*price. §9.3."""
    opex = tph * cost_proc_ga_usd_t + tph * (1.0 + strip_ratio) * cost_mine_usd_t_moved
    energy_cost = energy_kwh_h * grid_tariff_usd_kwh
    fuel_cost = fuel_l_h * diesel_price_usd_l
    return nsr - opex - energy_cost - fuel_cost


def co2_t_h(energy_mwh_h: float, fuel_l_h: float, grid_ef_kg_kwh: float = C.GRID_CO2_KG_PER_KWH,
            diesel_ef_kg_l: float = C.DIESEL_CO2_KG_PER_L) -> float:
    """CO2_t/h = E_MWh*EF_grid + Fuel_L*2.68e-3. 03_domain.md §9.3/§6.3."""
    return (energy_mwh_h * 1000.0 * grid_ef_kg_kwh + fuel_l_h * diesel_ef_kg_l) / 1000.0


def lane_cutoff_pct(c_proc_ga_per_t_ore: float, c_sell_per_t_ore: float, p_usd_kg: float,
                     y_rec: float, pay: float) -> float:
    """
    Breakeven (marginal) cutoff, Lane 1988: g_c(%%Cu) = (c_proc+c_GA+c_sell)/((P-r)*y*pay*10).
    03_domain.md §3.4. P in $/kg, result in %% (x10 kg per %%-t).
    """
    denom = p_usd_kg * y_rec * pay * 10.0
    if denom <= 0:
        return 0.0
    return (c_proc_ga_per_t_ore + c_sell_per_t_ore) / denom


def mill_constrained_cutoff_pct(base_cutoff_pct: float, price_shock: bool) -> float:
    """
    03_domain.md §3.4/§11-S10: mill-constrained Lane cutoff is ~0.15-0.25%% in practice, rising
    to ~0.23%% under a -25%% Cu price shock (from the twin's ~0.20%% base).
    """
    return C.CUTOFF_GRADE_STRESSED_PCT if price_shock else base_cutoff_pct


if __name__ == "__main__":
    cu = cu_tph(3600.0, 0.50, 0.80)
    assert abs(cu - 14.4) < 1e-6
    au = au_ozph(3600.0, 0.26, 0.60)
    assert abs(au - 18.06) < 0.05
    nsr = nsr_usd_h(cu, au, 14500.0, 4300.0, 0.0)
    assert 250000.0 < nsr < 290000.0, nsr  # §9.3 base case ~ $275k/h before MET deduction nuance
    print("models/economics.py self-check OK:", cu, au, nsr)
