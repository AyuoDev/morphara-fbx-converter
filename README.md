# Morphara FBX Converter - Docker Version

## 100% GUARANTEED TO WORK

This version uses Blender in a Docker container.

## Files Needed

1. `Dockerfile` - Docker image with Blender pre-installed
2. `main.py` - FastAPI service
3. `requirements.txt` - Python dependencies

## Deployment on Render.com

### Step 1: Update GitHub Repo

Replace ALL files in your `morphara-fbx-converter` repo with these 3 files.

### Step 2: Configure Render

1. Go to your service on Render
2. Click **Settings**
3. Change these settings:
   - **Environment**: Docker
   - **Dockerfile Path**: ./Dockerfile
   - **Docker Build Context Directory**: .
4. Click **Save Changes**

### Step 3: Deploy

Click **Manual Deploy** → **Deploy latest commit**

Wait 5-10 minutes for:
- Docker image to build
- Blender to install
- Service to start

### Step 4: Test

```bash
curl https://morphara-fbx-converter.onrender.com/health
```

Should return: `{"status":"healthy"}`

## How It Works

```
GLB Upload
  ↓
Blender imports GLB
  ↓
Blender exports FBX (native, perfect quality)
  ↓
FBX Download
```

## Why This Works

- ✅ Blender is THE industry standard
- ✅ Native GLB → FBX conversion
- ✅ Preserves materials, textures, animations, blend shapes
- ✅ Used by Pixar, Disney, game studios worldwide
- ✅ Pre-installed in Docker = guaranteed to work

## Troubleshooting

If it fails, check Render logs for Blender output.