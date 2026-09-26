FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY src/ src/

RUN pip install --no-cache-dir uv && uv pip install --system .

CMD ["python", "-m", "arxiv_paper_rag_assistant.bot.discord_bot"]
