import { useEffect, useState } from "react";
import { buildFluxQuery, queryFlux, type InfluxPoint } from "../lib/influx";
import { KPI_THING_ID } from "../types";

// History from InfluxDB: mill feed vs ore mined over the last
// 20 real minutes (= 20 mine hours at 60x). The gap between the two lines is
// what the crushed-ore stockpile absorbs. Polled every 15 s (Telegraf
// flushes every ~10 s).

const SERIES = [
  { feature: "current_tph", label: "SAG mill feed", color: "#58a6ff" },
  { feature: "current_ore_mined_tph", label: "Ore mined (pit)", color: "#f0883e" }
];

export function TrendChart() {
  const [data, setData] = useState<InfluxPoint[][]>([]);
  const [status, setStatus] = useState<"loading" | "ok" | "empty">("loading");

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      const results = await Promise.all(SERIES.map((s) => queryFlux(buildFluxQuery(KPI_THING_ID, s.feature, "-20m"))));
      if (cancelled) return;
      setData(results);
      setStatus(results.some((r) => r.length > 1) ? "ok" : "empty");
    }
    poll();
    const id = setInterval(poll, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  return (
    <section className="panel trend-panel" aria-labelledby="trend-heading">
      <h2 id="trend-heading">
        Pit vs plant <span className="h-note">last 20 min ≈ 20 mine h · InfluxDB</span>
      </h2>
      {status === "loading" && <p className="empty-state">Loading history...</p>}
      {status === "empty" && <p className="empty-state">No history yet - points appear once Telegraf has flushed (~10 s).</p>}
      {status === "ok" && <Chart data={data} />}
    </section>
  );
}

function Chart({ data }: { data: InfluxPoint[][] }) {
  const W = 360;
  const H = 96;
  const all = data.flat();
  const times = all.map((p) => Date.parse(p.time));
  const t0 = Math.min(...times);
  const t1 = Math.max(...times);
  const values = all.map((p) => p.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  const pad = (max - min) * 0.1 || max * 0.05 || 1;
  min -= pad;
  max += pad;
  const x = (t: string) => 4 + ((Date.parse(t) - t0) / Math.max(1, t1 - t0)) * (W - 8);
  const y = (v: number) => H - 14 - ((v - min) / (max - min)) * (H - 22);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="trend-svg" role="img" aria-label="Mill feed and ore mined over the last 20 minutes">
        <text x={4} y={10} className="trend-axis">
          {Math.round(max).toLocaleString("en-US")} t/h
        </text>
        <text x={4} y={H - 2} className="trend-axis">
          {Math.round(min).toLocaleString("en-US")} t/h
        </text>
        {data.map((pts, i) =>
          pts.length > 1 ? (
            <path
              key={i}
              d={pts.map((p, k) => `${k === 0 ? "M" : "L"}${x(p.time).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ")}
              fill="none"
              stroke={SERIES[i].color}
              strokeWidth={2}
            />
          ) : null
        )}
      </svg>
      <ul className="trend-legend">
        {SERIES.map((s, i) => {
          const last = data[i]?.[data[i].length - 1]?.value;
          return (
            <li key={s.feature}>
              <span className="legend-dot" style={{ background: s.color }} aria-hidden="true" />
              {s.label}: <strong>{last === undefined ? "-" : `${Math.round(last).toLocaleString("en-US")} t/h`}</strong>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
