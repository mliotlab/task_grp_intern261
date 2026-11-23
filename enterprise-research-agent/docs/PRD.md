# PRD – Enterprise Research Agent

**Trạng thái:** Draft  
**Phiên bản:** v1.0  
**Ngày soạn:** 18/11/2026  
**Mã nhóm:** SE-AI-02  
**Track:** Software Engineering · AI Engineering  
**Mentor:** Trần Phan Đăng Khôi  
**Tài liệu nguồn:** *Enterprise Research Agent – Requirement Specification v1.0*

## 1. Bối cảnh và vấn đề

### 1.1 Bối cảnh

Nhân viên trong doanh nghiệp thường mất nhiều giờ để trả lời một câu hỏi cần đọc nhiều tài liệu nội bộ: quy trình, báo cáo kỹ thuật, biên bản họp, tài liệu sản phẩm. Các *research agent* dựa trên LLM có thể tự chia câu hỏi thành các câu hỏi con, tìm tài liệu liên quan, đọc và tổng hợp thành báo cáo có trích dẫn, giúp rút ngắn thời gian này.

Đề tài xây dựng một nền tảng như vậy với trọng tâm *software engineering*: kiến trúc nhiều service, xử lý tác vụ dài bất đồng bộ qua hàng đợi, API contract, xác thực người dùng, giao diện web, kiểm thử nhiều tầng và CI/CD. Thành phần AI được giữ đơn giản và đo lường được.

### 1.2 Vấn đề cần giải quyết

Người dùng cần một nơi để:

1. Tải tài liệu lên và tổ chức tài liệu thành các bộ sưu tập.
2. Gửi câu hỏi nghiên cứu dựa trên một bộ sưu tập.
3. Theo dõi tiến trình xử lý bất đồng bộ.   
4. Nhận báo cáo có cấu trúc, kèm trích dẫn tới đúng tài liệu và vị trí nguồn (trang/mục).
5. Chỉ truy cập được tài liệu, bộ sưu tập và báo cáo thuộc quyền của chính mình.

### 1.3 Mục tiêu sản phẩm

Xây dựng ứng dụng web cho phép người dùng đăng nhập, quản lý tài liệu và bộ sưu tập, gửi câu hỏi nghiên cứu, theo dõi tác vụ và đọc báo cáo có trích dẫn. Backend gồm API, worker xử lý tài liệu và worker nghiên cứu chạy qua hàng đợi; dữ liệu được lưu trong cơ sở dữ liệu có vector search. Chất lượng sản phẩm được kiểm chứng bằng API contract, kiểm thử tự động và các chỉ số chất lượng/hiệu năng đã định nghĩa trong tài liệu yêu cầu.

## 2. Người dùng và persona

Các persona dưới đây đại diện cho ba nhóm người dùng mục tiêu được nêu trong Requirement Specification và nhu cầu, mục tiêu diễn giải nhóm người dùng đó.

### Persona 1 – Chuyên viên phân tích (Analyst)

- **Vai trò:** Người thường xuyên nghiên cứu thông tin từ nhiều tài liệu kỹ thuật, quy trình hoặc báo cáo.
- **Mục tiêu:** Tổng hợp thông tin nhanh từ một hoặc nhiều tài liệu; nhận báo cáo có cấu trúc; kiểm tra được nguồn hỗ trợ cho từng nhận định.
- **Nỗi đau:** Phải đọc nhiều tài liệu thủ công; mất thời gian tìm đoạn liên quan; khó xác minh một kết luận nếu không có trích dẫn tới tài liệu và trang/mục.
- **Nhu cầu chính:** Quản lý bộ sưu tập, tải tài liệu, gửi câu hỏi, theo dõi trạng thái và mở trích dẫn nguồn.

### Persona 2 – Quản lý (Manager)

- **Vai trò:** Người cần thông tin tóm tắt để hỗ trợ việc ra quyết định.
- **Mục tiêu:** Nắm được tóm tắt và các phát hiện chính; xem lại báo cáo nghiên cứu trước đó.
- **Nỗi đau:** Không có đủ thời gian đọc toàn bộ tài liệu gốc; khó tra cứu lại kết quả nghiên cứu đã thực hiện.
- **Nhu cầu chính:** Đọc báo cáo có phần tóm tắt, phát hiện và kết luận; truy cập lịch sử báo cáo và tìm kiếm theo câu hỏi.

### Persona 3 – Quản trị hệ thống (System Administrator)

- **Vai trò:** Người triển khai và theo dõi hoạt động của hệ thống, đặc biệt là API, worker và các tác vụ lỗi.
- **Mục tiêu:** Theo dõi tình trạng hệ thống và tác vụ; hỗ trợ phát hiện lỗi và vận hành hệ thống có thể tái lập.
- **Nỗi đau:** Tác vụ chạy bất đồng bộ có thể kéo dài hoặc thất bại; cần log và số liệu để theo dõi xuyên suốt quá trình xử lý.
- **Nhu cầu chính:** Hệ thống có log JSON chứa `request_id` và `job_id`, số liệu về trạng thái tác vụ, thời gian từng bước và tỷ lệ lỗi; có thể khởi chạy theo hướng dẫn triển khai.
- **Lưu ý phạm vi:** Requirement Specification xác định quản trị hệ thống là nhóm người dùng mục tiêu và yêu cầu khả năng quan sát/triển khai; tài liệu hiện tại chưa mô tả một trang quản trị riêng.

## 3. User stories

User stories được viết theo mẫu “Là [persona], tôi muốn [hành động] để [lợi ích]”. Acceptance Criteria sử dụng Given/When/Then để kiểm chứng hành vi. Các mã US bên dưới được dùng để truy vết từ User Story tới FR.

### US-01 – Đăng ký và đăng nhập

**Liên quan:** FR-01
**User Story:** Là người dùng, tôi muốn đăng ký và đăng nhập bằng email và mật khẩu để sử dụng các chức năng nghiên cứu trong phạm vi tài khoản của mình.

**Acceptance Criteria:**

- **Given** người dùng chưa có phiên đăng nhập, **When** họ gửi thông tin đăng ký hợp lệ đến Register API mà không có JWT, **Then** hệ thống cho phép tạo tài khoản bằng email và mật khẩu.
- **Given** người dùng đã có tài khoản, **When** họ đăng nhập bằng email và mật khẩu hợp lệ, **Then** hệ thống xác thực người dùng bằng JWT có thời hạn.
- **Given** một request gọi API, **When** request không thuộc Register API, Login API hoặc `/health` và không có token hợp lệ, **Then** request không được phép truy cập API đó.

### US-02 – Tải và tổ chức tài liệu

**Liên quan:** FR-02, FR-06
**User Story:** Là chuyên viên phân tích, tôi muốn tải tài liệu PDF, DOCX hoặc Markdown vào một bộ sưu tập để dùng các tài liệu đó làm nguồn nghiên cứu.

**Acceptance Criteria:**

- **Given** người dùng đã đăng nhập, **When** họ tạo một bộ sưu tập với tên hợp lệ, **Then** hệ thống lưu bộ sưu tập thuộc quyền sở hữu của người dùng và hiển thị bộ sưu tập trong danh sách của họ.
- **Given** người dùng đã đăng nhập và có một hoặc nhiều bộ sưu tập, **When** họ xem danh sách bộ sưu tập, **Then** hệ thống chỉ hiển thị các bộ sưu tập thuộc quyền sở hữu của họ.
- **Given** người dùng đã đăng nhập và có ít nhất một bộ sưu tập, **When** họ tải lên một file PDF, DOCX hoặc Markdown có dung lượng không vượt quá 20 MB và chọn một bộ sưu tập thuộc quyền sở hữu của mình, **Then** hệ thống tiếp nhận file vào bộ sưu tập được chọn.
- **Given** file đã được tiếp nhận, **When** quá trình xử lý bất đồng bộ bắt đầu, **Then** hệ thống thực hiện trích xuất văn bản, chia đoạn, tạo embedding và đánh chỉ mục.
- **Given** một tài liệu đã được tải lên, **When** người dùng xem trạng thái tài liệu, **Then** giao diện thể hiện trạng thái thuộc một trong các giá trị `queued`, `processing`, `ready` hoặc `failed`.
- **Given** file không thuộc PDF/DOCX/Markdown hoặc có dung lượng lớn hơn 20 MB, **When** người dùng tải file lên, **Then** file không được chấp nhận theo giới hạn loại và dung lượng file của hệ thống.

### US-03 – Gửi câu hỏi nghiên cứu

**Liên quan:** FR-03  
**User Story:** Là chuyên viên phân tích, tôi muốn gửi một câu hỏi nghiên cứu kèm bộ sưu tập để hệ thống xử lý câu hỏi đó bất đồng bộ trên worker.

**Acceptance Criteria:**

- **Given** người dùng đã đăng nhập và chọn bộ sưu tập, **When** họ gửi câu hỏi nghiên cứu qua `POST /v1/research` với nội dung câu hỏi và bộ sưu tập, **Then** API trả về một `job_id`.
- **Given** câu hỏi đã được tiếp nhận, **When** tác vụ được tạo, **Then** tác vụ được đưa vào quy trình xử lý bất đồng bộ trên worker thay vì yêu cầu người dùng chờ một request đồng bộ kéo dài.

### US-04 – Theo dõi tiến trình nghiên cứu

**Liên quan:** FR-04, FR-06  
**User Story:** Là chuyên viên phân tích, tôi muốn theo dõi trạng thái và các bước đã hoàn thành của tác vụ để biết quá trình nghiên cứu đang ở đâu.

**Acceptance Criteria:**

- **Given** người dùng có `job_id`, **When** họ truy vấn `GET /v1/research/{id}`, **Then** API trả về trạng thái thuộc một trong các giá trị `queued`, `running`, `succeeded` hoặc `failed` (thêm `cancelled` cho FR-10 khi người dùng hủy tác vụ, xem US-09) cùng các bước đã hoàn thành.
- **Given** một tác vụ đang được xử lý, **When** người dùng mở màn hình theo dõi, **Then** giao diện cập nhật tiến trình bằng polling hoặc SSE.
- **Given** tác vụ đã kết thúc, **When** người dùng xem lại trạng thái, **Then** giao diện thể hiện trạng thái kết thúc tương ứng là `succeeded`, `failed` hoặc `cancelled`.

### US-05 – Tạo báo cáo có cấu trúc và trích dẫn

**Liên quan:** FR-05, FR-06  
**User Story:** Là chuyên viên phân tích, tôi muốn nhận báo cáo nghiên cứu có tóm tắt, phát hiện, kết luận và trích dẫn để kiểm tra thông tin dựa trên tài liệu nguồn.

**Acceptance Criteria:**

- **Given** một tác vụ nghiên cứu được xử lý, **When** research pipeline thực thi, **Then** pipeline chia câu hỏi thành các câu hỏi con và truy xuất các đoạn liên quan cho từng câu hỏi con.
- **Given** quá trình tổng hợp hoàn tất, **When** báo cáo được tạo, **Then** báo cáo ở định dạng Markdown và có cấu trúc gồm tóm tắt, các phát hiện và kết luận.
- **Given** báo cáo đưa ra nhận định dựa trên tài liệu, **When** người dùng xem báo cáo, **Then** nhận định có trích dẫn theo dạng `[tài liệu, trang/mục]` để chỉ tới vị trí nguồn.
- **Given** người dùng đang xem báo cáo trên web, **When** họ chọn một trích dẫn, **Then** giao diện mở đoạn nguồn tương ứng.

### US-06 – Bảo vệ dữ liệu theo người dùng

**Liên quan:** FR-07  
**User Story:** Là người dùng, tôi muốn chỉ nhìn thấy tài liệu, bộ sưu tập và báo cáo của mình để dữ liệu của tôi không bị người dùng khác truy cập.

**Acceptance Criteria:**

- **Given** người dùng A và người dùng B có dữ liệu riêng, **When** người dùng A truy cập tài liệu, bộ sưu tập hoặc báo cáo thuộc B, **Then** hệ thống từ chối truy cập.
- **Given** người dùng đã đăng nhập, **When** họ truy vấn danh sách hoặc nội dung tài liệu, bộ sưu tập và báo cáo, **Then** hệ thống chỉ trả về dữ liệu thuộc người dùng đó.
- **Given** người dùng A gửi câu hỏi nghiên cứu với bộ sưu tập do A sở hữu, **When** Research Worker truy xuất evidence cho các câu hỏi con, **Then** mọi document chunk được trả về phải thuộc bộ sưu tập được A chọn và không chứa chunk thuộc dữ liệu của người dùng B.
- **Given** Research Worker đã tạo báo cáo cho người dùng A, **When** A xem hoặc mở một citation trong báo cáo, **Then** nội dung citation và đoạn nguồn được trả về chỉ tham chiếu đến tài liệu mà A được phép truy cập.
- **Given** có endpoint yêu cầu xác thực hoặc thao tác truy xuất dữ liệu trong worker, **When** một người dùng cố truy cập dữ liệu không thuộc quyền của mình, **Then** hệ thống phải kiểm tra quyền tương ứng và hành vi truy cập trái phép có test kiểm chứng.

### US-07 – Xem lịch sử nghiên cứu

**Liên quan:** FR-08  
**User Story:** Là quản lý, tôi muốn xem danh sách báo cáo nghiên cứu cũ và tìm kiếm theo câu hỏi để tra cứu lại kết quả trước đây.

**Acceptance Criteria:**

- **Given** người dùng có các báo cáo nghiên cứu đã lưu, **When** họ mở lịch sử nghiên cứu, **Then** hệ thống hiển thị danh sách các báo cáo cũ.
- **Given** lịch sử có nhiều báo cáo, **When** người dùng tìm kiếm theo câu hỏi, **Then** hệ thống trả về các báo cáo phù hợp với câu hỏi tìm kiếm.

### US-08 – Xuất báo cáo

**Liên quan:** FR-09  
**User Story:** Là người dùng, tôi muốn xuất báo cáo nghiên cứu ra Markdown hoặc PDF để lưu trữ và chia sẻ theo nhu cầu.

**Acceptance Criteria:**

- **Given** người dùng đang xem một báo cáo, **When** họ chọn xuất Markdown, **Then** hệ thống cung cấp bản xuất định dạng Markdown.
- **Given** người dùng đang xem một báo cáo, **When** họ chọn xuất PDF, **Then** hệ thống cung cấp bản xuất định dạng PDF.

### US-09 – Hủy hoặc chạy lại tác vụ

**Liên quan:** FR-10  
**User Story:** Là người dùng, tôi muốn hủy một tác vụ đang chạy hoặc chạy lại một tác vụ bị lỗi để chủ động xử lý các lần nghiên cứu không còn cần thiết hoặc không thành công.

**Acceptance Criteria:**

- **Given** một tác vụ đang chạy, **When** người dùng yêu cầu hủy tác vụ, **Then** hệ thống xử lý yêu cầu hủy bất đồng bộ để dừng quá trình xử lý; sau khi dừng, tác vụ được ghi nhận ở trạng thái `cancelled` vì đã hủy.
- **Given** một tác vụ đã ở trạng thái `failed`, **When** người dùng yêu cầu chạy lại, **Then** hệ thống cho phép khởi chạy lại tác vụ lỗi.

### US-10 – Bật/tắt tìm kiếm web cho tác vụ

**Liên quan:** FR-11  
**User Story:** Là chuyên viên phân tích, tôi muốn bật hoặc tắt tool tìm kiếm web theo từng tác vụ để sử dụng nguồn web khi cần.

**Acceptance Criteria:**

- **Given** người dùng tạo một tác vụ nghiên cứu, **When** họ cấu hình tùy chọn tìm kiếm web, **Then** tác vụ có thể được thiết lập bật hoặc tắt tool tìm kiếm web.
- **Given** một báo cáo có sử dụng nguồn web, **When** người dùng xem báo cáo, **Then** nguồn web được đánh dấu riêng để phân biệt với nguồn tài liệu trong bộ sưu tập.

### US-11 – Đánh giá báo cáo

**Liên quan:** FR-12  
**User Story:** Là người dùng, tôi muốn đánh giá báo cáo là hữu ích hoặc không hữu ích và có thể ghi chú để cung cấp phản hồi cho tập đánh giá.

**Acceptance Criteria:**

- **Given** người dùng đang xem một báo cáo, **When** họ gửi đánh giá hữu ích hoặc không hữu ích, **Then** hệ thống ghi nhận lựa chọn đánh giá đó.
- **Given** người dùng muốn giải thích đánh giá, **When** họ gửi kèm ghi chú, **Then** ghi chú được lưu cùng phản hồi để bổ sung tập đánh giá.

## 4. Yêu cầu chức năng (Functional Requirements)

Các yêu cầu dưới đây được tổng hợp từ Mục 3.1 của Requirement Specification. ID, mô tả cốt lõi và mức ưu tiên được giữ theo tài liệu nguồn. Cột User Story thể hiện truy vết trong PRD này.

| ID | Yêu cầu chức năng | Ưu tiên | User Story |
|---|---|---|---|
| FR-01 | Đăng ký, đăng nhập bằng email và mật khẩu; xác thực bằng JWT có thời hạn; mọi API (trừ đăng ký, đăng nhập và `/health`) yêu cầu token. | Must | US-01 |
| FR-02 | Tải tài liệu PDF/DOCX/Markdown (tối đa 20 MB mỗi file) vào bộ sưu tập; xử lý bất đồng bộ (trích văn bản, chia đoạn, embedding, đánh chỉ mục); xem trạng thái từng tài liệu (`queued`, `processing`, `ready`, `failed`). | Must | US-02 |
| FR-03 | Gửi câu hỏi nghiên cứu `POST /v1/research` (câu hỏi, bộ sưu tập), nhận `job_id`; tác vụ chạy bất đồng bộ trên worker. | Must | US-03 |
| FR-04 | Theo dõi tác vụ `GET /v1/research/{id}`: trạng thái (`queued`, `running`, `succeeded`, `failed`) và các bước đã hoàn thành; giao diện cập nhật tiến trình (polling hoặc SSE). | Must | US-04 |
| FR-05 | Research pipeline: chia câu hỏi thành câu hỏi con, truy xuất đoạn liên quan cho từng câu hỏi con, tổng hợp báo cáo Markdown có cấu trúc (tóm tắt, các phát hiện, kết luận) với trích dẫn dạng `[tài liệu, trang/mục]`. | Must | US-05 |
| FR-06 | Giao diện web: quản lý tài liệu và bộ sưu tập, gửi câu hỏi, xem tiến trình, đọc báo cáo, bấm vào trích dẫn để xem đoạn nguồn. | Must | US-02, US-03, US-04, US-05 |
| FR-07 | Phân quyền dữ liệu: người dùng chỉ thấy tài liệu, bộ sưu tập và báo cáo của mình. | Must | US-06 |
| FR-08 | Lịch sử nghiên cứu: danh sách báo cáo cũ, tìm kiếm theo câu hỏi. | Should | US-07 |
| FR-09 | Xuất báo cáo ra Markdown và PDF. | Should | US-08 |
| FR-10 | Hủy tác vụ đang chạy; chạy lại tác vụ lỗi. | Should | US-09 |
| FR-11 | Tool tìm kiếm web (bật/tắt theo tác vụ), nguồn web được đánh dấu riêng trong báo cáo. | Could | US-10 |
| FR-12 | Người dùng đánh giá báo cáo (hữu ích / không hữu ích, kèm ghi chú) để bổ sung tập đánh giá. | Could | US-11 |

**Quy ước ưu tiên MoSCoW:** Must bắt buộc có trong bản phát hành v1.0.0; Should nên có, chỉ bỏ khi được mentor đồng ý; Could làm nếu còn thời gian. Mỗi yêu cầu phải được truy vết tới issue trên board và tới test case tương ứng.

## 5. Yêu cầu phi chức năng (Non-functional Requirements)

Các chỉ tiêu dưới đây được giữ theo Mục 3.2 của Requirement Specification. Tài liệu nguồn yêu cầu các chỉ tiêu được đo và báo cáo trong Evaluation Report (Sprint 3) và Release Notes (Sprint 4). NFR không được gán mức Must/Should/Could trong tài liệu nguồn, vì vậy PRD không tự bổ sung mức ưu tiên.

| ID | Thuộc tính | Chỉ tiêu và cách đo |
|---|---|---|
| NFR-01 | Độ chính xác trích dẫn | Kiểm tra thủ công ít nhất 50 trích dẫn ngẫu nhiên; ít nhất 90% trích dẫn phải thực sự hỗ trợ nhận định đi kèm. |
| NFR-02 | Chất lượng báo cáo | Trên tập 30 câu hỏi có danh sách ý chính tham chiếu, báo cáo bao phủ ít nhất 70% ý chính; chấm bằng LLM-as-judge và kiểm tra thủ công 10 mẫu. |
| NFR-03 | Hiệu năng | p95 thời gian một tác vụ nghiên cứu không quá 3 phút; p95 các API đồng bộ không quá 300 ms; xử lý tài liệu PDF 100 trang không quá 2 phút. |
| NFR-04 | Độ tin cậy | Tác vụ lỗi được thử lại tối đa 2 lần; khởi động lại worker không làm mất tác vụ; xử lý tài liệu idempotent (tải lại cùng file không tạo bản trùng). |
| NFR-05 | Bảo mật | Mật khẩu được băm bằng bcrypt/argon2; JWT có hạn; kiểm tra quyền ở mọi endpoint và có test cho truy cập trái phép; giới hạn loại và dung lượng file; secret được cung cấp qua biến môi trường. |
| NFR-06 | Quan sát được | Log JSON có `request_id` và `job_id` xuyên suốt API và worker; có số liệu về số tác vụ theo trạng thái, thời gian từng bước và tỷ lệ lỗi. |
| NFR-07 | Bảo trì | OpenAPI spec được commit và kiểm tra trong CI; coverage backend ít nhất 70%; frontend vượt qua lint và type check. |
| NFR-08 | Triển khai | `docker compose up` khởi động frontend, API, worker, PostgreSQL (pgvector), Redis; CI build image cho mọi service. |

## 6. Chỉ số thành công

Sản phẩm được xem xét theo các chỉ số định lượng dưới đây. Các ngưỡng NFR giữ nguyên từ tài liệu; các mục kiểm tra FR Must phản ánh mục tiêu v1.0.0 và tiêu chí kết thúc Sprint 3.

| Nhóm | Metric | Mục tiêu | Cách đo / bằng chứng |
|---|---|---|---|
| Chức năng | Mức hoàn thành FR Must (FR-01 đến FR-07) | Tất cả FR Must đạt Acceptance Criteria trước khi phát hành v1.0.0. | Đối chiếu từng FR với issue, test case và kết quả demo; kiểm tra tiêu chí Sprint 3. |
| Trích dẫn | NFR-01 – tỷ lệ trích dẫn hỗ trợ nhận định | ≥ 90% trên ít nhất 50 trích dẫn ngẫu nhiên. | Kiểm tra thủ công mẫu trích dẫn và nhận định đi kèm. |
| Chất lượng báo cáo | NFR-02 – tỷ lệ bao phủ ý chính | ≥ 70% trên bộ 30 câu hỏi. | LLM-as-judge; kiểm tra thủ công 10 mẫu. |
| Hiệu năng | NFR-03 – p95 thời gian tác vụ nghiên cứu | ≤ 3 phút. | Đo p95 trên các lần chạy tác vụ nghiên cứu. |
| Hiệu năng | NFR-03 – p95 API đồng bộ | ≤ 300 ms. | Đo p95 thời gian phản hồi API đồng bộ. |
| Hiệu năng | NFR-03 – thời gian xử lý PDF 100 trang | ≤ 2 phút. | Đo thời gian xử lý tài liệu PDF 100 trang. |
| Độ tin cậy | NFR-04 – retry, phục hồi worker, idempotency | Tối đa 2 lần retry cho tác vụ lỗi; tác vụ không mất khi worker khởi động lại; tải lại cùng file không tạo bản trùng. | Kiểm thử retry, khởi động lại worker và tải lặp cùng file. |
| Bảo mật | NFR-05 – kiểm soát truy cập và bảo vệ thông tin xác thực | Đạt toàn bộ điều kiện bảo mật được liệt kê trong NFR-05. | Kiểm tra cấu hình hash/JWT/secret, giới hạn file và test truy cập trái phép ở endpoint. |
| Quan sát được | NFR-06 – log và metrics | Có đủ `request_id`, `job_id` và ba nhóm số liệu: trạng thái tác vụ, thời gian từng bước, tỷ lệ lỗi. | Kiểm tra log JSON và số liệu từ API/worker. |
| Bảo trì | NFR-07 – OpenAPI, coverage, frontend checks | OpenAPI được commit và kiểm tra trong CI; coverage backend ≥ 70%; frontend lint và type check đạt. | Kết quả CI và báo cáo coverage. |
| Triển khai | NFR-08 – khởi chạy và build image | `docker compose up` khởi động đủ frontend, API, worker, PostgreSQL (pgvector), Redis; CI build image cho mọi service. | Chạy từ bản clone mới và kiểm tra pipeline CI. |

**Lưu ý về phạm vi ưu tiên:** FR-08, FR-09 và FR-10 là Should; FR-11 và FR-12 là Could. Không xem các yêu cầu này là điều kiện Must của v1.0.0 nếu chưa có quyết định thay đổi được đồng ý.

## 7. Ngoài phạm vi (Non-goals)

Các nội dung sau không thuộc phạm vi của đề tài theo Requirement Specification:

- Single sign-on (SSO), phân quyền theo tổ chức nhiều cấp, multi-tenant production.
- Kết nối nguồn dữ liệu doanh nghiệp thật (SharePoint, Google Drive hoặc Confluence).
- Fine-tune LLM, huấn luyện model embedding.
- Triển khai production trên cloud với tính sẵn sàng cao.

Ngoài ra, hệ thống sử dụng bộ tài liệu công khai hoặc dữ liệu giả lập do nhóm tạo; không sử dụng dữ liệu thật của khách hàng hoặc dữ liệu cá nhân.

## 8. Giả định, phụ thuộc, rủi ro

### 8.1 Giả định và ràng buộc

1. **LLM:** Đề xuất dùng Gemini 3.5 Flash-Lite qua Gemini API Free Tier. Lựa chọn này chưa chốt: ADR-0003 đang ở trạng thái Proposed, chờ mentor duyệt.
2. **Bộ tài liệu:** 50–100 tài liệu công khai thuộc chủ đề NIST SP 800. Mentor đã đồng ý chủ đề; danh sách tài liệu cụ thể đang chờ mentor duyệt.
3. **Tập đánh giá:** Nhóm tự xây dựng tập gồm 30 câu hỏi nghiên cứu; mỗi câu có danh sách ý chính tham chiếu và tài liệu nguồn.
4. **Dữ liệu:** Chỉ dùng dữ liệu công khai hoặc dữ liệu giả lập do nhóm tạo; không dùng dữ liệu thật của khách hàng hoặc dữ liệu cá nhân.
5. **Secret:** Không commit API key, mật khẩu hoặc secret lên repository. Dùng `.env` (không commit) và `.env.example` (có commit).
6. **Giấy phép:** Tuân thủ giấy phép của dataset, model và thư viện; ghi rõ trong README và Release Notes.
7. **Công nghệ tham chiếu:** Backend, queue, database, document parser, AI, frontend, testing và hạ tầng có các gợi ý trong Requirement Specification. Đây là công nghệ tham chiếu, không phải quyết định cuối cùng; thay đổi quan trọng phải được ghi thành ADR và mentor review.

### 8.2 Phụ thuộc

- Mentor chốt lựa chọn LLM qua ADR-0003 (đề xuất hiện tại ở Mục 8.1).
- Mentor duyệt danh sách 50–100 tài liệu NIST SP 800 do nhóm gửi (mã số, phiên bản, link, giấy phép).
- Nhóm xây dựng tập đánh giá 30 câu hỏi cùng ý chính tham chiếu và tài liệu nguồn.
- Nhóm thống nhất công nghệ cụ thể và các quyết định kiến trúc trong Sprint 1–2 thông qua Design Doc/OpenAPI/ADR.
- Repo GitHub (Pull Request workflow, CI) và Jira (board theo dõi issue và sprint) là nền tảng để theo dõi yêu cầu, kiểm thử và review tài liệu.

### 8.3 Rủi ro

| ID | Rủi ro | Ảnh hưởng | Hướng giảm thiểu / theo dõi |
|---|---|---|---|
| RSK-01 | LLM hoặc embedding không đáp ứng chất lượng trích dẫn và độ bao phủ ý chính. | Báo cáo có thể thiếu ý hoặc có nhận định không được nguồn hỗ trợ; ảnh hưởng NFR-01/NFR-02. | Chốt model sớm trong Sprint 1; chạy spike RAG trên 10 tài liệu; đánh giá bằng tập câu hỏi và kiểm tra thủ công trích dẫn. |
| RSK-02 | Thời gian xử lý tài liệu hoặc research task vượt ngưỡng. | Không đạt NFR-03. | Đo thời gian từng bước; theo dõi p95; tối ưu các bước gây chậm và đo lại. |
| RSK-03 | Tác vụ bất đồng bộ bị mất hoặc tạo kết quả trùng khi worker khởi động lại/tài liệu được tải lại. | Không đạt NFR-04 và làm gián đoạn trải nghiệm người dùng. | Kiểm thử retry, worker restart và idempotency; lưu trạng thái tác vụ bền vững theo thiết kế hệ thống. |
| RSK-04 | Kiểm tra quyền không được áp dụng nhất quán ở các endpoint. | Người dùng có thể truy cập dữ liệu của người khác; ảnh hưởng FR-07/NFR-05. | Kiểm tra quyền ở mọi endpoint; có integration test chứng minh người dùng A không đọc được dữ liệu của B. |
| RSK-05 | Bộ dữ liệu công khai không đủ chất lượng, không phù hợp giấy phép hoặc không hỗ trợ 30 câu hỏi đánh giá. | Giảm độ tin cậy của kết quả evaluation. | Chọn một chủ đề thống nhất; kiểm tra nguồn/giấy phép; xin mentor duyệt bộ tài liệu trước khi dùng. |

*Các rủi ro trên là phân tích rủi ro ban đầu của PRD dựa trên các chỉ tiêu và ràng buộc trong Requirement Specification; cần cập nhật xác suất, mức ảnh hưởng và biện pháp xử lý khi lập kế hoạch sprint.*

### 8.4 Phân công trách nhiệm R1–R4

Requirement Specification quy định bốn vai trò chính và trách nhiệm vì vậy PRD ghi nhận trách nhiệm theo role:

| Vai trò | Tên vai trò | Trách nhiệm chính theo Requirement Specification | Thành viên phụ trách |
|---|---|---|---|
| R1 | Backend & API | Thiết kế API contract, xác thực/phân quyền, data model và migration, API tác vụ; review thiết kế backend. | Nguyễn Huỳnh Gia Bảo |
| R2 | Data & Retrieval | Ingestion worker, chia đoạn và embedding, pgvector, chất lượng truy xuất, bộ tài liệu. | Huỳnh Nguyễn Huy Hoàng |
| R3 | Agent & Evaluation | Research worker (lập kế hoạch, tổng hợp, trích dẫn), prompt, tập đánh giá và eval harness, Evaluation Report. | Nguyễn Hoàng Nhân |
| R4 | Frontend & DevOps/QA | Giao diện web, Docker Compose, CI/CD, test end-to-end và test tải, Runbook. | Nguyễn Gia Huy |

**Nguyên tắc phối hợp:** Mỗi Pull Request do một thành viên ở vai trò khác review; thiết kế API contract và data model được cả nhóm review trước khi code. Vai trò Scrum Master luân phiên mỗi sprint; người đảm nhiệm điều phối Sprint Planning/Review, cập nhật board, viết WSR và ghi biên bản quyết định.

## 9. Câu hỏi còn mở

Các câu hỏi dưới đây chưa được chốt trong Requirement Specification hoặc cần nhóm xác nhận trước/khi hoàn thiện Design Doc và OpenAPI contract:

1. **LLM cụ thể:** Model và cấu hình LLM cần được chốt trong Sprint 1 và ghi ADR. Trạng thái: nhóm đề xuất Gemini 3.5 Flash-Lite qua Gemini API Free Tier; ADR-0003 đang Proposed, chờ mentor chốt.
2. **Embedding model:** Sẽ dùng model embedding đa ngôn ngữ nào? Requirement Specification mới nêu yêu cầu model đa ngôn ngữ, nhóm đề xuất Gemini-embedding-2. Trạng thái: chờ mentor chốt; Design Doc chờ ADR-0004 sau spike RAG.
3. **Bộ tài liệu:** Danh sách 50–100 tài liệu cụ thể đã được mentor duyệt chưa? Trạng thái: mentor đã đồng ý chủ đề NIST SP 800; nhóm gửi danh sách tài liệu (mã số, phiên bản, link, giấy phép) để mentor duyệt, sau đó cập nhật Mục 8.1.
4. **Thống nhất ý chính tham chiếu:** Theo Requirement Specification, R3 phụ trách tập 30 câu hỏi đánh giá. Cần thống nhất cách xác định và duyệt chéo ý chính tham chiếu cho từng câu (ai duyệt, tiêu chí thế nào là đủ ý) trước khi chấm NFR-02.
5. **Chi tiết bộ sưu tập và tài liệu:** Các thao tác quản lý cụ thể (ví dụ đổi tên/xóa bộ sưu tập hoặc xóa tài liệu) chưa được mô tả chi tiết trong FR; cần xác nhận trước khi chốt API/UI.
6. **Chính sách tài khoản:** Chính sách mật khẩu, thời hạn JWT cụ thể và quy trình xử lý khi token hết hạn chưa được định lượng trong Requirement Specification.
7. **Hủy và chạy lại tác vụ:** Quy tắc xử lý khi yêu cầu hủy đến sau khi worker đã bắt đầu một bước, cũng như cách liên kết lần chạy lại với báo cáo cũ, cần được thống nhất khi thiết kế.
8. **Tìm kiếm web và phản hồi:** Phạm vi tool tìm kiếm web, cách lưu ghi chú đánh giá và cách bổ sung feedback vào tập đánh giá cần được xác nhận nếu thực hiện FR-11/FR-12 (mức Could).

---

## Thông tin review

| Người review | Trạng thái | Nhận xét / ngày review |
|---|---|---|
| Nguyễn Hoàng Nhân (R3) | Đã review | Review PR #27. |
| Mentor – Trần Phan Đăng Khôi | Approve | Chờ mentor review/approve theo quy trình tài liệu của dự án. |
