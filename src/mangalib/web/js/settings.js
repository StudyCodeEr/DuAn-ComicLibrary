// Cài đặt: ghép đôi điện thoại, userscript, đường dẫn thật.
import { api, el, markCurrentNav } from "./api.js";

markCurrentNav();

const infoBox = document.getElementById("info");
const lanBox = document.getElementById("lan");
const qrImage = document.getElementById("qr");

function pairs(target, entries) {
  target.replaceChildren();
  for (const [key, value] of entries) {
    target.append(el("dt", { text: key }), el("dd", { text: value }));
  }
}

api
  .settings()
  .then((data) => {
    const port = location.port || "8000";
    qrImage.src = `/api/v1/settings/qr.svg?port=${port}`;

    pairs(lanBox, [
      ["Địa chỉ cho điện thoại", data.lan_ips.length ? `http://${data.lan_ips[0]}:${port}` : "(không tìm thấy IP LAN)"],
      ["IP khác", data.lan_ips.slice(1).join(", ") || "—"],
      ["Token", `${data.lan_token.slice(0, 6)}… (đã nhúng trong QR)`],
    ]);

    pairs(infoBox, [
      ["Thư mục dữ liệu", data.data_root],
      ["Thư viện truyện", data.library_dir],
      ["Định dạng ảnh", data.image_format === "original" ? "giữ nguyên bản gốc" : data.image_format],
      ["Tải song song", `${data.concurrency} ảnh mỗi lúc`],
    ]);
  })
  .catch((error) => {
    pairs(infoBox, [["Lỗi", error.message]]);
  });

const themeButton = document.getElementById("theme");
const saved = localStorage.getItem("mlib.theme");
if (saved) document.documentElement.dataset.theme = saved;
themeButton.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("mlib.theme", next);
});
