# Phiếu Phản Ánh — K4 Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
>
> Cách trả lời: thay dòng mẫu bên dưới mỗi câu bằng câu trả lời.
> `grade.py` đếm số câu đã trả lời (15 điểm cho 10 câu).
>
> Họ và tên: Vũ Hữu Trường  Mã học viên: 2A202601694

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `api_token` không có giá trị mặc định nên app chết ngay khi
khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà việc
"chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Tình huống: Khi deploy ứng dụng lên Cloud (Render/Railway), ta quên khai báo biến môi trường `API_TOKEN` trên Dashboard.
- **Nếu để mặc định `"changeme"`**: Ứng dụng vẫn khởi động bình thường. Kẻ tấn công hoặc bot quét tự động thử dùng token `"changeme"` sẽ xác thực thành công và thoải mái gọi API LLM, tiêu tốn toàn bộ ngân sách API key của bạn. Bạn chỉ phát hiện khi thấy hóa đơn LLM tăng vọt.
- **Nếu không có mặc định (Fail-fast)**: Ngay khi vừa container khởi động, `pydantic-settings` sẽ ném lỗi `ValidationError` và làm ứng dụng crash ngay lập tức. Màn hình Dashboard trên Cloud báo lỗi deploy lập tức giúp bạn nhận ra ngay việc thiếu biến môi trường trước khi bất kỳ request nào chạm tới service.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/chat` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Dòng log JSON thu được:
`{"event": "chat_completed", "severity": "INFO", "ts": "2026-08-10T14:30:00.123456+00:00", "client_id": "sv01", "prompt_tokens": 12, "completion_tokens": 45, "usd_cost": 0.00012}`

Hai việc làm được với log JSON:
1. **Lọc và tạo cảnh báo tự động trên Cloud Logging/Datadog**: Công cụ quản lý log có thể parse các trường JSON (`severity`, `client_id`, `usd_cost`). Bạn dễ dàng tạo rule alert như "Cảnh báo khi `severity` = ERROR quá 5 lần/phút" hoặc "Alert khi `client_id` vượt mức chi phí".
2. **Thống kê và tổng hợp dữ liệu (Metrics)**: Dễ dàng đẩy log JSON vào Datadog/Elasticsearch/BigQuery để tính tổng `usd_cost` theo từng client trong ngày hoặc đếm tổng request, điều mà dòng chữ tự do từ `print()` không thể parse chính xác được.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t chat:single .
docker build -t chat:multi .
docker images | grep chat
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | ~1.8 GB |
| Multi-stage | ~320 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Phần dung lượng chênh lệch (~1.5 GB) bao gồm:
1. Base image gốc (`python:3.11`) chứa đầy đủ các trình biên dịch (gcc, g++, make), header files và công cụ build hệ thống.
2. Thư mục cache wheel và các file tạm sinh ra trong quá trình cài đặt pip / build C extensions.
Trong Multi-stage build, stage `builder` thực hiện build/cài đặt thư viện, sau đó stage `runtime` (`python:3.11-slim`) chỉ `COPY` kết quả binary/thư viện đã cài sang, loại bỏ toàn bộ trình biên dịch và file rác.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

- Khi sửa 1 ký tự trong `app/main.py`: các layer `FROM`, `WORKDIR`, `COPY requirements.txt .`, `RUN pip install` đều được dùng lại từ cache vì `requirements.txt` không thay đổi. Chỉ các layer từ `COPY app ./app` trở đi mới phải chạy lại.
- Nếu đặt `COPY . .` lên trước `RUN pip install`: Mỗi lần sửa 1 dòng code, layer `COPY . .` bị invalid cache, dẫn đến Docker phải chạy lại toàn bộ lệnh `RUN pip install` từ đầu, gây lãng phí nhiều phút build image.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

- **Chuỗi sự kiện**:
  1. Code Python có lỗ hổng (RCE / Remote Code Execution qua eval/pickle/vulnerable package).
  2. Kẻ tấn công khai thác lỗ hổng và chạy được lệnh shell trong container.
  3. Vì container chạy dưới quyền root (UID=0), tiến trình shell của kẻ tấn công có quyền root trong container namespace.
  4. Kẻ tấn công lợi dụng các kỹ thuật container escape (hoặc qua mounted socket/volume) để chiếm quyền root trên máy host thật.
- **Lệnh `USER appuser` cắt đứt chuỗi**:
  Chuyển tiến trình sang chạy với người dùng thường (non-root UID 10001). Khi kẻ tấn công thực thi được code trong container, tiến trình bị giới hạn quyền và không có đặc quyền root để thực hiện các thao tác độc hại hay leo thang quyền lên máy host.

---

### Câu 6 — Bearer token (CP3)

Vì sao 401 phải kèm header `WWW-Authenticate: Bearer`? Và vì sao ta trả **cùng
một** thông báo lỗi cho cả ba trường hợp (thiếu header, sai scheme, sai token)
thay vì nói rõ sai ở đâu cho người dùng dễ sửa?

1. Header `WWW-Authenticate: Bearer` là quy định bắt buộc của chuẩn HTTP (RFC 7235 & RFC 6750) để thông báo cho client biết phương thức xác thực được yêu cầu (`Bearer`).
2. Trả cùng một thông báo lỗi nhằm tránh rò rỉ thông tin bảo mật (Information Disclosure). Nếu báo chi tiết "sai scheme" hay "sai token", kẻ tấn công sẽ biết bước nào của họ đã đoán đúng (ví dụ: biết scheme đúng để chuyển sang tấn công brute-force token). Thông báo chung `invalid or missing bearer token` giúp bảo mật hệ thống tốt hơn.

---

### Câu 7 — Token bucket (CP3)

Với `capacity=10`, `refill_per_minute=10`: một client im lặng 10 phút rồi gửi
liên tiếp. Nó gửi được bao nhiêu request trước khi bị 429? Nếu bỏ đoạn
`min(capacity, ...)` trong `available()` thì con số đó thành bao nhiêu, và tại sao?

- Với `capacity=10`, client im lặng 10 phút thì xô chỉ chứa tối đa 10 token. Nó sẽ gửi được **10 request** liên tiếp thành công trước khi bị chặn ở request thứ 11 với mã 429.
- Nếu bỏ `min(capacity, ...)`: Sau 10 phút (600 giây), số token tự nạp là `600 * (10 / 60) = 100 token`. Client sẽ gửi được **100 request** liên tiếp. Bỏ `min` làm mất khả năng giới hạn dung lượng xô, cho phép client tích trữ token vô hạn để tấn công burst.

---

### Câu 8 — Ngân sách theo ngày (CP3)

So sánh hạn mức $30/tháng với hạn mức $1/ngày cho cùng một client. Giả sử có sự
cố khiến một client gọi liên tục từ 2h sáng. Với mỗi cách, thiệt hại tối đa là
bao nhiêu và service tự hồi phục khi nào?

- **Hạn mức $30/tháng**: Thiệt hại tối đa là **$30** (toàn bộ ngân sách tháng bị đốt sạch trong vài giờ). Service sẽ bị ngưng hoạt động trong suốt thời gian còn lại của tháng và chỉ hồi phục vào đầu tháng sau.
- **Hạn mức $1/ngày**: Thiệt hại tối đa trong ngày chỉ là **$1**. Ngay khi chạm mốc $1, service trả 402 để chặn các request tiếp theo. Sang ngày mới (00:00 UTC), key tự reset và service **tự động phục hồi ngay ngày hôm sau** mà không cần can thiệp thủ công.

---

### Câu 9 — /healthz khác /readyz (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

1. **Giây 0-10**: Cả 3 container nhận health check. Vì Redis mất kết nối, endpoint trả về lỗi làm Orchestrator đánh giá cả 3 container đều bị hỏng (unhealthy).
2. **Giây 10-20**: Orchestrator tiến hành tiêu diệt (KILL) và khởi động lại (RESTART) cả 3 container cùng lúc.
3. **Giây 20-30**: Các container mới khởi động tiếp tục kiểm tra Redis và thất bại, dẫn đến vòng lặp restart liên tục (CrashLoopBackOff), làm sụp đổ toàn bộ cụm ứng dụng.
=> `/healthz` chỉ kiểm tra process app còn sống, `/readyz` mới kiểm tra kết nối Redis để Load Balancer tạm ngắt traffic mà không restart container.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

- **Lỗi gặp phải**: App bị crash khi deploy trên Cloud với thông báo `Port binding failed / Connection refused`.
- **Nguyên nhân**: App hardcode cổng 8000 trong code thay vì sử dụng biến môi trường `$PORT` do Platform (như Render/Railway) cấp phát động.
- **Cách sửa**: Cập nhật file `app/config.py` và `Dockerfile` để lấy giá trị cổng từ biến môi trường `port: int = 8000` (sử dụng `${PORT:-8000}`).
