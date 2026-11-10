# Lộ trình BeatCut — 8 tuần, 10–20 h/tuần

[English](ROADMAP.md) | **Tiếng Việt**

Nguyên tắc duy nhất: **mỗi mốc phải là một sản phẩm chạy được**. Nếu hết thời
gian ở M2, bạn vẫn có một project hoàn chỉnh để đưa vào CV, không phải một đống
code dở dang.

Mốc hiện tại: **M1 xong, M2 xong một nửa** — pipeline đã chạy trên VOD thật, có
bộ dò hạ gục, có số liệu ablation.
Demo Streamlit, CI, cache khi đổi nhạc, tiến độ xử lý và editor cơ bản đã có.
Đánh giá M2/M4 vẫn chưa xong; phần editor không thay thế việc đo chất lượng highlight.

---

## M1 — Vertical slice, không dùng model (tuần 1–2)

Mục tiêu: từ 1 VOD ra 1 file montage, cắt đúng beat, không cần train gì.

- [x] Khung repo, pipeline, CLI, unit tests
- [x] Cài ffmpeg và `.\scripts\bootstrap.ps1`
- [x] Quay VOD của chính bạn, đặt vào `data/raw/`
- [x] Chạy `beatcut run`, xem output, chỉnh `configs/default.yaml` cho hợp gu
- [x] Quay GIF before/after, chèn vào đầu README
- [x] `git init`, commit, push lên GitHub (public)

**Xong khi:** README có GIF, một người lạ clone về chạy được theo đúng các lệnh
trong Quickstart.

**Học được:** ffmpeg (seek, re-encode, concat demuxer, vì sao `-c copy` cắt lệch
beat), librosa beat tracking, xử lý video dài mà không hết RAM.

---

## M2 — Tín hiệu từ trong game (tuần 3–4)

Mục tiêu: vượt baseline motion+audio, và **chứng minh** là vượt.

- [x] Scorer `killcounter`: crop ô đếm hạ gục ở HUD, OCR lấy số, phát hiện lúc số
      tăng → kill event. Đã có lệnh `beatcut kills`.
- [x] Nối kill event vào `scoring.fuse()` dưới dạng bump quanh mỗi kill, có
      weight trong config
- [x] Đo ablation: 2/8 → 8/8 clip có chứa pha hạ gục
- [ ] Thêm scorer `enemy`: fine-tune YOLOv8n trên 800–1200 frame tự label (CVAT
      hoặc Roboflow free tier). GPU 4 GB: `imgsz=640`, `batch=8`, AMP.
- [ ] Chạy `beatcut analyze` trên nhiều VOD đã label, so precision@5 **trước/sau**

**Xong khi:** bảng "baseline vs M2" có số thật trong README.

**Học được:** labeling protocol, dataset versioning (DVC), fine-tune YOLO, và
quan trọng nhất — cách đo để biết thay đổi của mình có tốt lên hay không.

**Cảnh báo:** đừng nhảy thẳng vào YOLO. Đọc bộ đếm hạ gục cho tín hiệu chính xác
hơn "có enemy trong frame" rất nhiều, và nó không cần GPU. Một lưu ý nữa: OCR
trên chữ toàn màn hình đọc cả icon thành chữ cái, nên phải crop thật hẹp.

---

## M3 — Đóng gói (tuần 5–6)

- [x] Đóng gói API bằng Docker (kiểm tra local được ghi trong [deploy/README.md](deploy/README.md))
- [x] GitHub Actions: `ruff check` + `pytest` trên mỗi push vào main
- [x] Giới hạn độ dài upload; render hiện vẫn đồng bộ
- [x] Deploy demo lên Streamlit Community Cloud; giữ cấu hình Spaces để tham khảo
- [ ] Export ONNX, benchmark `onnxruntime` so với PyTorch (FPS, ms/frame)

**Xong khi:** có link demo bấm được, và CI xanh.

**Học được:** Docker, CI, ONNX, deployment — đây là phần phân biệt "sinh viên
train model trên Colab" với "người làm được việc".

---

## M4 — Kể chuyện (tuần 7–8)

- [ ] Chạy đủ [eval protocol](docs/eval-protocol.vi.md) trên 10 VOD, tách dev/test
- [ ] Error analysis: 10 false positive, mỗi cái một câu giải thích
- [ ] Blog post 800–1200 từ: bài toán, cách làm, số liệu, cái gì fail
- [ ] Video demo 60 giây (không cần đẹp, cần rõ)
- [ ] Dọn repo: xoá code chết, README cuối, tag `v1.0`

**Xong khi:** người phỏng vấn đọc README 2 phút là hiểu bạn làm gì và đo thế nào.

---

## Nhánh mở rộng editor

- [x] Chọn thời lượng, mốc bắt đầu nhạc và nghe thử
- [x] Dùng lại gameplay/OCR khi đổi nhạc; hiển thị tiến độ
- [x] Xem nguồn, cắt đoạn, giữ/bỏ, đổi thứ tự, hoàn tác và xuất MP4 thủ công
- [x] Lưu/mở lại bản dựng, kiểm tra đúng nội dung video và nhạc gốc
- [x] Timeline kéo thả đổi thứ tự, có nút mũi tên cho bàn phím/điện thoại
- [x] Tay nắm cắt đầu/cuối trên timeline và tuỳ chọn bắt nhịp thủ công
- [ ] Điều khiển âm lượng, chữ và chuyển cảnh

Mốc editor tiếp theo: điều chỉnh âm lượng, sau đó đến chữ và chuyển cảnh. Mốc nghiên cứu vẫn là gán nhãn độc lập
và đo precision@5 theo quy trình đánh giá, không dùng bản chỉnh từ đề xuất tự động
làm ground truth độc lập.

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
