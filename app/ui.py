"""Gradio demo — the free deployment target.

Hugging Face put Docker Spaces behind a paywall, so the demo ships as a Gradio
Space instead: no container, no build step, and a form a recruiter can actually
use. Gradio is imported lazily so the pipeline stays importable (and testable)
without it installed.
"""

from __future__ import annotations

import os
import sys
import tempfile
import uuid
from pathlib import Path

# On a Space the package is copied in, not installed, so the source tree has to
# be importable by path. Locally the editable install makes this a no-op.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from beatcut.media import probe  # noqa: E402
from beatcut.pipeline import run  # noqa: E402

MAX_DURATION_S = float(os.environ.get("BEATCUT_MAX_DURATION_S", "60"))
JOBS = Path(tempfile.gettempdir()) / "beatcut-jobs"

DESCRIPTION = """
Upload a short gameplay clip and a music track. BeatCut scores the footage,
picks the busiest moments, cuts each one to a whole number of musical bars, and
mixes the game audio under the music.

Processing is synchronous, so the demo is capped at {limit:.0f} seconds of video.
For longer recordings, run the pipeline locally: `beatcut run VIDEO MUSIC -o OUT`.
"""


def render_clip(video_path: str | Path, music_path: str | Path) -> Path:
    """Run the pipeline on two uploaded files and return the montage path."""
    if not video_path or not music_path:
        raise ValueError("both a video and a music file are required")

    job = JOBS / uuid.uuid4().hex
    job.mkdir(parents=True, exist_ok=True)

    info = probe(video_path)
    if info.duration_s > MAX_DURATION_S:
        raise ValueError(
            f"video is {info.duration_s:.0f}s; this demo accepts up to "
            f"{MAX_DURATION_S:.0f}s. Trim it or run the pipeline locally."
        )

    output = job / "montage.mp4"
    run(video_path, music_path, output)
    return output


def build_app():
    import gradio as gr

    def demo(video: str | None, music: str | None) -> str:
        try:
            return str(render_clip(video or "", music or ""))
        except ValueError as exc:
            raise gr.Error(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001 - surfaced in the UI
            raise gr.Error(f"render failed: {exc}") from exc

    with gr.Blocks(title="BeatCut") as app:
        gr.Markdown("# BeatCut")
        gr.Markdown(DESCRIPTION.format(limit=MAX_DURATION_S))
        with gr.Row():
            video_in = gr.File(label="Gameplay clip", file_types=["video"])
            music_in = gr.File(label="Music track", file_types=["audio"])
        run_btn = gr.Button("Render montage", variant="primary")
        video_out = gr.Video(label="Montage")
        run_btn.click(demo, inputs=[video_in, music_in], outputs=video_out)
    return app


if __name__ == "__main__":
    build_app().launch(server_name="0.0.0.0", server_port=int(os.environ.get("PORT", "7860")))
