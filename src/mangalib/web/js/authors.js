// Danh sách tác giả, bấm vào là lọc thư viện theo người đó.
import { api, el, markCurrentNav } from "./api.js";

markCurrentNav();

const peopleBox = document.getElementById("people");
const countLine = document.getElementById("count");
const filterInput = document.getElementById("q");

let everyone = [];

function render() {
  const needle = filterInput.value.trim().toLowerCase();
  const shown = needle
    ? everyone.filter((person) => person.name.toLowerCase().includes(needle))
    : everyone;

  peopleBox.replaceChildren(
    ...shown.map((person) =>
      el("a", { href: `index.html?author=${encodeURIComponent(person.name)}` }, [
        el("b", { text: person.name }),
        el("i", { text: `${person.count} truyện` }),
      ]),
    ),
  );
  countLine.textContent = everyone.length
    ? `${shown.length} / ${everyone.length} tác giả`
    : "Chưa có tác giả nào trong thư viện.";
}

api
  .authors()
  .then((data) => {
    everyone = data;
    render();
  })
  .catch((error) => {
    countLine.textContent = `Lỗi: ${error.message}`;
  });

filterInput.addEventListener("input", render);
