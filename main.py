"""
Morphara FBX Converter - COMPLETE FIX
Handles: Textures, Animations, Cleanup, Error Recovery
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
import subprocess
from pathlib import Path
import zipfile

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
        "version": "3.0.0",
        "features": ["textures", "animations", "cleanup"]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/convert-to-fbx")
async def convert_to_fbx(file: UploadFile = File(...)):
    """
    Convert GLB to FBX with:
    - All textures extracted and linked
    - Animations baked
    - IcoSphere/default objects removed
    - ZIP containing FBX + textures
    """
    
    if not file.filename.endswith('.glb'):
        raise HTTPException(status_code=400, detail="Only GLB files supported")
    
    temp_dir = tempfile.mkdtemp()
    textures_dir = os.path.join(temp_dir, "textures")
    os.makedirs(textures_dir, exist_ok=True)
    
    try:
        # Save GLB
        glb_path = os.path.join(temp_dir, "input.glb")
        content = await file.read()
        
        with open(glb_path, "wb") as f:
            f.write(content)
        
        print(f"📥 GLB size: {len(content):,} bytes")
        
        # Output paths
        fbx_path = os.path.join(temp_dir, "character.fbx")
        zip_path = os.path.join(temp_dir, "export.zip")
        
        # Blender conversion script
        script = f"""
import bpy
import sys
import os

print("=" * 60)
print("MORPHARA FBX CONVERTER v3.0")
print("=" * 60)

# Clear everything
bpy.ops.wm.read_factory_settings(use_empty=True)
print("✓ Scene cleared")

# Import GLB
try:
    bpy.ops.import_scene.gltf(filepath='{glb_path}')
    print(f"✓ GLB imported: {{len(bpy.data.objects)}} objects")
except Exception as e:
    print(f"✗ Import failed: {{e}}")
    sys.exit(1)

# === CLEANUP: Remove IcoSphere and default objects ===
removed_count = 0
for obj in list(bpy.data.objects):
    # Remove default Blender objects (Camera, Light, Cube, IcoSphere)
    if obj.name.startswith(('Camera', 'Light', 'Cube', 'IcoSphere', 'Icosphere')):
        print(f"  Removing: {{obj.name}}")
        bpy.data.objects.remove(obj, do_unlink=True)
        removed_count += 1

print(f"✓ Cleaned up {{removed_count}} default objects")
print(f"  Remaining: {{len(bpy.data.objects)}} objects")

# === EXTRACT TEXTURES ===
texture_count = 0
for img in bpy.data.images:
    if img.name and not img.name.startswith(('Render Result', 'Viewer Node')):
        # Save each texture as PNG
        filepath = os.path.join('{textures_dir}', f"{{img.name}}.png")
        
        # Ensure unique filename
        if os.path.exists(filepath):
            base, ext = os.path.splitext(filepath)
            counter = 1
            while os.path.exists(f"{{base}}_{{counter}}{{ext}}"):
                counter += 1
            filepath = f"{{base}}_{{counter}}{{ext}}"
        
        try:
            img.filepath_raw = filepath
            img.file_format = 'PNG'
            img.save()
            texture_count += 1
            print(f"  Saved: {{os.path.basename(filepath)}}")
        except Exception as e:
            print(f"  Warning: Could not save {{img.name}}: {{e}}")

print(f"✓ Extracted {{texture_count}} textures")

# === VERIFY ANIMATIONS ===
action_count = len(bpy.data.actions)
if action_count > 0:
    print(f"✓ Found {{action_count}} animation(s):")
    for action in bpy.data.actions:
        print(f"    - {{action.name}} ({{len(action.fcurves)}} channels, {{int(action.frame_range[1] - action.frame_range[0])}} frames)")
else:
    print("⚠ No animations found")

# === EXPORT FBX ===
try:
    bpy.ops.export_scene.fbx(
        filepath='{fbx_path}',
        use_selection=False,
        global_scale=1.0,
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_NONE',
        
        # Objects to export
        object_types={{'MESH', 'ARMATURE'}},
        use_mesh_modifiers=True,
        use_mesh_modifiers_render=True,
        mesh_smooth_type='FACE',
        
        # Armature settings
        use_armature_deform_only=False,
        add_leaf_bones=False,
        primary_bone_axis='Y',
        secondary_bone_axis='X',
        armature_nodetype='NULL',
        
        # === ANIMATION EXPORT (CRITICAL) ===
        bake_anim=True,                      # Enable animation baking
        bake_anim_use_all_bones=True,       # Bake all bones
        bake_anim_use_nla_strips=True,      # Include NLA strips
        bake_anim_use_all_actions=True,     # Export ALL actions (not just active)
        bake_anim_force_startend_keying=True,  # Force keyframes at start/end
        bake_anim_step=1.0,                  # Sample every frame
        bake_anim_simplify_factor=0.0,      # No simplification (keep all keys)
        
        # === TEXTURE HANDLING ===
        path_mode='COPY',                    # Copy textures to output folder
        embed_textures=False,                # Don't embed (export separately for ZIP)
        
        # Axis conversion (for Unity/Unreal/Godot)
        axis_forward='-Z',
        axis_up='Y',
        
        # Metadata
        use_metadata=True,
        batch_mode='OFF'
    )
    
    fbx_size = os.path.getsize('{fbx_path}') if os.path.exists('{fbx_path}') else 0
    print(f"✓ FBX exported: {{fbx_size:,}} bytes")
    
except Exception as e:
    print(f"✗ Export failed: {{e}}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("=" * 60)
print("CONVERSION COMPLETE")
print("=" * 60)
"""
        
        script_path = os.path.join(temp_dir, "convert.py")
        with open(script_path, 'w') as f:
            f.write(script)
        
        # Run Blender
        print("🎨 Running Blender...")
        
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
                break
        
        if not blender_cmd:
            raise Exception("Blender not found")
        
        result = subprocess.run(
            [blender_cmd, '--background', '--python', script_path],
            capture_output=True,
            text=True,
            timeout=180  # 3 minutes
        )
        
        print("=" * 60)
        print("BLENDER OUTPUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        print("=" * 60)
        
        # Verify FBX was created
        if not os.path.exists(fbx_path):
            raise Exception(f"FBX not created. Exit code: {result.returncode}")
        
        fbx_size = os.path.getsize(fbx_path)
        
        # Count textures
        texture_files = [f for f in os.listdir(textures_dir) if f.endswith('.png')]
        texture_count = len(texture_files)
        
        print(f"📦 Creating export package:")
        print(f"   FBX: {fbx_size:,} bytes")
        print(f"   Textures: {texture_count} files")
        
        # Create ZIP with FBX + textures
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add FBX
            zipf.write(fbx_path, "character.fbx")
            
            # Add textures folder
            if texture_count > 0:
                for texture_file in texture_files:
                    texture_path = os.path.join(textures_dir, texture_file)
                    zipf.write(texture_path, f"textures/{texture_file}")
        
        zip_size = os.path.getsize(zip_path)
        print(f"✅ Package created: {zip_size:,} bytes")
        
        # Return ZIP file
        return FileResponse(
            path=zip_path,
            media_type="application/zip",
            filename=f"{Path(file.filename).stem}_fbx.zip",
            headers={
                "Content-Disposition": f'attachment; filename="{Path(file.filename).stem}_fbx.zip"',
                "X-Textures-Count": str(texture_count),
                "X-FBX-Size": str(fbx_size)
            }
        )
        
    except subprocess.TimeoutExpired:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail="Conversion timeout (>3min)")
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"❌ Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"🚀 Morphara FBX Converter v3.0")
    print(f"   Port: {port}")
    print(f"   Features: Textures ✓ Animations ✓ Cleanup ✓")
    uvicorn.run(app, host="0.0.0.0", port=port)