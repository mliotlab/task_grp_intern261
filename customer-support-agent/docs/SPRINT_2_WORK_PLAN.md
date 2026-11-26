# Sprint 2 · Kế hoạch triển khai Customer Support Agent

- **Dự án** · ShopX, nhóm AIE-01 · **Giai đoạn** · Walking Skeleton
- **Khôi** · AI Engineer · **Trọng** · Backend & Platform Engineer, kiêm Scrum Master Sprint 2 theo lịch luân phiên
- **Mentor** · Nguyễn Trần Anh Quân · **Trạng thái** · Đề xuất để chốt ở Sprint Planning

**Sprint Goal.** Trong Docker, gửi câu hỏi chính sách qua `POST /v1/chat`, truy xuất KB, gọi LLM và nhận câu trả lời có trích dẫn. Cùng API tra được đơn giả khi mã đơn và email khớp. Nhóm có báo cáo eval đầu tiên và CI chạy 10 ca với LLM giả lập.

## 1. Chuẩn bị đầu vào từ Sprint 1

| Đầu vào | Đối chiếu ngày 25/11/2026 | Việc đầu sprint |
| --- | --- | --- |
| KB và tập eval v0 | Ref `origin/main` có sẵn trong repo ở `bf22e9b` có **21 policy và 30 case**, ID case duy nhất và mọi `expected_doc_ids` đều tồn tại. Nhánh làm việc cũ ở `8add7bc` có 11 policy và 18 case. | Cả hai lấy commit tích hợp mới nhất làm gốc. Khôi kiểm lại số case, nguồn và phiên bản dataset. Trọng xác nhận policy Shipping/Payment/Account và nhãn order khớp fixture. |
| PRD và Design | Bản nháp AI có trong workspace. Các file PRD/Design trên ref đã kiểm tra còn nội dung mẫu. | Khôi và Trọng đối chiếu hai bản, ghép nội dung đã soạn và thống nhất phiên bản dùng để triển khai. Trọng mở PR Design v1 và xin mentor review. |
| LLM và notebook | ADR-0002 trong workspace đang **Proposed**. Notebook Sprint 1 dùng TF-IDF và trích xuất, tìm đúng tài liệu trong top 4 ở 8/8 câu có nguồn nhưng chỉ 6/8 đạt kiểm tra cụm từ. | Khôi xác nhận model/provider và quota với mentor. Kiểm tra model nhận context và trả được lời gọi tool theo schema. Dùng các câu dev sai nguồn hoặc sai đoạn để kiểm tra hồi quy. |
| Fixture đơn hàng | Script đã sinh được 100 đơn giả. `SX-000001` với `customer001@example.com` có trạng thái `confirmed` khi dùng seed 42 và ngày tham chiếu 2026-11-30. | Trọng dùng cùng cấu hình trong test, Docker và demo. Đối chiếu các ca tra đơn còn lại. Nếu trường tùy chọn như carrier là `null`, phản hồi đúng theo fixture. |
| Bản nháp trên máy | Workspace còn PRD, Design, ADR, notebook, WSR-S1, thay đổi docs README và file chạy local. | Ghi nhận và bảo toàn thay đổi trước khi tạo nhánh từ `origin/main`. Nếu cần, dùng checkout riêng để tích hợp rồi đưa từng phần vào PR đúng issue. |

Ngày bắt đầu/kết thúc, số issue và commit dùng cho baseline được ghi trong Planning. [Kế hoạch Sprint 1](SPRINT_1_WORK_PLAN.md) · [Tập eval v0](../eval/datasets/v0/cases.jsonl)

## 2. Phạm vi và cách chia

| Đầu ra Sprint 2 | Chủ trì | Phối hợp và tiêu chí |
| --- | --- | --- |
| **FR-02** · Ingestion và vector index | **Khôi** | Trọng tích hợp lệnh build index và volume. Đọc Markdown/PDF, giữ metadata, chạy lại sau khi policy thêm/sửa/xóa. |
| **FR-03** · Retrieval, LLM, citation | **Khôi** | Trọng kết nối orchestrator vào Chat API. Trả nội dung có bằng chứng, nguồn gồm `doc_id` và `snippet`, thiếu nguồn thì báo rõ và đề nghị gặp nhân viên. |
| **FR-04 / NFR-03** · Tra đơn có xác minh | **Trọng** phụ trách Order API và HTTP client của tool · **Khôi** phụ trách điều phối gọi tool | Có kiểm thử ba lớp cho nhánh thiếu email, sai email và đúng email. Không để lộ thông tin đơn trước xác minh. |
| **FR-01 / NFR-07** · API, logs và vận hành lần chạy | **Trọng** | Khôi đưa dữ liệu truy xuất, tool và token vào tracing. Trọng nối `request_id` với `trace_id`, đưa vào Compose và làm sạch dữ liệu khi log/trả lỗi. |
| **Eval harness v1 / NFR-08** | **Khôi** viết runner, rubric và baseline · **Trọng** đưa 10 ca mock lên CI | Một lệnh chạy bộ v0 qua HTTP và xuất CSV/Markdown. CI chọn đúng 10 ca, có assertion và chạy được với dependency giả lập. |
| Design v1, ≥3 ADR, baseline, WSR-S2 | **Trọng** tổng hợp Design và WSR · **Khôi** viết phần AI, ADR và cung cấp số liệu | Có PR để mentor review, ghi provider/model thật sự dùng, phiên bản KB/dataset, kết quả demo và link CI. |

**Phạm vi bàn giao.** Sprint này làm một lượt Chat API đầu cuối cho policy và tra đơn. Có bảo vệ dữ liệu đơn ở FR-04 và hành vi báo thiếu nguồn của FR-03. Ticket, bàn giao tạo ticket thật, hội thoại nhiều lượt đầy đủ, guardrail ngoài phạm vi/prompt injection toàn diện và UI xem/sửa ticket triển khai ở Sprint 3. Các ca v0 liên quan phần đó vẫn chạy để thu baseline và được ghi trạng thái phạm vi. Bộ ≥60 câu, ≥10 ca an toàn, judge và kiểm tra tay 20 mẫu là mốc Sprint 3.

## 3. Khôi · AI Engineer

### AI-1 · Nạp tài liệu, tạo index và truy xuất (M · 3 giờ)

**Repo đang có** loader Markdown và chia đoạn cơ bản. `build_index` chưa triển khai, retriever sản phẩm đang là `NullRetriever`. Tận dụng interface `Retriever.search` để Trọng nối Chat API sớm.

1. Sửa loader để nạp Markdown và PDF có lớp văn bản trong `KB_DIR`. Dùng stem làm `doc_id` nhất quán với eval, bỏ README, nhận diện ID trùng. Chia Markdown theo mục và PDF theo trang, rồi áp dụng kích thước và overlap từ cùng cấu hình với `--dry-run`.
2. Lưu `doc_id`, `chunk_id`, tên mục/trang và nội dung gốc. Bản triển khai dùng vector index NumPy cục bộ và mặc định `intfloat/multilingual-e5-small`. E5 dùng prefix `query:` và `passage:` tương ứng. Ghi model revision và hướng điểm số khi chốt [ADR-0003](adr/0003-vector-store-and-embedding.md).
3. Với KB nhỏ, ưu tiên rebuild một snapshot hoàn chỉnh và chỉ chuyển sang bản mới sau khi index sẵn sàng. Đọc snapshot cũ trong lúc build; ghi cách reload/restart nếu retriever giữ snapshot cũ. Truy vấn trả tối đa `top_k` theo điểm, chuyển distance sang score nhất quán với `min_score` nếu backend dùng distance.

**Nghiệm thu.** Test với ít nhất một Markdown và một PDF nhỏ, đối chiếu ID và metadata. Chạy lại cùng dữ liệu không tăng số chunk. Khi sửa/xóa một tài liệu, bản cũ không còn xuất hiện sau khi refresh. Câu policy có nguồn trả được đoạn phù hợp. Khi ngưỡng lọc hết kết quả, trả danh sách rỗng có chủ đích.

**File chính.** [ingest.py](../support_agent/retrieval/ingest.py) · [retriever.py](../support_agent/retrieval/retriever.py) · [ingest_kb.py](../scripts/ingest_kb.py) · [agent.yaml](../configs/agent.yaml)

### AI-2 · Nối LLM, RAG và vòng gọi tool (M · 3 giờ)

1. Mở lại ADR-0002, ghi model ID, endpoint giao thức, nguồn giá/quota và trạng thái mentor chốt. Dùng interface `LLMClient` cho một provider đã chọn. Kiểm tra mapping giữa `Message`, assistant tool call và tool result, kèm token usage nếu provider trả. Giữ mock để phát triển và chạy CI trong lúc chờ model.
2. Ghép prompt đã version với các đoạn retriever trả, phân biệt dữ kiện nguồn và chỉ dẫn hệ thống. Với câu policy, ghép mỗi trích dẫn về đoạn thực sự hỗ trợ phát biểu. `snippet` lấy từ KB; câu trả lời thiếu dữ kiện hoặc citation không kiểm chứng được đi theo nhánh báo thiếu nguồn. Đem các lỗi chọn câu ở Sprint 1 vào bộ dev để đối chiếu chất lượng.
3. Cho phép `get_order_status` ở luồng tra đơn theo ADR-0004. Kiểm tra mã và email hợp lệ đã được khách cung cấp trước khi gọi, giới hạn số bước bằng `max_tool_steps` và dùng registry để kiểm tham số. Khi tool trả lỗi, chuyển thông báo phù hợp và kết thúc có kiểm soát. Đưa tên tool, kết quả, ID đoạn và token từng lần gọi vào trace.

**Nghiệm thu.** Test policy có nguồn, thiếu nguồn và trích dẫn lạ; kiểm tra có tool call + tool result trong ngữ cảnh khi mã/email hợp lệ. Ca thiếu hoặc sai định dạng email phải hỏi lại và không gọi Order API. Model đề xuất giá trị chưa có trong lời khách thì từ chối gọi. Giữ đúng schema khi provider timeout, trả dữ liệu bất thường hoặc tool thất bại. Hoàn thiện test scaffold đang skip cho FR-03/04; FR-06 giữ theo mốc Sprint 3.

**File chính.** [LLM factory](../support_agent/llm/factory.py) · [orchestrator.py](../support_agent/orchestrator.py) · [tool registry](../support_agent/tools/registry.py) · [prompt](../prompts/system/v1.md)

### AI-3 · Eval harness v1, baseline và bàn giao AI (M · 2,5 giờ)

1. Nâng `eval/run_eval.py` để chạy v0 qua Chat API, kiểm status/schema, ghi rõ lỗi theo ID case và xuất CSV/Markdown. Giữ schema JSONL hiện hành. Chấm theo nhãn lượt cuối khi dữ liệu chỉ có một bộ nhãn, kiểm tra không rò thông tin đơn ở mọi lượt có liên quan.
2. Cố định 10 ID CI và fixture mock cho hành vi kỳ vọng. Cung cấp dữ liệu retriever và tool giả đủ để kiểm case. Test runner phân biệt thất bại thật, phần chưa hỗ trợ và chỉ số chưa đo. Bàn giao lệnh và danh sách ca cho Trọng.
3. Chạy baseline v0 trên Compose, công bố kết quả và giới hạn đo. Bổ sung phần retrieval, prompt, tool loop và eval vào Design v1. Gửi kết quả, commit và vài case đại diện cho WSR.

**Nghiệm thu.** Một lệnh tạo được hai file báo cáo. Có danh sách case đã chạy, chỉ số có mẫu số, case fail theo lý do, metadata để nhóm chạy lại và 10 case CI có assertion. [Runner](../eval/run_eval.py)

## 4. Trọng · Backend & Platform Engineer

### BE-1 · Order API giả lập và client cho tool (M · 2,5 giờ)

1. Dùng script sẵn có và chốt fixture `--n 100 --seed 42 --today 2026-11-30`. Đảm bảo Order API tìm đơn từ fixture và xác minh cặp `order_id`/email ở backend. Chuẩn hóa email theo một quy tắc dùng chung với fixture và test.
2. Với mã đúng định dạng, email sai và mã không tồn tại phải cùng mã HTTP và cùng nội dung lỗi chung. Khi khớp, chỉ trả schema `OrderStatus`: `order_id`, `status`, `estimated_delivery`, `carrier`. Xử lý file fixture thiếu/hỏng như lỗi cấu hình, để nhóm phân biệt với tra cứu trả 404.
3. Hoàn thiện `get_order_status` làm HTTP client đến `ORDER_API_URL`. Chốt kết quả thành công, không khớp và lỗi phụ thuộc cho Khôi. Đặt timeout, kiểm response và chuẩn hóa lỗi. Kiểm logs của server/client, kể cả access log có query string email.

**Nghiệm thu.** Test cặp đúng, sai email, mã không tồn tại, đầu vào lỗi và upstream timeout. So hai phản hồi từ chối, xác nhận không có trạng thái, ETA, carrier, email hoặc dữ liệu đơn trong phản hồi/log công khai. Khôi dùng đúng adapter trong orchestrator test. [Order API](../services/order_api/main.py) · [Tool tra đơn](../support_agent/tools/order_status.py) · [Script sinh đơn](../scripts/generate_orders.py)

### BE-2 · Tích hợp Chat API, tracing và Compose (M · 3 giờ)

1. Nối đối tượng retriever thật và adapter LLM vào `get_orchestrator`; dùng dependency override để kiểm thử. Giữ OpenAPI của `POST /v1/chat`. Dùng `X-Request-ID` và `trace_id` để đối chiếu từng lượt. Cùng Khôi thống nhất schema của `actions`, lọc dữ liệu trước khi trả công khai.
2. Hoàn thiện log JSON dùng `TurnTrace`: mỗi lượt ghi model/prompt, token vào/ra, chi phí ước tính, độ trễ tổng và từng bước, tên/kết quả tool và ID tài liệu/đoạn truy xuất. Cộng token của mọi lần gọi LLM trong lượt. Mock ghi rõ là mock; usage/giá chưa được provider cung cấp ghi là chưa biết. Đưa giá theo model vào cấu hình và theo dõi ngân sách đã thống nhất với mentor.
3. Cập nhật Docker image, lệnh nạp index và volume cho Chat API. Image hiện chỉ cài extra `llm`, volume có sẵn ở `/app/var`; bổ sung extra `rag` cho cấu hình chạy thật và bảo đảm quyền ghi/đọc index. Giữ Order API sinh fixture trong image hoặc bằng bước khởi tạo tái lập. Ghi rõ cách kiểm index/readiness trước demo để `/health` xanh có thể được theo sau bằng một request policy thật.

**Nghiệm thu.** Khởi động từ checkout sạch với cấu hình mẫu đã điền, hai API healthy, gọi được policy có citation và tra đơn đủ/thiếu/sai email theo contract. Khởi động lại dùng được index đã persist hoặc có bước nạp lại được ghi rõ. Trace từ một request có thể đối chiếu với response và không lộ dữ liệu xác minh. [Chat API](../services/chat_api/main.py) · [Schema](../support_agent/schemas.py) · [Tracing](../support_agent/tracing.py) · [Compose](../docker-compose.yml) · [Dockerfile Chat API](../services/chat_api/Dockerfile)

### BE-3 · CI, Design v1 và điều phối Sprint 2 (M · 3 giờ)

1. Chỉnh job mock trong CI và `make eval-ci` từ giới hạn hiện tại 20 xuống danh sách **10 ID** đã chốt. Ép cấu hình mock trong CI, dùng test doubles để chạy không cần credential hoặc tải model khi job eval thực thi. Tạo CI artifact cho báo cáo. Giữ các job Ruff, unit test + coverage, Docker build và smoke `/health` cho cả hai API. Bổ sung test kiểm lookup đúng/sai và ít nhất một request policy qua contract. Chỉ dùng fixture ShopX giả.
2. Tổng hợp Design v1 theo template, ghi flow policy và order, API contract + lỗi, vòng đời dữ liệu, vận hành, bảo mật, test và quyết định mở. Đính kèm ADR đã chốt và link baseline. Mở PR cho mentor review sớm.
3. Điều phối board, Planning, Review và Retro. Gom điểm, log, link PR/CI và kết quả demo vào `docs/reports/WSR-S2.md` theo template 10 mục. Mở PR báo cáo và gửi link qua kênh nhóm **trước 12:00 thứ Sáu**, trước Sprint Review.

**Nghiệm thu.** PR/CI cho phần Sprint 2 đã chạy, log cung cấp chứng cứ cho điều kiện cuối sprint, Design v1 và WSR-S2 có link và tình trạng review rõ ràng. [Workflow CSA](../../.github/workflows/csa-ci.yml) · [Makefile](../Makefile) · [Mẫu Design](../../docs/templates/DESIGN.md) · [Mẫu WSR](../../docs/templates/WSR.md)

**Quỹ thời gian đề xuất.** 8,5 giờ đầu việc/người + 1–1,5 giờ review và tích hợp/người. Các mục M có thể tách thành issue S tại Planning để mỗi PR dễ review. Nếu có blocker về provider, chốt sớm với mentor và dùng mock để tiếp tục kiểm tra kỹ thuật.

## 5. Hợp đồng tích hợp cần chốt cùng nhau

| Điểm nối | Hành vi cam kết | Bằng chứng |
| --- | --- | --- |
| Chat API → Kho tài liệu | `POST /v1/chat` nhận `session_id`, `message`; trả `answer`, `citations`, `actions`, `handoff`, `ticket_id`, `trace_id` theo schema hiện tại. Policy có nguồn trả `doc_id` và `snippet` hỗ trợ đáp án. | Integration test với LLM giả; request policy qua Docker với provider đã chọn. |
| Chat API → RAG khi thiếu nguồn | Phản hồi nói chưa tìm thấy thông tin và đề nghị gặp nhân viên. Ở lượt đầu chưa có yêu cầu chuyển người, `handoff=false`, `ticket_id=null` và không tự tạo ticket. | `pol-108` và test khi retriever trả rỗng hoặc trả đoạn cùng chủ đề nhưng thiếu dữ kiện. |
| Agent → Order API | Mã và email thiếu/sai định dạng → hỏi lại, không gọi tool. Đủ dữ liệu hợp lệ → gọi một lần với giá trị khách cung cấp. Email sai và mã không tồn tại → cùng lỗi xác minh, không xác nhận có đơn. Đúng cặp → công bố đúng trường Order API trả. | `ord-001`, `ord-002`, `ord-104`, `ord-105`; test số lần gọi và test 404. |
| Tool → Phản hồi và eval | Chat response có thể ghi tên tool, kết quả và tham số đã lọc. Xác nhận đầy đủ tham số bằng stub/spy trong test với fixture giả; xác nhận giá trị không xuất hiện trong log và response công khai. | Test tool schema, test lỗi upstream, test kiểm response và log của ca có email. |
| Index → Compose | Build index dùng cùng KB/model/cấu hình với retriever. Chốt cách phát hiện index thiếu, cấp quyền cho volume, cập nhật snapshot và gọi lại Chat API. | Lệnh được ghi trong README/Design v1 và một lần chạy từ checkout sạch. |

### Ba ADR kỹ thuật của Sprint 2

| ADR | Chủ trì | Nội dung cần quyết định |
| --- | --- | --- |
| `0002-llm-provider.md` | Khôi | API mentor cấp hoặc Ollama; model, giao thức, tool calling, token, giá/quota hoặc giới hạn tài nguyên. Giữ trạng thái Proposed tới khi có quyết định thực tế. |
| `0003-vector-store-and-embedding.md` | Khôi · Trọng review triển khai | So sánh Chroma/FAISS và embedding phù hợp tiếng Việt/Anh. Ghi lựa chọn, revision, metric và prefix nếu dùng, persist index và quy trình cập nhật KB. |
| `0004-own-tool-loop-vs-framework.md` | Khôi và Trọng · Khôi giữ bản soạn | So sánh vòng gọi tool bằng registry với framework agent. Ghi giới hạn bước, schema, lỗi và trách nhiệm xác minh tại Order API. |

Kiểm tra số ADR đã dùng trên nhánh tích hợp trước khi tạo file. Ba ADR trên tương ứng ba quyết định kỹ thuật của đặc tả. ADR-0001 của repo mô tả quy trình viết ADR. [Mẫu ADR](../../docs/templates/ADR.md)

## 6. Eval và nghiệm thu

**Bộ 10 ca CI đề xuất**, chọn theo ID để thứ tự dòng trong JSONL có thể thay đổi:

| Nhóm | Case ID | Kiểm tra chính |
| --- | --- | --- |
| Policy có nguồn (5) | `pol-001`, `pol-002`, `pol-101`, `pol-102`, `pol-106` | Đúng trường response, `doc_id`/đoạn trích khớp nguồn fixture, không phát sinh hành động ngoài dự kiến. |
| Policy thiếu nguồn (1) | `pol-108` | Nói rõ thiếu dữ kiện, đề nghị kết nối hỗ trợ, không bịa phí hoặc tự gọi tool. |
| Tra đơn (4) | `ord-001`, `ord-002`, `ord-104`, `ord-105` | Đúng xác minh, hỏi thêm khi thiếu email, lỗi chung khi sai email hoặc mã không tồn tại, không rò dữ liệu. |

**Baseline v0.** Chạy cả 30 ca qua HTTP, sau khi Docker đã sẵn sàng. Lệnh repo dự kiến dùng được sau tích hợp là `make eval`, tương đương `python eval/run_eval.py --dataset eval/datasets/v0 --api-url http://localhost:8000` từ `customer-support-agent/`. CI dùng `make eval-ci`. Trạng thái `out of scope in S2` hay `not measured` cần hiện rõ, tách khỏi fail thực sự; ca handoff/ticket và các ca đòi guardrail đầy đủ chờ Sprint 3 được ghi lý do theo từng ca. Nếu chỉ chạy mock để kiểm luồng, ghi tên mock và trạng thái baseline với provider thật còn chờ.

| Chỉ số hoặc chứng cứ | Cách đọc và ghi trong báo cáo Sprint 2 |
| --- | --- |
| Citation | Báo số đúng/tổng câu có nhãn nguồn đủ điều kiện. Kiểm nguồn khớp ID và review đoạn trích cho mẫu demo. Ghi riêng policy thiếu nguồn xử lý đúng. |
| Tool và bảo vệ dữ liệu đơn | Báo số ca dùng đúng tool và ca không được gọi tool. So tham số đầy đủ ở integration test nội bộ. Phân biệt tool được gọi hợp lệ nhưng API từ chối xác minh với trường hợp gửi sai tham số. Đếm và báo số lượt có dấu hiệu rò dữ liệu trong nhóm kiểm. |
| Thời gian và chi phí | Lưu độ trễ từng lượt hoặc theo bước, cấu hình máy, token và chi phí ước tính nếu có. Ghi số mẫu; đo chính thức p95 trên 50 lượt đã warm-up ở giai đoạn đánh giá theo NFR-06. |
| Tái lập và chất lượng | Báo commit, phiên bản/hash KB và dataset, model/provider, prompt version, cấu hình index/top-k và lệnh chạy. Accuracy bằng judge, handoff recall/precision và an toàn đầy đủ đo ở Sprint 3. |
| Chứng cứ nộp | CSV + Markdown từ runner, link artifact CI 10 ca và link baseline trong WSR-S2. Đưa code, bộ case nhỏ đã review và tài liệu quyết định vào Git. Kết quả chạy và dữ liệu sinh được để theo quy ước artifact của nhóm. |

### Kịch bản demo cuối sprint

1. Từ `customer-support-agent/`, chuẩn bị `.env` theo `.env.example`; chạy Compose theo README/Design v1. Cho thấy hai endpoint `/health` và bước nạp index hoàn tất.
2. Gọi `POST /v1/chat` hỏi thời hạn đổi trả hoặc cách hoàn tiền. Đọc một câu trả lời và citation kèm đoạn bằng chứng. Hỏi tiếp một câu policy thiếu dữ kiện ở phiên demo riêng và kiểm phản hồi giới hạn.
3. Tra đơn giả ở ba request độc lập gồm thiếu email, email sai và cặp đúng. Đối chiếu `SX-000001` có trạng thái `confirmed` theo fixture đã chốt. Mở log JSON và ghép `trace_id` với response.
4. Chạy lệnh eval, mở bảng điểm baseline, chỉ rõ mẫu số và các giới hạn. Dẫn link CI mock 10 ca.

## 7. Lịch làm việc và cách chia PR

| Mốc | Khôi | Trọng |
| --- | --- | --- |
| **Đầu sprint** | Khóa dataset v0 và ID CI. Chốt interface retrieval/tool, trao đổi provider với mentor. | Chốt fixture và contract Chat/Order. Tạo issue trên board, kiểm đầu vào Sprint 1 và nhánh tích hợp. |
| **Thứ Ba–Tư** | Mở PR ingestion/retriever; ghép provider và orchestrator, dùng tool giả trong lúc BE-1 triển khai. | Mở PR Order API/client, test đúng/sai email; chuẩn bị wiring, volume và log trong Compose. |
| **Thứ Năm** | Chạy 30 ca qua HTTP sau tích hợp, kiểm regressions và chuẩn bị bảng điểm. | Tích hợp Compose, CI mock 10 ca, smoke test và test không lộ dữ liệu. Tổng hợp Design v1 và WSR. |
| **Thứ Sáu** | Bàn giao baseline, ADR và cùng demo hai luồng. | Nộp WSR-S2 trước 12:00, điều phối Review với mentor và Retro. Cập nhật quyết định, backlog Sprint 3. |

**Thứ tự ghép PR.** `Ingestion/retriever` và `Order API/client` có thể merge riêng sau khi kiểm interface. `LLM/orchestrator` và `Chat API/Compose/tracing` ghép khi hai interface sẵn. `Eval runner` có thể làm song song với mock; `CI + baseline + Design` xác minh sau tích hợp. Khi có nhiều issue, tách nhánh theo số issue thật. Ví dụ `feat/<issue>-csa-vector-index` với tiêu đề `feat(csa): build policy vector index`. [CONTRIBUTING.md](../../CONTRIBUTING.md) · [Quy tắc tiêu đề PR](../../.github/workflows/pr-title.yml)

Mỗi người tối thiểu hai PR được merge và hai lượt review có nhận xét. Gắn FR/NFR, issue và lệnh kiểm thử vào PR. Theo dõi CI xanh, ít nhất một approval, squash merge và review trong 24 giờ. Giữ PR nhỏ theo hướng dẫn repo. Stage theo đường dẫn, vì workspace từng có `var/orders.json` và báo cáo local bị stage cùng một lượt. Scrum Master cập nhật board và ghi việc còn vướng sau Review.

## 8. Checklist chốt Sprint 2

- [ ] **Khôi + Trọng** · Docker chạy hai API. Một request policy có trích dẫn đúng, một request tra đơn đúng định dạng và trả thông tin đã xác minh.
- [ ] **Trọng + Khôi** · Có test tự động chứng minh email sai không lộ thông tin. Có bằng chứng cho ca thiếu email và mã không tồn tại.
- [ ] **Khôi** · Ingestion/retrieval chạy trên KB đầy đủ, có nguồn Markdown/PDF và tái nạp sau khi tài liệu đổi/xóa.
- [ ] **Khôi** · Có baseline v0 qua HTTP, xuất CSV/Markdown, ghi provider và số liệu thực tế. Bộ mock trong CI đúng 10 ca.
- [ ] **Trọng** · Log JSON có bằng chứng token, chi phí, độ trễ, tool và đoạn truy xuất. CI, coverage và smoke test có link.
- [ ] **Trọng + Khôi** · Design v1 và ít nhất ba ADR kỹ thuật đã qua review theo quy trình. Quyết định còn mở ghi người phụ trách và ảnh hưởng.
- [ ] **Trọng** · Có PR WSR-S2, link demo, kết quả Retro và backlog Sprint 3. Mục chưa đạt ghi rõ bằng chứng còn thiếu và lý do.

**Nguồn đối chiếu.** Customer Support Agent Requirement Specification v1.0, mục 3–9 và Phụ lục A.1/A.3/A.4; kế hoạch Sprint 1; các bản nháp bàn giao và code hiện có trong repo. Số giờ, nhóm 10 ID CI và phương án vector store/embedding trong file là đề xuất để hai bạn chốt khi Planning.
