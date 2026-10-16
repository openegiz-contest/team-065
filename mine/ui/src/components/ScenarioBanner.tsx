import { useMineStore } from "../store/useMineStore";
import { getKpiThing, getScenarioThing, featureString, featureNumber } from "../lib/selectors";
import { SCENARIOS, CHAIN_CHECKS, chainCheckMet } from "../lib/scenarios";
import { metric, readMetric, deltaTone, formatDelta, formatMetric, unitFor } from "../lib/kpi";

/** Overlay across the top of the 3D view: what is active, its causal chain and the KPIs to watch. */
export function ScenarioBanner() {
  const things = useMineStore((s) => s.things);
  const active = featureString(getScenarioThing(things), "active_scenario", "none");
  const scenario = getScenarioThing(things);
  const kpi = getKpiThing(things);
  let def = SCENARIOS.find((s) => s.id === active);
  if (!def && active === "custom") {
    // Custom what-if: describe the values actually set on the scenario twin.
    const steps: string[] = [];
    const shovel = featureString(scenario, "shovel_down_id", "");
    const trucks = featureNumber(scenario, "truck_count_delta", 0);
    const crusher = featureNumber(scenario, "crusher_availability", 1);
    const powder = featureNumber(scenario, "blast_powder_factor", 1);
    const dispatch = featureString(scenario, "dispatch_policy", "dynamic");
    if (shovel) steps.push(`${shovel.split(":").pop()} out of service`);
    if (trucks < 0) steps.push(`${-trucks} trucks parked`);
    if (crusher < 1) steps.push(`crusher availability ${Math.round(crusher * 100)}%`);
    if (powder !== 1) steps.push(`powder factor ×${powder.toFixed(2)}`);
    if (dispatch === "fixed") steps.push("dispatch and grade control offline");
    const temp = featureNumber(scenario, "ambient_temp_c", 15);
    const bwi = featureNumber(scenario, "ore_bwi_kwht", 14);
    const millPower = featureNumber(scenario, "mill_power_factor", 1);
    const rr = featureNumber(scenario, "road_rr_bonus_pct", 0);
    const price = featureNumber(scenario, "cu_price_usd_t", 14500);
    if (temp !== 15) steps.push(`air ${temp} °C${temp < 0 ? " (no road watering)" : ""}`);
    if (bwi !== 14) steps.push(`ore Bond Wi ${bwi.toFixed(1)} kWh/t`);
    if (millPower !== 1) steps.push(`mill power ${Math.round(millPower * 100)}%`);
    if (rr !== 0) steps.push(`road rolling resistance +${rr.toFixed(1)} points`);
    if (price !== 14500) steps.push(`copper $${price.toLocaleString("en-US")}/t`);
    def = {
      id: "custom",
      label: "Custom what-if",
      group: "pit",
      short: "",
      description: "",
      chain: steps.length ? steps : ["all values at their defaults"],
      watch: ["ore_mined_tph", "haul_cycle_min", "buffer_h", "tph", "cu_tph", "nsr_usd_h"],
      domainRef: "",
      buildPatch: () => ({})
    };
  }

  if (active === "none") {
    return (
      <div className="scenario-banner is-baseline" role="status">
        <span className="banner-tag">Baseline</span>
        <span>No scenario active - pick a what-if scenario on the left to see its knock-on effects here and in the 3D view.</span>
      </div>
    );
  }

  return (
    <div className="scenario-banner is-active" role="status" aria-live="polite">
      <div className="banner-top">
        <span className="banner-tag">Scenario active</span>
        <strong className="banner-title">{def?.label ?? active}</strong>
      </div>
      {def && (
        <ol className="banner-chain" aria-label="Cause and effect chain (typical effects from seeded runs)">
          {def.chain.map((step, i) => {
            const check = CHAIN_CHECKS[def!.id]?.[i];
            const met = !check || chainCheckMet(check, things);
            return (
              <li key={i} className={met ? undefined : "chain-waiting"}>
                {step}
                {!met && check && <span className="chain-wait-note"> (waiting: {check.waiting})</span>}
              </li>
            );
          })}
        </ol>
      )}
      {def && (
        <ul className="banner-watch" aria-label="Key indicators versus baseline">
          {def.watch.map((key) => {
            const m = metric(key);
            if (!m) return null;
            const r = readMetric(kpi, m);
            const tone = deltaTone(r.deltaPct, m.good);
            return (
              <li key={key} className={`watch-chip tone-${tone}`}>
                <span className="watch-label">{m.label}</span>
                <span className="watch-value">
                  {formatMetric(m, r.current)} {unitFor(m)}
                </span>
                {m.unit === "count" ? (
                  <span className="watch-delta tone-flat">baseline {r.baseline ?? "-"}</span>
                ) : r.deltaPct !== null ? (
                  <span className="watch-delta">{formatDelta(r.deltaPct)}</span>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
