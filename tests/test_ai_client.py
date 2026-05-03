from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.ai_client import AIClient, OpenAIClient, OllamaClient, _is_network_error


class TestIsNetworkError:
    def test_timeout_is_network(self):
        assert _is_network_error(Exception("The read operation timed out"))
        assert _is_network_error(Exception("Connection timed out"))

    def test_refused_is_network(self):
        assert _is_network_error(Exception("Connection refused"))

    def test_dns_is_network(self):
        assert _is_network_error(Exception("DNS resolution failed"))

    def test_client_error_is_not_network(self):
        assert not _is_network_error(Exception("Invalid API key"))
        assert not _is_network_error(Exception("Bad request"))


class TestOpenAIClient:
    def test_uses_opencode_go_by_default(self):
        client = OpenAIClient(model="test-model", api_key="sk-test")
        assert client.base_url == "https://opencode.ai/zen/go/v1"
        assert client.model == "test-model"

    def test_uses_custom_base_url(self):
        client = OpenAIClient(model="test", base_url="https://custom.api/v1",
                              api_key="sk-test")
        assert client.base_url == "https://custom.api/v1"

    def test_chat_success(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello world"}}]
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            client = OpenAIClient(model="test", api_key="sk-test")
            result = client.chat("system", "user")
            assert result == "Hello world"
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["model"] == "test"
            assert call_args.kwargs["json"]["messages"][0]["content"] == "system"
            assert call_args.kwargs["headers"]["Authorization"] == "Bearer sk-test"

    def test_chat_retries_on_network_error(self):
        fail_response = MagicMock(spec=httpx.Response)
        fail_response.raise_for_status.side_effect = httpx.TimeoutException(
            "Connection timed out"
        )

        success_response = MagicMock(spec=httpx.Response)
        success_response.raise_for_status = MagicMock()
        success_response.json.return_value = {
            "choices": [{"message": {"content": "retry worked"}}]
        }

        with patch("httpx.post",
                   side_effect=[fail_response, success_response]) as mock_post:
            with patch("time.sleep"):
                client = OpenAIClient(model="test", api_key="sk-test")
                result = client.chat("system", "user")
                assert result == "retry worked"
                assert mock_post.call_count == 2

    def test_chat_no_retry_on_client_error(self):
        fail_response = MagicMock(spec=httpx.Response)
        fail_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad request", request=MagicMock(), response=MagicMock(status_code=400)
        )

        with patch("httpx.post", return_value=fail_response):
            client = OpenAIClient(model="test", api_key="sk-test")
            with pytest.raises(RuntimeError, match="AI API call failed"):
                client.chat("system", "user")

    def test_reads_api_key_from_env(self):
        with patch.dict("os.environ", {"OPENCODE_API_KEY": "env-key"}):
            client = OpenAIClient(model="test")
            assert client.api_key == "env-key"

    def test_openai_env_fallback(self):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "openai-key"},
                        clear=True):
            client = OpenAIClient(model="test")
            assert client.api_key == "openai-key"


class TestOllamaClient:
    def test_uses_localhost_by_default(self):
        client = OllamaClient(model="llama3")
        assert client.base_url == "http://localhost:11434"

    def test_chat_success(self):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "Ollama says hi"}
        }

        with patch("httpx.post", return_value=mock_response) as mock_post:
            client = OllamaClient(model="llama3")
            result = client.chat("system", "user")
            assert result == "Ollama says hi"
            call_args = mock_post.call_args
            assert call_args.kwargs["json"]["model"] == "llama3"
            assert call_args.kwargs["json"]["stream"] is False

    def test_chat_retries_on_network_error(self):
        fail_response = MagicMock(spec=httpx.Response)
        fail_response.raise_for_status.side_effect = httpx.TimeoutException(
            "Connection timed out"
        )

        success_response = MagicMock(spec=httpx.Response)
        success_response.raise_for_status = MagicMock()
        success_response.json.return_value = {
            "message": {"content": "retry worked"}
        }

        with patch("httpx.post",
                   side_effect=[fail_response, success_response]):
            with patch("time.sleep"):
                client = OllamaClient(model="llama3")
                result = client.chat("system", "user")
                assert result == "retry worked"

    def test_custom_base_url(self):
        client = OllamaClient(model="test",
                              base_url="http://192.168.1.100:11434")
        assert client.base_url == "http://192.168.1.100:11434"
