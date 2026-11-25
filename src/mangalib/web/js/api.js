// Lớp gọi API dùng chung. Không build step: ES module thuần, chạy trực tiếp.

const BASE = "/api/v1";

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
      /* phản hồi không phải JSON: giữ nguyên thông điệp mặc định */
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
  const here = location.pathname.endsWith("/") ? "index.html" : location.pathname.split("/").pop();
  for (const link of document.querySelectorAll(".nav a")) {
    if (link.getAttribute("href") === here) link.setAttribute("aria-current", "page");
  }
}
