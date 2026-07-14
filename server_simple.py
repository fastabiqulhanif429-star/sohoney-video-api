#!/usr/bin/env python3
"""
server_simple.py — Versi PALING SEDERHANA: gabung panel gambar STATIS
(dari video referensi) + video testimoni baru jadi split-screen.

TIDAK ADA AI/Claude API/Gemini di sini sama sekali — panel kirinya selalu
sama persis (diambil dari template.jpg), cuma video kanannya yang beda-beda.

Ini dirancang supaya gampang di-deploy ke platform seperti Render.com atau
Railway (tinggal push, tidak perlu SSH/systemd/firewall manual kayak VPS).
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse

app = FastAPI(title="Sohoney Jr - Simple Split-Screen API")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_IMAGE = BASE_DIR / "template.jpg"   # panel kiri statis, taruh di folder yang sama
API_SECRET = os.environ.get("API_SECRET")  # opsional, isi di Render kalau mau proteksi


@app.get("/health")
def health():
    return {
        "status": "ok",
        "template_found": TEMPLATE_IMAGE.exists(),
    }


@app.post("/render")
async def render_video(
    video: UploadFile = File(...),
    x_api_key: str | None = Header(default=None),
):
    if API_SECRET and x_api_key != API_SECRET:
        raise HTTPException(401, "API key salah. Isi header X-API-Key.")

    if not TEMPLATE_IMAGE.exists():
        raise HTTPException(500, "template.jpg tidak ditemukan di server. Upload dulu file panel-nya.")

    tmpdir = Path(tempfile.mkdtemp(prefix="sohoney_"))
    input_path = tmpdir / (video.filename or "input.mp4")
    output_path = tmpdir / f"{input_path.stem}_final.mp4"

    with open(input_path, "wb") as f:
        shutil.copyfileobj(video.file, f)

    # Ambil ukuran video biar tau berapa tinggi canvas yang pas (default 1080x1080)
    canvas_w, canvas_h = 1080, 1080
    panel_w = canvas_w // 2

    filter_complex = (
        f"[0:v]scale={panel_w}:{canvas_h}[left];"
        f"[1:v]scale={panel_w}:{canvas_h}:force_original_aspect_ratio=increase,"
        f"crop={panel_w}:{canvas_h}[right];"
        f"[left][right]hstack=inputs=2,format=yuv420p[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(TEMPLATE_IMAGE),
        "-i", str(input_path),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "128k",
        "-shortest", "-loglevel", "error",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0 or not output_path.exists():
        raise HTTPException(500, f"Gagal render: {result.stderr}")

    return FileResponse(
        path=str(output_path),
        media_type="video/mp4",
        filename=output_path.name,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
