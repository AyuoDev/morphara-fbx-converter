# Morphara FBX Converter Service

Python service that converts GLB files to FBX format.

## Deployment

This service is deployed on Render.com

## API Endpoints

### `GET /`
Health check - returns service info

### `GET /health`
Health check for monitoring

### `POST /convert-to-fbx`
Convert GLB to FBX

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (GLB)

**Response:**
- FBX file (application/octet-stream)

## Local Development

```bash
pip install -r requirements.txt
python main.py
```

Service runs on http://localhost:8000

## Testing

```bash
curl -X POST http://localhost:8000/convert-to-fbx \
  -F "file=@character.glb" \
  --output character.fbx
```
