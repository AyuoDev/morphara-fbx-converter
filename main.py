"""
Morphara FBX Converter Service
Converts GLB files to FBX format using pygltflib and FBX SDK
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
from pathlib import Path
import subprocess

app = FastAPI(title="Morphara FBX Converter")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Morphara FBX Converter",
        "status": "running",
        "version": "1.0.0",
        "methods": ["blender", "assimp"]
    }

@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {"status": "healthy"}

@app.post("/convert-to-fbx")
async def convert_to_fbx(file: UploadFile = File(...)):
    """
    Convert GLB file to FBX format
    
    Args:
        file: GLB file uploaded by user
        
    Returns:
        FBX file
    """
    
    # Validate file type
    if not file.filename.endswith('.glb'):
        raise HTTPException(status_code=400, detail="Only GLB files are supported")
    
    # Create temp directory for processing
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save uploaded GLB
        glb_path = os.path.join(temp_dir, "input.glb")
        with open(glb_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"Saved GLB: {glb_path} ({len(content)} bytes)")
        
        # Define output FBX path
        fbx_path = os.path.join(temp_dir, "output.fbx")
        
        # Try conversion methods in order
        success = False
        error_msg = ""
        
        # Method 1: Try assimp (fastest, most reliable)
        try:
            print("Trying assimp conversion...")
            result = subprocess.run(
                ['assimp', 'export', glb_path, fbx_path, '-f', 'fbx'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0 and os.path.exists(fbx_path):
                print("✓ Assimp conversion successful")
                success = True
            else:
                error_msg = f"Assimp failed: {result.stderr}"
                print(error_msg)
        except FileNotFoundError:
            error_msg = "Assimp not installed"
            print(error_msg)
        except Exception as e:
            error_msg = f"Assimp error: {str(e)}"
            print(error_msg)
        
        # Method 2: Try Blender (best quality, slower)
        if not success:
            try:
                print("Trying Blender conversion...")
                blender_script = f"""
import bpy
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath='{glb_path}')
bpy.ops.export_scene.fbx(filepath='{fbx_path}', use_selection=False)
"""
                script_path = os.path.join(temp_dir, "convert.py")
                with open(script_path, 'w') as f:
                    f.write(blender_script)
                
                result = subprocess.run(
                    ['blender', '--background', '--python', script_path],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                if os.path.exists(fbx_path):
                    print("✓ Blender conversion successful")
                    success = True
                else:
                    error_msg = f"Blender failed: {result.stderr}"
                    print(error_msg)
            except FileNotFoundError:
                error_msg = "Blender not installed"
                print(error_msg)
            except Exception as e:
                error_msg = f"Blender error: {str(e)}"
                print(error_msg)
        
        # Method 3: Use FBX SDK directly (if available)
        if not success:
            try:
                print("Trying FBX SDK conversion...")
                # FBX SDK not implemented - would require additional setup
                error_msg = "FBX SDK not available"
                print(error_msg)
            except Exception as e:
                error_msg = f"FBX SDK error: {str(e)}"
                print(error_msg)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail=f"All conversion methods failed. Last error: {error_msg}"
            )
        
        # Verify FBX was created
        if not os.path.exists(fbx_path):
            raise HTTPException(status_code=500, detail="FBX file was not created")
        
        fbx_size = os.path.getsize(fbx_path)
        print(f"FBX created: {fbx_path} ({fbx_size} bytes)")
        
        # Return the FBX file
        return FileResponse(
            path=fbx_path,
            media_type="application/octet-stream",
            filename=f"{Path(file.filename).stem}.fbx",
            headers={
                "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}.fbx"'
            }
        )
        
    except HTTPException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Conversion error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)