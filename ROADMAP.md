# Lộ trình BeatCut — 8 tuần, 10–20 h/tuần

Nguyên tắc duy nhất: **mỗi mốc phải là một sản phẩm chạy được**. Nếu hết thời
gian ở M2, bạn vẫn có một project hoàn chỉnh để đưa vào CV, không phải một đống
code dở dang.

Mốc hiện tại: **M1 đã có code**, bạn chỉ cần chạy nó với footage thật.

---

## M1 — Vertical slice, không dùng model (tuần 1–2)

Mục tiêu: từ 1 VOD ra 1 file montage, cắt đúng beat, không cần train gì.

- [x] Khung repo, pipeline, CLI, unit tests
- [ ] Cài ffmpeg (`winget install Gyan.FFmpeg`) và `.\scripts\bootstrap.ps1`
- [ ] Quay 2–3 VOD của chính bạn, 1080p60, 20–60 phút, đặt vào `data/raw/`
- [ ] Chạy `beatcut run`, xem output, chỉnh `configs/default.yaml` cho hợp gu
- [ ] Quay GIF before/after 15–20 giây, chèn vào đầu README
- [ ] `git init`, commit, push lên GitHub (public)

**Xong khi:** README có GIF, một người lạ clone về chạy được theo đúng 4 lệnh
trong Quickstart.

**Học được:** ffmpeg (seek, re-encode, concat demuxer, vì sao `-c copy` cắt lệch
beat), librosa beat tracking, xử lý video dài mà không hết RAM.

---

## M2 — Scorer có học (tuần 3–4)

Mục tiêu: vượt baseline motion+audio, và **chứng minh** là vượt.

- [x] Scorer `killcounter`: crop ô đếm hạ gục ở HUD, OCR lấy số, phát hiện lúc số
      tăng → kill event. Đã có lệnh `beatcut kills`. Đây là hướng rẻ nhất — không
      cần train, không cần GPU.
- [ ] Nối kill event vào `scoring.fuse()` dưới dạng một curve cộng thêm, với
      weight trong config
- [ ] Thêm scorer `enemy`: fine-tune YOLOv8n trên 800–1200 frame tự label (CVAT
      hoặc Roboflow free tier). GPU 4 GB: `imgsz=640`, `batch=8`, AMP.
- [ ] Chạy `beatcut analyze` trên 10 VOD đã label, so precision@5 **trước/sau**

**Xong khi:** bảng "baseline vs M2" có số thật trong README.

**Học được:** labeling protocol, dataset versioning (DVC), fine-tune YOLO, và
quan trọng nhất — cách đo để biết thay đổi của mình có tốt lên hay không.

**Cảnh báo:** đừng nhảy thẳng vào YOLO. Đọc bộ đếm hạ gục cho tín hiệu chính xác
hơn "có enemy trong frame" rất nhiều, và nó không cần GPU. Một lưu ý nữa: OCR
trên chữ toàn màn hình đọc cả icon thành chữ cái, nên phải crop thật hẹp.

---

## M3 — Đóng gói (tuần 5–6)

- [ ] Export ONNX, benchmark `onnxruntime` so với PyTorch (FPS, ms/frame)
- [ ] `docker build` + `docker run` chạy được `app/api.py`
- [ ] GitHub Actions: `ruff check` + `pytest` trên mỗi push
- [ ] Deploy demo lên Hugging Face Spaces (dùng bản M1 nếu M2 chưa xong)
- [ ] `.env` + giới hạn dung lượng upload

**Xong khi:** có link demo bấm được, và CI xanh.

**Học được:** Docker, CI, ONNX, deployment — đây là phần phân biệt "sinh viên
train model trên Colab" với "người làm được việc".

---

## M4 — Kể chuyện (tuần 7–8)

- [ ] Chạy đủ [eval protocol](docs/eval-protocol.md) trên 10 VOD, tách dev/test
- [ ] Error analysis: 10 false positive, mỗi cái một câu giải thích
- [ ] Blog post 800–1200 từ: bài toán, cách làm, số liệu, cái gì fail
- [ ] Video demo 60 giây (không cần đẹp, cần rõ)
- [ ] Dọn repo: xoá code chết, README cuối, tag `v1.0`

**Xong khi:** người phỏng vấn đọc README 2 phút là hiểu bạn làm gì và đo thế nào.

---

## Phần cứng của bạn (RTX 2050, 4 GB)

Đây là lý do các con số dưới đây quan trọng hơn "model to":

| Việc | Cách làm trên 4 GB |
|---|---|
| Fine-tune YOLOv8n | `imgsz=640`, `batch=8`, AMP (`amp=True`) |
| Fine-tune YOLOv8s | `imgsz=512`, `batch=4`, hoặc Colab free |
| Train lâu hơn 1 giờ | Colab/Kaggle, lưu checkpoint lên Drive |
| Benchmark FPS | chạy local, ghi rõ GPU trong README |

---

## Những câu sẽ bị hỏi khi phỏng vấn

Chuẩn bị sẵn câu trả lời cho 6 câu này — chúng gần như chắc chắn xuất hiện:

1. Vì sao cắt bằng re-encode mà không `-c copy`? (→ độ chính xác frame vs tốc độ)
2. Vì sao chọn motion + audio thay vì học từ đầu? (→ baseline trước, model sau)
3. Precision@5 của bạn đo thế nào, ground truth do ai label? (→ protocol)
4. Nếu video 3 tiếng thì pipeline có chết không? (→ streaming, memory)
5. Downbeat bạn xác định bằng gì, sai thì sao? (→ heuristic phase, thừa nhận)
6. Cái gì **không** hoạt động? (→ error analysis, đây là câu ăn điểm nhất)

---

## Dấu hiệu project bị đánh giá là "copy tutorial"

Tránh 5 điều này:

- Dataset là thứ có sẵn (`coco128`, `cifar10`) và không có gì của bạn
- Không có số đo, chỉ có ảnh chụp màn hình kết quả
- README không nói gì về cái gì fail
- Commit history là một commit duy nhất "initial commit"
- Không có demo chạy được, chỉ có notebook

Ngược lại, 5 thứ ghi điểm: data tự thu, ablation có số, error analysis, CI xanh,
demo link.
