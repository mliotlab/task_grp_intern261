# ADR-0009: Use PostgreSQL with pgvector for Vector Storage

- **Status:** Proposed — selected by the ERA team; pending team and mentor review
- **Date:** 2026-11-28
- **Parent:** ERA-19 — Discovery & Design
- **Task:** S2-08 — Queue & Vector Store ADRs
- **Requirements:** FR-02, FR-05, NFR-04, NFR-08
- **Deciders:** Enterprise Research Agent (ERA) team

## 1. Context

The Enterprise Research Agent must persist document chunks and their embeddings so that the Research Pipeline can retrieve evidence relevant to a user's question. Under **FR-02**, uploaded documents are parsed and split into chunks. Under **FR-05**, the system retrieves relevant chunks for each research sub-question and uses them to produce a structured report with citations to the source document and page or section.

A chunk is not only a vector. It also has relational information required by the application, including its document, collection, owner, text, ordinal position, page, and section. Retrieval must respect these relationships and access constraints. In particular, only chunks belonging to the requested collection and owner, and associated with documents in the `ready` state, may be returned.

The current ERA data model already uses PostgreSQL for users, collections, documents, chunks, and research jobs. The baseline stores each chunk's embedding in the `chunks.embedding` column using pgvector. The current application configuration uses 384-dimensional embeddings; the embedding provider and database column must use the same dimension. The embedding-model choice itself is outside the scope of this ADR.

The system must also satisfy **NFR-08**: PostgreSQL with pgvector is one of the services started through Docker Compose, and CI builds the image used by the deployment.

The vector store is responsible for storing and searching embeddings. It is not the storage location for the original uploaded PDF, DOCX, or Markdown binaries. Original file storage is a separate concern and is outside the scope of this decision.

### Decision drivers

- Keep chunk text, embeddings, source metadata, and relational ownership information consistent.
- Support dense nearest-neighbor retrieval with metadata and authorization filters.
- Preserve citation metadata required by FR-05.
- Fit the existing PostgreSQL, SQLAlchemy, migration, and Docker Compose architecture.
- Avoid additional infrastructure unless measured scale or performance requires it.
- Allow retrieval indexing to evolve based on evaluation rather than introducing premature complexity.

## 2. Options Considered

### Option A — PostgreSQL + pgvector (selected)

PostgreSQL stores the application's relational entities and chunk records. pgvector adds vector data types, distance operators, and optional approximate-nearest-neighbor indexes to PostgreSQL.

**Advantages**

- Stores embeddings alongside chunk text and relational metadata in the same database.
- SQL joins, transactions, foreign keys, and filters can be used in the same query path as vector distance ordering.
- Retrieval can enforce `collection_id`, `owner_id`, and `Document.status = READY` constraints while selecting relevant chunks.
- pgvector supports exact nearest-neighbor search and approximate indexes such as HNSW and IVFFlat.
- Exact search provides a useful reference result for evaluation; approximate indexes can be introduced later if measured latency or corpus size requires them.
- Reuses the PostgreSQL service, SQLAlchemy models, migrations, and operational setup already present in ERA.
- Does not require a second database service in Docker Compose.

**Limitations**

- PostgreSQL handles both transactional application queries and vector-search workloads. As data volume and concurrency grow, those workloads may compete for CPU, memory, I/O, and connection capacity.
- Approximate indexes require tuning and may trade recall for latency. Query filters and index behavior must be evaluated on the actual corpus.
- A dedicated vector database may provide more suitable independent scaling or specialized vector-search operations at a larger scale.
- The team must manage PostgreSQL backups, extension compatibility, migrations, and index maintenance.

### Option B — Qdrant

Qdrant is a vector-native database that stores vectors as points in collections and supports payload metadata and filtering.

**Advantages**

- Provides a purpose-built vector-search data model and API.
- Supports vector collections, similarity metrics, and metadata/payload filters.
- Can be deployed independently from PostgreSQL, allowing vector-search resources to be scaled separately.
- Is a credible alternative if vector-search throughput, corpus size, or independent scaling becomes a primary requirement.

**Limitations**

- Adds another service, client library, deployment configuration, monitoring target, and backup/restore procedure.
- PostgreSQL would still need to store users, collections, documents, ownership, and document lifecycle state.
- The application would need to coordinate PostgreSQL records with Qdrant points during ingestion, re-ingestion, deletion, and failure recovery.
- Authorization and document-readiness filtering would need to be represented consistently in Qdrant payloads or enforced through a coordinated query path.
- The extra storage and synchronization complexity is not currently justified by the project's expected scale.

### Option C — Chroma

Chroma provides a developer-oriented storage and retrieval API for embeddings, documents, metadata, and vector queries. It supports local/self-hosted and cloud deployment modes.

**Advantages**

- Offers a straightforward API for storing embeddings, document content, and metadata.
- Supports dense and sparse vector retrieval, metadata filtering, and hybrid retrieval features.
- Is convenient for rapid prototyping and standalone retrieval experiments.

**Limitations**

- PostgreSQL would still be required for the application's relational entities, authorization rules, and document lifecycle state.
- Using Chroma as a separate store would require synchronization between Chroma records and PostgreSQL records.
- It introduces a second persistence model and another service/client path into an application already centered on PostgreSQL and SQLAlchemy.
- Its developer convenience does not currently outweigh the additional consistency and operational responsibilities for this project.

## 3. Decision

The ERA system will use **PostgreSQL with the pgvector extension as its vector store** for the current implementation and end-to-end baseline.

1. Store each chunk's text, embedding, document/collection identifiers, and citation metadata (including page and section where available) in PostgreSQL. The current embedding dimension is 384; this value must remain consistent between the embedding provider, application configuration, database column, and query vectors. Selecting or changing the embedding model/dimension is outside this ADR.
2. Use SQLAlchemy with pgvector distance operators for dense retrieval. The baseline uses cosine distance and orders results by ascending distance, with a configured Top-K limit.
3. Every dense-retrieval query must retain the application authorization and lifecycle predicates. At minimum, filter by the requested collection, document owner, collection owner, and `Document.status = READY` before returning evidence to the research pipeline.
4. Keep PostgreSQL as the source of truth for relational metadata and vector records. Use database constraints, foreign keys, and transactions where appropriate to keep chunk records consistent with their parent documents and collections.
5. Start with **exact nearest-neighbor search**. Do not introduce HNSW or IVFFlat solely because they are available. Add an approximate index only after measuring corpus size, query latency, recall, and the effect of authorization filters on the actual evaluation dataset. Record the chosen index type and parameters when it is introduced.
6. Keep hybrid retrieval responsibilities explicit. pgvector supplies dense-retrieval candidates. The current BM25 stage is implemented in the application using `rank-bm25`; Reciprocal Rank Fusion combines the ranked lists. This ADR selects the vector store and does not claim that pgvector itself implements the application's BM25 or RRF logic.
7. Use the existing PostgreSQL service in Docker Compose with the pgvector extension installed and enabled through the database setup/migration process. Persist the database using a Docker-managed named volume for local development, and include the PostgreSQL/pgvector image in CI image builds as required by NFR-08.
8. Treat the Docker named volume as persistence across container recreation, not as an independent backup. Use database-aware PostgreSQL backups and test restoration. Uploaded source binaries remain in the file-storage layer and are not moved into pgvector by this decision.

## 4. Consequences

### Positive

- One database contains application entities, chunk text, embeddings, and citation metadata.
- Retrieval can combine vector ordering with SQL joins and ownership/readiness filters.
- The implementation reuses the current PostgreSQL, SQLAlchemy, migration, and Docker Compose infrastructure.
- Exact search provides a reproducible baseline against which future approximate indexes can be evaluated.
- The architecture avoids introducing another database service before the workload demonstrates a need for one.
- Original-file storage can evolve independently without changing the decision to store chunk embeddings in PostgreSQL.

### Negative / risks

- Vector retrieval and transactional workloads share PostgreSQL resources and may compete as the corpus and concurrency grow.
- Exact nearest-neighbor search may become too slow for a substantially larger corpus or heavier concurrent workload.
- HNSW and IVFFlat require configuration and evaluation; approximate search can return different results from exact search.
- If a dedicated vector database is adopted later, vectors and metadata must be migrated and cross-store consistency must be designed.
- A Docker named volume can still be lost through accidental deletion, disk failure, or host loss; separate backups and restore tests remain necessary.
- The vector column dimension is coupled to the embedding configuration. Changing the embedding model or dimension may require schema changes and re-embedding existing chunks.

### Operational responsibilities

- Ensure the pgvector extension is available in the PostgreSQL image and enabled in the database before vector columns and queries are used.
- Keep embedding dimensions consistent between document embeddings and query embeddings.
- Monitor query latency, database resource usage, corpus size, and recall/quality metrics before adding approximate indexes.
- Back up PostgreSQL with database-aware tooling and verify restoration rather than relying only on the Docker volume.
- Preserve stable document and chunk identifiers so embeddings can be rebuilt from source documents if required.

## 5. Revisit This Decision When

Reconsider a dedicated vector database if measured retrieval latency, corpus size, concurrent query load, memory requirements, or independent scaling needs exceed what the PostgreSQL deployment can support. Any migration should compare retrieval quality, authorization-filter correctness, operational cost, backup/restore behavior, and synchronization complexity against the PostgreSQL + pgvector baseline.

## 6. References

1. [pgvector documentation](https://github.com/pgvector/pgvector) — vector types, distance operators, exact search, HNSW, IVFFlat, and hybrid-search examples.
2. [PostgreSQL documentation — Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html) — atomic database updates and transaction behavior.
3. [Qdrant documentation](https://qdrant.tech/documentation/) — collections, payload metadata, filtering, indexing, and vector search.
4. [Chroma documentation — Introduction](https://docs.trychroma.com/docs/overview/introduction) — embedding/document storage, vector search, and metadata filtering.
