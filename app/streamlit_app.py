"""Streamlit demo — the deployment that stays free.

Hugging Face now only offers ZeroGPU to free accounts, and ZeroGPU refuses to
start a Space without a @spaces.GPU function; spending GPU quota on a CPU
pipeline would be the wrong trade. Streamlit Community Cloud hosts this straight
from the public GitHub repo with no card.

Run locally with:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import tempfile
from pathlib import Path

# Hosted runners copy the repo without installing it, so make src/ importable.
_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from beatcut.config import Config  # noqa: E402
from beatcut.media import audio_duration, probe  # noqa: E402
from beatcut.pipeline import run  # noqa: E402

MAX_DURATION_S = float(os.environ.get("BEATCUT_MAX_DURATION_S", "60"))

st.set_page_config(page_title="BeatCut", page_icon="🎬", layout="centered")

st.markdown(
    f"<style>{Path(__file__).with_name('style.css').read_text(encoding='utf-8')}</style>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="bc-nav"><div class="bc-brand">▥ Beat<span>Cut</span></div>'
    '<div class="bc-label">Gameplay. Rhythm. Highlights.</div></div>'
    '<div class="bc-hero"><div class="bc-label">Your best plays. Remixed.</div>'
    '<h1>Make every play<br><span>hit the beat.</span></h1>'
    '<p>Turn your gameplay into a highlight montage that moves with your music. '
    'Bring the footage. Pick the track. We’ll find the moments.</p>'
    '<div class="bc-tags"><span>Beat-synced cuts</span><span>Automatic highlights</span>'
    '<span>Your music, your moment</span></div>'
    '<div class="bc-wave" aria-hidden="true">'
    + ''.join(f'<i style="height:{h}px"></i>' for h in
              [10, 20, 34, 16, 42, 26, 12, 32, 48, 22, 36, 14, 28, 40, 18, 30, 12])
    + '</div></div>',
    unsafe_allow_html=True,
)

demo_video = Path(__file__).resolve().parent.parent / "docs" / "assets" / "montage-demo.mp4"
if demo_video.is_file():
    st.markdown('<div class="bc-section"><b>PLAY</b><h2>See it in action</h2></div>',
                unsafe_allow_html=True)
    st.video(str(demo_video))
    st.caption(
        "44-second montage from an 11-minute gameplay recording: "
        "8 highlights selected with motion, audio, and kill-counter OCR, cut to the beat."
    )

with st.expander("How it works"):
    st.markdown(
        "1. Upload your gameplay and a music track.\n"
        "2. We find the action and choose highlights.\n"
        "3. Cuts follow the musical bars, with game audio mixed under your track.\n"
        "4. Preview your montage and download the MP4."
    )

st.caption(
    f"Try it with a gameplay clip up to {MAX_DURATION_S:.0f} seconds. "
    "Upload a shorter excerpt for this demo."
)

st.markdown('<div class="bc-section"><b>01</b><h2>Bring your footage & sound</h2></div>',
            unsafe_allow_html=True)
video_col, music_col = st.columns(2)
with video_col:
    video_file = st.file_uploader("Gameplay clip", type=["mp4", "mov", "mkv", "webm"])
with music_col:
    music_file = st.file_uploader("Music track", type=["mp3", "wav", "m4a", "ogg", "flac"])

st.markdown('<div class="bc-section"><b>02</b><h2>Find your rhythm</h2></div>',
            unsafe_allow_html=True)
duration_col, start_col = st.columns(2)
target_duration = duration_col.number_input(
    "Montage duration (seconds)", min_value=5, max_value=600, value=45, step=5,
    help="Approximate length. Cuts follow musical bars, so the final length can vary.",
)
music_start = start_col.number_input(
    "Start music at (seconds)", min_value=0, value=0, step=1,
    help="For example, enter 25 to start at 0:25. This exact offset is used in the montage.",
)
st.caption(
    f"Requested montage: {target_duration}s · Music starts at "
    f"{music_start // 60}:{music_start % 60:02d}. "
    "Longer montages need enough source footage; the available highlights may be shorter."
)
if music_file is not None:
    st.markdown("**Preview music from the selected start**")
    st.audio(
        music_file.getvalue(),
        format=music_file.type or "audio/mpeg",
        start_time=music_start,
    )
    st.caption("Press play to listen. Changing the start above also updates the preview.")

st.markdown('<div class="bc-section"><b>03</b><h2>Make the cut</h2></div>',
            unsafe_allow_html=True)
if st.button("Render montage", type="primary", use_container_width=True):
    if not video_file or not music_file:
        st.error("Upload both a clip and a music track.")
    else:
        if "work_dir" not in st.session_state:
            st.session_state["work_dir"] = tempfile.mkdtemp(prefix="beatcut-")
        job = Path(st.session_state["work_dir"])
        paths = []
        for upload in (video_file, music_file):
            content = upload.getvalue()
            digest = hashlib.sha256(content).hexdigest()
            path = job / f"{digest}{Path(upload.name).suffix}"
            # Keep the path and modification time stable across renders in this session.
            if not path.exists():
                path.write_bytes(content)
            paths.append(path)
        video_path, music_path = paths

        try:
            info = probe(video_path)
            music_duration = audio_duration(music_path)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            st.error(f"Cannot read the uploaded video or music: {exc}")
            st.stop()

        if info.duration_s > MAX_DURATION_S:
            st.error(
                f"Video is {info.duration_s:.0f}s; this demo accepts up to "
                f"{MAX_DURATION_S:.0f}s. Trim it or run the pipeline locally."
            )
            st.stop()

        if music_start >= music_duration:
            st.error("Choose a music start before the end of a track containing audio.")
            st.stop()
        if target_duration > info.duration_s:
            st.error("The montage duration must not exceed the uploaded gameplay duration.")
            st.stop()
        if target_duration > music_duration - music_start:
            st.error(
                "Not enough music after this start. Choose an earlier start or shorter montage."
            )
            st.stop()

        cfg = Config(
            target_duration_s=float(target_duration),
            music_start_s=float(music_start),
            max_segments=max(10, math.ceil(target_duration / 2.5)),
        )
        with st.status("Preparing your montage…", expanded=True) as status:
            def show_progress(message):
                status.update(label=message)
                status.write(message)

            output = job / "montage.mp4"
            try:
                manifest = run(video_path, music_path, output, cfg, progress=show_progress)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                status.update(label="Could not finish the montage", state="error")
                st.error(f"Render failed: {exc}")
                st.stop()
            status.update(label="Montage ready — preview and download below", state="complete")

        st.session_state["last_montage"] = {
            "data": output.read_bytes(),
            "duration": manifest["analysis"]["total_duration_s"],
            "music_start": music_start,
            "music_name": music_file.name,
        }

if "last_montage" in st.session_state:
    result = st.session_state["last_montage"]
    st.success(f"Latest montage: {result['duration']:.1f}s")
    st.caption(f"Music: {result['music_name']} · Starts at {result['music_start']} seconds")
    st.video(result["data"])
    st.download_button(
        "Download the montage",
        data=result["data"],
        file_name="montage.mp4",
        mime="video/mp4",
        use_container_width=True,
    )

st.markdown(
    '<div class="bc-footer"><span>BeatCut · Made for your best plays.</span>'
    '<span>Cut to the rhythm. Keep the moment.</span></div>',
    unsafe_allow_html=True,
)
