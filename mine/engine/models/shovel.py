"""
Shovel dig-rate and loading model. 03_domain.md §2.4, §2.6, §4.3.
"""
from __future__ import annotations

from . import constants as C


def swing_time_s(base_swing_min: float = C.LOAD_SWING_MEAN_MIN, x80_mm: float = 520.0,
                  x80_ref_mm: float = 520.0, digrate_exp: float = C.SHOVEL_DIGRATE_X80_EXP,
                  hydraulic_penalty: float = 0.0) -> float:
    """
    Swing/dig time per pass, modulated by fragment size (finer blast -> faster dig,
    03_domain.md §4.3: "shovel dig rate +5-10% per -20% X50, dig time ~ X80^0.3-0.5") and by a
    cold-hydraulic response penalty (§5.4, -10 to -20% response -> cycle +10%, applied as a time
    multiplier here, i.e. (1+penalty) lengthens swing time).
    """
    base_s = base_swing_min * 60.0
    frag_mult = (x80_mm / x80_ref_mm) ** digrate_exp
    return base_s * frag_mult * (1.0 + hydraulic_penalty)


def dig_rate_tph(bucket_m3: float, t_swing_s: float, fill: float = C.FILL_FACTOR,
                  rho_loose: float = C.RHO_LOOSE_T_M3, availability: float = 0.88,
                  utilisation: float = 0.85) -> float:
    """Q_shovel(t/h), see models.truck.shovel_productivity_tph for the full formula (§2.6)."""
    from .truck import shovel_productivity_tph
    return shovel_productivity_tph(t_swing_s, bucket_m3, fill, rho_loose, availability, utilisation)


def queue_wait_min(busy_until_s: float, now_s: float) -> float:
    """Wait time (minutes) for a truck requesting this shovel as a single-server resource."""
    return max(0.0, (busy_until_s - now_s) / 60.0)


if __name__ == "__main__":
    t = swing_time_s()
    assert abs(t - 33.0) < 0.1, t
    q = dig_rate_tph(22.0, t)
    assert q > 0
    print("models/shovel.py self-check OK:", t, q)
