# ADR-0002 · Chọn provider LLM cho ShopX

**Trạng thái** · Proposed · **Ngày soạn** · 21/11/2026

**Người đề xuất** · Trần Minh Khôi · **Người phối hợp** · Nguyễn Quốc Trọng · **Người chốt** · Nguyễn Trần Anh Quân

## Bối cảnh

Sprint 1 cần provider để chạy phần sinh câu trả lời của notebook trên 10 câu phát triển. Sprint 2 cần adapter để gọi chat, gửi JSON schema tool và thu thời gian/token nếu provider cung cấp. Đầu vào thử nghiệm là policy và dữ liệu ShopX giả lập. Provider cần có hướng dẫn cấp quyền, cách chạy và giới hạn chi phí rõ ràng.

## Các phương án

| Phương án | Lợi ích | Việc cần xác nhận |
| --- | --- | --- |
| API do mentor cấp | Dễ dùng chung cấu hình model giữa hai máy và thử nhanh một endpoint sẵn có. | URL giao thức, model ID, quota/ngân sách, quyền sử dụng và hỗ trợ tool calling. |
| Ollama chạy local | Có thể giữ dữ liệu trên máy và chạy khi máy có model khả dụng. | Model/phiên bản đã cài, tài nguyên, thời gian phản hồi, tiếng Việt và chất lượng tool calling. |

## Đề xuất quyết định

Ưu tiên thử API mentor cấp khi đã xác nhận endpoint, model và quota. Nếu API chưa sẵn sàng, thử Ollama trên model và máy được mentor đồng ý. Chốt theo khả năng chạy 10 câu notebook và một ca tool call giả lập có JSON đúng schema. Chưa có tên model hoặc phê duyệt được ghi nhận. Trong lúc chờ, notebook chạy baseline TF-IDF với câu trả lời trích xuất cục bộ.

## Hệ quả và việc cần làm

- Khôi cấu hình notebook qua `RAG_SPIKE_BASE_URL`, `RAG_SPIKE_MODEL` và `RAG_SPIKE_API_KEY` nếu endpoint yêu cầu. Ghi model/phiên bản, thời gian, nguồn và lỗi để so các lần chạy.
- Trọng kiểm tra cách dùng cấu hình trong Docker và logging không chứa credential. Nhóm giữ mock cho luồng CI tất định.
- Sau khi mentor chốt, cập nhật provider/model, ngày duyệt, quota hoặc tài nguyên, link bằng chứng và trạng thái Accepted. [Notebook](../../notebooks/rag_spike_s1.ipynb)

## Cập nhật triển khai Sprint 2

Adapter Chat Completions đọc `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY` và `LLM_TIMEOUT_SECONDS`. Đã test mapping tool call, tool result, usage và lỗi HTTP bằng dữ liệu giả lập. File này giữ Proposed trong khi chờ mentor xác nhận model, endpoint và hạn mức thật. [Bàn giao phần AI](../SPRINT_2_AI_HANDOFF.md)
