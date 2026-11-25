# ADR-0004 · Điều phối tool bằng registry

**Trạng thái** · Proposed · **Ngày soạn** · 25/11/2026 · **Người đề xuất** · Trần Minh Khôi

## Bối cảnh và phương án

Walking Skeleton có một tool nghiệp vụ triển khai là `get_order_status`. Có thể mở rộng bằng Pydantic registry hiện có, hoặc dùng framework agent có runtime điều phối. Framework hữu ích nếu một lượt cần nhiều bước phụ thuộc nhau. Luồng Sprint 2 chỉ tra một đơn và cần kiểm soát chặt tham số, quyền truy cập và đầu ra.

## Đề xuất và hiện trạng code

- Phân loại tối thiểu hai luồng policy và tra đơn. Với policy, agent chỉ gọi LLM sau khi có nguồn phù hợp và chỉ trả trích dẫn khớp đoạn thật trong context.
- Với tra đơn, agent yêu cầu đúng một mã đơn và một email hợp lệ từ lượt hiện tại. LLM đề xuất một lời gọi `get_order_status`. Orchestrator so các tham số với dữ liệu khách đã nhập, rồi dùng registry xác thực trước khi gọi.
- Một lượt Sprint 2 tối đa một lần gọi thật. Kết quả hợp lệ được chuyển thành câu trả lời từ schema đã xác minh. Quyết định định dạng này giảm thêm một lần gọi provider và tránh để model suy diễn trạng thái đơn. Adapter vẫn đọc/ghi được message tool call và tool result cho các bước điều phối sau này.
- Backend giữ quyền kiểm tra mã đơn/email và trả kết quả phù hợp. Agent chỉ công bố các trường nằm trong hợp đồng kết quả sau khi xác minh thành công.

## Hệ quả

Test có thể thay LLM, retriever và tool qua interface hiện có. Ticket, handoff, bộ nhớ nhiều lượt và điều phối phức tạp được xem xét ở Sprint 3. [Phần bàn giao AI](../SPRINT_2_AI_HANDOFF.md)
