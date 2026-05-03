import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.solver import LabSolver


class MockClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def chat(self, system_prompt, user_prompt):
        self.calls.append((system_prompt, user_prompt))
        return self.responses.get(user_prompt, "default answer")


@pytest.fixture
def mock_client():
    return MockClient()


@pytest.fixture
def output_dir():
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)


class TestLabSolverSolve:
    def test_splits_on_enviar_markers(self, mock_client, output_dir):
        content = (
            "Question 1 text here.\nEnviar \"Posicao.java\"\n\n"
            "Question 2 text here.\nEnviar \"Celular.java\""
        )
        lab_file = _write_lab_file(content)
        mock_client.responses = {
            "Question 1 text here.\nEnviar \"Posicao.java\"": "class Posicao {}",
            "Question 2 text here.\nEnviar \"Celular.java\"": "class Celular {}",
        }

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert result["solved"] == ["Posicao.java", "Celular.java"]
        assert result["failed"] == []
        assert (output_dir / "Posicao.java").read_text() == "class Posicao {}\n"
        assert (output_dir / "Celular.java").read_text() == "class Celular {}\n"

    def test_skips_empty_questions(self, mock_client, output_dir):
        content = (
            "Enviar \"Posicao.java\"\n\n"
            "Question 1 text.\nEnviar \"Celular.java\""
        )
        lab_file = _write_lab_file(content)
        mock_client.responses = {
            "Question 1 text.\nEnviar \"Celular.java\"": "class Celular {}",
        }

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert result["solved"] == ["Celular.java"]
        assert not (output_dir / "Posicao.java").exists()

    def test_fallback_when_no_markers(self, mock_client, output_dir):
        content = "Some lab content without file markers."
        lab_file = _write_lab_file(content)
        mock_client.responses = {content: "solution code"}

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert result["solved"] == ["solution.txt"]
        assert (output_dir / "solution.txt").read_text() == "solution code\n"

    def test_empty_file_returns_empty(self, mock_client, output_dir):
        lab_file = _write_lab_file("")

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert result == {"solved": [], "failed": []}

    def test_raises_file_not_found(self, mock_client, output_dir):
        solver = LabSolver(mock_client, "test-model", output_dir)
        with pytest.raises(FileNotFoundError):
            solver.solve(Path("/nonexistent/lab.txt"))

    def test_records_failure_on_api_error(self, mock_client, output_dir):
        content = "Question 1.\nEnviar \"Fail.java\"\n\nQuestion 2.\nEnviar \"Ok.java\""
        lab_file = _write_lab_file(content)
        mock_client.responses = {
            "Question 2.\nEnviar \"Ok.java\"": "class Ok {}",
        }

        def fail_on_first(system_prompt, user_prompt):
            if "Fail.java" in user_prompt:
                raise RuntimeError("API error")
            return "class Ok {}"

        mock_client.chat = fail_on_first

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert result["solved"] == ["Ok.java"]
        assert result["failed"] == ["Fail.java"]

    def test_strips_markdown_fences(self, mock_client, output_dir):
        content = "Question.\nEnviar \"Code.java\""
        lab_file = _write_lab_file(content)
        mock_client.responses = {
            "Question.\nEnviar \"Code.java\"": "```java\npublic class Code {}\n```",
        }

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert (output_dir / "Code.java").read_text() == "public class Code {}\n"

    def test_creates_output_dir(self, mock_client, output_dir):
        nested = output_dir / "deeply" / "nested"
        content = "Q.\nEnviar \"Test.java\""
        lab_file = _write_lab_file(content)
        mock_client.responses = {content: "code"}

        solver = LabSolver(mock_client, "test-model", nested)
        solver.solve(lab_file)

        assert (nested / "Test.java").exists()

    def test_full_lab_content_integration(self, mock_client, output_dir):
        content = (
            "Nota:0.0 Tempo:1d 16h 41m Sair\n"
            "Laboratório 7: Encapsulamento\n"
            "Objetivo\n"
            "Implementação de classes...\n"
            "Enviar \"Posicao.java\"\n"
            "40 160\n"
            "0.0 / 2.0\n"
            "Interface Localizavel\n"
            "Enviar \"Localizavel.java\"\n"
            "40 160\n"
            "0.0 / 2.0\n"
            "Classe Celular\n"
            "Enviar \"Celular.java\"\n"
        )
        lab_file = _write_lab_file(content)
        mock_client.responses = {
            "Classe Celular\n"
            "Enviar \"Celular.java\"": "class Celular {}",
        }

        solver = LabSolver(mock_client, "test-model", output_dir)
        result = solver.solve(lab_file)

        assert len(result["solved"]) >= 2


def _write_lab_file(content: str) -> Path:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                      encoding="utf-8") as f:
        f.write(content)
        return Path(f.name)
