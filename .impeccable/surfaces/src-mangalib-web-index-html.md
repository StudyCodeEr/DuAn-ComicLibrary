---
version: 1
slug: "src-mangalib-web-index-html"
primary_target: "src/mangalib/web/index.html"
related_targets: ["src/mangalib/web/reader.html","src/mangalib/web/downloads.html","src/mangalib/web/settings.html"]
---

Scope: thư viện + trình đọc + hàng đợi tải + cài đặt, phục vụ cùng lúc PC và điện thoại từ một server cục bộ. Visitor mode: Operate.

Audience: một người dùng duy nhất, hai thiết bị quan trọng ngang nhau. Job: duyệt bằng mắt để chọn truyện đọc, trong một thư viện hàng nghìn mục. Phải thấy ngay không cần bấm: đọc tới đâu, số chương/số trang, thể loại. Ràng buộc: tiếng Việt toàn bộ, chạy 100% offline, giữ tên "Manga Local Library" và `app_icon.ico`.

## Direction contract

THESIS: Thư viện nghìn truyện mà tiến độ đọc, dung lượng chương và thể loại đều đọc được ngay trên bìa, không phải bấm vào. Nó từ chối lối bày poster-wall kiểu rạp chiếu, nơi mọi metadata ẩn sau tiêu điểm.

OWN-WORLD: Nền slate tối #0F172A, chữ #E2E8F0, một màu nhấn cyan #06B6D4. Chia vùng bằng hairline #334155; không bóng đổ, không gradient, không glass. Lưới bìa tỉ lệ 2:3, 2–7 cột theo bề rộng. Thanh tiến độ 2px sát đáy bìa; chip thể loại ba trạng thái; mọi số đếm dùng chữ số tabular.

STORY: Mở ra là thấy ngay truyện đang đọc dở; quét lưới bằng mắt, hoặc lọc bằng chip thể loại và gõ tên tác giả; một lần bấm vào đúng trang đang đọc, trên PC hay điện thoại đều cùng vị trí.

FIRST VIEWPORT: Thanh trên cùng mang tên app, ô tìm kiếm và bốn mục điều hướng. Ngay dưới là dải "Đọc tiếp" cao 160px chứa các truyện dở, cuộn ngang. Phần còn lại của khung là lưới bìa dày đặc: mỗi ô có thanh tiến độ ở đáy, badge số chương ở góc trên phải, hai chip thể loại dưới tên truyện. Hành động chính là chính ô bìa.

FORM: Cửa thoát thường trực — chuẩn của hạng mục, chơi thẳng, không châm biếm và không cài quirk. Không nằm trong danh sách bảy hướng của tôi. Thước đo thi công do người dùng chọn: Mihon/Tachiyomi và Komga/Kavita. seed:df75ff6dc95a2bb9

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance

Unresolved: có xuất CBZ hay không; có nhập thư mục ảnh/CBZ có sẵn hay không.
