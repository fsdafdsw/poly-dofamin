import os
import re
from dataclasses import dataclass


ADDRESS_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")


@dataclass(frozen=True)
class Settings:
    polymarket_wallet_address: str
    telegram_bot_token: str
    telegram_chat_id: str
    threshold_percent: float
    poll_interval_seconds: int
    request_timeout_seconds: int
    positions_page_limit: int
    state_path: str
    data_api_base_url: str
    gamma_api_base_url: str


def load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return

    with open(path, "r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or key in os.environ:
                continue
            if value and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            os.environ[key] = value


def load_settings(require_telegram: bool = True) -> Settings:
    load_dotenv()

    polymarket_wallet_address = os.getenv("POLYMARKET_WALLET_ADDRESS", "").strip()
    telegram_bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    missing = []
    if not polymarket_wallet_address:
        missing.append("POLYMARKET_WALLET_ADDRESS")
    if require_telegram and not telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")
    if require_telegram and not telegram_chat_id:
        missing.append("TELEGRAM_CHAT_ID")
    if missing:
        raise ValueError("Missing required environment variables: {0}".format(", ".join(missing)))

    if polymarket_wallet_address and not ADDRESS_RE.match(polymarket_wallet_address):
        raise ValueError(
            "POLYMARKET_WALLET_ADDRESS must be a 0x-prefixed 40-hex wallet address."
        )

    threshold_percent = _env_float("ALERT_THRESHOLD_PERCENT", 100.0)
    poll_interval_seconds = _env_int("POLL_INTERVAL_SECONDS", 300)
    request_timeout_seconds = _env_int("REQUEST_TIMEOUT_SECONDS", 20)
    positions_page_limit = _env_int("POSITIONS_PAGE_LIMIT", 200)
    state_path = os.getenv("STATE_PATH", "state/portfolio_alert_state.json").strip()
    data_api_base_url = os.getenv("POLYMARKET_DATA_API_URL", "https://data-api.polymarket.com").strip()
    gamma_api_base_url = os.getenv("POLYMARKET_GAMMA_API_URL", "https://gamma-api.polymarket.com").strip()

    if positions_page_limit < 1 or positions_page_limit > 500:
        raise ValueError("POSITIONS_PAGE_LIMIT must be between 1 and 500.")
    if threshold_percent < 0:
        raise ValueError("ALERT_THRESHOLD_PERCENT must be >= 0.")
    if poll_interval_seconds < 1:
        raise ValueError("POLL_INTERVAL_SECONDS must be >= 1.")
    if request_timeout_seconds < 1:
        raise ValueError("REQUEST_TIMEOUT_SECONDS must be >= 1.")

    return Settings(
        polymarket_wallet_address=polymarket_wallet_address,
        telegram_bot_token=telegram_bot_token,
        telegram_chat_id=telegram_chat_id,
        threshold_percent=threshold_percent,
        poll_interval_seconds=poll_interval_seconds,
        request_timeout_seconds=request_timeout_seconds,
        positions_page_limit=positions_page_limit,
        state_path=state_path,
        data_api_base_url=data_api_base_url.rstrip("/"),
        gamma_api_base_url=gamma_api_base_url.rstrip("/"),
    )


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("{0} must be an integer.".format(name)) from exc


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return float(raw_value)
    except ValueError as exc:
        raise ValueError("{0} must be a number.".format(name)) from exc
