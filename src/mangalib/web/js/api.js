// Lớp gọi API + helper dựng DOM. Không build step: ES module thuần.

const BASE = "/api/v1";

// Theme phải áp TRƯỚC khi vẽ, và áp trên MỌI trang. Trước đây reader và settings
// ghi localStorage nhưng thư viện không đọc, nên chọn sáng rồi quay lại là tối.
export function applyTheme() {
  const saved = localStorage.getItem("mlib.theme");
  if (saved === "light" || saved === "dark") {
    document.documentElement.dataset.theme = saved;
  }
}
applyTheme();

export function toggleTheme() {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("mlib.theme", next);
  return next;
}

async function request(path, options = {}) {
  const response = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      /* phản hồi không phải JSON: giữ thông điệp mặc định */
    }
    throw new Error(detail);
  }
  return response.status === 204 ? null : response.json();
}

export const api = {
  health: () => request("/health"),
  library: (params) => request(`/library?${new URLSearchParams(params)}`),
  tags: () => request("/tags"),
  authors: () => request("/authors"),
  manga: (slug) => request(`/manga/${encodeURIComponent(slug)}`),
  pages: (slug, chapterId) =>
    request(`/manga/${encodeURIComponent(slug)}/chapters/${chapterId}/pages`),
  saveProgress: (slug, chapterId, pageIdx) =>
    request(`/progress/${encodeURIComponent(slug)}`, {
      method: "PUT",
      body: JSON.stringify({ chapter_id: chapterId, page_idx: pageIdx }),
    }),
  jobs: (activeOnly = false) => request(`/jobs?active_only=${activeOnly}`),
  createJob: (url) => request("/jobs", { method: "POST", body: JSON.stringify({ url }) }),
  cancelJob: (id) => request(`/jobs/${id}`, { method: "DELETE" }),
  settings: () => request("/settings"),
  pickFolder: () => request("/settings/pick-folder", { method: "POST" }),
  saveSettings: (body) =>
    request("/settings", { method: "PATCH", body: JSON.stringify(body) }),
};

export function subscribeEvents(onEvent) {
  const source = new EventSource(`${BASE}/jobs/events`);
  source.onmessage = (message) => {
    try {
      onEvent(JSON.parse(message.data));
    } catch {
      /* bỏ qua gói tin không đọc được */
    }
  };
  return source;
}

// Icon vẽ bằng SVG một nét, thay cho ký tự Unicode (←, →, ◐) vì chúng đổi nét
// và đường cơ sở giữa Windows, Android và iOS — người dùng thấy cả hai thiết bị.
const PATHS = {
  prev: "M14 5 L7 12 L14 19",
  next: "M10 5 L17 12 L10 19",
  theme: "M12 3 A9 9 0 0 1 12 21 Z M12 3 A9 9 0 0 0 12 21",
  close: "M6 6 L18 18 M18 6 L6 18",
  back: "M11 5 L4 12 L11 19 M4 12 H20",
  download: "M12 4 V15 M7 11 L12 16 L17 11 M5 20 H19",
};

export function icon(name, { size = 18 } = {}) {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("class", "icon");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("width", size);
  svg.setAttribute("height", size);
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", PATHS[name] || PATHS.close);
  path.setAttribute("fill", "none");
  path.setAttribute("stroke", "currentColor");
  path.setAttribute("stroke-width", "2");
  path.setAttribute("stroke-linecap", "round");
  path.setAttribute("stroke-linejoin", "round");
  svg.append(path);
  return svg;
}

export function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) {
    if (child) node.append(child);
  }
  return node;
}

export function markCurrentNav() {
  // "/" phuc vu downloads.html, nen tab sang len phai la Tai ve chu khong phai Thu vien.
  const here = location.pathname.endsWith("/")
    ? "downloads.html"
    : location.pathname.split("/").pop();
  for (const link of document.querySelectorAll(".nav a")) {
    if (link.getAttribute("href").split("?")[0] === here) {
      link.setAttribute("aria-current", "page");
    }
  }
}
