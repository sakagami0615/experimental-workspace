from pathlib import Path
import tomllib


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_docker_files_exist_for_document_masking():
    assert (PROJECT_ROOT / "Dockerfile").is_file()
    assert (PROJECT_ROOT / "docker-compose.yml").is_file()


def test_dockerfile_installs_project_and_spacy_model():
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FROM python:3.14.7" in dockerfile
    assert "slim" not in dockerfile
    assert 'pip install -e ".[dev]"' in dockerfile
    assert "python -m spacy download ja_core_news_sm" in dockerfile
    assert '"-m", "document_masking"' in dockerfile


def test_compose_builds_local_project_directory():
    compose = (PROJECT_ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "build: ." in compose
    assert ".:/app" in compose
    assert "python -m document_masking" in compose


def test_project_requires_python_314_or_newer():
    pyproject = tomllib.loads((PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["requires-python"] == ">=3.14"


def test_documented_output_directory_is_output():
    docs = [
        (PROJECT_ROOT / "README.md").read_text(encoding="utf-8"),
        (PROJECT_ROOT / "docs" / "specs" / "design.md").read_text(encoding="utf-8"),
    ]

    for content in docs:
        assert "out/" not in content
        assert "output/" in content
