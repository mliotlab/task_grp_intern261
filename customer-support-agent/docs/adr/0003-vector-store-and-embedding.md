# ADR-0003 · Vector index và embedding cho kho policy

**Trạng thái** · Proposed · **Ngày soạn** · 25/11/2026 · **Người đề xuất** · Trần Minh Khôi

## Bối cảnh

Sprint 2 cần tìm đoạn chính sách tiếng Việt và tiếng Anh, trả ID nguồn/đoạn trích và thay kho dữ liệu khi policy được thêm, sửa hoặc xóa. Bản KB tích hợp được dùng để kiểm thử có 21 tài liệu và 76 đoạn với cấu hình hiện tại. API đọc cùng phiên bản index đã được đóng gói, kể cả khi tiến trình nạp thất bại.

## Các phương án

| Phương án | Ưu điểm | Chi phí hoặc giới hạn |
| --- | --- | --- |
| NumPy lưu ma trận đã chuẩn hóa và tìm cosine chính xác | Đọc một snapshot, dễ kiểm tra thứ tự kết quả và metadata. Thử được cả quy trình lưu và mở index với embedding giả lập. | Quét toàn bộ vector mỗi truy vấn và giữ ma trận trong RAM. Chưa có lọc metadata hoặc nhiều người ghi. |
| Chroma | Có API lưu collection và truy vấn theo vector/metadata. | Tăng phụ thuộc runtime và cần chốt cấu hình cấp phát, thu gom snapshot và backup. |
| FAISS | Hỗ trợ lập index vector với nhiều lựa chọn tìm kiếm. | Cần quản lý mapping metadata, đóng gói binary và lựa chọn loại index theo kích thước thực tế. |

## Đề xuất và hiện trạng code

Dùng NumPy chính xác cho Sprint 2. Dùng mặc định `intfloat/multilingual-e5-small`, có `EMBEDDING_REVISION` để ghim phiên bản sau khi thống nhất. Với E5, thêm `passage:` cho đoạn và `query:` cho câu hỏi. Lưu ma trận float32 đã chuẩn hóa. Tích vô hướng với query đã chuẩn hóa là cosine, điểm lớn hơn được ưu tiên. Nhóm sẽ đo retrieval trên bộ dev trước khi chốt `min_score` cho provider/model thật. [Model card E5](https://huggingface.co/intfloat/multilingual-e5-small)

## Hệ quả

Mỗi lần nạp tạo một tệp tạm có vector, cấu hình model và metadata, rồi thay `var/vector_store/policy-index.npz` bằng một thao tác sau khi ghi thành công. Truy vấn đang dùng snapshot trong bộ nhớ giữ bản cũ cho tới khi reload Chat API. Nếu thay model hoặc revision, build lại index bằng cùng cấu hình. Cân nhắc Chroma hoặc FAISS khi benchmark thực tế cho thấy quét toàn ma trận vượt ngân sách độ trễ/bộ nhớ hoặc khi nhóm cần lọc metadata.
