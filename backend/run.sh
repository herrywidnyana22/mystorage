#!/bin/bash
uvicorn app.main:app --reload --host ${HOST:-0.0.0.0} --port ${PORT:-8000}
