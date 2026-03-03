"""
Tests for bel_ai_jar.llm_integration module
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from bel_ai_jar.llm_integration import (
    AIModel,
    GeminiClient,
    LocalLlamaClient,
    OpenAIClient,
    _resolve_api_key,
    get_llm_client,
    generate_questions_with_llm,
)


SAMPLE_CONFIG = {
    "total_questions": 2,
    "answer_options": 4,
    "additional_prompt": "",
}

SAMPLE_QUESTIONS_JSON = json.dumps(
    [
        {
            "question": "What does add() do?",
            "options": ["Adds", "Subtracts", "Multiplies", "Divides"],
            "correct_answer": "Adds",
        },
        {
            "question": "What is the return type?",
            "options": ["int", "str", "list", "None"],
            "correct_answer": "int",
        },
    ]
)


class TestResolveApiKey:
    def test_explicit_key_takes_priority(self, monkeypatch):
        monkeypatch.setenv("BEL_AI_JAR_LLM_API_KEY", "generic-key")
        monkeypatch.setenv("MISTRAL_API_KEY", "legacy-key")
        assert _resolve_api_key(AIModel.MISTRAL, "explicit-key") == "explicit-key"

    def test_generic_env_var_takes_priority_over_legacy(self, monkeypatch):
        monkeypatch.setenv("BEL_AI_JAR_LLM_API_KEY", "generic-key")
        monkeypatch.setenv("MISTRAL_API_KEY", "legacy-key")
        assert _resolve_api_key(AIModel.MISTRAL) == "generic-key"

    def test_mistral_legacy_fallback(self, monkeypatch):
        monkeypatch.delenv("BEL_AI_JAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("MISTRAL_API_KEY", "mistral-key")
        assert _resolve_api_key(AIModel.MISTRAL) == "mistral-key"

    def test_openai_legacy_fallback(self, monkeypatch):
        monkeypatch.delenv("BEL_AI_JAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")
        assert _resolve_api_key(AIModel.OPENAI_GPT35) == "openai-key"

    def test_gemini_legacy_fallback(self, monkeypatch):
        monkeypatch.delenv("BEL_AI_JAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
        assert _resolve_api_key(AIModel.GEMINI) == "google-key"

    def test_returns_none_when_no_key(self, monkeypatch):
        monkeypatch.delenv("BEL_AI_JAR_LLM_API_KEY", raising=False)
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        assert _resolve_api_key(AIModel.MISTRAL) is None


class TestGetLLMClient:
    def test_mistral_returns_openai_client(self):
        client = get_llm_client(AIModel.MISTRAL, api_key="key")
        assert isinstance(client, OpenAIClient)

    def test_openai_gpt35_returns_openai_client(self):
        client = get_llm_client(AIModel.OPENAI_GPT35, api_key="key")
        assert isinstance(client, OpenAIClient)

    def test_gemini_returns_gemini_client(self):
        client = get_llm_client(AIModel.GEMINI, api_key="key")
        assert isinstance(client, GeminiClient)

    def test_local_llama_returns_local_client(self):
        client = get_llm_client(AIModel.LOCAL_LLAMA)
        assert isinstance(client, LocalLlamaClient)

    def test_mistral_reads_env_var(self, monkeypatch):
        monkeypatch.delenv("BEL_AI_JAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("MISTRAL_API_KEY", "env-key")
        client = get_llm_client(AIModel.MISTRAL)
        assert client.api_key == "env-key"

    def test_openai_reads_env_var(self, monkeypatch):
        monkeypatch.delenv("BEL_AI_JAR_LLM_API_KEY", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        client = get_llm_client(AIModel.OPENAI_GPT35)
        assert client.api_key == "env-key"

    def test_generic_key_used_for_any_model(self, monkeypatch):
        monkeypatch.setenv("BEL_AI_JAR_LLM_API_KEY", "generic-key")
        client = get_llm_client(AIModel.GEMINI)
        assert client.api_key == "generic-key"


class TestOpenAIClientGenerateQuestions:
    def _make_response(self, content: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": content}}]
        }
        return mock_resp

    def test_parses_valid_json_response(self):
        client = OpenAIClient(AIModel.MISTRAL, api_key="key")
        with patch("requests.post", return_value=self._make_response(SAMPLE_QUESTIONS_JSON)):
            questions = client.generate_questions("diff content", SAMPLE_CONFIG)
        assert len(questions) == 2
        assert questions[0]["question"] == "What does add() do?"

    def test_strips_markdown_fences(self):
        fenced = f"```json\n{SAMPLE_QUESTIONS_JSON}\n```"
        client = OpenAIClient(AIModel.MISTRAL, api_key="key")
        with patch("requests.post", return_value=self._make_response(fenced)):
            questions = client.generate_questions("diff", SAMPLE_CONFIG)
        assert len(questions) == 2

    def test_falls_back_on_http_error(self):
        client = OpenAIClient(AIModel.MISTRAL, api_key="key")
        with patch("requests.post", side_effect=Exception("connection refused")):
            questions = client.generate_questions("def foo(): pass", SAMPLE_CONFIG)
        # Fallback returns a list (possibly empty)
        assert isinstance(questions, list)

    def test_falls_back_on_invalid_json(self):
        client = OpenAIClient(AIModel.MISTRAL, api_key="key")
        with patch("requests.post", return_value=self._make_response("not json at all")):
            questions = client.generate_questions("def bar(): pass", SAMPLE_CONFIG)
        assert isinstance(questions, list)


class TestGeminiClient:
    def _make_response(self, content: str) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {
            "candidates": [{"content": {"parts": [{"text": content}]}}]
        }
        return mock_resp

    def test_parses_valid_json_response(self):
        client = GeminiClient(AIModel.GEMINI, api_key="key")
        with patch("requests.post", return_value=self._make_response(SAMPLE_QUESTIONS_JSON)):
            questions = client.generate_questions("diff content", SAMPLE_CONFIG)
        assert len(questions) == 2

    def test_strips_markdown_fences(self):
        fenced = f"```json\n{SAMPLE_QUESTIONS_JSON}\n```"
        client = GeminiClient(AIModel.GEMINI, api_key="key")
        with patch("requests.post", return_value=self._make_response(fenced)):
            questions = client.generate_questions("diff", SAMPLE_CONFIG)
        assert len(questions) == 2

    def test_falls_back_when_no_api_key(self):
        client = GeminiClient(AIModel.GEMINI, api_key=None)
        questions = client.generate_questions("def foo(): pass", SAMPLE_CONFIG)
        assert isinstance(questions, list)

    def test_falls_back_on_http_error(self):
        client = GeminiClient(AIModel.GEMINI, api_key="key")
        with patch("requests.post", side_effect=Exception("connection refused")):
            questions = client.generate_questions("def foo(): pass", SAMPLE_CONFIG)
        assert isinstance(questions, list)


class TestLocalLlamaClient:
    def test_uses_configured_api_url(self):
        client = LocalLlamaClient(AIModel.LOCAL_LLAMA, api_url="http://localhost:9090/completion")
        assert client.api_url == "http://localhost:9090/completion"

    def test_generate_questions_parses_response(self):
        client = LocalLlamaClient(AIModel.LOCAL_LLAMA)
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"content": SAMPLE_QUESTIONS_JSON}
        with patch("requests.post", return_value=mock_resp):
            questions = client.generate_questions("diff", SAMPLE_CONFIG)
        assert len(questions) == 2

    def test_falls_back_on_error(self):
        client = LocalLlamaClient(AIModel.LOCAL_LLAMA)
        with patch("requests.post", side_effect=Exception("timeout")):
            questions = client.generate_questions("def baz(): pass", SAMPLE_CONFIG)
        assert isinstance(questions, list)


class TestGenerateQuestionsWithLLM:
    def test_returns_questions_list(self):
        with patch(
            "bel_ai_jar.llm_integration.get_llm_client"
        ) as mock_factory:
            mock_client = MagicMock()
            mock_client.generate_questions.return_value = [{"question": "Q?"}]
            mock_factory.return_value = mock_client

            result = generate_questions_with_llm("diff", SAMPLE_CONFIG, AIModel.MISTRAL, "key")
        assert result == [{"question": "Q?"}]

    def test_falls_back_on_exception(self):
        with patch(
            "bel_ai_jar.llm_integration.get_llm_client",
            side_effect=ValueError("bad model"),
        ):
            result = generate_questions_with_llm("def f(): pass", SAMPLE_CONFIG)
        assert isinstance(result, list)
