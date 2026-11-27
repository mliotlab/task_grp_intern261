# Evaluation datasets

- **Corpus:** 50–100 public documents on one topic (open-source technical docs, public annual
  reports, arXiv papers), chosen by the team and approved by the mentor. Record each document's
  source URL and license in `corpus_manifest.csv` — do not commit documents whose license forbids it.
- **Questions:** [Dataset v0](v0/questions.jsonl) contains 15 research questions with reference
  key points and source documents. The final evaluation targets 30 questions. Freeze a dataset
  version once a report has been published on it.

## Corpus v0

Download the 10 PDFs below, keep their filenames unchanged, and place them in
`eval/datasets/v0/corpus/` relative to `enterprise-research-agent/`. The folder is ignored by Git.
[Team Drive corpus](https://drive.google.com/drive/folders/1W-kBFmMSytkPP-dhzDCH3N6dfCZoLVKP)

- `NIST-SP-800-122.pdf`
- `NIST-SP-800-190.pdf`
- `NIST-SP-800-204.pdf`
- `NIST-SP-800-204A.pdf`
- `NIST-SP-800-207.pdf`
- `NIST-SP-800-207A.pdf`
- `NIST-SP-800-218.pdf`
- `NIST-SP-800-218A.pdf`
- `NIST-SP-800-30r1.pdf`
- `NIST-SP-800-61r3.pdf`

The `source_documents` fields in the dataset use these exact filenames.
