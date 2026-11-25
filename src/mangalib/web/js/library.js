// Thư viện: dải "Đọc tiếp", lưới bìa, tìm kiếm, lọc thể loại ba trạng thái.
import { api, el, markCurrentNav } from "./api.js";

markCurrentNav();

const grid = document.getElementById("grid");
const filters = document.getElementById("filters");
const countLine = document.getElementById("count");
const moreButton = document.getElementById("more");
const search = document.getElementById("q");
const continueBox = document.getElementById("continue");
const continueStrip = document.getElementById("strip");

const params = new URLSearchParams(location.search);
const state = {
  q: params.get("q") || "",
  author: params.get("author") || null,
  tagStates: new Map(), // tên -> 1 (bắt buộc có) | 2 (loại trừ)
  page: 1,
  perPage: 40,
};
search.value = state.q;

const FINISHED = 0.999;

function tagsParam(wanted) {
  return [...state.tagStates.entries()]
    .filter(([, value]) => value === wanted)
    .map(([name]) => name)
    .join(",");
}

function coverNode(item, alt = "") {
  return item.cover
    ? el("img", { src: item.cover, alt, loading: "lazy", decoding: "async" })
    : el("div", { class: "empty", text: "chưa có bìa" });
}

/* Tiến độ có ba trạng thái phân biệt được, không phải một dải bật/tắt:
   chưa đọc · đang đọc (chương mấy) · đã đọc hết. */
function progressFacts(item) {
  const progress = item.progress;
  if (!progress) return { label: "Chưa đọc", ratio: 0, done: false };
  if (progress.ratio >= FINISHED) return { label: "Đã đọc hết", ratio: 1, done: true };
  const where = progress.chapter_title ? `Đang đọc · ${progress.chapter_title}` : "Đang đọc";
  return { label: where, ratio: progress.ratio, done: false };
}

function card(item) {
  const facts = progressFacts(item);
  const inner = [coverNode(item)];

  // Badge mang CẢ số chương và số trang: người dùng nói cả hai phải thấy ngay.
  inner.push(
    el("div", {
      class: "badge",
      text: `${item.chapter_count} ch · ${item.page_count} tr`,
      title: `${item.chapter_count} chương, ${item.page_count} trang`,
    }),
  );

  if (facts.ratio > 0) {
    inner.push(
      el("div", { class: "progress", "data-done": facts.done ? "1" : "0" }, [
        el("i", { style: `width:${Math.min(100, Math.round(facts.ratio * 100))}%` }),
      ]),
    );
  }

  return el(
    "a",
    { class: "card", href: `reader.html?slug=${encodeURIComponent(item.slug)}`, title: item.title },
    [
      el("div", { class: "cover" }, inner),
      el("div", { class: "meta" }, [
        el("div", { class: "title", text: item.title }),
        el("div", { class: "stat" }, [
          el("b", { "data-done": facts.done ? "1" : "0", text: facts.label }),
        ]),
        el(
          "div",
          { class: "tags" },
          item.tags.slice(0, 2).map((name) => el("span", { text: name })),
        ),
      ]),
    ],
  );
}

function resumeCard(item) {
  const facts = progressFacts(item);
  return el(
    "a",
    { class: "resume", href: `reader.html?slug=${encodeURIComponent(item.slug)}`, title: item.title },
    [
      coverNode(item),
      el("div", { class: "body" }, [
        el("div", { class: "t", text: item.title }),
        el("div", { class: "c", text: facts.label }),
        el("div", { class: "go", text: "Đọc tiếp →" }),
      ]),
    ],
  );
}

/* Dải "Đọc tiếp": câu thứ hai của FIRST VIEWPORT, và là thứ phân biệt thư viện
   này với một bức tường poster — truyện dở nằm ngay trên cùng. */
async function renderContinue() {
  const data = await api.library({ sort: "last_read", per_page: 12 });
  const resuming = data.items.filter((item) => item.progress && item.progress.ratio < FINISHED);
  if (!resuming.length) {
    continueBox.hidden = true;
    return;
  }
  continueBox.hidden = false;
  continueStrip.replaceChildren(...resuming.map(resumeCard));
}

async function renderChips() {
  const tags = await api.tags();
  const chips = [];

  if (state.author) {
    chips.push(
      el("button", {
        class: "chip",
        "data-state": "1",
        text: `tác giả: ${state.author} ✕`,
        onclick: () => {
          state.author = null;
          reload();
          renderChips();
        },
      }),
    );
  }

  for (const tag of tags.slice(0, 30)) {
    const chip = el("button", {
      class: "chip",
      "data-state": String(state.tagStates.get(tag.name) || 0),
      title: "Bấm để: bắt buộc có → loại trừ → bỏ qua",
    });
    chip.append(document.createTextNode(tag.name), el("span", { class: "n", text: tag.count }));
    chip.addEventListener("click", () => {
      const next = ((state.tagStates.get(tag.name) || 0) + 1) % 3;
      if (next === 0) state.tagStates.delete(tag.name);
      else state.tagStates.set(tag.name, next);
      chip.dataset.state = String(next);
      reload();
    });
    chips.push(chip);
  }
  filters.replaceChildren(...chips);
}

async function load({ append = false } = {}) {
  const data = await api.library({
    q: state.q,
    include_tags: tagsParam(1),
    exclude_tags: tagsParam(2),
    ...(state.author ? { author: state.author } : {}),
    page: state.page,
    per_page: state.perPage,
  });

  if (!append) grid.replaceChildren();
  for (const item of data.items) grid.append(card(item));

  countLine.textContent = data.total
    ? `${grid.children.length} / ${data.total} truyện`
    : "Thư viện trống. Dán một link ở tab Tải về để bắt đầu.";
  moreButton.hidden = grid.children.length >= data.total;
}

function reload() {
  state.page = 1;
  load().catch((error) => {
    countLine.textContent = `Lỗi: ${error.message}`;
  });
}

let typingTimer = 0;
search.addEventListener("input", () => {
  clearTimeout(typingTimer);
  typingTimer = setTimeout(() => {
    state.q = search.value.trim();
    reload();
  }, 250);
});

moreButton.addEventListener("click", () => {
  state.page += 1;
  load({ append: true });
});

renderContinue().catch(() => {
  continueBox.hidden = true;
});
renderChips().catch(() => {});
reload();
