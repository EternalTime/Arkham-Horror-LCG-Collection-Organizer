// AHLCG Collection Organizer - native shell.
//
// Serves the collection folder (index.html + data + images) over
// 127.0.0.1:17845 to the app window, so nothing is bundled into the binary.
// Also exposes save_state/load_state commands: the page mirrors its
// localStorage state to <collection>/decks/autosave.json on every change.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::fs;
use std::path::{Path, PathBuf};

const PORT: u16 = 17845;

/// The collection folder: $AHLCG_DIR if set, else ~/Documents/AHLCG.
fn collection_dir() -> PathBuf {
    if let Ok(d) = std::env::var("AHLCG_DIR") {
        return PathBuf::from(d);
    }
    dirs::home_dir()
        .expect("no home directory")
        .join("Documents")
        .join("AHLCG")
}

fn mime(path: &Path) -> &'static str {
    match path.extension().and_then(|e| e.to_str()).unwrap_or("") {
        "html" => "text/html; charset=utf-8",
        "js" => "text/javascript; charset=utf-8",
        "css" => "text/css; charset=utf-8",
        "json" => "application/json; charset=utf-8",
        "svg" => "image/svg+xml",
        "avif" => "image/avif",
        "webp" => "image/webp",
        "png" => "image/png",
        "jpg" | "jpeg" => "image/jpeg",
        "gif" => "image/gif",
        "ico" => "image/x-icon",
        "pdf" => "application/pdf",
        "woff2" => "font/woff2",
        "woff" => "font/woff",
        "ttf" => "font/ttf",
        "otf" => "font/otf",
        "txt" | "md" => "text/plain; charset=utf-8",
        _ => "application/octet-stream",
    }
}

/// Minimal percent-decoding (enough for spaces & friends in file names).
fn percent_decode(s: &str) -> String {
    let bytes = s.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'%' {
            if let (Some(h), Some(l)) = (
                bytes.get(i + 1).and_then(|c| (*c as char).to_digit(16)),
                bytes.get(i + 2).and_then(|c| (*c as char).to_digit(16)),
            ) {
                out.push((h * 16 + l) as u8);
                i += 3;
                continue;
            }
        }
        out.push(bytes[i]);
        i += 1;
    }
    String::from_utf8_lossy(&out).into_owned()
}

fn serve(dir: PathBuf, handle: tauri::AppHandle) {
    use tauri::Manager;
    let server = tiny_http::Server::http(("127.0.0.1", PORT))
        .expect("could not bind 127.0.0.1:17845 (is another copy running?)");
    let root = dir.canonicalize().expect("collection folder not found");
    for mut request in server.incoming_requests() {
        let url = request
            .url()
            .split(['?', '#'])
            .next()
            .unwrap_or("/")
            .to_string();
        // native marker: lets the page know autosave is available
        if url == "/__native" {
            let _ = request.respond(tiny_http::Response::from_string("ahlcg"));
            continue;
        }
        // raw URL keeps the query string (`url` above has it stripped)
        let raw = request.url().to_string();
        // set the native window background color (title bar) to #RRGGBB
        if let Some(q) = raw.strip_prefix("/__winbg?c=") {
            let hex = percent_decode(q);
            let hex = hex.trim_start_matches('#');
            let ok = u32::from_str_radix(hex, 16)
                .ok()
                .filter(|_| hex.len() == 6)
                .and_then(|v| {
                    let color = tauri::window::Color(
                        (v >> 16) as u8, (v >> 8) as u8, v as u8, 255);
                    handle
                        .get_webview_window("main")
                        .map(|w| w.set_background_color(Some(color)).is_ok())
                })
                .unwrap_or(false);
            let _ = request.respond(
                tiny_http::Response::from_string("").with_status_code(if ok { 204 } else { 400 }),
            );
            continue;
        }
        // open a file (inside the collection) or an http(s) URL with the system default app
        if let Some(q) = raw.strip_prefix("/__open?") {
            let ok = if let Some(rel) = q.strip_prefix("f=") {
                let p = root.join(percent_decode(rel));
                p.canonicalize().map(|p| p.starts_with(&root)).unwrap_or(false)
                    && std::process::Command::new("open").arg(&p).spawn().is_ok()
            } else if let Some(u) = q.strip_prefix("u=") {
                let u = percent_decode(u);
                (u.starts_with("https://") || u.starts_with("http://"))
                    && std::process::Command::new("open").arg(&u).spawn().is_ok()
            } else {
                false
            };
            let _ = request.respond(
                tiny_http::Response::from_string("").with_status_code(if ok { 204 } else { 400 }),
            );
            continue;
        }
        // autosave endpoint: page POSTs its full state on every change
        if url == "/__autosave" && request.method() == &tiny_http::Method::Post {
            let mut body = String::new();
            use std::io::Read;
            let status = if request.as_reader().read_to_string(&mut body).is_ok()
                && save_autosave(&body).is_ok()
            {
                204
            } else {
                500
            };
            let _ = request.respond(
                tiny_http::Response::from_string("").with_status_code(status),
            );
            continue;
        }
        let url = url.as_str();
        let mut rel = percent_decode(url.trim_start_matches('/'));
        if rel.is_empty() {
            rel = "index.html".into();
        }
        let path = root.join(&rel);
        // refuse anything that escapes the collection folder
        let ok = path
            .canonicalize()
            .map(|p| p.starts_with(&root))
            .unwrap_or(false);
        let response = if ok {
            match fs::read(&path) {
                Ok(data) => {
                    let ct = tiny_http::Header::from_bytes(
                        &b"Content-Type"[..],
                        mime(&path).as_bytes(),
                    )
                    .unwrap();
                    tiny_http::Response::from_data(data).with_header(ct)
                }
                Err(_) => tiny_http::Response::from_string("404").with_status_code(404),
            }
        } else {
            tiny_http::Response::from_string("403").with_status_code(403)
        };
        let _ = request.respond(response);
    }
}

fn save_autosave(data: &str) -> std::io::Result<()> {
    let p = collection_dir().join("decks").join("autosave.json");
    if let Some(parent) = p.parent() {
        fs::create_dir_all(parent)?;
    }
    // write-then-rename so a crash mid-write never corrupts the backup
    let tmp = p.with_extension("json.tmp");
    fs::write(&tmp, data)?;
    fs::rename(&tmp, &p)
}

fn main() {
    let dir = collection_dir();
    if !dir.join("index.html").exists() {
        eprintln!(
            "index.html not found in {} - set AHLCG_DIR to your collection folder",
            dir.display()
        );
    }
    tauri::Builder::default()
        .setup(move |app| {
            let handle = app.handle().clone();
            std::thread::spawn(move || serve(dir, handle));
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
