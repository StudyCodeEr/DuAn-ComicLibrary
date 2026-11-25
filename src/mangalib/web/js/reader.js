// Trình đọc: cuộn dọc, lazy-load, zoom bằng biến CSS, tự lưu vị trí đọc.
//
// Bản Flet cũ nạp TOÀN BỘ ảnh của chương vào RAM và phải lặp lại mọi control để
// đổi kích thước khi zoom. Ở đây trình duyệt làm sẵn cả hai: `loading="lazy"` và
// `img { width: min(var(--page-width), 100%) }`.
import { api, el, subscribeEvents } from "./api.js";

const slug = new URLSearchParams(location.search).get("slug");
const pagesBox = document.getElementById("pages");
const titleBox = document.getElementById("title");
const chapterSelect = document.getElementById("chapters");
const positionLabel = document.getElementById("pos");
const zoom = document.getElementById("zoom");

const state = { manga: null, chapterId: null, pages: [], current: 0 };

if (!slug) {
  titleBox.textContent = "Thiếu tham số ?slug=";
} else {
  start().catch((error) => {
    pagesBox.append(el("div", { class: "empty-state", text: `Lỗi: ${error.message}` }));
  });
}

async function start() {
  state.manga = await api.manga(slug);
  titleBox.textContent = state.manga.title;
  document.title = `${state.manga.title} · Manga Local Library`;

  chapterSelect.replaceChildren(
    ...state.manga.chapters.map((chapter) =>
      el("option", {
        value: chapter.id,
        text:
          (chapter.number !== null ? `Ch. ${chapter.number} — ` : "") +
          chapter.title +
          (chapter.status === "partial" ? "  (thiếu ảnh)" : ""),
      }),
    ),
  );

  const wanted =
    Number(new URLSearchParams(location.search).get("chapter")) ||
    state.manga.progress?.chapter_id ||
    state.manga.chapters[0]?.id;
  await openChapter(wanted, state.manga.progress?.page_idx || 0);
}

async function openChapter(chapterId, startPage = 0) {
  if (!chapterId) {
    pagesBox.replaceChildren(el("div", { class: "empty-state", text: "Truyện chưa có chương nào." }));
    return;
  }
  state.chapterId = chapterId;
  chapterSelect.value = String(chapterId);

  const data = await api.pages(slug, chapterId);
  state.pages = data.pages;
  pagesBox.replaceChildren(
    ...data.pages.map((page, index) =>
      el("img", {
        src: page.url,
        alt: `Trang ${index + 1}`,
        loading: index < 3 ? "eager" : "lazy",
        decoding: "async",
        width: page.width || undefined,
        height: page.height || undefined,
        "data-idx": index,
      }),
    ),
  );
  updatePosition(startPage);
  if (startPage > 0) {
    pagesBox.children[Math.min(startPage, pagesBox.children.length - 1)]?.scrollIntoView();
  } else {
    window.scrollTo(0, 0);
  }
}

function updatePosition(index) {
  state.current = index;
  positionLabel.textContent = state.pages.length
    ? `${index + 1}/${state.pages.length}`
    : "";
}

// Trang đang đọc = ảnh gần đỉnh khung nhìn nhất.
let saveTimer = 0;
window.addEventListener(
  "scroll",
  () => {
    let best = 0;
    let bestDistance = Infinity;
    for (const img of pagesBox.children) {
      const distance = Math.abs(img.getBoundingClientRect().top);
      if (distance < bestDistance) {
        bestDistance = distance;
        best = Number(img.dataset.idx);
      }
    }
    if (best !== state.current) updatePosition(best);

    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      if (state.chapterId) api.saveProgress(slug, state.chapterId, state.current).catch(() => {});
    }, 800);
  },
  { passive: true },
);

function step(delta) {
  const ids = state.manga.chapters.map((c) => c.id);
  const next = ids[ids.indexOf(state.chapterId) + delta];
  if (next) openChapter(next, 0);
}

document.getElementById("prev").addEventListener("click", () => step(-1));
document.getElementById("next").addEventListener("click", () => step(1));
chapterSelect.addEventListener("change", () => openChapter(Number(chapterSelect.value), 0));

document.addEventListener("keydown", (event) => {
  if (event.target.tagName === "INPUT" || event.target.tagName === "SELECT") return;
  if (event.key === "ArrowLeft") step(-1);
  if (event.key === "ArrowRight") step(1);
});

zoom.addEventListener("input", () => {
  document.documentElement.style.setProperty("--page-width", `${zoom.value}px`);
  localStorage.setItem("mlib.zoom", zoom.value);
});
const savedZoom = localStorage.getItem("mlib.zoom");
if (savedZoom) {
  zoom.value = savedZoom;
  document.documentElement.style.setProperty("--page-width", `${savedZoom}px`);
}

const themeButton = document.getElementById("theme");
const savedTheme = localStorage.getItem("mlib.theme");
if (savedTheme) document.documentElement.dataset.theme = savedTheme;
themeButton.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("mlib.theme", next);
});

// Chương đang tải dở: khi worker báo xong thì nạp lại danh sách trang.
subscribeEvents((event) => {
  if (event.phase === "done" && event.slug === slug && state.chapterId) {
    openChapter(state.chapterId, state.current).catch(() => {});
  }
});
