import tempfile
import zipfile
from pathlib import Path

import pytest

from src.config.notifications_config import load_telegram_config, create_notifier

TELEGRAM_CONFIG = Path("config/telegram.json")


@pytest.mark.integration
class TestTelegramIntegration:
    def test_send_message_to_test_bot(self):
        cfg = load_telegram_config(TELEGRAM_CONFIG)
        notifier = create_notifier(cfg)

        result = notifier.telegram.send_message(
            "<b>Integration Test</b>\nStatus: <i>running from pytest</i>",
            verbose=True
        )
        assert result is True

    def test_send_document_to_test_bot(self):
        cfg = load_telegram_config(TELEGRAM_CONFIG)
        notifier = create_notifier(cfg)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            test_file = tmp_dir / "integration-test.txt"
            test_file.write_text("This is a test file from the integration suite.")

            zip_path = tmp_dir / "test-bundle.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.write(test_file, test_file.name)

            result = notifier.telegram.send_document(
                zip_path,
                caption="<b>Integration Test</b>\nZipped file attached.",
                verbose=True
            )
            assert result is True

    def test_full_notification_flow(self):
        cfg = load_telegram_config(TELEGRAM_CONFIG)
        notifier = create_notifier(cfg)

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            lab_file = tmp_dir / "fake-lab-content.txt"
            lab_file.write_text("Question 1: Write a Java class.\nEnviar \"Test.java\"")

            notifier.notify_lab_saved("test-site", lab_file, len("fake content"),
                                      verbose=True)

            sol_dir = tmp_dir / "solutions"
            sol_dir.mkdir()
            (sol_dir / "Test.java").write_text("class Test {}")

            notifier.notify_solutions_saved("test-site", sol_dir,
                                            solved=["Test.java"],
                                            failed=[],
                                            verbose=True)
