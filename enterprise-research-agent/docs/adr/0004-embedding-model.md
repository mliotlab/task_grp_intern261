# ADR-0004: Lựa chọn Embedding Model và Dimensionality

**Status:** Proposed
**Date:** 23/11/2026
**Owner:** R2 – Data & Retrieval
**Deciders:** Nhóm SE-AI-02 và mentor (Pending Review)
**Related Documents:** Requirement Specification v1.0, Design Doc v0, ADR-0003, ADR-0007

## 1. Context

Enterprise Research Agent sử dụng embedding model để chuyển document chunks và user queries thành vector representations, phục vụ semantic retrieval trên PostgreSQL với pgvector.

Hiện tại, implementation đã chuyển từ `intfloat/multilingual-e5-small` sang `gemini-embedding-2`. Tuy nhiên, quyết định này chưa có ADR được phê duyệt.

Việc lựa chọn embedding model ảnh hưởng trực tiếp đến:

- Retrieval quality trên tài liệu và câu hỏi tiếng Việt.
- Embedding dimensionality và PostgreSQL schema.
- Ingestion latency, query latency và resource consumption.
- API quota, chi phí và external service dependency.
- Việc phải re-embed corpus khi thay đổi model hoặc dimension.

Schema hiện tại sử dụng `vector(384)`. Vì vậy, việc sử dụng Gemini Embedding 2 phải xác định rõ output dimensionality, không được mặc định rằng output của model luôn tương thích với schema.

Document embeddings và query embeddings phải sử dụng cùng model, dimension và preprocessing configuration.

## 2. Options Considered

### Option A – `intfloat/multilingual-e5-small`

| Attribute | Specification |
|---|---|
| Provider | Local inference |
| Model ID | `intfloat/multilingual-e5-small` |
| Embedding dimension | 384 |
| Maximum sequence length | 512 tokens |
| Language support | 94 languages |
| License | MIT |
| Input convention | `query:` và `passage:` prefixes |

**Advantages**

- Chạy local bên trong backend worker.
- Không phụ thuộc external embedding API và API quota.
- Dimension 384 tương thích với schema `vector(384)` hiện tại.
- Model tương đối nhỏ, phù hợp với text retrieval baseline.

**Trade-offs**

- Cần cài đặt và quản lý model dependencies.
- Worker phải dành RAM và CPU cho inference.
- Input dài hơn giới hạn model có thể bị truncation.
- Phải tuân thủ prefix convention cho query và passage.

### Option B – `gemini-embedding-2`

| Attribute | Specification |
|---|---|
| Provider | Google Gemini API |
| Model ID | `gemini-embedding-2` |
| Default dimension | 3072 |
| Supported dimension range | 128–3072 |
| Recommended dimensions | 768, 1536, 3072 |
| Maximum input length | 8192 tokens |
| Supported modalities | Text, image, audio, video và PDF |

**Advantages**

- Hỗ trợ multilingual và multimodal embedding.
- Input context dài hơn multilingual-e5-small.
- Có thể tùy chỉnh output dimensionality.
- Không cần tải và host model weights trong worker.

**Trade-offs**

- Phụ thuộc Internet, API availability và quota.
- Có chi phí khi sử dụng paid tier.
- Cần quản lý API credential, rate limiting và retry.
- Dữ liệu phải được gửi tới external provider.
- Thay đổi output dimensionality có thể yêu cầu migration database và re-embedding toàn bộ corpus.

**Dimension compatibility**

Gemini Embedding 2 mặc định trả về 3072 dimensions. Google cho phép điều chỉnh bằng `output_dimensionality`.

| Output dimension | Compatibility với schema hiện tại | Nhận xét |
|---:|---|---|
| 384 | Compatible | Giữ được `vector(384)`, nhưng thấp hơn các dimension Google khuyến nghị |
| 768 | Requires migration | Dimension thấp được Google khuyến nghị |
| 1536 | Requires migration | Dimension thấp được Google khuyến nghị |
| 3072 | Requires migration | Default output của model |

Nếu giữ schema hiện tại, request phải thiết lập `output_dimensionality=384` một cách explicit. Không được dựa vào default output của Gemini.

## 3. Decision

**Proposed decision: Tiếp tục sử dụng `gemini-embedding-2` trong implementation, với output dimensionality được cấu hình tường minh.**

Đây là model đang được tích hợp và là candidate được đề xuất cho RAG Baseline. Quyết định chính thức vẫn cần team và mentor phê duyệt sau khi có evaluation.

### 3.1. Configuration

Model được chọn thông qua environment variables.

Cấu hình hiện tại được đề xuất giữ schema tương thích:

```dotenv
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_DIM=384
```

Implementation phải truyền dimension tương ứng vào Gemini API:

```python
config = types.EmbedContentConfig(
    output_dimensionality=384,
)
```

Tên biến và cách truyền config phải được đồng bộ với Settings implementation thực tế.

Không thay đổi schema `vector(384)` cho đến khi có quyết định khác được phê duyệt.

### 3.2. Evaluation

Trước khi chuyển ADR sang Accepted, nhóm cần so sánh E5 và Gemini Embedding 2 trên cùng evaluation dataset v0 và cùng corpus.

| Experiment | Embedding model | Dimension |
|---|---|---:|
| E1 | multilingual-e5-small | 384 |
| G1 | gemini-embedding-2 | 384 |
| G2 | gemini-embedding-2 | 768 |
| G3 | gemini-embedding-2 | 1536 |

Các tiêu chí đánh giá:

- Source Hit@5.
- Embedding latency.
- Retrieval latency.
- Worker resource usage.
- API quota và estimated cost.
- Vector storage requirement.

Mỗi experiment phải giữ nguyên corpus, chunking strategy, retrieval method và evaluation questions để kết quả có thể so sánh.

### 3.3. Migration Rule

Mỗi embedding vector phải tương ứng với model và dimensionality đã dùng để sinh ra nó.

Khi thay đổi model hoặc dimensionality:

1. Tạo migration phù hợp với vector schema mới nếu dimension thay đổi.
2. Re-embed toàn bộ corpus.
3. Không trộn document vectors được sinh từ model/dimension cũ với query vectors được sinh từ model/dimension mới.
4. Chỉ sử dụng corpus mới sau khi quá trình re-embedding hoàn tất và được kiểm tra.

## 4. Consequences

**Benefits**

- Tiếp tục tận dụng Gemini Embedding 2 đã được tích hợp.
- Có khả năng mở rộng sang multimodal retrieval.
- Có thể kiểm soát storage thông qua output dimensionality.
- Không tự ý thay đổi database schema trước khi có benchmark và phê duyệt.

**Trade-offs**

- Phụ thuộc Google Gemini API và quota.
- Phát sinh chi phí khi sử dụng paid tier.
- Phải quản lý external API failures.
- Dimension 384 cần được đánh giá thực nghiệm vì thấp hơn các kích thước được Google khuyến nghị.
- Chuyển sang dimension khác yêu cầu migration và re-embedding corpus.

**Decision Status:** Proposed — pending comparative evaluation and team/mentor approval.

## References

1. [Multilingual-E5-small Model Card](https://huggingface.co/intfloat/multilingual-e5-small)
2. [Gemini Embedding 2 – Google DeepMind](https://deepmind.google/models/gemini/embedding/)
3. [Gemini Embeddings Documentation](https://ai.google.dev/gemini-api/docs/embeddings)
4. [Gemini API Pricing](https://ai.google.dev/gemini-api/docs/pricing)
5. [pgvector Documentation](https://github.com/pgvector/pgvector)
