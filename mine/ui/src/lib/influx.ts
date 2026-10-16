// History/trend client for InfluxDB 2 via the same-origin proxy:
//   POST /influx/query   body: raw Flux text   Content-Type: application/vnd.flux
// Schema (OpenEgiz Telegraf): bucket "default", measurement "mqtt_consumer",
// fields "value_<feature>_properties_value", tag "thingId". Telegraf flushes
// every ~10s, so don't poll faster than that.

export interface InfluxPoint {
  time: string;
  value: number;
}

/** Build a Flux query for one feature's history on one thing. */
export function buildFluxQuery(thingId: string, feature: string, rangeStart = "-15m"): string {
  const field = `value_${feature}_properties_value`;
  return [
    `from(bucket: "default")`,
    `  |> range(start: ${rangeStart})`,
    `  |> filter(fn: (r) => r._measurement == "mqtt_consumer")`,
    `  |> filter(fn: (r) => r.thingId == "${thingId}")`,
    `  |> filter(fn: (r) => r._field == "${field}")`,
    `  |> aggregateWindow(every: 10s, fn: last, createEmpty: false)`,
    `  |> keep(columns: ["_time", "_value"])`
  ].join("\n");
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Run a Flux query and parse the InfluxDB annotated-CSV response into
 * {time, value} points. Retries with backoff; returns [] (empty state)
 * rather than throwing, so a chart panel can render an empty-state message
 * instead of crashing when Influx/Telegraf isn't reachable yet.
 */
export async function queryFlux(flux: string, maxAttempts = 3): Promise<InfluxPoint[]> {
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const res = await fetch("/influx/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/vnd.flux",
          Accept: "text/csv"
        },
        body: flux
      });
      if (!res.ok) {
        throw new Error(`Influx query failed: HTTP ${res.status}`);
      }
      const text = await res.text();
      return parseAnnotatedCsv(text);
    } catch (err) {
      lastError = err;
      await sleep(600 * (attempt + 1));
    }
  }
  console.warn("influx query giving up after retries", lastError);
  return [];
}

/** Minimal parser for InfluxDB's annotated CSV (handles the single-table common case). */
function parseAnnotatedCsv(csv: string): InfluxPoint[] {
  const lines = csv.split("\n").filter((l) => l.length > 0 && !l.startsWith("#"));
  if (lines.length < 2) return [];
  const header = splitCsvLine(lines[0]);
  const timeIdx = header.indexOf("_time");
  const valueIdx = header.indexOf("_value");
  if (timeIdx === -1 || valueIdx === -1) return [];

  const points: InfluxPoint[] = [];
  for (let i = 1; i < lines.length; i++) {
    const cols = splitCsvLine(lines[i]);
    const time = cols[timeIdx];
    const raw = cols[valueIdx];
    if (!time || raw === undefined || raw === "") continue;
    const value = Number(raw);
    if (Number.isNaN(value)) continue;
    points.push({ time, value });
  }
  return points;
}

function splitCsvLine(line: string): string[] {
  return line.split(",").map((c) => c.trim());
}
