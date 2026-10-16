import { useEffect, useState } from "react";
import { useMineStore, mineTimeNow } from "../store/useMineStore";

const STATUS_TEXT: Record<string, string> = {
  connecting: "Connecting...",
  live: "Live",
  reconnecting: "Reconnecting...",
  error: "Feed error - retrying"
};

/** Mine hour 0 is the start of day shift, 07:00 on day 1 (shifts change at 07:00 and 19:00). */
export const SHIFT_START_H = 7;

/** Hour of the day (0-24) at mine time h. */
export function hourOfDay(h: number): number {
  const c = h + SHIFT_START_H;
  return c - Math.floor(c / 24) * 24;
}

export function formatMineTime(h: number | null): string {
  if (h === null || !Number.isFinite(h)) return "-";
  h += SHIFT_START_H;
  const day = Math.floor(h / 24) + 1;
  const minutes = Math.floor((h - Math.floor(h / 24) * 24) * 60);
  const hh = String(Math.floor(minutes / 60)).padStart(2, "0");
  const mm = String(minutes % 60).padStart(2, "0");
  return `day ${day}, ${hh}:${mm}`;
}

/** Short stamp for the event log: "D1 03:12". */
export function formatMineStamp(h: number | undefined): string {
  if (h === undefined || !Number.isFinite(h)) return "";
  h += SHIFT_START_H;
  const day = Math.floor(h / 24) + 1;
  const minutes = Math.floor((h - Math.floor(h / 24) * 24) * 60);
  return `D${day} ${String(Math.floor(minutes / 60)).padStart(2, "0")}:${String(minutes % 60).padStart(2, "0")}`;
}

function MineClock() {
  const speedup = useMineStore((s) => s.speedup);
  const [, tick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => tick((t) => t + 1), 1000);
    return () => clearInterval(id);
  }, []);
  const h = mineTimeNow(useMineStore.getState());
  const realPerHour = 60 / speedup;
  const ratio = realPerHour === 1 ? "1 min = 1 h" : `${realPerHour.toFixed(1)} min = 1 h`;
  return (
    <div className="mine-clock" role="timer" aria-label={`Mine time ${formatMineTime(h)}, simulation running at ${speedup} times real time`}>
      <span className="mine-clock-label">Mine time</span>
      <span className="mine-clock-value">{formatMineTime(h)}</span>
      <span className="mine-clock-speed">
        {speedup}× ({ratio})
      </span>
    </div>
  );
}

export function Header() {
  const status = useMineStore((s) => s.connectionStatus);
  const loaded = useMineStore((s) => s.loaded);
  const loadError = useMineStore((s) => s.loadError);
  const count = useMineStore((s) => s.catalogueCount);
  const fps = useMineStore((s) => s.fps);
  const performanceMode = useMineStore((s) => s.performanceMode);
  const autoPerformance = useMineStore((s) => s.autoPerformance);
  const setPerformanceMode = useMineStore((s) => s.setPerformanceMode);

  return (
    <header className="app-header">
      <div className="brand">
        <h1>Kyzyl-Tas Mine</h1>
        <p>Open-pit copper-gold digital twin · OpenEgiz</p>
      </div>
      <MineClock />
      <div className="header-status" role="status">
        <span className={`status-dot status-${status}`} aria-hidden="true" />
        <span>{STATUS_TEXT[status] ?? status}</span>
        <span className="sep">·</span>
        <span>{loaded ? `${count} twins` : "Loading twins..."}</span>
        {loadError && <span className="status-error">Catalogue error: {loadError}</span>}
        <span className="sep">·</span>
        <span title="3D frame rate">{fps > 0 ? `${fps} fps` : "- fps"}</span>
      </div>
      <label className="perf-toggle">
        <input type="checkbox" checked={performanceMode} onChange={(e) => setPerformanceMode(e.target.checked)} />
        Performance mode{autoPerformance ? " (auto)" : ""}
      </label>
    </header>
  );
}
