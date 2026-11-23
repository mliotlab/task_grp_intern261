# ADR-0007: Lựa chọn RAG Baseline cho Research Pipeline

**Status:** Proposed
**Date:** 23/11/2026
**Owner:** R2 – Data & Retrieval
**Deciders:** Nhóm SE-AI-02 và mentor (Pending Review)
**Related Documents:** Requirement Specification v1.0, PRD.md, Design Doc v0, ADR-0003, ADR-0004

## 1. Context

Enterprise Research Agent cần một retrieval mechanism để tìm các đoạn nội dung liên quan trong tài liệu thuộc collection. Kết quả retrieval được chuyển tới Research Pipeline cùng source metadata để tạo câu trả lời có citations.

Nhóm cần một baseline đơn giản, có thể tái lập và đo lường được, phục vụ việc hoàn thành Walking Skeleton trong Sprint 2 và làm mốc tham chiếu cho những cải tiến sau này.

Implementation hiện tại đã có các thành phần:

- PDF parsing bằng PyMuPDF, giữ lại page metadata.
- Fixed-size Chunking.
- Embedding generation bằng Gemini Embedding 2.
- Vector storage trên PostgreSQL với pgvector.
- Dense Retrieval sử dụng cosine distance.

## 2. Options Considered

| Option | Description | Advantages | Trade-offs |
|---|---|---|---|
| A. Dense + Exact KNN | Embedding và cosine similarity trên pgvector | Đơn giản, tìm kiếm theo ngữ nghĩa, kết quả chính xác theo distance metric | Có thể bỏ sót từ khóa chính xác; latency tăng khi corpus lớn |
| B. Sparse Retrieval | BM25 | Hiệu quả với keyword, identifier và thuật ngữ chính xác | Không trực tiếp biểu diễn semantic similarity |
| C. Hybrid Retrieval | BM25 + Dense Retrieval | Kết hợp lexical và semantic search | Tăng độ phức tạp, cần đánh giá cách kết hợp ranking |
| D. Dense + ANN | HNSW hoặc IVFFlat | Có thể cải thiện tốc độ khi corpus lớn | Trade-off giữa latency và recall; cần benchmark và tuning |

## 3. Decision

**Proposed decision: Chọn Option A – Fixed-size Chunking + Dense Retrieval + Exact KNN trên PostgreSQL/pgvector làm RAG Baseline.**

### 3.1. Chunking

Đối với PDF documents:

- Parsing bằng PyMuPDF và giữ lại page metadata.
- Chunk size: 1.000 ký tự.
- Chunk overlap: 150 ký tự.
- Chunk step: 850 ký tự.
- Không chia chunk xuyên qua ranh giới trang.

Mỗi chunk giữ lại:

- `document_id`
- `ordinal`
- `text`
- `page`
- `section`

### 3.2. Embedding và Vector Storage

- Sử dụng PostgreSQL với pgvector.
- Lưu vector trong `chunks.embedding`.
- Embedding model và dimensionality tuân theo ADR-0004.
- Implementation hiện tại sử dụng `gemini-embedding-2`.
- Query và document chunks phải dùng cùng model và output dimensionality.
- Nếu giữ schema hiện tại `vector(384)`, Gemini API phải được cấu hình với `output_dimensionality=384`.

Embedding model và dimension phải được cấu hình qua environment variables; không hardcode model selection trong source code.

### 3.3. Retrieval

- Method: Dense Retrieval.
- Distance metric: Cosine distance.
- Ranking: Cosine distance tăng dần.
- Default Top-K: 5.
- Indexing strategy: Exact Nearest Neighbor Search.
- Không sử dụng ANN index trong baseline.

Similarity score:

\[
similarity = 1 - cosine\_distance
\]

Mỗi truy vấn phải áp dụng các điều kiện bảo đảm collection ownership và document eligibility:

- `Document.collection_id = collection_id`
- `Document.owner_id = owner_id`
- `Collection.owner_id = owner_id`
- `Document.status = ready`

Retrieval output phải giữ lại metadata để phục vụ citation:

`rank`, `chunk_id`, `document_id`, `filename`, `ordinal`, `text`, `page`, `section`, `score`.

### 3.4. Sprint 2 Scope

Sprint 2 tập trung vào Walking Skeleton với luồng end-to-end:

`Upload → Ingestion → Chunking → Embedding → Storage → Retrieval → Answer with Citations → Frontend`

Các thành phần cần được triển khai và kiểm thử theo baseline đã xác định.

LLM provider/model không được quyết định trong ADR này. Trong khi ADR-0003 chưa được phê duyệt, LLM default phải là `mock`; model thật được chọn thông qua `.env`.

Các kỹ thuật Advanced RAG như Semantic/Recursive Chunking, Query Decomposition, Hybrid Retrieval, RRF, Cross-Encoder Reranking và ANN Indexing không thuộc phạm vi Sprint 2. Chúng được chuyển sang backlog để xem xét sau khi có luồng end-to-end và kết quả đo NFR.

## 4. Consequences

### Benefits

- Pipeline đơn giản và giảm độ phức tạp trong Walking Skeleton.
- Fixed-size Chunking dễ kiểm thử và tái lập.
- Exact KNN cung cấp kết quả tham chiếu không có sai số do ANN approximation.
- Source metadata được giữ lại để phục vụ citation.
- Có thể dùng cùng evaluation dataset và corpus để so sánh các cải tiến sau này.

### Trade-offs

- Fixed-size Chunking chưa nhận biết ranh giới ngữ nghĩa.
- Dense Retrieval có thể bỏ sót kết quả phù hợp với keyword hoặc identifier chính xác.
- Exact KNN có thể giảm hiệu năng khi corpus tăng lớn.
- Thay đổi embedding model hoặc dimension yêu cầu re-embedding corpus.
- Source Hit@5 không chứng minh citation correctness hoặc answer coverage.

### Baseline Evaluation

Metric chính: **Source-document Hit@5**.

Một câu hỏi được tính là hit khi ít nhất một tài liệu trong danh sách `source_documents` xuất hiện trong Top-5 retrieval results.

\[
SourceHit@5 =
\frac{\text{Number of questions with at least one expected source in Top-5}}
{\text{Total evaluated questions}}
\times 100\%
\]

Kết quả baseline phải được bổ sung từ evaluation run thực tế:

| Evaluation Information | Result |
|---|---|
| Evaluation dataset | v0 |
| Number of questions | Pending measurement |
| Corpus version / hash | Pending recording |
| Embedding model | `gemini-embedding-2` |
| Embedding dimension | 384, subject to implementation verification |
| Chunk size / overlap | 1,000 / 150 characters |
| Retrieval method | Dense + Exact KNN |
| Distance metric | Cosine |
| Top-K | 5 |
| Source Hit@5 | Pending measurement |
| Retrieval latency | Pending measurement |
| Evaluation commit SHA | Pending recording |

Không sử dụng Source Hit@5 để kết luận trực tiếp rằng hệ thống đạt:

- **NFR-01:** Citation correctness ≥90% trên ít nhất 50 citations.
- **NFR-02:** Answer coverage ≥70% trên 30 câu hỏi.
- **NFR-03:** p95 Research Job Latency ≤180 giây.

**Decision Status:** Proposed — pending baseline measurement and team/mentor approval.

## References

1. [pgvector – Official Documentation](https://github.com/pgvector/pgvector)
2. Requirement Specification v1.0.
3. PRD.md.
4. Design Doc v0.
5. ADR-0003 – Lựa chọn LLM Provider.
6. ADR-0004 – Lựa chọn Embedding Model và Dimensionality.
