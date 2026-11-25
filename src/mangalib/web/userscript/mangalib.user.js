// ==UserScript==
// @name         Gửi vào Manga Local Library
// @namespace    mangalib
// @version      1.0.0
// @description  Gửi danh sách ảnh của chương đang mở về mangalib trên máy này
// @match        *://*/*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

/*
 * Dùng khi site cần đăng nhập hoặc chặn truy cập tự động: trang đã render trong
 * trình duyệt của chính bạn, nên script chỉ cần đọc danh sách ảnh và gửi về
 * 127.0.0.1. Không có automation nào, và cookie chỉ đi trong một request rồi
 * mangalib giữ nó trong RAM, không ghi xuống đĩa.
 */
(function () {
  "use strict";

  const ENDPOINT = "http://127.0.0.1:8000/api/v1/capture";
  const MIN_WIDTH = 400;

  function collectImages() {
    const seen = new Set();
    const urls = [];
    for (const img of document.querySelectorAll("img")) {
      const src = img.currentSrc || img.src || "";
      if (!src.startsWith("http") || seen.has(src)) continue;
      if (img.naturalWidth < MIN_WIDTH) continue;
      if (/loading\.gif|avatar|logo|icon|banner|sprite/i.test(src)) continue;
      seen.add(src);
      urls.push(src);
    }
    return urls;
  }

  function send(button) {
    const images = collectImages();
    if (!images.length) {
      button.textContent = "Chưa thấy ảnh — cuộn hết trang rồi bấm lại";
      return;
    }
    button.disabled = true;
    button.textContent = `Đang gửi ${images.length} ảnh…`;

    GM_xmlhttpRequest({
      method: "POST",
      url: ENDPOINT,
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify({
        source_url: location.origin + location.pathname.replace(/\/[^/]*$/, ""),
        chapter_url: location.href,
        title: (document.querySelector("h1") || {}).textContent?.trim() || document.title,
        chapter_title: document.title,
        images,
        cookies: Object.fromEntries(
          document.cookie
            .split(";")
            .map((part) => part.trim().split("="))
            .filter((pair) => pair.length === 2),
        ),
        user_agent: navigator.userAgent,
      }),
      onload: (response) => {
        button.disabled = false;
        try {
          const body = JSON.parse(response.responseText);
          button.textContent = `Đã lưu ${body.saved + body.skipped}/${body.expected} trang (${body.status})`;
        } catch {
          button.textContent = `Lỗi: HTTP ${response.status}`;
        }
      },
      onerror: () => {
        button.disabled = false;
        button.textContent = "Không kết nối được mangalib (đã chạy `mangalib serve` chưa?)";
      },
    });
  }

  const button = document.createElement("button");
  button.textContent = "Gửi vào thư viện";
  button.style.cssText = [
    "position:fixed", "right:16px", "bottom:16px", "z-index:999999",
    "padding:10px 14px", "border-radius:8px", "border:1px solid #06b6d4",
    "background:#0f172a", "color:#e2e8f0", "font:14px system-ui", "cursor:pointer",
  ].join(";");
  button.addEventListener("click", () => send(button));
  document.body.appendChild(button);
})();
