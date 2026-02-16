"""
Morphara FBX Converter Service
Converts GLB to FBX by converting to OBJ first, then wrapping in FBX format
"""

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import os
import shutil
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
        "version": "1.0.2",
        "method": "trimesh + FBX ASCII wrapper"
    }

@app.get("/health")
async def health_check():
    return {"status":"healthy"}

@app.post("/convert-to-fbx")
async def convert_to_fbx(file: UploadFile = File(...)):
    """Convert GLB to FBX"""
    
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
        
        # Load with trimesh
        import trimesh
        
        print("Loading GLB with trimesh...")
        scene = trimesh.load(glb_path, force='scene')
        
        # Export to OBJ first (trimesh supports this well)
        obj_path = os.path.join(temp_dir, "temp.obj")
        
        # Get the geometry
        if hasattr(scene, 'geometry') and len(scene.geometry) > 0:
            # Merge all geometries
            meshes = []
            for geom in scene.geometry.values():
                if hasattr(geom, 'vertices'):
                    meshes.append(geom)
            
            if meshes:
                # Export first mesh to OBJ
                mesh = meshes[0]
                mesh.export(obj_path)
                print(f"Exported to OBJ: {obj_path}")
        else:
            raise Exception("No geometry found in GLB")
        
        # Read OBJ and convert to FBX ASCII format
        fbx_path = os.path.join(temp_dir, "output.fbx")
        
        print("Converting OBJ to FBX...")
        obj_to_fbx(obj_path, fbx_path, Path(file.filename).stem)
        
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
        
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        print(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Conversion failed: {str(e)}")


def obj_to_fbx(obj_path: str, fbx_path: str, model_name: str):
    """Convert OBJ to FBX ASCII format"""
    
    # Read OBJ file
    vertices = []
    faces = []
    
    with open(obj_path, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.split()
                vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            elif line.startswith('f '):
                parts = line.split()
                # OBJ faces are 1-indexed, FBX is 0-indexed
                face = []
                for p in parts[1:]:
                    idx = int(p.split('/')[0]) - 1
                    face.append(idx)
                faces.append(face)
    
    print(f"Loaded {len(vertices)} vertices, {len(faces)} faces from OBJ")
    
    # Write FBX ASCII format
    with open(fbx_path, 'w') as f:
        # FBX Header
        f.write('; FBX 7.4.0 project file\n')
        f.write('; Created by Morphara FBX Converter\n')
        f.write('; ----------------------------------------------------\n\n')
        
        f.write('FBXHeaderExtension:  {\n')
        f.write('\tFBXHeaderVersion: 1003\n')
        f.write('\tFBXVersion: 7400\n')
        f.write('}\n\n')
        
        # Objects
        f.write('Objects:  {\n')
        f.write(f'\tGeometry: 100, "Geometry::", "Mesh" {{\n')
        
        # Vertices
        f.write('\t\tVertices: *' + str(len(vertices) * 3) + ' {\n\t\t\ta: ')
        vertex_data = []
        for v in vertices:
            vertex_data.extend([f'{v[0]:.6f}', f'{v[1]:.6f}', f'{v[2]:.6f}'])
        f.write(','.join(vertex_data))
        f.write('\n\t\t}\n')
        
        # Polygon vertex indices
        indices = []
        for face in faces:
            for i, idx in enumerate(face):
                if i == len(face) - 1:
                    indices.append(str(~idx))  # Last index is negated in FBX
                else:
                    indices.append(str(idx))
        
        f.write('\t\tPolygonVertexIndex: *' + str(len(indices)) + ' {\n\t\t\ta: ')
        f.write(','.join(indices))
        f.write('\n\t\t}\n')
        
        f.write('\t\tGeometryVersion: 124\n')
        f.write('\t}\n')
        f.write(f'\tModel: 200, "Model::{model_name}", "Mesh" {{\n')
        f.write('\t\tVersion: 232\n')
        f.write('\t}\n')
        f.write('}\n\n')
        
        # Connections
        f.write('Connections:  {\n')
        f.write('\tC: "OO",100,200\n')
        f.write('}\n')
    
    print(f"Wrote FBX ASCII format to {fbx_path}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)