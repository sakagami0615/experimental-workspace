from fastapi import FastAPI
from pydantic import BaseModel, Field

from pipeline import AnswerResponse, answer_question
from settings import load_settings

app = FastAPI(title="Domain Search Service")


class AnswerRequest(BaseModel):
    """Request body for answering a question."""

    question: str = Field(min_length=1)


@app.get("/health")
async def health() -> dict[str, str]:
    """Return service health."""
    return {"status": "ok"}


@app.post("/answer")
async def answer(request: AnswerRequest) -> AnswerResponse:
    """Answer a question using configured web sources."""
    return await answer_question(request.question, load_settings())
