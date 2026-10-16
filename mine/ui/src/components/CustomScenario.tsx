import { useState } from "react";
import { useMineStore } from "../store/useMineStore";
import { buildResetPatch } from "../lib/scenarios";

const NS = "kz.kyzyltas.mine:";
const SHOVELS = [
  { id: "", label: "none" },
  { id: `${NS}shovel-s1`, label: "S1 (ore, 0.45% Cu)" },
  { id: `${NS}shovel-s2`, label: "S2 (ore, 0.58% Cu)" },
  { id: `${NS}shovel-s3`, label: "S3 (waste)" },
  { id: `${NS}shovel-s4`, label: "S4 (waste)" }
];

/**
 * Custom what-if: writes chosen values straight to the scenario twin's fields
 * (active_scenario "custom"), so any combination can be tried without code changes.
 */
export function CustomScenario({ disabled }: { disabled: boolean }) {
  const triggerScenario = useMineStore((s) => s.triggerScenario);
  const [shovel, setShovel] = useState("");
  const [trucks, setTrucks] = useState(0);
  const [crusher, setCrusher] = useState(1);
  const [powder, setPowder] = useState(1);
  const [dispatch, setDispatch] = useState<"dynamic" | "fixed">("dynamic");
  const [temp, setTemp] = useState(15);
  const [bwi, setBwi] = useState(14);
  const [millPower, setMillPower] = useState(1);
  const [rr, setRr] = useState(0);
  const [price, setPrice] = useState(14500);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function apply() {
    setBusy(true);
    setError(null);
    try {
      await triggerScenario({
        ...buildResetPatch(),
        active_scenario: "custom",
        shovel_down_id: shovel,
        truck_count_delta: trucks,
        crusher_availability: crusher,
        blast_powder_factor: powder,
        dispatch_policy: dispatch,
        ambient_temp_c: temp,
        ore_bwi_kwht: bwi,
        mill_power_factor: millPower,
        road_rr_bonus_pct: rr,
        cu_price_usd_t: price
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="custom-scenario">
      <summary>Custom what-if (set the scenario twin's values)</summary>
      <label>
        Shovel out of service
        <select aria-label="Shovel out of service" value={shovel} onChange={(e) => setShovel(e.target.value)}>
          {SHOVELS.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
            </option>
          ))}
        </select>
      </label>
      <label>
        Trucks parked: <b>{-trucks}</b>
        <input aria-label="Trucks parked" type="range" min={-6} max={0} step={1} value={trucks} onChange={(e) => setTrucks(Number(e.target.value))} />
      </label>
      <label>
        Crusher availability: <b>{Math.round(crusher * 100)}%</b>
        <input aria-label="Crusher availability" type="range" min={0} max={1} step={0.05} value={crusher} onChange={(e) => setCrusher(Number(e.target.value))} />
      </label>
      <label>
        Blast powder factor: <b>×{powder.toFixed(2)}</b> ({(0.3 * powder).toFixed(2)} kg/t)
        <input aria-label="Blast powder factor" type="range" min={0.8} max={1.5} step={0.05} value={powder} onChange={(e) => setPowder(Number(e.target.value))} />
      </label>
      <label>
        Dispatch
        <select aria-label="Dispatch mode" value={dispatch} onChange={(e) => setDispatch(e.target.value as "dynamic" | "fixed")}>
          <option value="dynamic">dynamic (fleet-management system on)</option>
          <option value="fixed">fixed shift plan (system offline)</option>
        </select>
      </label>
      <label>
        Air temperature: <b>{temp} °C</b> {temp < 0 ? "(no road watering)" : ""}
        <input aria-label="Air temperature" type="range" min={-40} max={15} step={1} value={temp} onChange={(e) => setTemp(Number(e.target.value))} />
      </label>
      <label>
        Ore hardness (Bond Wi): <b>{bwi.toFixed(1)} kWh/t</b>
        <input aria-label="Ore hardness" type="range" min={10} max={20} step={0.5} value={bwi} onChange={(e) => setBwi(Number(e.target.value))} />
      </label>
      <label>
        Mill power available: <b>{Math.round(millPower * 100)}%</b>
        <input aria-label="Mill power available" type="range" min={0.5} max={1} step={0.05} value={millPower} onChange={(e) => setMillPower(Number(e.target.value))} />
      </label>
      <label>
        Haul-road rolling resistance: <b>+{rr.toFixed(1)} points</b>
        <input aria-label="Haul-road rolling resistance" type="range" min={0} max={5} step={0.5} value={rr} onChange={(e) => setRr(Number(e.target.value))} />
      </label>
      <label>
        Copper price: <b>${price.toLocaleString("en-US")}/t</b>
        <input aria-label="Copper price" type="range" min={8000} max={18000} step={250} value={price} onChange={(e) => setPrice(Number(e.target.value))} />
      </label>
      <button type="button" className="scenario-btn custom-apply" disabled={disabled || busy} onClick={apply}>
        {busy ? "Applying..." : "Apply custom what-if"}
      </button>
      {error && (
        <p className="scenario-error" role="alert">
          {error}
        </p>
      )}
    </details>
  );
}
