from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Set, Tuple

from .polymarket import Position


@dataclass(frozen=True)
class AlertSignal:
    position: Position
    growth_percent: float


def compute_growth_percent(position: Position) -> Optional[float]:
    if position.avg_price <= 0:
        return None
    return ((position.current_price - position.avg_price) / position.avg_price) * 100.0


def partition_alerts(
    positions: Sequence[Position],
    alerted_keys: Iterable[str],
    threshold_percent: float,
) -> Tuple[List[AlertSignal], Set[str]]:
    known_alerts = set(alerted_keys)
    active_keys = set()
    new_alerts = []

    for position in positions:
        growth_percent = compute_growth_percent(position)
        if growth_percent is None:
            continue
        if growth_percent <= threshold_percent:
            continue

        active_keys.add(position.key)
        if position.key in known_alerts:
            continue
        new_alerts.append(AlertSignal(position=position, growth_percent=growth_percent))

    new_alerts.sort(key=lambda item: item.growth_percent, reverse=True)
    return new_alerts, active_keys
