use crate::TableSession;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tokio::sync::RwLock;

#[derive(Clone, Debug, Default, Serialize, Deserialize)]
pub struct HotReloadSnapshot {
    pub tables: HashMap<u32, TableSession>,
    pub lobby_assignments: HashMap<u32, HashMap<String, String>>,
}

pub fn snapshot_path_from_env() -> Option<PathBuf> {
    let enabled = std::env::var("COORDINATOR_HOT_RELOAD")
        .map(|value| value == "1" || value.eq_ignore_ascii_case("true"))
        .unwrap_or(false);
    if !enabled {
        return None;
    }
    Some(
        std::env::var("COORDINATOR_HOT_RELOAD_SNAPSHOT")
            .map(PathBuf::from)
            .unwrap_or_else(|_| PathBuf::from(".tmp/coordinator-hot-reload.json")),
    )
}

pub fn load_snapshot(path: &Path) -> Option<HotReloadSnapshot> {
    match std::fs::read_to_string(path) {
        Ok(raw) => match serde_json::from_str::<HotReloadSnapshot>(&raw) {
            Ok(snapshot) => Some(snapshot),
            Err(error) => {
                tracing::warn!(
                    "Failed to parse hot-reload snapshot {}: {}",
                    path.display(),
                    error
                );
                None
            }
        },
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => None,
        Err(error) => {
            tracing::warn!(
                "Failed to read hot-reload snapshot {}: {}",
                path.display(),
                error
            );
            None
        }
    }
}

pub fn spawn_snapshot_task(
    path: PathBuf,
    tables: Arc<RwLock<HashMap<u32, TableSession>>>,
    lobby_assignments: Arc<RwLock<HashMap<u32, HashMap<String, String>>>>,
) {
    tokio::spawn(async move {
        let interval = std::env::var("COORDINATOR_HOT_RELOAD_SNAPSHOT_SECONDS")
            .ok()
            .and_then(|value| value.parse::<u64>().ok())
            .unwrap_or(2)
            .max(1);
        loop {
            if let Err(error) = write_snapshot(&path, &tables, &lobby_assignments).await {
                tracing::warn!(
                    "Failed to write hot-reload snapshot {}: {}",
                    path.display(),
                    error
                );
            }
            tokio::time::sleep(tokio::time::Duration::from_secs(interval)).await;
        }
    });
}

async fn write_snapshot(
    path: &Path,
    tables: &Arc<RwLock<HashMap<u32, TableSession>>>,
    lobby_assignments: &Arc<RwLock<HashMap<u32, HashMap<String, String>>>>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    if let Some(parent) = path.parent() {
        tokio::fs::create_dir_all(parent).await?;
    }
    let snapshot = HotReloadSnapshot {
        tables: tables.read().await.clone(),
        lobby_assignments: lobby_assignments.read().await.clone(),
    };
    let raw = serde_json::to_vec_pretty(&snapshot)?;
    let tmp = path.with_extension("json.tmp");
    tokio::fs::write(&tmp, raw).await?;
    tokio::fs::rename(tmp, path).await?;
    Ok(())
}
