import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.notifications.notifier import NotificationManager, _escape_html, _format_size
from src.notifications.telegram import TelegramNotifier


def make_mock_telegram():
    mock = MagicMock(spec=TelegramNotifier)
    mock.send_message.return_value = True
    mock.send_document.return_value = True
    return mock


class TestEscapeHtml:
    def test_escapes_special_chars(self):
        assert _escape_html("<script>") == "&lt;script&gt;"
        assert _escape_html("a & b") == "a &amp; b"

    def test_passes_plain_text(self):
        assert _escape_html("hello world") == "hello world"


class TestFormatSize:
    def test_bytes(self):
        assert _format_size(0) == "0 B"
        assert _format_size(500) == "500 B"
        assert _format_size(1023) == "1023 B"

    def test_kilobytes(self):
        assert _format_size(1024) == "1.0 KB"
        assert _format_size(1536) == "1.5 KB"

    def test_megabytes(self):
        assert _format_size(1048576) == "1.0 MB"


class TestNotificationManager:
    def test_notify_lab_saved_sends_message_and_zip(self):
        mock_tg = make_mock_telegram()
        nm = NotificationManager(mock_tg)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                         delete=False) as f:
            f.write("lab content here")
            tmp_path = Path(f.name)

        try:
            nm.notify_lab_saved("example-site", tmp_path, 17)

            mock_tg.send_message.assert_called_once()
            msg = mock_tg.send_message.call_args[0][0]
            assert "Projeto de Programas" in msg
            assert "lab content" not in msg

            mock_tg.send_document.assert_called_once()
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_notify_lab_saved_no_file_no_zip(self):
        mock_tg = make_mock_telegram()
        nm = NotificationManager(mock_tg)
        non_existent = Path("/nonexistent/lab.txt")

        nm.notify_lab_saved("site", non_existent, 0)

        mock_tg.send_message.assert_called_once()
        mock_tg.send_document.assert_not_called()

    def test_notify_solutions_saved_lists_files(self):
        mock_tg = make_mock_telegram()
        nm = NotificationManager(mock_tg)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            (tmp_dir / "Foo.java").write_text("class Foo {}")
            (tmp_dir / "Bar.java").write_text("class Bar {}")

            nm.notify_solutions_saved("test-site", tmp_dir,
                                      solved=["Foo.java", "Bar.java"],
                                      failed=["Baz.java"])

            mock_tg.send_message.assert_called_once()
            msg = mock_tg.send_message.call_args[0][0]
            assert "Respostas geradas" in msg
            assert "Projeto de Programas" in msg
            assert "Foo.java" in msg
            assert "Bar.java" in msg
            assert "Baz.java" in msg

            mock_tg.send_document.assert_called_once()

    def test_notify_solutions_saved_no_files_no_zip(self):
        mock_tg = make_mock_telegram()
        nm = NotificationManager(mock_tg)

        nm.notify_solutions_saved("site", Path("/tmp"), solved=[], failed=[])

        mock_tg.send_message.assert_called_once()
        mock_tg.send_document.assert_not_called()

    def test_notify_solutions_no_solved_files_in_dir(self):
        mock_tg = make_mock_telegram()
        nm = NotificationManager(mock_tg)

        with tempfile.TemporaryDirectory() as tmp:
            nm.notify_solutions_saved("site", Path(tmp),
                                      solved=["Missing.java"], failed=[])

            mock_tg.send_message.assert_called_once()
            mock_tg.send_document.assert_not_called()
