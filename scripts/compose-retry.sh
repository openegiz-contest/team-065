#!/usr/bin/env bash
#
# Run a command up to 3 times. Used for `docker compose up --build`, whose
# image pulls and base-image lookups on Docker Hub fail now and then with
# transient network errors (EOF, timeouts, rate limits). Compose resumes
# where it stopped, so a retry is safe.
#
set -uo pipefail

attempts=3
for i in $(seq 1 "$attempts"); do
  "$@" && exit 0
  status=$?
  if [ "$i" -lt "$attempts" ]; then
    echo "Attempt $i of $attempts failed (exit $status); retrying in 20 s..." >&2
    sleep 20
  fi
done
echo "Failed after $attempts attempts." >&2
exit "$status"
