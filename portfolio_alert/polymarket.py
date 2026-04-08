import json
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .config import Settings
from .http import get_json


@dataclass(frozen=True)
class Position:
    key: str
    asset: str
    condition_id: str
    title: str
    outcome: str
    slug: str
    event_slug: str
    size: float
    avg_price: float
    current_price: float
    initial_value: float
    current_value: float
    cash_pnl: float
    percent_pnl: float
    total_bought: float
    realized_pnl: float
    end_date: str
    redeemable: bool
    mergeable: bool
    negative_risk: bool

    @property
    def url(self) -> str:
        slug = self.event_slug or self.slug
        if not slug:
            return ""
        return "https://polymarket.com/event/{0}".format(slug)


@dataclass(frozen=True)
class Market:
    slug: str
    condition_id: str
    question: str
    outcomes: List[str]
    outcome_prices: List[float]
    closed: bool
    accepting_orders: bool
    automatically_resolved: bool
    uma_resolution_status: str

    def outcome_price_for(self, outcome_label: str) -> Optional[float]:
        normalized = outcome_label.strip().lower()
        for index, outcome in enumerate(self.outcomes):
            if outcome.strip().lower() != normalized:
                continue
            if index >= len(self.outcome_prices):
                return None
            return self.outcome_prices[index]
        return None


@dataclass(frozen=True)
class ResolvedProfile:
    requested_address: str
    user_profile_address: str
    display_name: str


class PolymarketClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.headers = {"User-Agent": "poly-dofamin-portfolio-alert/1.0"}

    def resolve_profile(self) -> ResolvedProfile:
        try:
            payload = get_json(
                "{0}/public-profile".format(self.settings.gamma_api_base_url),
                params={"address": self.settings.polymarket_wallet_address},
                timeout=self.settings.request_timeout_seconds,
                headers=self.headers,
            )
        except Exception:
            payload = None

        if not isinstance(payload, dict):
            return ResolvedProfile(
                requested_address=self.settings.polymarket_wallet_address,
                user_profile_address=self.settings.polymarket_wallet_address,
                display_name="",
            )

        return ResolvedProfile(
            requested_address=self.settings.polymarket_wallet_address,
            user_profile_address=_extract_user_profile_address(
                payload=payload,
                fallback=self.settings.polymarket_wallet_address,
            ),
            display_name=_extract_display_name(payload),
        )

    def fetch_positions(
        self,
        redeemable: Optional[bool] = False,
        mergeable: Optional[bool] = False,
    ) -> List[Position]:
        positions = []
        offset = 0
        profile = self.resolve_profile()

        while True:
            params = {
                "user": profile.user_profile_address,
                "sizeThreshold": 0,
                "limit": self.settings.positions_page_limit,
                "offset": offset,
                "sortBy": "PERCENTPNL",
                "sortDirection": "DESC",
            }
            if redeemable is not None:
                params["redeemable"] = str(redeemable).lower()
            if mergeable is not None:
                params["mergeable"] = str(mergeable).lower()
            payload = get_json(
                "{0}/positions".format(self.settings.data_api_base_url),
                params=params,
                timeout=self.settings.request_timeout_seconds,
                headers=self.headers,
            )
            if not isinstance(payload, list):
                raise ValueError("Unexpected Polymarket response: /positions did not return a list.")
            if not payload:
                break

            for item in payload:
                position = self._normalize_position(item)
                if position is None:
                    continue
                positions.append(position)

            if len(payload) < self.settings.positions_page_limit:
                break
            offset += len(payload)

        return positions

    def fetch_markets_by_slug(self, slugs: Iterable[str]) -> Dict[str, Market]:
        markets = {}
        for slug in slugs:
            normalized_slug = str(slug or "").strip()
            if not normalized_slug or normalized_slug in markets:
                continue
            try:
                market = self.fetch_market_by_slug(normalized_slug)
            except Exception:
                continue
            if market is None:
                continue
            markets[normalized_slug] = market
        return markets

    def fetch_market_by_slug(self, slug: str) -> Optional[Market]:
        payload = get_json(
            "{0}/markets/slug/{1}".format(self.settings.gamma_api_base_url, slug),
            timeout=self.settings.request_timeout_seconds,
            headers=self.headers,
        )
        if not isinstance(payload, dict):
            return None
        return self._normalize_market(payload)

    def _normalize_position(self, payload: Dict[str, Any]) -> Optional[Position]:
        size = _to_float(payload.get("size"))
        if size <= 0:
            return None

        asset = str(payload.get("asset") or "").strip()
        condition_id = str(payload.get("conditionId") or "").strip()
        outcome = str(payload.get("outcome") or "Unknown").strip()
        key = asset or "{0}:{1}".format(condition_id, outcome.lower())

        avg_price = _to_float(payload.get("avgPrice"))
        current_price = _to_float(payload.get("curPrice"))
        initial_value = _to_float(payload.get("initialValue")) or (size * avg_price)
        current_value = _to_float(payload.get("currentValue")) or (size * current_price)

        return Position(
            key=key,
            asset=asset,
            condition_id=condition_id,
            title=str(payload.get("title") or payload.get("slug") or "Untitled market").strip(),
            outcome=outcome,
            slug=str(payload.get("slug") or "").strip(),
            event_slug=str(payload.get("eventSlug") or "").strip(),
            size=size,
            avg_price=avg_price,
            current_price=current_price,
            initial_value=initial_value,
            current_value=current_value,
            cash_pnl=_to_float(payload.get("cashPnl")),
            percent_pnl=_to_float(payload.get("percentPnl")),
            total_bought=_to_float(payload.get("totalBought")),
            realized_pnl=_to_float(payload.get("realizedPnl")),
            end_date=str(payload.get("endDate") or "").strip(),
            redeemable=bool(payload.get("redeemable", False)),
            mergeable=bool(payload.get("mergeable", False)),
            negative_risk=bool(payload.get("negativeRisk", False)),
        )

    def _normalize_market(self, payload: Dict[str, Any]) -> Market:
        return Market(
            slug=str(payload.get("slug") or "").strip(),
            condition_id=str(payload.get("conditionId") or "").strip(),
            question=str(payload.get("question") or "").strip(),
            outcomes=_parse_jsonish_array(payload.get("outcomes")),
            outcome_prices=[_to_float(item) for item in _parse_jsonish_array(payload.get("outcomePrices"))],
            closed=bool(payload.get("closed", False)),
            accepting_orders=bool(payload.get("acceptingOrders", False)),
            automatically_resolved=bool(payload.get("automaticallyResolved", False)),
            uma_resolution_status=str(payload.get("umaResolutionStatus") or "").strip(),
        )


def _to_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _parse_jsonish_array(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return []
        if isinstance(loaded, list):
            return loaded
    return []


def _extract_user_profile_address(payload: Dict[str, Any], fallback: str) -> str:
    candidate = str(payload.get("proxyWallet") or "").strip()
    if candidate:
        return candidate
    return fallback


def _extract_display_name(payload: Dict[str, Any]) -> str:
    for key in ("name", "pseudonym", "xUsername"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return ""
