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

1. Quay hoặc chọn **10 VOD**, mỗi cái 10–60 phút, từ gameplay của chính bạn. Khác
   map, khác phiên — không phải mười clip của cùng một trận.
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

5. Chia thành `dev` (6 VOD, dùng để chỉnh weight/config) và `test` (4 VOD, chỉ
   báo cáo một lần). Chỉnh trên tập test rồi báo cáo trên chính nó là cách con số
   trở nên vô nghĩa.

## Các chỉ số

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
Nếu precision là 0.62 thì báo 0.62 — một thực tập sinh báo 0.62 kèm phân tích lỗi
rõ ràng thuyết phục hơn nhiều so với người báo 0.95 mà không ai tái lập được.

## Phân tích lỗi (làm đi, đây là chất liệu phỏng vấn)

Với mỗi false positive, viết một câu về lý do nó bị chọn. Sau mười ví dụ thường
sẽ lộ ra một quy luật, và quy luật đó trở thành thay đổi cho M2: "chọn màn hình
menu vì UI tĩnh vẫn có chuyển động", "bỏ lỡ pha clutch im lặng vì trọng số âm
thanh át hết", "cắt sớm 0.3 giây vì pha downbeat bị lệch một phách". Danh sách đó
đáng giá hơn chính con số khi phỏng vấn.
