<div align="center">

# Comic Library

**Tải truyện tranh về máy, quản lý thư viện cục bộ, và đọc trên cả PC lẫn điện thoại — từ một server chạy ngay trên máy bạn.**

![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/DB-SQLite-003B57?logo=sqlite&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)

</div>

---

## Dự án này là gì

Một ứng dụng cá nhân, chạy hoàn toàn trên máy bạn:

- **Tải truyện** từ một link. Metadata (tên truyện, tác giả, thể loại, bìa, danh sách chương) lấy bằng HTTP thuần. Browser chỉ được mở ở đúng một bước — phân giải danh sách URL ảnh của từng chương — rồi đóng ngay; ảnh được tải song song bằng HTTP nên nhận **file gốc, không re-encode**.
- **Thư viện** có tag ba trạng thái (bắt buộc có / loại trừ / bỏ qua), tác giả và họa sĩ riêng, tìm kiếm khớp cả tên truyện lẫn tên tác giả **không dấu cũng ra**.
- **Đọc** trên trình duyệt: PC và điện thoại dùng **cùng một UI**, và **vị trí đọc đồng bộ** giữa hai thiết bị.
- **Không dịch vụ bên ngoài**, không tài khoản, không đồng bộ ra Internet. Mất mạng vẫn đọc bình thường.

## Chạy thử

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"

mangalib app            # server + khay hệ thống + cửa sổ app
mangalib serve          # chỉ server, mở http://127.0.0.1:8000 bằng trình duyệt
```

Các lệnh khác:

| Lệnh | Việc |
|---|---|
| `mangalib probe <url>` | Thử lấy metadata của một link, **không mở browser**. Chạy cái này trước khi nghi code sai |
| `mangalib download <url>` | Tải truyện. `--dry-run` chỉ in metadata, `--limit N` giới hạn số chương, `--headful` hiện cửa sổ browser |
| `mangalib scan` | Dựng lại DB từ thư viện trên đĩa. `--prune` bỏ truyện không còn thư mục, `--reset` dời DB cũ sang một bên |
| `mangalib doctor-paths` | In mọi đường dẫn đang dùng. Hữu ích khi nghi app ghi sai chỗ |
| `mangalib app --autostart on\|off\|status` | Tự khởi động cùng Windows ở chế độ ẩn |

## Đọc trên điện thoại

Mở tab **Cài đặt** trên máy chủ, quét mã QR bằng điện thoại. Một lần là xong: điện thoại được đặt cookie và dùng mãi. Máy chủ không cần token; thiết bị khác trong LAN thì cần.

## Kiến trúc

Mỗi file một trách nhiệm, không file nào vượt ~260 dòng.

```
src/mangalib/
├─ paths.py        ⭐ NGUỒN CHÂN LÝ DUY NHẤT của mọi đường dẫn
├─ naming.py          tên file, slug, số chương, tên người (hàm thuần)
├─ config.py          data/config.toml
├─ errors.py          cây lỗi có ngữ cảnh
├─ cli.py             probe · download · scan · serve · app · doctor-paths
├─ db/                engine (WAL + lock ghi) · models · schema.sql · 8 repo
├─ meta/              tầng HTTP: client (curl_cffi) · parse · rules (YAML) · generic
├─ pagegrab/          tầng browser: CHỈ phân giải URL ảnh, rồi đóng ngay
├─ download/          fetcher (song song, ghi nguyên tử) · images · pipeline
├─ library/           metadata.json của mỗi truyện · scanner
├─ jobs/              hàng đợi một worker · bus sự kiện cho SSE
├─ api/               FastAPI: library · jobs+SSE · settings · discovery
├─ web/               UI: HTML + CSS + ES module thuần, KHÔNG build step
└─ shell/             khay hệ thống · cửa sổ Edge --app · autostart
```

### Tám quy tắc biên giới

Đây là nội dung thật của bản đại tu, không phải lời khuyên chung:

1. **Chỉ `paths.py` được tính đường dẫn.** Bản cũ có năm định nghĩa "thư mục gốc" xung đột, một cái lệch hẳn một cấp.
2. **Module không được làm I/O lúc import.** Bản cũ gọi `os.makedirs("logs")` ở module scope với đường dẫn tương đối, nên tự khởi động cùng Windows (cwd = `C:\Windows\System32`) làm app chết **ngay lúc import**.
3. **Không connection DB sống lâu; mọi lần ghi qua một lock.** Bản cũ dùng một connection với `check_same_thread=False` từ ba luồng, không lock nào.
4. **Không nuốt lỗi.** `ruff` bật `E722` + `BLE001` nên quy tắc này do máy kiểm, không phải lời hứa. Bản cũ có 27 chỗ `except:` trần.
5. **DB lưu `slug`, không lưu đường dẫn tuyệt đối.** Di chuyển cả thư viện sang ổ khác chỉ cần đổi `data_root`.
6. **Mỗi thư mục truyện tự mô tả được** (`metadata.json`) → mất DB không mất dữ liệu, kể cả tag và tác giả bạn sửa tay.
7. **Rule của site thật không vào repo** — nằm ở `data/sites/*.yml` (gitignored).
8. **Chỉ `pagegrab/` được chạm browser, và import lười** → mở app để *đọc* truyện không bao giờ nạp Playwright.

### Một thiết kế đáng nói

`expected_page_count` của một chương lấy từ **số trang mà reader của site tự khai báo**, không phải số ảnh ta lấy được. Nhờ vậy một lần cuộn chưa đủ sẽ ghi `partial` và lần sau tự vá — thay vì báo `complete` sai. Bản cũ báo `"✅ Xong: N ảnh"` với N là số URL tìm thấy, nên một chương trắng vẫn báo thành công.

## Thêm một nguồn truyện

Thêm một file `.yml` vào `data/sites/`, **không sửa code**. Mẫu: `src/mangalib/sites/example.yml`. Mọi selector, nhãn, bộ lọc và danh sách domain đều là dữ liệu, nên web đổi giao diện thì sửa file cấu hình.

Khi một site chặn truy cập tự động: cài userscript ở tab **Cài đặt**, mở chương trên trình duyệt của chính bạn rồi bấm nút nổi — trang đã render sẵn nên không cần automation nào.

## Dữ liệu nằm ở đâu

```
data/                     (toàn bộ được .gitignore)
├─ library/<slug>/<chương>/001.webp      truyện đã tải
├─ library/<slug>/metadata.json          mô tả truyện, dựng lại DB được
├─ library.db · config.toml · logs/
├─ sites/*.yml                           rule của nguồn truyện
└─ browser/                              profile Edge khi cần phân giải URL
```

Đổi chỗ lưu: đặt biến môi trường `MANGALIB_DATA`.

## Đóng gói

```powershell
pyinstaller tools/mangalib.spec --noconfirm
```

`--onedir` có chủ đích: `data/` nằm cạnh file `.exe` thay vì trong thư mục tạm.

`shell-tauri/` là scaffold cho vỏ desktop bằng Rust — **chưa từng được biên dịch** vì máy phát triển không có Rust toolchain. Vỏ đang dùng là `mangalib app`: khay hệ thống + cửa sổ Edge `--app`, không thêm dependency nào.

## Thiết kế giao diện

Hướng hình ảnh được chốt qua plugin [impeccable](https://github.com/pbakaus/impeccable): sau khi xem các hướng khác, chủ dự án chọn **chuẩn của hạng mục, chơi thẳng** — quen mắt một cách có chủ đích, và khác biệt đến từ độ tinh của thi công. Thước đo: **Mihon/Tachiyomi** và **Komga/Kavita**.

Mọi màu nằm trong một khối `:root` của `web/app.css`, thay cho 43 mã hex rải rác trong bản cũ. Không bóng đổ, không gradient; phân vùng bằng đường kẻ hairline. Tiến độ đọc là một dải 2px sát đáy ảnh bìa, đọc được ở cỡ thumbnail. Font dùng system stack nên đủ dấu tiếng Việt và không tải gì từ Internet.

Chi tiết: `PRODUCT.md` (product truth) và `.impeccable/surfaces/` (direction contract).

## Khi có vấn đề

| Hiện tượng | Làm gì |
|---|---|
| Không biết app ghi file vào đâu | `mangalib doctor-paths` |
| Nghi scraper sai | `mangalib probe <url>` rồi `mangalib download <url> --dry-run` |
| Chương bị thiếu ảnh | Chạy lại `mangalib download` — chương `partial` sẽ được vá, chương `complete` được bỏ qua |
| Site đòi đăng nhập hoặc chặn | `--headful` để tự vượt một lần, hoặc dùng userscript |
| DB báo schema lệch | `mangalib scan --reset` (dời file cũ sang một bên, không xoá) |
| Điện thoại không thấy máy chủ | Mở cổng TCP 8000 và UDP 55555 trong Windows Firewall |

Log: `data/logs/log_YYYY-MM-DD.txt`. Lỗi nghiêm trọng: `data/logs/crash.log` (ghi thêm, không ghi đè).

## Miễn trừ trách nhiệm

Dự án cá nhân, phục vụ việc đọc offline trên thiết bị của chính người dùng. Phần mềm **không** đi kèm nguồn nội dung nào: người dùng tự khai báo nguồn trong `data/sites/` và tự chịu trách nhiệm tuân thủ điều khoản của website đó cũng như quy định bản quyền tại nơi mình sinh sống. Hãy tải ở mức hợp lý để không gây ảnh hưởng tới hạ tầng của nhà cung cấp.
