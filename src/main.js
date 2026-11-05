import "./style.css";

const input = document.querySelector("#model-files");
const folderInput = document.querySelector("#model-folder");
const dropZone = document.querySelector("#drop-zone");
const selection = document.querySelector("#selection");
const fileList = document.querySelector("#file-list");
const selectionSummary = document.querySelector("#selection-summary");
const convertButton = document.querySelector("#convert-button");
const progressPanel = document.querySelector("#progress-panel");
const resultPanel = document.querySelector("#result-panel");
const errorMessage = document.querySelector("#error-message");
const progressTitle = document.querySelector("#progress-title");
const progressDetail = document.querySelector("#progress-detail");
const progressPercent = document.querySelector("#progress-percent");
const progressFill = document.querySelector("#progress-fill");
const resultDetail = document.querySelector("#result-detail");
const downloadButton = document.querySelector("#download-button");
const adConsent = document.querySelector("#ad-consent");
const adSlot = document.querySelector("#ad-slot");
const adConsentKey = "morphara-ad-consent-v1";
const MAX_TOTAL_BYTES = 50 * 1024 * 1024;

function loadAd() {
  const script = document.createElement("script");
  script.src = "https://pl28869091.profitableratecpmnetwork.com/f8/01/fa/f801fa4c6aae2920887cb8637d49839d.js";
  document.querySelector("#adsterra-ad-slot").append(script);
  adSlot.hidden = false;
}

function chooseAdPreference(value) {
  const previous = localStorage.getItem(adConsentKey);
  localStorage.setItem(adConsentKey, value);
  adConsent.close();
  if (value === "accepted") loadAd();
  else if (previous === "accepted") window.location.reload();
}

const savedAdConsent = localStorage.getItem(adConsentKey);
if (savedAdConsent === "accepted") loadAd();
else if (savedAdConsent !== "rejected") adConsent.showModal();

document.querySelector("#allow-ads").addEventListener("click", () => chooseAdPreference("accepted"));
document.querySelector("#decline-ads").addEventListener("click", () => chooseAdPreference("rejected"));
document.querySelector("#ad-preferences").addEventListener("click", () => {
  adConsent.showModal();
});

let files = [];
let entryIndex = -1;
let worker = null;
let requestId = 0;
let outputUrl = null;

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function normalizeFilePath(file) {
  return (file.webkitRelativePath || file.name).replaceAll("\\", "/");
}

function resetOutput() {
  resultPanel.classList.add("hidden");
  errorMessage.classList.add("hidden");
  if (outputUrl) URL.revokeObjectURL(outputUrl);
  outputUrl = null;
}

function renderFiles() {
  fileList.replaceChildren();
  const total = files.reduce((sum, file) => sum + file.size, 0);
  const models = files.map((file, index) => ({ file, index })).filter(item => /\.(glb|gltf)$/i.test(item.file.name));
  if (entryIndex < 0 || !models.some(item => item.index === entryIndex)) entryIndex = models[0]?.index ?? -1;

  for (const { file, index } of files.map((file, index) => ({ file, index }))) {
    const row = document.createElement("li");
    row.className = "file-row";
    const isModel = /\.(glb|gltf)$/i.test(file.name);
    const entry = isModel ? document.createElement("button") : document.createElement("span");
    entry.className = `file-entry${index === entryIndex ? " active" : ""}`;
    if (isModel) {
      entry.type = "button";
      entry.setAttribute("aria-pressed", String(index === entryIndex));
      entry.title = "Use this file as the main model";
      entry.addEventListener("click", () => {
        entryIndex = index;
        renderFiles();
      });
      entry.textContent = index === entryIndex ? "MODEL" : "SET MODEL";
    } else {
      entry.textContent = "FILE";
    }
    const name = document.createElement("span");
    name.className = "file-name";
    name.title = normalizeFilePath(file);
    name.textContent = normalizeFilePath(file);
    const size = document.createElement("span");
    size.className = "file-size";
    size.textContent = formatBytes(file.size);
    row.append(entry, name, size);
    fileList.append(row);
  }

  const tooLarge = total > MAX_TOTAL_BYTES;
  const hasModel = entryIndex >= 0;
  selectionSummary.textContent = `${files.length} file${files.length === 1 ? "" : "s"} · ${formatBytes(total)} total${tooLarge ? " · 50 MB maximum" : ""}`;
  convertButton.disabled = !hasModel || tooLarge || !files.length;
  selection.classList.toggle("hidden", !files.length);
  dropZone.classList.toggle("compact", !!files.length);
}

function addFiles(selectedFiles) {
  resetOutput();
  const incoming = Array.from(selectedFiles || []);
  const supported = incoming.filter(file => /\.(glb|gltf|bin|png|jpe?g|webp|ktx2)$/i.test(file.name));
  if (!supported.length) {
    showError("Choose a GLB or GLTF model. GLTF companion data and texture files can be selected alongside it.");
    return;
  }
  const map = new Map(files.map(file => [normalizeFilePath(file).toLowerCase(), file]));
  for (const file of supported) map.set(normalizeFilePath(file).toLowerCase(), file);
  files = Array.from(map.values());
  const found = files.findIndex(file => /\.(glb|gltf)$/i.test(file.name));
  if (found >= 0 && (entryIndex < 0 || !/\.(glb|gltf)$/i.test(files[entryIndex]?.name || ""))) entryIndex = found;
  progressPanel.classList.add("hidden");
  renderFiles();
  if (files.reduce((sum, file) => sum + file.size, 0) > MAX_TOTAL_BYTES) showError("The selected files are over the 50 MB total limit. Remove some files or choose a smaller model.");
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.classList.remove("hidden");
}

function setProgress(message) {
  progressTitle.textContent = message.title;
  progressDetail.textContent = message.detail;
  const percent = Math.max(0, Math.min(100, message.percent || 0));
  progressPercent.textContent = `${percent}%`;
  progressFill.style.width = `${percent}%`;
}

function getWorker() {
  if (!worker) {
    worker = new Worker(new URL("./converter.worker.js", import.meta.url), { type: "module" });
    worker.addEventListener("message", onWorkerMessage);
    worker.addEventListener("error", event => {
      showError(event.message || "The browser could not start the conversion engine.");
      progressPanel.classList.add("hidden");
      convertButton.disabled = false;
    });
  }
  return worker;
}

function onWorkerMessage(event) {
  const message = event.data;
  if (message.id !== requestId) return;
  if (message.type === "progress") {
    setProgress(message);
    return;
  }
  progressPanel.classList.add("hidden");
  convertButton.disabled = false;
  if (message.type === "cancelled") return;
  if (message.type === "error") {
    showError(message.message);
    return;
  }
  if (message.type === "complete") {
    const blob = new Blob([message.buffer], { type: "application/zip" });
    outputUrl = URL.createObjectURL(blob);
    resultDetail.textContent = `${message.files.length} file${message.files.length === 1 ? "" : "s"} · ${formatBytes(blob.size)}${message.warnings.length ? " · review compatibility note" : ""}`;
    resultPanel.classList.remove("hidden");
    errorMessage.classList.add("hidden");
  }
}

document.querySelector("#browse-files").addEventListener("click", () => input.click());
document.querySelector("#browse-folder").addEventListener("click", () => folderInput.click());
input.addEventListener("change", () => addFiles(input.files));
folderInput.addEventListener("change", () => addFiles(folderInput.files));
document.querySelector("#clear-files").addEventListener("click", () => {
  files = [];
  entryIndex = -1;
  input.value = "";
  folderInput.value = "";
  resetOutput();
  errorMessage.classList.add("hidden");
  renderFiles();
});

dropZone.addEventListener("click", event => {
  if (event.target.closest("button")) return;
  input.click();
});
dropZone.addEventListener("keydown", event => {
  if (event.target !== dropZone || !["Enter", " "].includes(event.key)) return;
  event.preventDefault();
  input.click();
});
for (const eventName of ["dragenter", "dragover"]) dropZone.addEventListener(eventName, event => {
  event.preventDefault();
  dropZone.classList.add("dragging");
});
for (const eventName of ["dragleave", "drop"]) dropZone.addEventListener(eventName, event => {
  event.preventDefault();
  dropZone.classList.remove("dragging");
});
dropZone.addEventListener("drop", event => addFiles(event.dataTransfer.files));

convertButton.addEventListener("click", async () => {
  if (entryIndex < 0 || convertButton.disabled) return;
  resetOutput();
  requestId += 1;
  const id = requestId;
  convertButton.disabled = true;
  progressPanel.classList.remove("hidden");
  errorMessage.classList.add("hidden");
  setProgress({ title: "Preparing converter", detail: "The conversion engine loads in your browser the first time you use it.", percent: 1 });
  try {
    const fileBuffers = await Promise.all(files.map(async file => ({ name: normalizeFilePath(file), buffer: await file.arrayBuffer() })));
    if (id !== requestId) return;
    const transfer = fileBuffers.map(file => file.buffer);
    getWorker().postMessage({ type: "convert", id, entryName: normalizeFilePath(files[entryIndex]), files: fileBuffers }, transfer);
  } catch {
    progressPanel.classList.add("hidden");
    convertButton.disabled = false;
    showError("The selected files could not be read. Check that the files are available and try again.");
  }
});

document.querySelector("#cancel-button").addEventListener("click", () => {
  requestId += 1;
  worker?.terminate();
  worker = null;
  progressPanel.classList.add("hidden");
  convertButton.disabled = false;
});

downloadButton.addEventListener("click", () => {
  if (!outputUrl) return;
  const entryName = files[entryIndex]?.name || "character.glb";
  const baseName = entryName.replace(/\.(glb|gltf)$/i, "").replace(/[^a-z0-9._-]+/gi, "_");
  const link = document.createElement("a");
  link.href = outputUrl;
  link.download = `${baseName || "character"}_fbx.zip`;
  document.body.append(link);
  link.click();
  link.remove();
});

window.addEventListener("beforeunload", () => {
  if (outputUrl) URL.revokeObjectURL(outputUrl);
  worker?.terminate();
});
