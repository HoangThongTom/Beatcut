"""Minimal HTTP surface — an M3 milestone, not a production service.

Deliberately synchronous: one job at a time, files written to local disk, no
auth. Uploads are capped by size and by duration, because a 10-minute 60 fps
recording takes minutes to process and any public endpoint would time out
holding the connection. Before this serves real traffic it needs a job queue and
object storage; the caps are what make it safe to demo.
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from beatcut.media import probe
from beatcut.pipeline import run

ROOT = Path(__file__).resolve().parent.parent
JOBS = ROOT / "outputs" / "jobs"

MAX_UPLOAD_MB = int(os.environ.get("BEATCUT_MAX_UPLOAD_MB", "256"))
MAX_DURATION_S = float(os.environ.get("BEATCUT_MAX_DURATION_S", "180"))

app = FastAPI(title="BeatCut", version="0.1.0")


def _save_upload(upload: UploadFile, dest: Path, limit_mb: int) -> None:
    """Stream the upload to disk, refusing anything over the limit.

    Reading in chunks rather than `shutil.copyfileobj` is what makes the cap
    work: the whole point is to stop before a 2 GB file has landed.
    """
    limit = limit_mb * 1024 * 1024
    written = 0
    with dest.open("wb") as handle:
        while True:
            chunk = upload.file.read(1 << 20)
            if not chunk:
                break
            written += len(chunk)
            if written > limit:
                handle.close()
                dest.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"upload exceeds {limit_mb} MB; trim the clip first",
                )
            handle.write(chunk)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "max_upload_mb": MAX_UPLOAD_MB,
        "max_duration_s": MAX_DURATION_S,
    }


@app.post("/render")
def render(
    video: Annotated[UploadFile, File()],
    music: Annotated[UploadFile, File()],
) -> FileResponse:
    job = JOBS / uuid.uuid4().hex
    job.mkdir(parents=True, exist_ok=True)

    video_path = job / f"video{Path(video.filename or 'input.mp4').suffix or '.mp4'}"
    music_path = job / f"music{Path(music.filename or 'input.mp3').suffix or '.mp3'}"
    _save_upload(video, video_path, MAX_UPLOAD_MB)
    _save_upload(music, music_path, MAX_UPLOAD_MB)

    try:
        info = probe(video_path)
    except Exception as exc:  # noqa: BLE001 - bad container, not a server fault
        raise HTTPException(status_code=400, detail=f"cannot read the video: {exc}") from exc

    if info.duration_s > MAX_DURATION_S:
        raise HTTPException(
            status_code=413,
            detail=(
                f"video is {info.duration_s:.0f}s, the limit is {MAX_DURATION_S:.0f}s; "
                "trim it or run the pipeline locally"
            ),
        )

    output = job / "montage.mp4"
    try:
        run(video_path, music_path, output)
    except Exception as exc:  # noqa: BLE001 - surfaced to the caller as 500
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return FileResponse(output, media_type="video/mp4", filename="montage.mp4")
