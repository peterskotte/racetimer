#!/bin/sh
# Lokal test af spejlserveren (som på en webserver) – egen database, port 8001
cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib PYTHONPATH=.deps
export RACETIMER_MODE=mirror RACETIMER_DB=data-mirror/racetimer.db RACETIMER_MIRROR_KEY=dev-noegle-123
exec /opt/homebrew/bin/python3.12 -m uvicorn racetimer.app:app --host 127.0.0.1 --port 8001
