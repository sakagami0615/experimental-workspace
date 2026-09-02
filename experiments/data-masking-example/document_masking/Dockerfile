FROM python:3.14.7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY src ./src
COPY sample_data ./sample_data
COPY tests ./tests

RUN python -m pip install --upgrade pip \
    && pip install -e ".[dev]" \
    && python -m spacy download ja_core_news_sm

CMD ["python", "-m", "document_masking", "--help"]
