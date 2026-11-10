# Quy trình đánh giá

[English](eval-protocol.md) | **Tiếng Việt**

Unit test chứng minh code làm đúng như nó tuyên bố. Chúng không nói gì về việc
*các clip được chọn có tốt không*. Tài liệu này định nghĩa cách đo điều đó, để con
số trong README có ý nghĩa.

## Cái gì được tính là một highlight

Chọn một định nghĩa và không đổi nó giữa chừng:

> Highlight là khoảnh khắc mà một người sẽ giữ lại trong montage 45 giây: một pha
> hạ gục, một pha clutch, một pha hài, một pha hay — một sự kiện có điểm bắt đầu
> và kết thúc rõ ràng.

"Rõ ràng" quan trọng. Định nghĩa mơ hồ sinh ra nhãn mà không ai tái lập được, kể
cả bạn của hai tuần sau.

## Xây dựng ground truth

1. Quay hoặc chọn **5 VOD**, mỗi cái 10–60 phút, từ gameplay của chính bạn. Khác
   map, khác phiên — không phải năm clip của cùng một trận.
2. Với mỗi VOD, cho **hai người** độc lập đánh dấu các đoạn highlight (bắt đầu,
   kết thúc) mà không thấy nhãn của người kia và không thấy kết quả của BeatCut.
3. Giữ những đoạn mà hai người lệch nhau không quá ±2 giây. Bỏ phần còn lại. Đây
   là ground truth của bạn.
4. Lưu thành JSON đặt cạnh video:

```json
{
  "video": "match_01.mp4",
  "annotators": ["A", "B"],
  "highlights": [
    {"start": 412.0, "end": 419.5},
    {"start": 1305.0, "end": 1311.0}
  ]
}
```

5. Chia thành `dev` (3 VOD, dùng để chỉnh weight/config) và `test` (2 VOD, chỉ
   báo cáo một lần). Chỉnh trên tập test rồi báo cáo trên chính nó là cách con số
   trở nên vô nghĩa.

## Các chỉ số

### Công cụ gán nhãn local

Bấm đúp **Start-Labeling.cmd**, hoặc chạy:

```powershell
.\scripts\start-local.ps1 -Annotate
```

Giao diện ở [localhost:8503](http://localhost:8503), tách khỏi editor ở cổng 8501.
Mỗi người nhập mã riêng (ví dụ `A`, `B`), nhập đường dẫn tới **video gốc trên máy**
rồi bấm **Mở video gốc**. Không cần upload video; không có đề xuất tự động hay
nhãn của người kia trên màn hình. Xem nguồn, nhập mốc đầu/cuối, **Thêm highlight**,
rồi **Lưu nhãn của tôi**. Sửa mốc hoặc bỏ chọn Giữ trong bảng rồi áp dụng trước khi lưu.
Lưu trước khi đổi video/người chấm; tải file của chính mình trong **Mở lại nhãn của tôi**
để tiếp tục. Nhãn trống lưu được để ghi nhận chưa tìm thấy highlight, không tự trở
thành ground truth đã hoàn tất.

Hai người phải thực sự xem và chấm độc lập; hai mã khác nhau không chứng minh
được điều đó. Chỉ sau khi cả hai hoàn tất, gom hai file vào `data/labels/` và chạy:

```powershell
beatcut agree data\labels\match_02.A.annotations.json data\labels\match_02.B.annotations.json -o data\labels\match_02.json
```

Lệnh kiểm tra cùng nội dung video bằng SHA-256 và khác mã người chấm. Một cặp được
giữ khi **cả mốc đầu và cuối lệch không quá 2 giây**, và mỗi nhãn chỉ có đúng một
đối tác phù hợp ở bộ còn lại. Cặp mơ hồ hoặc không khớp bị loại; lệnh báo số giữ/bỏ.
Mốc đồng thuận là trung bình của hai mốc. Lệnh không ghi đè file có sẵn; chọn tên
đầu ra mới khi chạy lại. File kết quả đọc được trực tiếp bằng `beatcut score`.
Không có cặp đồng thuận thì chưa thể chấm precision@5 cho VOD đó bằng CLI hiện tại.

Giữ hai file nhãn gốc; JSON chỉ chứa tên video, hash, thời lượng và mốc nhãn, không
chứa video hay đường dẫn trên máy. Không nhập project, manifest hay các clip do
BeatCut đề xuất làm nhãn độc lập. Công cụ này chưa thay thế việc chọn đủ 5 VOD
10–60 phút và chốt dev/test theo bước 5 ở trên.

### Chấm kết quả

Chạy `beatcut analyze VIDEO MUSIC --json out.json`, rồi chấm kết quả chọn so với
nhãn:

```powershell
beatcut score data\labels\match_01.json out.json -k 5
```

Các chỉ số dưới đây đúng là những gì lệnh đó báo cáo.

**Precision@k** — trong k clip BeatCut chọn, bao nhiêu clip chồng lên một
highlight thật ít nhất 50% độ dài của clip?

```
P@k = |{clip được chọn i ≤ k : overlap_i ≥ 0.5 × duration_i}| / k
```

Đây là con số chủ đạo. Nó trả lời câu "nếu người làm nội dung giữ k clip đầu tiên
thì bao nhiêu cái dùng được?".

**IoU thời gian** — với mỗi clip được chọn, `giao / hợp` với highlight khớp nhất.
Báo cáo trung bình trên các cặp khớp; nó bắt được việc mối cắt có bắt đầu và kết
thúc đúng chỗ không, không chỉ là có nằm đúng vùng không.

**Recall / độ phủ** — trong tất cả highlight đã gán nhãn, bao nhiêu phần được
BeatCut tìm ra? Một mô hình luôn chọn đúng ba khoảnh khắc đẹp nhất có precision
cao và recall thảm hại.

**Sai số khớp nhịp** — với mỗi mối cắt, khoảng cách tuyệt đối tính bằng
milli-giây tới downbeat gần nhất. Báo cáo trung bình và p95. Đây là con số rẻ
nhất để đo và so sánh được ngay giữa các phiên bản.

## Cách báo cáo

Đặt một bảng trong README với cột `dev` và `test`, số VOD, và hash của config.
Với 5 VOD (3 dev / 2 test), đây là đánh giá quy mô nhỏ; kết quả chỉ phản ánh bộ
dữ liệu này, chưa đủ để kết luận chất lượng trên nhiều game hoặc nhiều kiểu gameplay.
Nếu precision là 0.62 thì báo 0.62 — một thực tập sinh báo 0.62 kèm phân tích lỗi
rõ ràng thuyết phục hơn nhiều so với người báo 0.95 mà không ai tái lập được.

## Phân tích lỗi (làm đi, đây là chất liệu phỏng vấn)

Với mỗi false positive, viết một câu về lý do nó bị chọn. Sau mười ví dụ thường
sẽ lộ ra một quy luật, và quy luật đó trở thành thay đổi cho M2: "chọn màn hình
menu vì UI tĩnh vẫn có chuyển động", "bỏ lỡ pha clutch im lặng vì trọng số âm
thanh át hết", "cắt sớm 0.3 giây vì pha downbeat bị lệch một phách". Danh sách đó
đáng giá hơn chính con số khi phỏng vấn.
