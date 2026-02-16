"""
Morphara FBX Converter Service
Converts GLB files to FBX format
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
from pathlib import Path

app = FastAPI(title="Morphara FBX Converter")

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your domain
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
        "version": "1.0.0"
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
        
        # Define output FBX path
        fbx_path = os.path.join(temp_dir, "output.fbx")
        
        # CONVERSION HAPPENS HERE
        # For now, we'll use a library - will add in next step
        success = convert_glb_to_fbx(glb_path, fbx_path)
        
        if not success:
            raise HTTPException(status_code=500, detail="Conversion failed")
        
        # Return the FBX file
        return FileResponse(
            path=fbx_path,
            media_type="application/octet-stream",
            filename=f"{Path(file.filename).stem}.fbx",
            background=cleanup_temp_dir(temp_dir)
        )
        
    except Exception as e:
        # Cleanup on error
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Conversion error: {str(e)}")


def convert_glb_to_fbx(glb_path: str, fbx_path: str) -> bool:
    """
    Convert GLB to FBX using available library
    
    We'll implement this with either:
    - trimesh (simpler)
    - Blender Python (better quality)
    """
    
    # METHOD 1: Using trimesh (simple but limited)
    try:
        import trimesh
        
        # Load GLB
        scene = trimesh.load(glb_path)
        
        # Export to FBX
        scene.export(fbx_path, file_type='fbx')
        
        return True
        
    except ImportError:
        # trimesh not available, try alternative
        pass
    
    except Exception as e:
        print(f"Trimesh conversion failed: {e}")
        return False
    
    # METHOD 2: Using pygltflib + manual FBX writing
    # (We'll add this if trimesh doesn't work)
    
    return False


def cleanup_temp_dir(temp_dir: str):
    """Background task to cleanup temporary files"""
    def cleanup():
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
    return cleanup


if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable (Render.com provides this)
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
