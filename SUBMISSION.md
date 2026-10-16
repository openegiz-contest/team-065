# Kyzyl-Tas - Submission

Kyzyl-Tas is a digital twin of a fictional open-pit copper-gold mine with a 30 Mt/a concentrator, built on
OpenEgiz. The mine is fictional, but its equipment, capacities, grades, costs and climate come from public
data for Kazakhstan's Bozshakol and Aktogay operations. Every number has a source or a stated assumption
(see [Data and Assumptions](#data-and-assumptions)).

How to start it: [README.md](README.md) (`make up`, then open http://localhost:8000).

## Team

| Name | GitHub |
|---|---|
| Mahbubul Islam | [@Islam-DS](https://github.com/Islam-DS) |

#### Contents

1. [Mine model](#1-mine-model)
2. [Behaviour](#2-behaviour)
3. [Visualization](#3-visualization)
4. [Modules](#4-modules)
5. [What-if scenarios](#5-what-if-scenarios)
6. [Data and Assumptions](#data-and-assumptions)
7. [Limitations](#7-limitations)
8. [Verification](#8-verification)

---

## 1. Mine model

All mine objects are Eclipse Ditto twins in the namespace `kz.kyzyltas.mine`, created by
[mine/setup/model.json](mine/setup/model.json): **21 type twins and 66 instance twins**.

| Group | Instances | Live state (examples) |
|---|---|---|
| Mine, pit, 10 benches | `mine`, `pit`, `bench-01..10` (waste cap on benches 01-04 and 09, ore below) | role, face grade, strip ratio, tonnes mined |
| Haul fleet | `truck-01..14` (12× Cat 785C, 2× Komatsu 830E-5 with AC electric drive), `dispatch` | haul-cycle state, payload, speed, assigned shovel, route progress, fuel burn, estimated health, coolant temperature, oil iron, work-order flag, estimated hours to wear-out |
| Loading and drilling | `shovel-s1..s4` (Hitachi EX3600), `drill-01..02` | state, face grade, queue length, dig rate, penetration, health |
| Haul roads | 12 `road-*` segments | rolling resistance, closed flag, traffic |
| Plant | `plant`, `crusher-01`, `conveyor-01..02`, `mill-sag-01`, `mill-ball-01..02`, `flotation-01`, `tailings-01` | throughput, feed grade, power (follows load), P80, recovery, plant availability |
| Stockpiles | `stockpile-rom`, `stockpile-crushed`, `stockpile-hg`, `stockpile-waste` | mass, grade, fill, high-grade reclaim rate |
| Environment and safety | `weather-station-01`, `slope-radar-01..02`, `fan-pit-01`, `fan-plant-01` | temperature, wind, visibility, slope velocity and TARP level, haul-road PM10, watering possible |
| Energy | `substation-01` | load, capacity, grid CO₂ factor |
| Control and KPIs | `scenario`, `kpi` | active scenario; current, baseline and delta KPIs; simulation clock; latest event |

#### Types

Each instance names its type twin in `definition` (for example `kz.kyzyltas.mine:HaulTruck:1.0.0`).
Each type twin holds its instance count (`instances`), its parent types with counts in `_parents` (for example
`{"Dispatch": 14}` for HaulTruck), and the feature names and units of its instances with neutral defaults.

#### Relations

- Hierarchy in `attributes._parents`: mine -> pit -> benches and radars; mine -> dispatch -> trucks, shovels and
  drills; mine -> plant -> crusher, conveyors, mills, flotation, tailings and stockpiles.
- Material flow in `attributes.feeds`: shovels -> ROM pad or waste dump; ROM pad and high-grade pile ->
  crusher -> conveyor -> crushed-ore stockpile -> overland conveyor -> SAG mill -> ball mills -> flotation ->
  tailings. The substation `feeds` the crusher, conveyors and mills.
- Workplace in `attributes.bench`: each shovel names the bench it digs.
- Live relations in features: each truck's `assigned_shovel` and the `road_segment` it is driving on; each road's `closed` flag.

#### How to see it

- Twin model button in the 3D view (no login): the hierarchy with live states, and the types with instance counts.
- Click any twin, there or in 3D: its live features and its relations (part of, type, bench, feeds).
- Grafana (http://localhost:3000, login printed by `make up`) -> **OpenEgiz** app -> **Twins** / **Types**.

Instance twins declare exactly the features the engine publishes. [mine/engine/tests/test_contract.py](mine/engine/tests/test_contract.py)
fails if a twin declares a feature the engine does not publish, or the reverse, or if a value type differs. Most
features change continuously; a few are fixed process parameters published for reference (for example concentrate
grade and tailings grade).

## 2. Behaviour

The simulation engine ([mine/engine/](mine/engine/)) steps the whole mine five times a second. Each step
covers 12 seconds of mine time, so mine time runs **60× faster than real time: one real minute is one mine
hour**. The clock is published as `kpi.sim_time_h`. The engine publishes every state change to Ditto as
Ditto-protocol `merge` commands over MQTT (about 28 commands per second in total).

| Process | Model | Code |
|---|---|---|
| Truck travel | Rimpull/grade-resistance speed per road segment (drivetrain efficiency by drive type), speed caps (ramp, winter, visibility) | `models/truck.py` |
| Haul cycle | Queue -> spot -> load (bucket passes × swing time) -> haul -> dump queue (2 bays) -> dump -> return; one truck at a time per shovel | `simulation.py` |
| Loading | Swing time from fragmentation and cold-weather hydraulics | `models/shovel.py` |
| Blasting | Kuz-Ram X50/X80 from powder factor | `models/blast.py` |
| Crushing, grinding | Crusher capacity; SAG throughput from feed size, ore hardness (Axb) and available power, limited by the ball mills in service; Bond P80; mills draw their available power unless starved | `models/comminution.py`, `simulation.py` |
| Flotation | Constant-tails recovery; grind (P80) and residence-time penalties | `models/flotation.py` |
| Stockpiles | Mass and grade balance (well-mixed) for ROM, crushed, high-grade and waste piles; mass is conserved | `models/stockpile.py` |
| Reliability | Weibull wear-out mode with a condition signal, plus random faults; all-causes MTBF from the reference table | `models/reliability.py` |
| Dust | US EPA AP-42 unpaved-road PM10 on truck vehicle-km; watering only above 0 °C | `models/dust.py` |
| Weather | Temperature, wind and visibility toward scenario targets | `models/weather.py` |
| Economics, energy | Net smelter revenue, costs, diesel and grid energy, CO₂ | `models/economics.py`, `modules/energy.py` |

#### Interlinked processes

Trucks deliver ore to the ROM pad at the grade of the face they loaded. The crusher
draws the ROM pad, plus high-grade ore when grade control asks for it, into the crushed-ore stockpile. The SAG
mill draws that stockpile at a rate set by fragmentation, hardness, power and the ball mills in service.
Flotation recovery then follows the feed grade and grind. Pit-side changes reach the plant only through the
stockpiles. That is why haulage scenarios hit "ore mined" first and plant KPIs later.

#### Back-pressure

The coupling also runs from plant to pit:
- the crusher stops when the crushed-ore stockpile is full;
- ore trucks wait at the dump when the ROM pad (150 kt) is full.

The engine checks that mass is conserved (`test_ore_mass_balance_closes`).

#### Realistic constraints

Examples:
- one truck at a time under a shovel;
- two dump bays;
- winter speed caps;
- no road watering below 0 °C;
- crusher, mill and stockpile capacities;
- one ball mill down cuts the grinding circuit to 60 % of its capacity;
- fume re-entry times after blasting;
- a closed ramp forces a 2.7 km detour;
- with every shovel on a route down, trucks wait;
- only the two electric-drive trucks can use a trolley line.

#### Shadow baseline

The engine runs a second simulation that never receives scenarios. Each time a scenario
is applied or undone, the baseline restarts as an exact copy of the live mine at that moment, including
stockpiles, equipment states and random-number streams. From then on the two differ only because of the
scenario. Each machine also draws its failure times from its own random stream seeded by its name, so both
runs see the same breakdowns. The `kpi` twin publishes `current_*`, `baseline_*` and `delta_*_pct` for
16 KPIs (including grinding energy in kWh per tonne milled). Right after a click every delta is zero, and right after Undo they return to zero. Rate KPIs (ore mined,
diesel, grid energy, haul cycle) are one-mine-hour moving averages, so they move over about a minute of real time.

#### Validation against the reference site

Average over 1,000 mine hours (six weeks) of normal running, seed 3,
reproduced by [mine/engine/tools/validate.py](mine/engine/tools/validate.py):

| Quantity | Twin | Reference |
|---|---|---|
| Mill feed | 3,245 t/h on average (28.4 Mt/a, with mill outages); 3,425 t/h when all mills run | Bozshakol sulphide concentrator 30 Mt/a design [S3] |
| Copper recovery | 79.4 % | 79.7 % reported for 2020 [S1] |
| Copper in concentrate per tonne milled | 4.10 kg/t | 4.04 kg/t (127.8 kt from 31.6 Mt, 2020) [S1] |
| Truck fleet availability | 92.6 % | 88-92 % target range [T9], §8.1 |
| Truck haul cycle | 24 min | ~22 min implied by the published fleet plan [S3], §2.5 |
| Unplanned failures (14 trucks, 4 shovels, 2 drills) | 24 per week | all-causes MTBF of §8.1 |
| Mill starved by the pit | never | - |

The mill rate and recovery follow from calibrated inputs (rated capacity, recovery model), so they show the
model is consistent rather than proving it independently. The copper per tonne, fleet availability and
failure count are produced by the simulation. Equipment failures are random, so a single week can differ
(one mill outage of a day lowers that week's mill feed by several percent).

## 3. Visualization

The interface at http://localhost:8000 is a React/three.js application, built into
[mine/ui/dist/](mine/ui/dist/) and served by nginx. It reads twins only from the platform:
- Ditto REST for the catalogue;
- Ditto server-sent events for live changes;
- InfluxDB for history.

It shows:
- 3D scene: the open pit with its benches and two ramps, trucks moving and coloured by haul-cycle state,
  shovels labelled with their face grade, and the plant cluster with stockpiles;
- dust along the haul ramps, whose density follows the twins' haul-road PM10 (fewer particles in performance mode);
- affected equipment highlighted while a scenario runs (broken shovels from their twin state; scenario areas such as
  a closed ramp or the trolley line from the scenario twin);
- weather from the weather twin: snow and denser haze when its temperature and condition call for them;
- mine clock: simulated day and time, 60× real time, starting at 07:00 (day-shift start), with a night tint;
- 2D minimap of equipment positions and states;
- Twin model view (hierarchy, types, live states);
- inspector: click any truck, shovel, plant unit or label to see that twin's live features and relations;
- KPI cards and a baseline-versus-current table, grouped into pit, plant, and economics and energy, plus a
  crushed-ore buffer gauge (hours of mill feed at the SAG mill's rated rate);
- scenario banner with the causal chain and the live key indicators, each marked once the twins confirm it;
- causal event log;
- scenario panel with **↺ Undo - back to baseline**.

Software WebGL is enough: no GPU is required, and a performance mode reduces effects automatically when the
frame rate drops.

A Grafana dashboard, **"Kyzyl-Tas Mine - KPIs vs baseline"**, is Grafana's home page and is readable without
login. It shows the history of the main KPIs from InfluxDB, live mine against the shadow baseline.

## 4. Modules

Each module makes a decision on its own while the mine runs, and its result is written to twin features.

### 4.1 Dispatch and grade control: the fleet-management system (Haulage and Dispatch; Geology and Ore Quality)

#### Dispatch decision

Whenever a truck finishes dumping, the dispatcher sends it to an eligible shovel:
- the one with the shortest queue;
- skipping broken, closed-off or fume-blocked shovels;
- if every shovel on its route is down, the truck waits and asks again.

Code: [mine/engine/modules/dispatch.py](mine/engine/modules/dispatch.py).

#### Grade-control decision

When the ROM pad grade falls below the 0.50 % Cu target, a loader reclaims the
high-grade stockpile (0.65 % Cu) into the crusher feed. It runs in the proportion that restores the target, up
to 800 t/h, and stops when the grade recovers.
Code: [mine/engine/modules/grade_control.py](mine/engine/modules/grade_control.py).

Without the system (`dispatch_policy: "fixed"`, the **Fleet-management system offline** scenario):
- trucks keep their shift-plan shovels;
- a truck whose shovel breaks waits 30 minutes for a supervisor to reassign it by radio ("reassigned by radio"
  in the event log), and the new assignment holds until shift change;
- grade control stops.

#### Where it shows

- each truck's `assigned_shovel` and shovel queue lengths;
- "rerouted" lines in the event log when a shovel breaks;
- `stockpile-hg.reclaim_tph` and `kpi.gc_reclaim_tph`;
- the event lines "grade control: ... reclaiming" and "... stopped".

#### Measured effect

Shovel S2 failure, 12 mine hours, against the shadow baseline, mean of 8 seeded runs
(`tools/validate.py`):

| | Ore mined | Copper output, mine hours 2-12 |
|---|---|---|
| System on | −23 % | −2.8 % |
| System offline (same failure, `dispatch_policy: "fixed"`) | −28 % | −6.6 % |

The system saves about 5 points of ore and more than half of the copper loss. In normal running with balanced
shovels its tonnage effect is about zero.

### 4.2 Predictive maintenance (Equipment Maintenance and Reliability)
- Decision. Every truck carries a coolant-temperature and oil-iron signal that rises as its wear-out
  failure approaches. The engine estimates health and hours to wear-out from that signal; it does not see the
  hidden failure time. With the strategy on (**Predictive maintenance** scenario), crossing the watch level
  raises a work order, and the truck is repaired at the next shift change (5-7 h, no tow) instead of failing
  in service (4-8 h plus a tow). Random faults stay unpredictable.
- Where it shows.
  - estimated `health_pct`, `coolant_temp_c` and `next_pm_due_h` on every truck;
  - "predictive work order raised" and "planned repair" events;
  - `kpi.current_unplanned_failures` against `kpi.baseline_unplanned_failures`, and `kpi.current_planned_repairs`.
- Effect. It pays off over days of mine time. Over 200 mine hours (about 3.3 real hours), summed over 8 seeded
  runs (`tools/validate.py`), unplanned failures fell 23 % (191 against 249, with 73 planned repairs instead), so
  there are fewer in-service breakdowns and tows. Mean fleet availability stayed about the same (92.2 % against
  92.2 %), because planned repairs also take trucks out. The literature reports +2 to +3 points (§8.2, §11-S9); the
  twin's planned-repair time is conservative.
- Code: [mine/engine/models/reliability.py](mine/engine/models/reliability.py), [mine/engine/modules/maintenance.py](mine/engine/modules/maintenance.py).

### 4.3 Energy and CO₂ (Energy)
- What it does. Accounting rather than a control decision:
  - diesel by truck class and haul phase;
  - grid power: crushing, conveying, grinding (mills draw their available power unless starved) and the trolley
    line, whose draw follows the electric trucks under it;
  - both converted into cost and CO₂ with Kazakh tariffs and a 0.80 kg CO₂/kWh grid factor.
- Where it shows. `kpi.current_fuel_l_h`, `kpi.current_energy_kwh_h`, `kpi.current_co2_t_h` and their
  baselines; `substation-01.load_kw`; mill `power_kw`.
- Effect. **Enable trolley assist** puts the two Komatsu 830E trucks on the main ore ramp: fleet diesel
  −4 to −7 %, ore mined up to +5 %. On Kazakhstan's coal-heavy grid the electricity they draw emits about as
  much CO₂ as the diesel it replaces (break-even ≈ 0.64 kg/kWh, §6.4). **Grid power curtailment (mills at 75%)**
  cuts grid energy and CO₂ 13-23 % together with output.
- Code: [mine/engine/modules/energy.py](mine/engine/modules/energy.py).

## 5. What-if scenarios

#### How to run

Open http://localhost:8000 and click a button in **What-if scenarios**. The interface writes
the request to the `scenario` twin (`PATCH /api/2/things/kz.kyzyltas.mine:scenario`). Ditto publishes the
change on MQTT, the engine applies it, and its effects return through the equipment twins and the `kpi` twin.

#### Custom what-if

Under **Custom what-if (set the scenario twin's values)** the same panel sets the twin's
fields directly:
- a shovel out of service;
- trucks parked (0-6);
- crusher availability;
- blast powder factor;
- dispatch mode;
- air temperature, −40 to 15 °C (below 0 °C haul roads cannot be watered; at −30 °C and colder winter speed caps
  apply);
- ore hardness as Bond work index (Axb follows);
- mill power available;
- haul-road rolling resistance;
- copper price.

Any combination can be tried. A value left at its baseline leaves the scenario preset in charge, so a preset can
also be adjusted (for example a cold snap with a different temperature).

Apply custom what-if sends them with `active_scenario: "custom"`. The fields can also be written straight
to the twin by any Ditto client.

#### How to undo

Click **↺ Undo - back to baseline**. It writes every `scenario` field back to its default
(`active_scenario: "none"`, a new `run_id`, `truck_count_delta: 0`, `shovel_down_id: ""`,
`crusher_availability: 1`, `blast_powder_factor: 1`, `fan_speed_factor: 1`, `dispatch_policy: "dynamic"`,
`ambient_temp_c: 15`, `ore_bwi_kwht: 14`, `mill_power_factor: 1`, `road_rr_bonus_pct: 0`, `cu_price_usd_t: 14500`).
- A shovel taken down by a scenario returns to service at once, and a fume exclusion lifts.
- The shadow baseline restarts as a copy of the mine, so every delta returns to zero.
- Scenarios stay active until undone. A restarted engine reads the scenario twin and continues where it was.

#### What to watch

- the banner over the 3D view: the causal chain and its key indicators;
- the event log;
- the baseline-versus-current table;
- the highlighted equipment in 3D.

Pit KPIs react within a minute. Plant KPIs react when the change reaches the mill, either directly
(plant-side scenarios) or after the crushed-ore buffer drains (pit-side scenarios).

#### Measured effects

Averages of current against the shadow baseline, seed 3, produced by
[mine/engine/tools/measure_scenarios.py](mine/engine/tools/measure_scenarios.py). One mine hour is one real
minute. Random equipment failures make longer windows vary between runs, so the live stand can differ.

| Button | What changes | First 2 mine hours | Mine hours 2-10 |
|---|---|---|---|
| Shovel S2 failure | `shovel-s2` down 10 mine hours; trucks re-dispatched to S1; grade control reclaims high-grade ore | ore mined −15 %, ore grade −5 %, haul cycle +18 % | ore −17 %, grade −12 %; Cu output −3 % (buffer and grade control) |
| Slope radar alarm (east wall) | main ore ramp closed; 2.7 km detour | ore −16 %, cycle +19 % | ore −30 %, cycle +28 %, buffer −16 % |
| Post-blast fume delay (winter inversion) | S1 and S3 blocked ~150 min | ore −15 %, cycle +19 % | ore −6 %, recovering |
| Siberian cold snap (−38 °C) | temperature, wind; no road watering | ore −5 %, cycle +9 % | ore −13 %, cycle +15 %, buffer −6 %; road PM10 about ×2 |
| Spring thaw (wet haul roads) | rolling resistance +2.5 points | ore −14 %, cycle +27 % | ore −26 %, cycle +39 %, buffer −13 % |
| Fleet cut (−2 trucks) | two ore trucks parked | ore −10 % | ore −14 %, buffer −7 % |
| Fleet-management system offline | fixed shift plan; no grade control | about 0 % | about 0 %; see §4.1 for its effect during a failure |
| Intensify blast (PF 0.30 -> 0.40 kg/t) | powder factor ×1.33 | mill feed +11 %, Cu output +10 %, revenue +11 % | same; buffer −10 % |
| Harder ore domain (BWi 14 -> 16) | Bond Wi 16, Axb 32 | mill feed, Cu output, revenue −24 %; buffer +3 % | same; buffer +11 % |
| Grid power curtailment (mills at 75%) | SAG and ball mills at 75 % power | mill feed, Cu output −25 %; grid energy −13 % | grid energy −23 %, CO₂ −21 % |
| Enable trolley assist | trolley on the main ore ramp (830E trucks) | diesel −4 % | diesel −7 %, ore +5 % |
| Copper price drop (−25%) | Cu $10,900/t, TC/RC +$80/dmt | revenue −19 % | revenue −19 % |
| Predictive maintenance (vs reactive) | maintenance strategy | no change yet | small; see §4.2 for 200 mine hours |

Each scenario's causal chain is also written to the event log when it starts.

---

## Data and Assumptions

#### Real versus synthetic

- All telemetry is synthetic. It is generated by the simulation engine. No operational data from any
  company is used.
- The mine is fictional. "Kyzyl-Tas" and its layout are invented. Its parameters are taken from public
  sources about Bozshakol and Aktogay, KAZ Minerals' operations in Kazakhstan.
- No third-party datasets are stored in this repository.

#### Where the parameters come from

Every number in [mine/engine/models/constants.py](mine/engine/models/constants.py)
carries a tag and a section reference into [mine/docs/03_domain.md](mine/docs/03_domain.md). That document lists
each value with its source, equations and worked examples. Section 12 there has the full source list.

| Tag | Meaning |
|---|---|
| [R] | Reported by the operator (KAZ Minerals reports and presentations) |
| [V] | Vendor or OEM specification |
| [L] | Literature, standards, regulators |
| [D] | Derived from cited numbers; the calculation is shown |
| [A] | Engineering assumption with a stated range (synthetic) |

#### Main sources

- Plant capacities, fleet, power and strip ratio. KAZ Minerals reports and presentations [S1-S5]: crusher
  4,186 t/h, SAG 28 MW, ball mills 2 × 22 MW, flotation, 214 MW site demand, −40 °C winters, Leica/Hexagon
  dispatch.
- Equipment. Cat 785C specifications [S11], Komatsu 830E-5 [S12], Hitachi EX3600-7 [S13],
  Caterpillar Performance Handbook [S14], trolley assist [S16, S17].
- Process models.
  - Fragmentation: Kuz-Ram (Kuznetsov 1973; Cunningham) [T2, T3].
  - Comminution: Bond [T1], Morrell [T10], mine-to-mill cases [S20-S22].
  - Flotation: Wills [T8].
- Safety and environment. US EPA AP-42 §13.2.2 for dust [S27], blast-fume codes of practice [S29, S30],
  slope-radar alarm studies [S31-S33].
- Energy and prices.
  - Kazakhstan grid emission factors [S37-S40], tariffs [S41], diesel price [S42];
  - exchange rate [S43], LME copper [S44], gold [S45];
  - 2026 TC/RC [S46];
  - emission factors: IPCC 2006 [S35], DESNZ 2024 [S36].
- Reliability. Weibull studies of haul trucks [S47, S48] and the SME handbook [T9].

Assumptions to be aware of (all tagged [A] in the code):
- the haul-road network and pit geometry;
- maintenance and failure parameters, since no public site data exists;
- the high-grade stockpile size (150 kt) and grade (0.65 % Cu);
- the grade-control target (0.50 %) and loader rate (800 t/h);
- the ROM pad capacity (150 kt) and the crushed-ore stockpile starting 70 % full;
- the fixed plant (crusher, mills) starting early in its maintenance cycle, as after a scheduled reline;
- the ball-mill design margin (20 % above nominal) and mill no-load power (25 %);
- the 30-minute radio reassignment without a dispatch system;
- the 0.80 kg CO₂/kWh grid factor, the central value of a 0.60-1.05 range;
- the delivered industrial power tariff, which is an estimate;
- PM10 watering efficiency (65 %).

#### Deviations from the reference site

- Fleet size and strip ratio. The twin has 14 trucks, 10 on ore and 4 on waste, against Bozshakol's 18. It
  meets the mill's ore demand, but its realised strip ratio is about 0.39 against the planned 0.7.
- Cycle time. The truck cycle (24 min) is a little longer than the ~22 min implied by the published fleet
  plan, because the twin's roads are slightly longer and it includes queueing.

#### Licences

Our code is MIT ([LICENSE](LICENSE)). OpenEgiz is MIT, and parts derived from OpenTwins are under
Apache 2.0 ([NOTICE](NOTICE), [LICENSES/](LICENSES/)). The interface's npm dependencies keep their own licences
(listed in [mine/ui/package-lock.json](mine/ui/package-lock.json)). The engine uses `paho-mqtt` (EPL-2.0/EDL-1.0).

## 7. Limitations

- Haul trips. Each haul leg is timed as one block over its road segments. Per-segment traffic counts are
  therefore estimated from segment length, not from truck positions.
- Not modelled:
  - fuel tank levels and refuelling;
  - block-model grade variability (each face has one grade);
  - the slope-failure event itself (the slope alarm closes the ramp; the wall does not fail);
  - drill availability feeding back into blasting.
- Copper price drop. It changes revenue only; the cut-off grade does not move.
- Scenario parameters. Wind, slope-radar velocity and fume-delay length exist only inside their preset
  scenarios; the other drivers are adjustable through the custom what-if.
- Back-pressure. Plant-to-pit back-pressure (ROM pad full) takes days of mine time to build up.
- Blast fragmentation. Absolute X50/X80 values run 15-20 % above the reference worked example because of
  the chosen rock factor. Relative changes match.
- Dispatch rule. Dispatch uses a shortest-queue rule, not a full LP optimiser.
- Scenario numbers vary from run to run. Scenario effects over longer windows depend on random equipment
  failures. The table above is one seeded run; the first-two-hours effects are the most repeatable.

## 8. Verification

- Engine tests. `python mine/engine/tests/test_models.py`, `test_simulation.py` and `test_contract.py` run
  58 checks with no network:
  - 36 check physics against worked examples, and that stockpiles conserve mass;
  - 18 check scenario behaviour:
    - effect directions;
    - Undo ending scenario-imposed outages;
    - the baseline copy;
    - full twin IDs;
    - the custom scenario and its numeric fields;
    - the mass balance;
    - ball-mill outages;
    - radio reassignment under fixed dispatch;
    - a shovel failure on a shovel that is already broken;
  - 4 check that the twin model and the engine use the same features.
- Scenario table and figures. `python mine/engine/tools/measure_scenarios.py` reproduces the scenario
  table; `python mine/engine/tools/validate.py` reproduces the validation and module figures.
- Stack check. `make smoke` checks the full chain on a running stack:
  - MQTT -> Ditto -> Telegraf -> InfluxDB, Grafana and the platform services;
  - the mine twins and the scenario twin exist;
  - mine telemetry reaches InfluxDB;
  - the interface and its proxy answer.
