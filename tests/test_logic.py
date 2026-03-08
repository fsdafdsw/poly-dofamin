import unittest

from portfolio_alert.logic import compute_growth_percent, partition_alerts
from portfolio_alert.polymarket import Position, _extract_display_name, _extract_user_profile_address


def make_position(key: str, avg_price: float, current_price: float) -> Position:
    size = 100.0
    return Position(
        key=key,
        asset=key,
        condition_id="condition-" + key,
        title="Market " + key,
        outcome="Yes",
        slug="market-" + key,
        event_slug="market-" + key,
        size=size,
        avg_price=avg_price,
        current_price=current_price,
        initial_value=size * avg_price,
        current_value=size * current_price,
        cash_pnl=size * (current_price - avg_price),
        percent_pnl=0.0,
        total_bought=size,
        realized_pnl=0.0,
        end_date="",
        redeemable=False,
        mergeable=False,
        negative_risk=False,
    )


class LogicTests(unittest.TestCase):
    def test_compute_growth_percent(self) -> None:
        position = make_position("one", avg_price=0.25, current_price=0.55)
        self.assertAlmostEqual(compute_growth_percent(position), 120.0)

    def test_partition_alerts_only_for_new_threshold_crossings(self) -> None:
        positions = [
            make_position("a", avg_price=0.20, current_price=0.45),
            make_position("b", avg_price=0.30, current_price=0.40),
        ]
        alerts, active_keys = partition_alerts(
            positions=positions,
            alerted_keys={"a"},
            threshold_percent=100.0,
        )

        self.assertEqual([], alerts)
        self.assertEqual({"a"}, active_keys)

    def test_partition_alerts_rearms_after_drop_below_threshold(self) -> None:
        positions_below = [make_position("a", avg_price=0.25, current_price=0.45)]
        alerts_below, active_keys_below = partition_alerts(
            positions=positions_below,
            alerted_keys={"a"},
            threshold_percent=100.0,
        )
        self.assertEqual([], alerts_below)
        self.assertEqual(set(), active_keys_below)

        positions_above = [make_position("a", avg_price=0.25, current_price=0.60)]
        alerts_above, active_keys_above = partition_alerts(
            positions=positions_above,
            alerted_keys=set(),
            threshold_percent=100.0,
        )
        self.assertEqual(1, len(alerts_above))
        self.assertEqual({"a"}, active_keys_above)

    def test_partition_alerts_does_not_fire_at_exactly_100_percent(self) -> None:
        positions = [make_position("a", avg_price=0.25, current_price=0.50)]
        alerts, active_keys = partition_alerts(
            positions=positions,
            alerted_keys=set(),
            threshold_percent=100.0,
        )
        self.assertEqual([], alerts)
        self.assertEqual(set(), active_keys)

    def test_extract_user_profile_address_prefers_proxy_wallet(self) -> None:
        payload = {"proxyWallet": "0x1234567890abcdef1234567890abcdef12345678"}
        self.assertEqual(
            "0x1234567890abcdef1234567890abcdef12345678",
            _extract_user_profile_address(payload, fallback="0xfallback"),
        )

    def test_extract_display_name(self) -> None:
        self.assertEqual("name1", _extract_display_name({"name": "name1"}))
        self.assertEqual("pseudo", _extract_display_name({"pseudonym": "pseudo"}))


if __name__ == "__main__":
    unittest.main()
