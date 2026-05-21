FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/src ./src
COPY app/frontend ./frontend
COPY app/LLM_PROMPT.md ./LLM_PROMPT.md
COPY noshow.db ./noshow.db

ENV DATABASE_URL=sqlite:////app/noshow.db
EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", "8000"]
