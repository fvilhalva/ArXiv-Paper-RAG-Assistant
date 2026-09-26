"""arXiv fetch -> PDF text extraction -> section-aware chunking -> vector store write.

See DESIGN.md section 4 (Ingestion Pipeline) and FR01-FR03.
"""


def ingest_paper(arxiv_id: str) -> None:
    raise NotImplementedError
