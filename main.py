"""
Morphara FBX Converter Service
Converts GLB files to FBX format using pymeshlab
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
from pathlib import Path

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
        "version": "1.0.1",
        "method": "pymeshlab"
    }

@app.get("/health")
async def health_check():
    """Health check for monitoring"""
    return {"status":"healthy"}

@app.post("/convert-to-fbx")
async def convert_to_fbx(file: UploadFile = File(...)):
    """Convert GLB to FBX using pymeshlab"""
    
    if not file.filename.endswith('.glb'):
        raise HTTPException(status_code=400, detail="Only GLB files are supported")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save GLB
        glb_path = os.path.join(temp_dir, "input.glb")
        content = await file.read()
        
        with open(glb_path, "wb") as f:
            f.write(content)
        
        print(f"Saved GLB: {glb_path} ({len(content)} bytes)")
        
        # Output path
        fbx_path = os.path.join(temp_dir, "output.fbx")
        
        # Convert using pymeshlab
        try:
            import pymeshlab
            
            print("Loading mesh with pymeshlab...")
            ms = pymeshlab.MeshSet()
            ms.load_new_mesh(glb_path)
            
            print(f"Mesh loaded: {ms.current_mesh().vertex_number()} vertices")
            
            # Export to FBX
            print("Exporting to FBX...")
            ms.save_current_mesh(fbx_path)
            
            if not os.path.exists(fbx_path):
                raise Exception("FBX file was not created")
            
            fbx_size = os.path.getsize(fbx_path)
            print(f"✓ FBX created: {fbx_size} bytes")
            
            return FileResponse(
                path=fbx_path,
                media_type="application/octet-stream",
                filename=f"{Path(file.filename).stem}.fbx",
                headers={
                    "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}.fbx"'
                }
            )
            
        except ImportError as e:
            print(f"pymeshlab not available: {e}")
            raise HTTPException(
                status_code=500, 
                detail="pymeshlab library not installed"
            )
        except Exception as e:
            print(f"Conversion failed: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Conversion failed: {str(e)}"
            )
        
    except HTTPException:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)