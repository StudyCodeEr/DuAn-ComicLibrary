---
name: Manga Local Library
description: Thư viện truyện cục bộ, phẳng và chia vùng bằng hairline, nơi tiến độ đọc đọc được ngay trên bìa.
colors:
  ground: "#14161b"
  surface: "#1c1f26"
  surface-hi: "#252932"
  line: "#30353f"
  line-soft: "#23272f"
  text: "#e8e6e1"
  muted: "#8c9099"
  accent: "#c9a227"
  accent-ink: "#1a1505"
  ok: "#4e9a6a"
  warn: "#c98a2b"
  bad: "#c0564f"
  ground-light: "#f4f2ee"
  surface-light: "#ffffff"
  surface-hi-light: "#eae7e0"
  line-light: "#d7d2c9"
  line-soft-light: "#e6e2da"
  text-light: "#1b1d22"
  muted-light: "#6b6f78"
  accent-light: "#8a6d12"
  accent-ink-light: "#ffffff"
typography:
  display:
    fontFamily: "Segoe UI, system-ui, -apple-system, Noto Sans, Arial, sans-serif"
    fontSize: "26px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "Segoe UI, system-ui, -apple-system, Noto Sans, Arial, sans-serif"
    fontSize: "19px"
    fontWeight: 600
    lineHeight: 1.5
    letterSpacing: "-0.01em"
  title:
    fontFamily: "Segoe UI, system-ui, -apple-system, Noto Sans, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    lineHeight: 1.5
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Segoe UI, system-ui, -apple-system, Noto Sans, Arial, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Segoe UI, system-ui, -apple-system, Noto Sans, Arial, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.3
  caption:
    fontFamily: "Segoe UI, system-ui, -apple-system, Noto Sans, Arial, sans-serif"
    fontSize: "11px"
    fontWeight: 400
    lineHeight: 1.6
  mono:
    fontFamily: "ui-monospace, Cascadia Mono, Consolas, monospace"
    fontSize: "13px"
    lineHeight: 1.6
rounded:
  md: "8px"
  pill: "999px"
spacing:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  gap: "16px"
  gap-phone: "12px"
components:
  button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "8px 13px"
  button-hover:
    backgroundColor: "{colors.surface-hi}"
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "8px 13px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "8px 13px"
  button-icon:
    backgroundColor: "transparent"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "7px"
    size: "18px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 10px"
  chip:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.pill}"
    padding: "4px 10px"
  chip-include:
    textColor: "{colors.ok}"
  chip-exclude:
    textColor: "{colors.bad}"
  nav-link:
    backgroundColor: "transparent"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.md}"
    padding: "6px 11px"
  nav-link-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "6px 11px"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    width: "148px"
  card-badge:
    textColor: "{colors.text}"
    typography: "{typography.caption}"
    rounded: "{rounded.pill}"
    padding: "2px 7px"
  panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    padding: "16px"
  resume-tile:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.md}"
    width: "320px"
    height: "132px"
  log-console:
    backgroundColor: "{colors.ground}"
    textColor: "{colors.text}"
    typography: "{typography.mono}"
    rounded: "{rounded.md}"
    padding: "10px"
    height: "240px"
---

# Design System: Manga Local Library

## Overview

**Creative North Star: "Kệ sách trong phòng tối"**

Hệ này là chuẩn của hạng mục, chơi thẳng. Thước đo thi công do người dùng chọn là Mihon/Tachiyomi và Komga/Kavita: khác biệt phải đến từ độ tinh của thi công, không phải độ lạ của ý tưởng. Nền là mực xanh lạnh pha ấm (`#14161b`), chữ là trắng ngà chứ không phải trắng xám, và chỉ có một màu nhấn — đồng thau `#c9a227` — đủ sáng để đọc ở một dải cao 2px trên bìa truyện. Bảng màu này được chỉnh tay sau vòng review hoàn thiện, không lấy nguyên ramp của framework nào.

Vật liệu là phẳng tuyệt đối. Không bóng đổ, không gradient, không glass; mọi phân vùng làm bằng đường kẻ 1px. Độ sâu đến từ ba bậc nền (`ground` → `surface` → `surface-hi`) chứ không từ ánh sáng giả. `backdrop-filter: none` được viết ra tường minh trên `.readerbar` để lớp chrome của trình đọc không bao giờ trượt về hiệu ứng kính.

Mật độ cao là chủ ý: công việc của bề mặt chính là duyệt bằng mắt một thư viện hàng nghìn mục, nên bìa xếp dày (`minmax(148px, 1fr)`, xuống 118px trên điện thoại) và mỗi ô tự mang đủ thông tin. Chữ dùng system stack dẫn đầu bằng Segoe UI với Noto Sans đứng sau để đủ dấu tiếng Việt — hệ quả trực tiếp của ràng buộc 100% offline trong PRODUCT.md: không font, script hay ảnh nào được tải từ Internet, nên không có thư viện nào được vendor vào.

PRODUCT.md ghim `assets/bg-dark.jpg` và `assets/bg-light.jpg` là tài sản bắt buộc giữ, và bản ship không tham chiếu cả hai. Lý do được ghi lại ở đây để chỗ trống này truy được, không giống như một thứ bị bỏ quên: thế giới đã chốt là phẳng và chia vùng bằng hairline, nên một nền trang bằng ảnh chụp sẽ chống lại chính quy tắc vật liệu của nó. Hai file vẫn nằm trong repo theo yêu cầu của người dùng, nhưng **chúng không thuộc hệ thống hình ảnh này** và không được đưa vào bề mặt mới.

**Key Characteristics:**
- Phẳng tuyệt đối: không bóng đổ, không gradient, không glass — chỉ hairline 1px.
- Ba bậc nền thay cho độ cao: `#14161b` → `#1c1f26` → `#252932`.
- Một màu nhấn duy nhất, đồng thau `#c9a227`, dùng rất tiết kiệm.
- Mật độ cao: bìa 2:3 xếp dày, mỗi ô tự đủ thông tin.
- System font stack, zero tài sản tải từ mạng.
- Số đếm luôn dùng chữ số tabular (`font-variant-numeric: tabular-nums` trên `body`).

## Colors

Bảng màu là mực xanh lạnh pha ấm với một màu nhấn kim loại; mọi màu sống trong một khối `:root` duy nhất cộng một lớp override `[data-theme="light"]`.

### Primary
- **Đồng thau** (`accent`): màu nhấn duy nhất của hệ. Dùng cho dải tiến độ "đang đọc", nút chính, viền focus, caret, `::selection`, số chương trong dòng trạng thái, viền hover của thẻ bìa, và phần nhãn phase trong log. Ở theme sáng nó tối lại thành vàng ô-liu đậm (`accent-light`) để giữ tương phản trên giấy trắng.
- **Mực nhấn** (`accent-ink`): chữ đặt trên nền đồng thau; gần như đen pha nâu ở theme tối, trắng ở theme sáng.

### Tertiary
Ba màu trạng thái, chỉ dùng cho trạng thái thật — không bao giờ để trang trí:
- **Xanh hoàn tất** (`ok`): "đã đọc hết" (dải tiến độ đầy), job `done`, chip thể loại ở trạng thái "bắt buộc có".
- **Vàng cần người** (`warn`): job `needs_login` — việc đang chờ người dùng, không phải lỗi.
- **Đỏ thất bại** (`bad`): job `failed`, dòng lỗi, chip thể loại "loại trừ" (kèm gạch ngang).

### Neutral
- **Mực nền** (`ground`): nền trang, nền thanh trên, nền thanh dưới của trình đọc, nền khung log.
- **Nền nổi** (`surface`): thẻ, panel, input, nút mặc định, mục điều hướng đang chọn.
- **Nền nổi cao** (`surface-hi`): hover của nút, và ô giữ chỗ phía sau ảnh bìa/ảnh trang đang tải.
- **Kẻ** (`line`): mọi đường phân vùng và mọi viền thành phần, luôn 1px.
- **Kẻ nhạt** (`line-soft`): viền của tag nhỏ trong thẻ bìa, nơi `line` sẽ quá nặng.
- **Trắng ngà** (`text`): chữ chính. Không phải trắng xám — đây là lựa chọn có chủ ý.
- **Xám chữ phụ** (`muted`): nhãn, số đếm, metadata, URL, mục điều hướng chưa chọn.

### Named Rules
**The One Brass Rule.** Chỉ một màu nhấn trong cả hệ, và nó phải kiếm được chỗ của mình: tiến độ đọc, hành động chính, focus. Nếu một bề mặt mới cần "một màu nữa cho đẹp", câu trả lời là hairline hoặc `muted`.

**The Real-State Rule.** `ok` / `warn` / `bad` chỉ được gán từ trạng thái thật của dữ liệu (ratio đọc, state của job). Không bao giờ tô màu trạng thái cho thứ chưa biết là đúng — đây là Product Principle 3 nói bằng màu.

## Typography

**Display Font:** Segoe UI (system-ui, -apple-system, Noto Sans, Arial, sans-serif)
**Body Font:** cùng stack — hệ chỉ có một họ chữ
**Label/Mono Font:** ui-monospace (Cascadia Mono, Consolas, monospace), chỉ dùng trong khung log

**Character:** Một stack hệ thống, không trang trí, dẫn đầu bằng Segoe UI cho Windows và có Noto Sans đứng sau để dấu tiếng Việt không bị gãy trên Android. Tính cách đến từ bậc chữ và độ đậm, không từ mặt chữ — và từ việc không tải một byte nào từ mạng.

### Hierarchy
- **Display** (700, 26px, 1.5, `-0.02em`): tiêu đề trang (`h1.page`). Xuống 21px trên điện thoại.
- **Headline** (600, 19px, 1.5, `-0.01em`): tiêu đề panel. Xuống 17px trên điện thoại.
- **Title** (700, 15px, 1.5, `-0.015em`): tên app ở thanh trên, với "Local Library" ăn màu nhấn.
- **Body** (400, 15px, 1.5): chữ mặc định của `body`, kèm `tabular-nums`.
- **Label** (600, 13px, 1.3): tên truyện trong thẻ bìa, nhãn nút, mục điều hướng, chip, trạng thái job, vị trí trang trong trình đọc.
- **Caption** (400, 11px, 1.6): badge số chương/số trang, tag thể loại, dòng metadata phụ.
- **Mono** (13px, 1.6): nhật ký tải realtime — đây là nơi duy nhất mono được phép xuất hiện.

Bậc chữ có đúng năm bước (`--fs-xs` 11 · `--fs-sm` 13 · `--fs-base` 15 · `--fs-lg` 19 · `--fs-xl` 26); hai bước lớn nhất co lại trên điện thoại, ba bước nhỏ giữ nguyên để metadata vẫn đọc được.

### Named Rules
**The Five-Step Rule.** Năm bậc chữ, hết. Một cỡ mới phải là một biến mới trong `:root`, không phải một `font-size` viết rời trong thành phần.

**The Tabular Rule.** Mọi số đếm — chương, trang, tiến độ, job — dùng chữ số tabular, vì chúng nằm cạnh nhau trong lưới và phải thẳng cột khi thay đổi.

## Layout

Một nhịp duy nhất: `--gap: 16px`, xuống 12px dưới 640px. Khoảng đệm trong thành phần dùng nhịp nhỏ hơn và lặp lại (4 · 6 · 8 · 10px); không có giá trị nào ngoài hai dãy này.

Thân trang không có container giới hạn: `main` chỉ có padding bằng `--gap` và lưới chiếm hết bề rộng — thư viện dày đặc là mục tiêu, không phải một cột đọc. Lưới bìa là `repeat(auto-fill, minmax(var(--cover-min), 1fr))` với `--cover-min` 148px (118px trên điện thoại), `align-items: start`, nên số cột tự giãn theo bề rộng mà không cần breakpoint riêng.

Chỉ có **một** breakpoint: `max-width: 640px`. Ở đó bốn thứ đổi, mỗi thứ vì một lý do quan sát được: ô tìm kiếm xuống hàng riêng chiếm cả chiều rộng (`order: 3; flex: 1 0 100%`) thay vì bị bóp còn ~70px; hàng chip thể loại cuộn ngang một dòng thay vì xuống nhiều dòng; thanh trên cho phép `flex-wrap` với `row-gap: 8px`; và `--cover-min` / `--gap` / hai bậc chữ lớn co lại.

Thanh trên là `position: sticky; top: 0` với `z-index: 10`; thanh điều khiển của trình đọc là `position: fixed` ở đáy. Trình đọc dựng chiều rộng trang bằng đúng một biến (`--page-width: 900px`, `width: min(var(--page-width), 100%)`), nên thanh zoom chỉ ghi lại biến đó chứ không dựng lại layout.

### Named Rules
**The One-Breakpoint Rule.** Một ngưỡng 640px. Hành vi đáp ứng khác phải đến từ `auto-fill` / `flex-wrap` / `min()`, không từ một media query mới.

## Elevation & Depth

Hệ này **không có bóng đổ nào**, không gradient, không glass, không `backdrop-filter`. Không có từ vựng shadow để liệt kê — đó là câu trả lời đầy đủ.

Độ sâu đến từ hai thứ: ba bậc nền (`ground` cho trang và chrome, `surface` cho vật nổi lên, `surface-hi` cho hover và ô giữ chỗ), và đường kẻ 1px `line` phân vùng. Lớp chrome của trình đọc nằm trên nội dung bằng `position: fixed` và nền đặc `ground`, với `backdrop-filter: none` viết ra tường minh để nó không trượt về kính mờ.

### Named Rules
**The Hairline Rule.** Hai vùng tách nhau bằng một đường 1px `line`, không bao giờ bằng bóng đổ hay nền mờ. Nếu một bố cục cần bóng để đọc được, bố cục đó sai, không phải vật liệu.

**The No-Glass Rule.** `backdrop-filter` bị cấm trên mọi bề mặt. Lớp nổi dùng nền đặc `ground` cộng một hairline.

## Shapes

Hai bán kính, và chỉ hai. `8px` (`--radius`) cho mọi thứ hình chữ nhật: thẻ, panel, input, nút, mục điều hướng, khung log, ô job. `999px` cho mọi thứ dạng viên: chip thể loại, badge trên bìa, tag nhỏ, thẻ tác giả. Không có góc vuông tuyệt đối và không có bán kính trung gian.

Mọi thành phần có nền đều có viền `1px solid var(--line)` — viền là cách hệ này vẽ hình, nên một thẻ không viền sẽ tan vào nền. Thẻ bìa dùng `overflow: hidden` để ảnh bìa bị cắt đúng theo bán kính. Hình học lặp lại duy nhất là khung 2:3 (`aspect-ratio: 2 / 3`) của bìa truyện.

## Components

### Buttons
- **Shape:** góc cong nhẹ (8px), luôn có viền 1px `line`.
- **Default:** nền `surface`, chữ `text`, padding `8px 13px`, cỡ nhãn 13px, `display: inline-flex` với `gap: 6px` để icon SVG đứng cạnh chữ.
- **Primary:** nền và viền `accent`, chữ `accent-ink`, font-weight 600. Dùng cho hành động chính duy nhất của một bề mặt.
- **Ghost:** nền trong suốt, giữ viền. Dùng cho hành động phụ ("Tải thêm", "Huỷ") và cho nút chỉ có icon.
- **Icon-only:** biến thể ghost với padding `7px` và một icon 18px; luôn kèm `aria-label` và `title` tiếng Việt.
- **Hover / Focus:** hover đổi nền sang `surface-hi`. Focus là `outline: 2px solid var(--accent)` với `outline-offset: 2px` — cùng một vòng focus cho nút, input, select và thẻ bìa, không ngoại lệ.

### Chips
- **Style:** viên tròn (999px), nền `surface`, viền `line`, chữ `muted` 13px, kèm một `<span class="n">` đếm số ở cỡ 11px.
- **State:** ba trạng thái thật của bộ lọc thể loại — bỏ qua (mặc định, xám), bắt buộc có (viền và chữ `ok`), loại trừ (viền và chữ `bad`, thêm `text-decoration: line-through`). Hover chỉ nâng chữ lên `text`.
- Trên điện thoại hàng chip thành một dòng cuộn ngang với scrollbar ẩn.

### Cards / Containers
- **Corner Style:** 8px, `overflow: hidden`.
- **Background:** `surface`; ô giữ chỗ của ảnh là `surface-hi`.
- **Shadow Strategy:** không có — xem Elevation & Depth.
- **Border:** `1px solid var(--line)`; hover đổi viền sang `accent` (viền là tín hiệu hover duy nhất, không có transform hay bóng).
- **Internal Padding:** `8px` trong vùng meta của thẻ bìa, `16px` (`--gap`) trong panel.
- **Panel:** khối nội dung của các trang cài đặt / tải về / tác giả: nền `surface`, viền hairline, padding `--gap`, tiêu đề 19px.

### Inputs / Fields
- **Style:** nền `surface`, viền `1px solid line`, bán kính 8px, padding `8px 10px`, `font: inherit`, `caret-color: accent`, `min-width: 0` để không phá flex.
- **Focus:** vòng `outline: 2px solid accent` với offset 2px — giống hệt nút.
- **Search:** `flex: 1 1 240px; max-width: 420px` trong thanh trên; dưới 640px nó chiếm cả hàng riêng.

### Navigation
- Thanh trên sticky, nền `ground`, phân cách bằng hairline dưới. Tên app bên trái (15px/700, với "Local Library" ăn màu nhấn), nhóm điều hướng đẩy sang phải bằng `margin-left: auto`, ô tìm kiếm cuối.
- Mục điều hướng: 13px, chữ `muted`, viền trong suốt, bán kính 8px. Hover: nền `surface`, chữ `text`. Trang hiện tại (`[aria-current="page"]`): nền `surface`, chữ `text`, viền `line` — trạng thái active do `markCurrentNav()` gán từ pathname, không viết tay trong HTML.

### Signature Component — Thẻ bìa (cover tile)
Thành phần định nghĩa cả hệ. Một thẻ bìa là khung 2:3 cộng một dải meta, và nó mang **ba sự thật đọc được ở cỡ thumbnail** mà không cần bấm:

1. **Dải tiến độ 2px** sát đáy bìa (`inset: auto 0 0 0`), với rãnh là `color-mix(in srgb, var(--line) 70%, transparent)` và thanh trong là `<i>` có `width` theo phần trăm. Ba trạng thái phân biệt được: **chưa đọc** — không có dải nào trong DOM; **đang đọc** — dải đồng thau dài theo ratio; **đã đọc hết** — dải `ok` đầy (`[data-done="1"]`).
2. **Badge** ở góc trên phải (999px, nền `ground` 86% opaque, viền hairline, 11px) mang cả số chương và số trang: `12 ch · 240 tr`.
3. **Dải meta** dưới bìa: tên truyện 13px/600 khoá cứng ở `height: 2.6em` (hai dòng, cắt tràn) để lưới không gãy nhịp, một dòng trạng thái đọc nơi phần in đậm ăn màu `accent` hoặc `ok`, và tối đa hai tag thể loại dạng viên viền `line-soft` trong một hàng cao 20px.

Cả thẻ là một `<a>` — hành động chính là chính ô bìa, không có nút chồng lên.

### Signature Component — Dải "Đọc tiếp"
Băng cuộn ngang ngay dưới thanh trên, tự ẩn (`hidden`) khi không có truyện nào đọc dở. Tiêu đề là nhãn 13px/600 `muted` in hoa với `letter-spacing: 0.04em`. Mỗi ô là một thẻ ngang 320×132px (244×118 trên điện thoại): bìa cắt dọc bên trái, tên truyện ở bậc `--fs-lg` (bậc chữ cao nhất của bề mặt thư viện), dòng vị trí đọc "trang 13/51" — chứ không phải tên chương, vì tên chương lấy từ site thường là rác — và một dòng "Đọc tiếp" màu nhấn kèm chevron SVG. Nội dung căn giữa theo trục dọc; không dùng `margin-top: auto` (cách đó để lại một khoảng trống ~85px và đã bị bỏ). Hover đổi viền sang `accent`.

### Reader chrome
Thanh trên và thanh dưới của trình đọc **lùi đi khi đang đọc và hiện lại khi chạm hoặc khi dừng cuộn** — hành vi của Mihon và Komga. Cơ chế: `data-chrome` trên `<body class="reader">`; khi `hidden`, thanh trên `translateY(-100%)` và thanh dưới `translateY(100%)`, cả hai `opacity: 0`. Transition `transform 0.18s ease, opacity 0.18s ease`, và cả hai transition bị tắt hoàn toàn dưới `prefers-reduced-motion: reduce`. Khi cuộn dừng, chrome quay lại sau 900ms.

### Icons
Icon là SVG inline dựng bằng `icon(name)` trong `js/api.js`: `viewBox="0 0 24 24"`, 18px, `fill: none`, `stroke: currentColor`, `stroke-width: 2`, `stroke-linecap/linejoin: round`, `aria-hidden="true"`. **Một độ dày nét duy nhất cho cả hệ.** Ký tự Unicode đứng thay icon đã bị bỏ, vì chúng đổi nét và đường cơ sở giữa Windows, Android và iOS — và người dùng này thấy cả hai thiết bị.

## Do's and Don'ts

### Do:
- **Do** phân vùng bằng `1px solid var(--line)`; dùng `line-soft` khi đường kẻ nằm bên trong một thẻ đã có viền.
- **Do** lấy mọi màu, cỡ chữ, nhịp và bán kính từ biến trong `:root` của `src/mangalib/web/app.css`; màu mới phải được thêm vào cả `:root` và `[data-theme="light"]`.
- **Do** dùng đúng hai bán kính: 8px cho khối, 999px cho viên.
- **Do** dựng icon bằng `icon()` — SVG inline, một độ dày nét 2, `stroke: currentColor`.
- **Do** cho mọi thành phần tương tác cùng một vòng focus: `outline: 2px solid var(--accent)`, `outline-offset: 2px`.
- **Do** tôn trọng `prefers-reduced-motion: reduce` cho mọi transition mới, như chrome của trình đọc đã làm.
- **Do** để tiến độ đọc có ba trạng thái phân biệt được (không dải · dải nhấn · dải xanh đầy), không phải một dải bật/tắt.
- **Do** viết mọi nhãn, thông báo và lỗi bằng tiếng Việt, và cho mọi nút chỉ có icon một `aria-label` tiếng Việt.
- **Do** giữ mọi tài sản cục bộ: không font, script hay ảnh nào tải từ Internet.

### Don't:
- **Don't** dùng `box-shadow`, `gradient` hay `backdrop-filter` ở bất kỳ đâu — kể cả cho lớp nổi; dùng nền đặc `ground` cộng hairline.
- **Don't** thêm màu nhấn thứ hai. `accent` là duy nhất; `ok` / `warn` / `bad` chỉ dành cho trạng thái thật của dữ liệu.
- **Don't** tô màu trạng thái cho thứ chưa xác nhận là đúng (Product Principle 3: không bao giờ báo thành công khi chưa thành công).
- **Don't** thêm bậc chữ thứ sáu hay viết `font-size` rời trong thành phần — năm biến `--fs-*` là toàn bộ bậc chữ.
- **Don't** thêm media query mới; dùng `auto-fill`, `flex-wrap` và `min()`, và nếu buộc phải có ngưỡng thì vẫn là 640px.
- **Don't** dùng ký tự Unicode (`←`, `→`, `✕`, `◐`) làm icon trong giao diện; chúng chỉ được phép trong chữ gợi ý bàn phím như `title="Chương trước (←)"`.
- **Don't** đặt ảnh chụp làm nền trang hay nền thẻ. `assets/bg-dark.jpg` và `assets/bg-light.jpg` được giữ trong repo theo yêu cầu của người dùng nhưng **không thuộc hệ thống này**: một nền ảnh sẽ phá quy tắc phẳng + hairline.
- **Don't** vendor thư viện CSS/JS hay tải font từ CDN; ràng buộc 100% offline là bắt buộc, không phải sở thích.
- **Don't** viết style trực tiếp vào thuộc tính `style` của HTML cho một mẫu đã lặp lại — nó phải thành một class trong `app.css`.
