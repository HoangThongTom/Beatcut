"""Minimal HTTP surface — an M3 milestone skeleton, not a production service.

Deliberately synchronous: one job at a time, files written to local disk, no
auth. Before this is exposed to anyone it needs a job queue, object storage and
a size/duration limit. Kept small so it is honest about what it is.
"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from beatcut.pipeline import run

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "outputs" / "jobs"

app = FastAPI(title="BeatCut", version="0.1.0")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/render")
def render(
    video: Annotated[UploadFile, File()],
    music: Annotated[UploadFile, File()],
) -> FileResponse:
    job = JOBS / uuid.uuid4().hex
    job.mkdir(parents=True, exist_ok=True)

    video_path = job / f"video{Path(video.filename or 'input.mp4').suffix or '.mp4'}"
    music_path = job / f"music{Path(music.filename or 'input.mp3').suffix or '.mp3'}"
    with video_path.open("wb") as handle:
        shutil.copyfileobj(video.file, handle)
    with music_path.open("wb") as handle:
        shutil.copyfileobj(music.file, handle)

    output = job / "montage.mp4"
    try:
        run(video_path, music_path, output)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(output, media_type="video/mp4", filename="montage.mp4")
