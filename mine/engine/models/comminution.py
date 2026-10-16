"""
Comminution (Bond work index) and mine-to-mill coupling. 03_domain.md §4.3, §7.3.
"""
from __future__ import annotations

from . import constants as C


def bond_work_kwh_t(wi: float, f80_um: float, p80_um: float) -> float:
    """Bond (1961): W(kWh/t) = 10*Wi*(1/sqrt(P80) - 1/sqrt(F80)). 03_domain.md §7.3."""
    return 10.0 * wi * (1.0 / (p80_um ** 0.5) - 1.0 / (f80_um ** 0.5))


def throughput_from_power_tph(power_draw_kw: float, eta_circuit: float, specific_energy_kwh_t: float) -> float:
    """TPH = P_draw(kW) * eta_circuit / W. 03_domain.md §7.3."""
    if specific_energy_kwh_t <= 0:
        return 0.0
    return power_draw_kw * eta_circuit / specific_energy_kwh_t


def sag_tph_surrogate(
    tph_ref: float,
    power_fraction: float,
    axb: float,
    axb_ref: float,
    f80_ref_um: float,
    f80_um: float,
    fines_25mm_frac: float,
    fines_ref_frac: float,
) -> float:
    """
    Twin surrogate (03_domain.md §4.3):
        TPH_SAG = TPH_ref * (P_SAG/P_ref) * (Axb/Axb_ref)^0.8 * (F80_ref/F80)^0.25 * (fines/fines_ref)^0.15
    Calibrated so -20% X50 (hence lower F80/more fines) gives +8 to +10% TPH.
    """
    axb_term = (max(axb, 1.0) / axb_ref) ** C.SAG_TPH_AXB_EXP
    f80_term = (f80_ref_um / max(f80_um, 1.0)) ** C.SAG_TPH_F80_EXP
    fines_term = (max(fines_25mm_frac, 0.001) / max(fines_ref_frac, 0.001)) ** C.SAG_TPH_FINES_EXP
    return tph_ref * power_fraction * axb_term * f80_term * fines_term


def hardness_adjusted_p80(p80_base_um: float, wi_base: float, wi_now: float,
                           hold_tph: bool = True) -> float:
    """
    03_domain.md §7.3: "at fixed power, TPH ~ 1/Wi... Holding TPH instead coarsens P80 from
    180 to ~242 um" for Wi 13->16 (+23% Wi). We generalise: if the operator holds throughput,
    P80 scales with the Wi ratio raised to the power that reproduces that 180->242 um example.
    ln(242/180) / ln(16/13) = 0.2957 / 0.2076 = 1.424.
    """
    if not hold_tph:
        return p80_base_um
    ratio = wi_now / wi_base
    exponent = 1.424  # [D] calibrated to the §7.3 worked example
    return p80_base_um * (ratio ** exponent)


def plant_availability(base_availability: float, relines_penalty: float = 0.0,
                        derate_penalty: float = 0.0) -> float:
    return max(0.0, min(1.0, base_availability - relines_penalty - derate_penalty))


if __name__ == "__main__":
    w = bond_work_kwh_t(13.0, 2500.0, 180.0)
    assert abs(w - 7.1) < 0.3, w  # 03_domain.md §7.3 worked example: 7.1 kWh/t
    tph = throughput_from_power_tph(2 * 22000 * 0.9, C.ETA_CIRCUIT, w)  # not the exact doc check, sanity only
    assert tph > 0
    p80 = hardness_adjusted_p80(180.0, 13.0, 16.0)
    assert 230.0 < p80 < 255.0, p80  # doc: ~242 um
    print("models/comminution.py self-check OK:", w, p80)
