// Data-layer client for the Ditto HTTP/SSE API, proxied same-origin by the
// mine-ui nginx. The browser never talks to :8080 directly and
// never sends an Authorization header - the proxy injects basic auth.
//
// Paths used (must match deploy/compose/mine-ui/nginx.conf.template):
//   GET   /ditto/api/2/search/things?namespaces=kz.kyzyltas.mine&option=size(200)
//   GET   /ditto/api/2/things?ids=a,b,c&fields=thingId,attributes,features
//   GET   /ditto/api/2/things?namespaces=kz.kyzyltas.mine&fields=thingId,features   (via EventSource)
//   PATCH /ditto/api/2/things/kz.kyzyltas.mine:scenario   (application/merge-patch+json)

import type { DittoThing, SearchThingsResponse } from "../types";
import { NAMESPACE } from "../types";

const DITTO_BASE = "/ditto/api/2";

/** Sleep helper for backoff. */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Fetch the full catalogue, paginating via `cursor` whenever a page comes
 * back full (items.length === pageSize).
 * Retries with exponential backoff on network/HTTP failure (defensive -
 * we have no live backend to test this against).
 */
export async function fetchCatalogue(
  pageSize = 200,
  onProgress?: (count: number) => void
): Promise<DittoThing[]> {
  const all: DittoThing[] = [];
  let cursor: string | undefined;
  let guard = 0;

  // eslint-disable-next-line no-constant-condition
  while (guard++ < 50) {
    const params = new URLSearchParams();
    params.set("namespaces", NAMESPACE);
    params.set("option", cursor ? `size(${pageSize}),cursor(${cursor})` : `size(${pageSize})`);

    const url = `${DITTO_BASE}/search/things?${params.toString()}`;
    const json = await fetchJsonWithRetry<SearchThingsResponse>(url);
    const items = json.items ?? [];
    all.push(...items);
    onProgress?.(all.length);

    if (items.length === pageSize && (json.cursor || json.nextPageOffset)) {
      cursor = json.cursor ?? json.nextPageOffset;
    } else {
      break;
    }
  }

  return all;
}

/** Targeted refetch of a specific set of thing ids. */
export async function fetchThingsByIds(ids: string[]): Promise<DittoThing[]> {
  if (ids.length === 0) return [];
  const params = new URLSearchParams();
  params.set("ids", ids.join(","));
  params.set("fields", "thingId,attributes,features");
  const url = `${DITTO_BASE}/things?${params.toString()}`;
  return fetchJsonWithRetry<DittoThing[]>(url);
}

async function fetchJsonWithRetry<T>(url: string, maxAttempts = 4): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    try {
      const res = await fetch(url, { headers: { Accept: "application/json" } });
      if (!res.ok) {
        throw new Error(`HTTP ${res.status} for ${url}`);
      }
      return (await res.json()) as T;
    } catch (err) {
      lastError = err;
      const backoffMs = Math.min(1000 * 2 ** attempt, 8000) + Math.random() * 250;
      await sleep(backoffMs);
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError));
}

export type LiveStatus = "connecting" | "live" | "reconnecting" | "error";

interface LiveMessage {
  thingId?: string;
  features?: DittoThing["features"];
  [key: string]: unknown;
}

/**
 * Open the live SSE feed and stream partial thing updates.
 * EventSource reconnects on its own after a drop; we layer a short
 * "reconnecting" status on top so the UI can show it, plus a manual
 * restart if the browser gives up entirely (readyState stays CLOSED).
 */
export function subscribeLive(
  onMessage: (msg: LiveMessage) => void,
  onStatus: (status: LiveStatus) => void
): () => void {
  let es: EventSource | null = null;
  let closedByUs = false;
  let watchdog: ReturnType<typeof setInterval> | null = null;
  let reconnectDelay = 1000;

  const connect = () => {
    if (closedByUs) return;
    onStatus(es ? "reconnecting" : "connecting");

    const params = new URLSearchParams();
    params.set("namespaces", NAMESPACE);
    params.set("fields", "thingId,features");
    const url = `${DITTO_BASE}/things?${params.toString()}`;

    try {
      es = new EventSource(url);
    } catch {
      onStatus("error");
      scheduleReconnect();
      return;
    }

    es.onopen = () => {
      reconnectDelay = 1000;
      onStatus("live");
    };

    es.onmessage = (ev: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(ev.data) as LiveMessage;
        onMessage(parsed);
      } catch {
        // Malformed/partial frame - ignore this one, keep the stream open.
      }
    };

    es.onerror = () => {
      onStatus("reconnecting");
      // EventSource retries internally; the watchdog below catches the
      // case where it gives up (readyState === CLOSED) and restarts us.
    };
  };

  const scheduleReconnect = () => {
    if (closedByUs) return;
    setTimeout(() => {
      reconnectDelay = Math.min(reconnectDelay * 1.7, 15000);
      connect();
    }, reconnectDelay);
  };

  connect();

  watchdog = setInterval(() => {
    if (closedByUs || !es) return;
    if (es.readyState === EventSource.CLOSED) {
      onStatus("reconnecting");
      scheduleReconnect();
    }
  }, 3000);

  return () => {
    closedByUs = true;
    if (watchdog) clearInterval(watchdog);
    es?.close();
  };
}

/**
 * PATCH the scenario control twin. Content-Type must be
 * application/merge-patch+json.
 */
export async function patchScenario(
  thingId: string,
  featuresPatch: Record<string, { properties: { value: number | string; unit?: string } }>
): Promise<void> {
  const url = `${DITTO_BASE}/things/${encodeURIComponent(thingId)}`;
  const body = JSON.stringify({ features: featuresPatch });

  let lastError: unknown;
  for (let attempt = 0; attempt < 3; attempt++) {
    try {
      const res = await fetch(url, {
        method: "PATCH",
        headers: { "Content-Type": "application/merge-patch+json" },
        body
      });
      if (!res.ok) {
        throw new Error(`PATCH ${thingId} failed: HTTP ${res.status}`);
      }
      return;
    } catch (err) {
      lastError = err;
      await sleep(500 * (attempt + 1));
    }
  }
  throw lastError instanceof Error ? lastError : new Error(String(lastError));
}
