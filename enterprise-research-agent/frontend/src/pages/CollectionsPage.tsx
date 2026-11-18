export default function CollectionsPage() {
  // TODO(FR-02, FR-06): list collections (GET /v1/collections), create one, upload documents
  // (POST /v1/collections/{id}/documents) and show per-document status:
  // queued → processing → ready | failed (poll until ready).
  return (
    <section className="card">
      <h1>Collections</h1>
      <p className="muted">Document collections will appear here.</p>
    </section>
  );
}
