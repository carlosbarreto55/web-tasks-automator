import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.notifications.telegram import TelegramNotifier


class TestTelegramNotifierInit:
    def test_builds_api_url(self):
        notifier = TelegramNotifier(bot_token="abc123", chat_id="456")
        assert notifier.bot_token == "abc123"
        assert notifier.chat_id == "456"
        assert notifier._base_url == "https://api.telegram.org/botabc123"

    def test_default_timeout(self):
        notifier = TelegramNotifier(bot_token="x", chat_id="y")
        assert notifier.timeout == 30


class TestSendMessage:
    def test_success(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {"ok": True}

        with patch("httpx.post", return_value=mock_resp) as mock_post:
            notifier = TelegramNotifier(bot_token="abc", chat_id="123")
            result = notifier.send_message("Hello")
            assert result is True

            call_kwargs = mock_post.call_args.kwargs
            assert call_kwargs["json"]["chat_id"] == "123"
            assert call_kwargs["json"]["text"] == "Hello"
            assert call_kwargs["json"]["parse_mode"] == "HTML"

    def test_api_error(self):
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.json.return_value = {"ok": False, "description": "chat not found"}

        with patch("httpx.post", return_value=mock_resp):
            notifier = TelegramNotifier(bot_token="abc", chat_id="123")
            result = notifier.send_message("Hello")
            assert result is False

    def test_retries_on_network_error(self):
        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.json.side_effect = httpx.TimeoutException("Connection timed out")

        success_resp = MagicMock(spec=httpx.Response)
        success_resp.json.return_value = {"ok": True}

        with patch("httpx.post", side_effect=[fail_resp, success_resp]) as mock_post:
            with patch("time.sleep"):
                notifier = TelegramNotifier(bot_token="abc", chat_id="123")
                result = notifier.send_message("Hello")
                assert result is True
                assert mock_post.call_count == 2

    def test_no_retry_on_non_network_error(self):
        fail_resp = MagicMock(spec=httpx.Response)
        fail_resp.json.side_effect = httpx.HTTPStatusError(
            "Bad request", request=MagicMock(), response=MagicMock(status_code=400)
        )

        with patch("httpx.post", return_value=fail_resp) as mock_post:
            notifier = TelegramNotifier(bot_token="abc", chat_id="123")
            result = notifier.send_message("Hello")
            assert result is False
            assert mock_post.call_count == 1


class TestSendDocument:
    def test_success(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            tmp.write(b"fake zip content")
            tmp.flush()
            tmp_path = Path(tmp.name)

            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.json.return_value = {"ok": True}

            with patch("httpx.post", return_value=mock_resp) as mock_post:
                notifier = TelegramNotifier(bot_token="abc", chat_id="123")
                result = notifier.send_document(tmp_path)
                assert result is True

                call_kwargs = mock_post.call_args.kwargs
                assert call_kwargs["data"]["chat_id"] == "123"

    def test_with_caption(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            tmp.write(b"fake zip content")
            tmp.flush()
            tmp_path = Path(tmp.name)

            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.json.return_value = {"ok": True}

            with patch("httpx.post", return_value=mock_resp) as mock_post:
                notifier = TelegramNotifier(bot_token="abc", chat_id="123")
                result = notifier.send_document(tmp_path, caption="Look at this")
                assert result is True
                assert mock_post.call_args.kwargs["data"]["caption"] == "Look at this"

    def test_api_error(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            tmp.write(b"fake zip content")
            tmp.flush()

            mock_resp = MagicMock(spec=httpx.Response)
            mock_resp.json.return_value = {"ok": False, "description": "Forbidden"}

            with patch("httpx.post", return_value=mock_resp):
                notifier = TelegramNotifier(bot_token="abc", chat_id="123")
                result = notifier.send_document(Path(tmp.name))
                assert result is False

    def test_retries_on_network_error(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            tmp.write(b"fake zip content")
            tmp.flush()

            fail_resp = MagicMock(spec=httpx.Response)
            fail_resp.json.side_effect = httpx.TimeoutException("Connection timed out")

            success_resp = MagicMock(spec=httpx.Response)
            success_resp.json.return_value = {"ok": True}

            with patch("httpx.post",
                       side_effect=[fail_resp, success_resp]) as mock_post:
                with patch("time.sleep"):
                    notifier = TelegramNotifier(bot_token="abc", chat_id="123")
                    result = notifier.send_document(Path(tmp.name))
                    assert result is True
                    assert mock_post.call_count == 2
