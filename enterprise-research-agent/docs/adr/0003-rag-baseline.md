# ADR-0004: Lựa chọn RAG Baseline cho Research Pipeline

**Status:** Proposed
**Date:** 23/11/2026
**Deciders:** Nhóm SE-AI-02 và mentor Trần Phan Đăng Khôi (Pending Review)
**Owner:** R2 – Data & Retrieval
**Related Documents:** Requirement Specification v1.0, PRD.md, Design Doc v0, ADR-0003

---

## 1. Context

Enterprise Research Agent cần một cơ chế truy xuất tài liệu làm nền tảng cho Research Pipeline. Khi người dùng đặt câu hỏi, hệ thống phải tìm được các đoạn văn bản liên quan trong bộ sưu tập tài liệu, sau đó cung cấp context cho LLM để tổng hợp câu trả lời và tạo citation.

Trong Sprint 1, nhóm đã triển khai phiên bản Basic RAG với các thành phần:

- PDF parsing bằng PyMuPDF, giữ lại thông tin trang.
- Fixed-size chunking với kích thước 1.000 ký tự và overlap 150 ký tự.
- Sinh embedding thông qua Google Gemini API.
- Lưu trữ vector trong PostgreSQL với extension pgvector.
- Dense Retrieval sử dụng cosine similarity để tìm Top-K chunks.
- Evaluation trên tập câu hỏi với danh sách tài liệu nguồn mong đợi.

Phiên bản hiện tại được sử dụng làm **RAG Baseline**, tức mốc tham chiếu để đo lường hiệu quả của các cải tiến retrieval trong Sprint 2.

### 1.1. Yêu cầu liên quan

- **FR-02:** Tải và xử lý tài liệu, trích xuất nội dung và chia đoạn để phục vụ truy xuất.
- **FR-03:** Tiếp nhận câu hỏi nghiên cứu và thực hiện truy xuất tài liệu liên quan.
- **FR-05:** Câu trả lời phải có citation tham chiếu đến tài liệu và trang/mục nguồn.
- **NFR-01:** Citation correctness ≥90% trên ít nhất 50 citation được lấy mẫu.
- **NFR-02:** Answer coverage ≥70% trên 30 câu hỏi đánh giá.
- **NFR-03:** p95 thời gian hoàn thành research job ≤180 giây.

Các yêu cầu NFR trên áp dụng cho hệ thống và Research Pipeline hoàn chỉnh. RAG Baseline chỉ cung cấp mốc đánh giá ban đầu, không đồng nghĩa đã chứng minh toàn bộ NFR đạt yêu cầu.

### 1.2. Mục đích xây dựng Baseline

Nhóm cần một phiên bản retrieval đủ đơn giản, có thể tái lập và đo lường được để:

1. Xác định chất lượng truy xuất của phương pháp Dense Retrieval cơ bản.
2. Có kết quả tham chiếu trước khi bổ sung các kỹ thuật Advanced RAG.
3. Đánh giá mức cải thiện của từng kỹ thuật bằng cùng một evaluation dataset.
4. Tránh triển khai nhiều kỹ thuật cùng lúc nhưng không xác định được kỹ thuật nào thực sự cải thiện kết quả.

---

## 2. Decision Drivers

Các tiêu chí được sử dụng để lựa chọn RAG Baseline:

- **Simplicity:** Dễ triển khai, kiểm thử và bảo trì trong phạm vi dự án.
- **Reproducibility:** Có thể chạy lại trên cùng corpus, evaluation dataset và cấu hình để thu được kết quả có thể so sánh.
- **Retrieval Quality:** Có khả năng tìm kiếm các chunks liên quan về mặt ngữ nghĩa.
- **Traceability:** Giữ lại metadata như document ID, filename, page và chunk ID để phục vụ citation.
- **Scalability:** Có khả năng mở rộng sang các kỹ thuật retrieval và indexing khác.
- **Evaluability:** Có metric cụ thể để so sánh với những phiên bản RAG tiếp theo.

---

## 3. Options Considered

### Option A — Dense Retrieval với Exact KNN (pgvector)

**Mô tả:**

- Sinh embedding cho từng chunk và query.
- Lưu embedding trong PostgreSQL thông qua pgvector.
- Sử dụng cosine distance để xếp hạng các chunks.
- Trả về Top-K chunks có khoảng cách nhỏ nhất.

**Ưu điểm:**

- Kiến trúc đơn giản, ít thành phần phụ thuộc.
- Tìm kiếm theo ngữ nghĩa thay vì chỉ dựa trên từ khóa.
- Exact KNN cho kết quả chính xác theo metric cosine, không có sai số do ANN approximation.
- Dễ đánh giá và sử dụng làm baseline.
- Tích hợp trực tiếp với PostgreSQL đang được sử dụng.

**Hạn chế:**

- Có thể bỏ sót những tài liệu chứa từ khóa, mã định danh hoặc thuật ngữ chính xác nhưng không có độ tương đồng ngữ nghĩa cao.
- Chưa hỗ trợ query decomposition.
- Hiệu năng truy vấn có thể giảm khi số lượng vector tăng lớn do phải thực hiện tìm kiếm chính xác.
- Chất lượng phụ thuộc vào embedding model và chiến lược chunking.

**Đánh giá:** Phù hợp nhất để xây dựng RAG Baseline trong Sprint 1. **Đề xuất lựa chọn.**

### Option B — Sparse Retrieval với BM25

**Mô tả:**

Tìm kiếm tài liệu dựa trên sự xuất hiện và tần suất của các từ khóa trong query và document.

**Ưu điểm:**

- Hiệu quả với từ khóa chính xác, mã định danh và thuật ngữ chuyên ngành.
- Không cần sinh embedding.
- Có thể bổ sung như một retrieval branch độc lập.

**Hạn chế:**

- Khả năng hiểu ngữ nghĩa và các cách diễn đạt khác nhau còn hạn chế.
- Không tận dụng được embedding hiện có.
- Cần thiết lập và đánh giá thêm hệ thống inverted index.

**Đánh giá:** Chưa lựa chọn làm baseline. Được cân nhắc trong Sprint 2 để kết hợp với Dense Retrieval theo hướng Hybrid Search.

### Option C — Hybrid Retrieval (BM25 + Dense Retrieval)

**Mô tả:**

Kết hợp kết quả từ hai phương pháp:

- BM25: tìm kiếm theo lexical matching.
- Dense Retrieval: tìm kiếm theo semantic similarity.

Hai danh sách kết quả có thể được kết hợp bằng Reciprocal Rank Fusion (RRF).

**Ưu điểm:**

- Kết hợp khả năng tìm kiếm từ khóa chính xác và ngữ nghĩa.
- Hạn chế điểm yếu riêng lẻ của từng phương pháp.
- Có thể cải thiện chất lượng retrieval trên các câu hỏi phức tạp.

**Hạn chế:**

- Tăng độ phức tạp trong việc quản lý và đánh giá nhiều retrieval branches.
- Cần xác định chiến lược kết hợp thứ hạng.
- Chưa có baseline để chứng minh Hybrid Retrieval cải thiện kết quả đến mức nào.

**Đánh giá:** Deferred sang Sprint 2 để thử nghiệm và so sánh với Dense Retrieval Baseline.

### Option D — Approximate Nearest Neighbor (ANN)

**Mô tả:**

Sử dụng ANN index để tăng tốc tìm kiếm vector gần nhất bằng cách chấp nhận một mức sai số nhất định so với Exact Nearest Neighbor Search.

pgvector hỗ trợ hai phương pháp indexing chính:

| Index | Đặc điểm |
|---|---|
| HNSW | Graph nhiều tầng, có trade-off tốc độ và recall tốt, nhưng tốn bộ nhớ và thời gian xây dựng index hơn |
| IVFFlat | Chia vector thành các cluster và chỉ tìm kiếm trên một số cluster được lựa chọn; build nhanh hơn và ít tốn bộ nhớ hơn HNSW |

**Ưu điểm:**

- Tăng tốc truy vấn khi số lượng vector lớn.
- Có thể điều chỉnh các tham số để cân bằng tốc độ và recall.

**Hạn chế:**

- Kết quả không còn bảo đảm chính xác tuyệt đối theo metric như Exact KNN.
- Cần benchmark và điều chỉnh tham số indexing.
- Filtering theo `collection_id` và `owner_id` có thể khiến số kết quả trả về ít hơn Top-K mong muốn do filtering được thực hiện sau khi ANN index scan.

**Đánh giá:** Chưa cần áp dụng cho baseline. Giữ Exact KNN làm reference và cân nhắc HNSW hoặc IVFFlat khi có nhu cầu tối ưu hiệu năng được chứng minh bằng benchmark.

### Option E — Advanced Chunking

**Mô tả:**

Thay thế Fixed-size Chunking bằng các chiến lược chia đoạn nâng cao như:

- Semantic Chunking: chia đoạn dựa trên sự thay đổi về ngữ nghĩa.
- Recursive Chunking: chia đoạn theo cấu trúc phân cấp, lần lượt từ đơn vị lớn xuống nhỏ để kiểm soát kích thước chunk.

**Ưu điểm:**

- Có khả năng giữ được ngữ cảnh và ranh giới nội dung tốt hơn.
- Hạn chế chia cắt các ý liên quan.
- Có thể cải thiện chất lượng truy xuất và citation.

**Hạn chế:**

- Phức tạp hơn trong xử lý ingestion.
- Cần đánh giá cấu hình chunking và cách bảo toàn metadata.
- Cần tái xử lý tài liệu và tạo lại embeddings khi thay đổi chiến lược.

**Đánh giá:** Giữ Fixed-size Chunking làm baseline. Semantic Chunking và Recursive Chunking được đưa vào kế hoạch thử nghiệm Sprint 2.

---

## 4. Decision

**Đề xuất lựa chọn Option A: Fixed-size Chunking + Dense Retrieval + Exact KNN trên PostgreSQL/pgvector làm RAG Baseline.**

Baseline được tổ chức theo pipeline:

```text
PDF Document
     |
     v
PyMuPDF Parsing
     |
     v
Page-aware Fixed-size Chunking
     |
     v
Embedding Generation
     |
     v
PostgreSQL + pgvector
     |
     v
Original User Query
     |
     v
Query Embedding
     |
     v
Exact Cosine Similarity Search
     |
     v
Top-K Chunks (K = 5)
     |
     v
Retrieval Results + Source Metadata
```

### 4.1. Document Parsing và Chunking

**Document Parsing:**

- Sử dụng PyMuPDF để trích xuất văn bản từ PDF.
- Duyệt từng trang và giữ lại số trang tương ứng.
- Bỏ qua các trang không có nội dung văn bản.
- Không gộp nội dung giữa hai trang khi chia chunk.

**Fixed-size Chunking:**

| Configuration | Giá trị |
|---|---:|
| Chunk size | 1.000 ký tự |
| Chunk overlap | 150 ký tự |
| Chunk step | 850 ký tự |
| Boundary | Theo từng trang PDF |

Chunk size và overlap được tính theo số ký tự, không phải số token.

Mỗi chunk giữ lại metadata:

- `document_id`
- `ordinal`
- `text`
- `page`
- `section`

Cách chia đoạn này được lựa chọn vì dễ triển khai, dễ tái lập và tạo ra baseline ổn định để đánh giá các phương pháp chunking nâng cao sau này.

**Lưu ý phạm vi:** Triển khai baseline trong code hiện tại sử dụng PDF parser. Việc hỗ trợ DOCX và Markdown vẫn phải đáp ứng phạm vi định dạng tài liệu của FR-02 thông qua các parser tương ứng.

### 4.2. Embedding Generation

- Sử dụng Google Gemini API thông qua Google GenAI SDK trong triển khai hiện tại.
- Model được cấu hình bằng `settings.embedding_model`.
- Số chiều vector được cấu hình bằng `settings.embedding_dim`.
- Query và document chunks phải sử dụng cùng embedding model và cùng dimensionality.
- Mỗi batch tối đa 32 texts.
- Rate limiter hiện tại giới hạn 80 texts/phút trên mỗi Python process.
- Khi API trả về 429, hệ thống thực hiện retry tối đa 2 lần theo retry delay được cung cấp; nếu không lấy được thông tin delay thì sử dụng mặc định 30 giây.

Model và dimensionality cụ thể được quản lý riêng, không được thay đổi tùy ý giữa các lần embedding mà không tái tạo vector tương ứng.

**Phạm vi ADR:** ADR này chốt cách sử dụng embedding trong baseline, không thay thế quyết định lựa chọn chính thức embedding model và dimensionality.

### 4.3. Vector Storage

- Sử dụng PostgreSQL với extension pgvector.
- Lưu vector trong trường `chunks.embedding`.
- Giữ nguyên metadata của chunk để phục vụ truy xuất và citation.
- Query vector được tạo bằng cùng phương pháp embedding với document vectors.

### 4.4. Retrieval Strategy

**Phương pháp:** Dense Retrieval với Exact Nearest Neighbor Search.

- Metric: Cosine distance.
- Ranking: Sắp xếp cosine distance tăng dần.
- Default Top-K: 5.
- Không sử dụng BM25 hoặc query decomposition trong baseline.
- Không sử dụng RRF hoặc Cross-Encoder reranking.

Query phải áp dụng các điều kiện lọc:

- `Document.collection_id = collection_id`
- `Document.owner_id = owner_id`
- `Collection.owner_id = owner_id`
- `Document.status = ready`

Chỉ các chunks thuộc bộ sưu tập hợp lệ, đúng chủ sở hữu và có trạng thái tài liệu `ready` mới được phép tham gia retrieval.

Similarity score được tính:

\[
similarity = 1 - cosine\_distance
\]

### 4.5. Vector Indexing Strategy

**Không tạo ANN index trong RAG Baseline.**

pgvector mặc định thực hiện Exact Nearest Neighbor Search khi không có approximate index tương ứng. Phương pháp này cung cấp kết quả chính xác theo metric tìm kiếm và được sử dụng làm reference để đánh giá các ANN index về sau.

Cụ thể:

- Không sử dụng HNSW index trong baseline.
- Không sử dụng IVFFlat index trong baseline.
- Giữ Exact KNN để có kết quả tham chiếu khi benchmark ANN.

Việc bổ sung ANN index chỉ được xem xét khi có số liệu cho thấy Exact Search không còn đáp ứng yêu cầu hiệu năng.

### 4.6. Retrieval Output

Mỗi kết quả retrieval cần giữ các thông tin:

| Field | Ý nghĩa |
|---|---|
| `rank` | Thứ hạng trong danh sách kết quả |
| `chunk_id` | Định danh chunk |
| `document_id` | Định danh tài liệu |
| `filename` | Tên tài liệu nguồn |
| `ordinal` | Vị trí chunk trong tài liệu |
| `text` | Nội dung chunk |
| `page` | Trang nguồn |
| `section` | Mục nguồn |
| `score` | Cosine similarity score |

Các metadata này được sử dụng cho bước tạo citation và hiển thị nguồn tham chiếu ở Frontend.

---

## 5. Evaluation Strategy

### 5.1. Baseline Evaluation

Sử dụng evaluation dataset hiện có với cấu trúc:

- `id`
- `question`
- `key_points`
- `source_documents`

Mỗi câu hỏi được truy xuất độc lập bằng chính nội dung query ban đầu, không thực hiện query decomposition.

**Primary Metric: Source-document Hit@K**

Một câu hỏi được tính là `source_hit` khi ít nhất một tài liệu nguồn mong đợi xuất hiện trong Top-K kết quả.

\[
Hit@K(q) =
\begin{cases}
1, & \text{nếu có ít nhất một nguồn đúng trong Top-K}\\
0, & \text{ngược lại}
\end{cases}
\]

\[
SourceHitRate@K =
\frac{\sum_{q=1}^{N} Hit@K(q)}{N}
\]

Cấu hình baseline:

\[
K = 5
\]

Metric này đo khả năng tìm được tài liệu nguồn ở cấp document, không trực tiếp đánh giá thứ hạng chính xác của từng chunk hoặc chất lượng câu trả lời.

`key_points` được giữ lại để phục vụ đánh giá answer quality ở các bước sau, không tham gia retrieval scoring hiện tại.

### 5.2. Evaluation Requirements

Mỗi evaluation run cần ghi nhận:

- Evaluation dataset version.
- Corpus version.
- Embedding model và dimensionality.
- Chunk size và overlap.
- Retrieval method.
- Top-K.
- Source Hit@5.
- Thời gian retrieval và các lỗi phát sinh.

Khi đánh giá các cải tiến Advanced RAG, nhóm phải giữ nguyên evaluation dataset và corpus nguồn để đảm bảo kết quả có thể so sánh.

Nếu thay đổi embedding model hoặc dimensionality, phải thực hiện re-embedding trên corpus trước khi chạy evaluation.

### 5.3. Distinction Between Retrieval and Answer Evaluation

Không sử dụng Source Hit@5 để kết luận trực tiếp rằng hệ thống đạt NFR-01 hoặc NFR-02.

| Metric | Phạm vi đánh giá |
|---|---|
| Source Hit@5 | Khả năng tìm được tài liệu nguồn |
| Citation correctness | Độ chính xác của citation trong câu trả lời |
| Answer coverage | Mức độ bao phủ các ý chính của câu hỏi |
| Research job latency | Thời gian hoàn thành toàn bộ research pipeline |

Các metric NFR chính thức tiếp tục được đánh giá theo Requirement Specification.

---

## 6. Consequences

### 6.1. Benefits

- Có một retrieval baseline rõ ràng và có thể tái lập.
- Exact KNN giúp loại bỏ yếu tố sai số do ANN approximation khi đánh giá ban đầu.
- Pipeline đơn giản, phù hợp với kiến trúc PostgreSQL + pgvector hiện tại.
- Dễ dàng kiểm tra kết quả bằng similarity score và metadata.
- Có thể dùng làm reference để đo mức cải thiện của các kỹ thuật Advanced RAG.
- Không cần triển khai thêm search engine hoặc vector database riêng.

### 6.2. Trade-offs và Limitations

- Fixed-size Chunking chưa nhận biết ranh giới ngữ nghĩa và cấu trúc nội dung.
- Dense Retrieval có thể bỏ sót các kết quả phù hợp về từ khóa chính xác.
- Query nguyên bản có thể chưa đủ để biểu diễn các câu hỏi nghiên cứu phức tạp.
- Exact KNN có thể không đáp ứng latency khi số lượng vector tăng lớn.
- Embedding API phụ thuộc quota và kết nối bên ngoài.
- Rate limiter hiện tại chỉ có phạm vi trong một Python process, chưa đảm bảo giới hạn quota dùng chung khi có nhiều worker process.
- Source Hit@5 hiện chưa phản ánh đầy đủ relevance ở cấp chunk và thứ hạng kết quả.

Những hạn chế này được chấp nhận trong phạm vi baseline để ưu tiên tính đơn giản và khả năng đo lường.

---

## 7. Future Direction – Advanced RAG (Sprint 2)

RAG Baseline được xem là điểm xuất phát cho việc nghiên cứu và phát triển Advanced RAG trong Sprint 2.

Các hướng dưới đây là **planned experiments**, chưa phải những quyết định kiến trúc đã được chốt.

### 7.1. Advanced Ingestion

Nghiên cứu cải tiến chiến lược chia đoạn:

- **Semantic Chunking:** Phân chia nội dung theo sự liên kết về ngữ nghĩa thay vì chỉ dựa trên số ký tự.
- **Recursive Chunking:** Chia nội dung theo cấu trúc phân cấp để bảo toàn ngữ cảnh và kiểm soát kích thước chunk.

Mục tiêu là đánh giá ảnh hưởng của chiến lược chunking đến chất lượng retrieval và citation.

Hai chiến lược sẽ được đánh giá có kiểm soát trước khi quyết định sử dụng riêng lẻ hoặc kết hợp.

### 7.2. Query Processing

Nghiên cứu **Query Decomposition**:

- Phân tích câu hỏi nghiên cứu ban đầu.
- Chia câu hỏi phức tạp thành các sub-queries nhỏ hơn.
- Thực hiện retrieval trên từng sub-query.
- Tổng hợp các kết quả trước khi chuyển sang ranking.

Mục tiêu là cải thiện khả năng xử lý các câu hỏi cần thông tin từ nhiều chủ đề hoặc nhiều tài liệu.

### 7.3. Hybrid Retrieval

Kết hợp hai phương pháp:

| Retrieval branch | Method | Mục tiêu |
|---|---|---|
| Lexical | BM25 | Tìm chính xác từ khóa và thuật ngữ |
| Semantic | Dense Retrieval | Tìm nội dung tương đồng về ngữ nghĩa |

Hai danh sách kết quả được tổng hợp để tận dụng điểm mạnh của cả hai phương pháp.

### 7.4. Ranking và Reranking

Nghiên cứu hai bước:

**Reciprocal Rank Fusion (RRF):**

- Kết hợp các danh sách kết quả từ BM25 và Dense Retrieval.
- Dựa trên thứ hạng thay vì so sánh trực tiếp các score có thang đo khác nhau.

**Cross-Encoder Reranking:**

- Đánh giá mức độ liên quan giữa query và từng candidate chunk.
- Sắp xếp lại danh sách kết quả sau bước fusion.
- Chọn các chunks phù hợp nhất để cung cấp cho LLM.

### 7.5. ANN Indexing

Khi số lượng vectors hoặc thời gian truy vấn trở thành bottleneck, nhóm sẽ đánh giá ANN indexing.

Các ứng viên:

- HNSW.
- IVFFlat.

Exact KNN từ baseline sẽ tiếp tục được sử dụng làm reference để so sánh:

- Retrieval latency.
- Recall so với Exact KNN.
- Khả năng đáp ứng Top-K khi có filtering theo collection và owner.
- Tài nguyên sử dụng và chi phí xây dựng index.

Không mặc định ANN sẽ thay thế Exact KNN nếu chưa có benchmark chứng minh lợi ích thực tế.

### 7.6. Planned Experimental Comparison

Các thử nghiệm dự kiến:

| Experiment | Thay đổi so với baseline | Mục đích |
|---|---|---|
| E0 – Baseline | Fixed-size + Dense + Exact KNN | Mốc tham chiếu |
| E1 – Advanced Chunking | Semantic hoặc Recursive Chunking | Đánh giá ảnh hưởng của chunking |
| E2 – Query Decomposition | Decompose query trước retrieval | Đánh giá khả năng xử lý câu hỏi phức tạp |
| E3 – Hybrid Retrieval | BM25 + Dense + RRF | Đánh giá khả năng kết hợp lexical và semantic search |
| E4 – Reranking | Thêm Cross-Encoder | Đánh giá cải thiện thứ hạng chunks |
| E5 – ANN | Thay Exact KNN bằng HNSW hoặc IVFFlat | Đánh giá trade-off latency và recall |

Các experiment cần được thực hiện có kiểm soát. Khi có thể, mỗi lần thử nghiệm chỉ thay đổi một thành phần chính để xác định rõ tác động của kỹ thuật đó.

Việc lựa chọn kiến trúc Advanced RAG cuối cùng sẽ dựa trên evaluation results, không chỉ dựa trên số lượng kỹ thuật được tích hợp.

---

## 8. Risks and Open Questions

| ID | Rủi ro / Câu hỏi | Hướng xử lý |
|---|---|---|
| R1 | Fixed-size Chunking có thể chia cắt nội dung ngữ nghĩa | Benchmark Semantic và Recursive Chunking trong Sprint 2 |
| R2 | Dense Retrieval bỏ sót nội dung phù hợp về từ khóa chính xác | Đánh giá Hybrid Retrieval với BM25 |
| R3 | Exact KNN có thể giảm hiệu năng khi corpus mở rộng | Đo latency và benchmark ANN index |
| R4 | Embedding API bị giới hạn quota hoặc trả về 429 | Duy trì batching, rate limiting và retry; đánh giá giới hạn khi tăng worker |
| R5 | Thay đổi embedding model làm mất tính tương thích của vector hiện có | Quản lý model/dimension version và re-embedding khi thay đổi |
| R6 | Advanced RAG có nhiều thành phần khiến khó xác định nguồn cải thiện | Sử dụng ablation experiments trên cùng evaluation dataset |

**Open Questions:**

1. Semantic Chunking và Recursive Chunking có nên được kết hợp hay lựa chọn dựa trên kết quả benchmark?
2. Query Decomposition nên sử dụng LLM hiện có hay một phương pháp decomposition khác?
3. BM25 sẽ được triển khai bằng giải pháp nào phù hợp với PostgreSQL hiện tại?
4. Cross-Encoder model nào đáp ứng được yêu cầu chất lượng và latency?
5. Khi nào corpus đủ lớn để chuyển từ Exact KNN sang ANN indexing?

Các câu hỏi trên sẽ được giải quyết thông qua implementation và evaluation trong Sprint 2, không thuộc phạm vi quyết định của baseline hiện tại.

---

## 9. References

1. [pgvector – Official Documentation](https://github.com/pgvector/pgvector)
   - Exact nearest neighbor search.
   - HNSW và IVFFlat indexing.
   - Filtering và iterative index scans.
2. Requirement Specification v1.0.
3. PRD.md.
4. Design Doc v0.
5. ADR-0003 – Lựa chọn LLM cho Research Pipeline.

---

## 10. Decision Outcome

Nhóm đề xuất sử dụng **Fixed-size Chunking + Dense Retrieval + Exact KNN (pgvector)** làm RAG Baseline.

Quyết định này nhằm thiết lập một mốc đánh giá ổn định trước khi triển khai Advanced RAG trong Sprint 2.

Các kỹ thuật Semantic/Recursive Chunking, Query Decomposition, Hybrid Retrieval, RRF, Cross-Encoder và ANN Indexing sẽ được xem xét thông qua các thử nghiệm riêng biệt.

**Decision Status:** Pending Review and Approval by the team and mentor.
