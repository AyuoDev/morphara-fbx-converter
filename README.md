# Morphara GLB to FBX Converter

Morphara's GLB-to-FBX tool is a static browser app. The conversion engine runs in a Web Worker in the visitor's browser. The model, companion files, and resulting ZIP are not sent to a conversion server.

## What happens during conversion

1. The browser reads the selected GLB or GLTF files locally.
2. A WebAssembly build of Assimp reads the scene and writes a binary FBX.
3. The browser packages the FBX and any generated sidecar files into a ZIP for download.

The Wasm engine is about 15 MB and is downloaded from the same site on first use. Browsers can cache it for later conversions. Conversion runs in a background Web Worker to keep the page responsive. The file picker accepts a 50 MB total selection. For GLTF files that reference external `.bin` or texture files, select those files too or choose the complete model folder.

## FBX compatibility

Assimp lists its FBX exporter as experimental. Basic geometry, materials, skeletons, and animation data can convert, but FBX output can differ by source file. Complex rigs, animation curves, morph targets, material features, and axis conventions may need correction in the target application. Review the exported file in Unity, Unreal, Blender, or the tool where it will be used. The converter does not promise a lossless round trip.

## Develop and build

Requirements: Node.js 20.19 or newer.

```sh
npm ci
npm run dev
npm run build
npm run preview
```

The static production site is written to `dist/`. It can be served by GitHub Pages or copied into the `fbx-converter/` directory of the Morphara website repository. No Python API, Docker container, or conversion server is required.

## Source layout

- `index.html` contains the converter interface and its privacy and compatibility explanation.
- `src/main.js` handles file selection, limits, progress, errors, and download.
- `src/converter.worker.js` runs the Wasm conversion and builds the ZIP.
- `src/style.css` contains the responsive interface styles.
- `vite.config.js` builds a static app with relative asset paths.

The production bundle includes the third-party notices under `public/`. Dependencies are pinned in `package-lock.json` for repeatable builds.
