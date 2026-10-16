"""
Ditto-protocol MQTT I/O: envelope builders, a rate-limited publisher, and a resilient MQTT
connection (connect/retry/backoff, scenario-twin subscription with echo suppression).

Exact merge envelope, a rate budget of about 20-30 commands/s (batched per twin),
item 5 (subscribe to opentwins/twin/events/<ns>/scenario, ignore no-op echoes), item 6 (idle-safe:
never crash on a single publish failure, retry MQTT with backoff).
Topics and envelope shapes follow the OpenEgiz Ditto connections (deploy/compose/init/).
"""
from __future__ import annotations

import json
import logging
import random
import threading
import time
from collections import deque
from typing import Callable, Optional

import paho.mqtt.client as mqtt

from roster import NAMESPACE

logger = logging.getLogger("engine.ditto_io")

SCENARIO_EVENT_TOPIC = f"opentwins/twin/events/{NAMESPACE}/scenario"
TELEMETRY_TOPIC_PREFIX = "telemetry/"


def feature(value, unit: str = "") -> dict:
    """One Ditto feature value: {"properties": {"value": v, "unit": u}}."""
    return {"properties": {"value": value, "unit": unit}}


def merge_envelope(name: str, features: dict) -> dict:
    """
    Exact Ditto-protocol merge command:
      {"topic": "<ns>/<name>/things/twin/commands/merge",
       "headers": {"content-type": "application/merge-patch+json", "response-required": false},
       "path": "/features",
       "value": {...}}
    """
    return {
        "topic": f"{NAMESPACE}/{name}/things/twin/commands/merge",
        "headers": {"content-type": "application/merge-patch+json", "response-required": False},
        "path": "/features",
        "value": features,
    }


class RateLimitedPublisher:
    """
    Coalescing, rate-limited sender. Multiple enqueue() calls for the same twin before it is
    sent are merged into one Ditto merge command ("batch multiple features of
    one twin into one merge call"). A single background thread drains the queue at <= rate_hz
    commands/sec, satisfying the ~20-30 cmd/s total budget across ALL twins.
    """

    def __init__(self, client: "mqtt.Client", rate_hz: float = 24.0):
        self.client = client
        self.min_interval = 1.0 / max(rate_hz, 1.0)
        self._pending: dict[str, dict] = {}
        self._order: deque[str] = deque()
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="ditto-publisher", daemon=True)
        self.sent_count = 0
        self.drop_count = 0

    def enqueue(self, name: str, features: dict) -> None:
        if not features:
            return
        with self._lock:
            if name not in self._pending:
                self._order.append(name)
                self._pending[name] = {}
            self._pending[name].update(features)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def current_rate_estimate(self) -> float:
        return 1.0 / self.min_interval

    def _run(self) -> None:
        while not self._stop.is_set():
            t0 = time.monotonic()
            name = None
            feats = None
            with self._lock:
                if self._order:
                    name = self._order.popleft()
                    feats = self._pending.pop(name, None)
            if name is not None and feats:
                try:
                    envelope = merge_envelope(name, feats)
                    self.client.publish(TELEMETRY_TOPIC_PREFIX + name, json.dumps(envelope), qos=0)
                    self.sent_count += 1
                except Exception:
                    # Idle-safe: never crash on a single publish failure.
                    self.drop_count += 1
                    logger.warning("publish failed for twin %s (dropped, continuing)", name, exc_info=True)
            elapsed = time.monotonic() - t0
            remaining = self.min_interval - elapsed
            if remaining > 0:
                time.sleep(remaining)
            elif name is None:
                time.sleep(0.01)


class DittoConnection:
    """
    paho-mqtt 2.x client wrapper: connect-with-retry/backoff, auto-resubscribe, and dispatch of
    scenario-twin events to a callback, with echo suppression (a scenario merge the engine itself
    triggers re-publishes to the same topic; we only act on events whose feature values actually
    differ from our last-applied state).
    """

    def __init__(self, host: str, port: int, on_scenario_event: Callable[[dict], None],
                 client_id: str = "mine-engine", publish_rate_hz: float = 24.0):
        self.host = host
        self.port = port
        self.on_scenario_event = on_scenario_event
        self._connected = threading.Event()
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=client_id)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.publisher = RateLimitedPublisher(self.client, rate_hz=publish_rate_hz)
        self._stop = threading.Event()
        self._connect_thread = threading.Thread(target=self._connect_loop, name="mqtt-connect", daemon=True)

    # -- connection lifecycle -------------------------------------------------
    def start(self) -> None:
        self.publisher.start()
        self.client.loop_start()
        self._connect_thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.publisher.stop()
        try:
            self.client.disconnect()
        except Exception:
            pass
        self.client.loop_stop()

    def wait_connected(self, timeout: float = 30.0) -> bool:
        return self._connected.wait(timeout)

    def _connect_loop(self) -> None:
        backoff = 1.0
        max_backoff = 30.0
        while not self._stop.is_set():
            if self._connected.is_set():
                time.sleep(1.0)
                continue
            try:
                logger.info("connecting to mqtt %s:%s", self.host, self.port)
                self.client.connect(self.host, self.port, keepalive=30)
                backoff = 1.0
                # connect() is non-blocking with loop_start already running; wait briefly
                time.sleep(0.5)
            except Exception:
                logger.warning("mqtt connect failed, retrying in %.1fs", backoff, exc_info=True)
                time.sleep(backoff + random.uniform(0, 0.5))
                backoff = min(backoff * 2.0, max_backoff)

    # -- paho callbacks (v2 API signatures) ----------------------------------
    def _on_connect(self, client, userdata, flags, reason_code, properties=None) -> None:
        ok = (reason_code == 0) or (hasattr(reason_code, "is_failure") and not reason_code.is_failure)
        if ok:
            logger.info("mqtt connected")
            self._connected.set()
            try:
                client.subscribe(SCENARIO_EVENT_TOPIC, qos=0)
            except Exception:
                logger.warning("scenario subscribe failed", exc_info=True)
        else:
            logger.warning("mqtt connect rejected: %s", reason_code)

    def _on_disconnect(self, client, userdata, flags, reason_code=None, properties=None) -> None:
        logger.warning("mqtt disconnected (reason=%s); will retry", reason_code)
        self._connected.clear()

    def _on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except Exception:
            logger.warning("bad scenario event payload, ignoring", exc_info=True)
            return
        try:
            self.on_scenario_event(payload)
        except Exception:
            # Never let a malformed/unexpected scenario event crash the engine.
            logger.warning("on_scenario_event handler raised, ignoring event", exc_info=True)
