// Vo Tauri: chay backend Python lam sidecar roi mo cua so vao web UI cua no.
// CHUA TUNG BIEN DICH (may nay khong co Rust) - xem README.md.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command};
use std::sync::Mutex;

struct Sidecar(Mutex<Option<Child>>);

fn spawn_backend() -> Option<Child> {
    Command::new("binaries/MangaLocalLibrary.exe")
        .arg("serve")
        .spawn()
        .ok()
}

fn main() {
    let sidecar = Sidecar(Mutex::new(spawn_backend()));

    tauri::Builder::default()
        .manage(sidecar)
        .on_window_event(|window, event| {
            if let tauri::WindowEvent::Destroyed = event {
                let state: tauri::State<Sidecar> = window.state();
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(child) = guard.as_mut() {
                        let _ = child.kill();
                    }
                }
            }
        })
        .run(tauri::generate_context!())
        .expect("khong chay duoc vo Tauri");
}
