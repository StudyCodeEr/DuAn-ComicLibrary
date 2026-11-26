// Cài đặt: ghép đôi điện thoại, userscript, đường dẫn thật.
import { api, el, markCurrentNav } from "./api.js";

markCurrentNav();

const infoBox = document.getElementById("info");
const libPath = document.getElementById("libpath");
const imgFormat = document.getElementById("imgfmt");
const saveButton = document.getElementById("save");
const browseButton = document.getElementById("browse");
const saveMessage = document.getElementById("savemsg");
const autostartBox = document.getElementById("f-autostart");
const closeSelect = document.getElementById("f-close");
const startMessage = document.getElementById("startmsg");
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

    libPath.value = data.library_override || "";
    imgFormat.value = data.image_format;
    autostartBox.checked = data.autostart;
    closeSelect.value = data.close_action;

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

browseButton.addEventListener("click", async () => {
  // Hop thoai chan cho toi khi nguoi dung dong, nen khoa nut de khong mo chong nhau.
  browseButton.disabled = true;
  saveMessage.textContent = "Đang mở hộp thoại chọn thư mục…";
  try {
    const { path } = await api.pickFolder();
    if (path) {
      libPath.value = path;
      saveMessage.textContent = "Đã chọn. Bấm Lưu để áp dụng.";
    } else {
      saveMessage.textContent = "Bạn đã huỷ, chưa đổi gì.";
    }
  } catch (error) {
    saveMessage.textContent = `Không mở được hộp thoại: ${error.message}`;
  } finally {
    browseButton.disabled = false;
  }
});

// Hai thiet lap nay la cong tac: luu ngay khi doi, khong bat bam them nut Luu.
async function luuNgay(body, loiNhan) {
  // Bao ngay trong panel nay, khong day xuong dong thong bao cua panel duoi.
  startMessage.hidden = false;
  try {
    const saved = await api.saveSettings(body);
    autostartBox.checked = saved.autostart;
    startMessage.textContent = loiNhan;
    startMessage.dataset.bad = "0";
  } catch (error) {
    startMessage.textContent = `Không lưu được: ${error.message}`;
    startMessage.dataset.bad = "1";
  }
}

autostartBox.addEventListener("change", () =>
  luuNgay(
    { autostart: autostartBox.checked },
    autostartBox.checked ? "Đã bật khởi động cùng Windows." : "Đã tắt khởi động cùng Windows.",
  ),
);

closeSelect.addEventListener("change", () =>
  luuNgay(
    { close_action: closeSelect.value },
    "Đã lưu. Có hiệu lực từ lần mở ứng dụng sau.",
  ),
);

saveButton.addEventListener("click", async () => {
  saveButton.disabled = true;
  saveMessage.textContent = "Đang lưu…";
  try {
    const saved = await api.saveSettings({
      library_override: libPath.value.trim(),
      image_format: imgFormat.value,
    });
    saveMessage.textContent = `Đã lưu. Truyện sẽ lưu vào: ${saved.library_dir}`;
    // Doc lai de o thong tin ben duoi khop voi cai vua ghi, khong phai tai lai trang.
    const fresh = await api.settings();
    pairs(infoBox, [
      ["Thư mục dữ liệu", fresh.data_root],
      ["Thư viện truyện", fresh.library_dir],
      ["Định dạng ảnh", fresh.image_format === "original" ? "giữ nguyên bản gốc" : fresh.image_format],
      ["Tải song song", `${fresh.concurrency} ảnh mỗi lúc`],
    ]);
  } catch (error) {
    saveMessage.textContent = `Không lưu được: ${error.message}`;
  } finally {
    saveButton.disabled = false;
  }
});

const themeButton = document.getElementById("theme");
const saved = localStorage.getItem("mlib.theme");
if (saved) document.documentElement.dataset.theme = saved;
themeButton.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
  document.documentElement.dataset.theme = next;
  localStorage.setItem("mlib.theme", next);
});
