import { useMineStore } from "../store/useMineStore";
import { getKpiThing, featureNumber } from "../lib/selectors";
import { METRICS, GROUPS, readMetric, deltaTone, formatDelta, formatMetric, unitFor } from "../lib/kpi";

/**
 * Baseline vs current, grouped Pit / Plant / Economics & energy. Baseline
 * values come from the engine's shadow simulation (same clock, no scenario),
 * published on the kpi twin as baseline_<k>; delta_<k>_pct is the engine's.
 */
export function BaselineDelta() {
  const kpi = useMineStore((s) => getKpiThing(s.things));
  const loaded = useMineStore((s) => s.loaded);

  const failCur = featureNumber(kpi, "current_unplanned_failures", NaN);
  const failBase = featureNumber(kpi, "baseline_unplanned_failures", NaN);
  const pmCur = featureNumber(kpi, "current_planned_repairs", NaN);
  const pmBase = featureNumber(kpi, "baseline_planned_repairs", NaN);

  return (
    <section className="panel compare-panel" aria-labelledby="compare-heading">
      <h2 id="compare-heading">Scenario vs baseline</h2>
      {!loaded && <p className="empty-state">Loading...</p>}
      <table className="compare-table">
        <thead>
          <tr>
            <th scope="col">Indicator</th>
            <th scope="col">Baseline</th>
            <th scope="col">Now</th>
            <th scope="col">Δ</th>
          </tr>
        </thead>
        {GROUPS.map((g) => (
          <tbody key={g.id}>
            <tr className="group-row">
              <th scope="colgroup" colSpan={4}>
                <span className="group-title">{g.title}</span>
                <span className="group-note">{g.note}</span>
              </th>
            </tr>
            {METRICS.filter((m) => m.group === g.id).map((m) => {
              const r = readMetric(kpi, m);
              const tone = deltaTone(r.deltaPct, m.good);
              return (
                <tr key={m.key}>
                  <th scope="row">
                    {m.label} <span className="unit">{unitFor(m)}</span>
                  </th>
                  <td>{formatMetric(m, r.baseline)}</td>
                  <td>{formatMetric(m, r.current)}</td>
                  <td className={`delta tone-${tone}`}>{formatDelta(r.deltaPct)}</td>
                </tr>
              );
            })}
            {g.id === "pit" && (
              <>
                <tr>
                  <th scope="row">
                    Unplanned failures <span className="unit">count</span>
                  </th>
                  <td>{Number.isFinite(failBase) ? failBase : "-"}</td>
                  <td>{Number.isFinite(failCur) ? failCur : "-"}</td>
                  <td className={`delta tone-${countTone(failCur, failBase, "down")}`}>{countDelta(failCur, failBase)}</td>
                </tr>
                <tr>
                  <th scope="row">
                    Planned repairs (work orders) <span className="unit">count</span>
                  </th>
                  <td>{Number.isFinite(pmBase) ? pmBase : "-"}</td>
                  <td>{Number.isFinite(pmCur) ? pmCur : "-"}</td>
                  <td className="delta tone-flat">{countDelta(pmCur, pmBase)}</td>
                </tr>
              </>
            )}
          </tbody>
        ))}
      </table>
    </section>
  );
}

function countDelta(cur: number, base: number): string {
  if (!Number.isFinite(cur) || !Number.isFinite(base)) return "-";
  const d = cur - base;
  return d === 0 ? "±0" : d > 0 ? `+${d}` : `−${-d}`;
}

function countTone(cur: number, base: number, good: "up" | "down"): "good" | "bad" | "flat" {
  if (!Number.isFinite(cur) || !Number.isFinite(base) || cur === base) return "flat";
  return (cur > base) === (good === "up") ? "good" : "bad";
}
