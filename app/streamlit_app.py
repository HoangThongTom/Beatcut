"""Streamlit demo — the deployment that stays free.

Hugging Face now only offers ZeroGPU to free accounts, and ZeroGPU refuses to
start a Space without a @spaces.GPU function; spending GPU quota on a CPU
pipeline would be the wrong trade. Streamlit Community Cloud hosts this straight
from the public GitHub repo with no card.

Run locally with:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

# Hosted runners copy the repo without installing it, so make src/ importable.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from beatcut.media import probe  # noqa: E402
from beatcut.pipeline import run  # noqa: E402

MAX_DURATION_S = float(os.environ.get("BEATCUT_MAX_DURATION_S", "60"))

st.set_page_config(page_title="BeatCut", page_icon="🎬", layout="centered")

st.title("🎬 BeatCut")
st.markdown(
    "Turn a gameplay clip into a short montage that **cuts on the beat** of a song. "
    "It scores the footage for action, picks the busiest moments, and cuts each clip "
    "to a whole number of musical bars. No model, no GPU, no training."
)

demo_video = Path(__file__).resolve().parent.parent / "docs" / "assets" / "montage-demo.mp4"
if demo_video.is_file():
    st.subheader("Sample montage")
    st.video(str(demo_video))
    st.caption(
        "44-second montage from an 11-minute gameplay recording: "
        "8 highlights selected with motion, audio, and kill-counter OCR, cut to the beat."
    )

with st.expander("How it works"):
    st.markdown(
        "1. decode the video at 4 fps and measure motion energy\n"
        "2. measure loudness from the game audio\n"
        "3. fuse the signals and slide a scoring window over them\n"
        "4. keep the top non-overlapping windows\n"
        "5. quantise each clip to whole bars so every cut lands on the beat\n"
        "6. cut, concatenate, and mix game audio under the music"
    )

st.caption(
    f"Rendering is synchronous, so this demo accepts clips up to {MAX_DURATION_S:.0f} "
    "seconds. Longer recordings: run `beatcut run` locally."
)

video_file = st.file_uploader("Gameplay clip", type=["mp4", "mov", "mkv", "webm"])
music_file = st.file_uploader("Music track", type=["mp3", "wav", "m4a", "ogg", "flac"])

if st.button("Render montage", type="primary", use_container_width=True):
    if not video_file or not music_file:
        st.error("Upload both a clip and a music track.")
    else:
        job = Path(tempfile.mkdtemp(prefix="beatcut-"))
        video_path = job / f"video{Path(video_file.name).suffix or '.mp4'}"
        music_path = job / f"music{Path(music_file.name).suffix or '.mp3'}"
        video_path.write_bytes(video_file.getbuffer())
        music_path.write_bytes(music_file.getbuffer())

        try:
            info = probe(video_path)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            st.error(f"Cannot read that video: {exc}")
            st.stop()

        if info.duration_s > MAX_DURATION_S:
            st.error(
                f"Video is {info.duration_s:.0f}s; this demo accepts up to "
                f"{MAX_DURATION_S:.0f}s. Trim it or run the pipeline locally."
            )
            st.stop()

        with st.spinner(f"Rendering {info.duration_s:.0f}s of footage…"):
            output = job / "montage.mp4"
            try:
                run(video_path, music_path, output)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                st.error(f"Render failed: {exc}")
                st.stop()

        st.success("Done.")
        st.video(str(output))
        st.download_button(
            "Download the montage",
            data=output.read_bytes(),
            file_name="montage.mp4",
            mime="video/mp4",
            use_container_width=True,
        )
