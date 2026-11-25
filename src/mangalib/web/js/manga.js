// Trang chi tiết truyện: giới thiệu, nút đọc, danh sách chương, và các việc phụ
// trong menu "…" (sửa thông tin, sắp xếp, xoá).
import { api, el, icon, markCurrentNav } from "./api.js";

markCurrentNav();

const slug = new URLSearchParams(location.search).get("slug");
const hero = document.getElementById("hero");
const titleBox = document.getElementById("title");
const factsBox = document.getElementById("facts");
const tagsBox = document.getElementById("tags");
const readButton = document.getElementById("read");
const menuButton = document.getElementById("menu");
const msgBox = document.getElementById("msg");
const editor = document.getElementById("editor");
const chaptersPanel = document.getElementById("chapters-panel");
const chaptersBox = document.getElementById("chapters");
const chapterCount = document.getElementById("chapter-count");
const sorter = document.getElementById("sorter");

const state = { manga: null, sorting: false, drag: null };

function say(text, bad = false) {
  msgBox.textContent = text;
  msgBox.hidden = !text;
  msgBox.dataset.bad = bad ? "1" : "0";
}

function readerUrl(chapterId) {
  const base = `reader.html?slug=${encodeURIComponent(slug)}`;
  return chapterId ? `${base}&chapter=${chapterId}` : base;
}

// ---------- vẽ ----------
function renderHero(manga) {
  document.title = `${manga.title} · Comic Library`;
  titleBox.textContent = manga.title;

  if (manga.cover && !document.getElementById("cover")) {
    hero.prepend(
      el("img", { class: "hero-cover", id: "cover", src: manga.cover, alt: `Bìa ${manga.title}` }),
    );
  }

  // Trường nào không có thì KHÔNG hiện dòng trống — nhiều site không ghi tác giả.
  const facts = [];
  if (manga.authors.length) {
    facts.push(["Tác giả", manga.authors.map((a) => a.name).join(", ")]);
  }
  facts.push(["Đã tải", `${manga.chapter_count} chương · ${manga.page_count} trang`]);
  if (manga.source_url) facts.push(["Nguồn", new URL(manga.source_url).hostname]);
  factsBox.replaceChildren(
    ...facts.flatMap(([k, v]) => [el("dt", { text: k }), el("dd", { text: v })]),
  );

  tagsBox.hidden = manga.tags.length === 0;
  tagsBox.replaceChildren(
    ...manga.tags.map((name) =>
      el("a", { class: "tag-chip", text: name, href: `index.html?tag=${encodeURIComponent(name)}` }),
    ),
  );

  const progress = manga.progress;
  const first = manga.chapters[0];
  if (progress) {
    readButton.textContent = `Đọc tiếp — chương ${progress.chapter_index}/${progress.chapter_total}, trang ${progress.page_pos}/${progress.chapter_pages}`;
    readButton.href = readerUrl(progress.chapter_id);
  } else {
    readButton.textContent = "Bắt đầu đọc";
    readButton.href = readerUrl(first?.id);
  }
  readButton.classList.toggle("disabled", !first);
  hero.hidden = false;
}

function chapterRow(chapter, index) {
  const thieu = chapter.status === "partial" || chapter.status === "failed";
  const children = [
    el("span", { class: "ch-no", text: chapter.number === null ? "—" : `${chapter.number}` }),
    el("span", { class: "ch-title", text: chapter.title }),
  ];
  // Pill truoc, so trang sau: so trang luon o cuoi nen cac hang thang cot.
  if (thieu) {
    children.push(el("span", { class: "pill", "data-s": "warn", text: "thiếu ảnh" }));
  }
  children.push(el("span", { class: "ch-pages", text: `${chapter.page_count} trang` }));

  if (!state.sorting) {
    return el("li", { class: "ch" }, [
      el("a", { class: "ch-link", href: readerUrl(chapter.id) }, children),
    ]);
  }

  // Icon SVG chu khong phai ky tu Unicode: Windows ve ↑ ↓ ✕ bang font emoji nen
  // chung ra MAU va lech duong co so - dung loi da sua o cho khac trong app.
  const nut = (ten, nhan, chay) => {
    const b = el("button", { class: "ghost iconbtn", title: nhan, "aria-label": nhan, onclick: chay });
    b.append(icon(ten, { size: 16 }));
    return b;
  };
  children.push(
    el("span", { class: "ch-tools" }, [
      nut("up", "Lên", () => move(index, -1)),
      nut("down", "Xuống", () => move(index, 1)),
      nut("close", "Xoá chương này", () => removeChapter(chapter)),
    ]),
  );
  const row = el("li", { class: "ch", draggable: "true" }, [el("div", { class: "ch-link" }, children)]);
  row.addEventListener("dragstart", () => {
    state.drag = index;
  });
  row.addEventListener("dragover", (event) => event.preventDefault());
  row.addEventListener("drop", (event) => {
    event.preventDefault();
    if (state.drag !== null && state.drag !== index) moveTo(state.drag, index);
    state.drag = null;
  });
  return row;
}

function renderChapters() {
  const list = state.manga.chapters;
  chapterCount.textContent = list.length ? `${list.length} chương` : "";
  sorter.hidden = !state.sorting;
  chaptersBox.replaceChildren(
    ...(list.length
      ? list.map(chapterRow)
      : [el("li", { class: "empty-state", text: "Truyện này chưa có chương nào." })]),
  );
  chaptersPanel.hidden = false;
}

// ---------- sắp xếp ----------
function moveTo(from, to) {
  const list = state.manga.chapters;
  list.splice(to, 0, ...list.splice(from, 1));
  renderChapters();
  saveOrder();
}

function move(index, delta) {
  const to = index + delta;
  if (to < 0 || to >= state.manga.chapters.length) return;
  moveTo(index, to);
}

function sortBy(dir) {
  const key = (c) => (c.number === null ? Number.POSITIVE_INFINITY : c.number);
  state.manga.chapters.sort((a, b) => (key(a) - key(b)) * dir || a.title.localeCompare(b.title) * dir);
  renderChapters();
  saveOrder();
}

async function saveOrder() {
  try {
    await api.setChapterOrder(slug, state.manga.chapters.map((c) => c.id));
    say("Đã lưu thứ tự.");
  } catch (error) {
    say(`Không lưu được thứ tự: ${error.message}`, true);
  }
}

// ---------- việc phụ ----------
async function removeChapter(chapter) {
  if (!confirm(`Xoá "${chapter.title}" khỏi thư viện?\n\nẢnh vẫn nằm trên đĩa, chỉ ẩn khỏi danh sách.`)) {
    return;
  }
  try {
    await api.deleteChapter(slug, chapter.id);
    state.manga.chapters = state.manga.chapters.filter((c) => c.id !== chapter.id);
    renderChapters();
    say("Đã xoá chương.");
  } catch (error) {
    say(`Không xoá được: ${error.message}`, true);
  }
}

async function removeManga() {
  if (!confirm(`Xoá "${state.manga.title}" khỏi thư viện?\n\nẢnh vẫn nằm trên đĩa, chỉ ẩn khỏi thư viện.`)) {
    return;
  }
  try {
    await api.deleteManga(slug);
    location.href = "index.html";
  } catch (error) {
    say(`Không xoá được: ${error.message}`, true);
  }
}

function openEditor() {
  document.getElementById("f-title").value = state.manga.title;
  document.getElementById("f-authors").value = state.manga.authors.map((a) => a.name).join(", ");
  document.getElementById("f-tags").value = state.manga.tags.join(", ");
  editor.hidden = false;
  document.getElementById("f-title").focus();
}

const split = (value) => value.split(",").map((x) => x.trim()).filter(Boolean);

editor.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const saved = await api.editManga(slug, {
      title: document.getElementById("f-title").value,
      authors: split(document.getElementById("f-authors").value),
      tags: split(document.getElementById("f-tags").value),
    });
    Object.assign(state.manga, saved);
    renderHero(state.manga);
    editor.hidden = true;
    say("Đã lưu thông tin.");
  } catch (error) {
    say(`Không lưu được: ${error.message}`, true);
  }
});

document.getElementById("cancel").addEventListener("click", () => {
  editor.hidden = true;
});
document.getElementById("sort-az").addEventListener("click", () => sortBy(1));
document.getElementById("sort-za").addEventListener("click", () => sortBy(-1));

menuButton.addEventListener("click", () => {
  const open = document.getElementById("more-menu");
  if (open) {
    open.remove();
    menuButton.setAttribute("aria-expanded", "false");
    return;
  }
  const item = (text, run) =>
    el("button", { class: "ghost", text, onclick: () => {
      document.getElementById("more-menu")?.remove();
      menuButton.setAttribute("aria-expanded", "false");
      run();
    } });
  menuButton.setAttribute("aria-expanded", "true");
  menuButton.after(
    el("div", { class: "more-menu", id: "more-menu" }, [
      item("Sửa thông tin", openEditor),
      item(state.sorting ? "Xong, thôi sắp xếp" : "Sắp xếp chương", () => {
        state.sorting = !state.sorting;
        renderChapters();
      }),
      item("Xoá truyện này", removeManga),
    ]),
  );
});

// ---------- khởi động ----------
if (!slug) {
  titleBox.textContent = "Thiếu tham số ?slug=";
  hero.hidden = false;
} else {
  api
    .manga(slug)
    .then((manga) => {
      state.manga = manga;
      renderHero(manga);
      renderChapters();
    })
    .catch((error) => {
      hero.hidden = false;
      titleBox.textContent = "Không mở được truyện";
      say(error.message, true);
    });
}
