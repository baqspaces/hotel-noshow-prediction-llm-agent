#!/usr/bin/env bash
set -e

uvicorn src.main:app --host 127.0.0.1 --port 8000
