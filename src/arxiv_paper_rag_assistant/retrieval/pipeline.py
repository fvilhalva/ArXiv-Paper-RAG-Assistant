"""Query embedding -> vector search -> prompt assembly -> cited answer generation.

See DESIGN.md section 4 (Retrieval + Generation) and FR04-FR05, FR08.
"""


def answer_question(question: str) -> str:
    raise NotImplementedError
