// Thư viện: lưới bìa, tìm kiếm, lọc thể loại ba trạng thái, lọc theo tác giả.
import { api, el, markCurrentNav } from "./api.js";

markCurrentNav();

const grid = document.getElementById("grid");
const filters = document.getElementById("filters");
const countLine = document.getElementById("count");
const moreButton = document.getElementById("more");
const search = document.getElementById("q");

const params = new URLSearchParams(location.search);
const state = {
  q: params.get("q") || "",
  author: params.get("author") || null,
  tagStates: new Map(), // tên -> 1 (bắt buộc có) | 2 (loại trừ)
  page: 1,
  perPage: 40,
  total: 0,
};
search.value = state.q;

function tagsParam(wanted) {
  return [...state.tagStates.entries()]
    .filter(([, value]) => value === wanted)
    .map(([name]) => name)
    .join(",");
}

function card(item) {
  const progress = item.progress;
  const cover = item.cover
    ? el("img", { src: item.cover, alt: "", loading: "lazy", decoding: "async" })
    : el("div", { class: "empty", text: "chưa có bìa" });

  const inner = [cover];
  if (item.chapter_count) {
    inner.push(el("div", { class: "badge", text: `${item.chapter_count} ch` }));
  }
  if (progress && progress.ratio > 0) {
    inner.push(
      el("div", { class: "progress" }, [
        el("i", { style: `width:${Math.min(100, Math.round(progress.ratio * 100))}%` }),
      ]),
    );
  }

  const byline = item.authors.length
    ? el("div", { class: "by" }, [
        el("a", {
          href: `index.html?author=${encodeURIComponent(item.authors[0].name)}`,
          text: item.authors[0].name,
          title: "Xem truyện khác của tác giả này",
        }),
      ])
    : null;

  return el(
    "a",
    {
      class: "card",
      href: `reader.html?slug=${encodeURIComponent(item.slug)}`,
      title: item.title,
    },
    [
      el("div", { class: "cover" }, inner),
      el("div", { class: "meta" }, [
        el("div", { class: "title", text: item.title }),
        byline,
        el(
          "div",
          { class: "tags" },
          item.tags.slice(0, 2).map((name) => el("span", { text: name })),
        ),
      ]),
    ],
  );
}

async function renderChips() {
  const tags = await api.tags();
  filters.replaceChildren();

  if (state.author) {
    filters.append(
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
    filters.append(chip);
  }
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

  state.total = data.total;
  if (!append) grid.replaceChildren();
  for (const item of data.items) grid.append(card(item));

  if (!data.total) {
    countLine.textContent = "Thư viện trống. Dán một link ở tab Tải về để bắt đầu.";
  } else {
    countLine.textContent = `${grid.children.length} / ${data.total} truyện`;
  }
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

renderChips().catch(() => {});
reload();
