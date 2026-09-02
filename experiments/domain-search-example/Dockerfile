FROM ghcr.io/astral-sh/uv:python3.14-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

COPY pyproject.toml uv.lock* ./
COPY src ./src

RUN uv sync --frozen --dev || uv sync --dev

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
