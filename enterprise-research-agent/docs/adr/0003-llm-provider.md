# ADR-0003: Lựa chọn LLM cho Research Pipeline

**Status:** Proposed  
**Date:** 19/11/2026  
**Deciders:** Nhóm SE-AI-02 và mentor Trần Phan Đăng Khôi (Pending Review)  
**Owner:** R3 – Nguyễn Hoàng Nhân  
**Related Documents:** Requirement Specification v1.0

---

## 1. Context

Enterprise Research Agent cần LLM để lập kế hoạch nghiên cứu, trích xuất bằng chứng, tổng hợp báo cáo Markdown có trích dẫn và hỗ trợ kiểm tra nội dung trích dẫn.

Các ràng buộc chính từ Requirement Specification v1.0:

- **NFR-01:** Citation correctness ≥90% trên ít nhất 50 trích dẫn.
- **NFR-02:** Coverage ≥70% trên 30 câu hỏi, sử dụng LLM-as-Judge và kiểm tra thủ công 10 mẫu.
- **NFR-03:** p95 research job ≤180 giây.
- **NFR-04:** Retry tối đa 2 lần, không mất job khi worker restart.
- **NFR-05/06:** Quản lý secret qua biến môi trường; log `request_id`, `job_id` và thời gian từng bước.
- **NFR-08:** Hệ thống chạy bằng Docker Compose.

Nhóm có 4 tuần thực hiện, ngân sách API hiện tại bằng 0 USD và chưa xác nhận phần cứng để triển khai local LLM.

## 2. Options Considered

### Option A — Gemini 3.5 Flash-Lite qua Gemini API Free Tier

**Model:** `gemini-3.5-flash-lite`

**Ưu điểm:**
- Miễn phí trong giới hạn Free Tier.
- Tích hợp trực tiếp qua API, không cần GPU server.
- Hỗ trợ structured output cho các bước plan và extract.
- Phù hợp với kiến trúc Research Worker.

**Hạn chế:**
- Phụ thuộc Internet và Gemini API.
- Chịu giới hạn RPM, TPM và RPD.
- Chất lượng và latency cần được kiểm chứng.

**Đánh giá:** Phù hợp nhất với ngân sách, tiến độ và hạ tầng hiện tại. **Đề xuất lựa chọn cho Sprint 2.**

### Option B — Local LLM qua Ollama

**Model:** Chưa chốt.

**Ưu điểm:**
- Không phụ thuộc quota Gemini API.
- Chủ động vận hành và cấu hình model.
- Có thể triển khai trong hạ tầng do nhóm kiểm soát.

**Hạn chế:**
- Cần RAM/VRAM phù hợp.
- Chưa có phần cứng được xác nhận.
- Chưa có benchmark chất lượng và latency.

**Đánh giá:** Phương án hợp lệ nhưng chưa đủ điều kiện triển khai. **Deferred**, không bị loại do chất lượng.

### Option C — Local LLM trên Google Colab Free

**Ưu điểm:**
- Có thể thử nghiệm model mở trên GPU.
- Không cần đầu tư phần cứng để benchmark ban đầu.

**Hạn chế:**
- GPU và thời lượng phiên chạy không được bảo đảm.
- Không phù hợp làm dịch vụ LLM ổn định cho Research Worker.

**Đánh giá:** Chỉ sử dụng cho thử nghiệm, không chọn làm môi trường triển khai chính.

### Option D — OpenAI API hoặc Paid API khác

**Ưu điểm:**
- Có thêm lựa chọn model.
- Dễ tích hợp theo kiến trúc API.

**Hạn chế:**
- Phát sinh chi phí theo token.
- Nhóm chưa có ngân sách hoặc credit được xác nhận.

**Đánh giá:** Chưa lựa chọn trong điều kiện hiện tại. Chỉ xem xét nếu có ngân sách hoặc API do mentor cung cấp.

## 3. Decision

**Đề xuất dùng `gemini-3.5-flash-lite` qua Gemini API Free Tier để sinh báo cáo cho Research Worker v1 của Sprint 2.** Worker truy xuất các đoạn liên quan, đưa câu hỏi và các đoạn đã đánh số vào một lần gọi sinh báo cáo Markdown. Spike ERA-14 sẽ đo độ bao phủ ý chính, kiểm tra trích dẫn và ghi nhận độ trễ.

**Lý do lựa chọn:** Phù hợp với ngân sách API 0 USD nếu project có hạn mức miễn phí đủ dùng. Nhóm có thể tích hợp qua API trong hạ tầng hiện tại và kiểm chứng chất lượng, độ trễ trên corpus trước khi mở rộng.

**Hướng mở rộng sau Sprint 2**

| Stage | Model/Cách xử lý |
|---|---|
| Plan | `gemini-3.5-flash-lite` |
| Retrieve | Embedding model + pgvector |
| Extract | `gemini-3.5-flash-lite` |
| Write | `gemini-3.5-flash-lite` |
| Verify citations | Kiểm tra marker bằng code. Đánh giá thêm khả năng kiểm tra mức độ nguồn hỗ trợ nhận định. |
| Evaluation | Judge đề xuất `gemini-3.1-flash-lite`, theo Mục 6. |

Embedding model được lựa chọn riêng, không thuộc ADR này.

### 3.1. API Quota

Các số dưới đây là **giả định lập kế hoạch**, đang chờ xác nhận trong Google AI Studio của project nhóm. Khi xác nhận, ghi lại ngày kiểm tra, usage tier và hạn mức thực tế theo từng model. 

| Model | RPM | TPM | RPD |
|---|---:|---:|---:|
| Gemini 3.5 Flash-Lite | 15 | 250.000 | 500 |

### 3.2. LLM Calls per Job

**Sprint 2 baseline:** Một lần gọi sinh báo cáo cho lượt chạy thành công ngay lần đầu. Các lần gọi embedding, judge và retry được ghi riêng.

**Pipeline đầy đủ sau Sprint 2:** Giả định mỗi research job có 3–5 câu hỏi con. Bảng chỉ tính các lần gọi model sinh báo cáo và những bước dùng cùng model đó.

| Stage | Calls/job |
|---|---:|
| Plan | 1 |
| Retrieve | 0 |
| Extract | 3–5 |
| Write | 1 |
| Verify citations | 0–1 |
| **Tổng** | **5–8** |

Số calls thực tế phụ thuộc cách triển khai extraction và verification, sẽ được cập nhật sau spike.

### 3.3. Daily Usage Estimation

Với 40 job/ngày, baseline Sprint 2 dự kiến 40 lần gọi sinh báo cáo trước khi tính retry. Bảng dưới đây minh họa pipeline đầy đủ ở mức 8 lần gọi/job.

| Hoạt động | Jobs/ngày | Requests/ngày |
|---|---:|---:|
| Development | 20 | 160 |
| Evaluation | 15 | 120 |
| Demo/Testing | 5 | 40 |
| **Tổng** | **40** | **320** |

Nếu project có hạn mức 500 RPD cho model sinh báo cáo, kịch bản 320 lần gọi/ngày dùng khoảng 64% hạn mức, còn 180 lần theo giả định. Ước tính này chưa tính retry, embedding và judge. Các giới hạn theo phút và theo token cần kiểm tra riêng.

---

## 4. Evaluation Criteria

### 4.1. Initial Spike — 15 câu hỏi v0

| Metric | Threshold đề xuất |
|---|---|
| Coverage | ≥70% ý chính |
| Citation correctness | ≥90% trên các citation kiểm tra |
| Đầu ra Markdown | Mục tiêu 100% phản hồi nhận được vượt qua bước kiểm tra marker. Ghi riêng số lượt lỗi gọi API và số phản hồi bị từ chối. |
| Latency | p95 ≤180 giây |
| API usage | Ghi nhận calls, tokens, latency và lỗi |

Đối với latency, chạy lặp để có tối thiểu khoảng 30 job executions.

Các ngưỡng pilot được đề xuất trước khi chạy spike và cần mentor xác nhận; kết quả 15 câu v0 chưa chứng minh hệ thống đạt NFR chính thức.

### 4.2. Final Evaluation

Đánh giá trên full research pipeline:

- **NFR-01:** Citation correctness ≥90% trên ít nhất 50 trích dẫn lấy mẫu ngẫu nhiên.
- **NFR-02:** Coverage ≥70% trên 30 câu hỏi.
- **LLM-as-Judge đề xuất:** `gemini-3.1-flash-lite`, sử dụng rubric thống nhất và đối chiếu thủ công 10 mẫu.
- **NFR-03:** p95 ≤180 giây.

### 4.3. Decision Rule

Giữ Gemini 3.5 Flash-Lite làm baseline Sprint 2 nếu:

- Tích hợp thành công với Research Worker.
- Báo cáo Markdown có marker tham chiếu đúng danh sách đoạn đã truy xuất và có metadata trích dẫn tương ứng.
- Chất lượng và latency đạt các mục tiêu pilot hoặc có kế hoạch khắc phục rõ ràng.
- Quota và chi phí phù hợp nguồn lực nhóm.

Nếu không đạt, nhóm phân tích lỗi từ retrieval, prompting và generation, sau đó cải thiện và kiểm thử lại trước khi xác nhận đáp ứng NFR.

Kết quả final evaluation được sử dụng để quyết định nghiệm thu pipeline v1.0.

---

## 5. Risks & Fallback

| Rủi ro | Xử lý đề xuất cho Sprint 2 |
|---|---|
| 429 tạm thời do RPM/TPM | Adapter backoff và thử lại tối đa một lần nếu còn trong thời hạn xử lý. |
| 429 do hết quota ngày | Khi xác định được đã hết RPD, trả lỗi rõ ràng để job kết thúc. |
| Timeout hoặc lỗi mạng/API tạm thời | Áp dụng timeout cho request, ghi lỗi và chuyển lỗi tạm thời còn lại cho worker xử lý theo chính sách retry của RQ. |
| Marker ngoài danh sách đoạn nguồn | Kiểm tra bằng code và xử lý trước khi lưu báo cáo. |

Retry trong adapter tính theo **lần gọi API** của mỗi lượt chạy. Retry trong RQ tính theo **lượt chạy lại cả job**, tối đa hai lần theo NFR-04. Với các lỗi tạm thời đủ điều kiện ở cả hai tầng, một job có thể tạo tối đa sáu lần gọi sinh báo cáo theo đề xuất này: ba lượt chạy, mỗi lượt tối đa hai lần gọi.

**Hướng mở rộng:** Đánh giá Redis rate limiter dùng chung, lập lịch lại khi quota ngày được cấp lại và cơ chế phục hồi job sau khi worker khởi động lại theo Design Doc.

Không tự động chuyển sang API trả phí.

Chỉ sử dụng corpus công khai hoặc dữ liệu giả lập phù hợp giấy phép, không gửi dữ liệu khách hàng thật hay thông tin cá nhân lên Free Tier.

---

## 6. LLM-as-Judge

**Proposed Judge:** `gemini-3.1-flash-lite`

Lý do:
- Dùng model khác với generator `gemini-3.5-flash-lite` để giảm nguy cơ model tự chấm đầu ra của mình. Kết quả vẫn cần đối chiếu thủ công.
- Google có công bố Free Tier cho model này. Nhóm sẽ xác nhận mức truy cập và quota trên project trước khi chạy đánh giá. 
- Chỉ sử dụng trong evaluation, không tham gia pipeline phục vụ người dùng.

Judge sử dụng rubric và gold key points để chấm coverage trên 30 câu hỏi. Nhóm đối chiếu thủ công 10 mẫu theo NFR-02.


---

## 7. Consequences

**Lợi ích:**
- Triển khai nhanh, không yêu cầu GPU server.
- Dễ quản lý prompt, quota và lỗi.
- Có baseline thống nhất để đánh giá.

**Hạn chế:**
- Phụ thuộc Gemini API và Free Tier.
- Chất lượng và latency chưa được xác nhận trước khi chạy spike.

