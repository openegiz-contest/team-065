# Kyzyl-Tas - a digital twin of an open-pit copper mine on OpenEgiz

Kyzyl-Tas is a fictional open-pit copper-gold mine with a 30 Mt/a concentrator. Its equipment, process
capacities, grades and costs are taken from public data for Kazakhstan's Bozshakol and Aktogay operations
(sources in [SUBMISSION.md](SUBMISSION.md#data-and-assumptions)). Every mine object is an Eclipse Ditto twin
on the OpenEgiz platform. A physics-based simulation engine drives the twins over MQTT. A 3D web interface
reads them back from the platform and runs what-if scenarios.

## Start

On a clean Ubuntu 24.04 machine with Docker Engine and Compose v2.20+ (the user must be in the `docker` group),
from the repository root:

```bash
sudo apt-get update && sudo apt-get install -y make
make up
```

`make up` starts the OpenEgiz platform and the mine together. The first run downloads about 2.5 GB of images
and takes several minutes. When it finishes it prints the addresses below. No other step is needed.

Optional end-to-end check of the running stack (platform and mine):

```bash
make smoke
```

## What to open

| Address | What it is | Login |
|---|---|---|
| **http://localhost:8000** | **Kyzyl-Tas 3D mine: live twins, KPIs, event log, what-if scenarios, twin model** | none |
| http://localhost:3000 | Grafana: mine dashboard "Kyzyl-Tas Mine - KPIs vs baseline" (home page) | none to view |
| http://localhost:3000/a/ertis-opentwins-app/twins | OpenEgiz **Twins** / **Types** pages (all mine twins, hierarchy) | `admin` / printed by `make up` (also in `deploy/compose/.env`) |
| http://localhost:8080/api/2 | Ditto API | `ditto` / printed by `make up` |

## A two-minute tour

1. Open http://localhost:8000. Haul trucks move in the pit and the mine clock runs at 60× (one real minute is
   one mine hour). The right panel shows live KPIs, each next to the value of a parallel baseline run.
2. In **What-if scenarios**, click **Shovel S2 failure**. Within about a minute:
   - shovel S2 turns red in the 3D view and on the minimap;
   - its trucks are re-dispatched to S1 and the event log records the chain;
   - ore mined and ore grade fall against the baseline;
   - grade control starts reclaiming the high-grade stockpile (highlighted in 3D).
3. Click **↺ Undo - back to baseline**. Every scenario field returns to its default, S2 returns to service and
   the comparison restarts from zero.
4. Open **Twin model** (top right of the 3D view) to browse all twins, or click any machine for its live data.
   **Custom what-if** at the top of the scenario panel sets the scenario twin's values directly: shovel out,
   trucks parked, crusher, powder factor, dispatch, temperature, ore hardness, mill power, road condition, copper price.

Each scenario and module is described in [SUBMISSION.md](SUBMISSION.md), with how to see it and how to undo it.

## How it is built

```
mine-engine (Python simulation)
   │  Ditto protocol "merge" commands, MQTT topic telemetry/<twin>
   ▼
Mosquitto ──► Eclipse Ditto (87 twins, namespace kz.kyzyltas.mine) ──► MQTT events ──► Telegraf ──► InfluxDB
                 ▲                    │                                                              │
                 │ PATCH scenario     │ REST + server-sent events                                    │ Flux
                 │                    ▼                                                              ▼
              mine-ui (nginx + React/three.js) ◄──────────────────────────────────────────── history
```

- mine-setup creates 21 type twins and 66 instance twins: mine, pit, benches, roads, 14 trucks, 4 shovels,
  drills, crusher, conveyors, mills, flotation, tailings, stockpiles, fans, substation, weather station,
  slope radars, dispatch, plant, KPI and scenario control.
- mine-engine simulates the mine and publishes every state change to Ditto through MQTT. It reads
  what-if requests from the `scenario` twin.
- mine-ui shows the twins in 3D and 2D and writes scenario requests to the `scenario` twin. Its nginx
  adds the platform credentials server-side, so the browser needs no login.

The services are defined in [deploy/compose/mine.yml](deploy/compose/mine.yml), and the Makefile always
starts them with the platform. Platform documentation: [OPENEGIZ.md](OPENEGIZ.md).

## Repository layout (additions to the OpenEgiz template)

| Path | Contents |
|---|---|
| [mine/setup/](mine/setup/) | Twin catalogue `model.json` and loader |
| [mine/engine/](mine/engine/) | Simulation: `models/` (physics), `modules/` (dispatch, grade control, maintenance, energy), scenarios, tests |
| [mine/ui/](mine/ui/) | 3D interface: `src/` and the built `dist/` that is served |
| [deploy/compose/mine.yml](deploy/compose/mine.yml) | The three mine services |
| [deploy/compose/mine-ui/](deploy/compose/mine-ui/) | nginx configuration for the interface |
| [SUBMISSION.md](SUBMISSION.md) | Modules, scenarios, data and assumptions |
| [presentation.pdf](presentation.pdf) | Presentation |

## Stop

```bash
make down    # stop, keep data
make clean   # stop and delete all data and generated credentials
```

## License

The mine code is MIT ([LICENSE](LICENSE)). OpenEgiz and third-party components keep their own licenses
([NOTICE](NOTICE), [LICENSES/](LICENSES/)).
