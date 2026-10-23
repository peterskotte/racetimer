#!/bin/sh
# Lokal udvikling på Mac (Homebrew-Python mangler expat-linkning, derfor DYLD)
cd "$(dirname "$0")"
export DYLD_LIBRARY_PATH=/opt/homebrew/opt/expat/lib PYTHONPATH=.deps
exec /opt/homebrew/bin/python3.12 -m uvicorn racetimer.app:app --host 127.0.0.1 --port 8000
