#!/usr/bin/env python3
"""Idempotent bootstrap of the Kyzyl-Tas mine twin catalogue into Eclipse Ditto.

For every entry in model.json (type twins first, then instance twins, parents
before children), this does:

    PUT /api/2/things/<thingId>   (HTTP Basic auth, DITTO_USER / DITTO_PASSWORD)

against DITTO_URL. A PUT is idempotent: re-running this script against an
already-populated Ditto just re-asserts the same state (Ditto returns 201 on
first create, 204/200 on update - both count as success).

On a fresh machine the Ditto cluster can take several minutes to become ready after
`make up` (JVM cluster formation, Mongo connection, 503/408 while the gateway
warms up).
This script therefore:
  1. Polls a lightweight Ditto endpoint until it answers successfully, up to
     READY_TIMEOUT_S (default 600 s / 10 min).
  2. PUTs each twin with its own bounded retry loop, tolerating connection
     refused / 503 / 408 / 5xx as transient.
  3. Re-GETs every twin at the end to confirm it is actually persisted.

Exit code is 0 only if every twin's PUT succeeded AND every twin's final GET
confirmed it exists. Any other outcome exits 1 (non-zero), so this script is
safe to use as a Compose one-shot job gate (`depends_on: ... service_completed_successfully`).

Stdlib only (urllib.request) - no pip install needed, so the Docker build has
no network dependency beyond the base image.
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

DITTO_URL = os.environ.get("DITTO_URL", "http://localhost:8080").rstrip("/")
DITTO_USER = os.environ.get("DITTO_USER", "ditto")
DITTO_PASSWORD = os.environ["DITTO_PASSWORD"]  # required, never defaulted/hardcoded

MODEL_FILE = os.environ.get(
    "MODEL_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.json")
)

# Tunables (env-overridable for local testing against a cold Ditto).
READY_TIMEOUT_S = int(os.environ.get("READY_TIMEOUT_S", "600"))
READY_POLL_INTERVAL_S = float(os.environ.get("READY_POLL_INTERVAL_S", "5"))
PUT_MAX_ATTEMPTS = int(os.environ.get("PUT_MAX_ATTEMPTS", "20"))
PUT_RETRY_INTERVAL_S = float(os.environ.get("PUT_RETRY_INTERVAL_S", "5"))
VERIFY_MAX_ATTEMPTS = int(os.environ.get("VERIFY_MAX_ATTEMPTS", "12"))
VERIFY_RETRY_INTERVAL_S = float(os.environ.get("VERIFY_RETRY_INTERVAL_S", "5"))

AUTH_HEADER = "Basic " + base64.b64encode(f"{DITTO_USER}:{DITTO_PASSWORD}".encode()).decode()

# Status codes worth retrying: connection not up yet, or Ditto still warming up.
RETRYABLE_HTTP_STATUS = {408, 500, 502, 503, 504}


def _request(method, path, body=None, timeout=15):
    url = f"{DITTO_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": AUTH_HEADER,
            "Content-Type": "application/json",
        },
    )
    return urllib.request.urlopen(req, timeout=timeout)


def wait_until_ready():
    """Poll Ditto until a simple authenticated GET succeeds, or give up."""
    deadline = time.monotonic() + READY_TIMEOUT_S
    attempt = 0
    while True:
        attempt += 1
        try:
            with _request("GET", "/api/2/search/things?option=size(1)", timeout=10) as resp:
                if 200 <= resp.status < 300:
                    print(f"ditto ready after {attempt} check(s)")
                    return True
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_STATUS:
                # Ditto is up and answering (e.g. 401 would mean wrong creds) -
                # treat as ready; let the real PUT calls surface the real error.
                print(f"ditto answering (HTTP {exc.code}), proceeding")
                return True
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            pass  # not up yet (connection refused / reset / DNS not resolvable yet)

        if time.monotonic() >= deadline:
            print(f"FAILED: ditto not ready after {READY_TIMEOUT_S}s", file=sys.stderr)
            return False
        time.sleep(READY_POLL_INTERVAL_S)


def put_thing(thing_id, body):
    """PUT one thing with bounded retry on transient failures. Returns True/False."""
    for attempt in range(1, PUT_MAX_ATTEMPTS + 1):
        try:
            with _request("PUT", f"/api/2/things/{thing_id}", body=body, timeout=30) as resp:
                status = resp.status
                verb = "created" if status == 201 else "updated"
                print(f"{verb:8s} {thing_id} (HTTP {status})")
                return True
        except urllib.error.HTTPError as exc:
            if exc.code in RETRYABLE_HTTP_STATUS:
                print(f"retry    {thing_id}: HTTP {exc.code} (attempt {attempt}/{PUT_MAX_ATTEMPTS})")
            else:
                # Non-retryable (400 bad request, 401/403 auth, 404, ...): fail fast.
                detail = exc.read().decode(errors="replace") if hasattr(exc, "read") else ""
                print(f"FAILED   {thing_id}: HTTP {exc.code} {exc.reason} {detail}", file=sys.stderr)
                return False
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
            print(f"retry    {thing_id}: {exc} (attempt {attempt}/{PUT_MAX_ATTEMPTS})")
        if attempt < PUT_MAX_ATTEMPTS:
            time.sleep(PUT_RETRY_INTERVAL_S)
    print(f"FAILED   {thing_id}: exhausted {PUT_MAX_ATTEMPTS} attempts", file=sys.stderr)
    return False


def verify_thing(thing_id):
    """Re-GET one thing with bounded retry; returns True once confirmed present."""
    for attempt in range(1, VERIFY_MAX_ATTEMPTS + 1):
        try:
            with _request("GET", f"/api/2/things/{thing_id}", timeout=15) as resp:
                if 200 <= resp.status < 300:
                    return True
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_STATUS:
                print(f"FAILED   verify {thing_id}: HTTP {exc.code}", file=sys.stderr)
                return False
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
            pass
        if attempt < VERIFY_MAX_ATTEMPTS:
            time.sleep(VERIFY_RETRY_INTERVAL_S)
    print(f"FAILED   verify {thing_id}: not confirmed after {VERIFY_MAX_ATTEMPTS} attempts", file=sys.stderr)
    return False


def main():
    with open(MODEL_FILE, encoding="utf-8") as f:
        twins = json.load(f)

    if not isinstance(twins, list):
        print("FAILED: model.json must be a flat JSON array of thing objects", file=sys.stderr)
        return 1

    print(f"loaded {len(twins)} twin definitions from {MODEL_FILE}")

    if not wait_until_ready():
        return 1

    # Phase 1: PUT every twin, in file order (types first, then parents before
    # children). A single failure here is fatal - later twins may reference
    # earlier ones via _parents, so exit 0 only on full success.
    failed = []
    for twin in twins:
        thing_id = twin["thingId"]
        if not put_thing(thing_id, twin):
            failed.append(thing_id)

    if failed:
        print(f"FAILED: {len(failed)} twin(s) could not be created/updated: {failed}", file=sys.stderr)
        return 1

    # Phase 2: verify every twin is actually readable back from Ditto before
    # declaring success (PUT 2xx plus a confirming GET).
    unverified = []
    for twin in twins:
        thing_id = twin["thingId"]
        if not verify_thing(thing_id):
            unverified.append(thing_id)

    if unverified:
        print(f"FAILED: {len(unverified)} twin(s) could not be verified: {unverified}", file=sys.stderr)
        return 1

    print(f"OK: all {len(twins)} twins created and verified in {DITTO_URL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
