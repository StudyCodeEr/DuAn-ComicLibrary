# Vỏ Tauri (chưa build được trên máy này)

Thư mục này là scaffold sẵn sàng, **chưa từng được biên dịch**: máy hiện tại không
có Rust toolchain (`cargo` và `rustup` đều không tồn tại). Tôi không tự cài vì nó
kéo theo khoảng 1–2 GB gồm cả MSVC build tools.

Vỏ desktop đang dùng thay thế là `mangalib app`: khay hệ thống bằng pystray cộng
cửa sổ Edge `--app=` — không thêm dependency nào và chạy được ngay hôm nay.

## Khi nào nên build cái này

Khi bạn muốn một file `.exe` desktop thật sự với icon riêng và không phụ thuộc
Edge. Nó **không** thêm tính năng nào: cùng web UI, cùng server.

## Cần gì

```powershell
winget install Rustlang.Rustup
rustup default stable-msvc
cargo install tauri-cli
```

## Build

```powershell
# 1. Đóng gói backend Python trước (tạo dist/ComicLibrary/)
pyinstaller tools/mangalib.spec --noconfirm

# 2. Build vỏ
cd shell-tauri
cargo tauri build
```

## Những gì chưa được kiểm chứng

Vì chưa biên dịch lần nào, hãy coi các file ở đây là **bản nháp đã viết đúng
hình dạng**, không phải bản đã chạy:

- đường dẫn sidecar trong `tauri.conf.json` phải khớp tên file PyInstaller tạo ra;
- `main.rs` kill sidecar khi cửa sổ đóng — cần kiểm lại trên Windows thật;
- cổng 8000 đang hardcode ở cả hai phía.
