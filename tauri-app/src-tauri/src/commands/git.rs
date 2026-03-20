// Placeholder — will be replaced in Task 2
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

const KEYCHAIN_SERVICE: &str = "io.pilotspace.app";
const KEYCHAIN_GIT_ACCOUNT: &str = "git_pat";

#[derive(serde::Serialize, Clone)]
pub struct GitProgress {
    pub pct: u32,
    pub message: String,
}

#[derive(serde::Serialize, Clone)]
pub struct GitCredentialInfo {
    pub username: String,
    pub has_pat: bool,
}

static CLONE_CANCEL: std::sync::OnceLock<Arc<AtomicBool>> = std::sync::OnceLock::new();

fn get_cancel_flag() -> Arc<AtomicBool> {
    CLONE_CANCEL
        .get_or_init(|| Arc::new(AtomicBool::new(false)))
        .clone()
}

#[tauri::command]
pub async fn git_clone(
    _app: tauri::AppHandle,
    _url: String,
    _target_dir: String,
    _on_progress: tauri::ipc::Channel<GitProgress>,
) -> Result<(), String> {
    Err("Not yet implemented".to_string())
}

#[tauri::command]
pub fn cancel_clone() -> Result<(), String> {
    get_cancel_flag().store(true, Ordering::Relaxed);
    Ok(())
}

#[tauri::command]
pub async fn set_git_credentials(
    _username: String,
    _pat: String,
) -> Result<(), String> {
    Err("Not yet implemented".to_string())
}

#[tauri::command]
pub async fn get_git_credentials() -> Result<Option<GitCredentialInfo>, String> {
    Ok(None)
}
