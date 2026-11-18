import { useParams } from "react-router-dom";

export default function ResearchPage() {
  const { jobId } = useParams();
  // TODO(FR-03..06):
  //  - form: question + collection → POST /v1/research → navigate to /research/:jobId
  //  - poll GET /v1/research/:jobId every 2 s (or SSE) and show step progress
  //  - render report_markdown; clicking [n] opens the source chunk (GET /v1/chunks/:id)
  return (
    <section className="card">
      <h1>Research</h1>
      {jobId ? <p>Job {jobId}</p> : <p className="muted">Ask a research question.</p>}
    </section>
  );
}
