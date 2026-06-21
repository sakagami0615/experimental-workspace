FROM python:3.12-slim
WORKDIR /app
RUN pip install uv --no-cache-dir
COPY pyproject.toml .
RUN uv pip install --system --no-cache .
COPY src/ ./src/
COPY data/ ./data/
