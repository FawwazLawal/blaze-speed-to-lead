#!/usr/bin/env bash
# Fire the fabricated lead at the running webhook.
# Usage: ./send_test_lead.sh    (server must already be running on :8000)
set -euo pipefail

curl -s -X POST http://127.0.0.1:8000/webhook/lead \
  -H 'Content-Type: application/json' \
  -d @sample_lead.json | python3 -m json.tool
