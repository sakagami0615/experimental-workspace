from fastapi.testclient import TestClient

from api import app


def test_answer_endpoint_rejects_empty_question():
    client = TestClient(app)

    response = client.post("/answer", json={"question": ""})

    assert response.status_code == 422
