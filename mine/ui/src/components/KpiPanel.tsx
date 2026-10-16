import { useMineStore } from "../store/useMineStore";
import { getKpiThing, featureNumber } from "../lib/selectors";
import { metric, readMetric, deltaTone, formatDelta, formatMetric, unitFor, fmt } from "../lib/kpi";
import type { DittoThing } from "../types";

const HEADLINE = ["tph", "cu_tph", "nsr_usd_h", "ore_mined_tph", "energy_kwh_h", "co2_t_h"];

/** Headline KPI cards (current value + delta vs the engine's shadow baseline) and the stockpile buffer gauge. */
export function KpiPanel() {
  const kpi = useMineStore((s) => getKpiThing(s.things));
  const loaded = useMineStore((s) => s.loaded);

  return (
    <section className="panel kpi-panel" aria-labelledby="kpi-heading">
      <h2 id="kpi-heading">Live KPIs <span className="h-note">vs baseline</span></h2>
      {loaded && !kpi && <p className="empty-state">Waiting for the KPI twin to report...</p>}
      <ul className="kpi-grid">
        {HEADLINE.map((key) => {
          const m = metric(key)!;
          const r = readMetric(kpi, m);
          const tone = deltaTone(r.deltaPct, m.good);
          return (
            <li key={key} className="kpi-card">
              <span className="kpi-label">{m.label}</span>
              <span className="kpi-value">
                {formatMetric(m, r.current)}
                <span className="kpi-unit"> {unitFor(m)}</span>
              </span>
              <span className={`kpi-delta tone-${tone}`} aria-label={`${formatDelta(r.deltaPct)} versus baseline`}>
                {formatDelta(r.deltaPct)}
              </span>
            </li>
          );
        })}
      </ul>
      <BufferGauge kpi={kpi} />
      <p className="kpi-totals">
        Since start: <strong>{fmt(featureNumber(kpi, "cu_output_total_t", NaN), 1)} t</strong> Cu in concentrate ·{" "}
        <strong>{fmt(featureNumber(kpi, "co2_total_t", NaN), 0)} t</strong> CO₂ ·{" "}
        <strong>{fmt(featureNumber(kpi, "trucks_operating", NaN), 0)}</strong> trucks operating
      </p>
    </section>
  );
}

// Buffer trend: (mine hour, buffer_h) samples to estimate drain/fill rate.
const history: { t: number; v: number }[] = [];

function bufferTrend(simH: number | null, buffer: number | null): number | null {
  if (simH === null || buffer === null) return null;
  const last = history[history.length - 1];
  if (!last || simH - last.t >= 0.05) history.push({ t: simH, v: buffer });
  if (last && simH < last.t - 0.5) history.length = 0; // engine restarted
  while (history.length > 2 && simH - history[0].t > 1.5) history.shift();
  if (history.length < 3) return null;
  const a = history[0];
  const b = history[history.length - 1];
  if (b.t - a.t < 0.3) return null;
  return (b.v - a.v) / (b.t - a.t); // hours of feed per mine hour
}

function BufferGauge({ kpi }: { kpi: DittoThing | undefined }) {
  const simH = useMineStore((s) => s.simTimeH);
  const speedup = useMineStore((s) => s.speedup);
  const sagState = useMineStore((s) => {
    const v = s.things["kz.kyzyltas.mine:mill-sag-01"]?.features?.state?.properties.value;
    return typeof v === "string" ? v : "";
  });
  const r = readMetric(kpi, metric("buffer_h")!);
  const cur = r.current;
  const base = r.baseline;
  // Full pile: 40 kt at the SAG mill's rated 3,425 t/h.
  const max = Math.max(11.7, (cur ?? 0) * 1.02);
  const pct = cur === null ? 0 : Math.max(0, Math.min(100, (cur / max) * 100));
  const basePct = base === null ? null : Math.max(0, Math.min(100, (base / max) * 100));
  const slope = bufferTrend(simH, cur);
  const tone = cur === null ? "flat" : cur < 3 ? "bad" : cur < 7 ? "warn" : "good";

  let trendText = "Holding steady";
  if (sagState === "down") {
    trendText = "SAG mill DOWN - the pile fills while the crusher runs";
  } else if (slope !== null && slope < -0.15 && cur !== null) {
    const hoursLeft = cur / -slope;
    trendText = `Draining ${(-slope).toFixed(1)} h per mine hour - empty in ~${hoursLeft.toFixed(0)} mine h (≈${((hoursLeft * 60) / speedup).toFixed(0)} real min)`;
  } else if (slope !== null && slope > 0.15) {
    trendText = `Filling ${slope.toFixed(1)} h per mine hour`;
  } else if (slope === null) {
    trendText = "Measuring trend...";
  }

  return (
    <div className="buffer-gauge" role="group" aria-label="Crushed-ore stockpile buffer">
      <div className="buffer-head">
        <span className="buffer-title">Crushed-ore stockpile</span>
        <span className={`buffer-value tone-${tone}`}>
          {cur === null ? "-" : cur.toFixed(1)} <span className="kpi-unit">h of feed at full rate</span>
        </span>
      </div>
      <div
        className="buffer-bar"
        role="meter"
        aria-valuemin={0}
        aria-valuemax={Math.round(max)}
        aria-valuenow={cur ?? 0}
        aria-label="Hours of mill feed in the crushed-ore stockpile at full mill rate"
      >
        <div className={`buffer-fill tone-${tone}`} style={{ width: `${pct}%` }} />
        {basePct !== null && <div className="buffer-base" style={{ left: `${basePct}%` }} title="Baseline" />}
      </div>
      <p className="buffer-note">
        {trendText}. Baseline {base === null ? "-" : base.toFixed(1)} h. The mill keeps running on this buffer, so
        haulage losses reach plant output only once it runs low.
      </p>
    </div>
  );
}
