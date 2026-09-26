"""LangGraph orchestrator: classify intent, then route to ingestion, retrieval, or a clarification request.

MVP graph per DESIGN.md section 7: two nodes (classify intent -> ingest OR answer). See FR06.
"""


def build_graph():
    raise NotImplementedError
