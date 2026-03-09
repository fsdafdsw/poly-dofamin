import argparse
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Iterable, List, Sequence, Set, Tuple

from .config import Settings, load_settings
from .logic import AlertSignal, partition_alerts
from .polymarket import PolymarketClient
from .state import load_state, save_state
from .telegram import TelegramNotifier


def main(argv: Sequence[str] = ()) -> int:
    parser = argparse.ArgumentParser(
        description="Monitor Polymarket portfolio positions and alert in Telegram after >50% growth."
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously and check the portfolio every POLL_INTERVAL_SECONDS.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send Telegram messages; print alerts to stdout instead.",
    )
    parser.add_argument(
        "--threshold-percent",
        type=float,
        default=None,
        help="Override ALERT_THRESHOLD_PERCENT for this run.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=int,
        default=None,
        help="Override POLL_INTERVAL_SECONDS for loop mode.",
    )

    args = parser.parse_args(list(argv) if argv else None)

    settings = load_settings(require_telegram=not args.dry_run)
    if args.threshold_percent is not None:
        settings = replace(settings, threshold_percent=args.threshold_percent)
    if args.poll_interval_seconds is not None:
        settings = replace(settings, poll_interval_seconds=args.poll_interval_seconds)

    if args.loop:
        return run_forever(settings=settings, dry_run=args.dry_run)
    return run_once(settings=settings, dry_run=args.dry_run)


def run_forever(settings: Settings, dry_run: bool) -> int:
    while True:
        try:
            run_once(settings=settings, dry_run=dry_run)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            print("Check failed: {0}".format(exc))
        time.sleep(settings.poll_interval_seconds)


def run_once(settings: Settings, dry_run: bool) -> int:
    state = load_state(settings.state_path)
    client = PolymarketClient(settings)
    notifier = None if dry_run else TelegramNotifier(settings)

    positions = client.fetch_positions()
    new_alerts, active_keys = partition_alerts(
        positions=positions,
        alerted_keys=state.alerted_keys,
        threshold_percent=settings.threshold_percent,
    )

    persisted_keys = set(state.alerted_keys).intersection(active_keys)
    sent_count = 0

    if new_alerts:
        for message, keys in build_message_chunks(new_alerts, settings.threshold_percent):
            if dry_run:
                print(message)
                print("")
                sent_count += len(keys)
                continue

            try:
                notifier.send(message)
            except Exception:
                save_state(settings.state_path, persisted_keys)
                raise
            persisted_keys.update(keys)
            sent_count += len(keys)

    if not dry_run:
        save_state(settings.state_path, persisted_keys)
    print(
        "Checked {0} positions at {1}. New alerts: {2}. Active high-growth positions: {3}.".format(
            len(positions),
            datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            sent_count,
            len(active_keys),
        )
    )
    return 0


def build_message_chunks(
    alerts: Iterable[AlertSignal],
    threshold_percent: float,
    max_length: int = 3800,
) -> List[Tuple[str, Set[str]]]:
    header = "Polymarket alert: position growth above {0:.0f}%\n{1}".format(
        threshold_percent,
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    )

    chunks = []
    current_text = header
    current_keys = set()

    for index, alert in enumerate(alerts, start=1):
        block = format_alert_block(index=index, alert=alert)
        candidate = "{0}\n\n{1}".format(current_text, block)
        if current_keys and len(candidate) > max_length:
            chunks.append((current_text, current_keys))
            current_text = header + "\n\n" + block
            current_keys = {alert.position.key}
            continue

        current_text = candidate
        current_keys.add(alert.position.key)

    if current_keys:
        chunks.append((current_text, current_keys))
    return chunks


def format_alert_block(index: int, alert: AlertSignal) -> str:
    position = alert.position
    lines = [
        "{0}. {1}".format(index, position.title),
        "Outcome: {0}".format(position.outcome),
        "Avg {0} -> {1} ({2})".format(
            fmt_price(position.avg_price),
            fmt_price(position.current_price),
            fmt_percent(alert.growth_percent),
        ),
        "Size {0} | Cost {1} | Value {2}".format(
            fmt_number(position.size),
            fmt_money(position.initial_value),
            fmt_money(position.current_value),
        ),
    ]
    if position.url:
        lines.append(position.url)
    return "\n".join(lines)


def fmt_percent(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return "{0}{1:.1f}%".format(sign, value)


def fmt_money(value: float) -> str:
    return "${0:,.2f}".format(value)


def fmt_price(value: float) -> str:
    return "{0:.3f}".format(value)


def fmt_number(value: float) -> str:
    return "{0:,.2f}".format(value)
