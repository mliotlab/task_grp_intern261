# Weekly Status Report – Sprint 1 

> **Dự án:** Enterprise Research Agent (ERA)  
> **Sprint:** Sprint 1 – Discovery & Design, 16/11/2026–23/11/2026 (theo Jira)  
> **Scrum Master:** Nguyễn Hoàng Nhân  
> **Trạng thái:** **RED**  
> **Thời điểm cập nhật:** 22/11/2026
> **Trạng thái tài liệu:** Draft – cần xác minh và góp từ mentor trước khi merge

## 1. TL;DR

Sprint 1 **không đạt Sprint Goal theo tiêu chí hoàn thành trong Requirement Specification**. Nhóm đã có hoạt động thiết kế, nghiên cứu nguồn tài liệu, xây dựng các thành phần ban đầu của RAG và thiết lập công cụ. Tuy nhiên, nhiều kết quả chưa được merge vào nhánh main của repository chung, các tài liệu cần mentor phê duyệt vẫn đang trong quá trình review, RAG spike chưa hoàn tất end-to-end.

Tại thời điểm cập nhật, Jira ghi nhận **13 work items**, tổng **26 giờ ước lượng**, và GitHub ghi nhận **1 PR đã merge: #29 (ERA-10 – PDF Parsing & Chunking)**. Ba mục tài liệu ERA-6/7/8 đang ở trạng thái **Review trên Jira** và **PR** trên Github. 

Nhóm tiếp tục sử dụng **Jira để quản lý sprint, issue, assignee và estimate** (đã được mentor chấp thuận) và **GitHub để lưu mã nguồn, tài liệu, thực hiện PR/review, chạy CI và chứng minh Done**. Mã `ERA-n` dùng liên kết chéo giữa hai hệ thống.

## 2. Sprint Goal và kết quả

**Sprint Goal:** Thống nhất phạm vi, API contract và data model, nền tảng repo và CI sẵn sàng.

**Kết luận:** **RED**. Theo phản hồi của mentor, **cả 3 tiêu chí hoàn thành Sprint 1 chưa đạt** ở thời điểm đánh giá. Nhóm cần hỗ trợ và định hướng từ mentor để hoàn tất quy trình nộp và review tài liệu, chốt các quyết định đang Proposed và xử lý phần việc chuyển tiếp sang Sprint 2.

**Kết quả có thể ghi nhận:**

- Đã tạo và cập nhật Jira Sprint 1, gán assignee, deadline, time estimate cho 13 issue và liên kết Jira với Github.
- Đã chuẩn bị PRD, kiến trúc/ERD, API Contract và các nội dung thiết kế, ERA-6; ERA-7,8; ERA-11, ERA-17 đang trong bước PR trên github và review ở Jira, **chưa xác minh mentor approval bằng PR và chưa đủ điều kiện nên chưa merge vào main**.
- Đã đề xuất sử dụng tài liệu thuộc **NIST SP 800** làm nguồn dữ liệu.
- Đã thử nghiệm PDF parsing/chunking. **PR #29 (ERA-10) đã merge**, các status checks quan sát trên PR đều đạt ở lần kiểm tra trước merge.
- Đã test thành công **CI BE** xanh và **CI FE** xanh
- Đã soạn **ADR-0003** về lựa chọn LLM, nhưng **trạng thái Proposed, chưa được mentor approve**.

**Chưa đạt/cần hoàn thiện:**

- RAG Spike đã triển khai bước truy vấn, retrieval và trả về Top-K chunks
  liên quan. Code đã được đưa lên GitHub thông qua Pull Request và đang
  trong quá trình review, chưa đủ điều kiện merge. Phần tích hợp LLM
  để tạo câu trả lời có trích dẫn (citation) end-to-end chưa được hoàn thành.
- Các tài liệu PRD, System Architecture và API Contract đang trong quá
  trình review trên GitHub. Các tài liệu cần mentor phê duyệt vẫn đang
  chờ approval chính thức trước khi được tính là hoàn thành.
- Đã có time estimate cho từng task trên Jira, nhưng chưa tổng hợp
  đầy đủ số giờ làm việc thực tế (actual hours) của từng thành viên

## 3. Tiến độ công việc và bằng chứng

**Quy ước:** Jira được sử dụng để quản lý Sprint, phân công công việc, theo dõi trạng thái và thời gian ước lượng. GitHub được sử dụng để quản lý mã nguồn, tài liệu, Pull Request, code review và CI. Mỗi task được liên kết với bằng chứng GitHub tương ứng để xác minh Definition of Done (DoD).

| Issue | Người thực hiện | Estimate | Trạng thái Jira | Kết quả và bằng chứng |
|---|---|---:|---|---|
| ERA-6 – PRD v1.0 | Gia Bảo | 2h | Review | Đã hoàn thiện bản PRD và đang review trên GitHub. Chờ mentor phê duyệt PR. |
| ERA-7 – Architecture & Database ERD | Gia Bảo | 3h | Review | Đã hoàn thiện tài liệu kiến trúc và ERD. Đang review trên GitHub. |
| ERA-8 – API Contract & Upload Sequence | Gia Bảo | 2h | Review | Đã xây dựng API Contract và Sequence Diagram. Sử dụng chung branch và PR với ERA-7; cần kiểm tra Acceptance Criteria của cả hai task. |
| ERA-9 – Dataset Selection | Huy Hoàng | 2h | Done | Đã lựa chọn NIST SP 800 làm nguồn tài liệu. Danh sách 50–100 tài liệu cụ thể vẫn cần được hoàn thiện và mentor phê duyệt. |
| ERA-10 – PDF Parsing & Chunking | Huy Hoàng | 2h30 | Done | PR #29 đã được review, CI Passed và merge vào `main` bằng Squash and merge. |
| ERA-11 – Embedding & Retrieval Baseline | Huy Hoàng | 2h30 | Review | Đã triển khai bước truy vấn và retrieval trả về Top-K chunks liên quan. Code đang được review trên GitHub, chưa merge và chưa nghiệm thu đầy đủ baseline. |
| ERA-12 – LLM Selection | Hoàng Nhân | 1h30 | To Do | Đã phân tích các phương án LLM và xây dựng ADR-0003. Trạng thái Proposed, đang chờ mentor phê duyệt. |
| ERA-13 – Evaluation Dataset v0 | Hoàng Nhân | 2h30 | To Do | Vẫn đang chuẩn bị bộ 15 câu hỏi đánh giá ban đầu cùng reference key points và nguồn tham chiếu |
| ERA-14 – Research Flow & RAG Spike | Hoàng Nhân | 3h30 | To Do | Đã có tiến độ ở bước truy vấn và Retrieval Top-K. Phần tạo câu trả lời bằng LLM có citation end-to-end chưa được xác nhận hoàn thành. |
| ERA-15 – Monorepo & Git Workflow | Gia Huy, Hoàng Nhân | 1h30 | Done | Đã thiết lập Git Workflow, quy ước branch/commit/PR, tích hợp Jira với GitHub và triển khai quy trình làm việc cho nhóm. |
| ERA-16 – Backend CI | Gia Huy | 1h30 | Done | Đã triển khai Backend CI trên `main`. Workflow chạy thành công với hai job: Lint, tests & OpenAPI contract và Build images & smoke test. [GitHub Actions – Backend CI](https://github.com/mliotlab/task_grp_intern261/actions/runs/44778585789). |
| ERA-17 – Frontend CI | Gia Huy, Hoàng Nhân | 1h30 | Review | Đã triển khai Frontend CI, các bước lint, type check và build đều Passed. [PR #34](https://github.com/mliotlab/task_grp_intern261/pull/34) đang chờ review, chưa merge vào `main`. |
| ERA-18 – WSR-S1 & Sprint 2 Backlog | Hoàng Nhân | 2h | Review | Đang cập nhật WSR-S1 theo nhận xét của mentor và chuẩn bị Sprint 2 Backlog. Cần cập nhật estimate thực tế trên Jira. |

**Lưu ý:**

- ERA-7 và ERA-8 sử dụng chung một branch/PR. Mỗi task vẫn được theo dõi riêng trên Jira và phải đáp ứng Acceptance Criteria tương ứng.
- ERA-15 (Git Workflow) và ERA-17 (Frontend CI) có sự phối hợp thực hiện giữa Gia Huy và Hoàng Nhân.
- Git Workflow đã được triển khai cho nhóm và tích hợp Jira với GitHub để liên kết công việc và quá trình phát triển.
- Backend CI đã được triển khai trên `main` và chạy thành công. Frontend CI cũng đã Passed trên PR #34 nhưng chưa merge vào `main`.
- Việc CI Passed không đồng nghĩa task đã đạt Definition of Done (DoD). Các task vẫn cần đáp ứng Acceptance Criteria và quy trình PR/review/merge theo quy định.
- Hiện có **1 PR đã merge là PR #29 (ERA-10 – PDF Parsing & Chunking)**. Các PR đã mở còn lại đang trong quá trình review và chưa được tính hoàn thành.
- Sprint 1 hiện có **13 issue trên Jira**, bao gồm ERA-18 được bổ sung. Tại thời điểm báo cáo, **1/13 issue có bằng chứng PR đã merge được xác nhận**. Các issue còn lại tiếp tục được theo dõi theo trạng thái thực tế.
- Time estimate của Sprint 1 là **26 giờ**, được tổng hợp từ Jira. Giờ làm việc thực tế của từng thành viên được thống kê riêng.

## 4. Chỉ số Sprint 1

| Chỉ số | Kết quả | Ghi chú / Bằng chứng |
|---|---|---|
| Issue đạt DoD có bằng chứng PR merge / tổng issue | **1/13** | ERA-10 đã hoàn thành qua PR #29. Các issue khác chưa có đủ bằng chứng đáp ứng DoD. |
| Pull Request merged | **1** | PR #29 – PDF Parsing & Chunking, đã merge vào `main`. |
| Task ở trạng thái Review trên Jira | **6** | ERA-6, ERA-7, ERA-8, ERA-11, ERA-17 và ERA-18. Trong đó ERA-7 và ERA-8 sử dụng chung một PR. |
| Trạng thái Jira | **0 To Do, 3 In Progress, 6 Review, 4 Done** | Tổng 13 issue tại thời điểm báo cáo. Trạng thái Review không đồng nghĩa đã được approve hoặc đáp ứng DoD. |
| Tổng thời gian ước lượng | **26 giờ** | Tổng estimate của 13 issue trên Jira, không phải giờ làm thực tế. |
| Thời gian review PR trung bình | **Chưa tổng hợp được** | Do thời gian ảnh hưởng khá nhiều bởi việc setup Jira connect Github |
| Backend CI | **Passed trên `main`** | Workflow `ERA Backend CI #7` chạy thành công. Hai job lint/tests/OpenAPI và build/smoke test đều Passed. Có 2 cảnh báo deprecation. [GitHub Actions](https://github.com/mliotlab/task_grp_intern261/actions/runs/44778585789). |
| Frontend CI | **Passed trên PR #34** | Workflow lint, type check và build Passed. PR đang chờ review, chưa merge vào `main`. [PR #34](https://github.com/mliotlab/task_grp_intern261/pull/34). |
| CI của PR #29 | **3/3 checks Passed** | Backend CI và PR title validation đều đạt trước khi merge. |
| CI pass rate trên `main` | **Chưa tổng hợp đầy đủ** | Đã xác nhận Backend CI chạy thành công trên `main`. Cần thống kê toàn bộ workflow runs trong Sprint để tính tỷ lệ chính xác. |
| Backend test coverage | **Chưa có số liệu xác minh** | Cần bổ sung kết quả đo coverage từ test report hoặc CI. |
| Retrieval Top-K | **Đã triển khai, đang review** | Đã thực hiện truy vấn và truy xuất Top-K chunks liên quan. Code đang có PR trên GitHub nhưng chưa merge. |
| RAG end-to-end có citation | **Chưa hoàn thành** | Đã có bước Retrieval Top-K nhưng chưa xác nhận hoàn thiện luồng tích hợp LLM để tạo câu trả lời có trích dẫn end-to-end. |
### 4.1. Thời gian ước lượng theo thành viên

Thời gian được tổng hợp từ trường time estimate trên Jira. Với các task có nhiều người phối hợp, estimate được tính một lần theo người được giao chính để tránh cộng trùng.

| Thành viên | Task được giao chính | Tổng estimate | Công việc phối hợp | Giờ làm thực tế |
|---|---|---:|---|---|
| Gia Bảo (R1) | ERA-6, ERA-7, ERA-8 | **7h** | — | 8h |
| Huy Hoàng (R2) | ERA-9, ERA-10, ERA-11 | **7h** | — | 8h |
| Hoàng Nhân (R3) | ERA-12, ERA-13, ERA-14, ERA-18 | **7h30** | ERA-15, ERA-17 | 9h |
| Gia Huy (R4) | ERA-15, ERA-16, ERA-17 | **4h30** | Phối hợp với Nhân ở ERA-15, ERA-17 | 4h |
| **Tổng** | **13 issue** | **28h** | | 29h |

**Lưu ý:** Tổng estimate 26 giờ chỉ phản ánh khối lượng công việc được ước lượng trên Jira, không đại diện cho thời gian thực tế của các thành viên.

### 4.2 Chỉ số sản phẩm

- **Dataset:** NIST SP 800 là **nguồn được đề xuất**; corpus cụ thể 50–100 tài liệu chưa được duyệt.
- **Parsing & chunking:** Có bản triển khai đã merge qua PR #29. Trong lần thử nghiệm nội bộ trên bản PDF NIST 32 trang, PyMuPDF đọc đủ 32 trang, trích khoảng 77.031 ký tự, tạo 100 chunk; đây là kết quả local test, **không thay thế kiểm thử tích hợp worker/DB**.
- **Embedding / retrieval:** Chưa có kết quả end-to-end được xác minh.
- **Research answer / citation:** Chưa có demo đạt Sprint Goal.
- **Chất lượng retrieval, citation, latency:** Chưa có kết quả benchmark chính thức; không tự ước lượng.

## 5. Demo và minh chứng

### 5.1. Minh chứng hiện có

1. **Jira Sprint 1:**
   [ERA Sprint Board](https://hoangnhanbkag.atlassian.net/jira/software/projects/ERA/boards/2/backlog)
   - Quản lý 13 issue, bao gồm assignee, deadline và time estimate.
   - Hiện có 6 task ở trạng thái Review.

2. **PDF Parsing & Chunking – ERA-10:**
   - [GitHub PR #29](https://github.com/mliotlab/task_grp_intern261/pull/29).
   - Đã được review và merge vào `main`.
   - Cả 3 status checks của PR đều Passed.

3. **Backend CI – ERA-16:**
   - [GitHub Actions – Backend CI #7](https://github.com/mliotlab/task_grp_intern261/actions/runs/44778585789).
   - Workflow chạy thành công trên nhánh `main`.
   - Hai job lint/tests/OpenAPI và build/smoke test đều Passed.
   - Có 2 cảnh báo Node.js deprecation cần cải thiện sau.

4. **Frontend CI – ERA-17:**
   - [GitHub PR #34](https://github.com/mliotlab/task_grp_intern261/pull/34).
   - Frontend CI đã Passed các bước lint, type check và build.
   - PR hiện đang trong quá trình review, chưa merge vào `main`.

5. **Tài liệu thiết kế – ERA-6, ERA-7, ERA-8:**
   - PRD, System Architecture/ERD và API Contract đang trong quá trình review.
   - ERA-7 và ERA-8 sử dụng chung một branch/PR.
   - Các tài liệu cần mentor approve trực tiếp trên PR.
   

6. **Embedding & Retrieval Baseline – ERA-11:**
   - Đã triển khai chức năng truy vấn và truy xuất Top-K chunks liên quan.
   - Code đang trong quá trình review trên GitHub, chưa merge vào `main`.
   .

### 5.2. Nội dung chưa hoàn thành

- Chưa có demo end-to-end được nghiệm thu cho toàn bộ luồng:
  tải tài liệu → ingestion → retrieval → LLM answer generation
  → trả về câu trả lời có citation trên giao diện web.

- Retrieval Top-K đã được triển khai nhưng chưa hoàn tất
  review và merge vào `main`.

- Một số tài liệu thiết kế đang chờ mentor phê duyệt qua PR.

**Lưu ý:** Các sản phẩm và tài liệu chỉ được ghi nhận hoàn thành
khi đáp ứng Acceptance Criteria và Definition of Done theo quy định.
Các tài liệu lưu trên Google Drive chỉ phục vụ chia sẻ nội bộ,
không thay thế việc nộp tài liệu thông qua Pull Request.
## 6. Quyết định kỹ thuật và trạng thái phê duyệt

### 6.1. Các quyết định kỹ thuật

| Chủ đề | Trạng thái | Bằng chứng / Bước tiếp theo |
|---|---|---|
| Nguồn dữ liệu RAG | Đã lựa chọn NIST SP 800 làm nguồn tài liệu ban đầu; corpus cụ thể chưa được mentor phê duyệt | Hoàn thiện danh sách 50–100 tài liệu, bao gồm mã số, phiên bản, lý do lựa chọn và giấy phép. Sau đó gửi mentor review và phê duyệt. |
| LLM cho Research Worker | ADR-0003 đang ở trạng thái Proposed, chưa được mentor approve | Đang tiếp tục hoàn thiện phương án lựa chọn LLM theo nhận xét của mentor. Quyết định chính thức sẽ được cập nhật sau khi ADR được phê duyệt. |

### 6.2. Quy trình phát triển và quản lý dự án

Các nội dung sau là quy trình làm việc đã triển khai, không được
xem là quyết định kiến trúc hoặc ADR.

**Git Workflow:**
- Đã thống nhất và triển khai Git Workflow cho các thành viên.
- Sử dụng protected `main`, phát triển trên branch riêng.
- Thay đổi được tích hợp thông qua Pull Request.
- PR cần CI Passed và ít nhất một approval trước khi merge.
- Áp dụng Squash and merge.
- Git Workflow đã được phổ biến và áp dụng trong nhóm.

**Project Management:**
- Jira đã được mentor chấp thuận để quản lý Sprint và task.
- Sử dụng Jira để theo dõi assignee, deadline, time estimate
  và trạng thái công việc.
- Đã tích hợp Jira với GitHub để liên kết quá trình phát triển.
- GitHub được sử dụng để quản lý source code, tài liệu,
  Pull Request, code review và CI.
- Các task được đối chiếu với bằng chứng GitHub khi
  đánh giá Definition of Done.

## 7. Rủi ro và vấn đề

Các rủi ro được phân loại theo mức độ ảnh hưởng và khả năng xảy ra.
Mỗi rủi ro có người phụ trách chính, hướng xử lý và thời hạn cụ thể.
Các vấn đề ảnh hưởng trực tiếp đến Sprint 1 được ưu tiên giải quyết
trước hoặc trong ngày 24/11; các vấn đề cần nhiều thời gian được
đưa vào kế hoạch Sprint 2–3.

| ID | Rủi ro / vấn đề | Ảnh hưởng | Khả năng | Hướng xử lý | Owner | Deadline |
|---|---|---|---|---|---|---|
| R1 | Các tài liệu PRD, Architecture và API Contract đang chờ review/mentor approval | H | H | Hoàn tất chỉnh sửa theo review, cập nhật PR và gửi link cho mentor. Theo dõi các yêu cầu sửa và trạng thái phê duyệt. | Gia Bảo | 24/11 (Sprint 2) |
| R2 | RAG Spike chưa hoàn thiện luồng end-to-end có citation | H | H | Hoàn tất review Retrieval Top-K, tích hợp LLM để tạo câu trả lời có citation và chạy demo trên tập tài liệu thử nghiệm. | Hoàng Nhân | 23/11 (Sprint 2) |(Sprint 1) |
| R4 | Quota LLM giới hạn hoặc lỗi 429 làm gián đoạn Research Worker | H | M | Xác định quota sử dụng, triển khai rate limiting, retry/backoff và kiểm thử xử lý lỗi API. | Hoàng Nhân | 27/11 (Sprint 2) |
| R5 | Sprint 2 có nguy cơ quá tải do công việc chuyển tiếp từ Sprint 1 | H | H | Rà soát các task chưa đạt DoD, ưu tiên Walking Skeleton, phân chia công việc và cập nhật estimate, dependency trong Sprint Planning. | Hoàng Nhân | 24/11 (Sprint 2) |
| R6 | PDF NIST dài có thể khiến ingestion vượt NFR-03 (PDF 100 trang/2 phút) | H | M | Benchmark trên PDF 100 trang, đo thời gian parsing, chunking và embedding; xác định bottleneck và tối ưu nếu cần. | Huy Hoàng | 04/12 (Sprint 3) |
| R7 | Corpus NIST chưa có danh sách 50–100 tài liệu cụ thể được mentor duyệt | H | H | Hoàn thiện danh sách tài liệu gồm mã số, phiên bản, lý do lựa chọn và giấy phép; gửi mentor review và phê duyệt. | Huy Hoàng | 30/11 (Sprint 2) |

## 8. Retrospective

**1 việc nên giữ:** Chia công việc RAG thành các khối nhỏ (parsing, chunking, embedding, retrieval) để phát triển, kiểm tra và review độc lập.

**1 việc cần sửa:** Bắt đầu thực hiện công việc trước khi thống nhất đầy đủ cách đưa deliverable lên GitHub và quy trình PR, khiến nhiều kết quả chỉ tồn tại nội bộ hoặc trên Jira mà chưa đáp ứng Definition of Done.

**1 hành động cụ thể:** Nguyễn Hoàng Nhân điều phối việc rà soát toàn bộ issue trên Jira, bảo đảm mỗi deliverable có liên kết PR/bằng chứng GitHub và cập nhật trạng thái phù hợp với DoD; **hạn đề xuất: 24/11/2026** 

## 9. Kế hoạch Sprint 2 – Walking Skeleton

**Trạng thái lập kế hoạch:** Draft – chưa hoàn tất Sprint 2 Planning.

**Sprint Goal:** Luồng tối thiểu chạy xuyên suốt trong Docker: **đăng nhập → upload tài liệu → đặt câu hỏi → nhận câu trả lời có citation trên web**. Sprint Goal được xác định theo Requirement Specification.

**Ưu tiên triển khai:**

1. JWT authentication, data model và migration; kiểm tra cách ly dữ liệu người dùng.
2. API upload, queue, ingestion worker và trạng thái tài liệu; tích hợp parsing/chunking đã merge với embedding/indexing.
3. Research Worker v1: retrieval + answer có trích dẫn, API tạo task và tra cứu trạng thái.
4. Frontend: login, upload, ask, hiển thị report và citation.
5. Docker Compose đầy đủ; smoke test CI, integration test với PostgreSQL thật; CI build image các service.
6. Hoàn thiện Design Doc v1, OpenAPI, 4 ADR theo yêu cầu, WSR-S2.

**Carry-over từ Sprint 1 phải tính vào capacity Sprint 2:** PRD/Design Doc/API Contract còn chờ review/mentor approval; ADR-0003 Proposed; corpus NIST chưa duyệt; retrieval và RAG spike chưa nghiệm thu; bằng chứng CI và timesheet chưa đầy đủ.

Danh sách issue và khối lượng công việc chính thức sẽ được
cập nhật sau khi nhóm hoàn tất Sprint Planning vào thứ 2 ngày 23/11.

## 10. Cần hỗ trợ từ mentor

1. Review/approve **PRD và Design Doc trực tiếp trên PR**, khi nhóm gửi đúng link theo quy định.


