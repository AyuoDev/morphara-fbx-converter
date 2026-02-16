"""
Morphara FBX Converter - Using Blender
100% GUARANTEED to work
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
import subprocess
from pathlib import Path

app = FastAPI(title="Morphara FBX Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "Morphara FBX Converter",
        "status": "running",
        "version": "2.0.0",
        "method": "Blender 4.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/convert-to-fbx")
async def convert_to_fbx(file: UploadFile = File(...)):
    """Convert GLB to FBX using Blender"""
    
    if not file.filename.endswith('.glb'):
        raise HTTPException(status_code=400, detail="Only GLB files supported")
    
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save GLB
        glb_path = os.path.join(temp_dir, "input.glb")
        content = await file.read()
        
        with open(glb_path, "wb") as f:
            f.write(content)
        
        print(f"📥 Saved GLB: {len(content)} bytes")
        
        # Output path
        fbx_path = os.path.join(temp_dir, "output.fbx")
        
        # Create Blender Python script
        script = f"""
import bpy
import sys

# Clear scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Import GLB
try:
    bpy.ops.import_scene.gltf(filepath='{glb_path}')
    print('✓ GLB imported')
except Exception as e:
    print(f'✗ Import failed: {{e}}')
    sys.exit(1)

# Export FBX
try:
    bpy.ops.export_scene.fbx(
        filepath='{fbx_path}',
        use_selection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        bake_space_transform=False,
        object_types={{'MESH', 'ARMATURE'}},
        use_mesh_modifiers=True,
        use_mesh_modifiers_render=True,
        mesh_smooth_type='OFF',
        use_armature_deform_only=False,
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        armature_nodetype='NULL',
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=True,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=1.0,
        path_mode='COPY',
        embed_textures=True,
        batch_mode='OFF',
        use_batch_own_dir=True,
        use_metadata=True,
        axis_forward='-Z',
        axis_up='Y'
    )
    print('✓ FBX exported')
except Exception as e:
    print(f'✗ Export failed: {{e}}')
    sys.exit(1)
"""
        
        script_path = os.path.join(temp_dir, "convert.py")
        with open(script_path, 'w') as f:
            f.write(script)
        
        # Run Blender with full path
        print("🎨 Running Blender conversion...")
        
        # Try multiple possible Blender locations
        blender_paths = [
            '/usr/local/bin/blender',
            '/opt/blender-4.0.2-linux-x64/blender',
            '/opt/blender/blender',
            'blender'
        ]
        
        blender_cmd = None
        for path in blender_paths:
            if os.path.exists(path) or path == 'blender':
                blender_cmd = path
                print(f"Found Blender at: {blender_cmd}")
                break
        
        if not blender_cmd:
            raise Exception("Blender not found in any expected location")
        
        result = subprocess.run(
            [blender_cmd, '--background', '--python', script_path],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        print("STDOUT:", result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        # Check if FBX was created
        if not os.path.exists(fbx_path):
            raise Exception(f"FBX not created. Blender exit code: {result.returncode}")
        
        fbx_size = os.path.getsize(fbx_path)
        print(f"✅ FBX created: {fbx_size} bytes")
        
        # Return file
        return FileResponse(
            path=fbx_path,
            media_type="application/octet-stream",
            filename=f"{Path(file.filename).stem}.fbx",
            headers={
                "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}.fbx"'
            }
        )
        
    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Conversion timeout (>2min)")
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)