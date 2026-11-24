# Weekly Status Report – Sprint 1 

> **Dự án:** Enterprise Research Agent (ERA)  
> **Sprint:** Sprint 1 – Discovery & Design, 16/11/2026–23/11/2026 (theo Jira)  
> **Scrum Master:** Nguyễn Hoàng Nhân  
> **Trạng thái:** **RED**  
> **Thời điểm cập nhật:** 24/11/2026
> **Trạng thái tài liệu:** In Review – Đang chờ phê duyệt và merge PR

## 1. TL;DR

Sprint 1 **không đạt Sprint Goal theo tiêu chí hoàn thành trong Requirement Specification**. Nhóm đã có hoạt động thiết kế, nghiên cứu nguồn tài liệu, xây dựng các thành phần ban đầu của RAG và thiết lập công cụ. Tuy nhiên, nhiều kết quả chưa được merge vào nhánh main của repository chung, các tài liệu cần mentor phê duyệt vẫn đang trong quá trình review, RAG spike chưa hoàn tất end-to-end.

Tại thời điểm cập nhật, Jira ghi nhận **13 work items**, tổng **28 giờ ước lượng**, và GitHub ghi nhận **4 PR đã merge**. Mục tài liệu ERA-8 đang ở trạng thái **Review trên Jira** và **PR** trên Github. 

Nhóm tiếp tục sử dụng **Jira để quản lý sprint, issue, assignee và estimate** (đã được mentor chấp thuận) và **GitHub để lưu mã nguồn, tài liệu, thực hiện PR/review, chạy CI và chứng minh Done**. Mã `ERA-n` dùng liên kết chéo giữa hai hệ thống.

## 2. Sprint Goal và kết quả

**Goal**: Chốt phạm vi, API contract, data model, repo và CI sẵn sàng. 

**Kết quả**: Không đạt theo exit criteria Sprint 1 tại mốc mentor đánh giá, chưa hoàn tất đủ phê duyệt tài liệu/LLM và chưa end to end RAG để test.

## 3. Tiến độ công việc và bằng chứng

**Quy ước:** Jira quản lý tiến độ; GitHub lưu PR, CI và bằng chứng DoD. Chỉ tính hoàn thành khi đáp ứng Acceptance Criteria và Definition of Done.

| Issue | Phụ trách | Estimate | Jira (24/11) | Kết quả / Bằng chứng |
|---|---|---:|---|---|
| ERA-6 – PRD v1.0 | Gia Bảo | 2h | Done | [PR #27](https://github.com/mliotlab/task_grp_intern261/pull/27), Đã hoàn thiện bản PRD và đang review trên GitHub và được Mentor Approve |
| ERA-7 – Architecture & ERD | Gia Bảo | 3h | Done | [PR #30](https://github.com/mliotlab/task_grp_intern261/pull/30), Đã hoàn thiện tài liệu kiến trúc và ERD và được Mentor Approve |
| ERA-8 – API Contract | Gia Bảo | 2h | Review | Đã bổ sung ErrorResponse, Pagination và OpenAPI, PR đang review. |
| ERA-9 – Dataset Selection | Huy Hoàng | 2h | Done | Đã chuẩn bị corpus NIST, đã được Mentor Approve |
| ERA-10 – Parsing & Chunking | Huy Hoàng | 2h30 | Done | [PR #29](https://github.com/mliotlab/task_grp_intern261/pull/29), Đã hoàn thành Parse and Chunking Basic cho luồng RAG |
| ERA-11 – Embedding & Retrieval | Huy Hoàng | 2h30 | Review | Retrieval Top-K đã triển khai, ADR về Retrieval và Model Embedding đang được review trên Github. |
| ERA-12 – LLM Selection | Hoàng Nhân | 1h30 | In Progress | ADR-0003 Proposed, chờ mentor phê duyệt. |
| ERA-13 – Evaluation Dataset | Hoàng Nhân | 2h30 | In Progress | Đang xây dựng 15 câu hỏi đánh giá. |
| ERA-14 – RAG Spike | Hoàng Nhân | 3h30 | In Progress | Đã có Retrieval, chưa hoàn thiện Answer + Citation. |
| ERA-15 – Git Workflow | Gia Huy, Nhân | 1h30 | Done | Đã triển khai Git Workflow và kết nối Jira–GitHub, nhóm đã nắm flow về cách xài Git, nhóm Triển khai dựa trên tài liệu guidance từ anh mentor. |
| ERA-16 – Backend CI | Gia Huy | 1h30 | Done | [Backend CI](https://github.com/mliotlab/task_grp_intern261/actions/runs/44778585789) Passed trên `main`. |
| ERA-17 – Frontend CI | Gia Huy, Nhân | 1h30 | Done |[Frontend CI](https://github.com/mliotlab/task_grp_intern261/actions/runs/45211459476) Passed trên `main`. |
| ERA-18 – WSR-S1 | Hoàng Nhân | 2h | Review | WSR-S1 đang review, Sprint 2 Backlog đã chuẩn bị trên Jira. |

**Tổng hợp:** 13 issue · **7 Done, 3 Review, 3 In Progress** · **28h estimate, 29h thực tế**.

**Lưu ý:** Trạng thái trên được tính vào lục 24/11. PR chưa merge hoặc chưa được phê duyệt không được tính hoàn thành.

## 4. Chỉ số Sprint 1

| Chỉ số | Kết quả / Bằng chứng |
|---|---|
| Trạng thái Jira (24/11) | **13 issue: 7 Done, 3 Review, 3 In Progress**. |
| Pull Request merged | **4 PR:** [#27 – PRD](https://github.com/mliotlab/task_grp_intern261/pull/27), [#30 – Design Doc & ERD](https://github.com/mliotlab/task_grp_intern261/pull/30), [#29 – Parsing & Chunking](https://github.com/mliotlab/task_grp_intern261/pull/29), [#34 – Frontend CI](https://github.com/mliotlab/task_grp_intern261/pull/34). |
| CI | [Backend CI](https://github.com/mliotlab/task_grp_intern261/actions/runs/44778585789) và [Frontend CI](https://github.com/mliotlab/task_grp_intern261/actions/runs/45211459476) Passed trên `main`. |
| Kết quả sản phẩm | PRD, Design Doc/ERD, Parsing & Chunking và Frontend CI đã merge. Retrieval Top-K đang review. **RAG Spike trên notebook với 10 tài liệu chưa hoàn thiện bước Answer Generation có citation.** |

### 4.1. Giờ làm theo thành viên

| Thành viên | Estimate | Thực tế |
|---|---:|---:|
| Gia Bảo (R1) | 7h | 8h |
| Huy Hoàng (R2) | 7h | 8h |
| Hoàng Nhân (R3) | 9h30 | 9h |
| Gia Huy (R4) | 4h30 | 4h |
| **Tổng** | **28h** | **29h** |

**Lưu ý:** Số liệu trạng thái và PR merge cập nhật đến 24/11.

## 5. Demo và minh chứng

| Hạng mục | Bằng chứng | Kết quả |
|---|---|---|
| PRD v1.0 – ERA-6 | [PR #27](https://github.com/mliotlab/task_grp_intern261/pull/27) | Mentor approved, đã merge |
| Design Doc & ERD – ERA-7 | [PR #30](https://github.com/mliotlab/task_grp_intern261/pull/30) | Mentor approved, đã merge |
| Parsing & Chunking – ERA-10 | [PR #29](https://github.com/mliotlab/task_grp_intern261/pull/29) | CI Passed, đã merge |
| Frontend CI – ERA-17 | [PR #34](https://github.com/mliotlab/task_grp_intern261/pull/34) | CI Passed, đã merge |
| Backend CI – ERA-16 | [GitHub Actions](https://github.com/mliotlab/task_grp_intern261/actions/runs/44778585789) | Passed trên `main` |
| Frontend CI – ERA-17 | [GitHub Actions](https://github.com/mliotlab/task_grp_intern261/actions/runs/45211459476) | Passed trên `main` |

**RAG Spike – ERA-12, 13, 14:** Mục tiêu Sprint 1 là thử nghiệm RAG trên notebook với 10 tài liệu, gồm Retrieval → LLM Answer Generation → Citation. Hiện đã có bước Retrieval Top-K; chưa hoàn thành notebook trả lời có trích dẫn.

**Chưa hoàn tất review:** ERA-8 (API Contract), ERA-11 (ADR về model Embedding & method Retrieval) và ERA-18 (WSR-S1).

## 6. Quyết định kỹ thuật và trạng thái phê duyệt

| Chủ đề | Trạng thái / Bước tiếp theo |
|---|---|
| PRD & Architecture | PRD v1.0 và Design Doc/ERD đã được mentor approve và merge qua PR #27, #30. |
| Corpus NIST | Đã lựa chọn NIST SP 800 và được mentor phê duyệt theo cập nhật của nhóm. Tiếp tục quản lý danh sách tài liệu và phiên bản. |
| LLM Research Worker | ADR-0003 vẫn **Proposed**, chờ mentor phê duyệt phương án LLM. |
| API Contract | ERA-8 đã bổ sung ErrorResponse, Pagination và OpenAPI; tiếp tục review và đợi Mentor approve |
| Git Workflow & Jira | Đã áp dụng quy trình PR, CI, review và Squash merge; Jira được mentor chấp thuận quản lý Sprint. |

## 7. Rủi ro và vấn đề

| ID | Mô tả | Ảnh hưởng (H/M/L) | Khả năng (H/M/L) | Hướng xử lý | Người phụ trách | Trạng thái |
|---|---|---|---|---|---|---|
| R1 | ERA-8, ERA-11 và WSR-S1 chưa đạt DoD | H | H | Hoàn tất review, kiểm thử và merge PR theo Acceptance Criteria. | R1/R2/R3 | Đang xử lý – Sprint 2 |
| R2 | RAG Spike trên 10 tài liệu chưa hoàn thiện Answer Generation có citation | H | H | Hoàn thiện notebook, kiểm tra câu trả lời và trích dẫn. | Hoàng Nhân | Đang xử lý – Sprint 2 |
| R4 | Giới hạn quota LLM hoặc lỗi 429 gây gián đoạn | H | M | bổ sung rate limiting, retry/backoff. | Hoàng Nhân | Lên kế hoạch – Sprint 2 |
| R5 | Sprint 2 quá tải do các task carry-over | H | H | Rà soát estimate, dependency và ưu tiên Walking Skeleton. | Hoàng Nhân | Đang theo dõi |
| R6 | Ingestion PDF dài có nguy cơ vượt NFR-03 | H | M | Benchmark PDF 100 trang; đo thời gian parsing và embedding để tối ưu. | Huy Hoàng | Lên kế hoạch – Sprint 2 |

*H = High (Cao), M = Medium (Trung bình), L = Low (Thấp). Trạng thái phản ánh tình hình cập nhật ngày 24/11/2026.*

## 8. Retrospective

**Giữ:** Chia RAG pipeline thành các module nhỏ để phát triển, kiểm thử và review độc lập.

**Cần cải thiện:** Việc phối hợp PR, cập nhật Jira và cung cấp bằng chứng DoD chưa đồng bộ từ đầu Sprint, khiến RAG Spike chưa hoàn thiện theo mục tiêu.

**Hành động:** Hoàng Nhân rà soát issue, liên kết PR/CI, bổ sung dependencies và cân đối workload Sprint 2. **Hạn: 24/11/2026.**

## 9. Kế hoạch Sprint 2 – Walking Skeleton

**Sprint Goal:** Hoàn thành hệ thống end-to-end bằng Docker Compose:

**Login → Upload PDF → Ingestion → Retrieval → LLM Answer with Citations → Frontend.**

**Các nhóm công việc ưu tiên:**

1. **Backend & API (R1):** JWT, Database, Migration, Document API và Research Job API (ERA-32–35); hoàn thành ERA-8.
2. **Data & Retrieval (R2):** Redis Queue, Ingestion Worker, Embedding, pgvector, Dense Retrieval Top-K (ERA-37–41); hoàn thành ERA-11.
3. **Research Worker (R3):** Hoàn thiện RAG Spike còn lại, tích hợp LLM Adapter, Research Worker v1, Citation Mapping và Unit Tests (ERA-43–45).
4. **Frontend & DevOps (R4):** Login, Upload, Research UI, Docker Compose và CI Smoke Test (ERA-49–52).
5. **Reliability & Documentation:** Triển khai Reconciler NFR-04 trong Sprint 2, kiểm thử phân quyền User A/B; hoàn thiện Design Doc v1, OpenAPI, ADR và WSR-S2.

**Exit Criteria:**

- [ ] Clone repo, chạy `docker compose up` thành công và demo toàn bộ Walking Skeleton.
- [ ] Integration test xác nhận User A không truy cập được dữ liệu User B.
- [ ] CI build thành công các service image và smoke test đạt.

**Phạm vi:** Ưu tiên RAG cơ bản và Walking Skeleton. 

**Sprint 2 Backlog:** [Jira ERA](https://hoangnhanbkag.atlassian.net/jira/software/projects/ERA/boards/2/backlog).

## 10. Cần hỗ trợ từ mentor

1. **ADR-0003:** Review và phê duyệt lựa chọn LLM để triển khai Research Worker.
2. **API & Retrieval:** Review các PR còn mở cho ERA-8 và ERA-11.
3. **Walking Skeleton:** Góp ý phạm vi Sprint 2
4. **Sprint Review:** Xác nhận tiêu chí nghiệm thu Walking Skeleton end-to-end và bằng chứng CI/integration test.