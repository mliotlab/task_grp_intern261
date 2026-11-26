# Sprint 2 · Bàn giao AI Engineer

**Người phụ trách** · Trần Minh Khôi · **Ngày kiểm tra** · 25/11/2026

## Đã triển khai

| Hạng mục | Kết quả |
| --- | --- |
| FR-02 · Ingestion | Nạp Markdown và PDF có lớp văn bản. Chia theo tiêu đề/trang rồi áp dụng giới hạn và overlap. Lưu ID nguồn, ID đoạn, text, metadata và cấu hình model trong snapshot. Chạy lại thay cả snapshot để loại đoạn cũ. |
| FR-03 · Retrieval và prompt | Tìm top-k theo cosine trên embedding. Prompt v2 trả JSON có câu trả lời và trích đoạn đối chiếu được. Nếu nguồn lọc rỗng, sai ID, trích đoạn không tồn tại hoặc model báo không đủ bằng chứng, Chat API trả phản hồi thiếu nguồn. Kiểm tra trích đoạn là kiểm tra nguồn. Chất lượng ngữ nghĩa được đo sau với tập eval và provider thật. |
| FR-04 · Phần agent | Tối đa một lời gọi tra đơn đã qua registry. Mã đơn/email phải khớp giá trị khách nhập; kết quả xác minh sai dùng câu trả lời chung. API chỉ trả trạng thái và trường được phép khi thành công. |
| NFR-07 · Trace phần AI | Có ID tài liệu/đoạn, bước retrieval/LLM/tool, token, trạng thái tool và chi phí ước tính nếu đã cấu hình giá. Email không đi vào action công khai hay trace phần AI. |
| NFR-08 · Eval v1 | Kiểm HTTP, schema và hành vi theo case v0. Xuất Markdown/CSV cùng hash dữ liệu và cấu hình. Có chế độ chạy 10 ID cố định với mock, kiểm cả tham số tool nội bộ. |

## Chạy và kiểm tra

Chạy trong `customer-support-agent/` trên checkout đã có đủ 30 ca và 21 policy:

```powershell
python -m pip install -e ".[dev,rag]"
python -m pytest --cov
python -m scripts.ingest_kb --dry-run
python eval/run_eval.py --ci --dataset eval/datasets/v0
```

Chế độ `--ci` kiểm đúng 10 ca và trả mã lỗi nếu sai một ca hoặc thiếu ID. Nhánh Sprint 1 cũ có 18 ca; dùng tập v0 đã tích hợp (có `ord-104` và `ord-105`). Trọng có thể dùng lệnh `--ci` trên trong target `make eval-ci` khi nối CI.

Khi mentor đã chốt provider, cấu hình `.env` theo các trường `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` nếu endpoint yêu cầu, và `PROMPT_VERSION=v2`. Với index cũ hoặc khi đổi embedding model/revision, nạp lại và khởi động lại Chat API. `LLM_BASE_URL` là đường dẫn gốc đến API, thường kết thúc bằng `/v1`.

```powershell
python -m scripts.ingest_kb
python -m uvicorn services.chat_api.main:app --port 8000
```

Từ PowerShell khác, sau khi Chat API và Order API đã nối:

```powershell
$commit = git rev-parse --short HEAD
python eval/run_eval.py --dataset eval/datasets/v0 --api-url http://localhost:8000 --commit $commit --prompt-version v2
```

Điền `--model-label` bằng provider/model đang deploy để report có đủ cấu hình tái lập. Chạy cả 30 ca, báo rõ luồng Sprint 3 và chỉ số chưa đo. Tên/đếm tool được kiểm qua response; tham số đầy đủ kiểm trong mock spy vì email đã được loại khỏi response công khai.

## Kết quả đã chạy

- Kiểm tra dữ liệu từ ref `origin/main` ở `bf22e9b`. Đọc được **21 tài liệu, 76 đoạn** và tải được tập **30 ca** để chọn bộ CI.
- Chạy **10/10 ca mock** với route `/v1/chat`. Citation **5/5**, tên/số lần gọi tool **10/10**, tham số tool qua spy **10/10**, phản hồi bảo vệ dữ liệu ở ca thiếu/sai xác minh **3/3**, fallback khi thiếu dữ kiện **1/1**.
- `pytest --cov` có **36 test đạt**, **1 test handoff được skip** vì thuộc Sprint 3, coverage tổng **89%**. Ruff và kiểm tra định dạng đều đạt.
- Đã kiểm nạp PDF hai trang và đọc metadata trang, dựng lại index sau sửa/xóa file, giữ index hiện hành khi build thất bại. Adapter LLM qua HTTP đã kiểm bằng transport giả lập.
- Đo 30 ca với model thật qua Docker còn chờ provider đã được mentor duyệt, trọng số E5 khả dụng và phần Order API/Compose của Trọng. Trong phiên kiểm thử, máy chưa có cache E5, không kết nối được Hugging Face và Docker daemon chưa chạy.

## Hợp đồng bàn giao cho Trọng

| Điểm nối | Hành vi của AI và phần Backend cần nối |
| --- | --- |
| Order tool | `get_order_status(order_id, email)` giữ chữ ký hiện có. Thành công trả `order_id`, `status`, `estimated_delivery` và `carrier` theo schema Order API. Hai trường cuối có thể null. Nếu xác minh thất bại, trả `{"error":"not_found"}` hoặc ném `httpx.HTTPStatusError` 404/403. Timeout hoặc lỗi khác được báo chung là tạm chưa xử lý được. |
| Container | Cài extra `rag`, copy module `scripts` hoặc cung cấp bước init dùng cùng `KB_DIR`/embedding revision và volume mà Chat API đọc. `/v1/chat` trả 503 nếu chạy provider thật mà chưa có index. |
| CI và báo cáo | Nối `make eval-ci` sang lệnh `--ci` đã kiểm. Upload CSV/Markdown và chạy smoke policy/tra đơn sau khi tích hợp. Dùng kết quả provider thật trong WSR-S2. |

[ADR provider](adr/0002-llm-provider.md) · [ADR retrieval](adr/0003-vector-store-and-embedding.md) · [ADR tool](adr/0004-own-tool-loop-vs-framework.md) · [Eval harness](../eval/run_eval.py)
