# 03 - Domain Parameters for a Kazakh Open-Pit Cu-Au(-Mo) Mine + Concentrator Digital Twin

Prepared 2026-10-10. Reference assets: **KAZ Minerals Bozshakol** (Cu-Au-Mo, Pavlodar region, 30 Mtpa) and **Aktogay** (Cu-Mo, Abai/East Kazakhstan region, 25 Mtpa expanded to 50 Mtpa sulphide).
Purpose: the numeric parameter set behind the Kyzyl-Tas simulation engine (`mine/engine/`), with a source for each number, the equations used, and the cross-module causal links. Code comments cite this file by section (for example `03_domain.md §2.3`). The design-stage numbers here are refined in the engine where noted in [SUBMISSION.md](../../SUBMISSION.md).

## 0. How to read the evidence tags

| Tag | Meaning |
|---|---|
| **[R]** | Reported by the operator (KAZ Minerals reports and presentations) |
| **[V]** | Vendor or OEM specification |
| **[L]** | Peer-reviewed or technical literature, standards, or regulators |
| **[D]** | Derived by us from cited numbers. The calculation is shown so it can be audited. |
| **[A]** | Engineering assumption, with a range, used where no public site data exists. Treated as synthetic/assumed. |

Sources are numbered `[S#]` (web) and `[T#]` (textbooks/papers). The full list is in Section 12.

> **Key validation result.** The parameter set below reproduces Bozshakol's reported 2020 output to within a few percent. Using 31.6 Mt processed, 0.51 % Cu and 79.7 % recovery [S1] gives 31.6e6 × 0.0051 × 0.797 = **128.4 kt Cu in concentrate**, against 127.8 kt reported [S1]. Re-pricing the reported 2020 revenue ($729 M Cu at $6,198/t, $281 M Au at $1,770/oz [S2]) to 2026 prices gives **≈ $2.39 bn/yr**. The twin's base case gives ≈ $2.2 bn/yr (§9). Truck-fleet arithmetic (18 × 785C × 18,000 trips/yr × 140 t ≈ 45 Mt/yr [S3]) matches 4 shovels × 11 Mt/yr = 44 Mt/yr [S3] and a 0.7 strip ratio on ~26 Mt sulphide ore (§1).

---

## 1. Mine geometry, reserves, throughput, shifts

### 1.1 Reference-site facts

| Parameter | Bozshakol | Aktogay | Tag / source |
|---|---|---|---|
| Design ore throughput | 25 Mtpa main sulphide + 5 Mtpa clay plant = **30 Mtpa** | 25 Mtpa (Conc. 1), **50 Mtpa** after 2nd concentrator (2021) | [R] S3, S5, S1, S6 |
| Actual ore processed | 31.6 Mt (2020), 29.5 Mt (2019) | 24.1 Mt sulphide (2020); 50.4 -> 62.1 Mt (2022 -> 2025) | [R] S1, S6 |
| Ore extraction | 32.1 Mt (2020), 35.7 Mt (2019) | 41.2 Mt (2020) incl. 10.5 Mt oxide; 81.0 Mt (2025) | [R] S1, S6 |
| Strip ratio (waste:ore) | **0.7 : 1** LOM estimate | **~0.2** (MDO); 2025: 26.7 Mt waste / 81.0 Mt ore = 0.33 | [R] S3; [R] S6; [D] |
| Resource | 1,173 Mt @ 0.35 % Cu, 0.14 g/t Au, 0.88 g/t Ag, 0.004 % Mo (0.2 % Cu cut-off, JORC) | M&I 1,597 Mt sulphide @ 0.33 % Cu, 0.008 % Mo; oxide 121 Mt @ 0.37 % (0.2 % cut-off) | [R] S3 |
| Reserve (Aktogay, 31 Dec 2021) | - | P&P 1,372 Mt sulphide @ 0.32 % Cu, 0.008 % Mo | [R] S6 |
| Head grade processed (2020) | **0.51 % Cu**, **0.26 g/t Au** | **0.56 % Cu** (sulphide); 0.28 % (oxide to heap) | [R] S1 |
| LOM grade | 0.36 % Cu (c.40-yr life) | 0.33 % Cu sulphide (~25-yr life incl. expansion) | [R] S1 |
| Mineralised body | 2 pits (MDO) | 2.1 km × 1.6 km footprint, mineralised to 600-860 m depth; oxide cap avg 18 m (max 60 m) | [R] S6, S7 |
| Workforce | ~1,500 at full operation; 1,200-bed camp 3 km from plant | 1,500 planned; 5,031 employees in 2020 (incl. expansion) | [R] S3, S4, S6 |

### 1.2 Twin geometry (synthetic, Bozshakol-scale)

| Parameter | Value (range) | Tag / justification |
|---|---|---|
| Final pit (twin) | 3.0 km × 1.8 km, 450 m deep after ~15 yr | [A], scaled from the Aktogay footprint [S6] |
| Bench height | **15 m** (12-15 m) | [A]. Matches the max cutting height of 20-24 m³ class shovels such as the Hitachi EX3600 [S13] and SME practice [T9] |
| Bench face angle / berm | 65-70° / 8-10 m catch berm every 1-2 benches | [A] [T12] |
| Overall slope angle | 40-48° (ramps included) | [A] [T12] |
| Ramp grade | **8 % design, 10 % max** | [A] [T9][T12]. Sets haulage speed (§2). |
| Ramp width (two-way) | ≥ 3.5 × truck width + berm + ditch -> ~30 m for 785C (6.6 m wide) / ~35 m for 793F (7.6 m) | [A] [T12] |
| One-way haul distance, ore to crusher | 3.0 km (early) -> 5-6 km (late) | [D] from the 22-min cycle implied by 18,000 trips/yr/truck [S3], see §2.5 |
| Haul distance, waste to dump | 2.5-4.5 km | [A] |
| Material movement | ore 30 Mtpa + waste 21 Mtpa (SR 0.7) = **51 Mtpa** | [D] from S3/S5 |
| Shifts | 2 × 12 h, 4 crews, 365 d/yr. 15/15 fly-in/fly-out "vakhta" rotation; 30-45 min/shift lost to change-over, pre-start and blasting window | [A]. Bozshakol plans single and double shifts during pre-production [S4] and runs camp-based shift work [S3] |
| Shovel hours | ~6,500-7,000 operating h/yr per shovel | [A], consistent with 11 Mt/yr per shovel [S3] at ~1,600-1,700 t/op-h |

Recommended **simulation time-step**: 1 s for kinematics and 1 min for the plant. A shift is 720 min.

---

## 2. Haulage and dispatch

### 2.1 Fleet at reference sites

| Site | Trucks | Loading | Drills | Dispatch | Source |
|---|---|---|---|---|---|
| Bozshakol (start-up) | **18 × Cat 785C** (140 t max), Cat 777D (haul + water) | **4 × Hitachi 21 m³ electric shovels**, 11 Mt/yr each; EX3600, EX870 excavators; Cat 993K FEL | 4 × Sandvik D55 rotary | **Leica (now Hexagon) Jigsaw automated dispatch** | [R] S3, S4, S19 |
| Aktogay (MDO list) | Cat 785C/D, 793D, 777D | Hitachi EX5600, EX3600, ZX870, EX1200; Cat 993K/994K | Sandvik D55 ×4, Epiroc D65, PV-231 | Hexagon | [R] S6, S19 |

For the twin, use **mixed fleet A** (as-built): 785C/D trucks with 21-24 m³ shovels. Use **fleet B** (modernisation what-if): Cat 793F or Komatsu 830E-5 with EX5600-class shovels.

### 2.2 Truck specifications

| Model | Nominal payload | GMW (gross) | Net power | Max speed loaded | Drive | Source |
|---|---|---|---|---|---|---|
| Cat 785C | 136 t (≈140 t max per KAZ) | 249 t | 1,005 kW (1,348 hp), Cat 3512B | 55 km/h | mechanical | [V] S11; [R] S3 |
| Cat 793F | 226.8 t (227-231 t by rating) | 386 t (390 t alt.) | 1,848 kW net / 1,976 kW gross, C175-16 | 60 km/h | mechanical | [V] S10 |
| Komatsu 830E-5 | 227 t (230 t AU rating) | ~409-411 t operating | 1,865 kW (2,500 hp), Cummins QSK60 or Komatsu SDA16V160; 2,700 hp option | ~64 km/h | AC electric; trolley-ready | [V] S12 |

### 2.3 Speed versus grade (rimpull/power model)

Rimpull charts are machine-specific. Cat Performance Handbook Ed. 50 refers users to the machine brochures [S14]. Use this physics surrogate, which reproduces charted speeds to roughly ±15 %:

```
TR      = GR + RR                              (total resistance, % of GVW)
F_req   = m·g·TR/100                           (N)
v_power = η_d · P_net / F_req                  (m/s), η_d = 0.80 mechanical, 0.85 AC-electric   [A][T9]
v       = min(v_power, v_gear_max, v_limit_zone)
Downhill loaded: v = min(v_retarder(GR-RR), v_limit_zone)  (retarder-limited, use 15-25 km/h on −8...−10 %)  [A]
RR      = 2 % + 0.6 %·(tyre penetration, cm)   Cat rule of thumb [S14]
          -> 2 % (well-maintained), 3 % (typical), 4-5 % (wet/thaw), 8-10 % (soft)   [S14][T9]
```

Example ([D]): a 793F loaded at 386 t on a 10 % ramp with RR 2.5 % gives TR = 12.5 % and v = 0.80 × 1.848e6 / (386e3 × 9.81 × 0.125) = 3.90 m/s = **14.0 km/h**. The 785C loaded (249 t, 1.005 MW) gives 0.8 × 1.005e6 / (249e3 × 9.81 × 0.125) = 2.63 m/s = **9.5 km/h**. Empty trucks go uphill at roughly twice the loaded speed. Flat-haul speeds are capped by site limits (§5).

| Segment | Loaded (km/h) | Empty (km/h) | Tag |
|---|---|---|---|
| In-pit ramp +8-10 % | 10-14 | 22-28 | [D] equation above |
| Flat haul road (RR 2-3 %) | 35-45 (site cap 50) | 45-50 (cap) | [D]/[A] |
| Down-ramp | 15-25 (retarder) | 30-40 | [A] |
| Loading/dump area | ≤ 15-20 | ≤ 15-20 | [A], site rules |

### 2.4 Cycle-time components

| Component | Distribution (minutes) | Tag / basis |
|---|---|---|
| Spot at shovel | Tri(0.3, 0.5, 1.0) | [A] [T9] |
| Load | n_pass × t_swing + 0.1, t_swing ~ N(0.55, 0.08) min (30-36 s hydraulic, 28-32 s rope) | [A] [T9][S13] |
| Haul loaded | from §2.3 segment kinematics | [D] |
| Queue at dump/crusher | M/D/1 or event-driven; crusher dump bay 2 trucks | [A] |
| Spot + dump | Tri(0.7, 1.0, 1.5) | [A] [T9] |
| Return empty | §2.3 | [D] |
| Queue at shovel | emergent from dispatch | - |

Passes per truck: `n_pass = ceil(payload / (V_bucket · fill · ρ_loose))`, with in-situ ρ ≈ 2.65-2.75 t/m³, swell 1.4-1.5 (loose ρ ≈ 1.8-1.9 t/m³) and fill factor 0.85-0.95 [A][T9]. A 21-22 m³ bucket carries 32-37 t, so a 785C takes **4 passes** (~2.3 min) and a 793F **6-7 passes** (~3.6 min). An EX5600-class bucket (~29-34 m³) gives a 793F **4-5 passes**.

### 2.5 Calibration from Bozshakol's published fleet plan [D]

* 18 trucks × 18,000 trips/yr × 140 t = **45.4 Mt/yr**, against 4 shovels × 11 Mt/yr = **44 Mt/yr** [S3]. The figures are consistent.
* 18,000 trips/yr = 49.3 trips/day. At 18 effective h/day (availability 88 % × utilisation 85 %) that is a **cycle of ~22 min**.
* Subtracting load 2.3 + spot 0.5 + dump 1.0 + queues 2.0 leaves **~16 min of travel**. At average speeds of 20 km/h loaded and 30 km/h empty, that is **≈ 3.2 km one-way**.

### 2.6 Productivity and match factor

```
Q_truck (t/h)  = Payload · 60 / T_cycle · A_m · U · E          (E = 50/60 'job efficiency')   [T9]
Q_shovel (t/h) = (3600 / t_swing_s) · V_b · fill · ρ_loose · A_m · U · E
MF (Douglas 1964 [T5]) = (N_trucks · t_load) / (N_shovels · T_cycle)
     MF < 1 -> truck-limited (shovels idle); MF > 1 -> shovel-limited (trucks queue). Target 0.9-1.1.
Heterogeneous fleets: Burt & Caccetta (2007) [T5].
```
Bozshakol start-up check [D]: MF = 18 × 2.3 / (4 × 22) = **0.47** using full calendar fleets. With ~25 % of trucks down or on waste/ancillary duty, and long early-year haul cycles, effective MF on ore is closer to 0.6-0.8. The twin should therefore show **truck-limited** behaviour. Shovel outages hurt less than truck outages unless the failed shovel is the ore face (§11-S1).

### 2.7 Fuel burn

```
FC (L/h) = P_rated(kW) · LF · BSFC / ρ_diesel ;  BSFC ≈ 0.21-0.22 kg/kWh,  ρ = 0.835 kg/L   [A][T9]
LF (load factor) : low 0.25-0.35, medium 0.35-0.50, high 0.50-0.65                             [A][S14]
```
| Truck | LF 0.30 | LF 0.45 | LF 0.60 |
|---|---|---|---|
| 785C (1,082 kW gross) | 82 L/h | 123 L/h | 164 L/h |
| 793F (1,976 kW gross) | 150 L/h | 225 L/h | 300 L/h |

These are [D] from the equation. Tier 4 793F burns up to 5.3 % less than Tier 2 [S15]. **Idle** is 15-25 L/h for the 785C and 25-35 L/h for the 793F [A]. Winter idling to keep engines warm is a real fuel penalty (§11-S2). Recommended fuel-tank model: 793F has 4,354 L and 785C has 3,800 L [A, OEM brochures] -> refuel every 1-1.5 shifts, with 15-20 min refuel events.

### 2.8 Dispatch algorithms to implement

| Policy | Description | Expected effect | Source |
|---|---|---|---|
| Fixed / "locked" allocation | trucks hard-assigned to a shovel each shift | baseline | [T6] |
| Nearest / SQ (shortest queue) / SPTF | heuristics, as in OpenMines | +2-6 % vs fixed | [S18] (MIT code available) |
| **MTCT** (minimise truck cycle time) / MSWT (min. shovel waiting) | greedy, real-time | +5-10 % | [T6] Munirathinam & Yingling 1994 review |
| **Two-stage LP + real-time assignment** (White & Olson 1986, Modular DISPATCH style) | LP sets target flow rates per path subject to blend (grade) and crusher feed constraints; real-time stage assigns next truck to the path most "behind" | +5-15 %, plus grade control on the blend | [T6] |
| RL (PPO) | OpenMines ships a PPO dispatcher | research | [S18] |

KAZ deploys Leica/Hexagon fleet management that tracks material from loading to dumping, records truck cycle data, and does real-time optimisation [S4][S19]. **Dynamic LP-based dispatch is therefore the realistic baseline for KZ.** "Fixed" can be the degraded-mode fallback, for example after a comms outage.

#### Blend constraint (LP)

Σ_i f_i·g_i / Σ_i f_i ∈ [g_min, g_max] at the crusher, where f_i is the flow from face i. Also Σ_i f_i ≥ crusher target and f_i ≤ shovel capacity_i.

### 2.9 Trolley assist

Neither Bozshakol nor Aktogay uses trolley assist (no public mention; the Cat 785C/793F are mechanical drive). Cat trolley needs AC electric-drive trucks (795F, 794/796/798 AC) [S16]. Speed on grade rises up to **100 %**, and fuel and engine cost on trolley sections falls by more than **90 %** [S16] (Boliden Aitik). Kansanshi reports up to 90 % diesel saving on laden up-ramps and ~2 min saved per trolley stretch [S17]. Whole-fleet fuel saving is 30-70 % depending on coverage [S17-ABB]. **Kazakhstan caveat ([D]):** see §6.4. On a coal-heavy grid, trolley assist can *raise* CO₂.

### 2.10 Tyre wear

* Tyre life 4,000-8,000 h for 40.00R57 / 46/90R57 (rigid haulers); cut damage causes 30-50 % of removals [A][T9].
* TKPH constraint: `TKPH_site = Q_mean_tyre_load (t) × V_mean_cycle (km/h)` must be ≤ the tyre's TKPH rating. A breach means overheating and a speed cap [A][T9].
* Wear multiplier `k = 1 + 0.03·(RR% − 2) + 0.5·I(overload>10 %) + 0.2·I(T<−25 °C)` [A]. This links road maintenance, payload policy and winter to cost (§11-S6).
* Cat 10/10/20 payload policy: ≤ 10 % of loads may exceed 110 % of target payload, and none may exceed 120 % [V, Cat payload policy, see S14]. Implement it as a shovel-loading constraint and as a driver of frame/strut damage.

---

## 3. Geology, ore quality, blending, cut-off

### 3.1 Block model concept (synthetic)

* Block size 15 m × 15 m × 15 m (= bench height). ρ = 2.70 t/m³ gives 9,113 t/block [A][T12].
* Attributes per block: Cu %, Au g/t, Mo %, S %, **ore type** (sulphide / clay-sulphide / oxide / waste), **BWi** (kWh/t), **Axb** (SAG), recovery class, and a destination flag.
* Grade generation: lognormal Cu with mean 0.36 % and CV 0.5-0.7 in ore. Use sequential Gaussian simulation (SGS) with a spherical variogram (range 80-150 m horizontal, 40-60 m vertical, nugget 20-30 %) [A][T12]. Correlate Au with Cu (ρ ≈ 0.5-0.7 in porphyry Cu-Au) and BWi weakly negatively with Cu [A]. GeoMet [S51] is a real CC BY 4.0 dataset of porphyry-style drill holes with DWT/BWi and LCT recovery. **Calibrate the copulas on it.**
* Variability seen in real data ([R] S1, quarterly Bozshakol): Cu head grade **0.49-0.52 %**; Au **0.24-0.30 g/t**; recovery **79.0-81.1 %**; Au recovery **56-60.5 %**. Q4 2020 Au recovery fell to 56 % because of high sulphur in the main concentrator feed and oxidised ore at the clay plant [S1]. Aktogay Q4 2020 Cu recovery fell to 84.6 % from 86.1 % because of "temporary variation in the ore feed blend" [S1]. **These are real-world examples of blend-to-recovery coupling to cite.**
* Grade decline: Aktogay's 2020 processed grade was 0.56 % against the 0.33 % resource grade, because higher-grade zones are mined first [S1]. Bozshakol 2018 guidance was 0.44 % [S2-2017]. In multi-year runs the twin should taper head grade toward LOM grade.

### 3.2 Stockpiles and blending

* ROM pad ahead of the gyratory (finger stockpiles by grade bin: HG > 0.5 %, MG 0.3-0.5 %, LG 0.2-0.3 %) [A].
* Crushed-ore coarse stockpile between crusher and SAG. Bozshakol has a crushed-ore stockpile with apron-feeder reclaim [S4]. Live capacity is ~12 h of SAG feed (~40 kt) [A]. This is the main **buffer that decouples mine disruptions from the mill**.
* Long-term LG stockpile. Aktogay stockpiled lower-grade sulphide while extraction ran ahead of plant capacity [S1]. Bozshakol blended high-grade stockpiled ore into Q4 2020 feed [S1].
* Model the stockpile as a well-mixed tank (`dG/dt = (Q_in·(g_in − G))/M`) or FIFO layers. Grade uncertainty at reclaim is ±10-15 % relative [A].

### 3.3 Grade control

* Blast-hole sampling or RC grade-control drilling. Bozshakol started RC grade-control drilling in July 2015 [S4].
* Ore/waste misclassification: dilution 3-8 %, ore loss 2-5 % [A][T12]. Blast movement of 2-6 m shifts boundaries unless it is measured [A].

### 3.4 Cut-off grade

Breakeven (marginal) cut-off [T4 Lane]:
```
g_c (%Cu) = (c_proc + c_GA + c_sell_per_t_ore) / ( (P − r_ref) · y_rec · pay · 10 )   (P in $/kg -> ×10 kg per %-t)
```
At P = $14.5/kg, y = 0.80, pay = 0.965, c_proc + G&A ≈ $6.5/t [D, §9]: g_c = 6.5 / (14.5 × 0.80 × 0.965 × 10) = **0.058 % Cu**, before Au credits.
Mill-constrained Lane cut-off (`g = (h + f/H)/((p−r)·y)`, where f/H is the fixed cost per tonne of mill capacity) gives a much higher operating cut-off of ~0.15-0.25 % [A][T4]. This matches KAZ's 0.2 % reporting cut-off [S3]. Below that, material goes to the LG stockpile. The twin should expose **price -> cut-off -> ore/waste classification -> strip ratio -> fleet requirement** (§11-S10).

---

## 4. Drilling and blasting

### 4.1 Design parameters

| Parameter | Value (range) | Tag |
|---|---|---|
| Drills | Sandvik D55SP rotary (Bozshakol ×4), Epiroc D65 / PV-231 | [R] S3, S6 |
| Hole diameter | **251 mm** (229-270 mm) ore; 311 mm waste option | [A]. Within the D55SP / PV-231 range [V, OEM] |
| Bench / sub-drill / stemming | 15 m / 1.5 m / 5-6 m (≈ 20-25 × d) | [A][T9] |
| Burden × spacing | Ore 6.0 × 7.0 m; waste 7.0 × 8.5 m | [A], gives PF below |
| Explosive | ANFO (dry) / emulsion blends (wet); ρ 0.85 / 1.15-1.25 g/cm³ | [R] "Anfo/Emulsion" S3; [A] densities |
| Powder factor | **0.30-0.40 kg/t ore**, 0.20-0.30 kg/t waste | [A]. The PNG mine-to-mill case moved from 0.24 to 0.38 kg/t [S20-community], [S20] |
| Drill penetration | 25-40 m/h (UCS 80-150 MPa porphyry) | [A][T9] |
| Blast size / frequency | 0.5-1.5 Mt per blast, 3-5 blasts/week, daytime window | [A] |

### 4.2 Fragmentation (Kuz-Ram) [T2][T3]

```
X50 (cm) = A · K^(−0.8) · Q^(1/6) · (115/RWS)^(19/20)        Kuznetsov-Cunningham
  A   = rock factor = 0.06·(RMD + JF + RDI + HF)  (porphyry: 7-10)
  K   = powder factor (kg/m³), Q = charge mass per hole (kg), RWS = 100 for ANFO
n  (uniformity) = (2.2 − 14·B/d)·sqrt((1 + S/B)/2)·(1 − W/B)·(|BCL−CCL|/L + 0.1)^0.1·(L/H)   (Cunningham 1987)
P(x) = 1 − exp(−0.693·(x/X50)^n)          (Rosin-Rammler);  X80 = X50·(ln5/ln2)^(1/n) = X50·2.322^(1/n)
```
Worked example ([D]: A = 7, d = 251 mm, charge 10.5 m of ANFO-emulsion at ~54 kg/m gives Q ≈ 567 kg, n = 1.3):

| Case | K (kg/m³) | PF (kg/t) | X50 | X80 |
|---|---|---|---|---|
| Base | 0.81 | 0.30 | 272 mm | 520 mm |
| Intensified | 1.08 | 0.40 | 216 mm (−21 %) | 413 mm |

The Swebrec function improves the fines tail and is recommended if the El Aljibe dataset [S53] is used to calibrate it.

### 4.3 Mine-to-mill coupling

| Effect | Magnitude | Source |
|---|---|---|
| SAG throughput from finer blast | **+5-15 %** (SAG transfer size); +10-20 % (ball-mill feed size) | [L] McKee 2013 via Giblett, AusIMM [S20] |
| Case: blast redesign | +12 % SAG tph, +50 % material < 25.4 mm, −13 % SAG specific energy | [L/vendor] Hexagon Split [S21] |
| Case: PNG gold | PF 0.24 -> 0.38 kg/t; SAG feed P50 75 -> 35 mm; +15 % throughput | [L] [S20-community] |
| Non-linearity | throughput plateaus or falls at very high PF | [L] Red Dog [S22] |
| Shovel dig rate | +5-10 % per −20 % X50 (dig time ∝ X80^0.3-0.5) | [A] [T9] |

Twin surrogate [A]:
`TPH_SAG = TPH_ref · (P_SAG/P_ref) · (Axb/Axb_ref)^0.8 · (F80_ref/F80)^0.25 · (fines_25mm/fines_ref)^0.15`. Calibrate so that −20 % X50 gives +8 to +10 % TPH.

### 4.4 Blast exclusion and haulage

* Exclusion radius: **500 m personnel, 300 m equipment** (larger for flyrock-prone designs) [A]. These are typical site rules under Kazakh industrial-safety rules (Order No. 352, 30 Dec 2014, *verify*) [S59].
* Blast window: 30-60 min clear-out, firing, then fume clearance. Re-entry is ≥ **30 min** after firing and requires a gas-detector check [L] [S30]. NOx/CO management follows the AEISG Code (Ed. 2, 2011) [S29].
* Simulation effect: haul roads and shovels inside the radius are `UNAVAILABLE` from T_clear to T_reentry. Dispatch must re-plan around them.

---

## 5. Safety and environment

### 5.1 Dust (PM10)

| Item | Value | Source |
|---|---|---|
| WHO AQG 2021 | PM10 **45 µg/m³ (24 h)**, 15 µg/m³ (annual) | [L] S24 |
| Kazakhstan ambient MPC (ПДК, inherited from RU/SanPiN approach) | PM10 **0.3 mg/m³ max one-time, 0.06 mg/m³ daily average** | [L] S25. Standards updated 2 Aug 2022, with a summation rule from 7 Mar 2025 [S26]. *Verify the official text on adilet.zan.kz.* |
| Haul-road emissions, US EPA AP-42 §13.2.2 | `E (lb/VMT) = k·(s/12)^a·(W/3)^b`, PM10: k = 1.5, a = 0.9, b = 0.45. s = silt % (mine haul roads 5-15 %), W = mean vehicle weight (short tons) | [L] S27 |
| Watering control efficiency | 50-75 % typical, decays over 1-3 h (summer). **Not possible below about 0 °C**: winter relies on chemical suppressants or no control | [L] S27; [A] |

[D] example: a 793F at a mean weight of (165 + 386)/2 ≈ 276 t (304 short tons) with s = 8 % gives E_PM10 = 1.5 × (8/12)^0.9 × (304/3)^0.45 = 1.5 × 0.694 × 7.98 = **8.3 lb/VMT ≈ 2.3 kg/vehicle-km** uncontrolled.

### 5.2 Post-blast gases

| Gas | Limits | Source |
|---|---|---|
| CO | NIOSH REL 35 ppm TWA, ceiling 200 ppm, IDLH 1,200 ppm | [L] S28 |
| NO₂ | NIOSH REL 1 ppm STEL, IDLH 20 ppm (OSHA C 5 ppm) | [L] S28 |
| Re-entry rule | ≥ 30 min after firing **and** gas test below limits. If not clear, retreat and retest | [L] S30, S29 |
| Twin model | Gaussian puff: `C(x,t) = M/((2π)^1.5 σx σy σz)·exp(...)`. Stability class F (winter inversion, wind < 2 m/s) gives a 3-5× longer clearance than class D | [A] standard dispersion theory |

### 5.3 Slope stability monitoring

* Ground-based radar (GroundProbe SSR, IDS IBIS) plus prisms. A TARP maps alarm levels to actions: pause mining -> withdraw personnel -> isolate area -> evacuate [L] S33 (Bingham Canyon), S31, S32.
* Real thresholds: Putra et al. (2023) give velocity alarms of 33-91 mm/day per area, ~12 h before failure, and a site alarm of 50 mm/day [L] S31. Bingham Canyon uses displacement, velocity, velocity ratio (VR) and inverse velocity as triggers [L] S33.
* Twin TARP [A, aligned to S31/S33]: **Green** < 5 mm/day; **Amber** 5-30 mm/day, or VR > 2 -> no access under the wall, haul road speed restriction. **Red** > 50 mm/day, or inverse-velocity forecast time of failure < 24 h -> evacuate the zone and close the ramp.
* Failure forecast, Fukuzono (1985) [T7]: `1/v(t) ≈ a·(t_f − t)` -> linear regression of 1/v against t gives t_f at 1/v = 0.

### 5.4 Weather (Kazakh steppe)

| Parameter | Value | Source |
|---|---|---|
| Winter extreme | **down to −40 °C (Dec-Feb)** at Bozshakol | [R] S3 |
| Aktogay mean Jan min / Feb min | −18.2 °C / −15.6 °C | [L] S34 |
| Summer max | +35 to +40 °C | [A] (continental) |
| Winter wind | 3-8 m/s typical, gusts 15-25 m/s in blizzards ("buran") | [L] S34-forecast pages; [A] |
| Seasonal production | Aktogay SX-EW winter rate **c.70 % of design** | [R] S4 |
| Cold-weather effects (twin) | below −30 °C: +30-45 min warm-up per start, hydraulic response −10-20 %, tyre/strut damage ×1.2, idle fuel ↑, outdoor work limits (regional akimat rules on temperature/wind) | [A] |

### 5.5 Speed limits and collision avoidance

* Haul roads 40-50 km/h; ramps 30 km/h; loading/dump zones 15-20 km/h; workshops 10 km/h [A]. Site limits are set in the project traffic management plan under KZ industrial-safety rules [S59].
* Collision warning and avoidance follows **ISO 21815-1:2022** and EMESRT PR-5A levels 7 (warn) / 8 (advise) / 9 (intervene) [L, ISO/EMESRT]. Proximity warning zone ~50 m, intervention ~15-20 m at 15 km/h [A].
* Visibility: fog or blizzard < 100 m -> speed cap 20 km/h. < 50 m -> stop [A].

---

## 6. Energy and emissions

### 6.1 Electricity

| Item | Value | Source |
|---|---|---|
| Bozshakol project power requirement | **214 MW**, fed from Ekibastuz GRES-1 (4,000 MW coal) via 220 kV | [R] S3, S4 |
| Bozshakol 2015 expected tariff | **4.9 USc/kWh** | [R] S3 |
| Main grinding installed | SAG 40'×26', **28 MW** GMD @ 9.31 rpm; 2 × ball 28'×44', **22 MW** each @ 10.99 rpm -> **72 MW** | [R] S3; [V] ABB S8 |
| Aktogay Conc. 1 | SAG 28 MW (40'×26'), 2 × ball 28'×44', 2 × 7 MW HPGR, 2 × 3 MW IsaMill M10000 | [R/L] S6 |
| Gyratory (Bozshakol) | FLSmidth 60"×113", 4,186 t/h, 750 kW | [R] S3 |
| Overland conveyor | 3.8 km, 1.6 m belt, 4,880 t/h, 5 m/s, 3,640 kW | [R] S3 |
| Regrind | IsaMill M10000, 3,000 kW | [R] S3 |
| Tailings pumps | 2 trains × 4 stages × 850 kW | [R] S3 |
| Generator tariff caps 2026-2032 (frozen at 2025 levels) | Ekibastuz GRES-1 **9.50 KZT/kWh**; GRES-2 15.67; Kazakhmys Energy 30.24 | [L] S41 |
| Delivered industrial tariff (twin) | **16-22 KZT/kWh** (cap + KEGOC transmission + balancing) ≈ **3.5-4.8 USc/kWh** at 457 KZT/USD | [A] built from S41, S43. Consistent with the 2015 4.9 USc [S3] |
| Specific energy (twin) | grinding ~17-19 kWh/t (72 MW × 0.85 draw / 3,425 t/h); total concentrator 25-30 kWh/t; mine electric (shovels, drills, pumps) 1-2 kWh/t moved | [D] from S3; [A][T8] |

### 6.2 Diesel

| Item | Value | Source |
|---|---|---|
| Retail diesel price KZ | **341 KZT/L** (Jun 2026) ≈ $0.75/L | [L] S42, S43 |
| Twin site price | 300-340 KZT/L (bulk contract) | [A] |
| Mine diesel intensity | 0.25-0.45 L/t moved (785C: 123 L/h ÷ ~400 t/h ≈ 0.31 L/t) | [D] §2.7 |
| Fleet annual (18 × 785C + ancillaries) | trucks ~14 ML + ancillary/drills ~5 ML ≈ **19 ML/yr** | [D] 18 × 6,500 h × 120 L/h; [A] 35 % ancillary |

### 6.3 Emission factors

| Factor | Value | Source |
|---|---|---|
| Diesel CO₂ | **2.68 kg CO₂/L** (IPCC 74,100 kg/TJ × NCV 43.0 TJ/Gg × 0.84 kg/L). UK DESNZ: 2.66 kg CO₂e/L | [L] S35, S36 |
| KZ grid (consumption, recent) | 603 gCO₂e/kWh (Apr 2025-Mar 2026, LowCarbonPower); ~805 g/kWh (2025, inzonex citing Ember/OWID); ~1.00 t/MWh to 2014 (UNDP); 85 % fossil, 15 % low-carbon in 2025 | [L] S37, S40, S39, S38 |
| **Twin choice** | **0.80 kgCO₂/kWh central**, sensitivity 0.60-1.05. Use **1.05** for a direct Ekibastuz coal supply (site-specific market-based) | [A] from S37-S40 |
| Annual footprint (twin) | electricity 29 Mt × 32 kWh/t = 0.93 TWh -> **~740 kt CO₂**; diesel 19 ML -> **~51 kt CO₂** | [D] |

#### Insight

about 94 % of Scope 1+2 comes from purchased power. Grid factor and mill efficiency dominate decarbonisation, not truck diesel.

### 6.4 Trolley-assist carbon paradox [D]

1 L of diesel = 35.9 MJ. At ~38 % engine efficiency that is 3.8 kWh at the shaft. An electric trolley delivering the same wheel work needs ≈ 4.2 kWh from the grid at ~90 % efficiency. At 0.80 kg/kWh that is **3.4 kg CO₂, against 2.68 kg for burning the litre of diesel**. Break-even grid factor is ≈ **0.64 kg/kWh**. On today's Kazakh grid, trolley assist **cuts cost** (4.2 kWh × $0.04 = $0.17 against $0.75/L diesel) and **increases speed on grade**, but **raises CO₂** unless power is renewable or a PPA. It is a realistic constraint the twin reproduces.

---

## 7. Processing

### 7.1 Flowsheet (Bozshakol/Aktogay, identical engineering [S3])

Haul truck -> gyratory -> overland conveyor -> crushed-ore stockpile -> apron feeders -> SAG (with pebble crusher / HPGR) -> ball mills + cyclones (P80 ~180 µm) -> rougher flotation -> regrind (IsaMill) -> cleaners -> Cu-Mo bulk conc -> Mo separation -> Cu conc thickening and filtration -> rail. Tailings go to 80 m high-rate thickeners and then to the TSF [S3]. The clay plant (5 Mtpa) runs separately [S3].

### 7.2 Capacity

| Unit | Design | Source |
|---|---|---|
| Gyratory | 4,186 t/h (60"×113"). Aktogay 63"×114" | [R] S3, S6 |
| Conveyor | 4,880 t/h | [R] S3 |
| SAG | **3,425 t/h** | [R] S3 |
| Ball mills | 1,706 t/h each (×2) | [R] S3 |
| Flotation | 1,576 t/h solids, FLSmidth/WEMCO self-aspirated | [R] S3 |
| Rougher / scavenger regrind | 157 / 84.5 t/h | [R] S3 |
| Thickeners | 2 × 80 m, 27,000 m³, 4,313 m³/h feed each | [R] S3 |
| Aktogay Conc. 1 | ~70,000 t/d; P80 180 µm | [R/L] S6 |
| Plant availability | **92-94 %**. Relines ~3/yr at Aktogay in 2020, and Q4 2020 Bozshakol throughput fell 3 % QoQ for scheduled relines | [R] S1; [A] |

### 7.3 Comminution equations

```
Bond (1961) [T1]:   W (kWh/t) = 10·Wi·(1/√P80 − 1/√F80)        (P80, F80 in µm)
Throughput:         TPH = P_draw(kW) · η_circuit / W            η_circuit ≈ 0.75-0.90 (operating WI / lab WI)
Morrell SMC (2004) [T10] alternative for SAG-ball: W = Mia·4·(x2^f(x2) − x1^f(x1)),  f(x) = −(0.295 + x/1,000,000)
```
* Porphyry Cu BWi range **5.7-20.2 kWh/t** (Sarcheshmeh, lithology-driven) [L] S23. Twin base **Wi = 14 kWh/t** (σ 1.5, by domain); clay-rich ore 9-11 kWh/t [A].
* [D] check: ball circuit with F80 = 2,500 µm and P80 = 180 µm at Wi = 13 gives W = 130 × (1/13.42 − 1/50) = **7.1 kWh/t**. Two × 22 MW × 0.9 / 7.1 = 5,580 t/h of ball capacity, which exceeds SAG capacity. Bozshakol is therefore **SAG-limited**, which is typical. The **SAG + pebble circuit governs throughput** and responds to Axb and feed size (§4.3).
* Hardness sensitivity [D]: at fixed power, TPH ∝ 1/Wi. Wi 13 -> 16 gives **−19 % TPH**. Holding TPH instead coarsens P80 from 180 to **≈ 242 µm**.

### 7.4 Flotation recovery

#### Model A, constant-tails (best fit to KAZ data) [D]

```
R = (c/f)·(f − t)/(c − t)     f = head grade, c = conc grade, t = tails grade
```
* Aktogay check: f = 0.361 %, c = 24.3 %, t = 0.059 % gives R = 24.3 × 0.302 / (0.361 × 24.241) = **83.9 %**, against 83.8 % reported [S6].
* Bozshakol 2020 (f = 0.51 %, R = 79.7 %, c ≈ 22 % [A]) implies **t ≈ 0.105 % Cu** [D]. A higher tails grade is consistent with the gold-rich, clay-bearing ore.
* Consequence: recovery **falls with head grade**. At Bozshakol, 0.45 % gives 78.1 % and 0.55 % gives 81.6 %.

#### Model B, kinetic plus size/residence (for what-ifs)

```
R = R∞ · [1 − exp(−k·τ)]·φ(P80)·ψ(reagent)·ξ(ore type)
τ = V_cells·ε / Q_slurry  (throughput ↑ ⇒ τ ↓ ⇒ R ↓)
φ(P80) = 1 − 0.0006·max(0, P80 − 150)^1.3   -> 180 µm: −0.5 pp; 240 µm: −2.1 pp  [A, coarse-particle loss per Jameson 2012 T11]
ψ: collector dosage response saturating 1 − exp(−d/d0), d0 ≈ 10 g/t xanthate  [A]
ξ: clay/oxidised/high-S feed −2 to −5 pp Cu, −4 to −8 pp Au  [R] S1 (Au recovery 60.5 % -> 56 % in Q4 2020)
```
#### Gold

R_Au ≈ 55-62 % at Bozshakol [R] S1 (Q1 2018: 62.5 % at 0.29 g/t, S2-2018). Model R_Au = 0.60 ± 0.03 with the ξ penalties above.
#### Mo

75 % to Mo concentrate at 46.3 % Mo (Aktogay) [R] S6.

### 7.5 Products, tailings and water

| Item | Value | Source |
|---|---|---|
| Cu conc grade | 24.3 % Cu (Aktogay); twin 22-25 % | [R] S6; [A] Bozshakol |
| Mo conc grade | 46.3 % Mo | [R] S6 |
| Mass pull to Cu conc | f·R/c ≈ 0.51 × 0.797 / 22 = **1.85 %** | [D] |
| Tailings | ~98 % of feed mass, thickened to 55-65 % solids | [A][T8] |
| Fresh-water intensity | **0.57-0.60 m³/t** (Aktogay 2022-24) | [R] S6 |
| Water recycle | **70-80 %** | [R] S3, S6 |
| Aktogay raw water | 61,529 m³/day; process water 2,000 m³/h pipeline | [R] S6 |
| Bozshakol source | Satpayev canal (27 km), Shiderty reservoir 89 Mm³ | [R] S3 |
| Logistics | 18 km rail spur; 1,700 km to the Chinese border; DAF sales | [R] S3 |

---

## 8. Maintenance and reliability

### 8.1 Targets and parameters

Public site data is not available, so these are benchmarks [A] informed by [T9], [S47] and [S48]. Weibull fits are reported to beat other models for haul trucks [S47].

| Asset | PA target | UoA | MTBF (all unplanned) | MTTR | Weibull β / η (dominant failure mode) |
|---|---|---|---|---|---|
| Haul truck (785C/793F) | 88-92 % | 80-88 % | 60-120 h | 4-8 h (+ tow 1-2 h) | engine/cooling β 1.5, η 700 h; suspension (777D study S48) β 2.0, η 1,500 h; electrical β 0.8, η 400 h |
| Hydraulic shovel (EX3600/5600) | 85-90 % | 80-85 % | 40-80 h | 3-6 h | hydraulics β 1.2, η 250 h; GET/teeth β 3, η 300 h (planned) |
| Electric rope/hydraulic shovel (21 m³) | 88-92 % | 85 % | 60-100 h | 3-8 h (cable/trailing) | trailing-cable damage, Poisson λ = 1/500 h |
| Rotary drill | 80-88 % | 70-80 % | 30-60 h | 2-5 h | bit life 2,000-5,000 m |
| Gyratory crusher | 90-95 % | - | 300-500 h | 4-12 h | mantle/concave life 3-6 Mt; spider bushing β 2.5 |
| SAG / ball mill | 93-96 % | - | 500-1,500 h | 6-24 h | **relines ~3/yr** [R] S1, 72-120 h each; GMD trips λ = 1/2,000 h |
| Flotation / pumps | 95-98 % | - | - | - | slurry pump wear β 2.5, η 3,000 h |

Equations:
```
A_inherent = MTBF/(MTBF+MTTR);  R(t)=exp(−(t/η)^β);  h(t)=(β/η)(t/η)^(β−1)
Age-replacement PM optimum T*: minimise C(T) = [Cp·R(T) + Cf·(1−R(T))] / ∫0^T R(t)dt   (Cf/Cp ≈ 3-5 for engines)
OEE (mining) = Availability × Utilisation × Performance(rate) × Quality(payload/grade conformance)
```

### 8.2 Condition-monitoring signals (synthetic telemetry spec)

| Asset | Signal | Normal / Alarm | Basis |
|---|---|---|---|
| Truck engine | coolant temp | 85-95 °C / > 102 °C warn, > 107 °C shutdown | [A] OEM-typical |
| | oil pressure @ rated rpm | 350-450 kPa / < 200 kPa | [A] |
| | exhaust temp spread between banks | < 50 °C / > 100 °C (injector fault) | [A] |
| | oil analysis Fe, Cu, Si (ppm) | Fe < 30, Si < 15 / trending ×2 | [A] |
| | payload | 10/10/20 policy | [V] Cat |
| | tyre pressure/temp (TPMS) | ±10 % / > 85 °C | [A] |
| Shovel | hydraulic oil temp, pump case drain flow, swing-motor vibration | 50-70 °C / > 85 °C | [A] |
| Mills, crushers, conveyors | bearing vibration (ISO 10816-3, > 300 kW) | rigid: A/B 2.3, B/C 4.5, C/D 7.1 mm/s RMS; flexible: 3.5 / 7.1 / 11.0 | [L] ISO 10816-3 |
| | bearing temp, lube pressure, motor current, liner-wear (MillMapper) | ΔT > 15 °C above ambient trend | [A] |
| Crusher | power, CSS, cavity level | real-time | Jaw-crusher vibration/current dataset [S55] for anomaly-model training |

Predictive maintenance approaches: (1) Weibull/PHM with covariates (temperature, road RR, payload), the proportional-hazards model of [S47]. (2) Anomaly detection (isolation forest / autoencoder) on telemetry. (3) RUL regression. Expected value [A]: if PdM detects 60-70 % of engine failures with a 24-72 h lead, unplanned MTTR of 12-16 h becomes a 5-7 h planned job. That is **+2 to +3 pp truck PA**.

---

## 9. Economics

### 9.1 Prices and FX (October 2026)

| Item | Value | Source |
|---|---|---|
| LME Cu cash | **$14,689/t (9 Oct 2026)**; $14,335-14,797 range over 21 Sep-9 Oct | [L] S44 |
| Gold | ≈ **$4,330/oz** (spot, 18 Aug 2026) | [L] S45 |
| Mo | $40-50/kg [A] | *(source if Mo is modelled)* |
| TC/RC 2026 annual benchmark | **$0/t, 0.0 ¢/lb** (Antofagasta/Chinese smelters). Spot **negative, ≈ −$100 to −$127/dmt** (mid-2026) | [L] S46 |
| Payables | Cu 96.5 % (min. deduction 1 unit), Au 90-97 % depending on grade | [A] standard contract terms |
| USD/KZT | **457** (25 Aug 2026), 2026 range 457-513 | [L] S43 |
| 2020 reference | LME Cu $6,198/t, Au $1,770/oz, 413 KZT/$ | [R] S2 |

### 9.2 Costs

| Item | Value | Source |
|---|---|---|
| Bozshakol cash opex 2020 | $290 M / 31.6 Mt processed = **$9.2/t ore** (mine + plant + G&A) | [R] S2; [D] |
| Aktogay cash opex 2020 | $330 M / (24.1 + 10.6) Mt = **$9.5/t** | [R] S2; [D] |
| Gross cash cost | Bozshakol 126 ¢/lb, Aktogay 121 ¢/lb (2020); net after by-products Bozshakol **12 ¢/lb** | [R] S2 |
| Sustaining capex | Bozshakol $40 M (2020), $70 M (2021 guidance) | [R] S2 |
| Cost structure (Bozshakol plan, 6 categories) | shares 30 / 25 / 15 / 15 / 10 / 5 % across raw materials-fuel, raw materials-other, maintenance parts, **power**, salaries, other. *(PDF text extraction does not pair labels to slices unambiguously; check slide 46 of S3.)* | [R] S3 |
| **Twin 2026 unit costs** | mining **$2.0/t moved** (1.6-2.6); processing **$5.5/t ore** (4.5-6.5, of which power ≈ $1.2/t at 28 kWh/t × $0.042); G&A **$1.0/t ore**; rail + port to China **$40-60/wmt conc** | [A], reconciled to S2: $2.0 × 1.7 + 5.5 + 1.0 = $9.9/t ore, close to $9.2 × inflation/FX |
| MET (mineral extraction tax, KZ) | Cu 8.55 % of value; Au 7.65 % | [A, verify KZ Tax Code Art. 746] |

### 9.3 Revenue-per-hour model (KPI engine)

```
Cu_t/h   = TPH · f_Cu · R_Cu
Au_oz/h  = TPH · g_Au · R_Au / 31.1035
NSR_$/h  = Cu_t/h·pay_Cu·(P_Cu − RC·2204.6) − (Cu_t/h / c)·(TC + freight)
         + Au_oz/h·pay_Au·P_Au  − MET
Margin_$/h = NSR − TPH·(c_proc + c_GA) − (TPH·(1+SR))·c_mine − E_kWh·tariff − Fuel_L·price
CO2_t/h  = E_MWh·EF_grid + Fuel_L·2.68e-3
```
#### Base case [D]

TPH = 3,600, f = 0.50 %, R = 80 %, g = 0.26 g/t, R_Au = 60 %, P_Cu = $14,500, P_Au = $4,300, TC/RC = 0:
* Cu: 14.4 t/h × 0.965 × 14,500 = **$201 k/h**
* Au: 18.06 oz/h × 0.95 × 4,300 = **$74 k/h**
* Opex: 3,600 × $9.9 = **$36 k/h**; power ≈ 115 MW × $42/MWh = $4.8 k/h (included)
* Margin before MET and freight ≈ $239 k/h. Annual (8,050 run-h) ≈ **$2.2 bn NSR**. This is consistent with the price-adjusted 2020 actual of ~$2.39 bn (§0).
* Rule of thumb: **1 % of mill throughput ≈ $2.75 k/h; 0.01 % Cu head grade ≈ $4.4 k/h; 1 pp Cu recovery ≈ $2.5 k/h; 1 hour of whole-plant downtime ≈ $275 k.**

---

## 10. Open datasets for the repo

All licences below were checked on 2026-10-10. The Kaggle licence was checked through the Kaggle API metadata. The contest organiser's list is at S50.

| Dataset | URL | Licence | Size | Use in twin | Caveat |
|---|---|---|---|---|---|
| Quality Prediction in a Mining Process (E. M. Oliveira) | https://www.kaggle.com/datasets/edumagalhaes/quality-prediction-in-a-mining-process | **CC0: Public Domain** (Kaggle API `licenseNameNullable`) | 183.8 MB (183,766,261 B); Mar-Sep 2017; 20 s and hourly samples, ~24 cols | flotation soft-sensor, lag structure, reagent (starch/amina) & air/level effects. Train a surrogate for `ψ, ξ` dynamics | **Iron-ore reverse flotation (% silica)**, not Cu sulphide. Use for dynamics and noise structure, rescaled |
| GeoMet dataset (Hoffimann et al., IMPA/UFMG/Vale) | https://zenodo.org/records/7051975 (doi:10.5281/zenodo.7051975) | CC BY 4.0 | 405 kB (drillholes.csv, comminution.csv with DWT/BWi, flotation.csv with LCT Cu recovery) | **block-model copulas**: Cu grade ↔ BWi/Axb ↔ recovery. Variogram fitting | Brazilian Cu deposit, not Kazakh |
| Fragmentation, El Aljibe quarry (Segarra et al.) | https://zenodo.org/records/10666378 | CC BY 4.0 | 36 kB, 12 blasts, size vs passing | fit Rosin-Rammler/Swebrec n and X50 to calibrate Kuz-Ram | quarry, not porphyry |
| Energy consumption, mining & processing plant (Tytiuk et al.) | https://zenodo.org/records/20647907 | **CC BY-SA 4.0** (share-alike) | 1.1 MB xlsx, 30-min P/Q, Jan & Jun 2019 | load-profile shape, winter-summer contrast, reactive power | Ukrainian iron plant. **Derivatives must stay CC BY-SA**, so keep them in a separate folder |
| Jaw crushing tests of granite | https://zenodo.org/records/21241766 | CC BY 4.0 | 9.8 GB (subsample) | vibration and motor-current anomaly detection for crusher CM | jaw, not gyratory |
| MWD drilling (Norwegian tunnels) | https://zenodo.org/records/10358374 | CC BY 4.0 | 5.5 MB, 5,205 cycles | penetration-rate vs rock-quality model, feeding A-factor/BWi | tunnelling rigs |
| OpenMines `north_pit_mine.json` + simulator | https://github.com/370025263/openmines (arXiv 2404.00622) | MIT (keep licence text) | 6 kB config | **haulage benchmark**: 71 trucks (9×77, 29×35, 33×55 t), 5 load sites, 5 dumps, road-distance matrices (km), road-repair λ = 0.00833/min, μ = 50 min; dispatchers Naive/Random/Nearest/FixedGroup/SPTF/SQ/PPO | Chinese coal mine, units partly implicit |
| Methane, underground mine (Mendeley) | https://data.mendeley.com/datasets/yd7vw4c5mk/1 | CC BY 4.0 | 59 MB, 28 sensors @ 1 s | gas-sensor anomaly patterns for post-blast CO/NOx monitors (re-scaled) | underground coal |
| Seismic-bumps (UCI) | https://archive.ics.uci.edu/dataset/266/seismic+bumps | CC BY 4.0 | 138 kB | hazard-classification analogue for slope-alarm ML | underground coal |
| USGS Mineral Facilities of N & C Eurasia | https://pubs.usgs.gov/of/2010/1255/ | US public domain (cite USGS) | 153 kB | KZ facility capacities for context | 2010 vintage |
| Open-Meteo historical weather API (ERA5-based) | https://open-meteo.com/ | CC BY 4.0 (*verify on site*) | API | real hourly temperature/wind at 50.2°N 74.4°E (Bozshakol) or 46.97°N 79.98°E (Aktogay) for weather scenarios | - |
| NASA POWER | https://power.larc.nasa.gov/ | open, no restrictions (*verify*) | API | same, as backup | - |

The contest page notes that **no suitably licensed open haul-truck telemetry exists**. Haulage must be synthetic and calibrated to OpenMines, OEM sheets and KAZ fleet data (§2.5) [S50].

---

## 11. What-if scenarios with causal chains

Base case: §9.3. TPH = 3,600 t/h, 4 shovels (S1, S2 ore; S3, S4 waste), 18 × 785C, crushed-ore stockpile 40 kt (~11 h), LP dispatch. Magnitudes are [D] from the equations above unless tagged.

#### S1. Ore-shovel S2 hydraulic failure (MTTR 10 h)

Maintenance module raises a work order (Weibull draw) -> S2 is unavailable -> LP dispatch re-solves. Options: (a) reallocate trucks to S1 (MF on S1 goes from ~0.8 to ~1.6, so queue time at S1 rises from ~1.5 to ~12 min/cycle); (b) move waste shovel S3 onto ore (2-3 h tramming plus cable relocation) or start an FEL (993K) reclaiming the ROM stockpile.
-> Ore delivery falls ~50 % for 2-3 h; waste stripping falls 25 % for 10 h, creating a strip deficit; crusher-stockpile buffer covers ~11 h, so **mill TPH does not change** if the outage is < ~8 h.
-> **Blend shift:** S1 face at 0.45 % against S2 at 0.58 % drops head grade from 0.515 % to 0.45 %. Constant-tails recovery goes from 80.9 % to 78.1 %, so **Cu output falls from 15.0 to 12.65 t/h (−16 %) ≈ −$33 k/h** while the blend lasts.
-> KPIs: −$150-300 k per event. LP dispatch with a grade constraint plus HG stockpile reclaim recovers about two-thirds of the loss. The Bozshakol Q4 2020 HG-stockpile blending [S1] is the real precedent.

#### S2. Siberian high: −38 °C with 12 m/s wind for 72 h

Weather module -> speed caps of 30 km/h on haul roads and 20 km/h on ramps (visibility and traction) -> truck cycle +18 %. Warm-up adds +40 min per shift, so effective hours fall 5 %. Hydraulic response −15 % gives shovel cycle +10 %. Tyre/strut failure hazard ×1.2 (maintenance) and idle fuel +15 %. Watering is impossible, so PM10 rises ×2-3 (environment).
-> Mine ore delivery −20 to −25 %, absorbed first by the stockpile and then by **mill TPH −8 to −12 %** after ~1 day. Frozen fines cause chute hang-ups, giving −3 % plant availability.
-> Heap-leach/SX-EW (if modelled) runs at **70 % of design** [R] S4.
-> **Cu −10 %, ≈ −$27 k/h**; fuel L/t +20 %; CO₂/t +5 %.

#### S3. Blast intensification: PF 0.30 -> 0.40 kg/t on ore benches

D&B module -> B×S from 6.2×7.5 to 5.4×6.5 m (+33 % holes, drill hours +33 %) -> Kuz-Ram X50 272 -> 216 mm (−21 %), X80 520 -> 413 mm.
-> Shovel dig rate +6 %, so loading time −5%. Crusher power −8 %. SAG fines +30 % gives **SAG TPH +8 %** (within the 5-15 % evidence band [S20][S21]). Higher TPH shortens flotation τ, giving **R −0.3 pp**.
-> **Net Cu +7.5 % ≈ +$20 k/h**, against extra explosive and drilling cost of ≈ $0.14/t × 3,600 = **$0.5 k/h**. Risks: NOx fume (wet holes with ANFO), flyrock radius ↑ (exclusion 500 -> 600 m), and the Red Dog plateau [S22].

#### S4. Hard-ore domain: BWi 13 -> 16 kWh/t, Axb 45 -> 32

Geology/block model -> SAG specific energy +25 % -> at fixed 28 MW, **SAG TPH −20 %**. The operator coarsens the grind instead: TPH −10 %, P80 180 -> 215 µm, **R_Cu −1.5 pp**. Head grade is unchanged.
-> **Cu −12 % ≈ −$33 k/h.** Mine-side response: the LP dispatch blends 30 % soft clay-sulphide ore (BWi 10), restoring TPH +6 % at a grade cost of −0.03 %. Upstream remedy: S3 (finer blast) on the hard domain.

#### S5. Grid curtailment: Ekibastuz unit trip, KEGOC orders −40 MW for 6 h

Energy module -> SAG plus one ball mill derated -> **TPH −25 %** for 6 h. The crusher keeps running into the stockpile until it is full (stockpile ↑ 6.5 kt/h). Flotation running at reduced feed raises τ, giving **R +0.5 pp**.
-> **−$66 k/h × 6 h ≈ −$0.4 M**, power −40 MW (CO₂ −32 t/h). Diesel fleet unaffected; electric shovels and drills shed second.
-> Variant: tariff 18 -> 30 KZT/kWh (+67 %, as with the 2025 cap complaints [S41]) adds **+$2.6 k/h of cost, ≈ 1 % of margin**. Power is cheap relative to copper value, so the optimiser should **never trade throughput for power cost** at current prices.

#### S6. Spring thaw: haul-road RR 2.5 % -> 5 % on the main ramp and flats

Road module -> loaded ramp TR 12.5 -> 15 % gives v −17 %. Flat sections become power-limited. **Cycle +12 %, fleet output −11 %**, fuel L/t +18 %, tyre-wear multiplier 1.08 and TKPH alarms.
-> Mine shortfall −11 % while the plant is fed from stockpile. After 3-4 days **mill TPH −5 %**.
-> Maintenance module dispatches graders and a water truck. Each grader-hour restores RR −0.5 % on 1 km [A]. **Payback of road maintenance ≈ 1 h.**

#### S7. Slope radar red alarm on the east wall (velocity 55 mm/day, inverse-velocity forecast failure in 30 h)

Safety/TARP -> evacuate the bench and close ramp R1 -> haul to the crusher detours +1.5 km each way -> **cycle 22 -> 28 min (+27 %)** -> truck-limited fleet output −21 %. The LP gives priority to ore and defers waste. Strip deficit grows by ~2.5 kt/h.
-> Mill held at 100 % for ~11 h on the stockpile buffer, then −10 % if the closure lasts beyond a day.
-> If failure occurs, shovel S4 is buried. MTTR covers cleanup of 2-5 days of dozing [A].
-> The twin should show a TARP timeline: alarm -> evacuation time -> failure -> recovery.

#### S8. Post-blast fume trapped by a winter inversion (stability F, wind 0.5 m/s)

D&B/Safety -> NO₂ above 1 ppm persists -> re-entry 30 min -> 150 min [S30 rule plus gas test]. Shovels S1 and S3 lie inside the 500 m zone, so they are idle 2 h longer, and haul road H2 stays closed.
-> Dispatch reroutes to S2/S4, giving queueing (MF ~1.5) and **ore delivery −35 % for 2 h**. Mill unaffected (buffer). Daily ore −3 %. Personnel exposure KPI logged.
-> Mitigation what-if: shift the blast to the 13:00-15:00 mixing-height window, or use emulsion in wet holes, giving zero delay.

#### S9. Predictive maintenance on truck engines (coolant-temp and oil-Fe trend model)

CM module flags truck T07 (coolant 104 °C trend, Fe 45 ppm) -> planned 6 h repair at the next shift change instead of an in-cycle failure (14 h with tow) -> fleet PA **89 % -> 91.5 %** across the fleet once applied to every truck -> truck-limited mine output **+2.8 %**.
-> The stockpile fills -> mill TPH +1 % (when previously mine-limited). Fewer roadside failures mean fewer **ramp blockages**: an in-ramp breakdown blocks a single lane for ~45 min and slows all trucks.
-> **≈ +$3-8 k/h**, maintenance cost −15 % (less secondary damage).

#### S10. Copper price −25 % ($14,500 -> $10,900) with TC turning back to +$80/dmt

Economics -> NSR/h −27 %. Lane mill-limited cut-off rises from ~0.18 % to ~0.23 %, so 8-12 % of former ore goes to the LG stockpile. Effective strip ratio rises 0.70 -> 0.82 (fleet hours +7 %), while mill head grade rises +0.02 % (partly offsetting).
-> Dispatch LP targets update. The KPI shows the cut-off policy recovers ~15 % of the price-driven margin loss.
-> The reverse case (spot TC −$100/dmt, price +10 %) lowers cut-off and extends mine life.

#### S11. Dispatch policy: fixed allocation -> LP + MTCT dynamic

Haulage module -> shovel idle time 22 % -> 10 %, truck queue time −40 % -> **material moved +7 to +10 %** at the same fleet ([T6] reports +5-15 %). The grade constraint holds crusher-feed grade within ±0.02 % rather than ±0.06 %, so recovery variance falls and **average R +0.3 pp**. Fuel L/t −4 %.
-> **≈ +$6-10 k/h.** Second-order effect: the same fleet can absorb one truck breakdown with no ore loss.

#### S12. Trolley assist on the 1.2 km main ramp (fleet B: 830E-AC)

Energy/Haulage -> loaded ramp speed 13 -> 24 km/h, so cycle −2 min (−8 %) -> fleet output +8 % or −1 truck. Diesel −28 % fleet-wide, and electricity +3.1 MW average.
-> Cost: diesel saving ≈ $0.75/L × 1,050 L/h fleet saving ≈ $790/h, against power cost ≈ $130/h, so **cost −$660/h**.
-> **CO₂:** diesel −2.8 t/h, grid +2.5 t/h at 0.80 kg/kWh (+3.3 t/h on Ekibastuz coal at 1.05). **Net CO₂ change ≈ −0.3 to +0.5 t/h** (§6.4). The implication: decarbonising haulage in Kazakhstan needs **trolley plus a renewable PPA**. Trolley alone mainly saves time and money.

---

## 12. Sources

### Operator (KAZ Minerals) and site data
- [S1] KAZ Minerals, *Group Production Report, Q4 & FY 2020* (28 Jan 2021) - https://www.kazminerals.com/media/21861/kaz-minerals-q4-2020-28-jan-21.pdf
- [S2] KAZ Minerals, *Preliminary Results 2020* (24 Feb 2021) - https://www.kazminerals.com/media/21914/2020-prelim-24022021-final.pdf. Also FY2017/2018 guidance via https://www.kazminerals.com/category/financial/page/3/ and Q1/Q3 2018 production reports https://www.kazminerals.com/media/6774/kaz-minerals-q1-2018-26-apr-2018.pdf, https://www.kazminerals.com/media/9506/kaz-minerals-q3-2018-25-oct-18-final.pdf
- [S3] KAZ Minerals, *Projects Update* (11 Dec 2014). Fleet, crusher, conveyor, mills, flotation, power 214 MW, tariff, water, −40 °C, strip ratio 0.7, resources, cost breakdown - https://www.kazminerals.com/media/2828/projects_update_111214.pdf
- [S4] KAZ Minerals, *Bozshakol Site Visit* (1 Jun 2015). Leica dispatch, fleet list, shifts, winter SX-EW 70 % - https://www.kazminerals.com/media/2834/site-visit-presentation-vfinal-010615.pdf
- [S5] KAZ Minerals, Bozshakol page - https://www.kazminerals.com/our-business/bozshakol/
- [S6] MiningDataOnline, Aktogay Mine (reserves, fleet, flowsheet, metallurgy, water, production 2016-2025) - https://miningdataonline.com/property/4616/Aktogay-Mine.aspx
- [S7] MiningDataOnline, Bozshakol Mine - https://miningdataonline.com/property/334/Bozshakol-Mine.aspx
- [S8] ABB gearless mill drives for Kazakhmys (28 MW SAG, 2 × 22 MW ball) - https://www.automation.com/article/abb-to-supply-gearless-mill-drive-systems-in-kazak ; E&MJ: https://www.e-mj.com/news/asia/kazakhmys-developing-major-copper-mine-at-bozshakol/
- [S19] Mining Magazine, Hexagon wins fleet-management contracts at Bozshakol and Aktogay - https://miningmagazine.com/fleets/news/1262778/hexagon-wins-contracts-kazakhstan

### Equipment
- [S10] Cat 793F (Borusan Cat Kazakhstan) - https://kz.borusancat.com/en/equipment/new/470/off-highway-trucks/18092621/793f ; brochure https://mujstroj.zeppelin.cz/fileadmin/helios_files/JPG/ToM/OHT/793F/793F_PEDJ0470-01_Product_Brochure_2020.pdf
- [S11] Cat 785C specs - https://www.ritchiespecs.com/model/caterpillar-785c-rock-truck
- [S12] Komatsu 830E-5 - https://www.komatsu.com/en-us/products/equipment/trucks/electric-drive-mining-trucks/830e-5 ; https://www.komatsu.com/en-au/products/equipment/dump-trucks/electric-drive-mining-trucks/830e-5
- [S13] Hitachi EX3600-7 (22-24 m³) - https://www.hitachicm.com/global/en/solutions/mining-business/products/large-excavators/product.ex3600-7
- [S14] Caterpillar Performance Handbook Ed. 50 (rolling resistance, haul-road and fuel guidance; machine rimpull charts in brochures) - https://www.ringpower.com/media/2086/caterpillarperfhandbook_ed50.pdf
- [S15] Global Mining Review, Tier 4 793F up to 5.3 % less fuel - https://www.globalminingreview.com/mining/25092017/cat-793f-mining-trucks-prove-tier-4-performance/amp/
- [S16] Cat trolley assist (Aitik: +100 % speed on grade, >90 % fuel cut on trolley) - https://www.globalminingreview.com/mining/14022020/caterpillar-introduces-trolley-assist-system-for-cat-electric-drive-mining-trucks/
- [S17] First Quantum Kansanshi trolley - https://www.miningweekly.com/article/first-quantum-aims-to-drive-efficiency-through-new-electric-trolley-assist-system-2026-09-21 ; ABB all-electric mine (30-70 % fuel) - https://library.e.abb.com/public/1d0387af977141979024f6544740d9dc/The%20journey%20to%20the%20all%20Electric%20Mine%20-%20Copper%20Worldwide%20-%20Dec2020.pdf
- [S18] OpenMines (MIT) - https://github.com/370025263/openmines ; config https://raw.githubusercontent.com/370025263/openmines/main/openmines/src/conf/north_pit_mine.json ; paper https://arxiv.org/abs/2404.00622

### Blasting, comminution, mine-to-mill
- [S20] Giblett, AusIMM 14th Mill Operators (citing McKee 2013 gains) - https://www.ausimm.com/globalassets/pdf-files/publications/3-18_14th-mill-ops/3-18_giblett.pdf ; GEOVIA community PNG case - https://3dswym.3dexperience.3ds.com/post/geovia-user-community/new-solutions-to-the-old-mine-to-mill-approach_ZLSubymeTGGRBbNOP5SmkQ
- [S21] Hexagon Split case study - https://bynder.hexagon.com/m/64597534ce4e9aa0/original/Split-Maximising-Profit-Case-Study-EN.pdf
- [S22] Red Dog SAG/blasting (ISEE 2001) - https://onemine.org/documents/adjusting-blasting-to-increase-sag-mill-throughput-at-the-red-dog-mine
- [S23] Sarcheshmeh porphyry BWi 5.67-20.21 kWh/t - https://faculty.kashanu.ac.ir/abdzad/fa/articlesInPublications/11186

### Safety, environment, climate
- [S24] WHO Global Air Quality Guidelines 2021 - https://www.who.int/publications/i/item/9789240034228
- [S25] Annals of Global Health (KZ/RU PM10 reference 0.3 / 0.06 mg/m³) - https://www.annalsofglobalhealth.org/en/articles/2535
- [S26] Central Asia Climate Portal, KZ hygienic standards update - https://centralasiaclimateportal.org/hygienic-standards-for-atmospheric-air-have-changed-in-kazakhstan/
- [S27] US EPA AP-42 §13.2.2 Unpaved Roads - https://www.epa.gov/sites/default/files/2020-10/documents/13.2.2_unpaved_roads.pdf
- [S28] NIOSH Pocket Guide: CO https://www.cdc.gov/niosh/npg/npgd0105.html ; NO₂ https://www.cdc.gov/niosh/npg/npgd0454.html
- [S29] AEISG Code of Practice, blast-generated NOx (WorkSafe WA) - https://worksafe.wa.gov.au/publications/prevention-and-management-blast-generated-nox-gases-surface-blasting-code-practice ; QLD Guidance Note 20 - https://www.resources.qld.gov.au/__data/assets/pdf_file/0010/212500/qld-guidance-note-20-mgmt-oxides-nitrogen.pdf
- [S30] OceanaGold re-entry procedure (≥ 30 min plus gas test) - https://oceanagold.com/interactive-documents/part-h/section-2/214
- [S31] Putra, Yudono, Sari, Cabrejo (2023), velocity-ratio slope-radar alarms, ACG, doi:10.36487/ACG_repo/2335_57 - https://papers.acg.uwa.edu.au/d/2335_57_Putra/57_Putra.pdf
- [S32] Saunders, Nicoll, Christensen (2016), radar alarm threshold validation at Telfer - https://papers.acg.uwa.edu.au/d/1604_21_Saunders/21_Saunders.pdf
- [S33] Chapin et al. (2025), Bingham Canyon TARP triggers - https://papers.acg.uwa.edu.au/d/2025_07_Chapin/07_Chapin.pdf
- [S34] Aktogay climate table - https://en.wikipedia.org/wiki/Aktogay,_East_Kazakhstan_Region
- [S59] RK Order No. 352 (30 Dec 2014), Industrial safety rules for mining operations - https://adilet.zan.kz/rus/docs/V1400010247 *(verify document number)*

### Energy, emissions, prices
- [S35] IPCC 2006 GL Vol. 2 Ch. 3 Mobile Combustion - https://www.ipcc-nggip.iges.or.jp/public/2006gl/pdf/2_Volume2/V2_3_Ch3_Mobile_Combustion.pdf
- [S36] UK DESNZ GHG conversion factors 2024 - https://www.gov.uk/government/publications/greenhouse-gas-reporting-conversion-factors-2024
- [S37] LowCarbonPower, Kazakhstan (603 gCO₂e/kWh) - https://lowcarbonpower.org/region/Kazakhstan
- [S38] Ember, Kazakhstan (85 % fossil 2025) - https://ember-energy.org/countries-and-regions/kazakhstan/
- [S39] UNDP EESL project doc (≈1.00 tCO₂/MWh to 2014) - https://info.undp.org/docs/pdc/Documents/KAZ/Project%20Document%20EESL.pdf
- [S40] Inzonex Power Atlas, Kazakhstan (805 g/kWh, coal 54 %) - https://inzonex.co.uk/poweratlas/kazakhstan/
- [S41] Generator tariff caps 2026-2032 - https://qazaqgreen.com/en/news/kazakhstan/3268/ ; Samruk-Energy Q1 2025 - https://www.samruk-energy.kz/images/documents/2025/rez_deyatelnosti_SE_3mes_2025_en.pdf
- [S42] GlobalPetrolPrices, Kazakhstan diesel - https://www.globalpetrolprices.com/Kazakhstan/diesel_prices/
- [S43] USD/KZT history - https://www.valutafx.com/history/usd-kzt-2026-08-25
- [S44] LME copper cash settlement (Westmetall) - https://www.westmetall.com/en/markdaten.php?action=table&field=LME_Cu_cash
- [S45] Gold spot - https://metalcharts.org/1-oz-gold-price
- [S46] 2026 TC/RC benchmark $0 - https://news.metal.com/newscontent/103681795-chinese-smelters-antofagasta-set-2026-copper-concentrate-tcrc-benchmark-at-000¢ ; Fastmarkets spot TC - https://www.fastmarkets.com/insights/10-things-in-focus-at-cesco-week-2026-as-sulfuric-acid-upends-the-copper-market/

### Reliability
- [S47] Allahkarami, Sayadi, Ghodrati (2023), Reliability analysis of mining transportation system: semi-parametric vs parametric PHM, *Quarterly J. Transportation Eng.* 14(2) - https://research.chalmers.se/en/publication/544171
- [S48] Weibull suspension failures, Cat 777D, ANZIAM J. (2015) - https://journal.austms.org.au/ojs/index.php/ANZIAMJ/article/view/7863

### Datasets
- [S49] Kaggle flotation dataset (CC0, 183.8 MB) - https://www.kaggle.com/datasets/edumagalhaes/quality-prediction-in-a-mining-process
- [S50] Contest data recommendations - https://openegiz-contest.github.io/data/
- [S51]-[S58]: URLs as listed in the §10 table.

### Textbooks and papers (no stable free URL)
- [T1] Bond, F.C. (1961) Crushing and grinding calculations. *Brit. Chem. Eng.* 6:378-385, 543-548.
- [T2] Kuznetsov, V.M. (1973) The mean diameter of fragments formed by blasting rock. *Soviet Mining Science* 9:144-148. doi:10.1007/BF02506177
- [T3] Cunningham, C.V.B. (1983, 1987, 2005) The Kuz-Ram model for prediction of fragmentation from blasting; "The Kuz-Ram fragmentation model - 20 years on", Brighton Conf. Proc., EFEE.
- [T4] Lane, K.F. (1988) *The Economic Definition of Ore: Cut-off Grades in Theory and Practice*. Mining Journal Books.
- [T5] Douglas, J. (1964) *Prediction of shovel-truck production*, Stanford; Burt, C.N. & Caccetta, L. (2007) Match factor for heterogeneous truck and loader fleets. *IJMRE* 21(4):262-270. doi:10.1080/17480930701388606
- [T6] White, J.W. & Olson, J.P. (1986) Computer-based dispatching in mines with concurrent operating objectives. *Mining Engineering* 38(11):1045-1054; Munirathinam, M. & Yingling, J.C. (1994) A review of computer-based truck dispatching strategies for surface mining operations. *IJSM* 8(1):1-15. doi:10.1080/09208119408964750
- [T7] Fukuzono, T. (1985) A new method for predicting the failure time of a slope. *Proc. 4th Int. Conf. & Field Workshop on Landslides*, Tokyo, 145-150.
- [T8] Wills, B.A. & Finch, J.A. (2016) *Wills' Mineral Processing Technology*, 8th ed. Butterworth-Heinemann.
- [T9] Darling, P. (ed.) (2011) *SME Mining Engineering Handbook*, 3rd ed. SME.
- [T10] Morrell, S. (2004) An alternative energy-size relationship to that proposed by Bond. *Minerals Engineering* 17(3):437-445. doi:10.1016/j.mineng.2003.10.019
- [T11] Jameson, G.J. (2012) The effect of surface liberation and particle size on flotation rate constants. *Minerals Engineering* 36-38:132-137 (verify DOI before citing).
- [T12] Hustrulid, W., Kuchta, M., Martin, R. (2013) *Open Pit Mine Planning and Design*, 3rd ed. CRC Press.

---

## 13. Open items (values that remain estimates)

1. Bozshakol Cu concentrate grade (22 % assumed). Look in KAZ annual reports for 2021+ or Kazakh-language sources.
2. KZ PM10 MPC official text (Order of 2 Aug 2022) and Order No. 352 numbering on adilet.zan.kz.
3. Current delivered industrial power tariff for a 220 kV customer in Pavlodar oblast (only generator caps were found).
4. Gold price ($4,330/oz, August 2026) and LME copper move daily; the twin uses the values quoted.
5. Slide 46 of S3: exact pairing of the cost-category percentages.
6. Open-Meteo and NASA POWER licence wording.
7. MET rates (Tax Code).
8. Weibull/MTBF values are assumptions (§8). Keep them labelled synthetic, or replace them with a fitted public dataset if one is found.
