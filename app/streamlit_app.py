"""BeatCut editor for local use and Streamlit Community Cloud.

Run locally with Start-BeatCut.cmd, or streamlit run app/streamlit_app.py.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
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
import streamlit.components.v1 as components  # noqa: E402

from beatcut import config as config_module  # noqa: E402
from beatcut import editing, pipeline, render  # noqa: E402
from beatcut import project as project_module  # noqa: E402

# Cloud can rerun this entry point before refreshing an already-imported source module.
for module, helper in ((editing, "reorder_rows"), (editing, "apply_timeline"),
                       (editing, "validate_transition"),
                       (pipeline, "music_beats")):
    if not hasattr(module, helper):
        importlib.invalidate_caches()
        importlib.reload(module)

# A live session may predate the title/transition fields. Refresh consumers too:
# they hold direct references to Config and the old render function signatures.
if not {"title", "transition_s"} <= set(config_module.Config.__dataclass_fields__):
    importlib.invalidate_caches()
    for module in (config_module, render, project_module, pipeline):
        importlib.reload(module)

from beatcut.config import Config  # noqa: E402
from beatcut.editing import apply_timeline, rows_to_segments, validate_transition  # noqa: E402
from beatcut.media import audio_duration, probe  # noqa: E402
from beatcut.pipeline import run  # noqa: E402
from beatcut.project import load_project, save_project  # noqa: E402
from beatcut.titles import validate_title  # noqa: E402

LOCAL_MODE = os.environ.get("BEATCUT_LOCAL") == "1"
MAX_DURATION_S = float(os.environ.get("BEATCUT_MAX_DURATION_S", "3600" if LOCAL_MODE else "60"))
timeline = components.declare_component(
    "beatcut_timeline", path=str(Path(__file__).with_name("timeline")),
)


def save_sources(uploads):
    if "work_dir" not in st.session_state:
        st.session_state["work_dir"] = tempfile.mkdtemp(prefix="beatcut-")
    paths = []
    for upload in uploads:
        content = upload.getvalue()
        digest = hashlib.sha256(content).hexdigest()
        path = Path(st.session_state["work_dir"]) / f"{digest}{Path(upload.name).suffix}"
        if not path.exists():
            path.write_bytes(content)
        paths.append(path)
    return paths


def remember_edit(project):
    project["history"].append({
        "rows": copy.deepcopy(project["rows"]), "config": copy.deepcopy(project["config"]),
    })

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

if LOCAL_MODE:
    st.info(
        f"Running on your computer · Gameplay up to {MAX_DURATION_S / 60:g} minutes. "
        "Your gameplay and music are processed on this computer."
    )
else:
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
with st.expander("Open a saved project"):
    st.caption("Upload your saved project and the same original gameplay and music above. "
               "A project saves your edits, not the media files.")
    saved_file = st.file_uploader("BeatCut project (.json)", type=["json"])
    if st.button("Open project"):
        if saved_file is None or video_file is None or music_file is None:
            st.error("Upload a project, gameplay and music first.")
        else:
            try:
                saved = load_project(saved_file.getvalue())
                for kind, upload in (("video", video_file), ("music", music_file)):
                    digest = hashlib.sha256(upload.getvalue()).hexdigest()
                    if digest != saved["sources"][kind]["sha256"]:
                        raise ValueError(f"Upload the original {kind} used in this saved project.")
                video_path, music_path = save_sources((video_file, music_file))
                info = probe(video_path)
                music_duration = audio_duration(music_path)
                if info.duration_s > MAX_DURATION_S:
                    raise ValueError(f"Gameplay must be no longer than {MAX_DURATION_S:.0f}s.")
                selection = rows_to_segments(saved["rows"], info.duration_s)
                start = saved["settings"]["music_start_s"]
                if start + sum(s.duration for s in selection) > music_duration:
                    raise ValueError("The saved selection exceeds the available music.")
                restored = {
                    "video": str(video_path), "music": str(music_path),
                    "duration": info.duration_s, "music_duration": music_duration,
                    "config": Config(**saved["settings"]).to_dict(),
                    "rows": saved["rows"], "sources": saved["sources"], "history": [],
                }
            except Exception as exc:  # noqa: BLE001 - invalid file or unreadable media
                st.error(f"Could not open project: {exc}")
            else:
                st.session_state["edit_project"] = restored
                st.session_state.pop("last_montage", None)
                st.session_state["edit_revision"] = st.session_state.get("edit_revision", 0) + 1
                st.success("Project opened. Continue in Make it yours below, then export your MP4.")

if st.button("Render montage", type="primary", use_container_width=True):
    if not video_file or not music_file:
        st.error("Upload both a clip and a music track.")
    else:
        video_path, music_path = save_sources((video_file, music_file))
        job = video_path.parent

        try:
            info = probe(video_path)
            music_duration = audio_duration(music_path)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            st.error(f"Cannot read the uploaded video or music: {exc}")
            st.stop()

        if info.duration_s > MAX_DURATION_S:
            st.error(
                f"Video is {info.duration_s:.0f}s; the current limit is {MAX_DURATION_S:.0f}s. "
                + ("Restart the local launcher with a higher -MaxDurationSeconds value."
                   if LOCAL_MODE else "Trim it or open Start-BeatCut.cmd on your computer.")
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
        st.session_state["edit_project"] = {
            "sources": {
                kind: {"name": upload.name,
                       "sha256": hashlib.sha256(upload.getvalue()).hexdigest()}
                for kind, upload in (("video", video_file), ("music", music_file))
            },
            "video": str(video_path), "music": str(music_path),
            "duration": info.duration_s, "music_duration": music_duration,
            "config": {**cfg.to_dict(), "music_start_s": manifest["music_start_s"]},
            "rows": [
                {"Keep": True, "Order": index + 1,
                 "Start (s)": segment["start"], "End (s)": segment["end"]}
                for index, segment in enumerate(manifest["analysis"]["segments"])
            ],
            "history": [],
        }
        st.session_state["edit_revision"] = st.session_state.get("edit_revision", 0) + 1

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

if "edit_project" in st.session_state:
    project = st.session_state["edit_project"]
    st.markdown('<div class="bc-section"><b>EDIT</b><h2>Make it yours</h2></div>',
                unsafe_allow_html=True)
    st.download_button(
        "Save project", data=save_project(project), file_name="beatcut-project.json",
        mime="application/json",
    )
    st.caption("Save after applying edits. Keep your original gameplay and music to reopen later.")
    st.caption(
        "Times refer to the original gameplay. Change start/end to trim or extend a clip, "
        "untick Keep to remove it, or change Order to rearrange. Apply edits before exporting. "
        "Apply table edits before using the timeline to keep those changes. "
        "Use the timeline handles to trim. Enable Snap to music beats to align a changed "
        "clip's outgoing cut; later cuts may shift when you trim or reorder."
    )
    selection = rows_to_segments(project["rows"], project["duration"])
    timeline_clips = [
        {"id": index, "start": row["Start (s)"], "end": row["End (s)"]}
        for index, row in sorted(enumerate(project["rows"]), key=lambda pair: pair[1]["Order"])
        if row["Keep"]
    ]
    beat_times = []
    if st.checkbox("Snap to music beats", key="timeline_snap"):
        try:
            with st.spinner("Loading music beats…"):
                grid = pipeline.music_beats(
                    project["music"], Config(**project["config"]),
                    Path(project["video"]).parent / "editor-beats",
                )
            beat_times = [t - project["config"]["music_start_s"] for t in grid.beats
                          if t >= project["config"]["music_start_s"]]
            if not beat_times:
                st.info("No beats found after the music start. Trimming uses exact times.")
        except Exception as exc:  # noqa: BLE001
            st.warning(f"Could not load beats; trimming uses exact times: {exc}")
    new_clips = timeline(clips=timeline_clips, duration=project["duration"],
                         beats=beat_times, default=None,
                         key=f"timeline_{st.session_state['edit_revision']}")
    if new_clips is not None:
        try:
            reordered = apply_timeline(project["rows"], new_clips, project["duration"])
            validate_title(project["config"].get("title"), sum(
                s.duration for s in rows_to_segments(reordered, project["duration"])
            ))
            validate_transition(project["config"].get("transition_s", 0),
                                rows_to_segments(reordered, project["duration"]))
        except ValueError as exc:
            st.error(str(exc))
        else:
            if reordered != project["rows"]:
                remember_edit(project)
                project["rows"] = reordered
                st.session_state["edit_revision"] += 1
                st.rerun()
    clip_index = st.selectbox(
        "Preview original gameplay", range(len(project["rows"])),
        format_func=lambda i: f"Clip {i + 1} · {project['rows'][i]['Start (s)']:.2f}s",
        key=f"source_preview_{st.session_state['edit_revision']}",
    )
    st.video(project["video"], start_time=int(project["rows"][clip_index]["Start (s)"]))
    with st.form(f"clip_edits_{st.session_state['edit_revision']}"):
        edited_rows = st.data_editor(
            project["rows"], hide_index=True, use_container_width=True,
            column_config={
                "Keep": st.column_config.CheckboxColumn("Keep"),
                "Order": st.column_config.NumberColumn("Order", min_value=1, step=1),
                "Start (s)": st.column_config.NumberColumn("Start (s)", min_value=0.0, step=0.1),
                "End (s)": st.column_config.NumberColumn("End (s)", min_value=0.0, step=0.1),
            },
        )
        if st.form_submit_button("Apply edits"):
            try:
                changed_selection = rows_to_segments(edited_rows, project["duration"])
                validate_transition(project["config"].get("transition_s", 0), changed_selection)
                validate_title(project["config"].get("title"),
                               sum(s.duration for s in changed_selection))
            except ValueError as exc:
                st.error(str(exc))
            else:
                remember_edit(project)
                project["rows"] = copy.deepcopy(edited_rows)
                st.session_state["edit_revision"] += 1
                st.rerun()
    st.markdown("**Transitions**")
    st.caption("Fade through black keeps clip lengths and music timing unchanged. "
               "Half the fade is before each cut, half after it. "
               "Game sound fades with the picture. "
               "The title stays above the transition. Apply, then export to preview.")
    transition = project["config"].get("transition_s", 0.0)
    with st.form(f"transitions_{st.session_state['edit_revision']}"):
        style = st.selectbox("Transition style", ["Hard cut", "Fade through black"],
                             index=int(transition > 0))
        fade_length = st.slider("Transition duration (s)", 0.1, 1.0,
                                float(transition or 0.4), step=0.1)
        if st.form_submit_button("Apply transitions"):
            new_transition = fade_length if style == "Fade through black" else 0.0
            try:
                validate_transition(new_transition, selection)
            except ValueError as exc:
                st.error(str(exc))
            else:
                if new_transition != transition:
                    remember_edit(project)
                    project["config"]["transition_s"] = new_transition
                    st.session_state["edit_revision"] += 1
                    st.rerun()
    if len(selection) < 2:
        st.caption("A single clip has no transition. Keep at least two clips to see the effect.")
    st.caption(f"Applied transitions: fade through black · {transition:.1f}s"
               if transition else "Applied transitions: hard cuts")
    st.markdown("**Audio mix**")
    st.caption("0 = mute · 1 = original level · 2 = boost. "
               "Game sound requires audio in the source. "
               "Apply the mix, then export an edited MP4 to hear it.")
    with st.form(f"audio_mix_{st.session_state['edit_revision']}"):
        keep_game = st.checkbox("Keep game audio", value=project["config"]["keep_game_audio"])
        game_col, song_col = st.columns(2)
        game_volume = game_col.slider(
            "Game volume", 0.0, 2.0, float(project["config"]["game_audio_volume"]),
            step=0.05, format="%.2fx",
        )
        song_volume = song_col.slider(
            "Music volume", 0.0, 2.0, float(project["config"]["music_volume"]),
            step=0.05, format="%.2fx",
        )
        if st.form_submit_button("Apply audio mix"):
            settings = {"keep_game_audio": keep_game, "game_audio_volume": game_volume,
                        "music_volume": song_volume}
            if any(project["config"][key] != value for key, value in settings.items()):
                remember_edit(project)
                project["config"].update(settings)
                st.session_state["edit_revision"] += 1
                st.rerun()
    st.caption(f"Applied mix: music {project['config']['music_volume']:.2f}x · "
               + (f"game {project['config']['game_audio_volume']:.2f}x"
                  if project["config"]["keep_game_audio"] else "game muted"))
    st.markdown("**Text overlay**")
    montage_length = sum(s.duration for s in rows_to_segments(project["rows"], project["duration"]))
    title = project["config"].get("title") or {
        "text": "", "start": 0.0, "end": min(3.0, montage_length),
        "position": "bottom", "color": "#FFFFFF", "size": 5.0,
    }
    st.caption("Add one title to the finished montage. Times start at 0 in the montage. "
               "Apply, then export to see it. Clear the text and apply to remove it.")
    with st.form(f"title_{st.session_state['edit_revision']}"):
        title_text = st.text_area("Title text", value=title["text"], max_chars=120)
        title_start_col, title_end_col = st.columns(2)
        title_start = title_start_col.number_input(
            "Title starts at (s)", min_value=0.0, value=float(title["start"]), step=0.1,
        )
        title_end = title_end_col.number_input(
            "Title ends at (s)", min_value=0.0, value=float(title["end"]), step=0.1,
        )
        position_col, color_col, size_col = st.columns(3)
        positions = ["top", "center", "bottom"]
        title_position = position_col.selectbox(
            "Title position", positions, index=positions.index(title["position"]),
        )
        title_color = color_col.color_picker("Title color", value=title["color"])
        title_size = size_col.slider("Title size (%)", 2.0, 8.0, float(title["size"]), step=0.5)
        if st.form_submit_button("Apply title"):
            new_title = {"text": title_text, "start": title_start, "end": title_end,
                         "position": title_position, "color": title_color, "size": title_size}
            if not title_text.strip():
                new_title = None
            try:
                validate_title(new_title, montage_length)
            except ValueError as exc:
                st.error(str(exc))
            else:
                if new_title != project["config"].get("title"):
                    remember_edit(project)
                    project["config"]["title"] = new_title
                    st.session_state["edit_revision"] += 1
                    st.rerun()
    if project["config"].get("title"):
        current_title = project["config"]["title"]
        st.caption(f"Applied title: {current_title['start']:.1f}–{current_title['end']:.1f}s · "
                   f"{current_title['position']}")
        st.text(current_title["text"])
    if st.button("Undo edit", disabled=not project["history"]):
        previous = project["history"].pop()
        # Existing browser sessions can still contain row-only checkpoints.
        if isinstance(previous, list):
            project["rows"] = previous
        else:
            project["rows"], project["config"] = previous["rows"], previous["config"]
        st.session_state["edit_revision"] += 1
        st.rerun()
    selection = rows_to_segments(project["rows"], project["duration"])
    st.caption(f"Applied selection: {len(selection)} clips · "
               f"{sum(s.duration for s in selection):.1f}s. Export to preview the saved selection.")
    if st.button("Export edited MP4", type="primary", use_container_width=True):
        cfg = Config(**project["config"])
        if sum(s.duration for s in selection) > project["music_duration"] - cfg.music_start_s:
            st.error("Your edits need more music. Shorten the selection before exporting.")
        else:
            output = Path(project["video"]).parent / "edited-montage.mp4"
            with st.status("Exporting your edits…", expanded=True) as edit_status:
                try:
                    manifest = run(
                        project["video"], project["music"], output, cfg,
                        segments=selection, progress=edit_status.write,
                    )
                    result = st.session_state.setdefault("last_montage", {
                        "music_start": cfg.music_start_s,
                        "music_name": project["sources"]["music"]["name"],
                    })
                    result["data"] = output.read_bytes()
                    result["duration"] = manifest["analysis"]["total_duration_s"]
                except Exception as exc:  # noqa: BLE001
                    edit_status.update(label="Export failed", state="error")
                    st.error(f"Could not export your edits: {exc}")
                else:
                    edit_status.update(label="Edited montage ready", state="complete")
                    st.rerun()

st.markdown(
    '<div class="bc-footer"><span>BeatCut · Made for your best plays.</span>'
    '<span>Cut to the rhythm. Keep the moment.</span></div>',
    unsafe_allow_html=True,
)
