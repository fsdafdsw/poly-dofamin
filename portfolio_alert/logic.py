from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .polymarket import Market, Position


@dataclass(frozen=True)
class AlertSignal:
    position: Position
    growth_percent: float


@dataclass(frozen=True)
class ResultSignal:
    position: Position
    result: str
    settlement_price: Optional[float]


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


def partition_result_alerts(
    positions: Sequence[Position],
    markets_by_slug: Dict[str, Market],
    alerted_result_keys: Iterable[str],
) -> Tuple[List[ResultSignal], Set[str]]:
    known_alerts = set(alerted_result_keys)
    persisted = set(known_alerts)
    alerts = []

    for position in positions:
        result, settlement_price = detect_position_result(position, markets_by_slug)
        if result is None:
            continue

        alert_key = "{0}:{1}".format(position.key, result)
        if alert_key in known_alerts:
            continue

        alerts.append(
            ResultSignal(
                position=position,
                result=result,
                settlement_price=settlement_price,
            )
        )
        persisted.add(alert_key)

    alerts.sort(key=lambda item: (item.result != "WON", item.position.title.lower(), item.position.outcome.lower()))
    return alerts, persisted


def detect_position_result(
    position: Position,
    markets_by_slug: Dict[str, Market],
) -> Tuple[Optional[str], Optional[float]]:
    if position.redeemable:
        return "WON", 1.0

    market = markets_by_slug.get(position.slug)
    if market is None:
        return None, None
    if not is_resolved_market(market):
        return None, None

    settlement_price = market.outcome_price_for(position.outcome)
    if settlement_price is None:
        return None, None
    if settlement_price >= 0.999:
        return "WON", settlement_price
    if settlement_price <= 0.001:
        return "LOST", settlement_price
    return None, None


def is_resolved_market(market: Market) -> bool:
    status = market.uma_resolution_status.strip().lower()
    if any(token in status for token in ("resolved", "final", "settled", "complete", "priced")):
        return True
    return market.closed and not market.accepting_orders and _has_binary_settlement_prices(market.outcome_prices)


def _has_binary_settlement_prices(outcome_prices: Sequence[float]) -> bool:
    if len(outcome_prices) != 2:
        return False
    low, high = sorted(outcome_prices)
    return low <= 0.001 and high >= 0.999 and abs(sum(outcome_prices) - 1.0) <= 0.01
