FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py .
COPY schemas/ schemas/
COPY data/ data/
COPY rag/ rag/
COPY llm/ llm/
COPY template/ template/
COPY audit/ audit/
COPY service/ service/
COPY api/ api/
COPY app.py .

# Build indices on build (corpus is in data/)
RUN python -c "from rag.ingest import ingest_corpus; ingest_corpus(); print('Ingestion OK')"

ENV OPENAI_API_KEY=""
EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
