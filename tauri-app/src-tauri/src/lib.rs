mod commands;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_store::Builder::default().build())
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_fs::init())
        .invoke_handler(tauri::generate_handler![
            commands::auth::get_auth_token,
            commands::auth::set_auth_token,
            commands::auth::migrate_tokens_to_keychain,
            commands::workspace::get_projects_dir,
            commands::workspace::set_projects_dir,
            commands::workspace::open_folder_dialog,
            commands::workspace::link_repo,
            commands::workspace::list_projects,
            commands::git::git_clone,
            commands::git::cancel_clone,
            commands::git::set_git_credentials,
            commands::git::get_git_credentials,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
