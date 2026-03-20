mod commands;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .manage(commands::terminal::TerminalSessions::new())
        .manage(commands::sidecar::SidecarProcesses::new())
        .setup(|app| {
            commands::tray::setup_tray(app.handle())?;
            commands::tray::setup_close_to_tray(app.handle());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::auth::get_auth_token,
            commands::auth::set_auth_token,
            commands::auth::migrate_tokens_to_keychain,
            commands::workspace::get_projects_dir,
            commands::workspace::set_projects_dir,
            commands::workspace::reset_projects_dir,
            commands::workspace::open_folder_dialog,
            commands::workspace::link_repo,
            commands::workspace::list_projects,
            commands::git::git_clone,
            commands::git::cancel_clone,
            commands::git::set_git_credentials,
            commands::git::get_git_credentials,
            commands::git::git_pull,
            commands::git::git_push,
            commands::git::git_status,
            commands::git::git_branch_list,
            commands::git::git_branch_create,
            commands::git::git_branch_switch,
            commands::git::git_branch_delete,
            commands::git::git_diff,
            commands::git::git_stage,
            commands::git::git_unstage,
            commands::git::git_commit,
            commands::terminal::create_terminal,
            commands::terminal::write_terminal,
            commands::terminal::resize_terminal,
            commands::terminal::close_terminal,
            commands::sidecar::run_sidecar,
            commands::sidecar::cancel_sidecar,
            commands::tray::send_notification,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
