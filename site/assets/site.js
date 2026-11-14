document.documentElement.classList.add("js");

const demo = document.querySelector(".demo");
const layouts = [...document.querySelectorAll(".demo-controls button")];
for (const button of layouts) {
  button.addEventListener("click", () => {
    demo.dataset.layout = button.dataset.layout;
    for (const other of layouts)
      other.setAttribute("aria-pressed", String(other === button));
    document.querySelector(".demo-shortcut kbd").textContent =
      button.dataset.shortcut;
  });
}

const download = document.querySelector(".download-button");
const status = document.querySelector(".download-status");
const command = document.querySelector("#install-command");
const copy = document.querySelector(".copy-command");
const initialCommand = command.textContent;
const copyLabel = copy.textContent;
let copyTimer;

function updateDownload() {
  const ubuntu = document.querySelector('input[name="ubuntu"]:checked').value;
  command.textContent = initialCommand.replace(
    "ubuntu24.04",
    `ubuntu${ubuntu}`,
  );
  download.href =
    ubuntu === "24.04" ? download.dataset.deb24 : download.dataset.deb26;
}
for (const radio of document.querySelectorAll('input[name="ubuntu"]'))
  radio.addEventListener("change", updateDownload);
copy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(command.textContent);
    copy.textContent = copy.dataset.copied;
    clearTimeout(copyTimer);
    copyTimer = setTimeout(() => {
      copy.textContent = copyLabel;
    }, 2000);
  } catch {
    status.textContent = copy.dataset.copyFailed;
  }
});
updateDownload();
