# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Backend Python (FastAPI + uvicorn + SQLite). Frontend: HTML + CSS + ES modules thuần,
Alpine.js vendored vào repo, **không build step** (không npm/bundler). Vỏ desktop Tauri (Rust)
bọc chính UI web ở giai đoạn cuối. Quyết định này đã được chốt trong kế hoạch đại tu đã duyệt,
không phải suy đoán.

## Users

Một người dùng duy nhất: chủ dự án. Không có tài khoản, không phân quyền, không người dùng thứ hai.

Người này dùng **hai thiết bị quan trọng ngang nhau**:
- PC Windows: tải truyện, quản lý thư viện, đọc trên màn hình lớn.
- Điện thoại trong cùng mạng LAN: đọc truyện, và gửi link về PC để tải.

Công việc họ đang làm: tải truyện về máy để đọc offline, rồi tìm lại truyện cũ trong một thư viện
đang lớn dần.

## Product Purpose

Tải truyện tranh từ web về ổ đĩa của chính người dùng, lập chỉ mục theo tên truyện / tác giả /
thể loại, và đọc được ở cả PC lẫn điện thoại mà không phụ thuộc bất kỳ dịch vụ bên ngoài nào.

Thành công nghĩa là: truyện đã tải thì **luôn** đọc được, kể cả khi mất mạng, kể cả khi trang web
nguồn biến mất; và tìm lại một truyện trong thư viện mất vài giây, không phải lục thư mục.

## Positioning

Thư viện cục bộ + server LAN cá nhân: **một backend duy nhất phục vụ cả PC và điện thoại**, dữ liệu
nằm trên ổ đĩa người dùng, không máy chủ trung gian, không tài khoản, không đồng bộ ra ngoài. Hệ quả
mà một ứng dụng đọc truyện online không thể sao chép: vị trí đọc đồng bộ giữa PC và điện thoại trong
khi toàn bộ nội dung chưa bao giờ rời khỏi máy của người dùng.

## Operating Context

- Windows 11, máy **không có Chrome** — chỉ có Microsoft Edge 158 (đã kiểm tra).
- App chạy ngầm, có khay hệ thống, tùy chọn tự khởi động cùng Windows ở chế độ ẩn.
- Điện thoại truy cập qua IP LAN; ghép đôi một lần bằng QR code; có UDP discovery để khỏi nhập IP.
- Nội dung nằm ở `data/library/<slug>/<chương>/<trang>`; mỗi truyện có `metadata.json` tự mô tả.
- Việc tải cần mở browser **chỉ để phân giải danh sách URL ảnh** (trang nguồn dựng ảnh bằng JS);
  sau đó file được tải bằng HTTP song song ngoài browser.
- Thư viện hiện có 2 truyện (124 MB) tải bằng bản cũ.

## Capabilities and Constraints

**Đã xác nhận có:**
- Tải truyện theo link dán vào UI, hoặc bằng nút "Gửi vào thư viện" từ trình duyệt đang mở.
- Lập chỉ mục: tên truyện, **tác giả và họa sĩ** (bảng riêng, lọc/tìm được), thể loại, ảnh bìa.
- Lọc thể loại ba trạng thái: bắt buộc có / loại trừ / bỏ qua.
- Tìm kiếm khớp cả tên truyện lẫn tên tác giả, không dấu cũng ra.
- Trình đọc cuộn dọc, và **đồng bộ vị trí đọc giữa PC và điện thoại**.
- Tải lại thì bỏ qua phần đã có (resume 3 tầng), và báo đúng số ảnh lưu được.

**Ràng buộc bắt buộc:**
- **Giao diện tiếng Việt** toàn bộ: nhãn, thông báo, lỗi.
- **Hoạt động 100% offline**: không font, script hay ảnh nào tải từ Internet. Mất mạng vẫn đọc bình thường.
- Chỉ một người dùng: không màn hình đăng nhập, không onboarding nhiều bước, không thiết lập bắt buộc
  trước khi dùng được.
- Truy cập từ LAN cần token; request từ `127.0.0.1` thì miễn.

**Chưa quyết định (không được tự bịa):**
- Có xuất CBZ hay không.
- Có hỗ trợ thêm nguồn truyện nào khác ngoài nguồn hiện tại hay không.
- Có nhập thư mục ảnh/CBZ có sẵn vào thư viện hay không.

## Brand Commitments

- Tên sản phẩm: **Manga Local Library**.
- Icon: `app_icon.ico` (bắt buộc giữ).
- Tài sản ảnh có sẵn, bắt buộc giữ: `assets/bg-dark.jpg`, `assets/bg-light.jpg`.
- **Hướng hình ảnh (người dùng chọn, bền vững):** chuẩn của hạng mục, chơi thẳng — không châm
  biếm, không cài quirk lạ. Người dùng đã xem các hướng khác và chọn cửa thoát này có chủ đích.
- **Thước đo thi công (người dùng chọn):** Mihon/Tachiyomi và Komga/Kavita. Độ hoàn thiện của
  hai sản phẩm đó là mức mà bản build phải đạt — khác biệt đến từ độ tinh của thi công, không
  phải độ lạ của ý tưởng.
- Không có logo hay wordmark riêng; chưa có font nào được chốt (ràng buộc offline nên ưu tiên
  system font stack có đủ dấu tiếng Việt).

## Evidence on Hand

- `Downloads/` — 2 truyện đã tải thật (124 MB), dùng được làm dữ liệu thật khi dựng giao diện thư viện.
  Tên thư mục cho thấy một lỗi thật: tên truyện bị dính đuôi SEO của trang nguồn, và có chương tên
  `Nội dung trực tiếp`.
- `manga_library.db` — DB cũ (schema v1), có dữ liệu tag thật.
- `assets/bg-dark.jpg`, `assets/bg-light.jpg`, `app_icon.ico`.
- `reports/` — 9 tài liệu phân tích nội bộ (scout / plan / debug) của chính dự án.
- **Không có**: logo, bộ nhận diện, ảnh chụp sản phẩm, testimonial, số liệu người dùng, benchmark.
  Những thứ này không tồn tại và không được bịa ra trong bất kỳ thiết kế nào.

## Product Principles

1. **Dữ liệu là của người dùng và nằm trên máy họ.** Không dịch vụ ngoài, không tài khoản, không
   đồng bộ ngầm.
2. **PC và điện thoại là hai mặt bằng nhau của cùng một thư viện** — không phải một bản chính và một
   bản rút gọn.
3. **Không bao giờ báo thành công khi chưa thành công.** Trạng thái hiển thị phải là trạng thái thật
   (bản cũ báo "Xong: N ảnh" với N là số URL tìm thấy, kể cả khi chương trắng).
4. **Mất mạng là trạng thái bình thường, không phải lỗi.** Mọi thứ đã tải phải dùng được offline.
5. **Một người dùng, không nghi thức.** Mở ra là đọc được; không bước thiết lập nào chắn đường.
