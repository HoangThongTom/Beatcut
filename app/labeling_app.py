"""Local source-only labeling, isolated from automatic highlight suggestions."""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import streamlit as st  # noqa: E402

from beatcut.annotations import load_annotations, save_annotations, validate_annotations  # noqa: E402
from beatcut.media import probe  # noqa: E402

st.set_page_config(page_title="BeatCut · Gán nhãn", page_icon="🎬", layout="centered")
st.markdown(f"<style>{Path(__file__).with_name('style.css').read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True)
st.title("BeatCut · Gán nhãn độc lập")
st.write("Xem video gốc và đánh dấu những đoạn bạn muốn giữ trong montage 45 giây. "
         "Mỗi người tự chấm, không xem nhãn của người kia hay đề xuất tự động.")
st.caption("Lưu nhãn trước khi đổi video hoặc mã người chấm. "
           "Thời gian tính bằng giây trong video gốc.")
annotator = st.text_input("Mã người chấm", value="A", max_chars=32)
source_path = st.text_input("Đường dẫn video gốc trên máy", placeholder=r"C:\Videos\match_01.mp4")
if st.button("Mở video gốc"):
    try:
        video = Path(source_path).expanduser().resolve()
        if not video.is_file() or video.suffix.lower() not in {".mp4", ".mov", ".mkv", ".webm"}:
            raise ValueError("Nhập đường dẫn tới file video gốc trên máy.")
        info = probe(video)
        if info.duration_s > float(os.environ.get("BEATCUT_MAX_DURATION_S", "3600")):
            raise ValueError("Video vượt giới hạn thời lượng hiện tại của launcher.")
        hasher = hashlib.sha256()
        with video.open("rb") as handle:
            for chunk in iter(lambda: handle.read(2 * 1024 * 1024), b""):
                hasher.update(chunk)
        digest = hasher.hexdigest()
        data = validate_annotations({
            "format": "beatcut-annotations", "version": 1, "video": video.name,
            "sha256": digest, "duration_s": info.duration_s, "annotator": annotator,
            "highlights": [],
        })
    except Exception as exc:  # noqa: BLE001 - bad upload or unreadable source
        st.error(str(exc))
        st.stop()
    drafts = st.session_state.setdefault("label_drafts", {})
    previous = st.session_state.get("labels")
    if previous is not None:
        drafts[(previous["sha256"], previous["annotator"])] = previous
    data = drafts.get((digest, annotator), data)
    st.session_state.update(labels=data, label_video=str(video),
                            label_revision=0)

if "labels" not in st.session_state:
    st.info("Màn hình này chạy local: mở trực tiếp video trên máy, không cần upload cả trận.")
    st.stop()
data = st.session_state["labels"]
if data["annotator"] != annotator:
    st.info("Mã người chấm đã đổi. Lưu nhãn với mã cũ trước, rồi mở video cho lượt chấm mới.")
    st.stop()
digest = data["sha256"]
revision = st.session_state["label_revision"]
st.video(st.session_state["label_video"])
st.caption(f"Nguồn: {data['duration_s']:.1f}s · {len(data['highlights'])} highlight đã áp dụng")

with st.expander("Mở lại nhãn của tôi"):
    saved = st.file_uploader("Nhãn độc lập (.json)", type=["json"])
    if st.button("Mở nhãn"):
        try:
            if saved is None:
                raise ValueError("Chọn file nhãn trước.")
            restored = load_annotations(saved.getvalue())
            if (restored["sha256"] != digest or restored["duration_s"] != data["duration_s"]
                    or restored["annotator"] != annotator):
                raise ValueError("Chọn đúng video gốc và mã người chấm của file này.")
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["labels"] = restored
            st.session_state["label_revision"] += 1
            st.rerun()

with st.form(f"add_{digest}_{annotator}_{revision}"):
    start_col, end_col = st.columns(2)
    start = start_col.number_input("Bắt đầu (s)", min_value=0.0, step=0.1)
    end = end_col.number_input("Kết thúc (s)", min_value=0.0, step=0.1)
    if st.form_submit_button("Thêm highlight"):
        try:
            updated = validate_annotations({**data, "highlights": [
                *data["highlights"], {"start": start, "end": end},
            ]})
        except ValueError as exc:
            st.error(str(exc))
        else:
            st.session_state["labels"] = updated
            st.session_state["label_revision"] += 1
            st.rerun()

if data["highlights"]:
    with st.form(f"edit_{digest}_{annotator}_{revision}"):
        rows = st.data_editor([{"Giữ": True, **item} for item in data["highlights"]],
                              hide_index=True, use_container_width=True)
        if st.form_submit_button("Áp dụng sửa / bỏ đoạn"):
            try:
                updated = validate_annotations({**data, "highlights": [
                    {"start": row["start"], "end": row["end"]} for row in rows if row["Giữ"]
                ]})
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["labels"] = updated
                st.session_state["label_revision"] += 1
                st.rerun()

st.download_button("Lưu nhãn của tôi", data=save_annotations(data), mime="application/json",
                   file_name=f"{Path(data['video']).stem}.{annotator}.annotations.json")
st.caption("File chỉ chứa nhãn đã áp dụng và định danh video, không chứa video hay đường dẫn máy. "
           "Không có highlight cũng lưu được; đó không phải một bộ ground truth đã hoàn tất.")
