// Trình đọc: cuộn dọc, lazy-load, zoom bằng biến CSS, tự lưu vị trí đọc.
//
// Bản Flet cũ nạp TOÀN BỘ ảnh của chương vào RAM và phải lặp lại mọi control khi
// zoom. Ở đây trình duyệt làm sẵn cả hai.
import { api, el, icon, subscribeEvents, toggleTheme } from "./api.js";

const slug = new URLSearchParams(location.search).get("slug");
const pagesBox = document.getElementById("pages");
const titleBox = document.getElementById("title");
const chapterSelect = document.getElementById("chapters");
const positionLabel = document.getElementById("pos");
const zoom = document.getElementById("zoom");

document.getElementById("back").append(icon("back"));
document.getElementById("prev").append(icon("prev"));
document.getElementById("next").append(icon("next"));
document.getElementById("theme").append(icon("theme"));

const state = { manga: null, chapterId: null, pages: [], current: 0, observer: null };

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
  document.title = `${state.manga.title} · Comic Library`;

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
    pagesBox.replaceChildren(
      el("div", { class: "empty-state", text: "Truyện chưa có chương nào." }),
    );
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

  watchPages();
  updatePosition(startPage);
  if (startPage > 0) {
    pagesBox.children[Math.min(startPage, pagesBox.children.length - 1)]?.scrollIntoView();
  } else {
    window.scrollTo(0, 0);
  }
}

/* Trang đang đọc = ảnh đang nằm ở vùng trên của khung nhìn.
   IntersectionObserver thay cho việc gọi getBoundingClientRect() trên từng ảnh
   trong mỗi nhịp cuộn: với chương 51 trang, cách cũ là 51 lần buộc tính lại
   layout mỗi lần cuộn, ngay trên điện thoại. */
function watchPages() {
  state.observer?.disconnect();
  state.observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          updatePosition(Number(entry.target.dataset.idx));
          scheduleSave();
          break;
        }
      }
    },
    { rootMargin: "-10% 0px -80% 0px", threshold: 0 },
  );
  for (const img of pagesBox.children) state.observer.observe(img);
}

function updatePosition(index) {
  state.current = index;
  positionLabel.textContent = state.pages.length ? `${index + 1}/${state.pages.length}` : "";
}

let saveTimer = 0;
function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => {
    if (state.chapterId) {
      api.saveProgress(slug, state.chapterId, state.current).catch(() => {});
    }
  }, 900);
}

/* Thanh menu chi doi trang thai khi NGUOI DUNG CHAM, khong tu an theo dong ho va
   khong phan ung theo cuon: dang doc ma no tu bat tat thi vua giat mat vua kho bam. */
pagesBox.addEventListener("click", () => {
  document.body.dataset.chrome =
    document.body.dataset.chrome === "hidden" ? "shown" : "hidden";
});

function step(delta) {
  const ids = state.manga.chapters.map((chapter) => chapter.id);
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

document.getElementById("theme").addEventListener("click", toggleTheme);

// Chương đang tải dở: khi worker báo xong thì nạp lại danh sách trang.
subscribeEvents((event) => {
  if (event.phase === "done" && event.slug === slug && state.chapterId) {
    openChapter(state.chapterId, state.current).catch(() => {});
  }
});
