# Phiếu Phản Ánh — K4 Level 3A, Ngày 12

> **Bài làm cá nhân.** Trả lời bằng lời của chính bạn, dựa trên những gì bạn
> quan sát được khi chạy code — không sao chép đáp án của người khác.
> Họ và tên: Hà Trung Dũng  Mã học viên: 2A202602948

---

### Câu 1 — Fail fast (CP1)

Trong `Settings`, `agent_api_key` không có giá trị mặc định nên app chết ngay
khi khởi động nếu thiếu biến môi trường. Hãy mô tả một tình huống cụ thể mà
việc "chết sớm" này cứu bạn, so với việc để mặc định `"changeme"`.

Nếu tôi quên cấu hình `AGENT_API_KEY` trên cloud mà trong code có sẵn giá trị mặc định như `"changeme"`, service vẫn có thể khởi động và public ra Internet với một khóa yếu hoặc dễ đoán. Khi để `agent_api_key` không có giá trị mặc định, ứng dụng dừng ngay lúc startup nếu thiếu biến môi trường. Nhờ vậy tôi phát hiện lỗi cấu hình ngay khi deploy thay vì chỉ biết sau khi service đã bị người khác gọi.

---

### Câu 2 — Log cho máy đọc (CP1)

Chạy service và gọi `/ask` vài lần. Dán một dòng log JSON bạn thu được, rồi
nêu **hai** việc bạn làm được với dòng log đó mà `print("đã trả lời xong")`
không làm được.

Một log JSON tôi quan sát được khi chạy `/ask` là:
`{"event":"ask_completed","level":"info","timestamp":"2026-09-28T08:09:15.563124+00:00","user_id":null,"tokens_in":4,"tokens_out":36,"cost_usd":2.22e-05}`
Với structured log này, tôi có thể lọc hoặc thống kê chi phí theo `user_id`, đồng thời theo dõi số token và thời điểm từng request. Nếu chỉ dùng `print("đã trả lời xong")` thì không thể truy vấn hoặc tổng hợp các thông tin đó một cách tự động.

---

### Câu 3 — Kích thước image (CP2)

Build cả hai phiên bản và ghi lại số đo thật:

```bash
docker build -f <Dockerfile-1-stage> -t agent:single .
docker build -t agent:multi .
docker images | grep agent
```

| Bản | Dung lượng |
|-----|-----------|
| 1 stage (bản đầu) | 1.7 GB |
| Multi-stage | 272 MB |

Giải thích: phần dung lượng chênh lệch đó là những gì?

Bản multi-stage nhỏ hơn rất nhiều vì image runtime không cần mang theo toàn bộ môi trường build và các thành phần không cần thiết khi chạy. Stage cuối chỉ giữ Python runtime, dependency cần thiết và source của ứng dụng. Kết quả thực tế của tôi giảm từ khoảng 1.7 GB xuống còn 272 MB.

---

### Câu 4 — Thứ tự lệnh trong Dockerfile (CP2)

Sửa một ký tự trong `app/main.py` rồi build lại. Với Dockerfile của bạn, những
layer nào được dùng lại từ cache, layer nào phải chạy lại? Nếu bạn đặt
`COPY . .` lên trước `RUN pip install` thì kết quả khác thế nào?

Trong Dockerfile của tôi, `requirements.txt` được copy và cài dependency trước khi copy toàn bộ source code. Vì vậy khi chỉ sửa một dòng trong `app/main.py`, Docker vẫn dùng lại các layer base image và layer cài dependency, chỉ các layer từ bước copy source trở đi phải chạy lại. Nếu đặt `COPY . .` trước `RUN pip install`, mỗi lần sửa source sẽ làm cache của layer copy thay đổi và Docker phải cài lại toàn bộ dependency.

---

### Câu 5 — Vì sao không chạy bằng root (CP2)

Container mặc định chạy bằng root. Mô tả chuỗi sự kiện dẫn từ "một lỗ hổng
trong code Python của bạn" tới "kẻ tấn công có quyền cao trên máy host", và
lệnh `USER` cắt đứt chuỗi đó ở chỗ nào.

Nếu code Python có lỗ hổng cho phép thực thi lệnh trong container, kẻ tấn công sẽ có quyền của user đang chạy process đó. Nếu container chạy bằng root thì mức quyền bên trong container rất cao, làm hậu quả nghiêm trọng hơn nếu tiếp tục khai thác được cấu hình hoặc lỗ hổng container runtime. Lệnh `USER appuser` làm ứng dụng chạy bằng user thường, nên ngay cả khi app bị khai thác thì quyền của attacker trong container cũng bị giới hạn.

---

### Câu 6 — Cửa sổ trượt (CP3)

Rate limit của bạn dùng sliding window 60 giây. Nếu thay bằng cách đếm theo
phút đồng hồ (reset lúc giây 00), một người dùng có thể gửi tối đa bao nhiêu
request trong 2 giây liên tiếp khi hạn mức là 10/phút? Giải thích cách đạt được
con số đó.

Nếu giới hạn là 10 request/phút nhưng đếm theo phút đồng hồ, người dùng có thể gửi 10 request lúc 10:00:59 và thêm 10 request lúc 10:01:01. Như vậy họ gửi được tối đa 20 request chỉ trong khoảng 2 giây mà mỗi phút vẫn không vượt quá 10 request. Sliding window 60 giây tránh được lỗ hổng này vì luôn đếm trong 60 giây gần nhất.

---

### Câu 7 — Rate limit và cost guard (CP3)

Hai cơ chế này khác nhau ở điểm nào? Cho một tình huống mà rate limit cho qua
nhưng cost guard phải chặn, và một tình huống ngược lại.

Rate limit giới hạn số request trong một khoảng thời gian, còn cost guard giới hạn tổng chi phí đã tiêu trong tháng. Ví dụ một user chỉ gửi vài request nhưng mỗi request rất lớn và tốn nhiều token thì rate limit vẫn cho qua nhưng cost guard có thể chặn do hết ngân sách. Ngược lại, một user gửi quá nhiều request rất nhỏ trong thời gian ngắn có thể bị rate limit chặn dù tổng chi phí tháng vẫn còn thấp.

---

### Câu 8 — /health khác /ready (CP4)

Nếu gộp hai endpoint làm một và cho nó kiểm tra Redis, chuyện gì xảy ra với cụm
3 container khi Redis mất kết nối 30 giây? Trả lời theo đúng thứ tự sự kiện.

Nếu gộp `/health` và `/ready` rồi cho endpoint đó kiểm tra Redis, khi Redis mất kết nối thì cả 3 container đều trả health check lỗi. Orchestrator có thể hiểu rằng cả 3 process đều hỏng và restart chúng, dù bản thân ứng dụng vẫn còn sống. Sau khi restart, Redis vẫn chưa hoạt động nên các container lại tiếp tục fail health check và có thể bị restart liên tục. Tách `/health` và `/ready` giúp process vẫn được xem là sống, nhưng load balancer ngừng gửi traffic tới instance chưa sẵn sàng.

---

### Câu 9 — Stateless (CP4)

Chạy `docker compose up --scale agent=3` rồi gọi `/ask` nhiều lần với cùng một
`X-User-Id`. Quan sát `history_length` trong response. Nếu lịch sử được lưu
trong một dict Python thay vì Redis, bạn sẽ thấy con số đó thay đổi thế nào?

Khi history được lưu trong Redis, các request sau vẫn nhìn thấy lịch sử trước đó dù có thể đi vào instance khác. Khi tôi test cùng `X-User-Id`, `history_length` đã tăng từ các lượt trước, cho thấy dữ liệu được giữ ngoài process. Nếu dùng một dict Python trong RAM, mỗi container sẽ có một bản history riêng nên khi request chuyển sang container khác, `history_length` có thể quay về 0 hoặc thay đổi không nhất quán.

---

### Câu 10 — Deploy thật (CP5)

Ghi lại **một** lỗi bạn gặp khi deploy lên cloud (build fail, health check
timeout, sai REDIS_URL, app không đọc `$PORT`...): thông báo lỗi là gì, bạn
tìm ra nguyên nhân bằng cách nào, và sửa ra sao?

Sau khi deploy lên Railway, `/health` và `/ready` đều trả 200 nhưng lần đầu tôi test `/ask` có xác thực lại nhận 401 `invalid or missing API key`. Tôi kiểm tra lại và phát hiện biến `DEPLOY_API_KEY` ở PowerShell chưa dùng đúng giá trị `AGENT_API_KEY` đang cấu hình trên Railway. Sau khi đặt lại biến local bằng đúng key production và gửi request đúng định dạng JSON, `/ask` trả 200, có `user_id`, `history_length`, `cost_usd` và thống kê token.
