import { createAssimp } from "libassimp";
import { zipSync } from "fflate";

let assimpPromise;
let activeRequest = null;

function getAssimp() {
  if (!assimpPromise) {
    assimpPromise = createAssimp({ backend: "wasm", recycleAboveBytes: 536870912 });
  }
  return assimpPromise;
}

function normalizePath(value) {
  const decoded = decodeURIComponent(value.replaceAll("\\", "/"));
  const parts = [];
  for (const part of decoded.split("/")) {
    if (!part || part === ".") continue;
    if (part === "..") parts.pop();
    else parts.push(part);
  }
  return parts.join("/");
}

function safeZipPath(value) {
  const clean = normalizePath(value).split("/").filter(part => part && part !== ".." && !part.includes(":"));
  return clean.length ? clean.join("/") : "character.fbx";
}

function sendProgress(id, title, detail, percent) {
  self.postMessage({ type: "progress", id, title, detail, percent });
}

self.onmessage = async event => {
  const message = event.data;
  if (message.type === "cancel") {
    activeRequest = null;
    self.postMessage({ type: "cancelled", id: message.id });
    return;
  }
  if (message.type !== "convert") return;

  const { id, entryName, files } = message;
  activeRequest = id;
  try {
    sendProgress(id, "Loading converter", "The conversion engine is being prepared in this browser.", 3);
    const assimp = await getAssimp();
    if (activeRequest !== id) return;

    const byPath = new Map();
    const byName = new Map();
    const inputs = files.map(file => {
      const record = { name: file.name, bytes: new Uint8Array(file.buffer) };
      byPath.set(normalizePath(file.name).toLowerCase(), record.bytes);
      const basename = normalizePath(file.name).split("/").pop().toLowerCase();
      if (!byName.has(basename)) byName.set(basename, record.bytes);
      return record;
    });
    const entry = inputs.find(file => normalizePath(file.name).toLowerCase() === normalizePath(entryName).toLowerCase());
    if (!entry) throw new Error("Select one GLB or GLTF file as the main model.");

    sendProgress(id, "Converting model", "Importing the scene and writing an FBX file.", 8);
    const result = await assimp.convert(entry, {
      to: "fbx",
      exportOptions: { binary: true },
      resolve: async name => {
        const normalized = normalizePath(name).toLowerCase();
        const relative = normalizePath(`${normalizePath(entry.name).split("/").slice(0, -1).join("/")}/${name}`).toLowerCase();
        return byPath.get(relative) || byPath.get(normalized) || byName.get(normalized.split("/").pop());
      },
      onProgress: progress => {
        if (activeRequest !== id) return;
        if (progress.phase === "import") {
          const ratio = progress.total ? Math.round((progress.step / progress.total) * 20) : 8;
          sendProgress(id, "Reading model", "Loading mesh, material, and scene data.", 8 + ratio);
        } else if (progress.phase === "postProcess") {
          sendProgress(id, "Preparing scene", "Preparing model data for FBX output.", 35 + Math.round((progress.step / Math.max(progress.total, 1)) * 20));
        } else {
          sendProgress(id, "Writing FBX", "Building the FBX file and sidecar textures.", 58 + Math.round((progress.step / Math.max(progress.total, 1)) * 37));
        }
      }
    });
    if (activeRequest !== id) return;
    if (!result.files.length) throw new Error("The converter finished without producing an FBX file.");

    const archive = {};
    for (const file of result.files) archive[safeZipPath(file.name)] = file.bytes;
    const zip = zipSync(archive, { level: 1 });
    if (activeRequest !== id) return;

    sendProgress(id, "Package ready", "Your model has been converted on this device.", 100);
    const buffer = zip.buffer.slice(zip.byteOffset, zip.byteOffset + zip.byteLength);
    self.postMessage({ type: "complete", id, buffer, files: result.files.map(file => file.name), warnings: result.warnings.map(warning => warning.message) }, [buffer]);
  } catch (error) {
    if (activeRequest === id) {
      self.postMessage({ type: "error", id, message: error?.message || "Conversion failed. Try another GLB or GLTF file." });
    }
  } finally {
    if (activeRequest === id) activeRequest = null;
  }
};
