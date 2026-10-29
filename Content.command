#!/bin/bash
# Double-click to open Content. Starts the local server if it is not running.
cd "$(dirname "$0")"
if ! curl -s -o /dev/null http://127.0.0.1:8769/; then
  nohup .venv/bin/python content_sunucu.py > content.log 2>&1 &
  for i in $(seq 1 30); do sleep 0.5; curl -s -o /dev/null http://127.0.0.1:8769/ && break; done
fi
open http://127.0.0.1:8769/
