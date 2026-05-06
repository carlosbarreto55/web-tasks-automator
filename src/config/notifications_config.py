import json
from pathlib import Path

from src.notifications.telegram import TelegramNotifier
from src.notifications.notifier import NotificationManager


def load_telegram_config(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def create_notifier(config: dict) -> NotificationManager:
    bot_token = config["bot_token"]
    chat_id = config["chat_id"]
    telegram = TelegramNotifier(bot_token=bot_token, chat_id=chat_id)
    return NotificationManager(telegram)
