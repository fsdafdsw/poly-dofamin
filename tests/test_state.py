import json
import os
import tempfile
import unittest

from portfolio_alert.state import load_state, save_state


class StateTests(unittest.TestCase):
    def test_load_state_defaults_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "missing.json")
            state = load_state(path)
            self.assertEqual(set(), state.growth_alerted_keys)
            self.assertEqual(set(), state.result_alerted_keys)
            self.assertFalse(state.result_tracking_initialized)

    def test_load_state_migrates_legacy_alerted_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "state.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump({"alerted_keys": ["a", "b"]}, handle)

            state = load_state(path)
            self.assertEqual({"a", "b"}, state.growth_alerted_keys)
            self.assertEqual(set(), state.result_alerted_keys)
            self.assertFalse(state.result_tracking_initialized)

    def test_save_state_persists_new_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "state.json")
            save_state(
                path=path,
                growth_alerted_keys={"growth-a"},
                result_alerted_keys={"result-a:WON"},
                result_tracking_initialized=True,
            )

            reloaded = load_state(path)
            self.assertEqual({"growth-a"}, reloaded.growth_alerted_keys)
            self.assertEqual({"result-a:WON"}, reloaded.result_alerted_keys)
            self.assertTrue(reloaded.result_tracking_initialized)


if __name__ == "__main__":
    unittest.main()
