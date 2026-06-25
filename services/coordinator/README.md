# MPC Coordinator Service

This service orchestrates the MPC committee for game proving and card shuffling.

## Hot Reload

Install `cargo-watch` once:

```bash
cargo install cargo-watch
```

Run the coordinator with Rust hot reload from the repository root:

```bash
./scripts/dev-coordinator-watch.sh
```

The watcher recompiles and restarts `cargo run -p coordinator` when coordinator
Rust sources, migrations, or Cargo manifests change. During hot reload the
coordinator writes table sessions and lobby assignments to
`.tmp/coordinator-hot-reload.json` every few seconds and restores that snapshot
on restart. Persistent chain state is still rehydrated from Soroban when a
session is missing from memory.

## API Endpoints

### GET `/api/health`

Returns the operational metrics and connectivity status of the coordinator, MPC nodes, and Soroban RPC network.

#### Sample Response

```json
{
  "uptime_seconds": 1284,
  "mpc_nodes": [
    {
      "endpoint": "http://localhost:8101",
      "connected": true,
      "last_heartbeat": "2026-06-23T16:32:00.123Z"
    },
    {
      "endpoint": "http://localhost:8102",
      "connected": true,
      "last_heartbeat": "2026-06-23T16:32:00.456Z"
    },
    {
      "endpoint": "http://localhost:8103",
      "connected": true,
      "last_heartbeat": "2026-06-23T16:32:00.789Z"
    }
  ],
  "soroban_rpc": {
    "endpoint": "http://localhost:8000/soroban/rpc",
    "status": "connected"
  },
  "active_mpc_sessions": 0,
  "request_metrics": {
    "POST /api/tables/create": {
      "count": 3,
      "errors": 0,
      "latency_histogram": {
        "under_50ms": 0,
        "under_250ms": 2,
        "under_1000ms": 1,
        "under_5000ms": 0,
        "over_5000ms": 0
      }
    }
  }
}
```
