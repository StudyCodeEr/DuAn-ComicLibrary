// Hàng đợi tải + nhật ký realtime qua SSE.
import { api, el, markCurrentNav, subscribeEvents } from "./api.js";

markCurrentNav();

const jobsBox = document.getElementById("jobs");
const logBox = document.getElementById("log");
const urlInput = document.getElementById("url");
const submitButton = document.getElementById("submit");

const STATE_LABEL = {
  queued: "trong hàng đợi",
  running: "đang chạy",
  done: "xong",
  failed: "thất bại",
  cancelled: "đã huỷ",
  needs_login: "cần đăng nhập thủ công",
};

function logLine(event) {
  const phase = event.phase || "";
  if (phase === "ping" || phase === "connected") return;
  const line = el("div", {}, [
    el("span", { class: "p", text: `[${phase}] ` }),
    document.createTextNode(event.message || ""),
  ]);
  logBox.append(line);
  logBox.scrollTop = logBox.scrollHeight;
  while (logBox.children.length > 400) logBox.firstChild.remove();
}

function jobRow(job) {
  const children = [
    el("div", { class: "row" }, [
      el("span", { class: "state", "data-s": job.state, text: STATE_LABEL[job.state] || job.state }),
      el("span", { class: "spacer", style: "flex:1" }),
      job.total ? el("span", { class: "pos", text: `${job.done}/${job.total} trang` }) : null,
      ["queued", "running", "needs_login"].includes(job.state)
        ? el("button", {
            class: "ghost",
            text: "Huỷ",
            onclick: async () => {
              await api.cancelJob(job.id);
              refresh();
            },
          })
        : null,
    ]),
    el("div", { class: "url", text: job.url }),
  ];
  if (job.error) children.push(el("div", { class: "err", text: job.error }));
  return el("div", { class: "job" }, children);
}

async function refresh() {
  try {
    const jobs = await api.jobs(false);
    jobsBox.replaceChildren(
      ...(jobs.length ? jobs.map(jobRow) : [el("div", { class: "count", text: "Chưa có việc nào." })]),
    );
  } catch (error) {
    jobsBox.replaceChildren(el("div", { class: "err", text: error.message }));
  }
}

async function submit() {
  const url = urlInput.value.trim();
  if (!url) return;
  submitButton.disabled = true;
  try {
    await api.createJob(url);
    urlInput.value = "";
    await refresh();
  } catch (error) {
    logLine({ phase: "lỗi", message: error.message });
  } finally {
    submitButton.disabled = false;
  }
}

submitButton.addEventListener("click", submit);
urlInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") submit();
});

subscribeEvents((event) => {
  logLine(event);
  if (["queued", "done", "failed", "cancelled"].includes(event.phase)) refresh();
});

refresh();
setInterval(refresh, 10_000);
