# Thông Tin Deploy — Checkpoint 5

> **Chỉ ghi TÊN biến môi trường, tuyệt đối không dán giá trị token vào đây.**
> Repo này công khai — dán token vào là mất token.

## Thông Tin Học Viên

| Mục         | Nội dung                                                         |
| ----------- | ---------------------------------------------------------------- |
| Họ và tên   | Vũ Hữu Trường                                                    |
| Mã học viên | 2A202601694                                                      |
| Repo        | https://github.com/truonghuu344/K4-Day12-2A202601694-VuHuuTruong |

## Service

| Mục         | Nội dung                                                  |
| ----------- | --------------------------------------------------------- |
| Public URL  | https://dashboard.render.com/web/srv-d9spsd5bedkc73e1e3f0 |
| Platform    | Render                                                    |
| Ngày deploy | 2026-08-10                                                |

## Biến Môi Trường Đã Set Trên Cloud

Ghi tên biến và **nguồn giá trị**, không ghi giá trị:

| Biến                | Đã set | Ghi chú                                   |
| ------------------- | ------ | ----------------------------------------- |
| `PORT`              | ✅     | platform tự gán                           |
| `API_TOKEN`         | ✅     | đặt trong dashboard, không nằm trong repo |
| `REDIS_URL`         | ✅     | Redis add-on của platform                 |
| `BUCKET_CAPACITY`   | ✅     | 10                                        |
| `REFILL_PER_MINUTE` | ✅     | 10                                        |
| `DAILY_BUDGET_USD`  | ✅     | 1.0                                       |
| `LOG_LEVEL`         | ✅     | INFO                                      |

## Lệnh Kiểm Tra

Thay `<URL>` bằng Public URL ở trên:

```bash
# 1. Liveness — mong đợi 200 {"status":"ok"}
curl -i https://k4-day12-2a202601694-vuhuutruong.up.railway.app/healthz

# 2. Readiness — mong đợi 200 {"status":"ready"} (đã nối được Redis)
curl -i https://k4-day12-2a202601694-vuhuutruong.up.railway.app/readyz

# 3. Không có token — mong đợi 401 kèm header WWW-Authenticate
curl -i -X POST https://k4-day12-2a202601694-vuhuutruong.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Hello"}'

# 4. Có token — mong đợi 200 kèm câu trả lời
curl -i -X POST https://k4-day12-2a202601694-vuhuutruong.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "X-Client-Id: sv-test" \
  -d '{"message":"Deploy là gì?"}'

# 5. Rate limit — gọi 15 lần, những lần cuối phải trả 429
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "%{http_code} " -X POST https://k4-day12-2a202601694-vuhuutruong.up.railway.app/chat \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "X-Client-Id: sv-test" \
    -d '{"message":"test"}'
done; echo
```

## Kết Quả Chạy Thật

Dán output của các lệnh trên vào đây:

```
HTTP/1.1 200 OK
content-type: application/json
{"status":"ok","service":"day12-chat-service","version":"1.0.0"}

HTTP/1.1 200 OK
content-type: application/json
{"status":"ready","redis":true}

HTTP/1.1 401 Unauthorized
www-authenticate: Bearer
{"detail":"invalid or missing bearer token"}

HTTP/1.1 200 OK
content-type: application/json
{"reply":"Theo mình hiểu, Deploy là gì?...","client_id":"sv-test","turns_before":0,"usd_cost":0.0001,"usage":{"prompt":10,"completion":25}}

200 200 200 200 200 200 200 200 200 200 429 429 429 429 429
```

## Ảnh Chụp Màn Hình

Đặt ảnh trong thư mục `screenshots/`:

- `screenshots/dashboard.png` — trang quản lý service trên platform
- `screenshots/healthz.png` — kết quả gọi `/healthz` từ trình duyệt hoặc curl
