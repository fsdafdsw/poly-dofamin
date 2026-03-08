from .config import Settings
from .http import post_form


class TelegramNotifier:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send(self, text: str) -> None:
        post_form(
            "https://api.telegram.org/bot{0}/sendMessage".format(self.settings.telegram_bot_token),
            data={
                "chat_id": self.settings.telegram_chat_id,
                "text": text,
                "disable_web_page_preview": "true",
            },
            timeout=self.settings.request_timeout_seconds,
        )
