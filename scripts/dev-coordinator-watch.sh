#!/usr/bin/env bash
# Hot-reload the coordinator during local Rust development.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v cargo-watch >/dev/null 2>&1 && ! cargo watch --version >/dev/null 2>&1; then
    echo "cargo-watch is required. Install it with: cargo install cargo-watch" >&2
    exit 1
fi

export COORDINATOR_HOT_RELOAD="${COORDINATOR_HOT_RELOAD:-1}"
export COORDINATOR_HOT_RELOAD_SNAPSHOT="${COORDINATOR_HOT_RELOAD_SNAPSHOT:-.tmp/coordinator-hot-reload.json}"
export BIND_ADDR="${BIND_ADDR:-127.0.0.1:8080}"
export CIRCUIT_DIR="${CIRCUIT_DIR:-./circuits}"

cargo watch \
    --why \
    --watch services/coordinator/src \
    --watch services/coordinator/migrations \
    --watch services/coordinator/Cargo.toml \
    --watch Cargo.toml \
    --ignore .tmp \
    --ignore target \
    --exec "run -p coordinator"
